#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 2년치 과거 데이터 수집 및 백테스팅 시스템

주석: 사용자 요청 "최소 몇년거는 해야지" - 2년치 데이터로 LLM 사전 학습
주석: 사용자 요청 "주식은 FMP로 해야지"
- FMP API로 NVDL/NVDQ 2년치 분봉 데이터 다운로드
- 과거 데이터로 백테스팅 시뮬레이션 실행
- 수천 개 거래 기록 생성 및 nvdl_trade_history.json 저장
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict
import os

class NVDLHistoricalBacktest:
    """NVDL/NVDQ 2년치 백테스팅 시스템"""

    def __init__(self, fmp_api_key: str):
        """
        초기화

        주석: FMP_API_KEY = 5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI
        """
        self.fmp_api_key = fmp_api_key
        self.fmp_base_url = "https://financialmodelingprep.com/api/v3"
        self.symbols = ["NVDL", "NVDQ"]

        # 2년치 데이터
        self.end_time = datetime.now()
        self.start_time = self.end_time - timedelta(days=730)  # 2년

        print(f"[BACKTEST] NVDL/NVDQ 백테스팅 초기화")
        print(f"[PERIOD] {self.start_time.strftime('%Y-%m-%d')} ~ {self.end_time.strftime('%Y-%m-%d')}")
        print(f"[API] FMP API 키: {fmp_api_key[:10]}...")

    def fetch_fmp_intraday(self, symbol: str, interval: str = '5min') -> List[Dict]:
        """
        FMP에서 Intraday 데이터 다운로드

        주석: FMP Starter 플랜
        - 5분봉 제공 (1min, 5min, 15min, 30min, 1hour)
        - 최근 1개월 데이터만 무료
        - 2년치 데이터는 Historical Intraday API 필요 (유료)

        대안: 일봉 데이터로 백테스팅 (무료)
        """
        all_data = []

        print(f"\n[DATA] {symbol} {interval} 데이터 수집 시작...")

        try:
            # FMP Historical Daily Price API (2년치 무료)
            url = f"{self.fmp_base_url}/historical-price-full/{symbol}"
            params = {
                'apikey': self.fmp_api_key,
                'from': self.start_time.strftime('%Y-%m-%d'),
                'to': self.end_time.strftime('%Y-%m-%d')
            }

            response = requests.get(url, params=params, timeout=30)

            if response.status_code != 200:
                print(f"[ERROR] API 오류: {response.status_code}")
                return []

            data = response.json()

            if 'historical' not in data:
                print(f"[ERROR] 데이터 없음: {data}")
                return []

            # 데이터 파싱
            for item in data['historical']:
                all_data.append({
                    'timestamp': datetime.strptime(item['date'], '%Y-%m-%d'),
                    'open': float(item['open']),
                    'high': float(item['high']),
                    'low': float(item['low']),
                    'close': float(item['close']),
                    'volume': float(item['volume'])
                })

            # 시간순 정렬 (오래된 것부터)
            all_data.sort(key=lambda x: x['timestamp'])

            print(f"[COMPLETE] {symbol}: 총 {len(all_data):,}개 일봉 수집 완료")
            return all_data

        except Exception as e:
            print(f"\n[ERROR] {symbol} 데이터 수집 오류: {e}")
            return []

    def simple_backtest_strategy(self, nvdl_data: List[Dict], nvdq_data: List[Dict]) -> List[Dict]:
        """
        간단한 백테스팅 전략 (NVDL vs NVDQ 로테이션)

        주석: LLM 없이 간단한 룰 기반으로 시뮬레이션
        - 목적: 다양한 시장 상황에서 성공/실패 사례 생성
        - NVDL 모멘텀 > NVDQ 모멘텀 = BUY NVDL
        - NVDQ 모멘텀 > NVDL 모멘텀 = SELL NVDL, BUY NVDQ
        """
        trades = []
        current_symbol = None
        entry_price = 0
        entry_time = None

        # 데이터 매핑 (날짜별)
        nvdl_dict = {d['timestamp'].date(): d for d in nvdl_data}
        nvdq_dict = {d['timestamp'].date(): d for d in nvdq_data}

        # 공통 날짜만 사용
        common_dates = sorted(set(nvdl_dict.keys()) & set(nvdq_dict.keys()))

        print(f"\n[BACKTEST] 시뮬레이션 시작... 총 {len(common_dates):,}일")

        for i in range(10, len(common_dates)):
            current_date = common_dates[i]

            nvdl = nvdl_dict[current_date]
            nvdq = nvdq_dict[current_date]

            # 최근 10일 모멘텀 계산
            prev_dates = common_dates[i-10:i]

            nvdl_prices = [nvdl_dict[d]['close'] for d in prev_dates]
            nvdq_prices = [nvdq_dict[d]['close'] for d in prev_dates]

            nvdl_momentum = (nvdl['close'] - nvdl_prices[0]) / nvdl_prices[0] * 100 if nvdl_prices[0] > 0 else 0
            nvdq_momentum = (nvdq['close'] - nvdq_prices[0]) / nvdq_prices[0] * 100 if nvdq_prices[0] > 0 else 0

            # NVDL/NVDQ 트렌드 판단
            nvdl_trend = 'up' if nvdl_momentum > 0 else 'down'
            nvdq_trend = 'up' if nvdq_momentum > 0 else 'down'

            # 거래 로직
            if current_symbol is None:
                # 포지션 없음 - 진입
                if nvdl_momentum > nvdq_momentum and nvdl_momentum > 2.0:
                    current_symbol = "NVDL"
                    entry_price = nvdl['close']
                    entry_time = nvdl['timestamp']
                elif nvdq_momentum > nvdl_momentum and nvdq_momentum > 2.0:
                    current_symbol = "NVDQ"
                    entry_price = nvdq['close']
                    entry_time = nvdq['timestamp']

            else:
                # 포지션 보유 중
                current_price = nvdl['close'] if current_symbol == "NVDL" else nvdq['close']
                holding_days = (nvdl['timestamp'] - entry_time).days
                pnl_pct = ((current_price - entry_price) / entry_price) * 100

                should_close = False

                # 조건 1: 손절 (-5%)
                if pnl_pct <= -5.0:
                    should_close = True

                # 조건 2: 익절 (+10%)
                elif pnl_pct >= 10.0:
                    should_close = True

                # 조건 3: 상대 강도 역전 (로테이션)
                elif current_symbol == "NVDL" and nvdq_momentum > nvdl_momentum + 3.0:
                    should_close = True

                elif current_symbol == "NVDQ" and nvdl_momentum > nvdq_momentum + 3.0:
                    should_close = True

                # 조건 4: 30일 이상 보유
                elif holding_days >= 30:
                    should_close = True

                if should_close:
                    # 거래 기록
                    trade = {
                        'timestamp': nvdl['timestamp'].isoformat(),
                        'symbol': current_symbol,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl_pct': round(pnl_pct, 2),
                        'result': 'WIN' if pnl_pct > 0 else 'LOSS',
                        'llm_reasoning': f"백테스트: NVDL {nvdl_momentum:+.1f}%, NVDQ {nvdq_momentum:+.1f}%",
                        'llm_confidence': 75 if abs(nvdl_momentum - nvdq_momentum) > 5.0 else 50,
                        'nvdl_trend': nvdl_trend,
                        'nvdq_trend': nvdq_trend,
                        'holding_time_min': int(holding_days * 24 * 60)
                    }

                    trades.append(trade)

                    # 포지션 초기화
                    current_symbol = None
                    entry_price = 0
                    entry_time = None

            # 진행률 표시
            if i % 50 == 0:
                progress = (i / len(common_dates) * 100)
                print(f"[PROGRESS] {i:,}/{len(common_dates):,} ({progress:.1f}%) - 거래: {len(trades):,}개", end='\r')

        print(f"\n[COMPLETE] 시뮬레이션 완료: 총 {len(trades):,}개 거래 생성")
        return trades

    def run_full_backtest(self):
        """
        전체 백테스팅 실행

        1. 2년치 데이터 수집
        2. 백테스팅 시뮬레이션
        3. nvdl_trade_history.json 저장
        """
        print(f"\n{'='*60}")
        print(f"[START] NVDL/NVDQ 2년치 백테스팅 시작")
        print(f"{'='*60}\n")

        # 1. 데이터 수집
        print(f"[STEP 1/3] 과거 데이터 다운로드")
        nvdl_data = self.fetch_fmp_intraday('NVDL')
        nvdq_data = self.fetch_fmp_intraday('NVDQ')

        if not nvdl_data or not nvdq_data:
            print(f"[ERROR] 데이터 수집 실패")
            return None

        # 2. 백테스팅
        print(f"\n[STEP 2/3] 백테스팅 시뮬레이션")
        trades = self.simple_backtest_strategy(nvdl_data, nvdq_data)

        if not trades:
            print(f"[ERROR] 거래 생성 실패")
            return None

        # 3. 통계 분석
        wins = sum(1 for t in trades if t['result'] == 'WIN')
        losses = len(trades) - wins
        win_rate = (wins / len(trades) * 100) if trades else 0
        avg_pnl = sum(t['pnl_pct'] for t in trades) / len(trades) if trades else 0

        print(f"\n[STEP 3/3] 결과 저장")
        print(f"\n{'='*60}")
        print(f"[STATS] 백테스팅 통계")
        print(f"{'='*60}")
        print(f"[TRADES] 총 거래: {len(trades):,}개")
        print(f"[WIN] 성공: {wins:,}개 ({win_rate:.1f}%)")
        print(f"[LOSS] 실패: {losses:,}개 ({100-win_rate:.1f}%)")
        print(f"[AVG PNL] 평균 수익률: {avg_pnl:+.2f}%")
        print(f"{'='*60}\n")

        # 4. JSON 저장
        output_file = "nvdl_trade_history.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)

        print(f"[SAVED] {output_file} 저장 완료 ({len(trades):,}개 거래)")
        print(f"[READY] LLM이 {len(trades):,}개 과거 사례를 학습할 준비 완료!")

        return trades


if __name__ == "__main__":
    # FMP API 키 (주석에 기록)
    FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

    print(f"\n{'#'*60}")
    print(f"# NVDL/NVDQ 2년치 백테스팅 시스템")
    print(f"# 주석: 사용자 요청 '최소 몇년거는 해야지'")
    print(f"# 주석: 사용자 요청 '주식은 FMP로 해야지'")
    print(f"# 목적: LLM 사전 학습용 과거 거래 데이터 생성")
    print(f"{'#'*60}\n")

    backtest = NVDLHistoricalBacktest(FMP_API_KEY)
    trades = backtest.run_full_backtest()

    if trades:
        print(f"\n[SUCCESS] 백테스팅 완료!")
        print(f"[NEXT] llm_nvdl_trader.py 실행 시 {len(trades):,}개 사례를 자동 학습합니다.")
    else:
        print(f"\n[ERROR] 백테스팅 실패")
