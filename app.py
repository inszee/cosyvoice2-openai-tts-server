#!/usr/bin/env python3
"""
CosyVoice2 OpenAI Compatible TTS Server

OpenAI TTS API互換のサーバー実装
DifyでTTSモデルとして使用可能
"""

import asyncio
import logging
import os
import tempfile
import time
import json
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Union

import aiofiles
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from config import Config
from cosyvoice_client import CosyVoiceClient
from models import (
    AudioSpeechRequest,
    AudioSpeechResponse,
    ErrorResponse,
    HealthResponse,
    ModelListResponse,
    ModelObject,
    VoiceCloneRequest,
    VoiceListResponse,
)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# グローバル変数
cosyvoice_client: Optional[CosyVoiceClient] = None
config = Config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    global cosyvoice_client
    
    logger.info("Starting CosyVoice TTS Server...")
    
    try:
        # CosyVoiceクライアント初期化
        cosyvoice_client = CosyVoiceClient(config)
        await cosyvoice_client.initialize()
        logger.info("CosyVoice client initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize CosyVoice client: {e}")
        raise
    finally:
        if cosyvoice_client:
            await cosyvoice_client.cleanup()
        logger.info("CosyVoice TTS Server shutdown")


# FastAPIアプリケーション作成
app = FastAPI(
    title="CosyVoice2 OpenAI TTS Server",
    description="OpenAI compatible TTS server using CosyVoice2",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """ヘルスチェック"""
    if cosyvoice_client is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return HealthResponse(
        status="healthy",
        model_loaded=cosyvoice_client.is_model_loaded(),
        gpu_available=cosyvoice_client.is_gpu_available(),
        version="1.0.0"
    )


@app.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    """利用可能なモデル一覧"""
    models = [
        ModelObject(
            id="cosyvoice2-0.5b",
            object="model",
            created=int(time.time()),
            owned_by="alibaba",
        )
    ]
    return ModelListResponse(object="list", data=models)


@app.get("/v1/voices", response_model=VoiceListResponse)
async def list_voices():
    """利用可能な音声一覧"""
    if cosyvoice_client is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    voices = await cosyvoice_client.list_available_voices()
    return VoiceListResponse(voices=voices)


@app.post("/v1/audio/speech")
async def create_speech(request: AudioSpeechRequest):
    """音声合成 (OpenAI互換エンドポイント)"""
    if cosyvoice_client is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # 入力検証
        if len(request.input) > config.max_text_length:
            raise HTTPException(
                status_code=400,
                detail=f"Input text too long. Maximum {config.max_text_length} characters."
            )
        
        logger.info(f"Generating speech for text: {request.input[:50]}...")
        
        # 音声合成実行
        audio_data = await cosyvoice_client.synthesize(
            text=request.input,
            voice=request.voice,
            model=request.model,
            response_format=request.response_format,
            speed=request.speed,
        )
        
        # Content-Typeを決定
        content_type_map = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "flac": "audio/flac",
            "aac": "audio/aac",
        }
        content_type = content_type_map.get(request.response_format, "audio/mpeg")
        
        logger.info(f"Speech generated successfully, size: {len(audio_data)} bytes")
        
        return Response(
            content=audio_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{request.response_format}"
            },
        )
        
    except Exception as e:
        logger.error(f"Speech synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/voice/clone")
async def clone_voice(
    voice_sample: UploadFile = File(...),
    speaker_name: str = Form(...),
    description: Optional[str] = Form(None),
):
    """音声クローニング"""
    if cosyvoice_client is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # ファイル検証
        if not voice_sample.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="Invalid audio file")
        
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            content = await voice_sample.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # 音声クローニング実行
            success = await cosyvoice_client.clone_voice(
                audio_path=tmp_file_path,
                speaker_name=speaker_name,
                description=description,
            )
            
            if success:
                return {"status": "success", "speaker_name": speaker_name}
            else:
                raise HTTPException(status_code=500, detail="Voice cloning failed")
                
        finally:
            # 一時ファイル削除
            os.unlink(tmp_file_path)
            
    except Exception as e:
        logger.error(f"Voice cloning failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/voice/clone_generate")
