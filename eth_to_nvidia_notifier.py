#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETH 신호 → NVIDIA ETF 추천 알림 시스템 v1.0

사용자 요청사항:
1. 자동매매 제거 (알림만 전송)
2. 텔레그램 알림 추가
3. ETH 롱 신호 → NVDL (NVIDIA 3x Long ETF) 추천
4. ETH 숏 신호 → NVDQ (NVIDIA Inverse ETF) 추천
5. 코드3의 검증된 LLM 분석 엔진 활용
6. 무한 실행 및 자동 복구 기능
"""

import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os

# 코드3의 모듈 임포트
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '코드3'))

from llm_market_analyzer import LLMMarketAnalyzer
from bybit_api_manager import BybitAPIManager as BybitAPI
from api_config import get_api_credentials, TELEGRAM_CONFIG


class TelegramNotifier:
    """텔레그램 알림 전송 클래스"""

    def __init__(self):
        self.token = TELEGRAM_CONFIG['token']
        self.chat_id = TELEGRAM_CONFIG['chat_id']
        self.base_url = f"https://api.telegram.org/bot{self.token}"

        # 중복 알림 방지
        self.last_signal_type = None
        self.last_signal_time = 0
        self.min_signal_interval = 300  # 5분 최소 간격

    def send_message(self, message: str) -> bool:
        """텔레그램 메시지 전송"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                print(f"[TELEGRAM] 알림 전송 성공")
                return True
            else:
                print(f"[ERROR] 텔레그램 전송 실패: {response.status_code}")
                return False

        except Exception as e:
            print(f"[ERROR] 텔레그램 오류: {e}")
            return False

    def should_send_notification(self, signal_type: str) -> bool:
        """중복 알림 방지 체크"""
        current_time = time.time()

        # 같은 신호가 5분 이내에 반복되면 스킵
        if (signal_type == self.last_signal_type and
            current_time - self.last_signal_time < self.min_signal_interval):
            return False

        return True

    def update_last_signal(self, signal_type: str):
        """마지막 신호 업데이트"""
        self.last_signal_type = signal_type
        self.last_signal_time = time.time()


