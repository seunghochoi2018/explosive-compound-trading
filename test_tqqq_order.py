#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TQQQ 주문 테스트 스크립트
"""
import json
import requests

# KIS API 설정
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"
ACCOUNT_NO = "43113014"
ACCOUNT_CODE = "01"

# PDNO 매핑
PDNO_MAP = {
    "TQQQ": "A206892",
    "SQQQ": "A206893"
}

def load_token():
    """토큰 로드"""
    try:
        with open("kis_token.json", 'r') as f:
            token_data = json.load(f)
            return token_data.get('access_token')
    except Exception as e:
        print(f"❌ 토큰 로드 실패: {e}")
        return None

def get_current_price(token, symbol):
    """현재가 조회"""
    url = f"{BASE_URL}/uapi/overseas-price/v1/quotations/price"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "HHDFS00000300",
        "custtype": "P"
    }
    params = {
        "AUTH": "",
        "EXCD": "NAS",
        "SYMB": symbol
    }

    print(f"\n[현재가 조회 시도]")
    print(f"URL: {url}")
    print(f"Symbol: {symbol}")
    print(f"EXCD: NAS")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"HTTP {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            result = response.json()
            print(f"rt_cd: {result.get('rt_cd')}")

            if result.get("rt_cd") == "0":
                output = result.get("output", {})
                price_str = output.get('last', '0')
                print(f"last 가격: {price_str}")

                if not price_str or price_str.strip() == '':
                    price_str = output.get('base', '0')
                    print(f"base 가격: {price_str}")

                try:
                    price = float(price_str)
                    if price > 0:
                        return price
                    else:
                        print(f"가격이 0 이하: {price}")
                except Exception as e:
                    print(f"가격 변환 실패: {e}")
            else:
                msg = result.get('msg1', 'Unknown')
                print(f"API 오류: {msg}")
        else:
            print(f"HTTP 오류: {response.status_code}")
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
    return None

def get_hashkey(token, data):
    """해시키 생성"""
    url = f"{BASE_URL}/uapi/hashkey"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            return result.get('HASH', '')
    except Exception as e:
        print(f"❌ 해시키 생성 실패: {e}")
    return ""

def test_buy_order(symbol="TQQQ", quantity=1):
    """TQQQ 매수 테스트"""
    print("="*70)
    print(f"[TQQQ 주문 테스트]")
    print("="*70)

    # 1. 토큰 로드
    token = load_token()
    if not token:
        print("❌ 토큰 로드 실패")
        return

    print("✅ 토큰 로드 성공")

    # 2. 현재가 조회
    current_price = get_current_price(token, symbol)
    if not current_price:
        print(f"❌ {symbol} 가격 조회 실패")
        return

    print(f"✅ {symbol} 현재가: ${current_price:.2f}")

    # 3. PDNO 변환
    pdno = PDNO_MAP.get(symbol)
    if not pdno:
        print(f"❌ {symbol} PDNO 매핑 없음")
        return

    print(f"✅ PDNO: {pdno}")

    # 4. 주문 데이터 생성
    order_data = {
        "CANO": ACCOUNT_NO,
        "ACNT_PRDT_CD": ACCOUNT_CODE,
        "OVRS_EXCG_CD": "NASD",
        "PDNO": pdno,
        "ORD_QTY": str(quantity),
        "OVRS_ORD_UNPR": f"{current_price:.2f}",
        "ORD_SVR_DVSN_CD": "0",
        "ORD_DVSN": "00"
    }

    print(f"\n[주문 데이터]")
    print(json.dumps(order_data, indent=2, ensure_ascii=False))

    # 5. 해시키 생성
    hashkey = get_hashkey(token, order_data)
    print(f"\n✅ Hashkey: {hashkey[:20]}...")

    # 6. 주문 실행
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/order"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "TTTT1002U",
        "custtype": "P",
        "hashkey": hashkey
    }

    print(f"\n[주문 전송 중...]")
    print(f"URL: {url}")
    print(f"TR_ID: TTTT1002U")

    try:
        response = requests.post(url, headers=headers, json=order_data, timeout=10)
        print(f"\n[응답]")
        print(f"HTTP {response.status_code}")
        print(response.text)

        if response.status_code == 200:
            result = response.json()
            if result.get("rt_cd") == "0":
                order_no = result.get('output', {}).get('ODNO', 'N/A')
                print(f"\n✅✅✅ 주문 성공! ✅✅✅")
                print(f"주문번호: {order_no}")
                print(f"{symbol} {quantity}주 @ ${current_price:.2f}")
            else:
                msg = result.get('msg1', 'Unknown error')
                print(f"\n❌ 주문 실패: {msg}")
                print(f"rt_cd: {result.get('rt_cd')}")
                print(f"msg_cd: {result.get('msg_cd')}")
        else:
            print(f"\n❌ HTTP 오류: {response.status_code}")

    except Exception as e:
        print(f"\n❌ 주문 예외: {e}")

    print("\n" + "="*70)

if __name__ == "__main__":
    test_buy_order("TQQQ", 1)
