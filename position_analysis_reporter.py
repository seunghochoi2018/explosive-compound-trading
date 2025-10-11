#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포지션 변경 주기 분석 및 보고 시스템
- 수익 패턴 학습 결과를 바탕으로 포지션 변경 주기 분석
- 텔레그램을 통한 정기 보고
- 최적 거래 주기 추천
"""

import json
import time
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter, defaultdict
import warnings
warnings.filterwarnings('ignore')

# 자체 모듈 임포트
from nvdl_nvdq_data_collector import NVDLNVDQDataCollector
from nvdl_nvdq_trading_model import NVDLNVDQTradingModel
from telegram_notifier import TelegramNotifier

class PositionAnalysisReporter:
    def __init__(self, fmp_api_key: str):
        """
        포지션 분석 리포터 초기화

        Args:
            fmp_api_key: Financial Modeling Prep API 키
        """
        print("=== 포지션 변경 주기 분석 시스템 ===")

        # 컴포넌트 초기화
        self.data_collector = NVDLNVDQDataCollector(fmp_api_key)
        self.trading_model = NVDLNVDQTradingModel(fmp_api_key)
        self.telegram = TelegramNotifier()

        # 분석 데이터
        self.position_history = []
        self.trade_intervals = []
        self.profitability_by_duration = {}
        self.optimal_intervals = {}

        # 보고서 캐시
        self.analysis_cache = {}
        self.last_analysis_time = None

        print("포지션 분석 시스템 초기화 완료")

    def load_historical_data(self):
        """역사적 거래 데이터 로드"""
        print("역사적 거래 데이터 로드 중...")

        # 데이터 수집기에서 특성 데이터 로드
        self.data_collector.load_data()

        # 거래 모델에서 패턴 데이터 로드
        self.trading_model.load_historical_patterns()
        self.trading_model.load_models()

        # 성공 패턴에서 거래 간격 분석
        self.analyze_historical_patterns()

        print(f"분석할 패턴 수: {len(self.trading_model.success_patterns)}")

    def analyze_historical_patterns(self):
        """역사적 패턴에서 거래 주기 분석"""
        print("역사적 패턴 분석 중...")

        if not self.trading_model.success_patterns:
            print("분석할 패턴이 없습니다.")
            return

        # 타임스탬프 기반 거래 간격 계산
        timestamps = []
        profits = []

        for pattern in self.trading_model.success_patterns:
            if 'timestamp' in pattern and 'profit' in pattern:
                try:
                    timestamp = datetime.fromisoformat(pattern['timestamp'])
                    timestamps.append(timestamp)
                    profits.append(pattern['profit'])
                except:
                    continue

        if len(timestamps) < 2:
            print("거래 간격 분석에 충분한 데이터가 없습니다.")
            return

        # 시간순 정렬
        sorted_data = sorted(zip(timestamps, profits))
        timestamps, profits = zip(*sorted_data)

        # 거래 간격 계산
        intervals = []
        interval_profits = []

        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600  # 시간 단위
            intervals.append(interval)
            interval_profits.append(profits[i])

        self.trade_intervals = intervals
        self.analyze_profitability_by_duration(intervals, interval_profits)

        print(f"거래 간격 분석 완료: {len(intervals)}개 간격")

    def analyze_profitability_by_duration(self, intervals: List[float], profits: List[float]):
        """보유 기간별 수익성 분석"""
        print("보유 기간별 수익성 분석 중...")

        # 구간별 분류
        duration_ranges = [
            (0, 1, "1시간 이내"),
            (1, 4, "1-4시간"),
            (4, 12, "4-12시간"),
            (12, 24, "12-24시간"),
            (24, 72, "1-3일"),
            (72, 168, "3-7일"),
            (168, float('inf'), "7일 이상")
        ]

        duration_stats = {}

        for min_hours, max_hours, label in duration_ranges:
            duration_data = [
                profit for interval, profit in zip(intervals, profits)
                if min_hours <= interval < max_hours
            ]

            if duration_data:
                stats = {
                    'count': len(duration_data),
                    'avg_profit': np.mean(duration_data),
                    'median_profit': np.median(duration_data),
                    'std_profit': np.std(duration_data),
                    'win_rate': sum(1 for p in duration_data if p > 0) / len(duration_data) * 100,
                    'max_profit': max(duration_data),
                    'min_profit': min(duration_data)
                }
                duration_stats[label] = stats

        self.profitability_by_duration = duration_stats
        self.find_optimal_intervals()

    def find_optimal_intervals(self):
        """최적 거래 주기 찾기"""
        print("최적 거래 주기 분석 중...")

        if not self.profitability_by_duration:
            return

        # 위험 조정 수익률 계산 (샤프 비율 유사)
        optimal_analysis = {}

        for duration, stats in self.profitability_by_duration.items():
            if stats['count'] >= 5:  # 최소 5회 이상 거래
                # 위험 조정 수익률 = 평균 수익률 / 표준편차
                risk_adjusted_return = stats['avg_profit'] / max(stats['std_profit'], 0.1)

                # 종합 점수 = 위험조정수익률 * 승률가중치 * 거래빈도가중치
                frequency_weight = min(stats['count'] / 10, 1.0)  # 거래 빈도 가중치
                win_rate_weight = stats['win_rate'] / 100
                total_score = risk_adjusted_return * win_rate_weight * frequency_weight

                optimal_analysis[duration] = {
                    'score': total_score,
                    'risk_adjusted_return': risk_adjusted_return,
                    'frequency_weight': frequency_weight,
                    'win_rate_weight': win_rate_weight,
                    'stats': stats
                }

        # 점수순 정렬
        self.optimal_intervals = dict(
            sorted(optimal_analysis.items(), key=lambda x: x[1]['score'], reverse=True)
        )

    def simulate_different_intervals(self) -> Dict:
        """다양한 거래 주기로 시뮬레이션"""
        print("다양한 거래 주기 시뮬레이션 중...")

        if not self.trading_model.features_data:
            self.data_collector.load_data()
            self.data_collector.calculate_all_features()

        simulation_results = {}

        # 시뮬레이션할 주기들 (시간 단위)
        test_intervals = [0.5, 1, 2, 4, 8, 12, 24, 48]

        for symbol in ['NVDL', 'NVDQ']:
            for data_interval in ['1hour']:  # 1시간 데이터 사용
                data_key = f"{symbol}_{data_interval}"

                if data_key not in self.trading_model.features_data:
                    continue

                df = self.trading_model.features_data[data_key]
                if df is None or len(df) < 100:
                    continue

                print(f"[{symbol}] 시뮬레이션 실행...")

                for test_interval_hours in test_intervals:
                    result = self.simulate_trading_with_interval(
                        df, symbol, test_interval_hours
                    )
                    if result:
                        key = f"{symbol}_{test_interval_hours}h"
                        simulation_results[key] = result

        return simulation_results

    def simulate_trading_with_interval(self, df: pd.DataFrame, symbol: str,
                                     interval_hours: float) -> Optional[Dict]:
        """특정 주기로 거래 시뮬레이션"""
        try:
            # 간격을 데이터 포인트로 변환 (1시간 데이터 기준)
            interval_points = max(1, int(interval_hours))

            trades = []
            current_position = None
            entry_price = None
            entry_time = None

            # 미래 수익률 계산
            df['future_return'] = df['close'].shift(-interval_points) / df['close'] - 1

            for i in range(0, len(df) - interval_points, interval_points):
                current_price = df.iloc[i]['close']
                future_return = df.iloc[i]['future_return']

                if pd.isna(future_return):
                    continue

                # 레버리지 적용 수익률
                if symbol == 'NVDL':
                    leveraged_return = future_return * 3
                elif symbol == 'NVDQ':
                    leveraged_return = -future_return * 2  # 역 레버리지
                else:
                    leveraged_return = future_return

                profit_pct = leveraged_return * 100

                trades.append({
                    'entry_price': current_price,
                    'exit_price': current_price * (1 + future_return),
                    'profit_pct': profit_pct,
                    'holding_hours': interval_hours
                })

            if not trades:
                return None

            # 통계 계산
            profits = [trade['profit_pct'] for trade in trades]
            win_rate = sum(1 for p in profits if p > 0) / len(profits) * 100
            avg_profit = np.mean(profits)
            total_profit = sum(profits)
            sharpe_ratio = avg_profit / max(np.std(profits), 0.1)

            return {
                'symbol': symbol,
                'interval_hours': interval_hours,
                'total_trades': len(trades),
                'win_rate': win_rate,
                'avg_profit_per_trade': avg_profit,
                'total_profit': total_profit,
                'max_profit': max(profits),
                'min_profit': min(profits),
                'sharpe_ratio': sharpe_ratio,
                'trades': trades
            }

        except Exception as e:
            print(f"시뮬레이션 오류 ({symbol}, {interval_hours}h): {e}")
            return None

    def generate_analysis_report(self) -> str:
        """분석 보고서 생성"""
        print("분석 보고서 생성 중...")

        report_sections = []

        # 1. 기본 통계
        report_sections.append(" **NVDL/NVDQ 포지션 변경 주기 분석 보고서**")
        report_sections.append(f"📅 분석 날짜: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report_sections.append("")

        # 2. 전체 거래 통계
        if self.trade_intervals:
            avg_interval = np.mean(self.trade_intervals)
            median_interval = np.median(self.trade_intervals)
            report_sections.append(" **전체 거래 통계**")
            report_sections.append(f"- 총 거래 간격: {len(self.trade_intervals)}개")
            report_sections.append(f"- 평균 간격: {avg_interval:.1f}시간")
            report_sections.append(f"- 중간값 간격: {median_interval:.1f}시간")
            report_sections.append("")

        # 3. 보유 기간별 수익성
        if self.profitability_by_duration:
            report_sections.append(" **보유 기간별 수익성**")
            for duration, stats in self.profitability_by_duration.items():
                report_sections.append(
                    f"- {duration}: "
                    f"평균 {stats['avg_profit']:+.2f}%, "
                    f"승률 {stats['win_rate']:.1f}%, "
                    f"거래 {stats['count']}회"
                )
            report_sections.append("")

        # 4. 최적 주기 추천
        if self.optimal_intervals:
            report_sections.append(" **최적 거래 주기 추천**")
            top_3 = list(self.optimal_intervals.items())[:3]
            for i, (duration, analysis) in enumerate(top_3, 1):
                stats = analysis['stats']
                report_sections.append(
                    f"{i}. {duration}: "
                    f"점수 {analysis['score']:.3f}, "
                    f"평균수익 {stats['avg_profit']:+.2f}%, "
                    f"승률 {stats['win_rate']:.1f}%"
                )
            report_sections.append("")

        # 5. 시뮬레이션 결과
        simulation_results = self.simulate_different_intervals()
        if simulation_results:
            report_sections.append("🧪 **시뮬레이션 결과 (상위 3개)**")

            # 샤프 비율 기준 정렬
            sorted_results = sorted(
                simulation_results.items(),
                key=lambda x: x[1]['sharpe_ratio'],
                reverse=True
            )[:3]

            for i, (key, result) in enumerate(sorted_results, 1):
                report_sections.append(
                    f"{i}. {result['symbol']} {result['interval_hours']}시간: "
                    f"샤프비율 {result['sharpe_ratio']:.3f}, "
                    f"승률 {result['win_rate']:.1f}%, "
                    f"평균수익 {result['avg_profit_per_trade']:+.2f}%"
                )
            report_sections.append("")

        # 6. 권장사항
        report_sections.append(" **거래 권장사항**")

        if self.optimal_intervals:
            best_duration = list(self.optimal_intervals.keys())[0]
            report_sections.append(f"- 권장 보유 기간: {best_duration}")

        if simulation_results:
            best_sim = max(simulation_results.values(), key=lambda x: x['sharpe_ratio'])
            report_sections.append(f"- 권장 체크 주기: {best_sim['interval_hours']}시간")
            report_sections.append(f"- 예상 승률: {best_sim['win_rate']:.1f}%")

        report_sections.append("")
        report_sections.append(" 과거 데이터 기반 분석이며, 미래 성과를 보장하지 않습니다.")

        return "\n".join(report_sections)

    def send_analysis_report(self):
        """분석 보고서를 텔레그램으로 전송"""
        print("분석 보고서 전송 중...")

        try:
            # 데이터 로드 및 분석
            self.load_historical_data()

            # 보고서 생성
            report = self.generate_analysis_report()

            # 텔레그램 전송 (길이 제한으로 나누어 전송)
            max_length = 4000
            if len(report) <= max_length:
                self.telegram.send_message(report)
            else:
                # 여러 메시지로 나누어 전송
                parts = []
                current_part = ""

                for line in report.split('\n'):
                    if len(current_part + line + '\n') > max_length:
                        if current_part:
                            parts.append(current_part)
                            current_part = line + '\n'
                        else:
                            parts.append(line)
                    else:
                        current_part += line + '\n'

                if current_part:
                    parts.append(current_part)

                for i, part in enumerate(parts):
                    header = f" **보고서 {i+1}/{len(parts)}**\n\n" if i == 0 else f" **보고서 {i+1}/{len(parts)} (계속)**\n\n"
                    self.telegram.send_message(header + part)
                    time.sleep(2)  # 메시지 간 딜레이

            print("분석 보고서 전송 완료!")

        except Exception as e:
            print(f"보고서 전송 오류: {e}")
            self.telegram.notify_error("분석 보고서 오류", str(e))

    def get_recommended_check_interval(self) -> float:
        """권장 체크 주기 반환 (시간 단위)"""
        if not self.optimal_intervals:
            return 4.0  # 기본값 4시간

        # 최고 점수의 주기 추출
        best_duration = list(self.optimal_intervals.keys())[0]

        # 문자열에서 시간 추출
        if "1시간" in best_duration:
            return 1.0
        elif "1-4시간" in best_duration:
            return 2.0
        elif "4-12시간" in best_duration:
            return 6.0
        elif "12-24시간" in best_duration:
            return 12.0
        elif "1-3일" in best_duration:
            return 24.0
        else:
            return 4.0

    def get_position_change_frequency_estimate(self) -> str:
        """포지션 변경 빈도 추정"""
        recommended_interval = self.get_recommended_check_interval()

        # 하루 기준 예상 포지션 변경 횟수
        changes_per_day = 24 / recommended_interval

        if changes_per_day >= 6:
            return "매우 빈번 (하루 6회 이상)"
        elif changes_per_day >= 3:
            return "빈번 (하루 3-6회)"
        elif changes_per_day >= 1:
            return "보통 (하루 1-3회)"
        elif changes_per_day >= 0.5:
            return "드문 (2-3일에 1회)"
        else:
            return "매우 드문 (일주일에 1-2회)"

def main():
    """메인 실행 함수"""
    FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    if not FMP_API_KEY or FMP_API_KEY == "YOUR_API_KEY_HERE":
        print(" FMP API 키를 설정해주세요!")
        return

    # 분석 리포터 생성
    reporter = PositionAnalysisReporter(FMP_API_KEY)

    # 분석 보고서 생성 및 전송
    reporter.send_analysis_report()

    # 권장사항 출력
    print(f"\n📋 권장 체크 주기: {reporter.get_recommended_check_interval()}시간")
    print(f" 예상 포지션 변경 빈도: {reporter.get_position_change_frequency_estimate()}")

if __name__ == "__main__":
    main()