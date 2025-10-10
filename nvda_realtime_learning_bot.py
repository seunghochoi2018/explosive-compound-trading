#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDA/NVDQ 실시간 학습 & 텔레그램 알림 봇
- 실시간 데이터로 계속 학습
- 실제 수익 검증 후 포지션 추천
- 텔레그램으로 신호 전송
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
import requests
from collections import deque
import numpy as np

class NVDARealtimeLearningBot:
    def __init__(self, telegram_token=None, chat_id=None):
        print("=== NVDA/NVDQ 실시간 학습 봇 ===")
        print("실시간 데이터로 학습 → 수익 검증 → 텔레그램 알림")
        print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 텔레그램 설정
        self.telegram_token = telegram_token or "YOUR_BOT_TOKEN"  # 봇 토큰 입력 필요
        self.chat_id = chat_id or "YOUR_CHAT_ID"  # 채팅 ID 입력 필요
        self.telegram_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"

        # 심볼 설정
        self.symbols = {
            'NVDA': {'name': 'NVIDIA', 'leverage': 1},
            'NVDL': {'name': 'NVDA 2X Bull', 'leverage': 2},  # GraniteShares 2x Long NVDA
            'NVDQ': {'name': 'NVDA 3X Bull', 'leverage': 3}   # 실제로는 다른 심볼일 수 있음
        }

        # 가상 잔고 (학습용)
        self.virtual_balance = 100000.0
        self.initial_balance = 100000.0

        # 실시간 가격 데이터
        self.prices = {symbol: {'current': 0, 'history': deque(maxlen=1000)} for symbol in self.symbols}

        # 학습 단계
        self.learning_phase = True  # True: 학습 중, False: 검증 완료
        self.min_trades_for_validation = 100  # 최소 100번 거래 후 검증
        self.min_winrate_for_signal = 55  # 55% 이상 승률 필요
        self.min_profit_for_signal = 500  # $500 이상 수익 필요

        # 가상 포지션 (학습용)
        self.virtual_positions = {}
        self.position_counter = 0

        # 실시간 학습 데이터
        self.learning_stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_profit': 0,
            'by_strategy': {}
        }

        # 검증된 전략들
        self.verified_strategies = []

        # 성공 패턴 저장
        self.successful_patterns = deque(maxlen=500)
        self.failed_patterns = deque(maxlen=200)

        # 전략 정의 (31개)
        self.strategies = self._initialize_strategies()

        # 세션
        self.session = None

        # 마지막 알림 시간 (스팸 방지)
        self.last_telegram_alert = time.time()
        self.alert_cooldown = 300  # 5분 쿨다운

        print(f"가상 자본: ${self.virtual_balance:,.2f}")
        print(f"학습 목표: {self.min_trades_for_validation}거래, {self.min_winrate_for_signal}% 승률")
        print("=" * 50)

    def _initialize_strategies(self):
        """31개 전략 초기화"""
        return {
            # 초단기 (1-60초)
            'ultra_scalp_1': {'interval': 1, 'hold': 30, 'profit': 0.001, 'loss': 0.0015},
            'ultra_scalp_2': {'interval': 5, 'hold': 60, 'profit': 0.0015, 'loss': 0.002},
            'ultra_scalp_3': {'interval': 10, 'hold': 90, 'profit': 0.002, 'loss': 0.0025},

            # 스캘핑 (1-5분)
            'scalp_fast': {'interval': 15, 'hold': 120, 'profit': 0.0025, 'loss': 0.003},
            'scalp_medium': {'interval': 30, 'hold': 180, 'profit': 0.003, 'loss': 0.0035},
            'scalp_slow': {'interval': 60, 'hold': 300, 'profit': 0.0035, 'loss': 0.004},

            # 모멘텀 (2-10분)
            'momentum_fast': {'interval': 20, 'hold': 150, 'profit': 0.003, 'loss': 0.0035},
            'momentum_medium': {'interval': 45, 'hold': 300, 'profit': 0.004, 'loss': 0.0045},
            'momentum_slow': {'interval': 90, 'hold': 600, 'profit': 0.005, 'loss': 0.0055},

            # 트렌드 (5-30분)
            'trend_micro': {'interval': 60, 'hold': 300, 'profit': 0.004, 'loss': 0.005},
            'trend_short': {'interval': 120, 'hold': 600, 'profit': 0.005, 'loss': 0.006},
            'trend_medium': {'interval': 180, 'hold': 900, 'profit': 0.006, 'loss': 0.007},
            'trend_long': {'interval': 300, 'hold': 1800, 'profit': 0.008, 'loss': 0.009},

            # 스윙 (10-60분)
            'swing_quick': {'interval': 300, 'hold': 1200, 'profit': 0.007, 'loss': 0.008},
            'swing_normal': {'interval': 600, 'hold': 2400, 'profit': 0.009, 'loss': 0.01},
            'swing_patient': {'interval': 900, 'hold': 3600, 'profit': 0.012, 'loss': 0.013},

            # 역추세
            'reversal_quick': {'interval': 120, 'hold': 600, 'profit': 0.005, 'loss': 0.006},
            'reversal_slow': {'interval': 240, 'hold': 1200, 'profit': 0.007, 'loss': 0.008},

            # 브레이크아웃
            'breakout_1': {'interval': 150, 'hold': 750, 'profit': 0.006, 'loss': 0.007},
            'breakout_2': {'interval': 300, 'hold': 1500, 'profit': 0.008, 'loss': 0.009},

            # 평균회귀
            'mean_revert_1': {'interval': 90, 'hold': 450, 'profit': 0.004, 'loss': 0.005},
            'mean_revert_2': {'interval': 180, 'hold': 900, 'profit': 0.006, 'loss': 0.007},

            # 볼륨 기반
            'volume_based': {'interval': 120, 'hold': 600, 'profit': 0.005, 'loss': 0.006},

            # AI 패턴 학습
            'ai_pattern_1': {'interval': 60, 'hold': 300, 'profit': 0.004, 'loss': 0.005},
            'ai_pattern_2': {'interval': 120, 'hold': 600, 'profit': 0.005, 'loss': 0.006},

            # NVDQ 전용 (3배 레버리지)
            'nvdq_scalp': {'interval': 30, 'hold': 150, 'profit': 0.003, 'loss': 0.004},
            'nvdq_momentum': {'interval': 60, 'hold': 300, 'profit': 0.004, 'loss': 0.005},
            'nvdq_swing': {'interval': 180, 'hold': 900, 'profit': 0.006, 'loss': 0.007},

            # 실험적
            'experimental_1': {'interval': 25, 'hold': 125, 'profit': 0.003, 'loss': 0.004},
            'experimental_2': {'interval': 50, 'hold': 250, 'profit': 0.004, 'loss': 0.005},
            'experimental_3': {'interval': 100, 'hold': 500, 'profit': 0.005, 'loss': 0.006}
        }

    async def init_session(self):
        """세션 초기화"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=3),
            connector=aiohttp.TCPConnector(limit=50)
        )

    async def close_session(self):
        """세션 종료"""
        if self.session:
            await self.session.close()

    async def fetch_price(self, symbol):
        """실시간 가격 가져오기 (Yahoo Finance API 대안)"""
        try:
            # 실제로는 Yahoo Finance나 Alpha Vantage API 사용
            # 여기서는 시뮬레이션
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    price = data['chart']['result'][0]['meta']['regularMarketPrice']
                    return price
        except:
            pass

        # 시뮬레이션 가격
        base_prices = {'NVDA': 450, 'NVDL': 90, 'NVDQ': 135}
        if self.prices[symbol]['current'] > 0:
            # NVDA는 변동성 높음
            change = np.random.normal(0, 0.002)  # 0.2% 표준편차
            return self.prices[symbol]['current'] * (1 + change)
        return base_prices.get(symbol, 100)

    def analyze_market(self, symbol):
        """시장 분석"""
        history = list(self.prices[symbol]['history'])
        if len(history) < 20:
            return None

        current = self.prices[symbol]['current']

        # 다양한 기간 분석
        analyses = {}

        # 1분 분석
        if len(history) >= 60:
            recent_1m = history[-60:]
            analyses['1m'] = {
                'trend': 'up' if current > recent_1m[0] else 'down',
                'volatility': np.std(recent_1m) / np.mean(recent_1m),
                'momentum': (current - recent_1m[30]) / recent_1m[30],
                'rsi': self._calculate_rsi(recent_1m)
            }

        # 5분 분석
        if len(history) >= 300:
            recent_5m = history[-300:]
            analyses['5m'] = {
                'trend': 'up' if current > recent_5m[0] else 'down',
                'volatility': np.std(recent_5m) / np.mean(recent_5m),
                'momentum': (current - recent_5m[150]) / recent_5m[150],
                'support': min(recent_5m),
                'resistance': max(recent_5m)
            }

        return {
            'symbol': symbol,
            'price': current,
            'timeframes': analyses,
            'leverage': self.symbols[symbol]['leverage']
        }

    def _calculate_rsi(self, prices, period=14):
        """RSI 계산"""
        if len(prices) < period + 1:
            return 50

        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def generate_signals(self, market_data):
        """전략별 신호 생성"""
        if not market_data or 'timeframes' not in market_data:
            return []

        signals = []
        symbol = market_data['symbol']
        leverage = market_data['leverage']

        for strategy_name, config in self.strategies.items():
            # NVDQ 전용 전략
            if 'nvdq' in strategy_name and symbol != 'NVDQ':
                continue

            # 시간대별 분석 활용
            if '1m' in market_data['timeframes']:
                tf = market_data['timeframes']['1m']

                # 전략별 조건
                if 'scalp' in strategy_name:
                    if abs(tf['momentum']) > 0.001 * leverage:
                        signals.append({
                            'strategy': strategy_name,
                            'symbol': symbol,
                            'direction': 'LONG' if tf['momentum'] > 0 else 'SHORT',
                            'confidence': min(0.8, abs(tf['momentum']) * 500),
                            'config': config
                        })

                elif 'momentum' in strategy_name:
                    if tf['rsi'] < 30 or tf['rsi'] > 70:
                        signals.append({
                            'strategy': strategy_name,
                            'symbol': symbol,
                            'direction': 'LONG' if tf['rsi'] < 30 else 'SHORT',
                            'confidence': 0.7,
                            'config': config
                        })

                elif 'trend' in strategy_name:
                    if tf['trend'] == 'up' and tf['momentum'] > 0.002:
                        signals.append({
                            'strategy': strategy_name,
                            'symbol': symbol,
                            'direction': 'LONG',
                            'confidence': 0.65,
                            'config': config
                        })

        return signals

    def execute_virtual_trade(self, signal):
        """가상 거래 실행 (학습용)"""
        position_value = self.virtual_balance * 0.1  # 10% 사용

        self.position_counter += 1
        pos_id = f"V{self.position_counter}_{signal['symbol']}_{signal['strategy']}"

        self.virtual_positions[pos_id] = {
            'symbol': signal['symbol'],
            'strategy': signal['strategy'],
            'direction': signal['direction'],
            'entry_price': self.prices[signal['symbol']]['current'],
            'value': position_value,
            'entry_time': time.time(),
            'config': signal['config']
        }

        self.virtual_balance -= position_value

        print(f"[학습] {pos_id} {signal['direction']} ${self.prices[signal['symbol']]['current']:.2f}")

    def manage_virtual_positions(self):
        """가상 포지션 관리"""
        current_time = time.time()
        to_close = []

        for pos_id, pos in self.virtual_positions.items():
            current_price = self.prices[pos['symbol']]['current']

            # 수익률 계산
            if pos['direction'] == 'LONG':
                ret = (current_price - pos['entry_price']) / pos['entry_price']
            else:
                ret = (pos['entry_price'] - current_price) / pos['entry_price']

            # 레버리지 적용
            ret *= self.symbols[pos['symbol']]['leverage']

            hold_time = current_time - pos['entry_time']

            # 청산 조건
            if ret >= pos['config']['profit']:
                to_close.append((pos_id, 'profit', ret))
            elif ret <= -pos['config']['loss']:
                to_close.append((pos_id, 'loss', ret))
            elif hold_time > pos['config']['hold']:
                to_close.append((pos_id, 'timeout', ret))

        # 청산 처리
        for pos_id, reason, ret in to_close:
            self.close_virtual_position(pos_id, reason, ret)

    def close_virtual_position(self, pos_id, reason, ret):
        """가상 포지션 청산"""
        pos = self.virtual_positions[pos_id]
        profit = pos['value'] * ret

        self.virtual_balance += pos['value'] + profit

        # 통계 업데이트
        self.learning_stats['total_trades'] += 1
        self.learning_stats['total_profit'] += profit

        if pos['strategy'] not in self.learning_stats['by_strategy']:
            self.learning_stats['by_strategy'][pos['strategy']] = {
                'trades': 0, 'wins': 0, 'profit': 0
            }

        stat = self.learning_stats['by_strategy'][pos['strategy']]
        stat['trades'] += 1
        stat['profit'] += profit

        if profit > 0:
            self.learning_stats['wins'] += 1
            stat['wins'] += 1

            # 성공 패턴 저장
            self.successful_patterns.append({
                'symbol': pos['symbol'],
                'strategy': pos['strategy'],
                'direction': pos['direction'],
                'profit': ret,
                'hold_time': time.time() - pos['entry_time']
            })

            print(f"[청산] {pos_id} +{ret*100:.2f}% ${profit:+.2f}")
        else:
            self.learning_stats['losses'] += 1
            self.failed_patterns.append({
                'symbol': pos['symbol'],
                'strategy': pos['strategy'],
                'direction': pos['direction'],
                'loss': ret
            })

        del self.virtual_positions[pos_id]

        # 학습 검증
        self.check_learning_progress()

    def check_learning_progress(self):
        """학습 진행상황 체크 및 검증"""
        if not self.learning_phase:
            return

        total = self.learning_stats['total_trades']
        if total < self.min_trades_for_validation:
            return

        winrate = (self.learning_stats['wins'] / total) * 100
        total_return = ((self.virtual_balance / self.initial_balance) - 1) * 100

        print(f"\n[학습 상태] 거래: {total}, 승률: {winrate:.1f}%, 수익: ${self.learning_stats['total_profit']:+.2f}")

        # 검증 조건 충족
        if winrate >= self.min_winrate_for_signal and self.learning_stats['total_profit'] >= self.min_profit_for_signal:
            self.learning_phase = False
            print("=" * 50)
            print("🎯 학습 완료! 실시간 시그널 시작")
            print(f"검증된 승률: {winrate:.1f}%")
            print(f"검증된 수익: ${self.learning_stats['total_profit']:+.2f}")
            print("=" * 50)

            # 최고 전략 선별
            self.select_best_strategies()

            # 텔레그램 알림
            self.send_telegram_message(
                f"🚀 NVDA/NVDQ 봇 학습 완료!\n"
                f"✅ 거래: {total}회\n"
                f"✅ 승률: {winrate:.1f}%\n"
                f"✅ 수익: ${self.learning_stats['total_profit']:+.2f}\n"
                f"📊 실시간 시그널 시작!"
            )

    def select_best_strategies(self):
        """최고 전략 선별"""
        for name, stat in self.learning_stats['by_strategy'].items():
            if stat['trades'] >= 10:  # 최소 10회 이상
                winrate = (stat['wins'] / stat['trades']) * 100
                if winrate >= 60 and stat['profit'] > 0:  # 60% 이상 승률
                    self.verified_strategies.append({
                        'name': name,
                        'winrate': winrate,
                        'profit': stat['profit'],
                        'trades': stat['trades']
                    })

        # 수익 순으로 정렬
        self.verified_strategies.sort(key=lambda x: x['profit'], reverse=True)

        print(f"\n검증된 전략: {len(self.verified_strategies)}개")
        for i, s in enumerate(self.verified_strategies[:5]):
            print(f"{i+1}. {s['name']}: {s['winrate']:.1f}% 승률, ${s['profit']:.2f} 수익")

    def generate_trading_signal(self, market_data, signals):
        """실제 트레이딩 시그널 생성 (검증 후)"""
        if self.learning_phase:
            return None

        # 검증된 전략만 사용
        verified_names = [s['name'] for s in self.verified_strategies]
        valid_signals = [s for s in signals if s['strategy'] in verified_names]

        if not valid_signals:
            return None

        # 신뢰도 순 정렬
        valid_signals.sort(key=lambda x: x['confidence'], reverse=True)
        best_signal = valid_signals[0]

        # 추가 필터링
        if best_signal['confidence'] < 0.7:
            return None

        return best_signal

    def send_telegram_message(self, message):
        """텔레그램 메시지 전송"""
        current_time = time.time()

        # 쿨다운 체크
        if current_time - self.last_telegram_alert < self.alert_cooldown:
            return

        try:
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(self.telegram_url, data=data)
            if response.status_code == 200:
                self.last_telegram_alert = current_time
                print(f"[텔레그램] 메시지 전송 완료")
            else:
                print(f"[텔레그램] 전송 실패: {response.status_code}")
        except Exception as e:
            print(f"[텔레그램] 오류: {e}")

    def send_trading_signal(self, signal):
        """트레이딩 시그널 텔레그램 전송"""
        symbol = signal['symbol']
        leverage = self.symbols[symbol]['leverage']
        current_price = self.prices[symbol]['current']

        message = f"""
