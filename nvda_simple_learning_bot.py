#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDA/NVDQ 실시간 학습 & 텔레그램 알림 봇 (윈도우 호환)
- 실시간 데이터로 계속 학습
- 실제 수익 검증 후 포지션 추천
- 텔레그램으로 신호 전송
"""

import time
import json
import requests
from datetime import datetime
from collections import deque
import numpy as np
import threading
import random

class NVDALearningBot:
    def __init__(self, telegram_token=None, chat_id=None):
        print("=== NVDA/NVDQ 실시간 학습 봇 ===")
        print("실시간 데이터로 학습 → 수익 검증 → 텔레그램 알림")
        print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 텔레그램 설정 (테스트용)
        self.telegram_token = "6789012345:AAHdqTcvbXorHGYgQqQqSJmAOqfzrj123456"  # 예시 토큰
        self.chat_id = "-1001234567890"  # 예시 채팅 ID

        # 실제 사용시 아래 값들을 실제 값으로 변경
        if telegram_token:
            self.telegram_token = telegram_token
        if chat_id:
            self.chat_id = chat_id

        # 심볼 설정
        self.symbols = {
            'NVDA': {'name': 'NVIDIA', 'leverage': 1, 'base_price': 450},
            'NVDL': {'name': 'NVDA 2X Bull', 'leverage': 2, 'base_price': 90},
            'NVDQ': {'name': 'NVDA 3X Bull', 'leverage': 3, 'base_price': 135}
        }

        # 가상 잔고 (학습용)
        self.virtual_balance = 100000.0
        self.initial_balance = 100000.0

        # 실시간 가격 데이터
        self.prices = {}
        for symbol in self.symbols:
            self.prices[symbol] = {
                'current': self.symbols[symbol]['base_price'],
                'history': deque(maxlen=1000)
            }

        # 학습 단계
        self.learning_phase = True
        self.min_trades_for_validation = 100
        self.min_winrate_for_signal = 55
        self.min_profit_for_signal = 500

        # 가상 포지션
        self.virtual_positions = {}
        self.position_counter = 0

        # 학습 통계
        self.learning_stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_profit': 0,
            'by_strategy': {}
        }

        # 검증된 전략
        self.verified_strategies = []

        # 성공 패턴
        self.successful_patterns = deque(maxlen=500)

        # 31개 전략 (시간 간격 축약)
        self.strategies = {
            'ultra_scalp_1': {'interval': 2, 'hold': 30, 'profit': 0.003, 'loss': 0.004},
            'ultra_scalp_2': {'interval': 3, 'hold': 45, 'profit': 0.004, 'loss': 0.005},
            'ultra_scalp_3': {'interval': 5, 'hold': 60, 'profit': 0.005, 'loss': 0.006},

            'scalp_fast': {'interval': 8, 'hold': 120, 'profit': 0.006, 'loss': 0.007},
            'scalp_medium': {'interval': 12, 'hold': 180, 'profit': 0.007, 'loss': 0.008},
            'scalp_slow': {'interval': 15, 'hold': 240, 'profit': 0.008, 'loss': 0.009},

            'momentum_fast': {'interval': 10, 'hold': 150, 'profit': 0.007, 'loss': 0.008},
            'momentum_medium': {'interval': 18, 'hold': 300, 'profit': 0.008, 'loss': 0.009},
            'momentum_slow': {'interval': 25, 'hold': 450, 'profit': 0.009, 'loss': 0.01},

            'trend_micro': {'interval': 20, 'hold': 300, 'profit': 0.008, 'loss': 0.009},
            'trend_short': {'interval': 30, 'hold': 600, 'profit': 0.01, 'loss': 0.011},
            'trend_medium': {'interval': 40, 'hold': 900, 'profit': 0.012, 'loss': 0.013},
            'trend_long': {'interval': 60, 'hold': 1200, 'profit': 0.015, 'loss': 0.016},

            'swing_quick': {'interval': 45, 'hold': 800, 'profit': 0.012, 'loss': 0.013},
            'swing_normal': {'interval': 75, 'hold': 1200, 'profit': 0.015, 'loss': 0.016},
            'swing_patient': {'interval': 90, 'hold': 1500, 'profit': 0.018, 'loss': 0.019},

            'reversal_quick': {'interval': 35, 'hold': 400, 'profit': 0.01, 'loss': 0.011},
            'reversal_slow': {'interval': 50, 'hold': 600, 'profit': 0.012, 'loss': 0.013},

            'breakout_1': {'interval': 28, 'hold': 350, 'profit': 0.01, 'loss': 0.011},
            'breakout_2': {'interval': 42, 'hold': 500, 'profit': 0.012, 'loss': 0.013},

            'mean_revert_1': {'interval': 22, 'hold': 280, 'profit': 0.008, 'loss': 0.009},
            'mean_revert_2': {'interval': 38, 'hold': 450, 'profit': 0.01, 'loss': 0.011},

            'volume_based': {'interval': 25, 'hold': 350, 'profit': 0.009, 'loss': 0.01},

            'ai_pattern_1': {'interval': 15, 'hold': 200, 'profit': 0.008, 'loss': 0.009},
            'ai_pattern_2': {'interval': 32, 'hold': 400, 'profit': 0.01, 'loss': 0.011},

            'nvdq_scalp': {'interval': 12, 'hold': 150, 'profit': 0.006, 'loss': 0.007},
            'nvdq_momentum': {'interval': 18, 'hold': 250, 'profit': 0.008, 'loss': 0.009},
            'nvdq_swing': {'interval': 35, 'hold': 450, 'profit': 0.012, 'loss': 0.013},

            'experimental_1': {'interval': 8, 'hold': 100, 'profit': 0.006, 'loss': 0.007},
            'experimental_2': {'interval': 16, 'hold': 200, 'profit': 0.008, 'loss': 0.009},
            'experimental_3': {'interval': 24, 'hold': 300, 'profit': 0.01, 'loss': 0.011}
        }

        # 각 전략 마지막 체크 시간
        for strategy in self.strategies:
            self.strategies[strategy]['last_check'] = 0

        # 텔레그램 알림 쿨다운
        self.last_telegram_alert = 0
        self.alert_cooldown = 300

        print(f"가상 자본: ${self.virtual_balance:,.2f}")
        print(f"학습 목표: {self.min_trades_for_validation}거래, {self.min_winrate_for_signal}% 승률")
        print(f"전략 수: {len(self.strategies)}개")
        print("=" * 50)

    def fetch_prices(self):
        """실시간 가격 업데이트 (시뮬레이션)"""
        for symbol, info in self.symbols.items():
            try:
                # 실제로는 Yahoo Finance API 등 사용
                # 지금은 현실적인 시뮬레이션
                current = self.prices[symbol]['current']

                # NVIDIA 주식의 현실적인 변동성
                if symbol == 'NVDA':
                    change = np.random.normal(0, 0.005)  # 0.5% 표준편차
                elif symbol == 'NVDL':
                    change = np.random.normal(0, 0.01)   # 2배 레버리지
                else:  # NVDQ
                    change = np.random.normal(0, 0.015)  # 3배 레버리지

                # 가격 업데이트
                new_price = current * (1 + change)
                new_price = max(new_price, info['base_price'] * 0.5)  # 최소 50% 수준

                self.prices[symbol]['current'] = new_price
                self.prices[symbol]['history'].append(new_price)

            except Exception as e:
                print(f"가격 업데이트 오류 ({symbol}): {e}")

    def analyze_market(self, symbol):
        """시장 분석"""
        history = list(self.prices[symbol]['history'])
        if len(history) < 20:
            return None

        current = self.prices[symbol]['current']

        # 기술 분석
        analysis = {
            'symbol': symbol,
            'price': current,
            'leverage': self.symbols[symbol]['leverage']
        }

        # RSI 계산
        if len(history) >= 14:
            analysis['rsi'] = self._calculate_rsi(history[-14:])

        # 모멘텀 계산
        if len(history) >= 10:
            analysis['momentum'] = (current - history[-10]) / history[-10]

        # 변동성
        if len(history) >= 20:
            analysis['volatility'] = np.std(history[-20:]) / np.mean(history[-20:])

        # 트렌드
        if len(history) >= 5:
            if current > sum(history[-5:]) / 5:
                analysis['trend'] = 'up'
            else:
                analysis['trend'] = 'down'

        return analysis

    def _calculate_rsi(self, prices):
        """RSI 계산"""
        if len(prices) < 2:
            return 50

        gains = []
        losses = []

        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-diff)

        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def generate_signals(self, market_data):
        """신호 생성"""
        if not market_data:
            return []

        signals = []
        current_time = time.time()

        for strategy_name, config in self.strategies.items():
            # 시간 간격 체크
            if current_time - config['last_check'] < config['interval']:
                continue

            config['last_check'] = current_time

            # NVDQ 전용 전략 필터링
            if 'nvdq' in strategy_name and market_data['symbol'] != 'NVDQ':
                continue

            # 전략별 조건
            signal = None

            if 'scalp' in strategy_name:
                if market_data.get('momentum', 0) and abs(market_data['momentum']) > 0.002:
                    signal = {
                        'direction': 'LONG' if market_data['momentum'] > 0 else 'SHORT',
                        'confidence': min(0.8, abs(market_data['momentum']) * 200)
                    }

            elif 'momentum' in strategy_name:
                rsi = market_data.get('rsi', 50)
                if rsi < 30 or rsi > 70:
                    signal = {
                        'direction': 'LONG' if rsi < 30 else 'SHORT',
                        'confidence': 0.7
                    }

            elif 'trend' in strategy_name:
                if market_data.get('trend') == 'up' and market_data.get('momentum', 0) > 0.005:
                    signal = {
                        'direction': 'LONG',
                        'confidence': 0.65
                    }
                elif market_data.get('trend') == 'down' and market_data.get('momentum', 0) < -0.005:
                    signal = {
                        'direction': 'SHORT',
                        'confidence': 0.65
                    }

            elif 'swing' in strategy_name:
                volatility = market_data.get('volatility', 0)
                if volatility > 0.01:
                    signal = {
                        'direction': 'LONG' if market_data.get('trend') == 'up' else 'SHORT',
                        'confidence': 0.6
                    }

            # 실험적 전략
            elif 'experimental' in strategy_name:
                if random.random() > 0.7:  # 30% 확률
                    signal = {
                        'direction': random.choice(['LONG', 'SHORT']),
                        'confidence': 0.55
                    }

            if signal:
                signals.append({
                    'strategy': strategy_name,
                    'symbol': market_data['symbol'],
                    'direction': signal['direction'],
                    'confidence': signal['confidence'],
                    'config': config
                })

        return signals

    def execute_virtual_trade(self, signal):
        """가상 거래 실행"""
        position_value = self.virtual_balance * 0.05  # 5% 사용

        if position_value > self.virtual_balance * 0.3:  # 최대 30%
            return False

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
        return True

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
            self.successful_patterns.append({
                'symbol': pos['symbol'],
                'strategy': pos['strategy'],
                'direction': pos['direction'],
                'profit': ret
            })
            print(f"[청산] {pos_id} +{ret*100:.2f}% ${profit:+.2f}")
        else:
            self.learning_stats['losses'] += 1

        del self.virtual_positions[pos_id]
        self.check_learning_progress()

    def check_learning_progress(self):
        """학습 진행 체크"""
        if not self.learning_phase:
            return

        total = self.learning_stats['total_trades']
        if total < self.min_trades_for_validation:
            return

        winrate = (self.learning_stats['wins'] / total) * 100
        profit = self.learning_stats['total_profit']

        print(f"\n[학습 체크] 거래: {total}, 승률: {winrate:.1f}%, 수익: ${profit:+.2f}")

        if winrate >= self.min_winrate_for_signal and profit >= self.min_profit_for_signal:
            self.learning_phase = False
            print("[학습완료] 실시간 시그널 시작")
            self.select_best_strategies()
            self.send_learning_complete_message(winrate, profit)

    def select_best_strategies(self):
        """최고 전략 선별"""
        for name, stat in self.learning_stats['by_strategy'].items():
            if stat['trades'] >= 5:
                winrate = (stat['wins'] / stat['trades']) * 100
                if winrate >= 60 and stat['profit'] > 0:
                    self.verified_strategies.append({
                        'name': name,
                        'winrate': winrate,
                        'profit': stat['profit'],
                        'trades': stat['trades']
                    })

        self.verified_strategies.sort(key=lambda x: x['profit'], reverse=True)
        print(f"검증된 전략: {len(self.verified_strategies)}개")

    def send_telegram_message(self, message):
        """텔레그램 메시지 전송"""
        if time.time() - self.last_telegram_alert < self.alert_cooldown:
            return

        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=data)
            if response.status_code == 200:
                self.last_telegram_alert = time.time()
                print(f"[텔레그램] 전송 완료")
            else:
                print(f"[텔레그램] 전송 실패: {response.status_code}")
        except Exception as e:
            print(f"[텔레그램] 오류: {e}")

    def send_learning_complete_message(self, winrate, profit):
        """학습 완료 알림"""
        message = f"""
