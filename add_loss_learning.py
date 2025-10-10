# -*- coding: utf-8 -*-
"""실패 경험 학습 강화"""

# 파일 읽기
with open('kis_llm_trader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 프롬프트 개선 - 실패 경험 학습 명시
old_prompt = '''            # LLM 프롬프트 구성
            prompt = f"""
당신은 전문 트레이더입니다. SOXL(상승 레버리지 ETF)과 SOXS(하락 레버리지 ETF) 추세돌파 전략을 분석하세요.

[현재 시장 상황]
현재가: ${current_price:.2f}
최근 가격 추이: {price_history[-10:]}

[과거 거래 학습 데이터]
{json.dumps(recent_trades, indent=2, ensure_ascii=False) if recent_trades else '데이터 없음'}

[메타 학습 인사이트]
{json.dumps(insights, indent=2, ensure_ascii=False) if insights else '데이터 없음'}

[분석 요청]
1. 현재 추세가 상승(BULL)인가 하락(BEAR)인가?
2. 추세돌파가 발생했는가?
3. 신뢰도는? (0-100)
4. 이유는?

JSON 형식으로 답변:
{{
    "signal": "BULL" or "BEAR" or "HOLD",
    "confidence": 75,
    "reasoning": "상승 추세 돌파 확인. 최근 10분간 지속적 상승...",
    "predicted_trend": "단기 상승 예상"
}}
"""'''

new_prompt = '''            # 거래 히스토리 분석 (성공/실패 패턴)
            success_trades = [t for t in recent_trades if t.get('result') == 'WIN']
            loss_trades = [t for t in recent_trades if t.get('result') == 'LOSS']

            # LLM 프롬프트 구성 (실패 경험 학습 강화)
            prompt = f"""
당신은 전문 트레이더입니다. SOXL(상승 레버리지 ETF)과 SOXS(하락 레버리지 ETF) 추세돌파 전략을 분석하세요.

[현재 시장 상황]
현재가: ${current_price:.2f}
최근 가격 추이: {price_history[-10:]}

[과거 거래 학습 데이터]
전체 거래: {len(recent_trades)}건
성공 거래: {len(success_trades)}건
실패 거래: {len(loss_trades)}건

{json.dumps(recent_trades, indent=2, ensure_ascii=False) if recent_trades else '데이터 없음'}

[⚠️ 실패 패턴 분석 - 반드시 고려]
{json.dumps(loss_trades[-5:], indent=2, ensure_ascii=False) if loss_trades else '실패 거래 없음'}

**실패 경험에서 배운 교훈:**
- 실패한 거래의 진입 시점, 신호, 손익률을 분석하세요
- 같은 실수를 반복하지 않도록 주의하세요
- 실패 패턴과 유사한 상황이면 신뢰도를 낮추세요

[메타 학습 인사이트]
{json.dumps(insights, indent=2, ensure_ascii=False) if insights else '데이터 없음'}

[분석 요청]
1. 현재 추세가 상승(BULL)인가 하락(BEAR)인가?
2. 추세돌파가 발생했는가?
3. **과거 실패 거래와 유사한 상황인가?**
4. 신뢰도는? (0-100) - 실패 패턴 유사시 신뢰도 감소
5. 이유는? - 실패 경험 고려 여부 명시

JSON 형식으로 답변:
{{
    "signal": "BULL" or "BEAR" or "HOLD",
    "confidence": 75,
    "reasoning": "상승 추세 돌파 확인. 과거 실패 패턴(XX%)과 유사하지 않음...",
    "predicted_trend": "단기 상승 예상",
    "loss_pattern_check": "과거 실패 패턴 검토 결과..."
}}
"""'''

# 교체
if old_prompt in content:
    content = content.replace(old_prompt, new_prompt)
    print("[OK] 프롬프트에 실패 경험 학습 로직 추가 완료")
else:
    print("[ERROR] 기존 프롬프트를 찾을 수 없습니다")
    exit(1)

# 파일 쓰기
with open('kis_llm_trader.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[완료] kis_llm_trader.py 파일이 업데이트되었습니다")
print("\n[추가된 기능]")
print("  - 성공/실패 거래 자동 분류")
print("  - 실패 패턴 명시적 분석")
print("  - 실패 경험 기반 신뢰도 조정")
print("  - LLM에 실패 경험 고려 지시")
