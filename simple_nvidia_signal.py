#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 NVIDIA 신호 알림 시스템
- NVDL/NVDD 가격 모니터링
- LLM 분석 결과 텔레그램 전송
- 에러 없는 안정적인 시스템
"""

import requests
import time
from datetime import datetime

class SimpleNVIDIASignal:
    def __init__(self):
        # 텔레그램 설정
        self.telegram_token = "7819173403:AAEwBNh6etqyWvh-GivLDrTJb8b_ho2ju-U"
        self.chat_id = "7805944420"

        # FMP API 키
        self.api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

        self.ollama_url = "http://localhost:11434/api/generate"

        print("[INIT] 간단한 NVIDIA 신호 알림 시스템 시작")

    def get_stock_price(self, symbol):
        """주가 조회"""
        try:
            url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}"
            params = {"apikey": self.api_key}
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0]["price"]
            return None
        except Exception as e:
            print(f"[ERROR] {symbol} 가격 조회 실패: {e}")
            return None

    def analyze_with_llm(self, nvdl_price, nvdd_price):
        """LLM 분석"""
        prompt = f"""NVIDIA ETF 분석:
- NVDL (3배 레버리지): ${nvdl_price:.2f}
- NVDD (-1배): ${nvdd_price:.2f}

매매 추천 (BUY_NVDL, BUY_NVDD, HOLD 중 하나만):"""

        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=15  # 짧은 타임아웃
            )

            if response.status_code == 200:
                result = response.json()
                analysis = result.get('response', '').strip()

                if 'BUY_NVDL' in analysis.upper():
                    return 'BUY_NVDL'
                elif 'BUY_NVDD' in analysis.upper():
                    return 'BUY_NVDD'
                else:
                    return 'HOLD'
            else:
                return 'HOLD'
        except:
            return 'HOLD'

    def send_telegram(self, message):
        """텔레그램 전송"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, data=data, timeout=5)
            return response.status_code == 200
        except:
            return False

    def run(self):
        """메인 실행"""
        print("[START] NVIDIA 신호 모니터링 시작")

        while True:
            try:
                # 가격 조회
                nvdl_price = self.get_stock_price("NVDL")
                nvdd_price = self.get_stock_price("NVDD")

                if nvdl_price and nvdd_price:
                    print(f"[PRICE] NVDL: ${nvdl_price:.2f}, NVDD: ${nvdd_price:.2f}")

                    # LLM 분석
                    decision = self.analyze_with_llm(nvdl_price, nvdd_price)
                    print(f"[LLM] 분석 결과: {decision}")

                    # 텔레그램 전송
                    if decision != 'HOLD':
                        message = f"""[NVIDIA 신호]
시간: {datetime.now().strftime('%H:%M:%S')}
NVDL: ${nvdl_price:.2f}
NVDD: ${nvdd_price:.2f}
추천: {decision}"""

                        if self.send_telegram(message):
                            print(f"[TELEGRAM] 신호 전송 완료: {decision}")
                    else:
                        print("[HOLD] 관망")
                else:
                    print("[ERROR] 가격 조회 실패")

                # 5분 대기
                print("[WAIT] 5분 대기...")
                time.sleep(300)

            except KeyboardInterrupt:
                print("[EXIT] 프로그램 종료")
                break
            except Exception as e:
                print(f"[ERROR] 시스템 오류: {e}")
                time.sleep(60)

if __name__ == "__main__":
    signal_bot = SimpleNVIDIASignal()
    signal_bot.run()