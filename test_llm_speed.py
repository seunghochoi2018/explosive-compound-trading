#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 성능 비교 테스트
- 7b vs 14b 응답 시간 측정
- GPU 사용률 비교
"""
import requests
import time
from datetime import datetime

def test_model_speed(model_name: str, test_count: int = 3):
    """모델 응답 속도 테스트"""
    print(f"\n{'='*60}")
    print(f"[{model_name}] 성능 테스트 시작")
    print(f"{'='*60}")

    # 간단한 시장 분석 프롬프트 (실제 트레이딩과 유사)
    prompt = """Current ETH price: $2,500
5min ago: $2,490 (+0.4%)
15min ago: $2,480 (+0.8%)
Volume spike: 1.5x normal

Quick analysis - respond in ONE word:
BULL, BEAR, or NEUTRAL?"""

    times = []

    for i in range(test_count):
        print(f"\n테스트 {i+1}/{test_count}...")
        start = time.time()

        try:
            response = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "temperature": 0.1,
                    "stream": False,
                    "keep_alive": "30s" if "7b" in model_name else "2m"
                },
                timeout=60
            )

            elapsed = time.time() - start
            times.append(elapsed)

            if response.status_code == 200:
                result = response.json()
                answer = result.get('response', '').strip()
                print(f"  응답: {answer[:50]}...")
                print(f"  시간: {elapsed:.2f}초")
            else:
                print(f"  ERROR: {response.status_code}")

        except Exception as e:
            print(f"  ERROR: {e}")

        # 테스트 간 대기
        if i < test_count - 1:
            time.sleep(2)

    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print(f"\n[{model_name}] 결과:")
        print(f"  평균: {avg_time:.2f}초")
        print(f"  최소: {min_time:.2f}초")
        print(f"  최대: {max_time:.2f}초")

        return avg_time
    else:
        return None

if __name__ == "__main__":
    print("\n" + "="*60)
    print("LLM 성능 비교 테스트")
    print("RTX 2060 6GB GPU 최적화 효과 측정")
    print("="*60)

    # 7b 테스트
    time_7b = test_model_speed("qwen2.5:7b", test_count=3)

    time.sleep(5)

    # 14b 테스트
    time_14b = test_model_speed("qwen2.5:14b", test_count=3)

    # 비교 결과
    print("\n" + "="*60)
    print("최종 비교")
    print("="*60)

    if time_7b and time_14b:
        print(f"7b 평균:  {time_7b:.2f}초 (빠른 필터)")
        print(f"14b 평균: {time_14b:.2f}초 (중요한 판단)")
        print(f"속도 차이: {time_14b - time_7b:.2f}초 (7b가 {((time_14b/time_7b - 1) * 100):.1f}% 빠름)")

        print(f"\nGPU 최적화 효과:")
        print(f"- 7b는 GPU에 완전 로드 (4.7GB)")
        print(f"- 14b는 부분 GPU 활용 (5GB)")
        print(f"- 이전 32b (20GB)는 CPU 폴백으로 매우 느렸음")
