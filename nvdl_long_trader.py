#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL 롱 전용 트레이더 v1.0
- NVIDIA 2x 레버리지 ETF 전용 매수 전략
- AI 기반 딥 분석으로 최적 진입점 포착
- 롱 포지션 최적화 시스템
"""

import time
import json
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

class NVDLLongAnalyzer:
    """NVDL 롱 전용 AI 분석기"""

    def __init__(self, model_name: str = "qwen2.5:7b"):
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/generate"

    def analyze_long_opportunity(self, current_price: float, price_history: List[float]) -> Dict:
        """롱 포지션 기회 분석"""

        # 가격 움직임 분석
        if len(price_history) >= 10:
            recent_trend = self._calculate_trend(price_history[-10:])
            volatility = self._calculate_volatility(price_history[-20:])
            momentum = self._calculate_momentum(price_history[-5:])
        else:
            recent_trend = 0
            volatility = 0
            momentum = 0

        # LLM 롱 분석 프롬프트
        prompt = f"""
당신은 NVDL(NVIDIA 2x 레버리지 ETF) 롱 전문 AI 트레이더입니다.
NVDL은 NVIDIA 주가의 2배 움직임을 추종하는 ETF로, 상승장에서 극대화된 수익을 목표로 합니다.

[현재 NVDL 상황]
- 현재가: ${current_price:.2f}
- 최근 추세: {recent_trend:.3f} (양수: 상승, 음수: 하락)
- 변동성: {volatility:.3f}
- 모멘텀: {momentum:.3f}
- 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[롱 전략 분석 요청]
NVDL의 현재 상황을 분석하여 롱 포지션 진입/유지/청산 결정을 내리세요:

1. 매수 신호 강도 (0-100): NVIDIA/AI 섹터 전망, 기술적 분석
2. 보유 신호 강도 (0-100): 현재 포지션 유지 권고도
3. 청산 신호 강도 (0-100): 리스크 회피 필요성
4. 신뢰도 (0-100): 분석의 확실성
5. 근거: 상세한 분석 이유

롱 전용 전략 고려사항:
- NVDL은 2x 레버리지로 높은 변동성
- NVIDIA의 AI 사업 전망
- 기술주 섹터 로테이션
- 시장 전체 리스크 온/오프

