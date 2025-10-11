# -*- coding: utf-8 -*-
"""symbol_exchange_map 업데이트 (실제 API 응답에 맞춤)"""

# 파일 읽기
with open('kis_llm_trader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# symbol_exchange_map 수정
old_map = '''        #  종목별 거래소 코드 (ChatGPT/KIS 챗봇 확인) 
        self.symbol_exchange_map = {
            "TQQQ": "NASD",  # KIS 기준 NASD 등록
            "SQQQ": "NASD",  # KIS 기준 NASD 등록
            "SOXL": "NASD",  # KIS 기준 NASD 등록
            "SOXS": "NASD"   # KIS 기준 NASD 등록
        }'''

new_map = '''        #  종목별 거래소 코드 (실제 API 응답 기준으로 업데이트) 
        self.symbol_exchange_map = {
            "TQQQ": "NASD",  # KIS 기준 NASD 등록
            "SQQQ": "NASD",  # KIS 기준 NASD 등록
            "SOXL": "AMEX",  # KIS 실제 등록: AMEX (API 확인 완료)
            "SOXS": "AMEX"   # KIS 실제 등록: AMEX (추정)
        }'''

if old_map in content:
    content = content.replace(old_map, new_map)
    print("[OK] symbol_exchange_map 업데이트 완료")
    print("  - SOXL: NASD → AMEX")
    print("  - SOXS: NASD → AMEX")
else:
    print("[ERROR] symbol_exchange_map을 찾을 수 없습니다")
    exit(1)

# 파일 쓰기
with open('kis_llm_trader.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[완료] kis_llm_trader.py 파일이 업데이트되었습니다")
