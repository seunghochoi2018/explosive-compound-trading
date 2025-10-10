#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETH 전체 데이터 깊은 학습 (하루종일 학습)

목표: 연 수천% 복리 폭발 전략 찾기

방법:
1. ETH 8년 3,605건 전체 분석
2. 손실 패턴 제거
3. 수익 패턴만 강화
4. LLM에게 패턴 학습시키기
5. 복리 폭발 조합 찾기
"""

import json
from datetime import datetime
from typing import List, Dict
from collections import defaultdict
import ollama

print("="*80)
print("ETH 전체 데이터 깊은 학습 (복리 폭발 전략)")
print("="*80)

# 데이터 로드
with open('C:/Users/user/Documents/코드3/eth_trade_history.json', 'r', encoding='utf-8') as f:
    all_trades = json.load(f)

print(f"\n전체 거래: {len(all_trades)}건")

completed = [t for t in all_trades if 'pnl_pct' in t and t.get('exit_price')]
print(f"완료 거래: {len(completed)}건")

# ============================================================================
# 1단계: 수익 패턴 vs 손실 패턴 분류
# ============================================================================
print("\n" + "="*80)
print("[1단계] 수익/손실 패턴 분류")
print("="*80)

wins = [t for t in completed if t['pnl_pct'] > 0]
losses = [t for t in completed if t['pnl_pct'] <= 0]

print(f"\n수익 거래: {len(wins)}건 ({len(wins)/len(completed)*100:.1f}%)")
print(f"손실 거래: {len(losses)}건 ({len(losses)/len(completed)*100:.1f}%)")

# 큰 수익 거래 (5% 이상)
big_wins = [t for t in wins if t['pnl_pct'] >= 5]
medium_wins = [t for t in wins if 2 <= t['pnl_pct'] < 5]
small_wins = [t for t in wins if 0 < t['pnl_pct'] < 2]

print(f"\n큰 수익 (5%+): {len(big_wins)}건")
print(f"중간 수익 (2-5%): {len(medium_wins)}건")
print(f"소액 수익 (0-2%): {len(small_wins)}건")

# 손실 분석
big_losses = [t for t in losses if t['pnl_pct'] <= -5]
medium_losses = [t for t in losses if -5 < t['pnl_pct'] <= -2]
small_losses = [t for t in losses if -2 < t['pnl_pct'] <= 0]

print(f"\n큰 손실 (-5% 이하): {len(big_losses)}건")
print(f"중간 손실 (-5 ~ -2%): {len(medium_losses)}건")
print(f"소액 손실 (0 ~ -2%): {len(small_losses)}건")

# ============================================================================
# 2단계: 수익 패턴 특징 추출
# ============================================================================
print("\n" + "="*80)
print("[2단계] 수익 패턴 특징 추출")
print("="*80)

def extract_features(trades: List[Dict]) -> Dict:
    """거래 리스트에서 특징 추출"""
    if not trades:
        return {}

    features = {
        'count': len(trades),
        'avg_pnl': sum(t['pnl_pct'] for t in trades) / len(trades),
        'avg_holding_min': sum(t.get('holding_time_min', 0) for t in trades) / len(trades),
    }

    # 추세 분석
    trends = defaultdict(int)
    for t in trades:
        trend = t.get('market_1m_trend', 'unknown')
        trends[trend] += 1

    features['trend_distribution'] = dict(trends)

    # 볼륨 분석
    volume_surge_count = sum(1 for t in trades if t.get('volume_surge'))
    features['volume_surge_rate'] = volume_surge_count / len(trades) * 100

    # 롱/숏 분석
    longs = [t for t in trades if t.get('side') == 'BUY']
    shorts = [t for t in trades if t.get('side') == 'SELL']

    features['long_rate'] = len(longs) / len(trades) * 100
    features['short_rate'] = len(shorts) / len(trades) * 100

    return features

big_win_features = extract_features(big_wins)
loss_features = extract_features(losses)

print("\n[큰 수익 거래 특징]")
for key, value in big_win_features.items():
    print(f"  {key}: {value}")

print("\n[손실 거래 특징]")
for key, value in loss_features.items():
    print(f"  {key}: {value}")

# ============================================================================
# 3단계: LLM에게 패턴 학습 요청
# ============================================================================
print("\n" + "="*80)
print("[3단계] LLM 깊은 학습 시작")
print("="*80)

# 데이터 요약
summary = f"""
ETH/USD 거래 전체 데이터 분석 결과:

