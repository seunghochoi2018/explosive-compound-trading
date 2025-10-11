#!/usr/bin/env python3
#-*- coding: utf-8 -*-
"""
KIS (SOXL/SOXS) Websocket 실시간 가격 모니터
- LLM 없음, 초경량
- 가격 변동 2% OR 거래량 급증 감지 → 7b 필터 트리거
"""
import json
import time
import threading
from datetime import datetime
from collections import deque

class KISWebsocketMonitor:
    """SOXL/SOXS 가격 실시간 감시 (한국투자증권 API 사용)"""

    def __init__(self, trigger_callback, symbols=['SOXL', 'SOXS']):
        """
        Args:
            trigger_callback: 트리거 발생 시 호출할 함수
            symbols: 감시할 종목 리스트
        """
        self.trigger_callback = trigger_callback
        self.symbols = symbols

        # 가격 데이터 (종목별)
        self.current_prices = {symbol: 0.0 for symbol in symbols}
        self.price_histories = {symbol: deque(maxlen=60) for symbol in symbols}

        # 트리거 조건
        self.PRICE_CHANGE_THRESHOLD = 2.0  # 2% 변동
        self.CHECK_INTERVAL = 1.0  # 1초마다 체크

        # 쿨다운
        self.last_trigger_times = {symbol: 0 for symbol in symbols}
        self.TRIGGER_COOLDOWN = 1.0

        # 모니터링 스레드
        self.running = False
        self.monitor_thread = None

        print("[Websocket] KIS 실시간 모니터 초기화")
        print(f"  감시 종목: {', '.join(symbols)}")
        print(f"  가격 변동 임계값: {self.PRICE_CHANGE_THRESHOLD}%")

    def fetch_current_prices(self):
        """현재 가격 조회 (한국투자증권 API)"""
        try:
            from us_stock_api_manager import USStockAPIManager
            from api_config import get_api_credentials

            # KIS API 초기화 (최초 1회만)
            if not hasattr(self, 'api'):
                creds = get_api_credentials()
                self.api = USStockAPIManager(
                    app_key=creds.get('app_key'),
                    app_secret=creds.get('app_secret'),
                    mock=False
                )

            # 각 종목 가격 조회
            for symbol in self.symbols:
                current_price = self.api.get_current_price(symbol)
                if current_price and current_price > 0:
                    self.update_price(symbol, current_price)

        except Exception as e:
            print(f"[Websocket ERROR] 가격 조회 실패: {e}")

    def update_price(self, symbol: str, price: float):
        """가격 업데이트 및 트리거 체크"""
        self.current_prices[symbol] = price
        self.price_histories[symbol].append(price)

        # 충분한 데이터가 쌓이면 체크
        if len(self.price_histories[symbol]) >= 10:
            self.check_triggers(symbol)

    def check_triggers(self, symbol: str):
        """트리거 조건 체크"""
        current_time = time.time()

        # 쿨다운 체크
        if current_time - self.last_trigger_times[symbol] < self.TRIGGER_COOLDOWN:
            return

        trigger_reason = None

        # 가격 급변동 체크 (최근 1분)
        price_history = self.price_histories[symbol]
        if len(price_history) >= 10:
            old_price = price_history[0]
            current_price = self.current_prices[symbol]
            price_change = abs((current_price - old_price) / old_price) * 100

            if price_change >= self.PRICE_CHANGE_THRESHOLD:
                trigger_reason = f"{symbol}_PRICE_SPIKE_{price_change:.2f}%"

        # 트리거 발동
        if trigger_reason:
            self.last_trigger_times[symbol] = current_time
            print(f"[Websocket] 트리거: {trigger_reason} @ ${self.current_prices[symbol]:.2f}")

            # 콜백 호출 (7b 필터 실행)
            if self.trigger_callback:
                threading.Thread(
                    target=self.trigger_callback,
                    args=(symbol, self.current_prices[symbol], trigger_reason),
                    daemon=True
                ).start()

    def monitor_loop(self):
        """모니터링 루프 (1초마다 가격 조회)"""
        while self.running:
            try:
                self.fetch_current_prices()
                time.sleep(self.CHECK_INTERVAL)
            except Exception as e:
                print(f"[Websocket ERROR] 모니터링 루프: {e}")
                time.sleep(5)

    def start(self):
        """모니터링 시작"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
            print("[Websocket] KIS 실시간 감시 시작")

    def stop(self):
        """모니터링 중지"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("[Websocket] KIS 실시간 감시 중지")

    def get_current_price(self, symbol: str) -> float:
        """현재 가격 조회"""
        return self.current_prices.get(symbol, 0.0)

if __name__ == "__main__":
    # 테스트
    def test_callback(symbol, price, reason):
        print(f"[TEST] 트리거 발동! 종목: {symbol}, 가격: ${price:.2f}, 이유: {reason}")

    monitor = KISWebsocketMonitor(trigger_callback=test_callback)
    monitor.start()

    try:
        while True:
            for symbol in monitor.symbols:
                price = monitor.get_current_price(symbol)
                if price > 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {symbol}: ${price:.2f}")
            time.sleep(5)
    except KeyboardInterrupt:
        monitor.stop()
        print("\n[종료]")
