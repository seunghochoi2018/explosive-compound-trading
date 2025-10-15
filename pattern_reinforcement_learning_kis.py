#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 작동하는 강화학습 시스템 (KIS 버전)

ETH 시스템과 동일한 로직, KIS 전용 파일 경로
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import numpy as np

class PatternReinforcementLearning:
    def __init__(self, trade_history_file: str):
        """
        강화학습 시스템 초기화

        Args:
            trade_history_file: 거래 기록 JSON 파일 경로
        """
        self.trade_history_file = Path(trade_history_file)
        self.pattern_db_file = Path(trade_history_file).parent / "kis_pattern_reinforcement.json"

        # 패턴 데이터베이스 로드 또는 생성
        self.pattern_db = self._load_or_create_pattern_db()

    def _load_or_create_pattern_db(self) -> Dict:
        """패턴 데이터베이스 로드 또는 신규 생성"""
        if self.pattern_db_file.exists():
            with open(self.pattern_db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "last_update": None,
                "total_patterns": 0,
                "patterns": {},
                "meta": {
                    "min_sample_size": 10,  # 최소 10개 샘플부터 신뢰
                    "confidence_boost_max": 40,  # 최대 +40 부스트
                    "confidence_penalty_max": 60,  # 최대 -60 페널티
                }
            }

    def extract_pattern_features(self, trade_data: Dict) -> str:
        """
        거래 데이터에서 패턴 특징 추출

        패턴 키 구성:
        - 추세 (1분봉, 5분봉)
        - LLM 신뢰도 범위
        - 거래량 급증 여부
        - 돌파 패턴 여부

        Returns:
            패턴 키 문자열 (예: "up_up_60-70_surge_nobreak")
        """
        trend_1m = trade_data.get('market_1m_trend', 'unknown')
        trend_5m = trade_data.get('market_5m_trend', 'unknown')
        confidence = trade_data.get('llm_confidence', 50)
        volume_surge = trade_data.get('volume_surge', False)
        breakout = trade_data.get('breakout', False)

        # 신뢰도를 10단위로 그룹화
        conf_range = f"{(confidence // 10) * 10}-{(confidence // 10) * 10 + 10}"

        # 패턴 키 생성
        pattern_key = f"{trend_1m}_{trend_5m}_{conf_range}_{('surge' if volume_surge else 'nosurge')}_{('break' if breakout else 'nobreak')}"

        return pattern_key

    def learn_from_all_trades(self):
        """
        전체 거래 기록에서 패턴 학습

        각 패턴별로:
        - 총 거래 수
        - 승리 수
        - 승률
        - 평균 PNL
        - 평균 보유 시간
        """
        print("="*80)
        print("강화학습 시작: 전체 거래 분석 (KIS)")
        print("="*80)

        # 거래 기록 로드
        with open(self.trade_history_file, 'r', encoding='utf-8') as f:
            trades = json.load(f)

        print(f"총 거래 수: {len(trades)}건")

        # 패턴별 통계 초기화
        pattern_stats = {}

        # 각 거래 분석
        for trade in trades:
            # 패턴 추출
            pattern_key = self.extract_pattern_features(trade)

            # 결과 분석
            balance_change = trade.get('balance_change', 0)
            is_win = balance_change > 0
            pnl_pct = trade.get('pnl_pct', 0)
            holding_time_sec = trade.get('holding_time_sec', 0)

            # 패턴 통계 업데이트
            if pattern_key not in pattern_stats:
                pattern_stats[pattern_key] = {
                    "total": 0,
                    "wins": 0,
                    "losses": 0,
                    "total_pnl": 0,
                    "total_balance_change": 0,
                    "total_holding_time": 0,
                    "win_trades": [],
                    "loss_trades": []
                }

            stats = pattern_stats[pattern_key]
            stats["total"] += 1
            stats["total_pnl"] += pnl_pct
            stats["total_balance_change"] += balance_change
            stats["total_holding_time"] += holding_time_sec

            if is_win:
                stats["wins"] += 1
                stats["win_trades"].append({
                    "pnl": pnl_pct,
                    "balance_change": balance_change,
                    "holding_time": holding_time_sec
                })
            else:
                stats["losses"] += 1
                stats["loss_trades"].append({
                    "pnl": pnl_pct,
                    "balance_change": balance_change,
                    "holding_time": holding_time_sec
                })

        # 패턴별 최종 통계 계산
        final_patterns = {}
        for pattern_key, stats in pattern_stats.items():
            total = stats["total"]
            wins = stats["wins"]
            win_rate = wins / total if total > 0 else 0
            avg_pnl = stats["total_pnl"] / total if total > 0 else 0
            avg_balance_change = stats["total_balance_change"] / total if total > 0 else 0
            avg_holding_time = stats["total_holding_time"] / total if total > 0 else 0

            # 신뢰도 조정값 계산
            confidence_adjustment = self._calculate_confidence_adjustment(
                win_rate, total, avg_balance_change
            )

            final_patterns[pattern_key] = {
                "total_trades": total,
                "wins": wins,
                "losses": stats["losses"],
                "win_rate": round(win_rate * 100, 1),
                "avg_pnl": round(avg_pnl, 2),
                "avg_balance_change": round(avg_balance_change, 2),  # KIS는 USD
                "avg_holding_time_min": round(avg_holding_time / 60, 1),
                "confidence_adjustment": confidence_adjustment,
                "recommendation": self._get_recommendation(win_rate, total, avg_balance_change)
            }

        # 패턴 데이터베이스 업데이트
        self.pattern_db["patterns"] = final_patterns
        self.pattern_db["total_patterns"] = len(final_patterns)
        self.pattern_db["last_update"] = datetime.now().isoformat()

        # 저장
        self._save_pattern_db()

        # 결과 출력
        self._print_learning_summary(final_patterns)

        return final_patterns

    def _calculate_confidence_adjustment(self, win_rate: float, sample_size: int, avg_balance_change: float) -> int:
        """
        승률과 샘플 수에 따른 신뢰도 조정값 계산

        Args:
            win_rate: 승률 (0.0 ~ 1.0)
            sample_size: 샘플 수
            avg_balance_change: 평균 잔고 변화 (USD)

        Returns:
            신뢰도 조정값 (-60 ~ +40)
        """
        min_samples = self.pattern_db["meta"]["min_sample_size"]

        # 샘플이 부족하면 중립
        if sample_size < min_samples:
            return 0

        # 샘플 수에 따른 가중치
        sample_weight = min(1.0, 0.5 + (sample_size / 100) * 0.5)

        # 잔고 변화 기준으로 조정
        if avg_balance_change > 0:
            # 수익 패턴: +10 ~ +40
            base_adjustment = 10 + (win_rate * 30)
        else:
            # 손실 패턴: -20 ~ -60
            loss_severity = abs(avg_balance_change) / 100  # USD 기준
            base_adjustment = -20 - (loss_severity * 40) - ((1 - win_rate) * 40)
            base_adjustment = max(-60, base_adjustment)

        # 샘플 가중치 적용
        final_adjustment = int(base_adjustment * sample_weight)

        # 범위 제한
        final_adjustment = max(-60, min(40, final_adjustment))

        return final_adjustment

    def _get_recommendation(self, win_rate: float, sample_size: int, avg_balance_change: float) -> str:
        """패턴 추천 메시지"""
        min_samples = self.pattern_db["meta"]["min_sample_size"]

        if sample_size < min_samples:
            return "데이터 부족 (중립)"

        if avg_balance_change > 0 and win_rate >= 0.6:
            return "강력 추천 (고수익 패턴)"
        elif avg_balance_change > 0 and win_rate >= 0.4:
            return "추천 (수익 패턴)"
        elif avg_balance_change < 0 and win_rate < 0.3:
            return "강력 회피 (고손실 패턴)"
        elif avg_balance_change < 0:
            return "회피 (손실 패턴)"
        else:
            return "중립"

    def _save_pattern_db(self):
        """패턴 데이터베이스 저장"""
        with open(self.pattern_db_file, 'w', encoding='utf-8') as f:
            json.dump(self.pattern_db, f, indent=2, ensure_ascii=False)
        print(f"\n[저장] 패턴 DB: {self.pattern_db_file}")

    def _print_learning_summary(self, patterns: Dict):
        """학습 결과 요약 출력"""
        print("\n" + "="*80)
        print("학습 완료 요약 (KIS)")
        print("="*80)

        # 패턴 분류
        strong_win_patterns = []
        strong_loss_patterns = []

        for key, data in patterns.items():
            if data["recommendation"] == "강력 추천 (고수익 패턴)":
                strong_win_patterns.append((key, data))
            elif data["recommendation"] == "강력 회피 (고손실 패턴)":
                strong_loss_patterns.append((key, data))

        # 수익 패턴 출력
        print(f"\n[고수익 패턴] {len(strong_win_patterns)}개 발견")
        for key, data in sorted(strong_win_patterns, key=lambda x: x[1]['avg_balance_change'], reverse=True)[:5]:
            print(f"  패턴: {key}")
            print(f"    승률: {data['win_rate']}% ({data['wins']}/{data['total_trades']})")
            print(f"    평균 잔고 변화: ${data['avg_balance_change']:+.2f}")
            print(f"    신뢰도 조정: {data['confidence_adjustment']:+d}")
            print()

        # 손실 패턴 출력
        print(f"\n[고손실 패턴] {len(strong_loss_patterns)}개 발견")
        for key, data in sorted(strong_loss_patterns, key=lambda x: x[1]['avg_balance_change'])[:5]:
            print(f"  패턴: {key}")
            print(f"    승률: {data['win_rate']}% ({data['wins']}/{data['total_trades']})")
            print(f"    평균 잔고 변화: ${data['avg_balance_change']:+.2f}")
            print(f"    신뢰도 조정: {data['confidence_adjustment']:+d}")
            print()

        print("="*80)

    def get_confidence_adjustment(self, current_market: Dict) -> Tuple[int, str]:
        """
        현재 시장 상황에 대한 신뢰도 조정값 반환

        Args:
            current_market: 현재 시장 데이터

        Returns:
            (조정값, 설명)
        """
        # 패턴 추출
        pattern_key = self.extract_pattern_features(current_market)

        # 패턴 DB에서 조회
        patterns = self.pattern_db.get("patterns", {})

        if pattern_key not in patterns:
            return (0, "신규 패턴 (데이터 없음)")

        pattern_data = patterns[pattern_key]
        adjustment = pattern_data["confidence_adjustment"]
        recommendation = pattern_data["recommendation"]
        win_rate = pattern_data["win_rate"]
        total = pattern_data["total_trades"]

        explanation = f"{recommendation} | 승률 {win_rate}% ({total}건) | 조정: {adjustment:+d}"

        return (adjustment, explanation)
