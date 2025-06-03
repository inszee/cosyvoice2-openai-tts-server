# 使用ガイド & デモンストレーション

## 🚀 クイックスタート

### 1. 環境準備

```bash
# リポジトリクローン
git clone https://github.com/ShunsukeTamura06/cosyvoice2-openai-tts-server.git
cd cosyvoice2-openai-tts-server

# Conda環境作成（推奨）
conda create -n cosyvoice python=3.10
conda activate cosyvoice

# セットアップ実行
bash setup.sh
```

### 2. サーバー起動

```bash
# 手動起動
python app.py

# または起動スクリプト使用
./start_server.sh
```

### 3. 動作確認

```bash
# テストスクリプト実行
python test_server.py
```

## 🎯 API使用例

### OpenAI SDKを使用した基本的な音声合成

```python
from openai import OpenAI

# クライアント初期化
client = OpenAI(
    api_key="dummy-key",  # 認証なし
    base_url="http://localhost:8000/v1"
)

# 日本語音声合成
response = client.audio.speech.create(
    model="cosyvoice2-0.5b",
    voice="nova",  # 日本語女性音声
    input="こんにちは、CosyVoice2です。今日の天気はいかがですか？",
    response_format="mp3",
    speed=1.0
)

# 音声ファイル保存
with open("japanese_output.mp3", "wb") as f:
    f.write(response.content)

print("✅ 日本語音声ファイルが生成されました: japanese_output.mp3")
```

### 多言語対応テスト

```python
# 複数言語のテスト
test_cases = [
    {"voice": "alloy", "text": "你好，这是中文语音合成测试。", "lang": "中文"},
    {"voice": "fable", "text": "Hello, this is English TTS test.", "lang": "English"},
    {"voice": "nova", "text": "こんにちは、日本語音声合成のテストです。", "lang": "日本語"},
    {"voice": "shimmer", "text": "안녕하세요, 한국어 음성 합성 테스트입니다.", "lang": "한국어"},
]

for i, test in enumerate(test_cases):
    response = client.audio.speech.create(
        model="cosyvoice2-0.5b",
        voice=test["voice"],
        input=test["text"],
        response_format="wav"
    )
    
    filename = f"multilang_test_{i+1}_{test['lang']}.wav"
    with open(filename, "wb") as f:
        f.write(response.content)
    
    print(f"✅ {test['lang']}音声ファイル生成: {filename}")
```

### cURLを使用したAPI呼び出し

```bash
# 基本的な音声合成
curl -X POST "http://localhost:8000/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cosyvoice2-0.5b",
    "input": "Hello from CosyVoice2! This is a test of the TTS system.",
    "voice": "alloy",
    "response_format": "mp3",
    "speed": 1.0
  }' \
  --output test_speech.mp3

# 速度調整テスト
curl -X POST "http://localhost:8000/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cosyvoice2-0.5b",
    "input": "This is a fast speech test.",
    "voice": "echo",
    "response_format": "wav",
    "speed": 1.5
  }' \
  --output fast_speech.wav
```

## 🎭 音声クローニング

### カスタム音声の追加

```python
import requests

# 音声サンプルをアップロード
with open("sample_voice.wav", "rb") as f:
    files = {"voice_sample": f}
    data = {
        "speaker_name": "my_custom_voice",
        "description": "私のカスタム音声サンプル"
    }
    
    response = requests.post(
        "http://localhost:8000/v1/voice/clone",
        files=files,
        data=data
    )
    
    print(f"クローン結果: {response.json()}")

# クローンした音声で合成
response = client.audio.speech.create(
    model="cosyvoice2-0.5b",
    voice="my_custom_voice",  # 追加したカスタム音声
    input="クローンされた音声で話しています。",
    response_format="mp3"
)

with open("cloned_voice_output.mp3", "wb") as f:
    f.write(response.content)
```

### 音声一覧の確認

```python
# 利用可能な音声一覧を取得
response = requests.get("http://localhost:8000/v1/voices")
voices = response.json()

print("利用可能な音声:")
for voice in voices["voices"]:
    print(f"  - {voice['id']}: {voice['name']} ({voice['type']})")
```

## 🔗 Dify統合設定

### Difyでの設定手順

1. **Dify管理画面にアクセス**
2. **設定 → モデルプロバイダー → OpenAI-API-compatible** を選択
3. **以下の設定を入力:**

```
Base URL: http://localhost:8000/v1
API Key: dummy-key
Model Type: TTS
Model Name: cosyvoice2-0.5b
```

4. **テスト接続実行**
5. **保存**

