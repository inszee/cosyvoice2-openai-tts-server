# CosyVoice2 OpenAI TTS Server Dockerfile
FROM nvidia/cuda:11.8-devel-ubuntu22.04

# 環境変数設定
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
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
    && rm -rf /var/lib/apt/lists/*

# Python環境設定
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# 作業ディレクトリ作成
WORKDIR /app

# Conda インストール
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh && \
    bash miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh
ENV PATH=/opt/conda/bin:$PATH

# Conda環境作成
RUN conda create -n cosyvoice python=3.10 -y
RUN echo "source activate cosyvoice" > ~/.bashrc
ENV PATH=/opt/conda/envs/cosyvoice/bin:$PATH

# Pynini インストール（Conda経由）
RUN conda install -c conda-forge pynini=2.1.5 -y

# CosyVoiceリポジトリクローン
RUN git clone https://github.com/FunAudioLLM/CosyVoice.git
WORKDIR /app/CosyVoice

# CosyVoice依存関係インストール
RUN pip install -r requirements.txt

# アプリケーションファイルコピー
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# モデル用ディレクトリ作成
RUN mkdir -p pretrained_models

# 権限設定
RUN chmod +x setup.sh

# ポート公開
EXPOSE 8000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# エントリーポイント
CMD ["python", "app.py"]