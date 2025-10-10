# -*- coding: utf-8 -*-
"""kis_llm_trader.py의 get_positions() 함수 수정 스크립트"""

# 파일 읽기
with open('kis_llm_trader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 수정할 부분
old_code = '''                        # ⭐ PDNO → Symbol 변환 ⭐
                        symbol = self.pdno_symbol_map.get(pdno, None)
                        if symbol is None:
                            print(f"[DEBUG] PDNO {pdno}는 매핑되지 않은 종목 (스킵)")
                            continue'''

new_code = '''                        # ⭐ PDNO → Symbol 변환 (API가 심볼을 반환하는 경우도 처리) ⭐
                        symbol = self.pdno_symbol_map.get(pdno, None)

                        # PDNO로 변환 실패 시, API가 심볼을 직접 반환한 경우 확인
                        if symbol is None:
                            # symbol_pdno_map에 있는 종목인지 확인 (API가 심볼 반환)
                            if pdno in self.symbol_pdno_map:
                                symbol = pdno  # API가 이미 심볼을 반환한 경우
                                print(f"[DEBUG] API가 심볼 직접 반환: {symbol}")
                            else:
                                print(f"[DEBUG] PDNO/Symbol {pdno}는 매핑되지 않은 종목 (스킵)")
                                continue'''

# 교체
if old_code in content:
    content = content.replace(old_code, new_code)
    print("[OK] get_positions() 수정 완료")
else:
    print("[ERROR] 기존 코드를 찾을 수 없습니다")
    exit(1)

# 파일 쓰기
with open('kis_llm_trader.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[완료] kis_llm_trader.py 파일이 업데이트되었습니다")
