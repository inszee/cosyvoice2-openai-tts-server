#!/bin/bash

# CosyVoice2 TTS Server Startup Script

export PYTHONPATH="$PWD/CosyVoice:$PWD/CosyVoice/third_party/Matcha-TTS:$PYTHONPATH"
export PYTHONIOENCODING=utf-8

echo "🚀 Starting CosyVoice2 OpenAI TTS Server..."
echo "Server will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python app.py
