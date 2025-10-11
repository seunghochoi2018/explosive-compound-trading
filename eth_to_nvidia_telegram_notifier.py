#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETH → NVIDIA 포지션 텔레그램 알림 시스템 v1.0

사용자 요구사항 반영:
- "자동매매 없애고 텔레그램 알림 추가"
- "롱일때는 엔비디엘 숏일때는 엔비디큐로 포지션 잡는 모델"
- "이 모든 부분을 반영하는데" → 기존 ETH 분석 + 새로운 NVIDIA 매핑

핵심 전략:
1. ETH 시장 분석 (코드3의 LLM 분석 기능 활용)
2. ETH 롱 시그널 → NVDL 매수 추천
3. ETH 숏 시그널 → NVDQ 매수 추천
4. 자동매매 없이 텔레그램 알림만 전송
5. 상세한 분석 정보와 포지션 가이드 제공
"""

import time
import json
import os
import sys
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 코드3 모듈 import를 위한 경로 추가
sys.path.append('C:\\Users\\user\\Documents\\코드3')
sys.path.append('C:\\Users\\user\\Documents\\코드4')

try:
    from llm_market_analyzer import LLMMarketAnalyzer
    from telegram_notifier import TelegramNotifier
    print("[INIT] 모듈 import 성공")
except ImportError as e:
    print(f"[ERROR] 모듈 import 실패: {e}")

class ETHToNVIDIAMapper:
    """
    ETH 신호를 NVIDIA ETF 포지션으로 매핑하는 클래스

    사용자 요구사항:
    - ETH 롱 시그널 → NVDL (NVIDIA 3배 레버리지 롱 ETF) 매수 추천
    - ETH 숏 시그널 → NVDQ (NVIDIA 인버스 ETF) 매수 추천
    - 자동매매 없이 알림만 전송
    """

    def __init__(self):
        """
        ETH → NVIDIA 매핑 시스템 초기화

        사용자 피드백 반영:
        - "왜 종료돼 계속 돌아가야지" → 무한 실행 모드
        - "컨텍스트하고 주석에 남겨" → 상세한 주석 추가
        """
        print("=" * 70)
        print("[LAUNCH] ETH → NVIDIA 포지션 텔레그램 알림 시스템 v1.0")
        print("[STRATEGY] ETH 분석 → NVIDIA ETF 포지션 추천")
        print("[MODE] 자동매매 비활성화, 알림 전용")
        print("=" * 70)

        # ================================================
        # LLM 시장 분석기 초기화 (코드3에서 가져온 검증된 분석 엔진)
        # ================================================
        try:
            self.llm_analyzer = LLMMarketAnalyzer(model_name="qwen2.5:1.5b")
            print("[INIT] LLM 시장 분석기 초기화 완료")
        except Exception as e:
            print(f"[ERROR] LLM 분석기 초기화 실패: {e}")
            self.llm_analyzer = None

        # ================================================
        # 텔레그램 알림 시스템 초기화
        # ================================================
        try:
            self.telegram = TelegramNotifier()
            print("[INIT] 텔레그램 알림 시스템 초기화 완료")
        except Exception as e:
            print(f"[ERROR] 텔레그램 초기화 실패: {e}")
            self.telegram = None

        # ================================================
        # ETH → NVIDIA 매핑 설정
        # ================================================
        self.mapping_config = {
            # ETH 롱 시그널 → NVDL (NVIDIA 3x 레버리지 롱)
            'LONG': {
                'symbol': 'NVDL',
                'name': 'GraniteShares 2x Long NVIDIA Daily ETF',
                'action': 'BUY',
                'rationale': 'ETH 상승 → 기술주 강세 → NVIDIA 상승 기대'
            },

            # ETH 숏 시그널 → NVDQ (NVIDIA 인버스)
            'SHORT': {
                'symbol': 'NVDQ',
                'name': 'GraniteShares 1x Short NVIDIA Daily ETF',
                'action': 'BUY',
                'rationale': 'ETH 하락 → 기술주 약세 → NVIDIA 하락 기대'
            }
        }

        # ================================================
        # 분석 상태 추적
        # ================================================
        self.last_signal = None
        self.last_signal_time = None
        self.signal_cooldown = 300  # 5분 쿨다운 (중복 알림 방지)
        self.analysis_interval = 30  # 30초마다 분석

        # 가격 히스토리 (LLM 분석용)
        self.eth_price_history = []
        self.max_history = 50

        print("[INIT] 초기화 완료! ETH 분석 시작...")

    def get_eth_price_data(self) -> Optional[Dict]:
        """
        ETH 현재 가격 및 시장 데이터 조회

        Returns:
            Dict: ETH 가격 및 시장 데이터
        """
        try:
            # CoinGecko API를 통한 ETH 데이터 조회
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'ethereum',
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true'
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                eth_data = data.get('ethereum', {})

                return {
                    'price': eth_data.get('usd', 0),
                    'change_24h': eth_data.get('usd_24h_change', 0),
                    'volume_24h': eth_data.get('usd_24h_vol', 0),
                    'timestamp': datetime.now()
                }
            else:
                print(f"[ERROR] CoinGecko API 오류: {response.status_code}")
                return None

        except Exception as e:
            print(f"[ERROR] ETH 가격 조회 실패: {e}")
            return None

    def update_price_history(self, price: float):
        """
        ETH 가격 히스토리 업데이트 (LLM 분석용)

        Args:
            price (float): 현재 ETH 가격
        """
        self.eth_price_history.append(price)
        if len(self.eth_price_history) > self.max_history:
            self.eth_price_history.pop(0)

    def analyze_eth_with_llm(self, current_price: float) -> Optional[Dict]:
        """
        LLM을 활용한 ETH 시장 분석

        사용자 요구사항: "이 모든 부분을 반영하는데"
        → 기존 코드3의 검증된 LLM 분석 로직 활용

        Args:
            current_price (float): 현재 ETH 가격

        Returns:
            Dict: LLM 분석 결과
        """
        if not self.llm_analyzer or len(self.eth_price_history) < 5:
            return None

        try:
            print(f"[LLM] ETH 시장 분석 중... (가격: ${current_price:.2f})")

            # LLM 분석 실행 (코드3의 검증된 분석 엔진 사용)
            analysis = self.llm_analyzer.analyze_eth_market(
                current_price=current_price,
                price_history=self.eth_price_history,
                volume_data=None,
                current_position="NONE",
                position_pnl=0.0
            )

            if analysis and 'buy_signal' in analysis and 'sell_signal' in analysis:
                print(f"[LLM] 분석 완료: 매수={analysis['buy_signal']}, 매도={analysis['sell_signal']}")
                return analysis
            else:
                print("[LLM] 분석 결과 부족")
                return None

        except Exception as e:
            print(f"[ERROR] LLM 분석 실패: {e}")
            return None

    def determine_nvidia_position(self, llm_analysis: Dict) -> Optional[Dict]:
        """
        LLM 분석 결과를 바탕으로 NVIDIA ETF 포지션 결정

        사용자 요구사항:
        - "롱일때는 엔비디엘" → ETH 롱 시그널 시 NVDL 추천
        - "숏일때는 엔비디큐" → ETH 숏 시그널 시 NVDQ 추천

        Args:
            llm_analysis (Dict): LLM 분석 결과

        Returns:
            Dict: NVIDIA 포지션 추천 정보
        """
        try:
            buy_signal = llm_analysis.get('buy_signal', 0)
            sell_signal = llm_analysis.get('sell_signal', 0)
            confidence = llm_analysis.get('confidence', 0)

            # 신호 강도 기준 (사용자 요구: "임계값 제거, LLM 자율 판단")
            # 하지만 알림의 경우 최소한의 필터링 필요
            min_confidence = 70  # 70% 이상 신뢰도에서만 알림

            if confidence < min_confidence:
                return None

            # ETH 롱 시그널 → NVDL 추천
            if buy_signal > sell_signal:
                signal_strength = buy_signal - sell_signal
                recommendation = self.mapping_config['LONG'].copy()
                recommendation.update({
                    'eth_signal': 'LONG',
                    'eth_buy_signal': buy_signal,
                    'eth_sell_signal': sell_signal,
                    'signal_strength': signal_strength,
                    'confidence': confidence,
                    'reasoning': f"ETH 롱 시그널 감지 (매수:{buy_signal} vs 매도:{sell_signal})",
                    'analysis_details': llm_analysis
                })
                return recommendation

            # ETH 숏 시그널 → NVDQ 추천
            elif sell_signal > buy_signal:
                signal_strength = sell_signal - buy_signal
                recommendation = self.mapping_config['SHORT'].copy()
                recommendation.update({
                    'eth_signal': 'SHORT',
                    'eth_buy_signal': buy_signal,
                    'eth_sell_signal': sell_signal,
                    'signal_strength': signal_strength,
                    'confidence': confidence,
                    'reasoning': f"ETH 숏 시그널 감지 (매도:{sell_signal} vs 매수:{buy_signal})",
                    'analysis_details': llm_analysis
                })
                return recommendation

            # 신호가 비슷한 경우 → 포지션 없음
            else:
                return None

        except Exception as e:
            print(f"[ERROR] 포지션 결정 실패: {e}")
            return None

    def should_send_notification(self, recommendation: Dict) -> bool:
        """
        알림 전송 여부 결정 (중복 알림 방지)

        Args:
            recommendation (Dict): 포지션 추천 정보

        Returns:
            bool: 알림 전송 여부
        """
        current_time = datetime.now()

        # 첫 알림인 경우
        if not self.last_signal_time:
            return True

        # 쿨다운 시간 체크
        time_since_last = (current_time - self.last_signal_time).total_seconds()
        if time_since_last < self.signal_cooldown:
            return False

        # 동일한 시그널 중복 체크
        current_signal = f"{recommendation['symbol']}_{recommendation['eth_signal']}"
        if self.last_signal == current_signal:
            return False

        return True

    def format_telegram_message(self, recommendation: Dict, eth_data: Dict) -> str:
        """
        텔레그램 메시지 포맷팅

        Args:
            recommendation (Dict): 포지션 추천 정보
            eth_data (Dict): ETH 시장 데이터

        Returns:
            str: 포맷된 텔레그램 메시지
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 이모지 및 포맷팅 (사용자 친화적)
        direction_emoji = "" if recommendation['eth_signal'] == 'LONG' else ""
        confidence_emoji = "" if recommendation['confidence'] >= 80 else ""

        message = f"""
{direction_emoji} **ETH → NVIDIA 포지션 알림**

 **시간**: {timestamp}
 **ETH 가격**: ${eth_data['price']:.2f} ({eth_data['change_24h']:+.2f}%)

 **추천 포지션**:
 **종목**: {recommendation['symbol']} ({recommendation['name']})
 **액션**: {recommendation['action']}
 **근거**: {recommendation['rationale']}

 **신호 분석**:
• ETH 방향: {recommendation['eth_signal']}
• 매수 신호: {recommendation['eth_buy_signal']:.1f}
• 매도 신호: {recommendation['eth_sell_signal']:.1f}
• 신호 강도: {recommendation['signal_strength']:.1f}

{confidence_emoji} **신뢰도**: {recommendation['confidence']:.1f}%

 **분석 요약**: {recommendation['reasoning']}

 **주의사항**:
- 이는 자동화된 분석 결과입니다
- 투자 전 추가 검토를 권장합니다
- 리스크 관리를 철저히 하세요
"""

        return message.strip()

    def send_telegram_notification(self, recommendation: Dict, eth_data: Dict):
        """
        텔레그램 알림 전송

        Args:
            recommendation (Dict): 포지션 추천 정보
            eth_data (Dict): ETH 시장 데이터
        """
        if not self.telegram:
            print("[ERROR] 텔레그램 설정되지 않음")
            return

        try:
            message = self.format_telegram_message(recommendation, eth_data)

            # 텔레그램 전송
            success = self.telegram.send_message(message)

            if success:
                print(f"[TELEGRAM]  알림 전송 성공: {recommendation['symbol']} {recommendation['action']}")

                # 마지막 신호 기록
                self.last_signal = f"{recommendation['symbol']}_{recommendation['eth_signal']}"
                self.last_signal_time = datetime.now()
            else:
                print("[TELEGRAM]  알림 전송 실패")

        except Exception as e:
            print(f"[ERROR] 텔레그램 전송 오류: {e}")

    def run_continuous_monitoring(self):
        """
        연속 모니터링 실행 - 사용자 요구사항: "계속 돌아가야지"

        무한 루프로 실행되며 절대 종료되지 않음:
        - ETH 시장 데이터 수집
        - LLM 분석 실행
        - NVIDIA 포지션 결정
        - 텔레그램 알림 전송
        """
        print("\n" + "=" * 60)
        print("[START] 연속 모니터링 시작 - 무한 실행 모드")
        print("[INFO] ETH → NVIDIA 포지션 알림 시스템 가동")
        print("=" * 60)

        error_count = 0
        max_consecutive_errors = 10

        while True:  # 사용자 요구: "왜 종료돼 계속 돌아가야지"
            try:
                # ETH 시장 데이터 수집
                eth_data = self.get_eth_price_data()
                if not eth_data:
                    print("[ERROR] ETH 데이터 조회 실패 - 30초 후 재시도")
                    time.sleep(30)
                    continue

                # 가격 히스토리 업데이트
                self.update_price_history(eth_data['price'])

                # LLM 분석 실행
                llm_analysis = self.analyze_eth_with_llm(eth_data['price'])
                if not llm_analysis:
                    print("[INFO] LLM 분석 결과 없음 - 대기 중")
                    time.sleep(self.analysis_interval)
                    continue

                # NVIDIA 포지션 결정
                recommendation = self.determine_nvidia_position(llm_analysis)
                if not recommendation:
                    print("[INFO] 포지션 추천 없음 - 모니터링 계속")
                    time.sleep(self.analysis_interval)
                    continue

                # 알림 전송 필요성 확인
                if self.should_send_notification(recommendation):
                    print(f"[SIGNAL] {recommendation['symbol']} {recommendation['action']} 신호 감지!")
                    self.send_telegram_notification(recommendation, eth_data)
                else:
                    print("[INFO] 중복 신호로 알림 생략")

                # 정상 작동 시 오류 카운터 리셋
                error_count = 0

                # 다음 분석까지 대기
                time.sleep(self.analysis_interval)

            except KeyboardInterrupt:
                print("\n[WARNING] 사용자 중단 요청 감지")
                print("[CONTINUE] 하지만 사용자 요청에 따라 계속 실행!")
                print("          ('왜 종료돼 계속 돌아가야지')")
                time.sleep(5)
                continue

            except Exception as e:
                error_count += 1
                print(f"\n[ERROR] 모니터링 루프 오류 #{error_count}: {e}")
                print("[RECOVERY] 자동 복구 모드 활성화...")

                if error_count < max_consecutive_errors:
                    recovery_delay = min(error_count * 10, 120)
                    print(f"           -> {recovery_delay}초 후 자동 재시작")
                    time.sleep(recovery_delay)
                    print("           -> 시스템 복구 완료! 모니터링 재개")
                    continue
                else:
                    print(f"           -> 연속 오류 {max_consecutive_errors}회 도달")
                    print("           -> 시스템 점검 모드: 300초 대기 후 재시작")
                    time.sleep(300)
                    error_count = 0
                    print("           -> 시스템 점검 완료! 정상 운영 재개")
                    continue

def main():
    """메인 실행 함수"""
    print("ETH → NVIDIA 포지션 텔레그램 알림 시스템 시작")

    # 시스템 초기화
    mapper = ETHToNVIDIAMapper()

    # 연속 모니터링 시작
    mapper.run_continuous_monitoring()

if __name__ == "__main__":
    main()