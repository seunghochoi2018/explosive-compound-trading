# -*- coding: utf-8 -*-
"""거래소 코드 불일치 문제 해결"""

# 파일 읽기
with open('kis_llm_trader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 함수 시그니처 수정
old_sig = '''    def get_usd_cash_balance(self, symbol: str = "TQQQ", price: float = 35.0) -> Dict:'''

new_sig = '''    def get_usd_cash_balance(self, symbol: str = "TQQQ", price: float = 35.0, exchange_cd: str = None) -> Dict:'''

if old_sig in content:
    content = content.replace(old_sig, new_sig)
    print("[OK] 함수 시그니처 수정 완료")
else:
    print("[ERROR] 함수 시그니처를 찾을 수 없습니다")
    exit(1)

# 2. 거래소 코드 로직 수정
old_exchange = '''        # 거래소 코드를 symbol_exchange_map에서 가져오기
        exchange_cd = self.symbol_exchange_map.get(symbol, "NASD")'''

new_exchange = '''        # 거래소 코드 처리 (파라미터 우선, 없으면 매핑에서 가져오기)
        if exchange_cd is None:
            exchange_cd = self.symbol_exchange_map.get(symbol, "NASD")
            print(f"[DEBUG] 거래소 코드를 매핑에서 가져옴: {exchange_cd}")
        else:
            print(f"[DEBUG] 거래소 코드를 파라미터에서 사용: {exchange_cd}")'''

if old_exchange in content:
    content = content.replace(old_exchange, new_exchange)
    print("[OK] 거래소 코드 로직 수정 완료")
else:
    print("[ERROR] 거래소 코드 로직을 찾을 수 없습니다")
    exit(1)

# 3. 메인 로직에서 호출 시 거래소 코드 전달
old_call = '''        # USD 잔고 조회 (보유 종목이 있으면 그 종목 기준, 없으면 기본 종목)
        if positions:
            symbol = positions[0]['symbol']
            price = positions[0]['current_price']
        else:
            symbol = "TQQQ"
            price = 35.0

        buying_power = self.get_usd_cash_balance(symbol=symbol, price=price)'''

new_call = '''        # USD 잔고 조회 (보유 종목이 있으면 그 종목 기준, 없으면 기본 종목)
        if positions:
            symbol = positions[0]['symbol']
            price = positions[0]['current_price']
            exchange_cd = positions[0].get('exchange_cd', None)  # 포지션에서 실제 거래소 코드 가져오기
            print(f"[DEBUG] 포지션에서 가져온 거래소 코드: {exchange_cd}")
        else:
            symbol = "TQQQ"
            price = 35.0
            exchange_cd = None

        buying_power = self.get_usd_cash_balance(symbol=symbol, price=price, exchange_cd=exchange_cd)'''

if old_call in content:
    content = content.replace(old_call, new_call)
    print("[OK] 메인 로직 호출 부분 수정 완료")
else:
    print("[ERROR] 메인 로직 호출 부분을 찾을 수 없습니다")
    exit(1)

# 파일 쓰기
with open('kis_llm_trader.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[완료] kis_llm_trader.py 파일이 업데이트되었습니다")
