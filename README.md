# CosyVoice2 OpenAI Compatible TTS Server

Dify用のCosyVoice2を使用したOpenAI API互換のTTSサーバーです。

## 🚀 機能

- **OpenAI TTS API完全互換** (`/v1/audio/speech`)
- **CosyVoice2-0.5Bモデル使用**（最高のストリーミング性能）
- **多言語対応**（中国語、英語、日本語、韓国語、方言）
- **Zero-shot音声クローニング**
- **ストリーミング対応**（低遅延150ms）
- **Docker対応**（CPU/GPU両対応）
- **Dify直接統合可能**

## 📦 クイックスタート

### 🐳 Docker使用（推奨）

#### GPU版（推奨）
```bash
git clone https://github.com/ShunsukeTamura06/cosyvoice2-openai-tts-server.git
cd cosyvoice2-openai-tts-server

# GPU版で起動
docker-compose --profile gpu up -d

# ログ確認
docker-compose logs -f cosyvoice-tts-gpu
```

#### CPU版（GPUが利用できない場合）
```bash
# CPU版で起動
docker-compose --profile cpu up -d

# ログ確認
docker-compose logs -f cosyvoice-tts-cpu
```

#### 🔧 手動セットアップ

1. **環境構築**

```bash
# Conda環境作成
conda create -n cosyvoice python=3.10
conda activate cosyvoice

# リポジトリクローン
git clone https://github.com/ShunsukeTamura06/cosyvoice2-openai-tts-server.git
cd cosyvoice2-openai-tts-server

# セットアップスクリプト実行
bash setup.sh
```

2. **サーバー起動**

```bash
# 自動起動スクリプト
./start_server.sh

# または手動起動
python app.py
```

3. **動作確認**

```bash
# テストスクリプト実行
python test_server.py
```

## 🔧 API使用例

### OpenAI SDK使用

```python
from openai import OpenAI

client = OpenAI(
    api_key="dummy-key",  # 認証なし
    base_url="http://localhost:8000/v1"
)

response = client.audio.speech.create(
    model="cosyvoice2-0.5b",
    voice="alloy",  # または "echo", "fable", "onyx", "nova", "shimmer"
    input="こんにちは、CosyVoice2です。",
    response_format="mp3",
    speed=1.0
)

with open("output.mp3", "wb") as f:
    f.write(response.content)
```

### cURL使用

```bash
curl -X POST "http://localhost:8000/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cosyvoice2-0.5b",
    "input": "Hello from CosyVoice2!",
    "voice": "alloy",
    "response_format": "mp3",
    "speed": 1.0
  }' \
  --output speech.mp3
```

## 🎭 音声クローニング

音声サンプルを使用したクローニング:

```python
# 音声サンプルをアップロード
with open("sample_voice.wav", "rb") as f:
    files = {"voice_sample": f}
    data = {"speaker_name": "my_voice"}
    response = requests.post(
        "http://localhost:8000/v1/voice/clone",
        files=files,
        data=data
    )

# クローンした音声で合成
response = client.audio.speech.create(
    model="cosyvoice2-0.5b",
    voice="my_voice",  # 登録したスピーカー名
    input="クローンされた音声です。",
    response_format="mp3"
)
```

## 🔗 Dify統合

1. Difyの「モデルプロバイダー」→「OpenAI-API-compatible」を選択
2. 以下の設定を入力:
   - **API Base URL**: `http://localhost:8000/v1`
   - **API Key**: `dummy-key` (任意の値)
   - **Model Type**: `TTS`
   - **Model Name**: `cosyvoice2-0.5b`

## 🐳 Docker使用方法

### プロファイル使用

```bash
# GPU版（最高性能）
docker-compose --profile gpu up -d

# CPU版（GPUなし環境）
docker-compose --profile cpu up -d

# 開発版（デバッグ用）
docker-compose --profile dev up -d
```

### 個別ビルド

```bash
# GPU版
docker build -f Dockerfile -t cosyvoice-tts:gpu .
docker run -d --gpus all -p 8000:8000 cosyvoice-tts:gpu

# CPU版
docker build -f Dockerfile.cpu -t cosyvoice-tts:cpu .
docker run -d -p 8000:8000 cosyvoice-tts:cpu
```

## 📊 対応音声形式

- **入力**: テキスト（任意の言語）
- **出力**: MP3, WAV, FLAC, AAC
- **音声**: 内蔵音声 + カスタム音声クローニング

## ⚡ パフォーマンス

| 項目 | GPU版 | CPU版 |
|------|-------|-------|
| 初回応答遅延 | 150ms | 2-5秒 |
| リアルタイム係数 | <1.0 | 3-10 |
| 推奨メモリ | 4GB | 8GB |
| ストリーミング | ✅ | ❌ |

## ⚙️ 環境変数

`.env` ファイルで設定可能:

```bash
# サーバー設定
HOST=0.0.0.0
PORT=8000
DEBUG=false

# CosyVoice設定
MODEL_PATH=./pretrained_models/CosyVoice2-0.5B
DEVICE=auto  # auto, cpu, cuda
FP16=true
STREAMING=true

# 詳細設定
MAX_TEXT_LENGTH=1000
CACHE_SIZE=100
CONCURRENT_REQUESTS=4
```

## 🔧 トラブルシューティング

### Dockerエラー

#### "nvidia/cuda image not found"
```bash
# CPU版を使用
docker-compose --profile cpu up -d
```

#### メモリ不足
```bash
# 軽量設定で起動
export MAX_TEXT_LENGTH=200
export CONCURRENT_REQUESTS=1
docker-compose --profile cpu up -d
```

### 手動セットアップエラー

#### GPU メモリ不足
```bash
export CUDA_VISIBLE_DEVICES=""  # CPU強制使用
export FP16=false
```

#### モデルダウンロード失敗
```bash
# 手動ダウンロード
python -c "
from modelscope import snapshot_download
snapshot_download('iic/CosyVoice2-0.5B', local_dir='./pretrained_models/CosyVoice2-0.5B')
"
```

#### 中国語音声合成問題
```bash
# TTSFRD リソース インストール
cd pretrained_models/CosyVoice-ttsfrd/
unzip resource.zip -d .
pip install ttsfrd_dependency-0.1-py3-none-any.whl
pip install ttsfrd-0.4.2-cp310-cp310-linux_x86_64.whl
```

## 📚 詳細ドキュメント

- [使用ガイド & デモ](USAGE.md)
- [Docker各種選択肢](#-docker使用方法)
- [API仕様](http://localhost:8000/docs) (サーバー起動後)

## 📄 ライセンス

MIT License

## 🤝 貢献

Pull Requestsや Issue報告を歓迎します。

## 📞 サポート

問題や質問がある場合は、GitHubのIssuesまでお願いします。