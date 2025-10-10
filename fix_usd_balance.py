# -*- coding: utf-8 -*-
"""USD 잔고 조회 로직 수정"""

# 파일 읽기
with open('kis_llm_trader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. get_usd_cash_balance() 함수 수정 - 거래소 코드를 동적으로 처리
old_code1 = '''        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": "AMEX",  # 필수!
            "OVRS_ORD_UNPR": str(price),
            "ITEM_CD": symbol
        }'''

new_code1 = '''        # 거래소 코드를 symbol_exchange_map에서 가져오기
        exchange_cd = self.symbol_exchange_map.get(symbol, "NASD")

        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": exchange_cd,  # 종목별 거래소 코드 사용
            "OVRS_ORD_UNPR": str(price),
            "ITEM_CD": symbol
        }'''

# 2. execute_llm_strategy()에서 USD 잔고 조회 부분 수정
old_code2 = '''        # 1. 계좌 상황 파악
        buying_power = self.get_usd_cash_balance()
        positions = self.get_positions()'''

new_code2 = '''        # 1. 계좌 상황 파악
        positions = self.get_positions()

        # USD 잔고 조회 (보유 종목이 있으면 그 종목 기준, 없으면 기본 종목)
        if positions:
            symbol = positions[0]['symbol']
            price = positions[0]['current_price']
        else:
            symbol = "TQQQ"
            price = 35.0

        buying_power = self.get_usd_cash_balance(symbol=symbol, price=price)'''

# 교체
modified = False

if old_code1 in content:
    content = content.replace(old_code1, new_code1)
    print("[OK] get_usd_cash_balance() 거래소 코드 수정 완료")
    modified = True
else:
    print("[WARN] get_usd_cash_balance() 거래소 코드 부분을 찾을 수 없습니다")

if old_code2 in content:
    content = content.replace(old_code2, new_code2)
    print("[OK] execute_llm_strategy() USD 잔고 조회 수정 완료")
    modified = True
else:
    print("[WARN] execute_llm_strategy() USD 잔고 조회 부분을 찾을 수 없습니다")

if modified:
    # 파일 쓰기
    with open('kis_llm_trader.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("[완료] kis_llm_trader.py 파일이 업데이트되었습니다")
else:
    print("[ERROR] 수정할 코드를 찾을 수 없습니다")
    exit(1)