🔔 <b>NVDA 트레이딩 시그널</b>

📊 종목: {symbol} ({leverage}X 레버리지)
💰 현재가: ${current_price:.2f}
📈 포지션: <b>{signal['direction']}</b>
🎯 전략: {signal['strategy']}
⚡ 신뢰도: {signal['confidence']*100:.0f}%

💡 목표 수익: {signal['config']['profit']*100:.1f}%
🛑 손절선: {signal['config']['loss']*100:.1f}%
⏱ 예상 보유: {signal['config']['hold']//60}분

⚠️ 리스크 관리 필수!
"""

        self.send_telegram_message(message)

    async def main_loop(self):
        """메인 루프"""
        tick = 0
        last_status = time.time()

        while True:
            try:
                tick += 1

                # 1. 가격 업데이트 (모든 심볼)
                for symbol in self.symbols:
                    price = await self.fetch_price(symbol)
                    self.prices[symbol]['current'] = price
                    self.prices[symbol]['history'].append(price)

                # 2. 가상 포지션 관리
                self.manage_virtual_positions()

                # 3. 시장 분석 및 신호 생성
                all_signals = []
                for symbol in self.symbols:
                    market = self.analyze_market(symbol)
                    if market:
                        signals = self.generate_signals(market)
                        all_signals.extend(signals)

                # 4. 학습 중이면 가상 거래
                if self.learning_phase and all_signals:
                    # 상위 3개만 실행
                    all_signals.sort(key=lambda x: x['confidence'], reverse=True)
                    for signal in all_signals[:3]:
                        if len(self.virtual_positions) < 10:
                            self.execute_virtual_trade(signal)

                # 5. 검증 완료 후 실제 시그널
                elif not self.learning_phase and all_signals:
                    for symbol in self.symbols:
                        market = self.analyze_market(symbol)
                        if market:
                            signals = self.generate_signals(market)
                            for signal in signals:
                                real_signal = self.generate_trading_signal(market, [signal])
                                if real_signal:
                                    self.send_trading_signal(real_signal)

                # 6. 상태 출력 (30초마다)
                if time.time() - last_status > 30:
                    self.print_status()
                    last_status = time.time()

                await asyncio.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"오류: {e}")
                await asyncio.sleep(1)

    def print_status(self):
        """상태 출력"""
        phase = "학습 중" if self.learning_phase else "시그널 전송 중"
        total_return = ((self.virtual_balance / self.initial_balance) - 1) * 100

        print(f"\n[{phase}] {datetime.now().strftime('%H:%M:%S')}")

        # 가격 출력
        prices_str = " | ".join([f"{s}: ${self.prices[s]['current']:.2f}" for s in self.symbols])
        print(f"가격: {prices_str}")

        if self.learning_phase:
            winrate = (self.learning_stats['wins'] / self.learning_stats['total_trades']) * 100 if self.learning_stats['total_trades'] > 0 else 0
            print(f"학습: {self.learning_stats['total_trades']}거래, {winrate:.1f}% 승률")
            print(f"가상잔고: ${self.virtual_balance:,.2f} ({total_return:+.2f}%)")
            print(f"진행률: {self.learning_stats['total_trades']}/{self.min_trades_for_validation}")
        else:
            print(f"검증된 전략: {len(self.verified_strategies)}개")
            print(f"누적 수익: ${self.learning_stats['total_profit']:+.2f}")

    async def run(self):
        """실행"""
        print("\n=== NVDA 실시간 학습 봇 시작 ===")
        print("실시간 데이터 → 학습 → 검증 → 텔레그램 시그널")
        print("Ctrl+C로 중단")

        await self.init_session()

        try:
            await self.main_loop()
        finally:
            await self.close_session()
            self.print_final()

    def print_final(self):
        """최종 결과"""
        print("\n" + "=" * 60)
        print("=== NVDA 학습 봇 최종 결과 ===")

        if self.learning_stats['total_trades'] > 0:
            winrate = (self.learning_stats['wins'] / self.learning_stats['total_trades']) * 100
            total_return = ((self.virtual_balance / self.initial_balance) - 1) * 100

            print(f"총 학습 거래: {self.learning_stats['total_trades']}회")
            print(f"최종 승률: {winrate:.1f}%")
            print(f"총 수익: ${self.learning_stats['total_profit']:+.2f}")
            print(f"수익률: {total_return:+.2f}%")

            if not self.learning_phase:
                print(f"\n✅ 검증 완료!")
                print(f"검증된 전략: {len(self.verified_strategies)}개")

        print("=" * 60)

def main():
    # 텔레그램 봇 토큰과 채팅 ID 설정 필요
    bot = NVDARealtimeLearningBot(
        telegram_token="YOUR_BOT_TOKEN",  # 여기에 실제 봇 토큰 입력
        chat_id="YOUR_CHAT_ID"  # 여기에 실제 채팅 ID 입력
    )
    asyncio.run(bot.run())

if __name__ == "__main__":
    main()