# -*- coding: utf-8 -*-
"""USD 잔고 조회 함수에 상세 디버깅 로그 추가"""

# 파일 읽기
with open('kis_llm_trader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 기존 함수 교체
old_code = '''        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('rt_cd') == '0':
                    output = result.get('output', {})
                    return {
                        'success': True,
                        'ord_psbl_frcr_amt': float(output.get('ord_psbl_frcr_amt', '0').replace(',', ''))
                    }
            return {'success': False}
        except:
            return {'success': False}'''

new_code = '''        print(f"[DEBUG] USD 잔고 조회 시작")
        print(f"[DEBUG] 심볼: {symbol}, 가격: ${price:.2f}, 거래소: {exchange_cd}")
        print(f"[DEBUG] URL: {url}")
        print(f"[DEBUG] TR_ID: {headers.get('tr_id')}")

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"[DEBUG] HTTP 응답 코드: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                rt_cd = result.get('rt_cd', 'N/A')
                msg_cd = result.get('msg_cd', 'N/A')
                msg1 = result.get('msg1', 'N/A')

                print(f"[DEBUG] rt_cd: {rt_cd}")
                print(f"[DEBUG] msg_cd: {msg_cd}")
                print(f"[DEBUG] msg1: {msg1}")

                if rt_cd == '0':
                    output = result.get('output', {})
                    print(f"[DEBUG] output 데이터: {output}")

                    if output:
                        ord_psbl_frcr_amt = output.get('ord_psbl_frcr_amt', '0')
                        print(f"[DEBUG] 매수가능금액 (원본): {ord_psbl_frcr_amt}")

                        try:
                            usd_amount = float(ord_psbl_frcr_amt.replace(',', ''))
                            print(f"[OK] USD 잔고 조회 성공: ${usd_amount:.2f}")
                            return {
                                'success': True,
                                'ord_psbl_frcr_amt': usd_amount
                            }
                        except Exception as e:
                            print(f"[ERROR] 금액 파싱 실패: {e}")
                            return {'success': False, 'error': f'금액 파싱 실패: {e}'}
                    else:
                        print(f"[WARN] output 데이터가 비어있음")
                        # 빈 output도 성공으로 처리 (잔고 0)
                        return {'success': True, 'ord_psbl_frcr_amt': 0.0}
                else:
                    print(f"[ERROR] API 응답 실패 - rt_cd={rt_cd}, msg_cd={msg_cd}, msg1={msg1}")
                    return {'success': False, 'error': f'{msg_cd}: {msg1}'}
            else:
                print(f"[ERROR] HTTP 오류: {response.status_code}")
                print(f"[ERROR] 응답 내용: {response.text[:500]}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}

        except requests.exceptions.Timeout:
            print(f"[ERROR] 타임아웃: 10초 이내 응답 없음")
            return {'success': False, 'error': 'Timeout'}
        except Exception as e:
            print(f"[ERROR] 예외 발생: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}'''

# 교체
if old_code in content:
    content = content.replace(old_code, new_code)
    print("[OK] USD 잔고 조회 함수 디버깅 로그 추가 완료")
else:
    print("[ERROR] 기존 코드를 찾을 수 없습니다")
    exit(1)

# 파일 쓰기
with open('kis_llm_trader.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[완료] kis_llm_trader.py 파일이 업데이트되었습니다")
