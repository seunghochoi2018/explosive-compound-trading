#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""현재 SOXL/SOXS 추천 포지션 확인"""
import requests
import json
from datetime import datetime
import ollama

def analyze_market():
    prompt = """당신은 반도체 ETF(SOXL/SOXS) 전문 트레이더입니다.

현재 시간: 2025-10-11 (금요일)
현재 보유: SOXL (BULL) @ $42.08 진입 (10-09)

최근 거래 기록:
- 10-08: SOXS (BEAR) @ $4.09 진입
- 10-09: SOXS @ $4.17 청산 (+1.95% 수익)
- 10-09: SOXL (BULL) @ $42.08 진입 (현재 보유 중)

질문: 지금 (10-11 금요일) 새로 진입한다면 어떤 포지션을 추천하시나요?
1. SOXL (BULL) - 반도체 상승 베팅 (3배 레버리지)
2. SOXS (BEAR) - 반도체 하락 베팅 (3배 레버리지)
3. HOLD - 관망

다음 형식으로만 답변:
SIGNAL: [BULL/BEAR/HOLD]
REASON: [한 문장으로 이유]
CONFIDENCE: [1-10]
"""

    try:
        print("LLM 분석 중...")

        # Ollama 라이브러리 사용
        client = ollama.Client(host='http://127.0.0.1:11435')
        response = client.chat(
            model='deepseek-coder-v2:16b',
            messages=[{'role': 'user', 'content': prompt}]
        )

        result = response['message']['content']
        print("\n=== LLM 추천 ===")
        print(result)
        print("=" * 50)
        return result
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    analyze_market()