async def clone_generate(
    voice_sample: UploadFile = File(...),
    speaker_name_id: str = Form(...),
    speaker_name:  str = Form(...),
    customer_id: str = Form(...),
    description: Optional[str] = Form(None),
):
    if cosyvoice_client is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        if not voice_sample.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="Invalid audio file")

        if not os.path.exists(config.default_spk_voice_path):
            os.makedirs(config.default_spk_voice_path)

        # 1. Check for a unique filename to prevent overwriting
        unique_filename = f"{speaker_name_id}.wav"
        file_path = os.path.join(config.default_spk_voice_path, unique_filename)
        
        if os.path.exists(file_path):
            raise HTTPException(status_code=409, detail=f"Speaker '{speaker_name_id}' already exists.")

        config_filename = f"config.json"
        config_file_path = os.path.join(config.default_spk_voice_path, config_filename)

        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await voice_sample.read()
            await out_file.write(content)
            
        try:
            with open(config_file_path, 'r+', encoding='utf-8') as f:
                config_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config_data = {
                "sample_rate": 16000,
                "wav_files": {}
            }
        
        spk2_info_name = f"{speaker_name_id}_spk2info.pt"
        
        config_data["wav_files"][unique_filename] = {
            "id": speaker_name_id, # Assign a unique ID to avoid conflicts
            "customer_id": customer_id, # 2. Added new parameter
            "speaker": speaker_name,
            "spk2info_path": spk2_info_name,
            "prompt_text": description or ""
        }

        with open(config_file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
            
        try:
            success = await cosyvoice_client.clone_voice_saved()
            
            if success:
                return {"status": "success", "customer_id": customer_id,"speaker_name_id":speaker_name_id,"speaker_name": speaker_name}
            else:
                raise HTTPException(status_code=500, detail="Voice cloning failed")
                
        except Exception as e:
            # Add rollback logic here if needed
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Remove the entry from config_data before raising the exception
            if speaker_name_id in config_data["wav_files"]:
                del config_data["wav_files"][speaker_name_id]
                with open(config_file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            raise e
            
    except HTTPException as http_exc:
        # Re-raise HTTPException to be handled by FastAPI
        raise http_exc
    except Exception as e:
        if logger:
            logger.error(f"Voice clone_generate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/v1/voice/{speaker_name}")
async def delete_voice(speaker_name: str):
    """音声削除"""
    if cosyvoice_client is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        success = await cosyvoice_client.delete_voice(speaker_name)
        if success:
            return {"status": "success", "message": f"Voice '{speaker_name}' deleted"}
        else:
            raise HTTPException(status_code=404, detail="Voice not found")
    except Exception as e:
        logger.error(f"Voice deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/audio/stream")
async def create_speech_stream(request: AudioSpeechRequest):
    """ストリーミング音声合成"""
    if cosyvoice_client is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    if not config.streaming_enabled:
        raise HTTPException(status_code=501, detail="Streaming not enabled")
    
    try:
        async def generate_audio():
            async for chunk in cosyvoice_client.synthesize_stream(
                text=request.input,
                voice=request.voice,
                model=request.model,
                response_format=request.response_format,
                speed=request.speed,
            ):
                yield chunk
        
        content_type_map = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "flac": "audio/flac",
            "aac": "audio/aac",
        }
        content_type = content_type_map.get(request.response_format, "audio/mpeg")
        
        return StreamingResponse(
            generate_audio(),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{request.response_format}"
            },
        )
        
    except Exception as e:
        logger.error(f"Streaming synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTPエラーハンドラー"""
    return Response(
        content=ErrorResponse(
            error={
                "message": exc.detail,
                "type": "invalid_request_error",
                "code": exc.status_code,
            }
        ).model_dump_json(),
        status_code=exc.status_code,
        media_type="application/json",
    )


if __name__ == "__main__":
    # サーバー起動
    uvicorn.run(
        "app:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        workers=1,  # CosyVoiceは単一プロセスで動作
        access_log=config.debug,
    )