# -*- coding: utf-8 -*-
"""메인 로직에서 USD 잔고 실패 시 처리 개선"""

# 파일 읽기
with open('kis_llm_trader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 기존 코드 교체
old_code = '''        buying_power = self.get_usd_cash_balance(symbol=symbol, price=price)

        if not buying_power['success']:
            print("[ERROR] USD 잔고 조회 실패")
            return

        usd_cash = buying_power['ord_psbl_frcr_amt']'''

new_code = '''        buying_power = self.get_usd_cash_balance(symbol=symbol, price=price)

        if not buying_power['success']:
            error_msg = buying_power.get('error', '알 수 없는 오류')
            print(f"[ERROR] USD 잔고 조회 실패: {error_msg}")
            print("[WARN] USD 잔고를 0으로 가정하고 계속 진행합니다")
            print("[INFO] 매수가 필요한 경우 API 문제를 먼저 해결해주세요")
            usd_cash = 0.0
        else:
            usd_cash = buying_power['ord_psbl_frcr_amt']'''

# 교체
if old_code in content:
    content = content.replace(old_code, new_code)
    print("[OK] 메인 로직 USD 잔고 실패 처리 개선 완료")
else:
    print("[ERROR] 기존 코드를 찾을 수 없습니다")
    exit(1)

# 파일 쓰기
with open('kis_llm_trader.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[완료] kis_llm_trader.py 파일이 업데이트되었습니다")