JSON 형식으로 응답:
{{
    "buy_signal": 75,
    "hold_signal": 60,
    "sell_signal": 20,
    "confidence": 85,
    "reasoning": "NVIDIA의 AI 칩 수요 급증과 데이터센터 확장으로...",
    "risk_level": "MEDIUM"
}}
"""

        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')

                # JSON 파싱
                try:
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    if start_idx != -1 and end_idx != 0:
                        json_str = response_text[start_idx:end_idx]
                        analysis = json.loads(json_str)

                        return {
                            'buy_signal': analysis.get('buy_signal', 0),
                            'hold_signal': analysis.get('hold_signal', 0),
                            'sell_signal': analysis.get('sell_signal', 0),
                            'confidence': analysis.get('confidence', 0),
                            'reasoning': analysis.get('reasoning', '분석 실패'),
                            'risk_level': analysis.get('risk_level', 'HIGH')
                        }
                except:
                    pass

        except Exception as e:
            print(f"[LLM ERROR] 분석 오류: {e}")

        return {
            'buy_signal': 0,
            'hold_signal': 0,
            'sell_signal': 0,
            'confidence': 0,
            'reasoning': '분석 실패',
            'risk_level': 'HIGH'
        }

    def _calculate_trend(self, prices: List[float]) -> float:
        """추세 계산"""
        if len(prices) < 2:
            return 0
        return (prices[-1] - prices[0]) / prices[0]

    def _calculate_volatility(self, prices: List[float]) -> float:
        """변동성 계산"""
        if len(prices) < 2:
            return 0

        changes = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        avg_change = sum(changes) / len(changes)
        variance = sum((change - avg_change) ** 2 for change in changes) / len(changes)
        return variance ** 0.5

    def _calculate_momentum(self, prices: List[float]) -> float:
        """모멘텀 계산"""
        if len(prices) < 3:
            return 0

        recent_change = (prices[-1] - prices[-2]) / prices[-2]
        prev_change = (prices[-2] - prices[-3]) / prices[-3]
        return recent_change - prev_change

class NVDLLongTrader:
    """NVDL 롱 전용 자동매매 시스템"""

    def __init__(self, analysis_interval: int = 120):
        print("=== NVDL 롱 전용 트레이더 v1.0 ===")
        print("NVIDIA 2x ETF 롱 포지션 최적화 시스템")

        # 설정 로드
        self.config = self.load_config()

        # API 설정 (동일한 KIS API 사용)
        from nvidia_stock_trader import KISAPIManager
        self.api = KISAPIManager(
            app_key=self.config['kis_app_key'],
            app_secret=self.config['kis_app_secret'],
            account_num=self.config['account_num'],
            account_code=self.config['account_code']
        )

        # NVDL 전용 분석기
        self.analyzer = NVDLLongAnalyzer()

        # 거래 설정
        self.symbol = "NVDL"  # NVIDIA 2x 레버리지 ETF
        self.analysis_interval = analysis_interval
        self.max_position_size_usd = 5000  # 최대 포지션 크기

        # 상태 관리
        self.position_quantity = 0
        self.entry_prices = []  # 분할 매수 진입가들
        self.entry_times = []
        self.price_history = []
        self.last_analysis_time = 0

        # 롱 전용 리스크 관리
        self.trailing_stop_pct = -15.0   # -15% 트레일링 스톱
        self.max_drawdown_pct = -20.0    # -20% 최대 손절
        self.pyramid_levels = 3          # 3단계 분할 매수
        self.min_confidence = 75         # 높은 신뢰도 요구

        # 성과 추적
        self.total_investment = 0
        self.realized_pnl = 0
        self.max_portfolio_value = 0

        print(f"[INIT] 종목: {self.symbol} (NVIDIA 2x ETF)")
        print(f"[INIT] 분석 주기: {self.analysis_interval}초")
        print(f"[INIT] 최대 포지션: ${self.max_position_size_usd}")
        print(f"[INIT] 롱 전용 전략 활성화")

    def load_config(self) -> Dict:
        """설정 파일 로드"""
        config_file = "nvdl_config.json"

        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # NVDL 전용 설정 생성
            default_config = {
                "kis_app_key": "YOUR_KIS_APP_KEY",
                "kis_app_secret": "YOUR_KIS_APP_SECRET",
                "account_num": "YOUR_ACCOUNT_NUMBER",
                "account_code": "01",
                "nvdl_strategy": {
                    "long_only": True,
                    "max_position_usd": 5000,
                    "pyramid_levels": 3,
                    "trailing_stop_pct": -15.0
                }
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)

            print(f"[CONFIG] {config_file} 파일을 생성했습니다.")
            return default_config

    def get_current_price(self) -> float:
        """NVDL 현재가 조회"""
        return self.api.get_current_price(self.symbol)

    def calculate_portfolio_value(self, current_price: float) -> float:
        """현재 포트폴리오 가치 계산"""
        return self.position_quantity * current_price

    def calculate_unrealized_pnl(self, current_price: float) -> Dict:
        """미실현 손익 계산"""
        if not self.entry_prices or self.position_quantity == 0:
            return {'pnl_usd': 0, 'pnl_pct': 0}

        avg_entry_price = sum(self.entry_prices) / len(self.entry_prices)
        current_value = self.position_quantity * current_price
        invested_value = self.position_quantity * avg_entry_price

        pnl_usd = current_value - invested_value
        pnl_pct = (pnl_usd / invested_value) * 100 if invested_value > 0 else 0

        return {'pnl_usd': pnl_usd, 'pnl_pct': pnl_pct}

    def execute_buy_order(self, current_price: float, allocation_pct: float = 0.33) -> bool:
        """분할 매수 실행"""
        available_cash = self.api.get_account_balance()['cash_balance']
        position_value = self.calculate_portfolio_value(current_price)

        # 최대 포지션 크기 체크
        if position_value >= self.max_position_size_usd:
            print(f"[SKIP] 최대 포지션 크기 도달: ${position_value:.0f}")
            return False

        # 매수 금액 계산
        buy_amount = min(
            available_cash * allocation_pct,
            self.max_position_size_usd - position_value
        )

        if buy_amount < 100:  # 최소 $100
            print(f"[SKIP] 매수 금액 부족: ${buy_amount:.0f}")
            return False

        quantity = int(buy_amount / current_price)

        if self.api.place_order(self.symbol, "BUY", quantity):
            self.position_quantity += quantity
            self.entry_prices.append(current_price)
            self.entry_times.append(datetime.now())
            self.total_investment += quantity * current_price

            print(f"[BUY] {quantity}주 매수 @ ${current_price:.2f}")
            print(f"[POSITION] 총 보유: {self.position_quantity}주")
            print(f"[INVESTMENT] 총 투자: ${self.total_investment:.0f}")

            return True

        return False

    def execute_sell_order(self, sell_pct: float = 1.0, reason: str = "시장 신호") -> bool:
        """매도 주문 실행"""
        if self.position_quantity <= 0:
            return False

        sell_quantity = int(self.position_quantity * sell_pct)
        current_price = self.get_current_price()

        if self.api.place_order(self.symbol, "SELL", sell_quantity):
            # 손익 계산
            if self.entry_prices:
                avg_entry = sum(self.entry_prices) / len(self.entry_prices)
                pnl_usd = (current_price - avg_entry) * sell_quantity
                pnl_pct = ((current_price - avg_entry) / avg_entry) * 100

                self.realized_pnl += pnl_usd

                print(f"[SELL] {sell_quantity}주 매도 @ ${current_price:.2f} ({reason})")
                print(f"[P&L] 수익률: {pnl_pct:+.2f}%, 수익: ${pnl_usd:+.2f}")

            # 포지션 업데이트
            self.position_quantity -= sell_quantity

            if sell_pct >= 1.0:  # 전량 매도시 초기화
                self.entry_prices = []
                self.entry_times = []
                self.total_investment = 0

            return True

        return False

    def check_trailing_stop(self, current_price: float) -> bool:
        """트레일링 스톱 체크"""
        if self.position_quantity <= 0:
            return False

        current_value = self.calculate_portfolio_value(current_price)

        # 최고 포트폴리오 가치 업데이트
        if current_value > self.max_portfolio_value:
            self.max_portfolio_value = current_value

        # 트레일링 스톱 계산
        if self.max_portfolio_value > 0:
            drawdown_pct = ((current_value - self.max_portfolio_value) / self.max_portfolio_value) * 100

            if drawdown_pct <= self.trailing_stop_pct:
                print(f"[TRAILING_STOP] 트레일링 스톱 발동: {drawdown_pct:.2f}%")
                return self.execute_sell_order(1.0, "트레일링 스톱")

        # 최대 드로우다운 체크
        unrealized_pnl = self.calculate_unrealized_pnl(current_price)
        if unrealized_pnl['pnl_pct'] <= self.max_drawdown_pct:
            print(f"[MAX_DRAWDOWN] 최대 손절: {unrealized_pnl['pnl_pct']:.2f}%")
            return self.execute_sell_order(1.0, "최대 손절")

        return False

    def make_trading_decision(self, analysis: Dict, current_price: float) -> Optional[str]:
        """롱 전용 거래 결정"""
        buy_signal = analysis.get('buy_signal', 0)
        hold_signal = analysis.get('hold_signal', 0)
        sell_signal = analysis.get('sell_signal', 0)
        confidence = analysis.get('confidence', 0)
        risk_level = analysis.get('risk_level', 'HIGH')

        print(f"[LLM] 매수: {buy_signal}, 보유: {hold_signal}, 청산: {sell_signal}")
        print(f"[LLM] 신뢰도: {confidence}, 리스크: {risk_level}")
        print(f"[LLM] 근거: {analysis.get('reasoning', 'N/A')}")

        # 신뢰도 체크
        if confidence < self.min_confidence:
            print(f"[SKIP] 신뢰도 부족: {confidence} < {self.min_confidence}")
            return None

        # 롱 전용 결정 로직
        if sell_signal >= 70 and self.position_quantity > 0:
            return "SELL_PARTIAL"  # 부분 매도
        elif sell_signal >= 85 and self.position_quantity > 0:
            return "SELL_ALL"      # 전량 매도
        elif buy_signal >= 80 and risk_level in ['LOW', 'MEDIUM']:
            return "BUY"           # 매수 신호
        elif hold_signal >= 60 and self.position_quantity > 0:
            return "HOLD"          # 보유 유지

        return None

    def execute_decision(self, decision: str, current_price: float):
        """거래 결정 실행"""
        if decision == "BUY":
            self.execute_buy_order(current_price)
        elif decision == "SELL_PARTIAL":
            self.execute_sell_order(0.5, "부분 매도")
        elif decision == "SELL_ALL":
            self.execute_sell_order(1.0, "전량 매도")
        elif decision == "HOLD":
            print("[HOLD] 포지션 유지")

    def print_status(self, current_price: float):
        """상태 출력"""
        balance = self.api.get_account_balance()
        portfolio_value = self.calculate_portfolio_value(current_price)
        unrealized_pnl = self.calculate_unrealized_pnl(current_price)

        print(f"\n[STATUS] {self.symbol}: ${current_price:.2f}")
        print(f"[POSITION] {self.position_quantity}주 보유")

        if self.position_quantity > 0:
            print(f"[PORTFOLIO] 가치: ${portfolio_value:.0f}")
            print(f"[P&L] 미실현: {unrealized_pnl['pnl_pct']:+.2f}% (${unrealized_pnl['pnl_usd']:+.0f})")
            print(f"[P&L] 실현손익: ${self.realized_pnl:+.0f}")

        print(f"[BALANCE] 현금: ${balance['cash_balance']:,.0f}")
        print(f"[BALANCE] 총자산: ${balance['total_balance']:,.0f}")

    def run(self):
        """메인 실행 루프"""
        print(f"\n[RUN] NVDL 롱 전용 트레이더 시작")
        print(f"[RUN] 분석 주기: {self.analysis_interval}초")

        try:
            while True:
                current_time = time.time()

                if current_time - self.last_analysis_time >= self.analysis_interval:
                    # 현재가 조회
                    current_price = self.get_current_price()
                    if current_price <= 0:
                        print("[ERROR] 가격 조회 실패")
                        time.sleep(10)
                        continue

                    # 가격 히스토리 업데이트
                    self.price_history.append(current_price)
                    if len(self.price_history) > 200:
                        self.price_history.pop(0)

                    # 트레일링 스톱 체크
                    if self.check_trailing_stop(current_price):
                        self.print_status(current_price)
                        time.sleep(5)
                        continue

                    # AI 분석
                    if len(self.price_history) >= 10:
                        analysis = self.analyzer.analyze_long_opportunity(
                            current_price, self.price_history
                        )

                        # 거래 결정
                        decision = self.make_trading_decision(analysis, current_price)
                        if decision:
                            self.execute_decision(decision, current_price)

                    # 상태 출력
                    self.print_status(current_price)
                    self.last_analysis_time = current_time

                time.sleep(1)

        except KeyboardInterrupt:
            print("\n[STOP] 사용자에 의해 중단됨")
        except Exception as e:
            print(f"\n[ERROR] 오류 발생: {e}")

def main():
    """메인 함수"""
    print("NVDL 롱 전용 자동매매 트레이더")
    print("="*50)

    # 분석 주기 설정
    try:
        interval = int(input("분석 주기를 입력하세요 (초, 기본값: 120): ") or "120")
    except:
        interval = 120

    trader = NVDLLongTrader(analysis_interval=interval)
    trader.run()

if __name__ == "__main__":
    main()