#!/usr/bin/env python3
"""
Pydantic Models

API リクエスト/レスポンス モデル定義
"""

from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class AudioSpeechRequest(BaseModel):
    """音声合成リクエスト (OpenAI互換)"""
    model: str = Field(default="cosyvoice2-0.5b", description="使用するモデル")
    input: str = Field(..., description="合成するテキスト")
    voice: str = Field(
        default="alloy",
        description="音声の種類 (alloy, echo, fable, onyx, nova, shimmer)"
    )
    response_format: Literal["mp3", "wav", "flac", "aac"] = Field(
        default="mp3", description="音声フォーマット"
    )
    speed: float = Field(
        default=1.0, ge=0.25, le=4.0, description="再生速度 (0.25-4.0)"
    )


class AudioSpeechResponse(BaseModel):
    """音声合成レスポンス"""
    audio_data: bytes = Field(..., description="音声データ")
    content_type: str = Field(..., description="コンテンツタイプ")
    duration: Optional[float] = Field(None, description="音声長さ（秒）")


class ModelObject(BaseModel):
    """モデル情報"""
    id: str
    object: str = "model"
    created: int
    owned_by: str


class ModelListResponse(BaseModel):
    """モデル一覧レスポンス"""
    object: str = "list"
    data: List[ModelObject]


class VoiceInfo(BaseModel):
    """音声情報"""
    id: str = Field(..., description="音声ID")
    name: str = Field(..., description="音声名")
    speaker: str = Field(..., description="スピーカー名")
    language: str = Field(..., description="言語コード")
    type: Literal["preset", "custom"] = Field(..., description="音声タイプ")
    description: Optional[str] = Field(None, description="説明")


class VoiceListResponse(BaseModel):
    """音声一覧レスポンス"""
    voices: List[VoiceInfo]


class VoiceCloneRequest(BaseModel):
    """音声クローニングリクエスト"""
    speaker_name: str = Field(..., description="スピーカー名")
    description: Optional[str] = Field(None, description="説明")


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str = Field(..., description="サービス状態")
    model_loaded: bool = Field(..., description="モデル読み込み状態")
    gpu_available: bool = Field(..., description="GPU使用可能性")
    version: str = Field(..., description="バージョン")


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    error: Dict[str, Union[str, int]] = Field(..., description="エラー情報")


class StreamingChunk(BaseModel):
    """ストリーミングチャンク"""
    chunk_id: int = Field(..., description="チャンクID")
    audio_data: bytes = Field(..., description="音声データ")
    is_final: bool = Field(..., description="最終チャンクかどうか")


class SynthesisStats(BaseModel):
    """合成統計情報"""
    text_length: int = Field(..., description="テキスト長")
    audio_duration: float = Field(..., description="音声長さ（秒）")
    synthesis_time: float = Field(..., description="合成時間（秒）")
    real_time_factor: float = Field(..., description="リアルタイム係数")
    model_used: str = Field(..., description="使用モデル")
    voice_used: str = Field(..., description="使用音声")