#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS API 주문 요청 상세 디버깅"""
import json
import yaml
import requests
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

print("="*80)
print("KIS API 주문 요청 상세 디버깅")
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

# SOXS 현재가 조회 (FMP API)
print("\n[1] SOXS 현재가 조회 (FMP API)...")
fmp_url = "https://financialmodelingprep.com/api/v3/quote/SOXS"
fmp_response = requests.get(fmp_url, params={'apikey': '5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI'}, timeout=10)
current_price = 0
if fmp_response.status_code == 200:
    fmp_data = fmp_response.json()
    if fmp_data:
        current_price = fmp_data[0].get('price', 0)
        print(f"  SOXS 현재가: ${current_price:.2f}")

if current_price <= 0:
    current_price = 4.0  # 테스트용 기본값
    print(f"  [WARN] 가격 조회 실패, 테스트용 기본값 사용: ${current_price:.2f}")

# 주문 요청 구성
print("\n[2] 주문 요청 구성 (매도 184주)...")
order_url = f"{base_url}/uapi/overseas-stock/v1/trading/order"
tr_id = "JTTT1006U"  # 매도

headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key,
    "appsecret": app_secret,
    "tr_id": tr_id,
    "content-type": "application/json; charset=utf-8"
}

order_data = {
    "CANO": account_no.split('-')[0],
    "ACNT_PRDT_CD": account_no.split('-')[1],
    "OVRS_EXCG_CD": "NASD",
    "PDNO": "A980680",  # SOXS
    "ORD_QTY": "184",
    "OVRS_ORD_UNPR": str(current_price),
    "ORD_SVR_DVSN_CD": "0"
}

print(f"\n[3] 요청 상세 정보:")
print(f"  URL: {order_url}")
print(f"  Method: POST")
print(f"  TR_ID: {tr_id}")
print(f"\n  Headers:")
for key, value in headers.items():
    if key == "authorization":
        print(f"    {key}: Bearer {access_token[:20]}... (토큰 앞 20자)")
    else:
        print(f"    {key}: {value}")

print(f"\n  Request Body (JSON):")
print(json.dumps(order_data, indent=4, ensure_ascii=False))

# JSON 형식 검증
print(f"\n[4] JSON 형식 검증:")
try:
    json_str = json.dumps(order_data)
    json.loads(json_str)
    print(f"  JSON 유효성: OK")
    print(f"  JSON 크기: {len(json_str)} bytes")
except Exception as e:
    print(f"  JSON 유효성: FAIL - {e}")

# 인증 정보 검증
print(f"\n[5] 인증 정보 검증:")
print(f"  AppKey: {app_key[:10]}... (앞 10자)")
print(f"  AppSecret: {app_secret[:10]}... (앞 10자)")
print(f"  Access Token: {access_token[:30]}... (앞 30자)")
issue_time = datetime.fromisoformat(token_data['issue_time'])
token_age = (datetime.now() - issue_time).total_seconds() / 3600
print(f"  토큰 발급: {issue_time.strftime('%Y-%m-%d %H:%M:%S')} ({token_age:.1f}시간 전)")
print(f"  토큰 상태: {'유효' if token_age < 24 else '만료'}")

# Hashkey 확인 (해외주식 주문은 hashkey 불필요하지만 확인)
print(f"\n[6] Hashkey 요구 여부:")
print(f"  해외주식 주문 API는 일반적으로 hashkey 불필요")
print(f"  현재 요청: hashkey 미포함")

# Rate Limit 확인
print(f"\n[7] Rate Limit 확인:")
print(f"  KIS API 제한: 초당 20건, 분당 200건")
print(f"  현재 요청: 단일 요청 (제한 내)")

# 실제 주문 요청 (상세 로깅)
print(f"\n[8] 실제 주문 요청 실행...")
print(f"  현재 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")

try:
    # 요청 전 마지막 확인
    print(f"\n  요청 전송 중...")
    response = requests.post(
        order_url,
        headers=headers,
        json=order_data,
        timeout=30
    )

    print(f"\n[9] 응답 결과:")
    print(f"  HTTP 상태 코드: {response.status_code}")
    print(f"  응답 시간: {response.elapsed.total_seconds():.3f}초")

    # 응답 헤더
    print(f"\n  응답 헤더:")
    for key, value in response.headers.items():
        print(f"    {key}: {value}")

    # 응답 본문
    print(f"\n  응답 본문:")
    try:
        response_json = response.json()
        print(json.dumps(response_json, indent=4, ensure_ascii=False))

        # 상세 분석
        if response.status_code == 200:
            rt_cd = response_json.get('rt_cd')
            msg_cd = response_json.get('msg_cd')
            msg1 = response_json.get('msg1')

            print(f"\n[10] 응답 분석:")
            print(f"  rt_cd: {rt_cd}")
            print(f"  msg_cd: {msg_cd}")
            print(f"  msg1: {msg1}")

            if rt_cd == '0':
                print(f"\n  [SUCCESS] 주문 성공!")
                output = response_json.get('output', {})
                print(f"  주문번호: {output.get('ODNO', 'N/A')}")
            else:
                print(f"\n  [ERROR] 주문 실패")
                print(f"  에러 분석:")

                # 일반적인 에러 코드 설명
                error_codes = {
                    'EGW00201': '초당 거래건수 초과 (Rate Limit)',
                    'EGW00356': '타임 스탬프 오류',
                    'APBK1507': '시장가 주문 시 가격 입력 필요',
                    'APBK1508': '주문 수량 오류',
                    'APBK1509': '주문 가격 오류',
                    'APBK2904': '주문 시간 외',
                }

                if msg_cd in error_codes:
                    print(f"    {msg_cd}: {error_codes[msg_cd]}")
                else:
                    print(f"    알 수 없는 에러 코드: {msg_cd}")

        elif response.status_code == 500:
            print(f"\n  [ERROR] HTTP 500 서버 내부 오류")
            print(f"  원인 가능성:")
            print(f"    1. KIS API 서버 일시적 장애")
            print(f"    2. 요청 데이터 형식 오류")
            print(f"    3. 인증 정보 오류")
            print(f"    4. Rate Limit 초과")

    except json.JSONDecodeError:
        print(f"  응답 본문 (Raw Text):")
        print(f"  {response.text}")

except requests.exceptions.Timeout:
    print(f"\n  [ERROR] 요청 타임아웃 (30초)")
except requests.exceptions.ConnectionError as e:
    print(f"\n  [ERROR] 연결 오류: {e}")
except Exception as e:
    print(f"\n  [ERROR] 예외 발생: {type(e).__name__}: {e}")

print("\n" + "="*80)
print("디버깅 완료")
print("="*80)

# 추가 정보
print(f"\n[참고] KIS 고객의소리 문의 시 포함할 정보:")
print(f"  - 요청 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  - API: {order_url}")
print(f"  - TR_ID: {tr_id}")
print(f"  - 계좌번호: {account_no}")
print(f"  - 에러 코드: (위 응답에서 확인)")
print(f"  - HTTP 상태: (위 응답에서 확인)")
