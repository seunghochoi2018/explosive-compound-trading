#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS 고객센터 문의용 에러 로그 수집"""
import json
import yaml
import requests
from datetime import datetime

print("="*80)
print("KIS 고객센터 문의용 에러 로그 수집")
print("="*80)

# 설정 로드
with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

with open('kis_token.json', 'r', encoding='utf-8') as f:
    token_data = json.load(f)

app_key = config['my_app']
app_secret = config['my_sec']
account_no = config['my_acct']
access_token = token_data['access_token']
base_url = "https://openapi.koreainvestment.com:9443"

# SOXS 현재가 조회
print("\n[1] SOXS 현재가 조회...")
fmp_url = "https://financialmodelingprep.com/api/v3/quote/SOXS"
fmp_response = requests.get(fmp_url, params={'apikey': '5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'}, timeout=10)
current_price = 0
if fmp_response.status_code == 200:
    fmp_data = fmp_response.json()
    if fmp_data:
        current_price = fmp_data[0].get('price', 0)
        print(f"SOXS 현재가: ${current_price:.2f}")

if current_price <= 0:
    current_price = 10.0  # Fallback
    print(f"SOXS 가격 조회 실패, fallback: ${current_price:.2f}")

# 매도 주문 시도
print(f"\n[2] SOXS 1주 매도 주문 테스트...")

order_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"

# 요청 시간 기록
request_time = datetime.now()
request_time_str = request_time.strftime("%Y-%m-%d %H:%M:%S")

headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": "JTTT1006U",  # 매도
    "custtype": "P",
    "content-type": "application/json; charset=utf-8",
    "tr_cont": "N",
    "tr_cont_key": ""
}

order_data = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "A980680",  # SOXS
    "ORD_QTY": "1",
    "OVRS_ORD_UNPR": str(current_price),
    "ORD_SVR_DVSN_CD": "0",
    "SLL_TYPE": "00",  # 매도=00
    "ORD_DVSN": "00"   # 지정가
}

print("\n[3] 요청 정보:")
print(f"요청 시간: {request_time_str}")
print(f"TR_ID: JTTT1006U (해외주식 매도)")
print(f"종목코드: A980680 (SOXS)")
print(f"수량: 1주")
print(f"가격: ${current_price:.2f}")

try:
    response = requests.post(order_url, headers=headers, json=order_data, timeout=30)
    response_time = datetime.now()

    print(f"\n[4] 응답:")
    print(f"응답 시간: {response_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"HTTP 상태: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        error_code = result.get('msg_cd', 'UNKNOWN')
        error_msg = result.get('msg1', '알 수 없는 오류')

        print(f"rt_cd: {result.get('rt_cd')}")
        print(f"msg_cd: {error_code}")
        print(f"msg1: {error_msg}")
    else:
        try:
            result = response.json()
            error_code = result.get('msg_cd', 'UNKNOWN')
            error_msg = result.get('msg1', '알 수 없는 오류')
        except:
            error_code = f"HTTP_{response.status_code}"
            error_msg = response.text[:200]

    # 고객센터 문의용 리포트 작성
    report = {
        "제목": "해외주식 매도 API EGW00356 오류 문의 (TR: JTTT1006U)",
        "발생_일시": request_time_str,
        "계정_정보": {
            "계좌번호_앞8자리": account_no[:8],
            "AppKey_앞10자리": app_key[:10] + "...",
            "환경": "실전투자 (https://openapi.koreainvestment.com:9443)"
        },
        "요청_정보": {
            "TR_ID": "JTTT1006U",
            "종목코드": "A980680 (SOXS)",
            "주문_수량": "1주",
            "주문_가격": f"${current_price:.2f}",
            "주문_구분": "지정가 (ORD_DVSN=00)",
            "매도_구분": "SLL_TYPE=00"
        },
        "요청_헤더": {
            "tr_id": "JTTT1006U",
            "custtype": "P",
            "content-type": "application/json; charset=utf-8",
            "tr_cont": "N",
            "tr_cont_key": "",
            "기타": "authorization, appkey, appsecret 포함"
        },
        "요청_바디": order_data,
        "오류_정보": {
            "오류_코드": error_code,
            "오류_메시지": error_msg,
            "HTTP_상태": response.status_code
        },
        "추가_정보": {
            "시도한_해결방법": [
                "SLL_TYPE, ORD_DVSN 파라미터 추가",
                "PDNO를 A980680 (고유코드) 사용",
                "custtype 헤더 추가",
                "tr_cont, tr_cont_key 헤더 추가",
                "시장가 주문 시도 (ORD_DVSN=01)",
                "헤더/Body에 타임스탬프 필드 추가 시도"
            ],
            "잔고_조회_API": "정상 작동 (TTTS3012R)",
            "해외주식_거래권한": "있음 (잔고 조회 성공)",
            "USD_잔고": "$0.00",
            "문의사항": [
                "EGW00356 에러의 정확한 원인",
                "해외주식 주문 API의 정확한 필수 필드",
                "타임스탬프 관련 필드의 정확한 위치와 형식"
            ]
        }
    }

    # JSON 파일로 저장
    report_file = f"kis_error_report_{request_time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print("[고객센터 문의용 리포트 생성 완료]")
    print(f"{'='*80}")
    print(f"파일명: {report_file}")

    print(f"\n[문의 내용 요약]")
    print(f"제목: {report['제목']}")
    print(f"발생 일시: {report['발생_일시']}")
    print(f"오류 코드: {error_code}")
    print(f"오류 메시지: {error_msg}")

    print(f"\n[첨부 정보]")
    print(f"1. 계좌번호 (앞8자리): {account_no[:8]}****")
    print(f"2. AppKey (앞10자리): {app_key[:10]}...")
    print(f"3. 요청 TR_ID: JTTT1006U")
    print(f"4. 종목코드: A980680 (SOXS)")
    print(f"5. 요청 시간: {request_time_str}")
    print(f"6. 오류 코드: {error_code}")
    print(f"7. 오류 메시지: {error_msg}")

    print(f"\n[문의 내용]")
    print("안녕하세요.")
    print("해외주식 매도 API(JTTT1006U) 사용 중 EGW00356 오류가 지속적으로 발생합니다.")
    print("")
    print(f"발생 일시: {request_time_str}")
    print(f"TR_ID: JTTT1006U (해외주식 매도)")
    print(f"오류 코드: {error_code}")
    print(f"오류 메시지: {error_msg}")
    print("")
    print("시도한 해결 방법:")
    for i, method in enumerate(report['추가_정보']['시도한_해결방법'], 1):
        print(f"  {i}. {method}")
    print("")
    print("문의 사항:")
    for i, question in enumerate(report['추가_정보']['문의사항'], 1):
        print(f"  {i}. {question}")
    print("")
    print(f"상세 요청/응답 정보는 첨부된 JSON 파일({report_file})을 참고해 주세요.")
    print("")
    print("감사합니다.")

    print(f"\n{'='*80}")
    print("[고객센터 연락처]")
    print(f"{'='*80}")
    print("전화: 1544-5000")
    print("이메일: apihelp@koreainvestment.com")
    print("개발자 포털: https://apiportal.koreainvestment.com")

except Exception as e:
    print(f"\n[ERROR] 예외 발생: {e}")
    import traceback
    traceback.print_exc()
