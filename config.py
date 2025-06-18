#!/usr/bin/env python3
"""
Configuration Settings

設定管理クラス
"""

import os
from pathlib import Path
from typing import Optional

try:
    # Pydantic v2
    from pydantic import BaseSettings, Field
except ImportError:
    # Pydantic v1 fallback
    from pydantic import BaseModel, Field
    
    class BaseSettings(BaseModel):
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"


class Config(BaseSettings):
    """アプリケーション設定"""
    
    # サーバー設定
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # CosyVoice設定
    model_path: str = Field(
        default="./pretrained_models/CosyVoice2-0.5B",
        env="MODEL_PATH"
    )
    default_spk_voice_path: str = Field(
        default="./voices",
        env="DEFAULT_SPK_VOICES_PATH"
    )
    
    device: str = Field(default="auto", env="DEVICE")  # auto, cpu, cuda
    fp16: bool = Field(default=True, env="FP16")
    streaming_enabled: bool = Field(default=True, env="STREAMING")
    
    # 制限設定
    max_text_length: int = Field(default=1000, env="MAX_TEXT_LENGTH")
    cache_size: int = Field(default=100, env="CACHE_SIZE")
    concurrent_requests: int = Field(default=4, env="CONCURRENT_REQUESTS")
    
    # ログ設定
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # 認証設定（将来拡張用）
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    enable_auth: bool = Field(default=False, env="ENABLE_AUTH")
    
    # パフォーマンス設定
    enable_caching: bool = Field(default=True, env="ENABLE_CACHING")
    cache_dir: str = Field(default="./cache", env="CACHE_DIR")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._post_init()
    
    def _post_init(self):
        """初期化後処理"""
        # デバイス設定の自動判定
        if self.device == "auto":
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
        
        # ディレクトリ作成
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        if self.enable_caching:
            Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        
        # ログレベル設定
        import logging
        logging.getLogger().setLevel(getattr(logging, self.log_level.upper()))
    
    @property
    def is_gpu_enabled(self) -> bool:
        """GPU使用可能かどうか"""
        return self.device == "cuda"
    
    @property
    def model_config_path(self) -> str:
        """モデル設定ファイルパス"""
        return os.path.join(self.model_path, "cosyvoice2.yaml")
    
    @property
    def model_weights_path(self) -> str:
        """モデル重みファイルパス"""
        return os.path.join(self.model_path, "cosyvoice.pt")
    
    def get_cache_path(self, key: str) -> str:
        """キャッシュファイルパス取得"""
        return os.path.join(self.cache_dir, f"{key}.cache")
    
    def validate_model_path(self) -> bool:
        """モデルパス有効性確認"""
        model_path = Path(self.model_path)
        return model_path.exists() and model_path.is_dir()