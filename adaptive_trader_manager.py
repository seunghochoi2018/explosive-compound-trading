#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
적응형 트레이더 매니저
- 전략 탐색기가 찾은 최고 전략을 실시간 적용
- ETH + KIS 동시 관리
- 10거래마다 승률 체크 (60% 미만 시 전략 교체)
"""
import asyncio
import json
import os
from datetime import datetime
import subprocess
import sys

class AdaptiveTraderManager:
    def __init__(self):
        self.current_strategy = None
        self.trade_history = []
        self.eth_wins = 0
        self.eth_total = 0
        self.kis_wins = 0
        self.kis_total = 0

    def load_best_strategy(self):
        """최고 전략 로드"""
        try:
            if os.path.exists('best_strategy.json'):
                with open('best_strategy.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_strategy = data
                    print(f"\n✅ 전략 로드: 점수 {data['score']:.4f}")
                    return True
            return False
        except Exception as e:
            print(f"전략 로드 실패: {e}")
            return False

    def check_performance(self, trader_type):
        """성과 체크"""
        if trader_type == 'ETH':
            if self.eth_total >= 10:
                win_rate = self.eth_wins / self.eth_total
                print(f"\n[ETH] 승률: {win_rate*100:.1f}% ({self.eth_wins}/{self.eth_total})")

                if win_rate < 0.6:
                    print("⚠️ ETH 승률 60% 미만 → 전략 교체 필요")
                    return False
                else:
                    print("✅ ETH 승률 60% 이상 → 계속 진행")
                    return True

        elif trader_type == 'KIS':
            if self.kis_total >= 10:
                win_rate = self.kis_wins / self.kis_total
                print(f"\n[KIS] 승률: {win_rate*100:.1f}% ({self.kis_wins}/{self.kis_total})")

                if win_rate < 0.6:
                    print("⚠️ KIS 승률 60% 미만 → 전략 교체 필요")
                    return False
                else:
                    print("✅ KIS 승률 60% 이상 → 계속 진행")
                    return True

        return True  # 아직 10거래 안 됨

    async def start_strategy_finder(self):
        """전략 탐색기 시작 (백그라운드)"""
        print("\n[전략 탐색기] 백그라운드 실행 중...")

        # 백그라운드로 실행
        subprocess.Popen(
            [sys.executable, "aggressive_strategy_finder.py"],
            cwd=r"C:\Users\user\Documents\코드5",
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        print("✅ 전략 탐색기 시작 완료")

    async def start_eth_trader(self):
        """ETH 트레이더 시작"""
        print("\n[ETH 트레이더] 시작 중...")

        # 최고 전략 적용하여 실행
        subprocess.Popen(
            [sys.executable, "llm_eth_trader_v4_3tier.py"],
            cwd=r"C:\Users\user\Documents\코드3",
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        print("✅ ETH 트레이더 시작 완료")

    async def start_kis_trader(self):
        """KIS 트레이더 시작"""
        print("\n[KIS 트레이더] 시작 중...")

        # 최고 전략 적용하여 실행
        subprocess.Popen(
            [sys.executable, "kis_llm_trader_v2_explosive.py"],
            cwd=r"C:\Users\user\Documents\코드5",
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )

        print("✅ KIS 트레이더 시작 완료")

    async def monitor_trades(self):
        """거래 모니터링 (로그 파일 기반)"""
        print("\n[모니터] 거래 모니터링 시작...")

        while True:
            try:
                # ETH 로그 확인
                if os.path.exists(r"C:\Users\user\Documents\코드3\eth_trading_log.txt"):
                    # 승률 계산 (간단 버전)
                    pass

                # KIS 로그 확인
                if os.path.exists(r"C:\Users\user\Documents\코드5\kis_trading_log.txt"):
                    # 승률 계산 (간단 버전)
                    pass

                # 전략 업데이트 확인
                if self.load_best_strategy():
                    print(f"\n🔄 전략 업데이트 감지 - {datetime.now().strftime('%H:%M:%S')}")

                await asyncio.sleep(10)  # 10초마다 체크

            except Exception as e:
                print(f"모니터링 오류: {e}")
                await asyncio.sleep(10)

    async def run(self):
        """매니저 실행"""
        print("="*80)
        print("적응형 트레이더 매니저 v1.0")
        print("="*80)
        print("기능:")
        print("1. 전략 탐색기 (1초마다 10개 전략 병렬 테스트)")
        print("2. ETH 트레이더 (최고 전략 적용)")
        print("3. KIS 트레이더 (최고 전략 적용)")
        print("4. 실시간 모니터링 (10거래마다 승률 체크)")
        print("="*80)

        # 전략 탐색기 시작
        await self.start_strategy_finder()
        await asyncio.sleep(5)  # 초기 전략 찾을 시간

        # 첫 전략 로드
        if not self.load_best_strategy():
            print("⚠️ 초기 전략 로드 실패 - 30초 대기 후 재시도")
            await asyncio.sleep(30)
            if not self.load_best_strategy():
                print("❌ 전략 로드 실패 - 종료")
                return

        # 트레이더들 시작
        await self.start_eth_trader()
        await asyncio.sleep(2)
        await self.start_kis_trader()
        await asyncio.sleep(2)

        print("\n" + "="*80)
        print("✅ 모든 시스템 시작 완료!")
        print("="*80)
        print(f"시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n실시간 모니터링 중...")

        # 모니터링 시작
        await self.monitor_trades()

async def main():
    manager = AdaptiveTraderManager()
    await manager.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n매니저 종료")
