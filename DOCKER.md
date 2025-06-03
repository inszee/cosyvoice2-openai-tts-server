# Docker 使用ガイド

CosyVoice2 TTS サーバーをDockerで実行するための詳細ガイドです。

## 🚀 クイックスタート

### 1. GPU版（推奨）

```bash
# リポジトリクローン
git clone https://github.com/ShunsukeTamura06/cosyvoice2-openai-tts-server.git
cd cosyvoice2-openai-tts-server

# GPU版で起動
docker-compose --profile gpu up -d

# ログ確認
docker-compose logs -f cosyvoice-tts-gpu
```

### 2. CPU版（GPU不要）

```bash
# CPU版で起動
docker-compose --profile cpu up -d

# ログ確認
docker-compose logs -f cosyvoice-tts-cpu
```

## 📋 利用可能なプロファイル

| プロファイル | 用途 | 性能 | 要件 |
|------------|------|------|------|
| `gpu` | 本番運用 | 最高 | NVIDIA GPU + Docker |
| `cpu` | GPU不要環境 | 中程度 | CPU 4コア以上 |
| `dev` | 開発用 | 低め | 開発/テスト用 |

## 🔧 詳細な使用方法

### プロファイル別起動

```bash
# GPU版（本番推奨）
docker-compose --profile gpu up -d

# CPU版（GPUなし環境）
docker-compose --profile cpu up -d

# 開発版（デバッグ用）
docker-compose --profile dev up -d
```

### 個別サービス制御

```bash
# サービス起動
docker-compose up cosyvoice-tts-gpu -d

# サービス停止
docker-compose stop cosyvoice-tts-gpu

# サービス再起動
docker-compose restart cosyvoice-tts-gpu

# ログ確認
docker-compose logs -f cosyvoice-tts-gpu
```

## 🐳 手動Docker実行

### GPU版

```bash
# イメージビルド
docker build -f Dockerfile -t cosyvoice-tts:gpu .

# コンテナ実行
docker run -d \
  --name cosyvoice-gpu \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/pretrained_models:/app/pretrained_models \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/logs:/app/logs \
  -e DEVICE=cuda \
  -e FP16=true \
  cosyvoice-tts:gpu
```

### CPU版

```bash
# イメージビルド
docker build -f Dockerfile.cpu -t cosyvoice-tts:cpu .

# コンテナ実行
docker run -d \
  --name cosyvoice-cpu \
  -p 8000:8000 \
  -v $(pwd)/pretrained_models:/app/pretrained_models \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/logs:/app/logs \
  -e DEVICE=cpu \
  -e FP16=false \
  cosyvoice-tts:cpu
```

## ⚙️ 環境変数設定

### 基本設定

```bash
# .env ファイル作成
cat << EOF > .env
# サーバー設定
HOST=0.0.0.0
PORT=8000
DEBUG=false

# デバイス設定
DEVICE=auto  # auto, cpu, cuda
FP16=true

# パフォーマンス設定
MAX_TEXT_LENGTH=1000
CONCURRENT_REQUESTS=4
STREAMING=true

# ログ設定
LOG_LEVEL=INFO
EOF

# 環境変数ファイルを使用して起動
docker-compose --env-file .env --profile gpu up -d
```

### カスタム設定例

```bash
# 高負荷環境用
docker run -d \
  --name cosyvoice-production \
  --gpus all \
  -p 8000:8000 \
  -e DEVICE=cuda \
  -e FP16=true \
  -e CONCURRENT_REQUESTS=8 \
  -e MAX_TEXT_LENGTH=2000 \
  -e STREAMING=true \
  -e CACHE_SIZE=200 \
  cosyvoice-tts:gpu

# 開発用（低リソース）
docker run -d \
  --name cosyvoice-dev \
  -p 8001:8000 \
  -e DEVICE=cpu \
  -e DEBUG=true \
  -e CONCURRENT_REQUESTS=1 \
  -e MAX_TEXT_LENGTH=200 \
  -e LOG_LEVEL=DEBUG \
  cosyvoice-tts:cpu
```

## 📊 モニタリング

### ログ確認

```bash
# リアルタイムログ
docker-compose logs -f cosyvoice-tts-gpu

# エラーログのみ
docker-compose logs cosyvoice-tts-gpu | grep ERROR

# 最新100行
docker-compose logs --tail 100 cosyvoice-tts-gpu
```

### コンテナ状態確認

```bash
# ヘルスチェック
curl http://localhost:8000/health

# コンテナ状態
docker-compose ps

# リソース使用量
docker stats cosyvoice-tts-server-gpu
```

### メトリクス取得

```bash
# API呼び出し統計
curl http://localhost:8000/v1/models

# 音声一覧
curl http://localhost:8000/v1/voices
```

## 🔧 トラブルシューティング

### よくある問題

#### 1. NVIDIA Docker エラー

```bash
# Error: nvidia/cuda image not found
# 解決: CPU版を使用
docker-compose --profile cpu up -d
```

#### 2. メモリ不足

```bash
# GPU メモリ不足
docker run ... -e DEVICE=cpu ...

# システムメモリ不足
docker run ... -e CONCURRENT_REQUESTS=1 -e MAX_TEXT_LENGTH=200 ...
```

#### 3. ポート衝突

```bash
# 別ポート使用
docker run -p 8001:8000 ...

# または docker-compose.yml を編集
sed -i 's/8000:8000/8001:8000/' docker-compose.yml
```

#### 4. モデルダウンロード失敗

```bash
# コンテナ内でダウンロード
docker exec -it cosyvoice-tts-server-cpu python -c "
from modelscope import snapshot_download
snapshot_download('iic/CosyVoice2-0.5B', local_dir='/app/pretrained_models/CosyVoice2-0.5B')
"
```

### デバッグモード

```bash
# デバッグ用起動
docker-compose --profile dev up

# コンテナ内アクセス
docker exec -it cosyvoice-tts-dev bash

# ログレベル変更
docker exec -it cosyvoice-tts-dev \
  python -c "import logging; logging.getLogger().setLevel(logging.DEBUG)"
```

## 🚀 本番環境デプロイ

### Nginx リバースプロキシ

```nginx
# /etc/nginx/sites-available/cosyvoice-tts
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # タイムアウト設定（音声合成用）
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### SSL証明書設定

```bash
# Let's Encrypt
sudo certbot --nginx -d your-domain.com

# 自動更新
sudo crontab -e
# 追加: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Docker Swarm デプロイ

```yaml
# docker-stack.yml
version: '3.8'
services:
  cosyvoice-tts:
    image: cosyvoice-tts:gpu
    ports:
      - "8000:8000"
    environment:
      - DEVICE=cuda
      - CONCURRENT_REQUESTS=4
    deploy:
      replicas: 2
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - models:/app/pretrained_models
      - cache:/app/cache

volumes:
  models:
  cache:
```

```bash
# スタックデプロイ
docker stack deploy -c docker-stack.yml cosyvoice
```

## 📈 スケーリング

### 水平スケーリング

```bash
# レプリカ数増加
docker-compose up --scale cosyvoice-tts-gpu=3

# ロードバランサー設定
# HAProxy または Nginx upstream 設定
```

### 垂直スケーリング

```bash
# リソース制限設定
docker run \
  --memory=8g \
  --cpus=4 \
  --gpus=1 \
  cosyvoice-tts:gpu
```

これでDockerを使った完全なデプロイが可能になります！ 🐳✨