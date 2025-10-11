#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETH 바이비트 실거래 시스템 (LIVE 모드)

################## 중요 설정 - 절대 변경 금지 ##################
# 1. ETHUSD 심볼 사용 (ETHUSDT 아님!)
# 2. ETH 잔고로 거래 (USDT 아님!)
# 3. LIVE 모드로 실거래 (testnet 아님!)
# 4. 15분봉 추세감지로 손실 방지
# 5. 87% 정확도 추세 감지 시스템 적용
##############################################################
"""

import json
import time
import random
from datetime import datetime
import sys
import os

# 코드3 디렉토리의 모듈 임포트
sys.path.append(r'C:\Users\user\Documents\코드3')

# 기존 API 설정 및 관리자 로드
try:
    from api_config import get_api_credentials, get_trading_mode
    from bybit_api_manager import BybitAPIManager
    from optimal_trend_detector import OptimalTrendDetector
    API_AVAILABLE = True
except ImportError:
    print(" 필수 모듈을 찾을 수 없습니다!")
    print("코드3 폴더에서 다음 파일들이 필요합니다:")
    print("- api_config.py")
    print("- bybit_api_manager.py")
    print("- optimal_trend_detector.py")
    API_AVAILABLE = False

class ETHBybitLiveTrader:
    def __init__(self):
        print("=" * 50)
        print("ETH BYBIT LIVE TRADING SYSTEM")
        print(" 15분봉 87% 정확도 추세감지 적용")
        print("  ETHUSD 실거래 - ETH 잔고 사용")
        print("=" * 50)

        if not API_AVAILABLE:
            print(" API 모듈 로드 실패!")
            return

        # API 설정 로드
        credentials = get_api_credentials()

        if not credentials.get("api_key") or not credentials.get("api_secret"):
            print(" API 키가 설정되지 않았습니다!")
            return

        # 바이비트 API 초기화 - 실거래 모드
        self.api = BybitAPIManager(
            api_key=credentials["api_key"],
            api_secret=credentials["api_secret"],
            testnet=False  # 중요: LIVE 모드 강제 설정!
        )

        # 중요: ETHUSD 사용 (ETHUSDT 아님!) - ETH로 거래
        self.symbol = "ETHUSD"  # 절대 변경 금지!

        # 전략 설정
        self.strategy = {
            'leverage': 10,           # 10배 레버리지
            'profit_target': 0.03,    # 3% 익절
            'stop_loss': 0.02,        # 2% 손절
            'position_size': 0.9,     # 90% 사용
            'min_trade_ratio': 0.4    # 최소 40% 잔고로 거래
        }

        # 실제 모드 확인 표시
        print(f" 모드: LIVE (실거래)")
        print(f" 심볼: {self.symbol}")
        print(f" 전략: {self.strategy['leverage']}x 레버리지")
        print(f" 익절: {self.strategy['profit_target']*100}%")
        print(f" 손절: {self.strategy['stop_loss']*100}%")

        # 87% 정확도 추세 감지 시스템 초기화
        self.trend_detector = OptimalTrendDetector()
        print(" 87% 정확도 추세 감지 시스템 로드 완료")

        # 순수 시장 학습 시스템
        self.learning_patterns = {}
        self.pattern_weights = {}
        self.trade_results = []
        self.min_pattern_length = 3
        self.max_pattern_length = 7
        print(" 순수 시장 학습 시스템 초기화 완료")

        # 연결 테스트
        print("\n API 연결 테스트 중...")
        test_result = self.api.test_connection()
        if test_result.get("retCode") == 0:
            print(" API 연결 성공!")
        else:
            print(f" API 연결 실패: {test_result.get('retMsg')}")
            return

        # 학습 데이터 로드
        self.load_learning_data()

        # 거래 상태
        self.is_ready = True
        self.initial_balance = None
        self.max_balance = 0
        self.wins = 0
        self.total_trades = 0
        self.cycle_count = 0

    def get_balance(self):
        """ETH 잔고 조회 - ETHUSD 거래용 (USDT 아님!)"""
        try:
            result = self.api.get_account_balance()
            if result.get("retCode") != 0:
                return 0

            for wallet in result.get("result", {}).get("list", []):
                for coin in wallet.get("coin", []):
                    if coin["coin"] == "ETH":  # 중요: ETH 잔고 사용!
                        return float(coin["availableToWithdraw"])

            return 0

        except Exception as e:
            print(f" 잔고 조회 오류: {e}")
            return 0

    def get_positions(self):
        """ETH 포지션 조회"""
        try:
            result = self.api.get_positions("linear")
            if result.get("retCode") != 0:
                return None

            for pos in result.get("result", {}).get("list", []):
                if pos["symbol"] == self.symbol and float(pos["size"]) > 0:
                    return pos

            return None

        except Exception as e:
            print(f" 포지션 조회 오류: {e}")
            return None

    def get_current_price(self):
        """현재 ETH 가격"""
        try:
            result = self.api.get_market_data(self.symbol, "1", 1)
            if result.get("retCode") != 0:
                return None

            price_data = result["result"]["list"][0]
            return float(price_data[4])  # 종가

        except Exception as e:
            print(f" 가격 조회 오류: {e}")
            return None

    def place_order(self, side, qty):
        """주문 실행"""
        try:
            result = self.api.place_order(
                symbol=self.symbol,
                side=side,
                order_type="Market",
                qty=str(qty),
                leverage=self.strategy['leverage']
            )

            if result.get("retCode") == 0:
                print(f" 주문 성공: {side} {qty} ETH")
                return True
            else:
                print(f" 주문 실패: {result.get('retMsg')}")
                return False

        except Exception as e:
            print(f" 주문 오류: {e}")
            return False

    def encode_price_pattern(self, prices):
        """가격 패턴 인코딩"""
        if len(prices) < 2:
            return ""

        pattern = []
        for i in range(1, len(prices)):
            change_pct = (prices[i] - prices[i-1]) / prices[i-1] * 100

            if change_pct > 0.5:
                pattern.append('U')
            elif change_pct < -0.5:
                pattern.append('D')
            else:
                pattern.append('S')

        return ''.join(pattern)

    def get_pattern_confidence_boost(self, prices):
        """학습된 패턴 기반 신뢰도 부스트"""
        if len(prices) < self.min_pattern_length:
            return 0

        boost = 0
        for length in range(self.min_pattern_length, min(len(prices), self.max_pattern_length + 1)):
            pattern = self.encode_price_pattern(prices[-length:])
            if pattern in self.pattern_weights:
                weight = self.pattern_weights[pattern]
                boost += weight * 0.1

        return min(boost, 0.3)  # 최대 30% 부스트

    def learn_from_trade(self, entry_price, exit_price, position_side, recent_prices):
        """거래 결과에서 학습"""
        if position_side == "Buy":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        # 패턴 가중치 업데이트
        for length in range(self.min_pattern_length, min(len(recent_prices), self.max_pattern_length + 1)):
            pattern = self.encode_price_pattern(recent_prices[-length:])

            if pattern not in self.pattern_weights:
                self.pattern_weights[pattern] = 0

            # 수익이면 가중치 증가, 손실이면 감소
            if pnl_pct > 0:
                self.pattern_weights[pattern] += pnl_pct * 0.5
            else:
                self.pattern_weights[pattern] += pnl_pct * 0.3

            # 가중치 범위 제한
            self.pattern_weights[pattern] = max(-1, min(1, self.pattern_weights[pattern]))

        # 거래 결과 저장
        self.trade_results.append({
            'timestamp': datetime.now().isoformat(),
            'pnl_pct': pnl_pct,
            'position_side': position_side,
            'entry_price': entry_price,
            'exit_price': exit_price
        })

        # 주기적으로 학습 데이터 저장
        if len(self.trade_results) % 5 == 0:
            self.save_learning_data()

    def save_learning_data(self):
        """학습 데이터 저장"""
        try:
            data = {
                'pattern_weights': self.pattern_weights,
                'trade_results': self.trade_results[-100:]  # 최근 100개만 저장
            }
            with open('eth_learning_data.json', 'w') as f:
                json.dump(data, f, indent=2)
            print(" 학습 데이터 저장 완료")
        except Exception as e:
            print(f" 학습 데이터 저장 실패: {e}")

    def load_learning_data(self):
        """학습 데이터 로드"""
        try:
            with open('eth_learning_data.json', 'r') as f:
                data = json.load(f)
                self.pattern_weights = data.get('pattern_weights', {})
                self.trade_results = data.get('trade_results', [])
                print(f" 학습 데이터 로드: {len(self.pattern_weights)} 패턴")
        except:
            print(" 새로운 학습 시작")

    def generate_signal(self):
        """추세감지 + 학습 기반 신호 생성"""
        try:
            # 최근 가격 데이터
            result = self.api.get_market_data(self.symbol, "15", 50)
            if result.get("retCode") != 0:
                return "HOLD"

            prices = []
            for candle in result["result"]["list"]:
                prices.append(float(candle[4]))

            prices.reverse()

            # 추세 감지 신호
            trend_result = self.trend_detector.detect_multi_timeframe_reversal()
            base_confidence = trend_result['confidence']

            # 학습 기반 부스트
            pattern_boost = self.get_pattern_confidence_boost(prices)
            final_confidence = base_confidence + pattern_boost

            # 신호 결정
            if final_confidence > 0.5:
                if trend_result['consensus'] == 'UP':
                    return "Buy"
                elif trend_result['consensus'] == 'DOWN':
                    return "Sell"

            return "HOLD"

        except Exception as e:
            print(f" 신호 생성 오류: {e}")
            return "HOLD"

    def run_trading_cycle(self):
        """거래 사이클 실행"""
        self.cycle_count += 1
        print(f"\n--- 사이클 {self.cycle_count} ---")

        try:
            # 현재 잔고 조회
            current_balance = self.get_balance()

            if self.initial_balance is None:
                self.initial_balance = current_balance
                print(f" 초기 ETH 잔고: {self.initial_balance:.4f} ETH")

            # 성장률 계산
            if self.initial_balance > 0:
                growth_pct = ((current_balance - self.initial_balance) / self.initial_balance) * 100
            else:
                growth_pct = 0

            # 최대 잔고 업데이트
            if current_balance > self.max_balance:
                self.max_balance = current_balance

            # 승률 계산
            win_rate = (self.wins / max(self.total_trades, 1)) * 100

            print(f" ETH 잔고: {current_balance:.4f} ETH")
            print(f" 성장률: {growth_pct:+.1f}%")
            print(f" 최대 잔고: {self.max_balance:.4f} ETH")
            print(f" 승률: {win_rate:.0f}% ({self.wins}/{self.total_trades})")

            # 포지션 확인
            position = self.get_positions()
            current_price = self.get_current_price()

            if current_price:
                print(f" ETH 가격: ${current_price:.2f}")

            # 포지션이 있을 때
            if position:
                entry_price = float(position["avgPrice"])
                side = position["side"]
                size = float(position["size"])

                print(f" 포지션: {side} {size} ETH @ ${entry_price:.2f}")

                # 수익률 계산
                if side == "Buy":
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100

                print(f" 수익률: {pnl_pct:+.2f}%")

                # 익절/손절 체크
                if pnl_pct >= self.strategy['profit_target'] * 100:
                    print(" 익절 도달! 포지션 청산")
                    self.close_position(position)
                    self.wins += 1
                    self.total_trades += 1
                elif pnl_pct <= -self.strategy['stop_loss'] * 100:
                    print(" 손절 도달! 포지션 청산")
                    self.close_position(position)
                    self.total_trades += 1
                else:
                    # 추세 변환 체크
                    trend_result = self.trend_detector.detect_multi_timeframe_reversal(
                        current_position="LONG" if side == "Buy" else "SHORT"
                    )
                    if trend_result['should_exit']:
                        print(f" 추세 변환 감지: {trend_result['reason']}")
                        self.close_position(position)
                        if pnl_pct > 0:
                            self.wins += 1
                        self.total_trades += 1

            # 포지션이 없을 때
            else:
                print(" 포지션: NONE")

                # 신호 생성
                signal = self.generate_signal()
                print(f" 신호: {signal}")

                if signal != "HOLD" and current_balance > 0.001:  # 최소 0.001 ETH
                    # 거래 수량 계산
                    qty = current_balance * self.strategy['position_size']
                    qty = round(qty, 4)  # ETH는 소수점 4자리

                    if qty > 0.001:
                        print(f" 주문: {signal} {qty} ETH (${current_price * qty:.2f})")
                        self.place_order(signal, qty)

        except Exception as e:
            print(f" 사이클 오류: {e}")

    def close_position(self, position):
        """포지션 청산"""
        try:
            side = "Sell" if position["side"] == "Buy" else "Buy"
            qty = float(position["size"])

            result = self.api.place_order(
                symbol=self.symbol,
                side=side,
                order_type="Market",
                qty=str(qty),
                reduce_only=True
            )

            if result.get("retCode") == 0:
                print(f" 포지션 청산: {side} {qty} ETH")

                # 학습 데이터 수집
                current_price = self.get_current_price()
                if current_price:
                    self.learn_from_trade(
                        float(position["avgPrice"]),
                        current_price,
                        position["side"],
                        []  # 가격 히스토리는 나중에 수집
                    )
                return True
            else:
                print(f" 청산 실패: {result.get('retMsg')}")
                return False

        except Exception as e:
            print(f" 청산 오류: {e}")
            return False

    def set_leverage(self):
        """레버리지 설정"""
        try:
            result = self.api.set_leverage(
                symbol=self.symbol,
                leverage=self.strategy['leverage']
            )

            if result.get("retCode") == 0:
                print(f" {self.strategy['leverage']}x 레버리지 설정 완료")
                return True
            else:
                print(f" 레버리지 설정 오류: {result.get('retMsg')}")
                return False

        except Exception as e:
            print(f" 레버리지 설정 오류: {e}")
            return False

    def run(self):
        """메인 실행"""
        if not hasattr(self, 'is_ready') or not self.is_ready:
            print(" 시스템 초기화 실패!")
            return

        print("\n" + "=" * 50)
        print("ETH BYBIT LIVE TRADING 시작!")
        print(" 15분봉 87% 정확도 추세감지 + 복리효과 적용")
        print(" 추세변환 시 즉시 청산 후 새 방향 진입")
        print("  ETHUSD 실거래 중 - ETH 잔고 사용")
        print("Ctrl+C로 중단")
        print("=" * 50)

        # 레버리지 설정
        print(f"\n {self.strategy['leverage']}x 레버리지 설정 중...")
        self.set_leverage()

        try:
            while True:
                self.run_trading_cycle()
                time.sleep(30)  # 30초마다 실행

        except KeyboardInterrupt:
            print("\n\n 거래 중단됨")
            print(f" 최종 성과:")
            print(f"  - 총 거래: {self.total_trades}")
            print(f"  - 승리: {self.wins}")
            print(f"  - 승률: {(self.wins/max(self.total_trades,1))*100:.1f}%")

            # 학습 데이터 최종 저장
            self.save_learning_data()

        except Exception as e:
            print(f" 시스템 오류: {e}")

if __name__ == "__main__":
    print("  WARNING: 실제 돈으로 거래합니다!")
    print("실제 ETH 잔고로 바이비트 ETHUSD 실거래를 시작합니다.")

    trader = ETHBybitLiveTrader()
    trader.run()