#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실시간 모니터링 + 자동 학습 시스템

기능:
1. ETH + KIS 봇 실시간 모니터링
2. 잔고 증가 추적
3. 손실 패턴 자동 감지 + 학습
4. 전략 자동 개선
5. 텔레그램 실시간 알림
"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import time
import json
from datetime import datetime, timedelta
from typing import Dict, List
from collections import deque

from telegram_notifier import TelegramNotifier

class ContinuousLearningMonitor:
    """연속 학습 모니터"""

    def __init__(self):
        print("="*80)
        print("실시간 모니터링 + 자동 학습 시스템")
        print("="*80)

        self.telegram = TelegramNotifier()

        # 모니터링 대상
        self.eth_history_file = "C:/Users/user/Documents/코드3/eth_trade_history.json"
        self.kis_history_file = "C:/Users/user/Documents/코드4/kis_trade_history.json"

        # 상태 추적
        self.last_eth_count = 0
        self.last_kis_count = 0

        # 잔고 추적
        self.eth_balance_history = deque(maxlen=100)
        self.kis_balance_history = deque(maxlen=100)

        # 학습 인사이트
        self.insights = {
            'eth': [],
            'kis': []
        }

        # 알림 설정
        self.alert_threshold = -3.0  # -3% 이상 손실 시 즉시 알림

        print("[OK] 모니터 초기화 완료")
        self.telegram.send_message(
            "🔍 실시간 모니터 시작\n\n"
            "기능:\n"
            "- 거래 실시간 추적\n"
            "- 손실 패턴 자동 감지\n"
            "- 잔고 증가 모니터링\n"
            "- 전략 자동 개선"
        )

    def load_eth_trades(self) -> List[Dict]:
        """ETH 거래 로드"""
        try:
            with open(self.eth_history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def load_kis_trades(self) -> List[Dict]:
        """KIS 거래 로드"""
        try:
            with open(self.kis_history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def analyze_new_trades(self, trades: List[Dict], asset_name: str) -> List[str]:
        """
        새 거래 분석 + 인사이트 도출

        체크 항목:
        1. 손실 패턴 (특히 큰 손실)
        2. 보유 시간
        3. 추세 방향
        4. 잔고 변화
        """
        insights = []

        for trade in trades:
            pnl = trade.get('pnl_pct', 0)
            holding_time = trade.get('holding_time_sec', trade.get('holding_time_min', 0))

            if isinstance(holding_time, (int, float)) and holding_time > 100:
                holding_time = holding_time / 60  # 초 → 분 변환

            # 1. 큰 손실 감지
            if pnl <= -5:
                insights.append({
                    'type': 'BIG_LOSS',
                    'asset': asset_name,
                    'pnl': pnl,
                    'holding_time': holding_time,
                    'reason': trade.get('reason', 'unknown'),
                    'action': '⚠️ 큰 손실 발생! 패턴 분석 필요',
                    'timestamp': trade.get('timestamp', '')
                })

            # 2. 120분 이상 보유 후 손실
            if holding_time > 120 and pnl < 0:
                insights.append({
                    'type': 'LONG_HOLD_LOSS',
                    'asset': asset_name,
                    'pnl': pnl,
                    'holding_time': holding_time,
                    'action': f'⚠️ {holding_time:.0f}분 보유 후 손실 → 보유시간 줄이기 권장',
                    'timestamp': trade.get('timestamp', '')
                })

            # 3. 빠른 손실 (10분 내)
            if holding_time < 10 and pnl <= -2:
                insights.append({
                    'type': 'FAST_LOSS',
                    'asset': asset_name,
                    'pnl': pnl,
                    'holding_time': holding_time,
                    'action': '⚠️ 빠른 손실 → 진입 타이밍 재검토 필요',
                    'timestamp': trade.get('timestamp', '')
                })

            # 4. 큰 수익 패턴 (학습용)
            if pnl >= 5:
                insights.append({
                    'type': 'BIG_WIN',
                    'asset': asset_name,
                    'pnl': pnl,
                    'holding_time': holding_time,
                    'action': f'✅ 큰 수익! 이 패턴 강화',
                    'timestamp': trade.get('timestamp', '')
                })

            # 5. 잔고 변화 추적
            if 'balance_change' in trade:
                balance_change = trade['balance_change']
                if balance_change < 0:
                    insights.append({
                        'type': 'BALANCE_DECREASE',
                        'asset': asset_name,
                        'change': balance_change,
                        'action': f'⚠️ 잔고 감소: {balance_change:+.6f}',
                        'timestamp': trade.get('timestamp', '')
                    })

        return insights

    def generate_improvement_suggestions(self, insights: List[Dict]) -> List[str]:
        """
        인사이트 기반 개선 제안

        자동으로 전략 조정 제안
        """
        suggestions = []

        # 그룹화
        big_losses = [i for i in insights if i['type'] == 'BIG_LOSS']
        long_hold_losses = [i for i in insights if i['type'] == 'LONG_HOLD_LOSS']
        fast_losses = [i for i in insights if i['type'] == 'FAST_LOSS']
        big_wins = [i for i in insights if i['type'] == 'BIG_WIN']

        # 큰 손실 많으면
        if len(big_losses) >= 3:
            suggestions.append(
                "🔧 큰 손실 3건 이상 발생\n"
                "→ 동적 손절 강화 권장 (-2% → -1.5%)"
            )

        # 장기 보유 손실 많으면
        if len(long_hold_losses) >= 5:
            suggestions.append(
                "🔧 120분 이상 보유 손실 5건 이상\n"
                "→ 최대 보유시간 단축 권장 (120분 → 60분)"
            )

        # 빠른 손실 많으면
        if len(fast_losses) >= 5:
            suggestions.append(
                "🔧 빠른 손실 5건 이상\n"
                "→ 최소 신뢰도 상향 권장 (75% → 80%)"
            )

        # 큰 수익 패턴 있으면
        if big_wins:
            avg_holding = sum(w['holding_time'] for w in big_wins) / len(big_wins)
            suggestions.append(
                f"✅ 큰 수익 패턴 발견\n"
                f"→ 평균 보유시간: {avg_holding:.0f}분\n"
                f"→ 이 시간대 강화 권장"
            )

        return suggestions

    def monitor_loop(self):
        """메인 모니터링 루프"""
        print("\n[시작] 실시간 모니터링")

        while True:
            try:
                # ETH 거래 체크
                eth_trades = self.load_eth_trades()

                if len(eth_trades) > self.last_eth_count:
                    new_eth = eth_trades[self.last_eth_count:]
                    print(f"\n[ETH] 새 거래 {len(new_eth)}건")

                    # 분석
                    insights = self.analyze_new_trades(new_eth, 'ETH')

                    if insights:
                        print(f"  인사이트: {len(insights)}건")

                        # 알림 필요한 것만
                        for insight in insights:
                            if insight['type'] in ['BIG_LOSS', 'LONG_HOLD_LOSS', 'BALANCE_DECREASE']:
                                self.telegram.send_message(
                                    f"📊 ETH 알림\n\n"
                                    f"{insight['action']}\n"
                                    f"PNL: {insight.get('pnl', 0):+.2f}%\n"
                                    f"시간: {insight.get('timestamp', '')[:16]}"
                                )

                        self.insights['eth'].extend(insights)

                    self.last_eth_count = len(eth_trades)

                # KIS 거래 체크
                kis_trades = self.load_kis_trades()

                if len(kis_trades) > self.last_kis_count:
                    new_kis = kis_trades[self.last_kis_count:]
                    print(f"\n[KIS] 새 거래 {len(new_kis)}건")

                    insights = self.analyze_new_trades(new_kis, 'KIS')

                    if insights:
                        print(f"  인사이트: {len(insights)}건")

                        for insight in insights:
                            if insight['type'] in ['BIG_LOSS', 'LONG_HOLD_LOSS', 'BALANCE_DECREASE']:
                                self.telegram.send_message(
                                    f"📊 KIS 알림\n\n"
                                    f"{insight['action']}\n"
                                    f"PNL: {insight.get('pnl', 0):+.2f}%\n"
                                    f"시간: {insight.get('timestamp', '')[:16]}"
                                )

                        self.insights['kis'].extend(insights)

                    self.last_kis_count = len(kis_trades)

                # 주기적 개선 제안 (1시간마다)
                if datetime.now().minute == 0:
                    self.send_periodic_report()

                time.sleep(60)  # 1분마다 체크

            except KeyboardInterrupt:
                print("\n[종료] 사용자 중단")
                break
            except Exception as e:
                print(f"[ERROR] 모니터링: {e}")
                time.sleep(60)

    def send_periodic_report(self):
        """주기적 리포트 전송 (1시간마다)"""
        try:
            # 최근 인사이트 기반 제안
            recent_insights = self.insights['eth'][-10:] + self.insights['kis'][-10:]

            if recent_insights:
                suggestions = self.generate_improvement_suggestions(recent_insights)

                if suggestions:
                    report = "📈 1시간 리포트\n\n" + "\n\n".join(suggestions)
                    self.telegram.send_message(report)

        except Exception as e:
            print(f"[ERROR] 리포트 전송: {e}")

if __name__ == "__main__":
    monitor = ContinuousLearningMonitor()
    monitor.monitor_loop()