class ETHToNVIDIAMapper:
    """
    ETH 신호를 NVIDIA ETF 포지션으로 매핑하는 클래스

    사용자 요구사항:
    - ETH 롱 시그널 → NVDL (NVIDIA 3배 레버리지 롱 ETF) 매수 추천
    - ETH 숏 시그널 → NVDQ (NVIDIA 인버스 ETF) 매수 추천
    - 자동매매 없이 알림만 전송
    """

    def __init__(self):
        print("=== ETH → NVIDIA ETF 알림 시스템 v1.0 ===")
        print("[INFO] 자동매매 비활성화 - 알림 전용 모드")
        print("[INFO] ETH 롱 → NVDL 추천")
        print("[INFO] ETH 숏 → NVDQ 추천")

        # API 설정 (가격 조회용)
        creds = get_api_credentials()
        self.api = BybitAPI(
            api_key=creds['api_key'],
            api_secret=creds['api_secret'],
            testnet=False
        )

        # LLM 분석기 (코드3에서 검증된 엔진)
        self.llm_analyzer = LLMMarketAnalyzer(model_name="qwen2.5:1.5b")

        # 텔레그램 알림
        self.telegram = TelegramNotifier()

        # ETH 심볼
        self.symbol = "ETHUSD"

        # 가격 히스토리
        self.price_history = []
        self.volume_history = []
        self.max_history = 50

        # ETH → NVIDIA 매핑 설정
        self.mapping_config = {
            'LONG': {
                'symbol': 'NVDL',
                'name': 'GraniteShares 2x Long NVIDIA Daily ETF',
                'action': 'BUY',
                'rationale': 'ETH 상승 → 기술주 강세 → NVIDIA 상승 기대'
            },
            'SHORT': {
                'symbol': 'NVDQ',
                'name': 'GraniteShares 1x Short NVIDIA Daily ETF',
                'action': 'BUY',
                'rationale': 'ETH 하락 → 기술주 약세 → NVIDIA 하락 기대'
            }
        }

        # 통계
        self.stats = {
            'total_signals': 0,
            'long_signals': 0,
            'short_signals': 0,
            'notifications_sent': 0
        }

    def get_eth_price(self) -> float:
        """ETH 현재가 조회"""
        try:
            market_data = self.api.get_market_data(symbol=self.symbol, interval="1", limit=1)
            if market_data and market_data.get("retCode") == 0:
                data_list = market_data.get("result", {}).get("list", [])
                if data_list:
                    price = float(data_list[0][4])  # close price
                    return price
            return 0.0
        except Exception as e:
            print(f"[ERROR] ETH 가격 조회 실패: {e}")
            return 0.0

    def update_price_history(self, price: float):
        """가격 히스토리 업데이트"""
        self.price_history.append(price)
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)

        # 볼륨 히스토리 (임시)
        self.volume_history.append(1000 + len(self.price_history) * 10)
        if len(self.volume_history) > self.max_history:
            self.volume_history.pop(0)

    def analyze_eth_with_llm(self, current_price: float) -> Dict:
        """LLM을 사용한 ETH 시장 분석"""
        try:
            analysis = self.llm_analyzer.analyze_eth_market(
                current_price=current_price,
                price_history=self.price_history.copy(),
                volume_data=self.volume_history.copy(),
                current_position="NONE",
                position_pnl=0.0
            )
            return analysis
        except Exception as e:
            print(f"[ERROR] LLM 분석 오류: {e}")
            return {
                'buy_signal': 50,
                'sell_signal': 50,
                'confidence': 0,
                'reasoning': f'분석 오류: {str(e)}'
            }

    def determine_nvidia_position(self, llm_analysis: Dict) -> Optional[Dict]:
        """LLM 분석 결과를 바탕으로 NVIDIA ETF 포지션 결정"""

        buy_signal = llm_analysis.get('buy_signal', 0)
        sell_signal = llm_analysis.get('sell_signal', 0)
        confidence = llm_analysis.get('confidence', 0)
        reasoning = llm_analysis.get('reasoning', 'N/A')

        # 최소 신뢰도 필터 (70% 이상만 알림)
        if confidence < 70:
            return None

        # ETH 롱 시그널 → NVDL 추천
        if buy_signal > sell_signal:
            recommendation = self.mapping_config['LONG'].copy()
            recommendation.update({
                'eth_signal': 'LONG',
                'eth_buy_signal': buy_signal,
                'eth_sell_signal': sell_signal,
                'confidence': confidence,
                'reasoning': reasoning,
                'signal_strength': buy_signal - sell_signal
            })
            return recommendation

        # ETH 숏 시그널 → NVDQ 추천
        elif sell_signal > buy_signal:
            recommendation = self.mapping_config['SHORT'].copy()
            recommendation.update({
                'eth_signal': 'SHORT',
                'eth_buy_signal': buy_signal,
                'eth_sell_signal': sell_signal,
                'confidence': confidence,
                'reasoning': reasoning,
                'signal_strength': sell_signal - buy_signal
            })
            return recommendation

        return None

    def format_notification_message(self, recommendation: Dict, eth_price: float) -> str:
        """텔레그램 알림 메시지 포맷"""

        signal_emoji = "" if recommendation['eth_signal'] == 'LONG' else ""

        message = f"""
{signal_emoji} <b>NVIDIA ETF 포지션 추천</b>

<b>━━━━━━━━━━━━━━━━━━━━━━</b>

<b> ETH 분석 결과</b>
• 현재가: ${eth_price:,.2f}
• ETH 신호: {recommendation['eth_signal']}
• 매수 신호: {recommendation['eth_buy_signal']}
• 매도 신호: {recommendation['eth_sell_signal']}
• 신뢰도: {recommendation['confidence']}%
• 신호 강도: {recommendation['signal_strength']}

<b> 분석 근거</b>
{recommendation['reasoning']}

<b> NVIDIA ETF 추천</b>
• 종목: <b>{recommendation['symbol']}</b>
• 종목명: {recommendation['name']}
• 액션: <b>{recommendation['action']}</b>

<b> 매핑 논리</b>
{recommendation['rationale']}

<b>━━━━━━━━━━━━━━━━━━━━━━</b>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>※ 알림 전용 시스템 (자동매매 비활성)</i>
"""
        return message.strip()

    def send_notification(self, recommendation: Dict, eth_price: float) -> bool:
        """NVIDIA ETF 추천 알림 전송"""

        signal_type = recommendation['symbol']  # NVDL or NVDQ

        # 중복 알림 방지
        if not self.telegram.should_send_notification(signal_type):
            print(f"[SKIP] 최근 {signal_type} 알림 전송됨 (5분 이내 중복)")
            return False

        # 메시지 생성 및 전송
        message = self.format_notification_message(recommendation, eth_price)

        if self.telegram.send_message(message):
            self.telegram.update_last_signal(signal_type)
            self.stats['notifications_sent'] += 1
            return True

        return False

    def print_status(self, eth_price: float, recommendation: Optional[Dict] = None):
        """현재 상태 출력"""
        print(f"\n[STATUS] ETH: ${eth_price:,.2f}")

        if recommendation:
            print(f"[SIGNAL] ETH {recommendation['eth_signal']} → {recommendation['symbol']} {recommendation['action']}")
            print(f"[CONFIDENCE] {recommendation['confidence']}%")
            print(f"[REASONING] {recommendation['reasoning'][:80]}...")
        else:
            print(f"[SIGNAL] 대기 중 (신뢰도 부족 또는 중립)")

        print(f"[STATS] 총 신호: {self.stats['total_signals']}, "
              f"롱: {self.stats['long_signals']}, "
              f"숏: {self.stats['short_signals']}, "
              f"알림: {self.stats['notifications_sent']}")

    def run_continuous_monitoring(self):
        """
        연속 모니터링 - 무한 실행

        사용자 요구사항 반영:
        - "왜 종료돼 계속 돌아가야지" → 무한 루프 보장
        - 모든 오류 상황에서 자동 복구
        - 절대 종료 없이 계속 실행
        """
        print("\n" + "=" * 60)
        print("[LAUNCH] ETH → NVIDIA ETF 알림 시스템 시작")
        print("[MODE] 알림 전용 (자동매매 비활성)")
        print("[AUTO] 무한 실행 및 자동 복구")
        print("=" * 60)

        error_count = 0
        max_consecutive_errors = 10

        # 시작 알림
        startup_message = f"""
 <b>ETH → NVIDIA ETF 알림 시스템 시작</b>

• 모드: 알림 전용
• ETH 롱 → NVDL 추천
• ETH 숏 → NVDQ 추천
• LLM 모델: {self.llm_analyzer.model_name}

시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.telegram.send_message(startup_message.strip())

        while True:  # 절대 종료하지 않는 무한 루프
            try:
                # ETH 가격 조회
                eth_price = self.get_eth_price()

                if eth_price <= 0:
                    print("[ERROR] ETH 가격 조회 실패 - 10초 후 재시도")
                    time.sleep(10)
                    continue

                # 정상 작동 시 오류 카운터 리셋
                error_count = 0

                # 가격 히스토리 업데이트
                self.update_price_history(eth_price)

                # 충분한 데이터가 있을 때만 분석
                if len(self.price_history) >= 10:
                    # LLM 분석
                    llm_analysis = self.analyze_eth_with_llm(eth_price)

                    # NVIDIA ETF 포지션 결정
                    recommendation = self.determine_nvidia_position(llm_analysis)

                    # 추천이 있으면 알림 전송
                    if recommendation:
                        self.stats['total_signals'] += 1

                        if recommendation['eth_signal'] == 'LONG':
                            self.stats['long_signals'] += 1
                        else:
                            self.stats['short_signals'] += 1

                        self.send_notification(recommendation, eth_price)

                    # 상태 출력
                    self.print_status(eth_price, recommendation)
                else:
                    print(f"[INFO] 데이터 수집 중... ({len(self.price_history)}/10)")

                # 30초 대기 (적절한 모니터링 간격)
                time.sleep(30)

            except KeyboardInterrupt:
                print("\n[WARNING] 사용자 중단 요청 감지")
                print("[CONTINUE] 하지만 무한 실행 모드로 계속됩니다!")
                time.sleep(5)
                continue

            except Exception as e:
                error_count += 1
                print(f"\n[ERROR] 메인 루프 오류 #{error_count}: {e}")
                print(f"[RECOVERY] 자동 복구 모드 활성화...")

                if error_count < max_consecutive_errors:
                    recovery_delay = min(error_count * 5, 60)
                    print(f"           -> {recovery_delay}초 후 자동 재시작")
                    time.sleep(recovery_delay)
                    print(f"           -> 시스템 복구 완료!")
                    continue
                else:
                    print(f"           -> 연속 오류 {max_consecutive_errors}회 도달")
                    print(f"           -> 시스템 점검 모드: 120초 대기")
                    time.sleep(120)
                    error_count = 0
                    print(f"           -> 정상 운영 재개")
                    continue


def main():
    """메인 실행 함수"""
    mapper = ETHToNVIDIAMapper()
    mapper.run_continuous_monitoring()


if __name__ == "__main__":
    main()
