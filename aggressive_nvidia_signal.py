#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
적극적 NVIDIA 신호 시스템
- 더 빠른 결정
- 더 많은 신호 생성
- 간단한 로직으로 안정성 확보
"""

import os
import sys
import time
import logging
import requests
from datetime import datetime
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

class AggressiveNVIDIASignal:
    """적극적 NVIDIA 신호 시스템"""

    def __init__(self):
        # FMP API 키
        self.fmp_api_key = "n8B5UCT5PD7P4DRokN0V5igzMw0XxH2j"

        # Telegram 설정
        self.telegram_token = "7719873041:AAGxlKf7Q0dwHXk90Hcxpv_BqCJWjMWFzPw"
        self.telegram_chat_id = "7400866348"

        # 설정
        self.check_interval = 120  # 2분 간격
        self.min_change = 1.0  # 1% 이상 변화시 신호
        self.last_signal_time = {}  # 심볼별 마지막 신호 시간
        self.signal_cooldown = 300  # 5분 쿨다운

        logger.info(" 적극적 NVIDIA 신호 시스템 시작")

    def get_stock_price(self, symbol: str) -> Optional[Dict]:
        """주식 가격 조회"""
        try:
            url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}"
            params = {"apikey": self.fmp_api_key}

            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data:
                    return {
                        "symbol": symbol,
                        "price": data[0]["price"],
                        "change": data[0]["change"],
                        "change_percent": data[0]["changesPercentage"],
                        "volume": data[0]["volume"],
                        "timestamp": datetime.now()
                    }
        except Exception as e:
            logger.error(f" {symbol} 조회 실패: {e}")
        return None

    def analyze_signal(self, data: Dict) -> Optional[str]:
        """신호 분석 (간단하고 적극적)"""
        if not data:
            return None

        symbol = data["symbol"]
        change_percent = data["change_percent"]

        # 마지막 신호 확인 (쿨다운)
        if symbol in self.last_signal_time:
            if time.time() - self.last_signal_time[symbol] < self.signal_cooldown:
                return None

        # 적극적 신호 생성
        signal = None

        # NVDL (3배 레버리지)
        if symbol == "NVDL":
            if change_percent >= self.min_change:
                signal = f" NVDL 상승 신호! {change_percent:+.2f}%"
            elif change_percent <= -self.min_change:
                signal = f" NVDL 하락 반등 기회! {change_percent:+.2f}%"

        # NVDD (인버스)
        elif symbol == "NVDD":
            if change_percent >= self.min_change:
                signal = f" NVDD 상승 (NVIDIA 하락) {change_percent:+.2f}%"
            elif change_percent <= -self.min_change:
                signal = f" NVDD 하락 (NVIDIA 상승) {change_percent:+.2f}%"

        if signal:
            self.last_signal_time[symbol] = time.time()
            return signal

        return None

    def send_telegram(self, message: str):
        """텔레그램 알림"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                logger.info(f" 텔레그램 전송: {message}")
            else:
                logger.error(f"텔레그램 전송 실패: {response.status_code}")
        except Exception as e:
            logger.error(f"텔레그램 오류: {e}")

    def run_cycle(self):
        """메인 사이클"""
        logger.info(f"\n⏰ 시장 분석 중... ({datetime.now().strftime('%H:%M:%S')})")

        # NVDL 분석
        nvdl_data = self.get_stock_price("NVDL")
        if nvdl_data:
            logger.info(f"NVDL: ${nvdl_data['price']:.2f} ({nvdl_data['change_percent']:+.2f}%)")

            signal = self.analyze_signal(nvdl_data)
            if signal:
                full_message = f"""
{signal}

 현재가: ${nvdl_data['price']:.2f}
 변화율: {nvdl_data['change_percent']:+.2f}%
 거래량: {nvdl_data['volume']:,}
⏰ 시간: {datetime.now().strftime('%H:%M:%S')}

#NVDL #레버리지 #신호
"""
                self.send_telegram(full_message)

        # NVDD 분석
        nvdd_data = self.get_stock_price("NVDD")
        if nvdd_data:
            logger.info(f"NVDD: ${nvdd_data['price']:.2f} ({nvdd_data['change_percent']:+.2f}%)")

            signal = self.analyze_signal(nvdd_data)
            if signal:
                full_message = f"""
{signal}

 현재가: ${nvdd_data['price']:.2f}
 변화율: {nvdd_data['change_percent']:+.2f}%
 거래량: {nvdd_data['volume']:,}
⏰ 시간: {datetime.now().strftime('%H:%M:%S')}

#NVDD #인버스 #신호
"""
                self.send_telegram(full_message)

        # 변화가 작을 때도 상태 알림 (10분마다)
        current_time = time.time()
        if not hasattr(self, 'last_status_time'):
            self.last_status_time = 0

        if current_time - self.last_status_time > 600:  # 10분마다
            if nvdl_data and nvdd_data:
                status_message = f"""
 NVIDIA 정기 리포트

NVDL: ${nvdl_data['price']:.2f} ({nvdl_data['change_percent']:+.2f}%)
NVDD: ${nvdd_data['price']:.2f} ({nvdd_data['change_percent']:+.2f}%)

시간: {datetime.now().strftime('%H:%M:%S')}
"""
                self.send_telegram(status_message)
                self.last_status_time = current_time

    def run(self):
        """메인 실행"""
        logger.info(" 적극적 NVIDIA 신호 시스템")
        logger.info(f" 체크 간격: {self.check_interval}초")
        logger.info(f" 최소 변화율: {self.min_change}%")
        logger.info("=" * 60)

        while True:
            try:
                self.run_cycle()

                logger.info(f"⏰ {self.check_interval}초 대기 중...")
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("\n 종료")
                break
            except Exception as e:
                logger.error(f"오류: {e}")
                time.sleep(30)

if __name__ == "__main__":
    signal = AggressiveNVIDIASignal()
    signal.run()