**전체 통계**
- 총 거래: {len(completed)}건
- 승률: {len(wins)/len(completed)*100:.1f}%
- 평균 수익: {sum(t['pnl_pct'] for t in wins)/len(wins):.2f}%
- 평균 손실: {sum(t['pnl_pct'] for t in losses)/len(losses):.2f}%

**수익 분류**
- 큰 수익 (5%+): {len(big_wins)}건
- 중간 수익 (2-5%): {len(medium_wins)}건
- 소액 수익 (0-2%): {len(small_wins)}건

**손실 분류**
- 큰 손실 (-5% 이하): {len(big_losses)}건
- 중간 손실 (-5 ~ -2%): {len(medium_losses)}건
- 소액 손실 (0 ~ -2%): {len(small_losses)}건

**큰 수익 거래 특징**
{json.dumps(big_win_features, indent=2, ensure_ascii=False)}

**손실 거래 특징**
{json.dumps(loss_features, indent=2, ensure_ascii=False)}

**보유시간별 복리 효과** (이전 분석)
- 초단타 (0-10분): +95.9% 복리, 승률 64.9%
- 단타 (10-30분): +180.7% 복리, 승률 65.9%
- 중기 (30-60분): +191.8% 복리, 승률 67.3%
- 장기 (120분+): -95% 복리, 승률 41.6% ← 절대 금지!

**현재 성과**
- ETH: 연 98% (목표 미달)
- SOXL 추세전략: 연 2,634% (목표 달성!)
"""

prompt = f"""당신은 암호화폐 트레이딩 전문가이자 복리 효과 최적화 전문가입니다.

{summary}

**핵심 질문:**

ETH는 25배 레버리지인데 왜 연 98%밖에 안 나올까요?
SOXL은 3배 레버리지인데 추세 전환으로 연 2,634%가 나왔습니다.

**분석 요청:**

1. **손실 패턴 제거 방법**
   - 큰 손실 (-5% 이하) {len(big_losses)}건을 어떻게 피할까?
   - 120분 이상 보유 시 -95% 손실 → 어떻게 막을까?

2. **수익 패턴 강화 방법**
   - 큰 수익 (5%+) {len(big_wins)}건의 공통점은?
   - 초단타~중기 (0-60분)에서 복리 폭발 → 어떻게 더 강화?

3. **복리 폭발 전략**
   - 승률 65% + 평균 수익 2% + 빠른 회전 → 연 수천% 가능?
   - 25배 레버리지를 어떻게 활용?

4. **구체적인 개선안**
   - 진입 조건: 어떤 상황에서만 진입?
   - 청산 조건: 언제 빨리 청산?
   - 손절 조건: 어떻게 빠르게 손절?

5. **실전 전략 3가지**
   전략1: 초고속 스캘핑 (0-10분)
   - 진입: ...
   - 청산: ...
   - 예상 연수익: ...

   전략2: 고속 스윙 (10-60분)
   - 진입: ...
   - 청산: ...
   - 예상 연수익: ...

   전략3: SOXL 스타일 추세 전환
   - 진입: ...
   - 청산: ...
   - 예상 연수익: ...

**중요**:
- 실제 데이터 기반으로 분석
- 수천% 복리 폭발 가능한 전략 제시
- 손실 최소화 + 수익 극대화 조합
"""

print("\n[LLM 분석 시작]")
print("모델: qwen2.5:14b")
print("예상 소요: 5-10분")
print("\n분석 중...")

try:
    response = ollama.chat(
        model='qwen2.5:14b',
        messages=[{
            'role': 'user',
            'content': prompt
        }],
        options={
            'temperature': 0.2,  # 더 정확하게
            'num_predict': 3000  # 더 긴 답변
        }
    )

    answer = response['message']['content']

    print("\n" + "="*80)
    print("[LLM 분석 결과]")
    print("="*80)
    print(answer)
    print("="*80)

    # 저장
    with open('C:/Users/user/Documents/deep_eth_learning_results.txt', 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("ETH 깊은 학습 결과 (복리 폭발 전략)\n")
        f.write("="*80 + "\n\n")
        f.write(summary + "\n\n")
        f.write("="*80 + "\n")
        f.write("LLM 분석 결과\n")
        f.write("="*80 + "\n\n")
        f.write(answer)

    print("\n[OK] deep_eth_learning_results.txt 저장")

except Exception as e:
    print(f"\n[ERROR] LLM 실패: {e}")
    print("Ollama 서버가 실행 중인지 확인하세요.")

print("\n" + "="*80)
print("[완료]")
print("="*80)
