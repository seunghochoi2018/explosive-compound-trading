#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 모델 로드 상태 확인"""
import requests
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("LLM 모델 상태 확인")
print("=" * 60)
print()

ports = {
    11434: "ETH (코드3)",
    11435: "KIS (코드4)",
    11436: "Self-Improvement"
}

for port, desc in ports.items():
    print(f"[포트 {port}] {desc}")
    try:
        # 설치된 모델 목록
        response = requests.get(f"http://127.0.0.1:{port}/api/tags", timeout=3)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            print(f"  설치된 모델 수: {len(models)}")
            for model in models:
                name = model.get('name', 'Unknown')
                size = model.get('size', 0) / (1024**3)  # GB
                print(f"    - {name} ({size:.1f} GB)")
        else:
            print(f"  오류: HTTP {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"  연결 실패: Ollama가 실행되지 않음")
    except Exception as e:
        print(f"  오류: {e}")
    print()

print("=" * 60)