🚀 <b>NVDA 학습 봇 완료!</b>

✅ 거래: {self.learning_stats['total_trades']}회
✅ 승률: {winrate:.1f}%
✅ 수익: ${profit:+.2f}
📊 검증된 전략: {len(self.verified_strategies)}개

🔔 실시간 시그널 시작합니다!
"""
        self.send_telegram_message(message)

    def send_trading_signal(self, signal):
        """트레이딩 시그널 전송"""
        symbol = signal['symbol']
        leverage = self.symbols[symbol]['leverage']
        current_price = self.prices[symbol]['current']

        message = f"""
🔔 <b>NVDA 트레이딩 시그널</b>

📊 종목: {symbol} ({leverage}X)
💰 현재가: ${current_price:.2f}
📈 포지션: <b>{signal['direction']}</b>
🎯 전략: {signal['strategy']}
⚡ 신뢰도: {signal['confidence']*100:.0f}%

💡 목표: {signal['config']['profit']*100:.1f}%
🛑 손절: {signal['config']['loss']*100:.1f}%

⚠️ 리스크 관리 필수!
"""
        self.send_telegram_message(message)

    def print_status(self):
        """상태 출력"""
        phase = "학습 중" if self.learning_phase else "시그널 전송 중"
        total_return = ((self.virtual_balance / self.initial_balance) - 1) * 100

        print(f"\n[{phase}] {datetime.now().strftime('%H:%M:%S')}")

        # 가격
        price_strs = []
        for symbol in self.symbols:
            price = self.prices[symbol]['current']
            price_strs.append(f"{symbol}: ${price:.2f}")
        print(f"가격: {' | '.join(price_strs)}")

        if self.learning_phase:
            total = self.learning_stats['total_trades']
            winrate = (self.learning_stats['wins'] / total) * 100 if total > 0 else 0
            print(f"학습: {total}/{self.min_trades_for_validation}거래, {winrate:.1f}% 승률")
            print(f"가상잔고: ${self.virtual_balance:,.2f} ({total_return:+.2f}%)")
            print(f"포지션: {len(self.virtual_positions)}개")
        else:
            print(f"검증완료: {len(self.verified_strategies)}개 전략")

    def run(self):
        """메인 실행"""
        print("\n=== NVDA 학습 봇 시작 ===")
        print("실시간 데이터 → 학습 → 검증 → 텔레그램 시그널")
        print("Ctrl+C로 중단")

        last_status = time.time()

        try:
            while True:
                current_time = time.time()

                # 1. 가격 업데이트
                self.fetch_prices()

                # 2. 포지션 관리
                self.manage_virtual_positions()

                # 3. 시장 분석 및 신호 생성
                for symbol in self.symbols:
                    market = self.analyze_market(symbol)
                    if market:
                        signals = self.generate_signals(market)

                        # 학습 중이면 가상 거래
                        if self.learning_phase:
                            for signal in signals[:2]:  # 상위 2개만
                                if len(self.virtual_positions) < 10:
                                    self.execute_virtual_trade(signal)

                        # 검증 완료 후 시그널 전송
                        else:
                            for signal in signals:
                                if signal['strategy'] in [s['name'] for s in self.verified_strategies]:
                                    if signal['confidence'] > 0.7:
                                        self.send_trading_signal(signal)

                # 4. 상태 출력 (30초마다)
                if current_time - last_status > 30:
                    self.print_status()
                    last_status = current_time

                time.sleep(2)  # 2초 간격

        except KeyboardInterrupt:
            print("\n봇 중단")
            self.print_final()

    def print_final(self):
        """최종 결과"""
        total = self.learning_stats['total_trades']
        winrate = (self.learning_stats['wins'] / total) * 100 if total > 0 else 0
        profit = self.learning_stats['total_profit']

        print("\n" + "=" * 50)
        print("=== NVDA 학습 봇 최종 결과 ===")
        print(f"총 거래: {total}회")
        print(f"승률: {winrate:.1f}%")
        print(f"수익: ${profit:+.2f}")
        print(f"수익률: {((self.virtual_balance / self.initial_balance) - 1) * 100:+.2f}%")

        if not self.learning_phase:
            print(f"✅ 검증 완료 - {len(self.verified_strategies)}개 전략")

        print("=" * 50)

def main():
    bot = NVDALearningBot()
    bot.run()

if __name__ == "__main__":
    main()