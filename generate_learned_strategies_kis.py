#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS 학습된 전략 생성기 (SOXL/SOXS용)

실제 거래 데이터에서 SOXL/SOXS 잔고를 증가시킨 패턴만 추출
"""
import json
import os

def generate_learned_strategies():
    """
    실제 KIS 거래 데이터에서 학습된 전략 생성
    - SOXL/SOXS 거래 패턴 분석
    - 잔고 증가 패턴만 추출
    - 손실 패턴 명확히 회피
    """
    
    # 거래 이력 파일 경로
    trade_file = os.path.join(os.path.dirname(__file__), 'kis_trade_history.json')
    
    try:
        with open(trade_file, 'r', encoding='utf-8') as f:
            trades = json.load(f)
    except FileNotFoundError:
        return """
[경고] KIS 거래 이력 없음

초기 전략:
1. 10시간 보유 타이머 엄수
2. 추세 전환 타이밍 정확히 포착
3. SOXL (상승장), SOXS (하락장) 명확한 구분
4. 최소 거래 간격: 30분
5. 손절: -3% (3배 레버리지 고려)

거래 데이터가 누적되면 학습 전략으로 전환됩니다.
"""
    except Exception as e:
        return f"학습 데이터 로드 실패: {e}"

    # 성공 거래 (balance_change > 0)
    success_trades = [t for t in trades if t.get('balance_change', 0) > 0]
    # 실패 거래 (balance_change <= 0)
    failure_trades = [t for t in trades if t.get('balance_change', 0) <= 0]

    # 통계
    total = len(trades)
    success_count = len(success_trades)
    failure_count = len(failure_trades)

    if total < 10:
        return f"""
[초기 단계] KIS 거래 {total}건 (최소 10건 필요)

임시 전략:
1. 10시간 보유 우선 (백테스트 승률 55%)
2. 추세 전환 시 즉시 반대 포지션
3. SOXL ↔ SOXS 빠른 전환
4. 손절: -3% 엄수
5. 최대 보유: 12시간

{total}건 더 거래 후 본격 학습 시작!
"""

    if success_count == 0:
        return f"""
[긴급] KIS 학습 데이터: {total}건 중 성공 0건!

절대 규칙:
1. 현재 전략은 100% 실패 중 → 모든 거래 금지!
2. CONFIDENCE를 50으로 고정 (거래 차단)
3. 전략 재검토 필요

원인 분석:
- 10시간 타이머가 작동하지 않음?
- 추세 반대 포지션 진입?
- 손절이 너무 빠름?
"""

    # 성공 거래 분석
    success_symbols = {}
    for t in success_trades:
        symbol = t.get('symbol', 'UNKNOWN')
        success_symbols[symbol] = success_symbols.get(symbol, 0) + 1

    # 실패 거래 분석
    failure_symbols = {}
    for t in failure_trades:
        symbol = t.get('symbol', 'UNKNOWN')
        failure_symbols[symbol] = failure_symbols.get(symbol, 0) + 1

    # SOXL/SOXS 승률
    soxl_success = success_symbols.get('SOXL', 0)
    soxl_failure = failure_symbols.get('SOXL', 0)
    soxl_total = soxl_success + soxl_failure
    soxl_winrate = (soxl_success / soxl_total * 100) if soxl_total > 0 else 0

    soxs_success = success_symbols.get('SOXS', 0)
    soxs_failure = failure_symbols.get('SOXS', 0)
    soxs_total = soxs_success + soxs_failure
    soxs_winrate = (soxs_success / soxs_total * 100) if soxs_total > 0 else 0

    # 평균 보유 시간
    success_holding = sum(t.get('holding_time_sec', 0) for t in success_trades) / len(success_trades) if success_trades else 0
    failure_holding = sum(t.get('holding_time_sec', 0) for t in failure_trades) / len(failure_trades) if failure_trades else 0

    # 10시간 (36000초) 근처 분석
    target_holding = 10 * 3600  # 10시간
    near_10h_success = sum(1 for t in success_trades if abs(t.get('holding_time_sec', 0) - target_holding) < 1800)  # ±30분
    near_10h_failure = sum(1 for t in failure_trades if abs(t.get('holding_time_sec', 0) - target_holding) < 1800)

    # 전략 생성
    strategy = f"""
=== KIS 실제 거래 데이터 기반 학습 전략 ===
(총 {total}건 거래 분석, 성공: {success_count}건, 실패: {failure_count}건, 승률: {success_count/total*100:.1f}%)

[종목별 승률]
1. SOXL (반도체 3배 롱):
   - 총 거래: {soxl_total}건
   - 성공: {soxl_success}건, 실패: {soxl_failure}건
   - 승률: {soxl_winrate:.1f}%
   
2. SOXS (반도체 3배 숏):
   - 총 거래: {soxs_total}건
   - 성공: {soxs_success}건, 실패: {soxs_failure}건
   - 승률: {soxs_winrate:.1f}%

[보유 시간 분석]
- 성공 평균: {success_holding:.0f}초 ({success_holding/3600:.1f}시간)
- 실패 평균: {failure_holding:.0f}초 ({failure_holding/3600:.1f}시간)
- 10시간 근처 성공: {near_10h_success}건
- 10시간 근처 실패: {near_10h_failure}건
→ 10시간 타이머 {'효과적' if near_10h_success > near_10h_failure else '재검토 필요'}

[절대 회피 패턴]
1. {'SOXL' if soxl_winrate < soxs_winrate else 'SOXS'} 회피:
   - 승률이 더 낮은 종목 ({soxl_winrate if soxl_winrate < soxs_winrate else soxs_winrate:.1f}%)
   
2. 너무 짧은 보유:
   - {failure_holding/60:.0f}분 미만은 손실 가능성 높음
   
3. 너무 긴 보유:
   - 12시간 초과 시 수익 감소 추세

[승리 패턴]
1. 최적 보유 시간: {success_holding/3600:.1f}시간 ± 1시간
2. 선호 종목: {'SOXL' if soxl_winrate > soxs_winrate else 'SOXS'} (승률 {max(soxl_winrate, soxs_winrate):.1f}%)
3. 추세 확인: 같은 방향 30분 이상 지속 시에만

[현재 시스템 분석]
- 전체 승률: {success_count/total*100:.1f}% {'(양호)' if success_count/total > 0.5 else '(개선 필요)'}
- 거래 빈도: {len(trades)}건
- 최적 포지션: {'SOXL' if soxl_winrate > soxs_winrate else 'SOXS'}

[LLM 판단 가이드]
1. {'SOXL' if soxl_winrate > soxs_winrate else 'SOXS'} 선호 → CONFIDENCE: 70+
2. {'SOXL' if soxl_winrate < soxs_winrate else 'SOXS'} 회피 → CONFIDENCE: 40
3. 10시간 타이머 임박 → CONFIDENCE: 50 (관망)
4. 추세 불명확 → CONFIDENCE: 50 (관망)
5. **핵심: 10시간 보유 + 추세 전환 타이밍!**
"""

    return strategy

if __name__ == "__main__":
    print(generate_learned_strategies())

