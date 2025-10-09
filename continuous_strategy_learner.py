#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
연속 전략 학습 시스템

기능:
1. 실시간 거래하면서 과거 데이터로 더 나은 전략 찾기
2. 획기적인 전략 발견 시 자동 교체
3. 검증 과정에서 안전장치 유지

방법:
- LLM 대신 통계적 분석 사용 (메모리 효율)
- 점진적 학습 (배치 처리)
- 실시간 백테스트
"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import time
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import statistics

sys.path.append('C:/Users/user/Documents/코드4')
from telegram_notifier import TelegramNotifier

class ContinuousStrategyLearner:
    """연속 전략 학습기"""

    def __init__(self):
        print("="*80)
        print("연속 전략 학습 시스템")
        print("="*80)
        print("목표: 실행 중 과거 데이터로 더 나은 전략 찾기")
        print("="*80)

        self.telegram = TelegramNotifier()

        # 현재 전략 설정
        self.current_strategies = {
            'eth': {
                'name': 'Explosive Compound v1',
                'max_holding_min': 60,
                'dynamic_stop_loss': -2.0,
                'avoid_trend_opposite': True,
                'compound_return': 4654,  # 기준 성능
                'win_rate': 64.2
            },
            'kis': {
                'name': 'SOXL 10-hour v1',
                'max_holding_hours': 10,
                'dynamic_stop_loss': -3.0,
                'trend_reversal_detection': True,
                'annual_return': 2634,
                'win_rate': 55.0
            }
        }

        # 거래 히스토리 파일
        self.history_files = {
            'eth': 'C:/Users/user/Documents/코드3/eth_trade_history.json',
            'kis': 'C:/Users/user/Documents/코드4/kis_trade_history.json'
        }

        # 후보 전략 저장
        self.candidate_strategies = []

        # 학습 상태
        self.learning_state = {
            'last_analysis': None,
            'total_analyses': 0,
            'strategies_tested': 0,
            'breakthroughs_found': 0
        }

        print("\n[초기화 완료]")

    def load_trade_history(self, asset: str) -> List[Dict]:
        """거래 히스토리 로드"""
        try:
            filepath = self.history_files.get(asset)
            if not filepath or not os.path.exists(filepath):
                print(f"[WARNING] {asset} 히스토리 없음")
                return []

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            print(f"[{asset.upper()}] 거래 히스토리: {len(data)}건")
            return data

        except Exception as e:
            print(f"[ERROR] 히스토리 로드 실패: {e}")
            return []

    def analyze_holding_time_patterns(self, trades: List[Dict]) -> Dict:
        """보유 시간 패턴 분석"""
        patterns = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnls': []})

        for t in trades:
            holding_min = t.get('holding_time_sec', 0) / 60
            pnl = t.get('pnl_pct', 0)

            # 10분 단위로 그룹화
            bucket = int(holding_min / 10) * 10

            patterns[bucket]['pnls'].append(pnl)
            if pnl > 0:
                patterns[bucket]['wins'] += 1
            else:
                patterns[bucket]['losses'] += 1

        # 통계 계산
        results = []
        for bucket, data in sorted(patterns.items()):
            total = len(data['pnls'])
            win_rate = data['wins'] / total * 100 if total > 0 else 0
            avg_pnl = statistics.mean(data['pnls']) if data['pnls'] else 0

            results.append({
                'holding_min_range': f"{bucket}-{bucket+10}분",
                'trades': total,
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'total_pnl': sum(data['pnls'])
            })

        return results

    def analyze_trend_patterns(self, trades: List[Dict]) -> Dict:
        """추세 패턴 분석"""
        patterns = {
            'with_trend': {'wins': 0, 'losses': 0, 'pnls': []},
            'against_trend': {'wins': 0, 'losses': 0, 'pnls': []},
            'sideways': {'wins': 0, 'losses': 0, 'pnls': []}
        }

        for t in trades:
            trend = t.get('market_1m_trend', 'unknown')
            side = t.get('side', 'unknown')
            pnl = t.get('pnl_pct', 0)

            # 추세 방향 판단
            if trend == 'up' and side == 'BUY':
                category = 'with_trend'
            elif trend == 'down' and side == 'SELL':
                category = 'with_trend'
            elif trend == 'sideways':
                category = 'sideways'
            else:
                category = 'against_trend'

            patterns[category]['pnls'].append(pnl)
            if pnl > 0:
                patterns[category]['wins'] += 1
            else:
                patterns[category]['losses'] += 1

        # 통계
        results = {}
        for category, data in patterns.items():
            total = len(data['pnls'])
            results[category] = {
                'trades': total,
                'win_rate': data['wins'] / total * 100 if total > 0 else 0,
                'avg_pnl': statistics.mean(data['pnls']) if data['pnls'] else 0,
                'total_pnl': sum(data['pnls'])
            }

        return results

    def test_new_strategy(self, trades: List[Dict], params: Dict) -> Dict:
        """새 전략 백테스트"""
        filtered_trades = []

        for t in trades:
            holding_min = t.get('holding_time_sec', 0) / 60
            trend = t.get('market_1m_trend', 'unknown')
            side = t.get('side', 'unknown')
            pnl = t.get('pnl_pct', 0)

            # 필터 적용
            # 1. 최대 보유 시간
            if 'max_holding_min' in params:
                if holding_min > params['max_holding_min']:
                    continue

            # 2. 추세 반대 진입 제외
            if params.get('avoid_trend_opposite', False):
                if (trend == 'up' and side == 'SELL') or (trend == 'down' and side == 'BUY'):
                    continue

            # 3. 최소 보유 시간
            if 'min_holding_min' in params:
                if holding_min < params['min_holding_min']:
                    continue

            filtered_trades.append(t)

        # 성과 계산
        if not filtered_trades:
            return None

        wins = [t for t in filtered_trades if t.get('pnl_pct', 0) > 0]
        win_rate = len(wins) / len(filtered_trades) * 100

        pnls = [t.get('pnl_pct', 0) for t in filtered_trades]
        avg_pnl = statistics.mean(pnls)

        # 복리 수익률 시뮬레이션
        balance = 1000
        for pnl in pnls:
            balance *= (1 + pnl / 100)

        compound_return = (balance - 1000) / 1000 * 100

        return {
            'params': params,
            'total_trades': len(filtered_trades),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'compound_return': compound_return,
            'filtered_from': len(trades)
        }

    def find_better_strategies(self, asset: str) -> Optional[Dict]:
        """더 나은 전략 찾기"""
        print(f"\n[전략 탐색] {asset.upper()} 분석 중...")

        trades = self.load_trade_history(asset)
        if len(trades) < 100:
            print(f"[건너뜀] 거래 데이터 부족 ({len(trades)}건)")
            return None

        current_strategy = self.current_strategies.get(asset)
        if not current_strategy:
            return None

        print(f"현재 전략: {current_strategy['name']}")
        print(f"  기준 성능: {current_strategy.get('compound_return', 0):,.0f}%")

        # 다양한 파라미터 조합 테스트
        test_cases = []

        if asset == 'eth':
            # ETH 전략 조합
            for max_holding in [30, 45, 60, 90, 120]:
                for min_holding in [0, 5, 10]:
                    for avoid_opposite in [True, False]:
                        test_cases.append({
                            'max_holding_min': max_holding,
                            'min_holding_min': min_holding,
                            'avoid_trend_opposite': avoid_opposite
                        })

        elif asset == 'kis':
            # KIS 전략 조합
            for max_holding in [4, 6, 8, 10, 12]:
                for min_holding in [0, 1, 2]:
                    test_cases.append({
                        'max_holding_min': max_holding * 60,  # 시간 → 분
                        'min_holding_min': min_holding * 60,
                        'avoid_trend_opposite': True
                    })

        # 전략 테스트
        best_strategy = None
        best_return = current_strategy.get('compound_return', 0)

        print(f"\n테스트할 전략: {len(test_cases)}개")

        for i, params in enumerate(test_cases):
            result = self.test_new_strategy(trades, params)

            if result and result['compound_return'] > best_return * 1.2:  # 20% 이상 개선
                best_return = result['compound_return']
                best_strategy = result

                print(f"\n🚀 획기적 전략 발견! (테스트 {i+1}/{len(test_cases)})")
                print(f"  복리 수익: {result['compound_return']:,.1f}%")
                print(f"  승률: {result['win_rate']:.1f}%")
                print(f"  거래 수: {result['total_trades']}/{result['filtered_from']}")
                print(f"  파라미터: {params}")

            if (i + 1) % 50 == 0:
                print(f"  진행: {i+1}/{len(test_cases)}...")

        self.learning_state['strategies_tested'] += len(test_cases)

        if best_strategy:
            self.learning_state['breakthroughs_found'] += 1
            return best_strategy

        print(f"[결과] 현재 전략이 최적")
        return None

    def validate_strategy(self, asset: str, strategy: Dict) -> bool:
        """전략 검증 (안전장치)"""
        print(f"\n[검증] {asset.upper()} 새 전략 검증 중...")

        # 기본 검증
        if strategy['total_trades'] < 50:
            print(f"[실패] 거래 수 부족 ({strategy['total_trades']} < 50)")
            return False

        if strategy['win_rate'] < 50:
            print(f"[실패] 승률 부족 ({strategy['win_rate']:.1f}% < 50%)")
            return False

        # 현재 전략 대비 개선도
        current = self.current_strategies[asset]
        improvement = strategy['compound_return'] / current.get('compound_return', 1)

        if improvement < 1.2:
            print(f"[실패] 개선도 부족 ({improvement:.2f}x < 1.2x)")
            return False

        print(f"[통과] 검증 완료")
        print(f"  개선도: {improvement:.2f}x")
        print(f"  복리 수익: {strategy['compound_return']:,.1f}%")
        print(f"  승률: {strategy['win_rate']:.1f}%")

        return True

    def deploy_new_strategy(self, asset: str, strategy: Dict):
        """새 전략 배포"""
        print(f"\n[배포] {asset.upper()} 전략 교체")

        # 백업
        backup_file = f"strategy_backup_{asset}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_strategies[asset], f, indent=2, ensure_ascii=False)

        print(f"[백업] 현재 전략 저장: {backup_file}")

        # 새 전략으로 업데이트
        if asset == 'eth':
            new_config = {
                'name': f"Explosive v2 (Auto-learned {datetime.now().strftime('%Y-%m-%d')})",
                'max_holding_min': strategy['params']['max_holding_min'],
                'min_holding_min': strategy['params'].get('min_holding_min', 0),
                'avoid_trend_opposite': strategy['params'].get('avoid_trend_opposite', True),
                'compound_return': strategy['compound_return'],
                'win_rate': strategy['win_rate'],
                'dynamic_stop_loss': -2.5,  # 검증 기간 동안 안전하게
                'verification_trades': 0  # 검증 카운터 초기화
            }

            # ETH 봇 설정 파일 업데이트
            strategy_file = 'C:/Users/user/Documents/코드3/eth_current_strategy.json'

        elif asset == 'kis':
            new_config = {
                'name': f"SOXL v2 (Auto-learned {datetime.now().strftime('%Y-%m-%d')})",
                'max_holding_hours': strategy['params']['max_holding_min'] / 60,
                'min_holding_hours': strategy['params'].get('min_holding_min', 0) / 60,
                'trend_reversal_detection': True,
                'annual_return': strategy['compound_return'],
                'win_rate': strategy['win_rate'],
                'dynamic_stop_loss': -3.5,  # 검증 기간 동안 안전하게
                'verification_trades': 0
            }

            strategy_file = 'C:/Users/user/Documents/코드4/kis_current_strategy.json'

        # 저장
        with open(strategy_file, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=2, ensure_ascii=False)

        # 업데이트
        self.current_strategies[asset] = new_config

        print(f"[완료] 전략 배포 완료")
        print(f"  파일: {strategy_file}")

        # 텔레그램 알림
        self.telegram.send_message(
            f"🚀 획기적 전략 발견 & 배포!\n\n"
            f"자산: {asset.upper()}\n"
            f"전략: {new_config['name']}\n\n"
            f"성능:\n"
            f"  복리 수익: {strategy['compound_return']:,.1f}%\n"
            f"  승률: {strategy['win_rate']:.1f}%\n"
            f"  거래 수: {strategy['total_trades']}\n\n"
            f"⚠️ 검증 기간:\n"
            f"  손절: {new_config['dynamic_stop_loss']}%\n"
            f"  100거래 후 자동 조정"
        )

    def continuous_learning_loop(self):
        """연속 학습 루프"""
        print("\n[시작] 연속 학습 시작")
        print("주기: 1시간마다 새 전략 탐색")

        cycle = 0

        while True:
            try:
                cycle += 1
                print(f"\n{'='*80}")
                print(f"[학습 사이클 {cycle}] {datetime.now()}")
                print(f"{'='*80}")

                # ETH 전략 학습
                print("\n--- ETH 전략 탐색 ---")
                eth_strategy = self.find_better_strategies('eth')

                if eth_strategy:
                    if self.validate_strategy('eth', eth_strategy):
                        self.deploy_new_strategy('eth', eth_strategy)
                    else:
                        print("[거부] 검증 실패")

                # KIS 전략 학습
                print("\n--- KIS 전략 탐색 ---")
                kis_strategy = self.find_better_strategies('kis')

                if kis_strategy:
                    if self.validate_strategy('kis', kis_strategy):
                        self.deploy_new_strategy('kis', kis_strategy)
                    else:
                        print("[거부] 검증 실패")

                # 상태 업데이트
                self.learning_state['last_analysis'] = datetime.now()
                self.learning_state['total_analyses'] += 1

                print(f"\n[학습 통계]")
                print(f"  총 분석: {self.learning_state['total_analyses']}회")
                print(f"  테스트한 전략: {self.learning_state['strategies_tested']}개")
                print(f"  발견한 획기적 전략: {self.learning_state['breakthroughs_found']}개")

                # 1시간 대기
                print(f"\n다음 분석까지 1시간 대기...")
                time.sleep(3600)

            except KeyboardInterrupt:
                print("\n[종료] 사용자 중단")
                break

            except Exception as e:
                print(f"[ERROR] 학습 오류: {e}")
                time.sleep(60)

    def run(self):
        """메인 실행"""
        print("\n[실행] 연속 전략 학습 시작")

        self.telegram.send_message(
            "🧠 연속 전략 학습 시작\n\n"
            "목표: 실시간 거래하면서\n"
            "과거 데이터로 더 나은 전략 발견\n\n"
            "주기: 1시간마다\n"
            "기준: 현재 대비 20%+ 개선"
        )

        self.continuous_learning_loop()

if __name__ == "__main__":
    learner = ContinuousStrategyLearner()
    learner.run()
