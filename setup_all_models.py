#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모든 Ollama 포트에 필요한 모델 설치
- 포트 11434, 11435, 11436에 모델 확인 및 설치
"""
import requests
import sys
import io
import time

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 필요한 모델 목록 (성능 향상 버전)
REQUIRED_MODELS = [
    "qwen2.5:7b",        # 실시간 모니터 (빠른 응답)
    "qwen2.5:14b",       # 메인 분석기 (균형)
    "deepseek-coder-v2:16b",  # 메인 분석기 (고성능)
    "qwen2.5:32b",       # 감시자 LLM (최고 성능)
]

PORTS = [11434, 11435, 11436]

print("=" * 60)
print("Ollama 모델 설치 스크립트")
print("=" * 60)
print()

def check_models(port):
    """해당 포트의 설치된 모델 확인"""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            model_names = [m.get('name', '') for m in models]
            return model_names
        return None
    except:
        return None

def pull_model(port, model_name):
    """해당 포트에서 모델 다운로드"""
    print(f"\n[포트 {port}] {model_name} 모델 다운로드 중...")
    print(f"  대용량 모델은 시간이 걸릴 수 있습니다...")

    try:
        response = requests.post(
            f"http://127.0.0.1:{port}/api/pull",
            json={"name": model_name},
            timeout=1800,  # 30분 타임아웃
            stream=True
        )

        if response.status_code == 200:
            # 스트리밍 응답 처리
            for line in response.iter_lines():
                if line:
                    try:
                        data = eval(line.decode('utf-8'))
                        status = data.get('status', '')
                        if 'pulling' in status.lower():
                            print(f"  진행 중: {status}", end='\r')
                    except:
                        pass

            print(f"\n[포트 {port}] {model_name} 다운로드 완료!")
            return True
        else:
            print(f"\n[포트 {port}] {model_name} 다운로드 실패: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"\n[포트 {port}] {model_name} 다운로드 오류: {e}")
        return False

# 각 포트별로 모델 확인 및 설치
for port in PORTS:
    port_name = {
        11434: "ETH Trader",
        11435: "KIS Trader",
        11436: "Self-Improvement"
    }.get(port, f"포트 {port}")

    print(f"\n{'=' * 60}")
    print(f"[포트 {port}] {port_name}")
    print(f"{'=' * 60}")

    # 현재 설치된 모델 확인
    installed = check_models(port)

    if installed is None:
        print(f"[경고] 포트 {port}에 연결할 수 없습니다. Ollama가 실행 중인지 확인하세요.")
        continue

    print(f"현재 설치된 모델: {len(installed)}개")
    for model in installed:
        print(f"  - {model}")

    # 필요한 모델 중 없는 것만 설치
    for required_model in REQUIRED_MODELS:
        if required_model not in installed:
            print(f"\n[필요] {required_model} 모델이 없습니다.")
            success = pull_model(port, required_model)
            if success:
                time.sleep(2)
        else:
            print(f"[OK] {required_model} 이미 설치됨")

print("\n" + "=" * 60)
print("모든 포트의 모델 설치 확인 완료!")
print("=" * 60)
print()
print("최종 상태:")
for port in PORTS:
    port_name = {
        11434: "ETH Trader",
        11435: "KIS Trader",
        11436: "Self-Improvement"
    }.get(port, f"포트 {port}")

    installed = check_models(port)
    if installed:
        print(f"\n[포트 {port}] {port_name}: {len(installed)}개 모델")
        for model in installed:
            print(f"  - {model}")
