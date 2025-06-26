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
            "input": "你好主人，我是念念，你的数字人小助手。今天也要一起加油哦！",
            "voice": "linzhiling",
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
