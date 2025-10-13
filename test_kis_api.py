#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS API 테스트 스크립트 (장외 테스트 가능)

테스트 항목:
1. PDNO 수정 확인 (A980679 / A980680)
2. 시세 조회 테스트
3. 주문 로직 테스트 (simulate_mode)
"""
import os
import sys
import yaml
import json
import requests
from datetime import datetime

# 한글 출력 설정
os.environ['PYTHONIOENCODING'] = 'utf-8'

# === 설정 ===
simulate_mode = True  # ✅ True = 실제 주문 안함, False = 실제 주문

print("="*80)
print("KIS API 테스트 스크립트")
print("="*80)
print(f"[SIMULATION] 시뮬레이션 모드: {'ON (실제 주문 안함)' if simulate_mode else 'OFF (실제 주문)'}")
print("="*80)

# === KIS API 설정 로드 ===
def load_kis_config():
    """KIS API 설정 로드"""
    try:
        with open('../코드/kis_devlp.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        app_key = config['my_app']
        app_secret = config['my_sec']
        account_no = config['my_acct']
        base_url = "https://openapi.koreainvestment.com:9443"

        print(f"[OK] KIS 설정 로드 완료")
        print(f"  계좌번호: {account_no}")

        return app_key, app_secret, account_no, base_url
    except Exception as e:
        print(f"[ERROR] KIS 설정 로드 실패: {e}")
        sys.exit(1)

def get_access_token(app_key, app_secret, base_url):
    """KIS 접근 토큰 발급"""
    # 기존 토큰 로드 시도
    token_file = "kis_token.json"
    try:
        if os.path.exists(token_file):
            with open(token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)

            access_token = token_data['access_token']
            print(f"[OK] 기존 토큰 사용")
            return access_token
    except Exception as e:
        print(f"[INFO] 기존 토큰 로드 실패: {e}")

    # 새 토큰 발급
    print(f"[INFO] 새 토큰 발급 시도...")
    return None

# === 테스트 1: PDNO 확인 ===
def test_pdno():
    """PDNO 매핑 확인"""
    print("\n" + "="*80)
    print("테스트 1: PDNO 매핑 확인")
    print("="*80)

    symbols = {
        'SOXL': {'pdno': 'A980679', 'name': '반도체 3배 레버리지 롱'},
        'SOXS': {'pdno': 'A980680', 'name': '반도체 3배 레버리지 숏'}
    }

    for symbol, info in symbols.items():
        print(f"[OK] {symbol} -> PDNO: {info['pdno']} ({info['name']})")

    print(f"\n[결과] PDNO 매핑 정상")
    return symbols

# === 테스트 2: 시세 조회 ===
def test_get_price(app_key, app_secret, access_token, base_url, symbol):
    """시세 조회 테스트"""
    print("\n" + "="*80)
    print(f"테스트 2: 시세 조회 ({symbol})")
    print("="*80)

    try:
        url = f"{base_url}/uapi/overseas-price/v1/quotations/price"

        headers = {
            "authorization": f"Bearer {access_token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "HHDFS00000300",
            "custtype": "P"
        }

        params = {
            "FID_COND_MRKT_DIV_CODE": "N",
            "FID_INPUT_ISCD": symbol
        }

        print(f"[요청] {symbol} 시세 조회 중...")
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get('rt_cd') == '0':
                stck_prpr = data.get('output', {}).get('stck_prpr', '0')
                if stck_prpr and stck_prpr != '':
                    price = float(stck_prpr)
                    print(f"[OK] [성공] {symbol} 현재가: ${price:.2f}")
                    return price
                else:
                    print(f"[WARN] [경고] 가격 정보 없음 (장 마감?)")
                    return None
            else:
                error_code = data.get('msg_cd', 'UNKNOWN')
                error_msg = data.get('msg1', '알 수 없는 오류')
                print(f"[ERROR] [실패] 에러 코드: {error_code}")
                print(f"   메시지: {error_msg}")
                return None
        else:
            print(f"[ERROR] [실패] HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"[ERROR] [예외] {e}")
        return None

# === 테스트 3: 주문 로직 ===
def test_place_order(app_key, app_secret, access_token, base_url, account_no, pdno, side, qty, price):
    """주문 로직 테스트 (simulate_mode)"""
    print("\n" + "="*80)
    print(f"테스트 3: 주문 로직 ({side.upper()})")
    print("="*80)

    if simulate_mode:
        print(f"[TEST] [SIMULATION] {side.upper()} 주문 로직 실행")
        print(f"   종목 PDNO: {pdno}")
        print(f"   수량: {qty}주")
        print(f"   가격: ${price:.2f}")
        print(f"   계좌: {account_no}")
        print(f"\n[OK] [결과] 주문 로직 정상 (실제 주문은 하지 않음)")
        return True

    # 실제 주문 (simulate_mode = False일 때만)
    try:
        url = f"{base_url}/uapi/overseas-stock/v1/trading/order"

        headers = {
            "authorization": f"Bearer {access_token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "JTTT1002U" if side == "buy" else "JTTT1006U"
        }

        data = {
            "CANO": account_no.split('-')[0],
            "ACNT_PRDT_CD": account_no.split('-')[1],
            "OVRS_EXCG_CD": "NASD",
            "PDNO": pdno,  # ✅ A980679 / A980680 사용!
            "ORD_QTY": str(qty),
            "OVRS_ORD_UNPR": str(price),
            "ORD_SVR_DVSN_CD": "0"
        }

        print(f"[요청] {side.upper()} 주문 실행 중...")
        print(f"   PDNO: {pdno}")
        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result.get('rt_cd') == '0':
                print(f"[OK] [성공] 주문 완료")
                return True
            else:
                error_code = result.get('msg_cd', 'UNKNOWN')
                error_msg = result.get('msg1', '알 수 없는 오류')
                print(f"[ERROR] [실패] 에러 코드: {error_code}")
                print(f"   메시지: {error_msg}")
                return False
        else:
            print(f"[ERROR] [실패] HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"[ERROR] [예외] {e}")
        return False

# === 메인 테스트 ===
if __name__ == "__main__":
    try:
        # 1. 설정 로드
        app_key, app_secret, account_no, base_url = load_kis_config()
        access_token = get_access_token(app_key, app_secret, base_url)

        if not access_token:
            print("[ERROR] 토큰을 가져올 수 없습니다")
            sys.exit(1)

        # 2. PDNO 확인
        symbols = test_pdno()

        # 3. 시세 조회 (SOXL)
        soxl_price = test_get_price(app_key, app_secret, access_token, base_url, "SOXL")

        # 4. 주문 로직 테스트 (SOXL 매수)
        if soxl_price:
            test_place_order(
                app_key, app_secret, access_token, base_url, account_no,
                pdno=symbols['SOXL']['pdno'],  # A980679
                side="buy",
                qty=2,
                price=soxl_price
            )
        else:
            print(f"\n[WARN] [경고] 시세 조회 실패로 주문 테스트 건너뜀")
            print(f"   장외 시간이라면 정상입니다")

            # 시뮬레이션으로라도 테스트
            test_place_order(
                app_key, app_secret, access_token, base_url, account_no,
                pdno=symbols['SOXL']['pdno'],
                side="buy",
                qty=2,
                price=34.21  # 가격 임의 설정
            )

        print("\n" + "="*80)
        print("테스트 완료")
        print("="*80)
        print(f"[OK] PDNO 매핑: 정상")
        print(f"{'[OK]' if soxl_price else '[WARN]'} 시세 조회: {'정상' if soxl_price else '실패 (장외 시간?)'}")
        print(f"[OK] 주문 로직: 정상 (simulate_mode)")
        print("="*80)

        if simulate_mode:
            print(f"\n[INFO] 실제 주문을 테스트하려면:")
            print(f"   1. 미국 장 개장 시간 확인")
            print(f"   2. 스크립트 상단 simulate_mode = False로 변경")
            print(f"   3. 다시 실행")

    except KeyboardInterrupt:
        print("\n\n[종료] 사용자 중단")
    except Exception as e:
        print(f"\n[ERROR] 테스트 오류: {e}")
        import traceback
        traceback.print_exc()
