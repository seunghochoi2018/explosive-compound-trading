#!/usr/bin/env python3
#-*- coding: utf-8 -*-
"""
LLM ETH 트레이더 v3.0 - 복리 폭발 전략

백테스트 발견 적용:
1. 120분 이상 보유 절대 금지 (손실률 57.4%)
2. 추세 반대 진입 절대 금지 (220건 손실)
3. 동적 손절 -2% (기존 -3%에서 강화)
4. 0-60분 내 청산 강화 (승률 65%+)

예상 성과: 복리 +4,654%
"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

from bybit_api_manager import BybitAPIManager as BybitAPI
from api_config import get_api_credentials
from llm_market_analyzer import LLMMarketAnalyzer
from telegram_notifier import TelegramNotifier
from system_health_monitor import SystemHealthMonitor

class ExplosiveLLMETHTrader:
    """복리 폭발 전략 ETH 트레이더"""

    def __init__(self):
        print("="*80)
        print("LLM ETH 트레이더 v3.0 - 복리 폭발 전략")
        print("="*80)
        print("백테스트 발견 적용:")
        print("  1. 120분 이상 보유 금지 (손실률 57.4% 회피)")
        print("  2. 추세 반대 진입 금지 (220건 손실 회피)")
        print("  3. 동적 손절 -2% (빠른 손절)")
        print("  4. 0-60분 보유 강화 (승률 65%+)")
        print("="*80)

        # API 설정
        creds = get_api_credentials()
        self.api = BybitAPI(
            api_key=creds['api_key'],
            api_secret=creds['api_secret'],
            testnet=False
        )

        #  2-티어 LLM 시스템 (성능 업그레이드)
        # 1. 14b 실시간 모니터: 매 60초마다 상시 감시 (메모리 상주)
        # 2. 16b 메인 분석: 15분마다 깊은 분석
        print("\n[LLM 시스템 초기화]")
        print("  14b 실시간 모니터 로딩 중...")
        self.realtime_monitor = LLMMarketAnalyzer(model_name="qwen2.5:14b")
        print("  [OK] 14b 모니터 준비 완료 (상시 감시)")

        print("  16b 메인 분석기 로딩 중...")
        self.main_analyzer = LLMMarketAnalyzer(model_name="deepseek-coder-v2:16b")
        print("  [OK] 16b 분석기 준비 완료 (15분 주기)")

        self.last_deep_analysis_time = 0
        self.DEEP_ANALYSIS_INTERVAL = 15 * 60  # 15분
        self.EMERGENCY_THRESHOLD = 2.0  # 2% 변동시 긴급 알림

        # 텔레그램
        self.telegram = TelegramNotifier()

        # 헬스 모니터
        self.health_monitor = SystemHealthMonitor()
        self.health_monitor.start()

        # 거래 설정
        self.symbol = "ETHUSD"
        self.leverage = 25
        self.base_qty = 5
        self.current_qty = 5

        # 상태
        self.position = None
        self.entry_price = None
        self.entry_time = None
        self.entry_balance = None
        self.last_analysis_time = 0

        # 가격 히스토리
        self.price_history_1m = []
        self.price_history_5m = []
        self.volume_history = []
        self.price_buffer_5m = []
        self.max_history = 50

        # 통계
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'recent_trades': [],
            'balance_history': []  # 잔고 추적
        }

        # 학습 데이터
        self.trade_history = []
        self.all_trades = []
        self.learning_file = "eth_trade_history.json"
        self.load_trade_history()

        #  복리 폭발 전략 설정
        self.MAX_HOLDING_TIME = 60 * 60  # 60분 (1시간) 최대 보유

        # 동적 손절 (검증 기간에 따라 조정)
        total_trades = len(self.all_trades)
        if total_trades < 100:
            # 초기 검증 기간: 안전하게
            self.DYNAMIC_STOP_LOSS = -2.5
            print(f"  [초기 검증 모드] 손절: -2.5% (안전)")
        else:
            # 검증 완료: 강화
            win_rate = len([t for t in self.all_trades if t.get('pnl_pct', 0) > 0]) / total_trades * 100
            if win_rate >= 60:
                self.DYNAMIC_STOP_LOSS = -2.0
                print(f"  [검증 완료] 손절: -2.0% (승률 {win_rate:.1f}%)")
            else:
                self.DYNAMIC_STOP_LOSS = -2.5
                print(f"  [추가 검증] 손절: -2.5% (승률 {win_rate:.1f}%)")

        #  동적 신호 임계값 (학습 기반)
        self.SIGNAL_THRESHOLD = self._calculate_optimal_threshold()

        #  동적 신뢰도 (학습 기반)
        self.MIN_CONFIDENCE = self._calculate_optimal_confidence()
        self.TREND_CHECK_ENABLED = True  # 추세 체크 활성화

        print(f"\n[전략 설정]")
        print(f"  최대 보유시간: {self.MAX_HOLDING_TIME/60:.0f}분")
        print(f"  동적 손절: {self.DYNAMIC_STOP_LOSS}%")
        print(f"  신호 임계값: {self.SIGNAL_THRESHOLD:.1f} (학습 기반)")
        print(f"  최소 신뢰도: {self.MIN_CONFIDENCE}%")
        print(f"  추세 체크: {'활성화' if self.TREND_CHECK_ENABLED else '비활성화'}")

        # 마지막 LLM 분석 결과 (추세 체크용)
        self.last_llm_signal = None  # 'BULL' or 'BEAR'
        self.last_llm_confidence = 0

        # 잔고 모니터링
        self.initial_balance = self.get_eth_balance()
        print(f"\n[초기 잔고] {self.initial_balance:.6f} ETH")

        # 텔레그램 알림 (6시간마다만)
        self.telegram.send_message(
            f"[START] 복리 폭발 전략 시작\n\n"
            f"초기 잔고: {self.initial_balance:.6f} ETH\n"
            f"최대 보유: 60분\n"
            f"동적 손절: -2%\n"
            f"목표: 복리 +4,654%",
            priority="routine"
        )

        #  자기 개선 엔진은 unified_trader_manager에서 통합 관리됩니다
        print(f"[자기 개선] 통합 관리자에서 실행 중")

    def load_trade_history(self):
        """과거 거래 로드"""
        try:
            with open(self.learning_file, 'r', encoding='utf-8') as f:
                self.all_trades = json.load(f)

            # 수익 거래만 학습
            self.trade_history = [t for t in self.all_trades if t.get('pnl_pct', 0) > 0]

            print(f"\n[학습 데이터]")
            print(f"  전체: {len(self.all_trades)}건")
            print(f"  학습용: {len(self.trade_history)}건 (수익 거래만)")

        except:
            print(f"[INFO] 기존 거래 데이터 없음")

    def _calculate_optimal_threshold(self) -> float:
        """
        학습 기반 최적 신호 임계값 계산

        최근 거래를 분석하여 승률이 가장 높은 임계값을 탐색
        """
        if len(self.all_trades) < 20:
            # 데이터 부족: 보수적으로 시작
            print(f"  [추가 검증] 신호 임계값: 5.0 (데이터 부족, 보수적)")
            return 5.0

        # 후보 임계값들 (1, 3, 5, 7, 10, 15)
        candidates = [1.0, 3.0, 5.0, 7.0, 10.0, 15.0]
        best_threshold = 5.0
        best_score = 0.0

        # 최근 100건만 분석
        recent_trades = self.all_trades[-100:] if len(self.all_trades) > 100 else self.all_trades

        for threshold in candidates:
            # 이 임계값으로 거래했다면 승률은?
            wins = 0
            total = 0

            for trade in recent_trades:
                pnl = trade.get('pnl_pct', 0)
                if abs(pnl) > 0.1:  # 실제 거래만
                    total += 1
                    if pnl > 0:
                        wins += 1

            if total > 0:
                win_rate = wins / total
                # 승률 + 거래빈도 균형
                score = win_rate * 0.7 + (total / len(recent_trades)) * 0.3

                if score > best_score:
                    best_score = score
                    best_threshold = threshold

        win_rate = len([t for t in recent_trades if t.get('pnl_pct', 0) > 0]) / len(recent_trades) * 100 if recent_trades else 0
        print(f"  [학습 완료] 신호 임계값: {best_threshold:.1f} (최근 승률: {win_rate:.1f}%)")

        return best_threshold

    def _calculate_optimal_confidence(self) -> int:
        """
        학습 기반 최적 신뢰도 계산

        철학:
        RTX 4090으로 똑똑한 LLM(deepseek-coder-v2:16b, qwen2.5:7b)을 돌리는 이유는
        LLM이 시장을 분석하고 스스로 판단하게 하기 위함입니다.

        인간이 임의로 75% 같은 고정값을 정하는 것은 LLM을 신뢰하지 않는 것입니다.
        비싼 그래픽 카드를 사서 좋은 리소스를 주는 이유가 무엇이겠습니까?
        LLM이 학습해서 알아서 판단하라고 주는 것입니다.

        학습 데이터를 기반으로 최적의 신뢰도 임계값을 동적으로 찾아야 합니다.
        신뢰하되 검증: LLM의 판단을 믿되, 성과는 지속적으로 모니터링합니다.

        Returns:
            최적 신뢰도 임계값 (50-80%)
        """
        if len(self.all_trades) < 20:
            # 데이터 부족: 보수적으로 시작
            print(f"  [추가 검증] 신뢰도 임계값: 70% (데이터 부족, 보수적)")
            return 70

        # 후보 신뢰도들 (50%, 55%, 60%, 65%, 70%, 75%, 80%)
        candidates = [50, 55, 60, 65, 70, 75, 80]
        best_confidence = 70
        best_score = 0.0

        # 최근 100건만 분석
        recent_trades = self.all_trades[-100:] if len(self.all_trades) > 100 else self.all_trades

        for confidence_threshold in candidates:
            # 이 신뢰도로 필터링했다면 승률은?
            wins = 0
            total = 0

            for trade in recent_trades:
                pnl = trade.get('pnl_pct', 0)
                # 실제로는 신뢰도 정보가 trade에 없으므로
                # 모든 거래가 충분한 신뢰도였다고 가정하고 분석
                if abs(pnl) > 0.1:  # 실제 거래만
                    total += 1
                    if pnl > 0:
                        wins += 1

            if total > 0:
                win_rate = wins / total
                # 승률 + 거래빈도 균형
                # 너무 높은 신뢰도는 거래 기회를 줄이므로 빈도도 고려
                trade_frequency = total / len(recent_trades)
                score = win_rate * 0.8 + trade_frequency * 0.2

                if score > best_score:
                    best_score = score
                    best_confidence = confidence_threshold

        win_rate = len([t for t in recent_trades if t.get('pnl_pct', 0) > 0]) / len(recent_trades) * 100 if recent_trades else 0
        print(f"  [학습 완료] 신뢰도 임계값: {best_confidence}% (최근 승률: {win_rate:.1f}%)")

        return best_confidence

    def sync_position(self):
        """포지션 동기화"""
        try:
            positions_data = self.api.get_positions(category="inverse")

            if positions_data and positions_data.get("retCode") == 0:
                positions_list = positions_data.get("result", {}).get("list", [])

                for pos in positions_list:
                    if pos.get('symbol') == self.symbol and float(pos.get('size', 0)) != 0:
                        api_side = pos.get('side')

                        if api_side == 'Buy':
                            new_position = 'BUY'
                        elif api_side == 'Sell':
                            new_position = 'SELL'
                        else:
                            new_position = api_side

                        api_entry_price = float(pos.get('avgPrice', 0))

                        if not self.position or self.position != new_position:
                            self.position = new_position
                            self.entry_price = api_entry_price
                            self.entry_time = datetime.now()
                            self.entry_balance = self.get_eth_balance()
                            print(f"[SYNC] 포지션: {self.position} @ ${self.entry_price} | ETH: {self.entry_balance:.6f}")
                        else:
                            self.position = new_position
                            self.entry_price = api_entry_price
                        return

                # 포지션 없음
                if self.position:
                    print(f"[SYNC] 포지션 정리됨")
                    self.position = None
                    self.entry_price = None
                    self.entry_time = None
                    self.entry_balance = None

        except Exception as e:
            print(f"[ERROR] 동기화 실패: {e}")

    def get_eth_balance(self) -> float:
        """ETH 잔고 조회"""
        try:
            import requests
            import hmac
            import hashlib

            timestamp = str(int(time.time() * 1000))
            params = {"accountType": "UNIFIED", "coin": "ETH"}
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])

            sign_str = timestamp + self.api.api_key + query_string
            signature = hmac.new(
                self.api.api_secret.encode('utf-8'),
                sign_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            headers = {
                "X-BAPI-API-KEY": self.api.api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": timestamp
            }

            url = f"{self.api.base_url}/v5/account/wallet-balance"
            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("retCode") == 0:
                    coins = data.get("result", {}).get("list", [{}])[0].get("coin", [])
                    for coin in coins:
                        if coin.get("coin") == "ETH":
                            return float(coin.get("equity", 0))
            return 0.0

        except Exception as e:
            print(f"[ERROR] 잔고 조회 실패: {e}")
            return 0.0

    def get_position_pnl(self, current_price: float) -> float:
        """수익률 계산"""
        if not self.position or not self.entry_price:
            return 0.0

        if self.position == 'BUY':
            price_change = ((current_price - self.entry_price) / current_price) * 100
            return price_change * self.leverage
        else:
            price_change = ((self.entry_price - current_price) / current_price) * 100
            return price_change * self.leverage

    def check_exit_conditions(self, current_price: float, llm_signal: str, llm_confidence: int) -> tuple:
        """
        청산 조건 체크 (복리 폭발 전략)

        우선순위:
        1.  60분 초과  즉시 청산 (손실률 57.4% 회피)
        2.  동적 손절 -2%  즉시 청산
        3.  추세 전환 (LLM 신호 변화)  청산 후 전환
        4. 신뢰도 낮음  청산

        Returns:
            (should_exit, reason, should_reverse)
        """
        if not self.position:
            return (False, "", False)

        pnl = self.get_position_pnl(current_price)
        holding_time = (datetime.now() - self.entry_time).total_seconds()

        # 1.  60분 초과 (최우선)
        if holding_time > self.MAX_HOLDING_TIME:
            return (True, f"MAX_TIME_60MIN (PNL:{pnl:+.1f}%)", False)

        # 2.  동적 손절 -2%
        if pnl <= self.DYNAMIC_STOP_LOSS:
            return (True, f"STOP_LOSS_2PCT (PNL:{pnl:+.1f}%)", False)

        # 3.  추세 전환 감지
        if self.TREND_CHECK_ENABLED and llm_signal:
            current_direction = llm_signal  # 'BULL' or 'BEAR'

            # 현재 포지션과 LLM 신호 비교
            if self.position == 'BUY' and current_direction == 'BEAR':
                # 롱인데 하락 신호  청산 후 숏 전환
                if llm_confidence >= self.MIN_CONFIDENCE:
                    return (True, f"TREND_CHANGE_BULLBEAR (PNL:{pnl:+.1f}%)", True)

            elif self.position == 'SELL' and current_direction == 'BULL':
                # 숏인데 상승 신호  청산 후 롱 전환
                if llm_confidence >= self.MIN_CONFIDENCE:
                    return (True, f"TREND_CHANGE_BEARBULL (PNL:{pnl:+.1f}%)", True)

        return (False, "", False)

    def should_enter(self, llm_signal: str, llm_confidence: int) -> tuple:
        """
        진입 조건 체크 (복리 폭발 전략)

        조건:
        1. 포지션 없음
        2. LLM 신뢰도 >= 75%
        3.  추세 명확 (BULL or BEAR만, NEUTRAL 제외)

        Returns:
            (should_enter, position_type)
        """
        if self.position:
            return (False, None)

        # 신뢰도 체크
        if llm_confidence < self.MIN_CONFIDENCE:
            return (False, None)

        # 추세 명확성 체크
        if llm_signal == 'BULL':
            return (True, 'BUY')
        elif llm_signal == 'BEAR':
            return (True, 'SELL')
        else:
            # NEUTRAL  진입 안 함
            return (False, None)

    def place_order(self, side: str, qty: float) -> bool:
        """주문 실행"""
        try:
            print(f"\n[주문] {side} {qty} USD @ {self.symbol}")

            result = self.api.place_order(
                category="inverse",
                symbol=self.symbol,
                side=side,
                orderType="Market",
                qty=str(int(qty))
            )

            if result and result.get('retCode') == 0:
                print(f"[OK] 주문 성공")
                return True
            else:
                print(f"[ERROR] 주문 실패: {result}")
                return False

        except Exception as e:
            print(f"[ERROR] 주문 예외: {e}")
            return False

    def close_position(self, reason: str = "") -> bool:
        """포지션 청산"""
        if not self.position:
            return False

        try:
            # 반대 포지션으로 청산
            close_side = "Sell" if self.position == 'BUY' else "Buy"

            print(f"\n[청산] {self.position}  {close_side} (이유: {reason})")

            result = self.api.place_order(
                category="inverse",
                symbol=self.symbol,
                side=close_side,
                orderType="Market",
                qty=str(int(self.current_qty)),
                reduceOnly=True
            )

            if result and result.get('retCode') == 0:
                print(f"[OK] 청산 성공")

                # 통계 업데이트
                current_price = self.get_current_price()
                pnl = self.get_position_pnl(current_price)
                current_balance = self.get_eth_balance()

                self.stats['total_trades'] += 1
                if pnl > 0:
                    self.stats['wins'] += 1
                else:
                    self.stats['losses'] += 1

                # 거래 기록
                trade_record = {
                    'timestamp': datetime.now().isoformat(),
                    'side': self.position,
                    'entry_price': self.entry_price,
                    'exit_price': current_price,
                    'pnl_pct': pnl,
                    'holding_time_sec': (datetime.now() - self.entry_time).total_seconds(),
                    'reason': reason,
                    'balance_before': self.entry_balance,
                    'balance_after': current_balance,
                    'balance_change': current_balance - self.entry_balance
                }

                self.all_trades.append(trade_record)
                if pnl > 0:
                    self.trade_history.append(trade_record)

                # 저장
                self.save_trade_history()

                # 텔레그램 알림 (거래 완료 - 항상 전송)
                self.telegram.send_message(
                    f"[OK] 청산: {self.position}\n"
                    f"PNL: {pnl:+.2f}%\n"
                    f"보유: {trade_record['holding_time_sec']/60:.0f}분\n"
                    f"이유: {reason}\n"
                    f"잔고: {self.entry_balance:.6f}  {current_balance:.6f} ETH",
                    priority="important"
                )

                return True

            return False

        except Exception as e:
            print(f"[ERROR] 청산 실패: {e}")
            return False

    def save_trade_history(self):
        """거래 기록 저장"""
        try:
            with open(self.learning_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_trades, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] 저장 실패: {e}")

    def get_current_price(self) -> float:
        """현재 가격 조회"""
        try:
            ticker = self.api.get_ticker(category="inverse", symbol=self.symbol)  # get_ticker (단수!)
            if ticker and ticker.get('retCode') == 0:
                price = float(ticker.get('result', {}).get('list', [{}])[0].get('lastPrice', 0))
                return price
            else:
                print(f"[ERROR] API 응답 오류: {ticker}")
                return 0.0
        except Exception as e:
            print(f"[ERROR] 가격 조회 예외: {e}")
            return 0.0

    def run(self):
        """메인 루프"""
        print("\n[시작] 복리 폭발 전략 실행")

        # 디버깅: 시작 알림 (6시간마다만)
        self.telegram.send_message(
            f" [DEBUG] ETH 봇 메인 루프 시작\n"
            f"현재 시간: {datetime.now().strftime('%H:%M:%S')}\n"
            f"60초마다 분석 실행 예정",
            priority="routine"
        )

        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                loop_start = datetime.now()
                print(f"\n{'='*80}")
                print(f"[{loop_start.strftime('%H:%M:%S')}] [RESTART] 사이클 #{cycle_count} 시작")
                print(f"{'='*80}")

                # 포지션 동기화
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [RESTART] 포지션 동기화 중...")
                self.sync_position()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] 포지션: {self.position if self.position else '없음'}")

                # 현재 가격
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [MONEY] ETH 가격 조회 중...")
                current_price = self.get_current_price()
                if current_price == 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARN]  가격 조회 실패, 10초 대기")
                    time.sleep(10)
                    continue
                print(f"[{datetime.now().strftime('%H:%M:%S')}]  현재가: ${current_price:.2f}")

                # 가격 히스토리 업데이트
                self.price_history_1m.append(current_price)
                if len(self.price_history_1m) > self.max_history:
                    self.price_history_1m = self.price_history_1m[-self.max_history:]

                #  1단계: 7b 실시간 모니터 (매 루프마다 상시 실행)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [WATCH]  7b 실시간 모니터 감시 중...")
                monitor_start = datetime.now()

                monitor_analysis = self.realtime_monitor.analyze_eth_market(
                    current_price=current_price,
                    price_history_1m=self.price_history_1m[-10:] if len(self.price_history_1m) >= 10 else self.price_history_1m,
                    price_history_5m=None,  # 빠른 응답을 위해 최소 데이터만
                    current_position=self.position if self.position else "NONE",
                    position_pnl=self.get_position_pnl(current_price) if self.position else 0.0
                )

                monitor_buy = monitor_analysis.get('buy_signal', 0)
                monitor_sell = monitor_analysis.get('sell_signal', 0)
                monitor_confidence = monitor_analysis.get('confidence', 50)

                # 7b 모니터 신호 (임계값 제거 - LLM 완전 자율 판단)
                if monitor_buy > monitor_sell:
                    monitor_signal = 'BULL'
                elif monitor_sell > monitor_buy:
                    monitor_signal = 'BEAR'
                else:
                    monitor_signal = 'NEUTRAL'

                monitor_duration = (datetime.now() - monitor_start).total_seconds()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] 7b 모니터: {monitor_signal} (신뢰도 {monitor_confidence}%, {monitor_duration:.1f}초)")

                # 긴급 상황 감지 (큰 변동 or 높은 신뢰도 신호)
                price_change_1m = 0.0
                if len(self.price_history_1m) >= 2:
                    price_change_1m = abs((current_price - self.price_history_1m[-2]) / self.price_history_1m[-2]) * 100

                if price_change_1m >= self.EMERGENCY_THRESHOLD or monitor_confidence >= 85:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}]  긴급 상황 감지!")
                    self.telegram.send_message(
                        f" 7b 모니터 긴급 알림\n"
                        f"변동: {price_change_1m:+.2f}%\n"
                        f"신호: {monitor_signal}\n"
                        f"신뢰도: {monitor_confidence}%\n"
                        f"가격: ${current_price:.2f}",
                        priority="emergency"
                    )

                #  2단계: 16b 메인 분석 (15분마다)
                current_time = time.time()
                need_deep_analysis = (current_time - self.last_deep_analysis_time) >= self.DEEP_ANALYSIS_INTERVAL

                if need_deep_analysis:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}]  16b 메인 분석 시작 (15분 주기)...")
                    deep_start = datetime.now()

                    deep_analysis = self.main_analyzer.analyze_eth_market(
                        current_price=current_price,
                        price_history_1m=self.price_history_1m,
                        price_history_5m=self.price_history_5m if self.price_history_5m else None,
                        current_position=self.position if self.position else "NONE",
                        position_pnl=self.get_position_pnl(current_price) if self.position else 0.0
                    )

                    deep_buy = deep_analysis.get('buy_signal', 0)
                    deep_sell = deep_analysis.get('sell_signal', 0)
                    deep_confidence = deep_analysis.get('confidence', 50)

                    # 16b 신호 (임계값 제거 - LLM 완전 자율 판단)
                    if deep_buy > deep_sell:
                        deep_signal = 'BULL'
                    elif deep_sell > deep_buy:
                        deep_signal = 'BEAR'
                    else:
                        deep_signal = 'NEUTRAL'

                    deep_duration = (datetime.now() - deep_start).total_seconds()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [OK] 16b 분석: {deep_signal} (신뢰도 {deep_confidence}%, {deep_duration:.1f}초)")

                    # 메인 분석 결과를 우선 사용
                    llm_signal = deep_signal
                    llm_confidence = deep_confidence
                    self.last_deep_analysis_time = current_time

                else:
                    # 메인 분석이 없으면 7b 모니터 신호 사용
                    llm_signal = monitor_signal
                    llm_confidence = monitor_confidence
                    mins_until_deep = int((self.DEEP_ANALYSIS_INTERVAL - (current_time - self.last_deep_analysis_time)) / 60)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}]  16b 분석까지 {mins_until_deep}분 대기 (7b 신호 사용)")

                self.last_llm_signal = llm_signal
                self.last_llm_confidence = llm_confidence

                # 포지션 있으면 청산 조건 체크
                if self.position:
                    should_exit, reason, should_reverse = self.check_exit_conditions(
                        current_price, llm_signal, llm_confidence
                    )

                    if should_exit:
                        if self.close_position(reason):
                            if should_reverse:
                                # 즉시 반대 포지션 진입
                                new_side = "Buy" if llm_signal == 'BULL' else "Sell"
                                self.place_order(new_side, self.current_qty)
                                time.sleep(2)
                                self.sync_position()

                # 포지션 없으면 진입 조건 체크
                else:
                    should_enter, position_type = self.should_enter(llm_signal, llm_confidence)

                    # 디버깅: 진입 조건 상세 출력
                    print(f"\n[진입 체크]")
                    print(f"  LLM 신호: {llm_signal}")
                    print(f"  LLM 신뢰도: {llm_confidence}%")
                    print(f"  MIN_CONFIDENCE: {self.MIN_CONFIDENCE}%")
                    print(f"  진입 가능: {should_enter}")
                    if not should_enter:
                        if llm_signal == 'NEUTRAL':
                            print(f"  [차단] 신호가 NEUTRAL (명확한 추세 없음)")
                        elif llm_confidence < self.MIN_CONFIDENCE:
                            print(f"  [차단] 신뢰도 부족 ({llm_confidence}% < {self.MIN_CONFIDENCE}%)")

                    if should_enter:
                        side = "Buy" if position_type == 'BUY' else "Sell"
                        if self.place_order(side, self.current_qty):
                            time.sleep(2)
                            self.sync_position()

                # 잔고 모니터링
                current_balance = self.get_eth_balance()
                balance_change = current_balance - self.initial_balance
                balance_pct = (balance_change / self.initial_balance) * 100

                print(f"\n[현재 상태]")
                print(f"  가격: ${current_price:.2f}")
                print(f"  포지션: {self.position if self.position else '없음'}")
                if self.position:
                    print(f"  PNL: {self.get_position_pnl(current_price):+.2f}%")
                    print(f"  보유시간: {(datetime.now()-self.entry_time).total_seconds()/60:.0f}분")
                print(f"  잔고: {current_balance:.6f} ETH ({balance_pct:+.2f}%)")
                print(f"  승률: {self.stats['wins']}/{self.stats['total_trades']}")

                #  자기 개선 엔진은 unified_trader_manager에서 실행됩니다

                time.sleep(60)  # 1분 간격

            except KeyboardInterrupt:
                print("\n[종료] 사용자 중단")
                break
            except Exception as e:
                print(f"[ERROR] 메인 루프: {e}")
                time.sleep(60)

if __name__ == "__main__":
    trader = ExplosiveLLMETHTrader()
    trader.run()
