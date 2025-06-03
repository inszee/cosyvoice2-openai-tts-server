#!/bin/bash

# CosyVoice2 OpenAI TTS Server Setup Script

set -e

echo "🚀 Setting up CosyVoice2 OpenAI TTS Server..."

# 色付きログ関数
log_info() {
    echo -e "\033[0;32m[INFO]\033[0m $1"
}

log_warn() {
    echo -e "\033[0;33m[WARN]\033[0m $1"
}

log_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

# システム情報確認
log_info "System information:"
echo "OS: $(uname -s)"
echo "Architecture: $(uname -m)"
echo "Python: $(python --version 2>/dev/null || echo 'Not found')"
echo "CUDA: $(nvcc --version 2>/dev/null | grep 'release' || echo 'Not found')"
echo ""

# Git LFS確認・インストール
if ! command -v git-lfs &> /dev/null; then
    log_warn "Git LFS not found, installing..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y git-lfs
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install git-lfs
    else
        log_error "Please install Git LFS manually: https://git-lfs.github.io/"
        exit 1
    fi
fi

git lfs install

# ディレクトリ作成
log_info "Creating directories..."
mkdir -p pretrained_models
mkdir -p cache
mkdir -p logs

# CosyVoiceリポジトリクローン
if [ ! -d "CosyVoice" ]; then
    log_info "Cloning CosyVoice repository..."
    git clone https://github.com/FunAudioLLM/CosyVoice.git
else
    log_info "CosyVoice repository already exists, updating..."
    cd CosyVoice
    git pull
    cd ..
fi

# Pythonパス設定
export PYTHONPATH="$PWD/CosyVoice:$PWD/CosyVoice/third_party/Matcha-TTS:$PYTHONPATH"

# CosyVoice依存関係インストール
log_info "Installing CosyVoice dependencies..."
cd CosyVoice
pip install -r requirements.txt
cd ..

# アプリケーション依存関係インストール
log_info "Installing application dependencies..."
pip install -r requirements.txt

# モデルダウンロード
log_info "Downloading CosyVoice2 models..."
cat << 'EOF' > download_models.py
import os
from pathlib import Path
from modelscope import snapshot_download

def download_models():
    try:
        # CosyVoice2-0.5B (推奨)
        print("Downloading CosyVoice2-0.5B...")
        snapshot_download(
            'iic/CosyVoice2-0.5B',
            local_dir='./pretrained_models/CosyVoice2-0.5B'
        )
        print("✅ CosyVoice2-0.5B downloaded")
        
        # CosyVoice-300M-SFT (バックアップ)
        print("Downloading CosyVoice-300M-SFT...")
        snapshot_download(
            'iic/CosyVoice-300M-SFT',
            local_dir='./pretrained_models/CosyVoice-300M-SFT'
        )
        print("✅ CosyVoice-300M-SFT downloaded")
        
        # CosyVoice-ttsfrd (中国語正規化用)
        print("Downloading CosyVoice-ttsfrd...")
        snapshot_download(
            'iic/CosyVoice-ttsfrd',
            local_dir='./pretrained_models/CosyVoice-ttsfrd'
        )
        print("✅ CosyVoice-ttsfrd downloaded")
        
        # TTSFRDリソース解凍
        ttsfrd_path = Path('./pretrained_models/CosyVoice-ttsfrd')
        if (ttsfrd_path / 'resource.zip').exists():
            print("Extracting TTSFRD resources...")
            import zipfile
            with zipfile.ZipFile(ttsfrd_path / 'resource.zip', 'r') as zip_ref:
                zip_ref.extractall(ttsfrd_path)
            print("✅ TTSFRD resources extracted")
        
        print("\n🎉 All models downloaded successfully!")
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print("You can try downloading manually later.")

if __name__ == "__main__":
    download_models()
EOF

python download_models.py
rm download_models.py

# 環境設定ファイル作成
if [ ! -f ".env" ]; then
    log_info "Creating environment configuration..."
    cat << 'EOF' > .env
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# CosyVoice Configuration
MODEL_PATH=./pretrained_models/CosyVoice2-0.5B
DEVICE=auto
FP16=true
STREAMING=true

