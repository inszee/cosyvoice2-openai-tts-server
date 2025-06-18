#!/usr/bin/env python3
"""
CosyVoice2 Client Wrapper

CosyVoice2モデルのラッパークラス
音声合成、クローニング機能を提供
"""

import asyncio
import io
import logging
import os
import sys
import tempfile
import threading
import time
import json
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf
import torch
import torchaudio
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

logger = logging.getLogger(__name__)


class CosyVoiceClient:
    """CosyVoice2クライアント"""
    
    def __init__(self, config):
        self.config = config
        self.model = None
        self.sample_rate = 22050
        self.executor = ThreadPoolExecutor(max_workers=config.concurrent_requests)
        self.custom_speakers = {}
        self.model_lock = threading.Lock()
        self.voice_mapping = {}
        self.voice_prompt_mapping = {}
        self.spk2info  = {}
        # デフォルト音声マッピング (OpenAI互換)
        # self.voice_mapping = {
        #     # "alloy": "中文女",
        #     # "echo": "中文男",
        #     # "fable": "英文女",
        #     # "onyx": "英文男",
        #     # "nova": "日文女",
        #     # "shimmer": "韩文女",
        # }

    def load_config(self,json_config_path):
        with open(json_config_path, 'r') as f:
            return json.load(f)

    def apply_per_file_config(self,wav_dir, json_config):
        files_config = {}

        for filename in os.listdir(wav_dir):
            if not filename.lower().endswith(".wav"):
                continue
            # Try per-file exact match first
            file_cfg = json_config.get("wav_files", {}).get(filename, {})
            # Merge with defaults
            full_cfg = {
                "sample_rate": json_config.get("sample_rate", 16000),
            }
            full_cfg.update(file_cfg)
            spk_id = os.path.splitext(filename)[0]  # removes ".wav"
            files_config[spk_id] = full_cfg
        return files_config

    async def initialize(self):
        """クライアント初期化"""
        try:
            await self._setup_environment()
            await self._load_model()
            logger.info("CosyVoice client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize CosyVoice client: {e}")
            raise
    
    async def _setup_environment(self):
        """環境セットアップ"""
        # CosyVoiceのパス設定
        cosyvoice_path = Path("./CosyVoice")
        if cosyvoice_path.exists():
            sys.path.insert(0, str(cosyvoice_path))
            sys.path.insert(0, str(cosyvoice_path / "third_party" / "Matcha-TTS"))
        
        # モデルディレクトリ作成
        model_dir = Path(self.config.model_path)
        model_dir.mkdir(parents=True, exist_ok=True)

        # モデルダウンロード（未存在の場合）
        if not (model_dir / "cosyvoice2.yaml").exists():
            await self._download_models()
    
    async def _download_models(self):
        """モデルダウンロード"""
        logger.info("Downloading CosyVoice2 models...")
        
        def download():
            try:
                from modelscope import snapshot_download
                
                # CosyVoice2-0.5B (推奨)
                snapshot_download(
                    'iic/CosyVoice2-0.5B',
                    local_dir=self.config.model_path
                )
                
                # TTSFRD リソース (中国語正規化用)
                ttsfrd_path = "./pretrained_models/CosyVoice-ttsfrd"
                Path(ttsfrd_path).mkdir(parents=True, exist_ok=True)
                snapshot_download(
                    'iic/CosyVoice-ttsfrd',
                    local_dir=ttsfrd_path
                )
                
                logger.info("Models downloaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to download models: {e}")
                raise
        
        await asyncio.get_event_loop().run_in_executor(self.executor, download)
    
    async def _load_model(self):
        """モデル読み込み"""
        def load():
            try:
                # CosyVoiceインポート
                from cosyvoice.cli.cosyvoice import CosyVoice2
                from cosyvoice.utils.file_utils import load_wav
                # モデル初期化
                self.model = CosyVoice2(
                    self.config.model_path,
                    load_jit=False,
                    load_trt=False,
                    load_vllm=False,
                    fp16=self.config.fp16
                )
                default_spk_voice_dir = Path(self.config.default_spk_voice_path)
                default_spk_voice_dir.mkdir(parents=True, exist_ok=True)

                default_spk_voice_config = os.path.join(default_spk_voice_dir, "config.json")

                json_config = self.load_config(default_spk_voice_config)
                json_file_configs = self.apply_per_file_config(default_spk_voice_dir, json_config)
                logging.info("Generated files_config:\n%s", json.dumps(json_file_configs, indent=2, ensure_ascii=False))
                start = time.time()
                model_dir = Path(self.config.model_path)
                for spk_id in json_file_configs:
                    config_item = json_file_configs[spk_id]
                    spk2info_path = os.path.join(model_dir, config_item["spk2info_path"])
                    speaker = config_item["speaker"]
                    prompt_text  = config_item["prompt_text"]
                    prompt_speech_16k_wav = os.path.join(default_spk_voice_dir, f"{spk_id}.wav")
                    prompt_speech_16k = load_wav(prompt_speech_16k_wav, 16000)
                    if os.path.exists(spk2info_path):
                        self.spk2info[speaker] = torch.load(spk2info_path, map_location=self.model.frontend.device)
                    else:
                        if speaker in self.spk2info:
                            del self.spk2info[speaker]

                    if speaker not in self.spk2info:
                        # 获取音色embedding
                        embedding = self.model.frontend._extract_spk_embedding(prompt_speech_16k)
                        # 获取语音特征
                        prompt_speech_resample = torchaudio.transforms.Resample(orig_freq=16000, new_freq=self.model.sample_rate)(prompt_speech_16k)
                        speech_feat, speech_feat_len = self.model.frontend._extract_speech_feat(prompt_speech_resample)
                        # 获取语音token
                        speech_token, speech_token_len = self.model.frontend._extract_speech_token(prompt_speech_16k)
                        # 将音色embedding、语音特征和语音token保存到字典中
                        self.spk2info[speaker] = {'embedding': embedding,
                                            'speech_feat': speech_feat, 'speech_token': speech_token}
                        # 保存音色embedding
                        torch.save(self.spk2info, spk2info_path)
                    self.voice_mapping[spk_id] = speaker
                    self.voice_prompt_mapping[spk_id] = prompt_text

                load_time = time.time() - start
                logging.info("Load time: %.3f seconds", load_time)
                self.sample_rate = self.model.sample_rate
                logger.info(f"Model loaded, sample rate: {self.sample_rate}")
                
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise
        
        await asyncio.get_event_loop().run_in_executor(self.executor, load)
    
    def is_model_loaded(self) -> bool:
        """モデル読み込み状態確認"""
        return self.model is not None
    
    def is_gpu_available(self) -> bool:
        """GPU使用可能性確認"""
        return torch.cuda.is_available() and self.config.device != "cpu"
    
    # 定义一个文本到语音的函数，参数包括文本内容、是否流式处理、语速和是否使用文本前端处理
    def tts_sft(self, tts_text, speaker_id,stream=False, speed=1.0, text_frontend=True):
        prompt_text =  self.voice_prompt_mapping[speaker_id]
        speaker = self.voice_mapping[speaker_id]
        speaker_info = self.spk2info[speaker][speaker]
        # self.spk2info[speaker] = {'中文女': {}}.... 
        # speaker_info = self.spk2info[speaker][speaker]
        for i in tqdm(self.model.frontend.text_normalize(tts_text, split=True, text_frontend=text_frontend)):
            # 提取文本的token和长度
            tts_text_token, tts_text_token_len = self.model.frontend._extract_text_token(i)
            # 提取提示文本的token和长度
            prompt_text_token, prompt_text_token_len = self.model.frontend._extract_text_token(prompt_text)
            # 获取说话人的语音token长度，并转换为torch张量，移动到指定设备
            speech_token_len = torch.tensor([speaker_info['speech_token'].shape[1]], dtype=torch.int32).to(self.model.frontend.device)
            # 获取说话人的语音特征长度，并转换为torch张量，移动到指定设备
            speech_feat_len = torch.tensor([speaker_info['speech_feat'].shape[1]], dtype=torch.int32).to(self.model.frontend.device)
            # 构建模型输入字典，包括文本、文本长度、提示文本、提示文本长度、LLM提示语音token、LLM提示语音token长度、流提示语音token、流提示语音token长度、提示语音特征、提示语音特征长度、LLM嵌入和流嵌入
            model_input = {'text': tts_text_token, 'text_len': tts_text_token_len,
                        'prompt_text': prompt_text_token, 'prompt_text_len': prompt_text_token_len,
                        'llm_prompt_speech_token': speaker_info['speech_token'], 'llm_prompt_speech_token_len': speech_token_len,
                        'flow_prompt_speech_token':speaker_info['speech_token'], 'flow_prompt_speech_token_len': speech_token_len,
                        'prompt_speech_feat': speaker_info['speech_feat'], 'prompt_speech_feat_len': speech_feat_len,
                        'llm_embedding': speaker_info['embedding'], 'flow_embedding': speaker_info['embedding']}
            # 使用模型进行文本到语音的转换，并迭代输出结果
            for model_output in self.model.model.tts(**model_input, stream=stream, speed=speed):
                yield model_output

    async def list_available_voices(self) -> List[Dict]:
        """利用可能音声一覧"""
        voices = []
        
        # デフォルト音声
        for voice_id, speaker in self.voice_mapping.items():
            voices.append({
                "id": voice_id,
                "name": voice_id.title(),
                "speaker": speaker,
                "language": self._get_language_from_speaker(speaker),
                "type": "preset"
            })
        
        # カスタム音声
        for speaker_name, info in self.custom_speakers.items():
            voices.append({
                "id": speaker_name,
                "name": speaker_name,
                "speaker": speaker_name,
                "language": "auto",
                "type": "custom",
                "description": info.get("description", "")
            })
        
        return voices
    
    def _get_language_from_speaker(self, speaker: str) -> str:
        """スピーカーから言語を推定"""
        if "中文" in speaker or "中国" in speaker:
            return "zh"
        elif "英文" in speaker or "English" in speaker:
            return "en"
        elif "日文" in speaker or "日本" in speaker:
            return "ja"
        elif "韩文" in speaker or "한국" in speaker:
            return "ko"
        else:
            return "auto"
    
    async def synthesize(
        self,
        text: str,
        voice: str = "linzhiling",
        model: str = "cosyvoice2-0.5b",
        response_format: str = "mp3",
        speed: float = 1.0,
    ) -> bytes:
        """音声合成"""
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        def _synthesize():
            with self.model_lock:
                try:
                    # 音声選択
                    if voice in self.custom_speakers:
                        # カスタム音声使用
                        speaker_id = voice
                        use_zero_shot = True
                    else:
                        # デフォルト音声使用
                        speaker = self.voice_mapping.get(voice, "中文女")
                        speaker_id = speaker
                        use_zero_shot = False
                    
                    # テキスト前処理
                    processed_text = self._preprocess_text(text)
                    
                    # 音声合成実行
                    if use_zero_shot and voice in self.custom_speakers:
                        # Zero-shot合成（カスタム音声）
                        audio_data = list(self.model.inference_zero_shot(
                            processed_text,
                            "",
                            "",
                            zero_shot_spk_id=speaker_id,
                            stream=False
                        ))
                    else:
                        logger.info("list(self.tts_sft(processed_text,speaker_id,stream=False))")
                        audio_data = list(self.tts_sft(processed_text,voice,stream=False))
                        # SFT合成（デフォルト音声）
                        # audio_data = list(self.model.inference_sft(
                        #     processed_text,
                        #     speaker_id,
                        #     stream=False
                        # ))
                        
                    if not audio_data:
                        raise RuntimeError("Failed to generate audio")
                    
                    # 音声データ取得
                    audio_tensor = audio_data[0]['tts_speech']
                    
                    # 速度調整
                    if speed != 1.0:
                        audio_tensor = self._adjust_speed(audio_tensor, speed)
                    
                    # フォーマット変換
                    return self._convert_audio_format(
                        audio_tensor, response_format
                    )
                    
                except Exception as e:
                    logger.error(f"Synthesis failed: {e}")
                    raise
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _synthesize
        )
    
    async def synthesize_stream(
        self,
        text: str,
        voice: str = "linzhiling",
        model: str = "cosyvoice2-0.5b",
        response_format: str = "mp3",
        speed: float = 1.0,
    ) -> AsyncGenerator[bytes, None]:
        """ストリーミング音声合成"""
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        def _synthesize_stream():
            with self.model_lock:
                try:
                    # 音声選択
                    if voice in self.custom_speakers:
                        speaker_id = voice
                        use_zero_shot = True
                    else:
                        speaker = self.voice_mapping.get(voice, "中文女")
                        speaker_id = speaker
                        use_zero_shot = False
                    
                    # テキスト前処理
                    processed_text = self._preprocess_text(text)
                    
                    # ストリーミング合成
                    if use_zero_shot and voice in self.custom_speakers:
                        audio_generator = self.model.inference_zero_shot(
                            processed_text,
                            "",
                            "",
                            zero_shot_spk_id=speaker_id,
                            stream=True
                        )
                    else:
                        audio_generator = self.tts_sft(processed_text,voice,stream=True)
                        # audio_generator = self.model.inference_sft(
                        #     processed_text,
                        #     speaker_id,
                        #     stream=True
                        # )
                    
                    # チャンクごとに処理
                    for chunk in audio_generator:
                        audio_tensor = chunk['tts_speech']
                        
                        if speed != 1.0:
                            audio_tensor = self._adjust_speed(audio_tensor, speed)
                        
                        yield self._convert_audio_format(
                            audio_tensor, response_format
                        )
                        
                except Exception as e:
                    logger.error(f"Streaming synthesis failed: {e}")
                    raise
        
        # ストリーミング実行
        for chunk in _synthesize_stream():
            yield chunk
    
    def _preprocess_text(self, text: str) -> str:
        """テキスト前処理"""
        # 基本的なテキストクリーニング
        text = text.strip()
        
        # 長すぎるテキストの分割対応（将来的な拡張）
        if len(text) > self.config.max_text_length:
            text = text[:self.config.max_text_length]
            logger.warning(f"Text truncated to {self.config.max_text_length} characters")
        
        return text
    
    def _adjust_speed(self, audio_tensor: torch.Tensor, speed: float) -> torch.Tensor:
        """音声速度調整"""
        if speed == 1.0:
            return audio_tensor
        
        try:
            # PyTorchのリサンプリングを使用した簡易速度調整
            if speed > 1.0:
                # 高速化: ダウンサンプリング後アップサンプリング
                new_rate = int(self.sample_rate / speed)
                resampler_down = torchaudio.transforms.Resample(
                    self.sample_rate, new_rate
                )
                resampler_up = torchaudio.transforms.Resample(
                    new_rate, self.sample_rate
                )
                audio_tensor = resampler_up(resampler_down(audio_tensor))
            else:
                # 低速化: アップサンプリング後ダウンサンプリング
                new_rate = int(self.sample_rate / speed)
                resampler_up = torchaudio.transforms.Resample(
                    self.sample_rate, new_rate
                )
                resampler_down = torchaudio.transforms.Resample(
                    new_rate, self.sample_rate
                )
                audio_tensor = resampler_down(resampler_up(audio_tensor))
            
            return audio_tensor
            
        except Exception as e:
            logger.warning(f"Speed adjustment failed: {e}, using original audio")
            return audio_tensor
    
    def _convert_audio_format(
        self, audio_tensor: torch.Tensor, format: str = "mp3"
    ) -> bytes:
        """音声フォーマット変換"""
        try:
            # NumPy配列に変換
            if audio_tensor.dim() > 1:
                audio_numpy = audio_tensor.squeeze().cpu().numpy()
            else:
                audio_numpy = audio_tensor.cpu().numpy()
            
            # メモリバッファに保存
            buffer = io.BytesIO()
            
            if format == "wav":
                sf.write(buffer, audio_numpy, self.sample_rate, format='WAV')
            elif format == "flac":
                sf.write(buffer, audio_numpy, self.sample_rate, format='FLAC')
            elif format == "mp3":
                # WAVとして一時保存してからMP3変換
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                    sf.write(tmp_wav.name, audio_numpy, self.sample_rate)
                    
                    # ffmpegでMP3変換
                    mp3_path = tmp_wav.name.replace(".wav", ".mp3")
                    cmd = f"ffmpeg -i {tmp_wav.name} -codec:a libmp3lame -b:a 128k {mp3_path} -y"
                    
                    import subprocess
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True
                    )
                    
                    if result.returncode == 0:
                        with open(mp3_path, "rb") as f:
                            buffer.write(f.read())
                        os.unlink(mp3_path)
                    else:
                        # ffmpeg失敗時はWAVを返す
                        logger.warning("MP3 conversion failed, returning WAV")
                        buffer.seek(0)
                        sf.write(buffer, audio_numpy, self.sample_rate, format='WAV')
                    
                    os.unlink(tmp_wav.name)
            else:
                # デフォルト: WAV
                sf.write(buffer, audio_numpy, self.sample_rate, format='WAV')
            
            buffer.seek(0)
            return buffer.read()
            
        except Exception as e:
            logger.error(f"Audio format conversion failed: {e}")
            raise
    
    async def clone_voice(
        self, audio_path: str, speaker_name: str, description: str = None
    ) -> bool:
        """音声クローニング"""
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        def _clone_voice():
            try:
                # 音声ファイル読み込み
                from cosyvoice.utils.file_utils import load_wav
                
                prompt_speech = load_wav(audio_path, 16000)
                
                # Zero-shotスピーカー追加
                success = self.model.add_zero_shot_spk(
                    description or f"Cloned voice: {speaker_name}",
                    prompt_speech,
                    speaker_name
                )
                
                if success:
                    # カスタムスピーカー情報保存
                    self.custom_speakers[speaker_name] = {
                        "description": description,
                        "created_at": time.time(),
                        "audio_path": audio_path,
                    }
                    logger.info(f"Voice cloned successfully: {speaker_name}")
                
                return success
                
            except Exception as e:
                logger.error(f"Voice cloning failed: {e}")
                return False
        
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _clone_voice
        )
    
    async def delete_voice(self, speaker_name: str) -> bool:
        """音声削除"""
        if speaker_name in self.custom_speakers:
            del self.custom_speakers[speaker_name]
            # モデルからも削除（CosyVoiceのAPIがあれば）
            return True
        return False
    
    async def cleanup(self):
        """クリーンアップ"""
        if self.executor:
            self.executor.shutdown(wait=True)
        
        if self.model:
            # GPUメモリ解放
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        logger.info("CosyVoice client cleaned up")