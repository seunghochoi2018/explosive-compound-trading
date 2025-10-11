#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자기 개선 엔진 (Self-Improvement Engine)
- 주기적 성과 분석 (1시간마다)
- 문제점 자동 탐지
- A급 개선 즉시 적용
- B급 개선 시뮬레이션 후 적용
- 메타 학습 (어떤 개선이 효과적인가?)
- 텔레그램 리포트 (6시간마다)
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import statistics
import requests

#  Ollama LLM 설정 (11436 포트 - 자기개선 엔진 전용)
OLLAMA_HOST = "http://127.0.0.1:11436"
OLLAMA_MODEL = "qwen2.5:14b"
OLLAMA_TIMEOUT = 60  # LLM 응답 타임아웃 60초


class SelfImprovementEngine:
    """자기 개선 엔진 - 각 봇이 스스로 학습하고 개선"""

    def __init__(self, bot_name: str, trading_history_file: str, strategy_file: str, telegram_config: dict = None):
        """
        Args:
            bot_name: 봇 이름 (ETH, KIS 등)
            trading_history_file: 거래 히스토리 JSON 파일 경로
            strategy_file: 현재 전략 JSON 파일 경로
            telegram_config: {'bot_token': str, 'chat_id': str}
        """
        self.bot_name = bot_name
        self.trading_history_file = trading_history_file
        self.strategy_file = strategy_file
        self.telegram_config = telegram_config

        # 분석 주기
        self.analysis_interval = 3600  # 1시간 (초)
        self.report_interval = 6 * 3600  # 6시간 (초)

        # 개선 히스토리
        self.improvement_history = []
        self.last_analysis_time = time.time()
        self.last_report_time = time.time()

        # 현재 전략 파라미터
        self.current_strategy = self.load_strategy()

        print(f"[{self.bot_name}] 자기 개선 엔진 초기화 완료")
        print(f"  - 분석 주기: 1시간")
        print(f"  - 리포트 주기: 6시간")

    def load_strategy(self) -> Dict:
        """현재 전략 로드"""
        try:
            with open(self.strategy_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                'stop_loss_pct': -2.5,
                'max_hold_minutes': 60,
                'min_confidence': 75,
                'trend_check_enabled': True
            }

    def save_strategy(self):
        """전략 저장"""
        try:
            with open(self.strategy_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_strategy, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[{self.bot_name}] 전략 저장 실패: {e}")

    def load_trading_history(self, hours: int = 24) -> List[Dict]:
        """최근 N시간 거래 히스토리 로드"""
        try:
            with open(self.trading_history_file, 'r', encoding='utf-8') as f:
                all_trades = json.load(f)

            cutoff_time = datetime.now() - timedelta(hours=hours)

            recent_trades = []
            for trade in all_trades:
                try:
                    trade_time = datetime.fromisoformat(trade.get('timestamp', ''))
                    if trade_time >= cutoff_time:
                        recent_trades.append(trade)
                except:
                    continue

            return recent_trades
        except:
            return []

    def analyze_performance(self, hours: int = 24) -> Dict:
        """성과 분석"""
        trades = self.load_trading_history(hours)

        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'total_return': 0
            }

        wins = [t for t in trades if t.get('profit_pct', 0) > 0]
        losses = [t for t in trades if t.get('profit_pct', 0) < 0]

        win_rate = len(wins) / len(trades) * 100 if trades else 0
        avg_profit = statistics.mean([t['profit_pct'] for t in wins]) if wins else 0
        avg_loss = statistics.mean([t['profit_pct'] for t in losses]) if losses else 0
        total_return = sum([t.get('profit_pct', 0) for t in trades])

        return {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': round(win_rate, 1),
            'avg_profit': round(avg_profit, 2),
            'avg_loss': round(avg_loss, 2),
            'total_return': round(total_return, 2)
        }

    def ask_llm(self, prompt: str) -> str:
        """ LLM에게 분석 요청 (11436 포트)"""
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=OLLAMA_TIMEOUT
            )

            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                print(f"[{self.bot_name}] LLM 응답 오류: {response.status_code}")
                return ""

        except requests.Timeout:
            print(f"[{self.bot_name}] LLM 타임아웃 (60초 초과)")
            return ""
        except Exception as e:
            print(f"[{self.bot_name}] LLM 오류: {e}")
            return ""

    def llm_analyze_trades(self, trades: List[Dict], performance: Dict) -> List[Dict]:
        """ LLM이 거래 패턴을 분석하고 개선안 제시"""
        if len(trades) < 5:
            return []  # 데이터 부족

        # 최근 20건만 분석 (너무 많으면 LLM 과부하)
        recent_trades = trades[-20:]

        # 거래 요약
        trades_summary = []
        for t in recent_trades:
            summary = f"- {t.get('action', '?')}: {t.get('profit_pct', 0):+.2f}%, 보유 {t.get('hold_minutes', 0):.0f}분, 트렌드 {t.get('trend', '?')}"
            trades_summary.append(summary)

        trades_text = "\n".join(trades_summary)

        # LLM 프롬프트
        prompt = f"""당신은 암호화폐/주식 트레이딩 전문가입니다. 다음 거래 데이터를 분석하고 문제점과 개선 방안을 제시하세요.

## 전체 성과
- 총 거래: {performance['total_trades']}건
- 승률: {performance['win_rate']}%
- 평균 수익: {performance['avg_profit']}%
- 평균 손실: {performance['avg_loss']}%
- 총 수익률: {performance['total_return']}%

## 최근 20건 거래
{trades_text}

## 분석 요청
1. 가장 큰 문제점 1-2개 (예: 횡보장 손실, 손절 지연, 과도한 보유시간 등)
2. 각 문제에 대한 구체적 개선안 (예: 횡보장 차단, 손절 -2.5% → -2.0%, 최대 보유 60분 → 45분)

답변은 간결하게 핵심만 2-3문장으로 작성하세요."""

        llm_response = self.ask_llm(prompt)

        if not llm_response:
            return []

        # LLM 응답 파싱 (간단하게)
        llm_issues = []

        # "횡보장" 키워드 감지
        if "횡보" in llm_response or "neutral" in llm_response.lower():
            llm_issues.append({
                'type': 'LLM_SIDEWAYS',
                'severity': 'B',
                'description': f'LLM 분석: 횡보장 거래 문제 감지',
                'improvement': 'sideways_block',
                'llm_insight': llm_response[:200]  # 처음 200자만
            })

        # "손절" 또는 "stop loss" 키워드 감지
        if ("손절" in llm_response or "stop" in llm_response.lower()) and "늦" in llm_response:
            llm_issues.append({
                'type': 'LLM_STOP_LOSS',
                'severity': 'A',
                'description': f'LLM 분석: 손절 타이밍 문제',
                'improvement': 'tighten_stop_loss',
                'llm_insight': llm_response[:200]
            })

        # "보유시간" 또는 "hold" 키워드 감지
        if "보유" in llm_response or "hold" in llm_response.lower():
            llm_issues.append({
                'type': 'LLM_HOLD_TIME',
                'severity': 'B',
                'description': f'LLM 분석: 보유시간 문제',
                'improvement': 'reduce_hold_time',
                'llm_insight': llm_response[:200]
            })

        print(f"[{self.bot_name}] [LLM 분석] {len(llm_issues)}개 인사이트 발견")
        if llm_response:
            print(f"[{self.bot_name}] [LLM] {llm_response[:300]}...")

        return llm_issues

    def find_issues(self, trades: List[Dict]) -> List[Dict]:
        """문제점 자동 탐지 (통계 + LLM 분석)"""
        issues = []

        if not trades:
            return issues

        # === 통계 기반 분석 ===
        # 1. 횡보장 손실 체크
        sideways_trades = [t for t in trades if t.get('trend') == 'NEUTRAL']
        if sideways_trades:
            sideways_losses = [t for t in sideways_trades if t.get('profit_pct', 0) < 0]
            sideways_loss_rate = len(sideways_losses) / len(sideways_trades) * 100

            if sideways_loss_rate > 60:
                issues.append({
                    'type': 'SIDEWAYS_LOSS',
                    'severity': 'A',
                    'description': f'횡보장 손실률 {sideways_loss_rate:.0f}% (손실 {len(sideways_losses)}건)',
                    'improvement': 'sideways_block'
                })

        # 2. 장기 보유 손실 체크
        long_holds = [t for t in trades if t.get('hold_minutes', 0) > 45]
        if long_holds:
            long_losses = [t for t in long_holds if t.get('profit_pct', 0) < 0]
            long_loss_rate = len(long_losses) / len(long_holds) * 100

            if long_loss_rate > 50:
                issues.append({
                    'type': 'LONG_HOLD_LOSS',
                    'severity': 'A',
                    'description': f'45분 이상 보유 시 손실률 {long_loss_rate:.0f}%',
                    'improvement': 'reduce_hold_time'
                })

        # 3. 손절 타이밍 체크
        losses = [t for t in trades if t.get('profit_pct', 0) < 0]
        if losses:
            avg_loss = statistics.mean([t['profit_pct'] for t in losses])
            if avg_loss < -3.0:
                issues.append({
                    'type': 'LATE_STOP_LOSS',
                    'severity': 'A',
                    'description': f'평균 손실 {avg_loss:.1f}% (손절 느림)',
                    'improvement': 'tighten_stop_loss'
                })

        # 4. 낮은 승률 체크
        if len(trades) >= 10:
            win_rate = len([t for t in trades if t.get('profit_pct', 0) > 0]) / len(trades) * 100
            if win_rate < 45:
                issues.append({
                    'type': 'LOW_WIN_RATE',
                    'severity': 'B',
                    'description': f'승률 {win_rate:.0f}% (낮음)',
                    'improvement': 'increase_confidence'
                })

        return issues

    def generate_improvements(self, issues: List[Dict]) -> List[Dict]:
        """개선 방안 생성"""
        improvements = []

        for issue in issues:
            if issue['improvement'] == 'sideways_block':
                improvements.append({
                    'grade': 'A',
                    'type': 'sideways_block',
                    'description': '횡보장 거래 차단',
                    'changes': {'trend_check_enabled': True, 'min_trend_strength': 0.3}
                })

            elif issue['improvement'] == 'reduce_hold_time':
                current_hold = self.current_strategy.get('max_hold_minutes', 60)
                new_hold = max(20, current_hold - 10)
                improvements.append({
                    'grade': 'A',
                    'type': 'reduce_hold_time',
                    'description': f'최대 보유시간 {current_hold}분 → {new_hold}분',
                    'changes': {'max_hold_minutes': new_hold}
                })

            elif issue['improvement'] == 'tighten_stop_loss':
                current_sl = self.current_strategy.get('stop_loss_pct', -2.5)
                new_sl = min(-1.5, current_sl + 0.3)
                improvements.append({
                    'grade': 'A',
                    'type': 'tighten_stop_loss',
                    'description': f'손절 {current_sl}% → {new_sl:.1f}% (빠른 손절)',
                    'changes': {'stop_loss_pct': new_sl}
                })

            elif issue['improvement'] == 'increase_confidence':
                current_conf = self.current_strategy.get('min_confidence', 75)
                new_conf = min(85, current_conf + 3)
                improvements.append({
                    'grade': 'B',
                    'type': 'increase_confidence',
                    'description': f'최소 신뢰도 {current_conf}% → {new_conf}% (보수적)',
                    'changes': {'min_confidence': new_conf}
                })

        return improvements

    def apply_improvements(self, improvements: List[Dict]) -> List[Dict]:
        """개선 적용 (A급만 자동, B급은 시뮬레이션 후)"""
        applied = []

        for imp in improvements:
            if imp['grade'] == 'A':
                # A급: 즉시 적용
                for key, value in imp['changes'].items():
                    old_value = self.current_strategy.get(key)
                    self.current_strategy[key] = value
                    print(f"[{self.bot_name}] [A급 개선] {key}: {old_value} → {value}")

                self.save_strategy()
                applied.append(imp)

                # 개선 히스토리 기록
                self.improvement_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'grade': imp['grade'],
                    'type': imp['type'],
                    'description': imp['description'],
                    'changes': imp['changes']
                })

            elif imp['grade'] == 'B':
                # B급: 시뮬레이션 (간단 버전 - 최근 거래에 적용해보기)
                if self.simulate_improvement(imp):
                    for key, value in imp['changes'].items():
                        old_value = self.current_strategy.get(key)
                        self.current_strategy[key] = value
                        print(f"[{self.bot_name}] [B급 개선] {key}: {old_value} → {value} (시뮬 통과)")

                    self.save_strategy()
                    applied.append(imp)

                    self.improvement_history.append({
                        'timestamp': datetime.now().isoformat(),
                        'grade': imp['grade'],
                        'type': imp['type'],
                        'description': imp['description'],
                        'changes': imp['changes'],
                        'simulated': True
                    })
                else:
                    print(f"[{self.bot_name}] [B급 거부] {imp['description']} (시뮬 실패)")

        return applied

    def simulate_improvement(self, improvement: Dict) -> bool:
        """B급 개선 시뮬레이션 (간단 버전)"""
        # 최근 50건 거래에 적용 시 개선되는지 확인
        trades = self.load_trading_history(hours=72)[-50:]

        if len(trades) < 10:
            return False

        # 현재 승률
        current_wins = len([t for t in trades if t.get('profit_pct', 0) > 0])
        current_win_rate = current_wins / len(trades) * 100

        # 개선 후 예상 승률 (간단 추정)
        simulated_win_rate = current_win_rate

        if improvement['type'] == 'increase_confidence':
            # 신뢰도 높이면 거래 수 감소하지만 승률 상승 예상
            new_conf = improvement['changes']['min_confidence']
            simulated_trades = [t for t in trades if t.get('confidence', 0) >= new_conf]
            if simulated_trades:
                simulated_wins = len([t for t in simulated_trades if t.get('profit_pct', 0) > 0])
                simulated_win_rate = simulated_wins / len(simulated_trades) * 100

        # 승률이 3%p 이상 개선되면 통과
        return simulated_win_rate >= current_win_rate + 3

    def meta_learning(self) -> Dict:
        """메타 학습: 어떤 개선이 효과적인가?"""
        if len(self.improvement_history) < 3:
            return {}

        # 최근 개선들의 효과 분석
        recent_improvements = self.improvement_history[-10:]

        improvement_types = {}
        for imp in recent_improvements:
            imp_type = imp['type']
            if imp_type not in improvement_types:
                improvement_types[imp_type] = {'count': 0, 'total_effect': 0}

            improvement_types[imp_type]['count'] += 1

        # 가장 자주 사용된 개선 = 가장 효과적
        most_used = max(improvement_types.items(), key=lambda x: x[1]['count'])[0] if improvement_types else None

        return {
            'total_improvements': len(self.improvement_history),
            'recent_improvements': len(recent_improvements),
            'most_effective': most_used,
            'improvement_types': improvement_types
        }

    def send_telegram_report(self, performance: Dict, issues: List[Dict], applied: List[Dict], meta: Dict):
        """텔레그램 리포트 전송 (6시간마다)"""
        if not self.telegram_config:
            return

        # 리포트 생성
        report = f" <b>{self.bot_name} 봇 자기 개선 리포트</b>\n\n"

        # 성과
        report += f" <b>성과 (최근 24시간)</b>\n"
        report += f"  거래: {performance['total_trades']}건 "
        report += f"(승: {performance['wins']}, 패: {performance['losses']})\n"
        report += f"  승률: {performance['win_rate']}%\n"
        report += f"  수익률: {performance['total_return']:+.2f}%\n"
        if performance['avg_profit'] > 0:
            report += f"  평균 수익: +{performance['avg_profit']}%\n"
        if performance['avg_loss'] < 0:
            report += f"  평균 손실: {performance['avg_loss']}%\n"

        # 문제점
        if issues:
            report += f"\n <b>발견된 문제점</b>\n"
            for issue in issues[:3]:
                report += f"  • {issue['description']}\n"

        # 적용된 개선
        if applied:
            report += f"\n <b>자동 개선 적용</b>\n"
            for imp in applied:
                report += f"   [{imp['grade']}급] {imp['description']}\n"

        # 메타 학습
        if meta.get('total_improvements', 0) > 0:
            report += f"\n <b>학습 현황</b>\n"
            report += f"  총 개선 횟수: {meta['total_improvements']}회\n"
            if meta.get('most_effective'):
                report += f"  가장 효과적: {meta['most_effective']}\n"

        report += f"\n⏰ 다음 리포트: 6시간 후"

        # 전송
        try:
            url = f"https://api.telegram.org/bot{self.telegram_config['bot_token']}/sendMessage"
            payload = {
                'chat_id': self.telegram_config['chat_id'],
                'text': report,
                'parse_mode': 'HTML'
            }
            requests.post(url, data=payload, timeout=5)
            print(f"[{self.bot_name}] 텔레그램 리포트 전송 완료")
        except Exception as e:
            print(f"[{self.bot_name}] 텔레그램 전송 실패: {e}")

    def run_analysis_cycle(self):
        """분석 사이클 실행 (1시간마다 호출)"""
        current_time = time.time()

        # 1시간 경과 체크
        if current_time - self.last_analysis_time < self.analysis_interval:
            return

        print(f"\n{'='*60}")
        print(f"[{self.bot_name}] 자기 분석 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*60}")

        # 1. 성과 분석
        performance = self.analyze_performance(hours=24)
        print(f"[분석] 거래 {performance['total_trades']}건, 승률 {performance['win_rate']}%")

        # 2. 문제점 탐지 (통계)
        trades = self.load_trading_history(hours=24)
        issues = self.find_issues(trades)
        print(f"[통계] 문제점 {len(issues)}개 발견")

        # 3.  LLM 추가 분석 (더 똑똑한 패턴 인식)
        llm_issues = self.llm_analyze_trades(trades, performance)
        issues.extend(llm_issues)  # 통계 + LLM 결과 합치기
        print(f"[LLM] 추가 인사이트 {len(llm_issues)}개 발견")
        print(f"[종합] 총 {len(issues)}개 문제점 탐지")

        # 4. 개선 방안 생성
        improvements = self.generate_improvements(issues)
        print(f"[개선] 개선 방안 {len(improvements)}개 생성")

        # 5. 개선 적용
        applied = self.apply_improvements(improvements)
        print(f"[적용] {len(applied)}개 개선 적용 완료")

        # 6. 메타 학습
        meta = self.meta_learning()

        # 7. 텔레그램 리포트 (6시간마다)
        if current_time - self.last_report_time >= self.report_interval:
            self.send_telegram_report(performance, issues, applied, meta)
            self.last_report_time = current_time

        self.last_analysis_time = current_time
        print(f"{'='*60}\n")

    def check_and_run(self):
        """주기 체크 후 실행 (메인 루프에서 호출)"""
        try:
            self.run_analysis_cycle()
        except Exception as e:
            print(f"[{self.bot_name}] 자기 개선 오류: {e}")


# 사용 예시
if __name__ == "__main__":
    # ETH 봇 예시
    eth_engine = SelfImprovementEngine(
        bot_name="ETH",
        trading_history_file="eth_trade_history.json",
        strategy_file="eth_current_strategy.json",
        telegram_config={
            'bot_token': '7819173403:AAEwBNh6etqyWvh-GivLDrTJb8b_ho2ju-U',
            'chat_id': '7805944420'
        }
    )

    # 테스트
    eth_engine.run_analysis_cycle()