### Dify APIから使用

```python
import requests

# Dify経由でTTS使用
dify_api_key = "your-dify-api-key"
dify_endpoint = "https://api.dify.ai/v1"

response = requests.post(
    f"{dify_endpoint}/audio/speech",
    headers={
        "Authorization": f"Bearer {dify_api_key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "cosyvoice2-0.5b",
        "input": "Dify経由で音声合成しています。",
        "voice": "alloy"
    }
)

with open("dify_tts_output.mp3", "wb") as f:
    f.write(response.content)
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. メモリ不足エラー

```bash
# GPU メモリが不足している場合
export CUDA_VISIBLE_DEVICES=""  # CPU強制使用
export FP16=false               # FP16無効化

# または .env ファイルで設定
echo "DEVICE=cpu" >> .env
echo "FP16=false" >> .env
```

#### 2. モデルダウンロード失敗

```python
# 手動でモデルダウンロード
from modelscope import snapshot_download

# CosyVoice2-0.5B
snapshot_download(
    'iic/CosyVoice2-0.5B',
    local_dir='./pretrained_models/CosyVoice2-0.5B'
)

# TTSFRD（中国語処理用）
snapshot_download(
    'iic/CosyVoice-ttsfrd',
    local_dir='./pretrained_models/CosyVoice-ttsfrd'
)
```

#### 3. 中国語音声の問題

```bash
# TTSFRDパッケージのインストール
cd pretrained_models/CosyVoice-ttsfrd/
unzip resource.zip -d .
pip install ttsfrd_dependency-0.1-py3-none-any.whl
pip install ttsfrd-0.4.2-cp310-cp310-linux_x86_64.whl
```

#### 4. ポート衝突

```bash
# 別のポートを使用
export PORT=8001
python app.py

# または .env ファイルで設定
echo "PORT=8001" >> .env
```

## 📊 パフォーマンステスト

### ベンチマークスクリプト

```python
import time
import statistics
from openai import OpenAI

client = OpenAI(
    api_key="dummy-key",
    base_url="http://localhost:8000/v1"
)

def benchmark_synthesis(text, iterations=5):
    """音声合成のベンチマークテスト"""
    times = []
    
    for i in range(iterations):
        start_time = time.time()
        
        response = client.audio.speech.create(
            model="cosyvoice2-0.5b",
            voice="alloy",
            input=text,
            response_format="wav"
        )
        
        end_time = time.time()
        synthesis_time = end_time - start_time
        times.append(synthesis_time)
        
        print(f"テスト {i+1}: {synthesis_time:.2f}秒")
    
    avg_time = statistics.mean(times)
    print(f"\n平均合成時間: {avg_time:.2f}秒")
    print(f"最小時間: {min(times):.2f}秒")
    print(f"最大時間: {max(times):.2f}秒")

# ベンチマーク実行
test_text = "This is a performance benchmark test for CosyVoice2 TTS server."
benchmark_synthesis(test_text)
```

## 🐳 Docker使用

### Docker Composeでの起動

```bash
# サービス起動
docker-compose up -d

# ログ確認
docker-compose logs -f cosyvoice-tts

# サービス停止
docker-compose down
```

### 個別Dockerコンテナでの実行

```bash
# イメージビルド
docker build -t cosyvoice-tts .

# コンテナ実行
docker run -d \
  --name cosyvoice-server \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/pretrained_models:/app/pretrained_models \
  -v $(pwd)/cache:/app/cache \
  cosyvoice-tts

# ヘルスチェック
curl http://localhost:8000/health
```

## 📝 ログ分析

### ログファイルの確認

```bash
# リアルタイムログ監視
tail -f logs/cosyvoice.log

# エラーログのみ表示
grep "ERROR" logs/cosyvoice.log

# 合成統計の表示
grep "synthesis" logs/cosyvoice.log | tail -10
```

## 🎯 実運用における推奨設定

### 本番環境用設定

```bash
# .env.production
HOST=0.0.0.0
PORT=8000
DEBUG=false
DEVICE=cuda
FP16=true
STREAMING=true
MAX_TEXT_LENGTH=500
CONCURRENT_REQUESTS=2
ENABLE_CACHING=true
LOG_LEVEL=WARNING
ENABLE_AUTH=true
API_KEY=your-secure-api-key
```

### リバースプロキシ設定（nginx）

```nginx
server {
    listen 80;
    server_name your-tts-server.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # タイムアウト設定
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

これでCosyVoice2 OpenAI互換TTSサーバーの完全なセットアップが完了です！🎉