#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOXL/SOXS 최적 시간봉 백테스트

FMP API로 실제 과거 데이터를 가져와서 여러 시간봉으로 시뮬레이션
"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time

class SOXLTimeframeBacktest:
    """SOXL/SOXS 시간봉별 백테스트"""

    def __init__(self):
        print("="*80)
        print("SOXL/SOXS 최적 시간봉 백테스트")
        print("="*80)

        # FMP API 키
        self.fmp_api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

        # 백테스트 설정
        self.initial_balance = 1000  # $1000
        self.leverage = 1  # SOXL/SOXS 자체가 3배 레버리지
        self.trade_fee = 0.0005  # 0.05% (한투 수수료)

        # 전략 파라미터 (매우 공격적으로)
        self.max_holding_time = 180  # 180분 (3시간) - 더 길게
        self.stop_loss = -4.0  # -4% - 여유 확보
        self.take_profit = 8.0  # +8% 익절 - 현실적으로

        # 시간봉 목록
        self.timeframes = {
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60
        }

        # 백테스트 기간 (최근 SOXL이 급등한 시기 포함)
        self.backtest_days = 90  # 90일 - 더 긴 기간으로 복리 효과 확인

        self.results = {}

    def fetch_intraday_data(self, symbol: str, interval: str, days: int = 30) -> pd.DataFrame:
        """
        FMP API로 인트라데이 데이터 가져오기

        Args:
            symbol: 'SOXL' or 'SOXS'
            interval: '1min', '5min', '15min', '30min', '1hour'
            days: 조회할 일수
        """
        try:
            print(f"\n[데이터 수집] {symbol} {interval}, {days}일치...")

            all_data = []

            # FMP API는 최근 데이터만 제공하므로 여러 날짜로 나눠서 요청
            for day_offset in range(days):
                date = (datetime.now() - timedelta(days=day_offset)).strftime('%Y-%m-%d')

                url = f"https://financialmodelingprep.com/api/v3/historical-chart/{interval}/{symbol}"
                params = {
                    'apikey': self.fmp_api_key,
                    'from': date,
                    'to': date
                }

                response = requests.get(url, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    if data:
                        all_data.extend(data)
                        print(f"  {date}: {len(data)}개 캔들")
                    time.sleep(0.3)  # API 레이트 리밋
                else:
                    print(f"  {date}: HTTP {response.status_code}")

            if not all_data:
                print(f"[ERROR] {symbol} 데이터 수집 실패")
                return pd.DataFrame()

            # DataFrame 변환
            df = pd.DataFrame(all_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.rename(columns={'date': 'timestamp'})

            # 숫자 변환
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # 시간순 정렬
            df = df.sort_values('timestamp').reset_index(drop=True)

            print(f"[OK] {len(df)}개 캔들 수집 완료")
            if len(df) > 0:
                print(f"  기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")

            return df

        except Exception as e:
            print(f"[ERROR] 데이터 수집 실패: {e}")
            return pd.DataFrame()

    def resample_to_timeframe(self, df: pd.DataFrame, minutes: int) -> pd.DataFrame:
        """데이터를 특정 시간봉으로 리샘플링"""
        if df.empty:
            return df

        df_copy = df.copy()
        df_copy.set_index('timestamp', inplace=True)

        # 리샘플링
        resampled = df_copy.resample(f'{minutes}min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        resampled.reset_index(inplace=True)
        return resampled

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술 지표 계산"""
        df = df.copy()

        # 이동평균
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # 추세 신호
        df['trend'] = 'NEUTRAL'
        df.loc[df['ma5'] > df['ma20'], 'trend'] = 'BULL'
        df.loc[df['ma5'] < df['ma20'], 'trend'] = 'BEAR'

        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """매매 신호 생성 - 개선된 전략"""
        df = df.copy()
        df['signal'] = 'NEUTRAL'
        df['confidence'] = 50

        # 추가 지표: 볼린저 밴드
        df['bb_mid'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * 2)

        # 가격 모멘텀
        df['momentum'] = df['close'].pct_change(5) * 100  # 5봉 전 대비 변화율

        # 개선된 BULL 신호: 여러 조건 조합
        bull_condition = (
            (df['ma5'] > df['ma20']) &  # 추세 상승
            (df['close'] > df['bb_mid']) &  # 볼린저 밴드 중심선 위
            (df['rsi'] > 30) & (df['rsi'] < 70) &  # RSI 적정 범위
            (df['momentum'] > 0)  # 양의 모멘텀
        )
        df.loc[bull_condition, 'signal'] = 'BULL'
        df.loc[bull_condition, 'confidence'] = 70

        # 개선된 BEAR 신호
        bear_condition = (
            (df['ma5'] < df['ma20']) &  # 추세 하락
            (df['close'] < df['bb_mid']) &  # 볼린저 밴드 중심선 아래
            (df['rsi'] > 30) & (df['rsi'] < 70) &  # RSI 적정 범위
            (df['momentum'] < 0)  # 음의 모멘텀
        )
        df.loc[bear_condition, 'signal'] = 'BEAR'
        df.loc[bear_condition, 'confidence'] = 70

        return df

    def backtest_timeframe(self, timeframe_name: str, timeframe_minutes: int) -> dict:
        """특정 시간봉으로 백테스트"""
        print(f"\n{'='*80}")
        print(f"백테스트: {timeframe_name} ({timeframe_minutes}분봉)")
        print(f"{'='*80}")

        # FMP interval 매핑
        interval_map = {
            5: '5min',
            15: '15min',
            30: '30min',
            60: '1hour'
        }
        interval = interval_map.get(timeframe_minutes, '5min')

        # SOXL 데이터 수집
        df = self.fetch_intraday_data('SOXL', interval, days=self.backtest_days)
        if df.empty:
            print("[ERROR] 데이터 없음")
            return None

        # 지표 계산
        df = self.calculate_indicators(df)
        df = self.generate_signals(df)

        # 백테스트 실행
        balance = self.initial_balance
        position = None  # 'SOXL' or 'SOXS'
        entry_price = 0
        entry_time = None
        entry_idx = 0

        trades = []
        equity_curve = []

        min_confidence = 70  # 더 많은 거래 기회

        for idx, row in df.iterrows():
            if idx < 20:  # 지표 워밍업
                continue

            timestamp = row['timestamp']
            price = row['close']
            signal = row['signal']
            confidence = row['confidence']

            # 포지션 있을 때
            if position:
                holding_bars = idx - entry_idx
                holding_time_min = holding_bars * timeframe_minutes

                # PNL 계산 (3배 레버리지 효과)
                if position == 'SOXL':
                    # SOXL 자체가 반도체 3배 레버리지
                    price_change = (price - entry_price) / entry_price * 100
                    pnl_pct = price_change  # SOXL 자체 레버리지
                else:  # SOXS
                    price_change = (entry_price - price) / entry_price * 100
                    pnl_pct = price_change  # SOXS 자체 레버리지

                should_exit = False
                exit_reason = ""

                # 청산 조건
                if pnl_pct >= self.take_profit:
                    should_exit = True
                    exit_reason = "TAKE_PROFIT"
                elif holding_time_min > self.max_holding_time:
                    should_exit = True
                    exit_reason = "MAX_TIME"
                elif pnl_pct <= self.stop_loss:
                    should_exit = True
                    exit_reason = "STOP_LOSS"
                elif position == 'SOXL' and signal == 'BEAR' and confidence >= min_confidence:
                    should_exit = True
                    exit_reason = "TREND_CHANGE"
                elif position == 'SOXS' and signal == 'BULL' and confidence >= min_confidence:
                    should_exit = True
                    exit_reason = "TREND_CHANGE"

                # 청산 (복리 적용 - 전체 잔고로 매번 거래)
                if should_exit:
                    # 수수료 차감 후 실제 수익
                    gross_profit = balance * (pnl_pct / 100)
                    fees = balance * self.trade_fee * 2  # 진입+청산
                    net_profit = gross_profit - fees

                    balance += net_profit
                    balance_change = net_profit

                    trade_record = {
                        'entry_time': entry_time,
                        'exit_time': timestamp,
                        'position': position,
                        'entry_price': entry_price,
                        'exit_price': price,
                        'holding_time_min': holding_time_min,
                        'pnl_pct': pnl_pct,
                        'balance_change': balance_change,
                        'balance': balance,
                        'exit_reason': exit_reason
                    }
                    trades.append(trade_record)

                    # 추세 전환이면 반대 포지션
                    if exit_reason == "TREND_CHANGE":
                        position = 'SOXL' if signal == 'BULL' else 'SOXS'
                        entry_price = price
                        entry_time = timestamp
                        entry_idx = idx
                    else:
                        position = None

            # 포지션 없을 때
            else:
                if signal in ['BULL', 'BEAR'] and confidence >= min_confidence:
                    position = 'SOXL' if signal == 'BULL' else 'SOXS'
                    entry_price = price
                    entry_time = timestamp
                    entry_idx = idx

            equity_curve.append({
                'timestamp': timestamp,
                'balance': balance
            })

        # 결과 분석
        if not trades:
            print("[WARN] 거래 없음")
            return None

        wins = [t for t in trades if t['pnl_pct'] > 0]
        losses = [t for t in trades if t['pnl_pct'] <= 0]

        total_trades = len(trades)
        win_rate = len(wins) / total_trades * 100
        total_return = ((balance - self.initial_balance) / self.initial_balance) * 100

        avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losses]) if losses else 0
        avg_holding_time = np.mean([t['holding_time_min'] for t in trades])

        # MDD
        equity_series = pd.Series([e['balance'] for e in equity_curve])
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        max_drawdown = drawdown.min()

        # Sharpe Ratio
        daily_returns = equity_series.pct_change().dropna()
        if len(daily_returns) > 0 and daily_returns.std() > 0:
            sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)  # 연간화
        else:
            sharpe_ratio = 0

        result = {
            'timeframe': timeframe_name,
            'timeframe_minutes': timeframe_minutes,
            'total_trades': total_trades,
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_return': total_return,
            'final_balance': balance,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_holding_time': avg_holding_time,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio
        }

        # 결과 출력
        print(f"\n[결과 요약]")
        print(f"  총 거래: {total_trades}건")
        print(f"  승률: {win_rate:.1f}% ({len(wins)}승 {len(losses)}패)")
        print(f"  총 수익률: {total_return:+.2f}%")
        print(f"  최종 잔고: ${balance:.2f}")
        print(f"  평균 수익: {avg_win:+.2f}%")
        print(f"  평균 손실: {avg_loss:+.2f}%")
        print(f"  평균 보유시간: {avg_holding_time:.1f}분")
        print(f"  최대 낙폭(MDD): {max_drawdown:.2f}%")
        print(f"  샤프 비율: {sharpe_ratio:.2f}")

        return result

    def run_all_backtests(self):
        """모든 시간봉 백테스트"""
        print("\n" + "="*80)
        print("모든 시간봉 백테스트 시작")
        print("="*80)

        for timeframe_name, timeframe_minutes in self.timeframes.items():
            result = self.backtest_timeframe(timeframe_name, timeframe_minutes)
            if result:
                self.results[timeframe_name] = result
            time.sleep(1)

        self.compare_results()
        self.save_results()

    def compare_results(self):
        """결과 비교"""
        if not self.results:
            print("\n[ERROR] 분석할 결과가 없습니다")
            return

        print("\n" + "="*80)
        print("시간봉별 성과 비교")
        print("="*80)

        print(f"\n{'시간봉':<8} {'거래수':<8} {'승률':<10} {'수익률':<12} {'MDD':<10} {'샤프':<8} {'평균보유':<10}")
        print("-" * 80)

        for timeframe_name in ['5m', '15m', '30m', '1h']:
            if timeframe_name in self.results:
                r = self.results[timeframe_name]
                print(f"{r['timeframe']:<8} {r['total_trades']:<8} "
                      f"{r['win_rate']:<10.1f}% {r['total_return']:<12.2f}% "
                      f"{r['max_drawdown']:<10.2f}% {r['sharpe_ratio']:<8.2f} "
                      f"{r['avg_holding_time']:<10.1f}분")

        # 최적 시간봉 선정
        best_by_return = max(self.results.items(), key=lambda x: x[1]['total_return'])
        best_by_winrate = max(self.results.items(), key=lambda x: x[1]['win_rate'])
        best_by_sharpe = max(self.results.items(), key=lambda x: x[1]['sharpe_ratio'])

        print("\n" + "="*80)
        print("최적 시간봉 분석")
        print("="*80)
        print(f"\n[최고 수익률] {best_by_return[0]}: {best_by_return[1]['total_return']:+.2f}%")
        print(f"[최고 승률] {best_by_winrate[0]}: {best_by_winrate[1]['win_rate']:.1f}%")
        print(f"[최고 샤프 비율] {best_by_sharpe[0]}: {best_by_sharpe[1]['sharpe_ratio']:.2f}")

        # 종합 점수
        scores = {}
        for name, result in self.results.items():
            score = (result['total_return'] * 0.5 +
                    result['win_rate'] * 0.3 +
                    result['sharpe_ratio'] * 10 * 0.2)
            scores[name] = score

        best_overall = max(scores.items(), key=lambda x: x[1])

        print(f"\n[종합 추천] {best_overall[0]}")
        print(f"  종합 점수: {best_overall[1]:.2f}")
        print(f"  수익률: {self.results[best_overall[0]]['total_return']:+.2f}%")
        print(f"  승률: {self.results[best_overall[0]]['win_rate']:.1f}%")
        print(f"  샤프 비율: {self.results[best_overall[0]]['sharpe_ratio']:.2f}")

    def save_results(self):
        """결과 저장"""
        try:
            with open('soxl_timeframe_backtest_results.json', 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
            print(f"\n[OK] 결과 저장: soxl_timeframe_backtest_results.json")
        except Exception as e:
            print(f"[ERROR] 결과 저장 실패: {e}")

if __name__ == "__main__":
    backtester = SOXLTimeframeBacktest()
    backtester.run_all_backtests()