# Performance Settings
MAX_TEXT_LENGTH=1000
CACHE_SIZE=100
CONCURRENT_REQUESTS=4

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/cosyvoice.log

# Optional: Authentication
# API_KEY=your-api-key-here
# ENABLE_AUTH=false
EOF
    log_info "Environment configuration created at .env"
else
    log_info ".env file already exists"
fi

# 起動スクリプト作成
log_info "Creating startup script..."
cat << 'EOF' > start_server.sh
#!/bin/bash

# CosyVoice2 TTS Server Startup Script

export PYTHONPATH="$PWD/CosyVoice:$PWD/CosyVoice/third_party/Matcha-TTS:$PYTHONPATH"

echo "🚀 Starting CosyVoice2 OpenAI TTS Server..."
echo "Server will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python app.py
EOF

chmod +x start_server.sh

# テストスクリプト作成
log_info "Creating test script..."
cat << 'EOF' > test_server.py
#!/usr/bin/env python3
"""
CosyVoice2 TTS Server Test Script
"""

import requests
import json
import time

def test_server():
    base_url = "http://localhost:8000"
    
    print("🧪 Testing CosyVoice2 TTS Server...")
    
    # Health check
    print("\n1. Health Check")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Server is healthy")
            print(f"   Status: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return
    
    # List models
    print("\n2. List Models")
    try:
        response = requests.get(f"{base_url}/v1/models")
        if response.status_code == 200:
            models = response.json()
            print("✅ Models listed successfully")
            print(f"   Available models: {[m['id'] for m in models['data']]}")
        else:
            print(f"❌ Failed to list models: {response.status_code}")
    except Exception as e:
        print(f"❌ Error listing models: {e}")
    
    # List voices
    print("\n3. List Voices")
    try:
        response = requests.get(f"{base_url}/v1/voices")
        if response.status_code == 200:
            voices = response.json()
            print("✅ Voices listed successfully")
            print(f"   Available voices: {[v['id'] for v in voices['voices']]}")
        else:
            print(f"❌ Failed to list voices: {response.status_code}")
    except Exception as e:
        print(f"❌ Error listing voices: {e}")
    
    # Speech synthesis test
    print("\n4. Speech Synthesis Test")
    try:
        data = {
            "model": "cosyvoice2-0.5b",
            "input": "Hello from CosyVoice2! This is a test.",
            "voice": "alloy",
            "response_format": "wav",
            "speed": 1.0
        }
        
        print("   Synthesizing speech...")
        start_time = time.time()
        response = requests.post(
            f"{base_url}/v1/audio/speech",
            json=data,
            timeout=30
        )
        synthesis_time = time.time() - start_time
        
        if response.status_code == 200:
            audio_size = len(response.content)
            print(f"✅ Speech synthesis successful")
            print(f"   Audio size: {audio_size} bytes")
            print(f"   Synthesis time: {synthesis_time:.2f}s")
            
            # Save test audio
            with open("test_output.wav", "wb") as f:
                f.write(response.content)
            print("   Test audio saved as: test_output.wav")
        else:
            print(f"❌ Speech synthesis failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Error during synthesis: {e}")
    
    print("\n🎉 Server testing completed!")

if __name__ == "__main__":
    test_server()
EOF

chmod +x test_server.py

# セットアップ完了
log_info "Setup completed successfully! 🎉"
echo ""
echo "📋 Next Steps:"
echo "  1. Start the server:    ./start_server.sh"
echo "  2. Test the server:     python test_server.py"
echo "  3. View API docs:       http://localhost:8000/docs"
echo "  4. Health check:        http://localhost:8000/health"
echo ""
echo "🔧 Configuration:"
echo "  - Edit .env file for custom settings"
echo "  - Models location: ./pretrained_models/"
echo "  - Cache location: ./cache/"
echo "  - Logs location: ./logs/"
echo ""
echo "🐳 Docker (alternative):"
echo "  - Build image:          docker-compose build"
echo "  - Start service:        docker-compose up -d"
echo "  - View logs:            docker-compose logs -f"
echo ""
echo "📚 Documentation: https://github.com/ShunsukeTamura06/cosyvoice2-openai-tts-server"