#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 백그라운드 데이터 로더

주석: 사용자 요청 "거래하면서 데이터 다운받고 다운받은걸로 학습"
주석: 사용자 요청 "하튼 과거 대이터를 다 가지고 와 코드4 엔비디아 봇도"
- 봇 실행 중에 백그라운드에서 과거 데이터 계속 다운로드
- FMP API로 NVDL/NVDQ 과거 데이터 수집
- 다운받은 데이터로 즉시 백테스팅 → 학습 데이터 업데이트
"""

import threading
import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict
import os

class NVDLBackgroundLoader:
    """백그라운드에서 NVDL/NVDQ 과거 데이터 다운로드 및 학습 데이터 생성"""

    def __init__(self, trader_instance):
        """
        Args:
            trader_instance: LLMNVDLTrader 인스턴스 (trade_history 업데이트용)
        """
        self.trader = trader_instance
        self.running = False
        self.thread = None

        # FMP API 설정
        # 주석: 사용자 요청 "주식은 에프엠피로 해야지"
        # 주석: FMP_API_KEY = 5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI
        self.fmp_api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
        self.fmp_base_url = "https://financialmodelingprep.com/api/v3"

        # 진행 상태
        self.total_trades_generated = 0
        self.download_progress = 0

    def start(self):
        """백그라운드 다운로드 시작"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._background_worker, daemon=True)
        self.thread.start()
        print(f"[BG_LOADER] NVDL/NVDQ 백그라운드 학습 데이터 생성 시작")

    def stop(self):
        """중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _background_worker(self):
        """백그라운드 작업자 스레드"""
        try:
            # 주석: 사용자 요청 "이건 학습했을거니까 학습 안한부분부터 학습해야지"
            # 이미 학습 데이터가 있으면 스킵
            if self.trader.trade_history:
                print(f"[BG_LOADER] 기존 학습 데이터 {len(self.trader.trade_history):,}개 발견")
                print(f"[BG_LOADER] 백그라운드 학습 스킵 (이미 학습 완료)")
                self.download_progress = 100
                return

            # 전체 기간 데이터 수집
            # 주석: 사용자 요청 "최소 몇년거는 해야지"
            # 주석: 사용자 요청 "엔비디아도 구렇고" - 전체 기간으로 확장
            # 주석: 사용자 요청 "nvdq도 해야할거 아냐" - NVDQ도 전체 기간
            # NVDL은 2022년 6월 상장, NVDQ는 2023년 7월 상장
            end_time = datetime.now()

            # 1단계: NVDL 데이터 다운로드 (2022년 6월부터)
            nvdl_start = datetime(2022, 6, 1)
            print(f"[BG_LOADER] NVDL 데이터 다운로드 중... ({nvdl_start.strftime('%Y-%m-%d')} ~ {end_time.strftime('%Y-%m-%d')})")
            nvdl_data = self._fetch_historical_data('NVDL', nvdl_start, end_time)

            if nvdl_data:
                print(f"[BG_LOADER] NVDL: {len(nvdl_data):,}개 일봉 수집 완료")

            # 10초 대기
            time.sleep(10)

            # 2단계: NVDQ 데이터 다운로드 (2023년 7월부터)
            nvdq_start = datetime(2023, 7, 1)
            print(f"\n[BG_LOADER] NVDQ 데이터 다운로드 중... ({nvdq_start.strftime('%Y-%m-%d')} ~ {end_time.strftime('%Y-%m-%d')})")
            nvdq_data = self._fetch_historical_data('NVDQ', nvdq_start, end_time)

            if nvdq_data:
                print(f"[BG_LOADER] NVDQ: {len(nvdq_data):,}개 일봉 수집 완료")

            # 3단계: 백테스팅 실행
            if nvdl_data and nvdq_data and len(nvdl_data) > 10:
                print(f"\n[BG_LOADER] 백테스팅 시작...")
                new_trades = self._backtest_strategy(nvdl_data, nvdq_data)

                if new_trades:
                    # ===============================================================
                    # 📌 학습 데이터 자동 저장 (손실 방지)
                    # ===============================================================
                    # 주석: 사용자 요청 "주기적으로 저장하고"
                    # 주석: 사용자 요청 "통합안해도 돼? 메인봇하고?" - ETH봇과 동일한 자동저장 적용
                    # - 백테스팅 완료 후 즉시 저장
                    # - 메모리와 디스크 동시 업데이트
                    # - 프로그램 중단 시에도 데이터 보존
                    # ===============================================================

                    # 기존 데이터에 추가 (중복 방지)
                    existing_timestamps = {t.get('timestamp') for t in self.trader.trade_history}
                    unique_trades = [t for t in new_trades if t.get('timestamp') not in existing_timestamps]

                    if unique_trades:
                        self.trader.trade_history.extend(unique_trades)
                        self.trader.save_trade_history()  # 즉시 저장!

                        self.total_trades_generated = len(unique_trades)
                        print(f"[BG_LOADER] 새 학습 데이터 {len(unique_trades):,}개 추가 (총: {len(self.trader.trade_history):,}개)")
                        print(f"[AUTO_SAVE] 학습 데이터 자동 저장 완료")

            print(f"\n[BG_LOADER] 완료! 총 {self.total_trades_generated:,}개 학습 데이터 생성")
            self.download_progress = 100

        except Exception as e:
            print(f"[BG_LOADER ERROR] {e}")

    def _fetch_historical_data(self, symbol: str, start: datetime, end: datetime) -> List[Dict]:
        """FMP API로 과거 데이터 다운로드"""
        try:
            url = f"{self.fmp_base_url}/historical-price-full/{symbol}"
            params = {
                'apikey': self.fmp_api_key,
                'from': start.strftime('%Y-%m-%d'),
                'to': end.strftime('%Y-%m-%d')
            }

            response = requests.get(url, params=params, timeout=30)

            if response.status_code != 200:
                print(f"[BG_LOADER ERROR] {symbol} API 오류: {response.status_code}")
                return []

            data = response.json()

            if 'historical' not in data:
                print(f"[BG_LOADER ERROR] {symbol} 데이터 없음")
                return []

            # 데이터 파싱
            historical_data = []
            for item in data['historical']:
                historical_data.append({
                    'timestamp': datetime.strptime(item['date'], '%Y-%m-%d'),
                    'open': float(item['open']),
                    'high': float(item['high']),
                    'low': float(item['low']),
                    'close': float(item['close']),
                    'volume': float(item['volume'])
                })

            # 시간순 정렬 (오래된 것부터)
            historical_data.sort(key=lambda x: x['timestamp'])

            return historical_data

        except Exception as e:
            print(f"[BG_LOADER ERROR] {symbol} 다운로드 오류: {e}")
            return []

    def _backtest_strategy(self, nvdl_data: List[Dict], nvdq_data: List[Dict]) -> List[Dict]:
        """
        개선된 백테스팅 전략

        주석: 사용자 요청 "백테스팅개선 코드4 앤비디아 코드도"
        - 단순 모멘텀 비교 → 추세 돌파 + 볼륨 분석
        - 상대 강도 + 절대 강도 조합
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

        print(f"[BG_LOADER] 백테스팅 기간: {len(common_dates):,}일")

        for i in range(20, len(common_dates)):
            current_date = common_dates[i]

            nvdl = nvdl_dict[current_date]
            nvdq = nvdq_dict[current_date]

            # 최근 20일 분석
            prev_dates_20 = common_dates[i-20:i]
            prev_dates_5 = common_dates[i-5:i]

            # 고점/저점 계산
            nvdl_prices_20 = [nvdl_dict[d]['close'] for d in prev_dates_20]
            nvdq_prices_20 = [nvdq_dict[d]['close'] for d in prev_dates_20]

            nvdl_high = max(nvdl_prices_20)
            nvdl_low = min(nvdl_prices_20)
            nvdq_high = max(nvdq_prices_20)
            nvdq_low = min(nvdq_prices_20)

            # 볼륨 분석
            nvdl_volumes = [nvdl_dict[d]['volume'] for d in prev_dates_20]
            nvdq_volumes = [nvdq_dict[d]['volume'] for d in prev_dates_20]

            nvdl_avg_vol = sum(nvdl_volumes) / len(nvdl_volumes)
            nvdq_avg_vol = sum(nvdq_volumes) / len(nvdq_volumes)

            nvdl_vol_surge = nvdl['volume'] > nvdl_avg_vol * 1.3
            nvdq_vol_surge = nvdq['volume'] > nvdq_avg_vol * 1.3

            # 추세 강도 (5일)
            nvdl_prices_5 = [nvdl_dict[d]['close'] for d in prev_dates_5]
            nvdq_prices_5 = [nvdq_dict[d]['close'] for d in prev_dates_5]

            nvdl_trend_up = all(nvdl_prices_5[i] <= nvdl_prices_5[i+1] for i in range(len(nvdl_prices_5)-1))
            nvdq_trend_up = all(nvdq_prices_5[i] <= nvdq_prices_5[i+1] for i in range(len(nvdq_prices_5)-1))

            # 돌파 패턴
            nvdl_breakout = nvdl['close'] > nvdl_high and nvdl_vol_surge
            nvdq_breakout = nvdq['close'] > nvdq_high and nvdq_vol_surge

            # 상대 강도
            nvdl_momentum = (nvdl['close'] - nvdl_prices_20[0]) / nvdl_prices_20[0] * 100 if nvdl_prices_20[0] > 0 else 0
            nvdq_momentum = (nvdq['close'] - nvdq_prices_20[0]) / nvdq_prices_20[0] * 100 if nvdq_prices_20[0] > 0 else 0

            # 거래 로직
            if current_symbol is None:
                # 진입: 돌파 + 추세 + 상대 강도
                if nvdl_breakout and nvdl_trend_up and nvdl_momentum > nvdq_momentum:
                    current_symbol = "NVDL"
                    entry_price = nvdl['close']
                    entry_time = nvdl['timestamp']
                elif nvdq_breakout and nvdq_trend_up and nvdq_momentum > nvdl_momentum:
                    current_symbol = "NVDQ"
                    entry_price = nvdq['close']
                    entry_time = nvdq['timestamp']

            else:
                # 포지션 보유 중
                current_price = nvdl['close'] if current_symbol == "NVDL" else nvdq['close']
                holding_days = (nvdl['timestamp'] - entry_time).days
                pnl_pct = ((current_price - entry_price) / entry_price) * 100

                should_close = False

                # 조건 1: 손절/익절
                if pnl_pct <= -8.0 or pnl_pct >= 15.0:
                    should_close = True

                # 조건 2: 상대 강도 역전 (돌파 + 볼륨)
                elif current_symbol == "NVDL" and nvdq_breakout and nvdq_momentum > nvdl_momentum + 5.0:
                    should_close = True

                elif current_symbol == "NVDQ" and nvdl_breakout and nvdl_momentum > nvdq_momentum + 5.0:
                    should_close = True

                # 조건 3: 30일 이상 보유
                elif holding_days >= 30:
                    should_close = True

                if should_close:
                    # 트렌드 판단
                    nvdl_trend = 'up' if nvdl_trend_up else 'down'
                    nvdq_trend = 'up' if nvdq_trend_up else 'down'

                    # 거래 기록
                    trade = {
                        'timestamp': nvdl['timestamp'].isoformat(),
                        'symbol': current_symbol,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl_pct': round(pnl_pct, 2),
                        'result': 'WIN' if pnl_pct > 0 else 'LOSS',
                        'llm_reasoning': f"BG학습: 돌파={'NVDL' if nvdl_breakout else 'NVDQ' if nvdq_breakout else '없음'}, NVDL모멘텀{nvdl_momentum:+.1f}%, NVDQ모멘텀{nvdq_momentum:+.1f}%",
                        'llm_confidence': 85 if (nvdl_breakout or nvdq_breakout) and abs(nvdl_momentum - nvdq_momentum) > 5.0 else 65,
                        'nvdl_trend': nvdl_trend,
                        'nvdq_trend': nvdq_trend,
                        'holding_time_min': int(holding_days * 24 * 60),
                        'nvdl_breakout': nvdl_breakout,
                        'nvdq_breakout': nvdq_breakout
                    }

                    trades.append(trade)

                    # 포지션 초기화
                    current_symbol = None
                    entry_price = 0
                    entry_time = None

            # 진행률 표시
            if i % 50 == 0:
                progress = (i / len(common_dates) * 100)
                print(f"[BG_LOADER] 진행: {i:,}/{len(common_dates):,} ({progress:.1f}%) - 거래: {len(trades):,}개", end='\r')

        print(f"\n[BG_LOADER] 백테스팅 완료: {len(trades):,}개 거래 생성")
        return trades

    def get_status(self) -> Dict:
        """현재 상태"""
        return {
            'running': self.running,
            'progress': self.download_progress,
            'trades_generated': self.total_trades_generated,
            'total_history': len(self.trader.trade_history)
        }
