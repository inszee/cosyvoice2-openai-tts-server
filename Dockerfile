# CosyVoice2 OpenAI TTS Server Dockerfile (CPU/GPU両対応)
# GPU使用の場合: docker build -f Dockerfile -t cosyvoice-tts .
# CPU使用の場合: docker build -f Dockerfile.cpu -t cosyvoice-tts .

ARG BASE_IMAGE=ubuntu:22.04
FROM ${BASE_IMAGE}

# 環境変数設定
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# CUDAが利用可能な場合の環境変数（GPU版のみ）
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=$CUDA_HOME/bin:$PATH
ENV LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# システムパッケージインストール
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    git-lfs \
    wget \
    curl \
    sox \
    libsox-dev \
    ffmpeg \
    build-essential \
    cmake \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Python環境設定
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# 作業ディレクトリ作成
WORKDIR /app

# Miniconda インストール
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh && \
    bash miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh
ENV PATH=/opt/conda/bin:$PATH

# Conda環境作成
RUN conda create -n cosyvoice python=3.10 -y
ENV PATH=/opt/conda/envs/cosyvoice/bin:$PATH

# Git LFS初期化
RUN git lfs install

# Pynini インストール（Conda経由）
RUN /opt/conda/envs/cosyvoice/bin/conda install -c conda-forge pynini=2.1.5 -y

# CosyVoiceリポジトリクローン
RUN git clone https://github.com/FunAudioLLM/CosyVoice.git
WORKDIR /app/CosyVoice

# CosyVoice依存関係インストール
RUN /opt/conda/envs/cosyvoice/bin/pip install -r requirements.txt

# アプリケーションファイルコピー
WORKDIR /app
COPY requirements.txt .

# アプリケーション依存関係インストール
RUN /opt/conda/envs/cosyvoice/bin/pip install -r requirements.txt

# アプリケーションファイルコピー
COPY . .

# モデル用ディレクトリ作成
RUN mkdir -p pretrained_models cache logs

# 権限設定
RUN chmod +x setup.sh || true

# ポート公開
EXPOSE 8000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# エントリーポイント
CMD ["/opt/conda/envs/cosyvoice/bin/python", "app.py"]