import requests
import time

# 실전 환경용 토큰 (tokenP로 발급된 것 사용)
ACCESS_TOKEN = "여기에_실전용_액세스토큰_입력"
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1Ciwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"

# 테스트 대상 종목
SYMBOL = "TQQQ"
PDNO = "A206892"       # TQQQ 정식 종목코드
EXCD = "NASD"          # 거래소 코드

# API 경로 (PDNO 기반 사용 권장)
URL = f"{BASE_URL}/uapi/overseas-price/v1/quotations/price?EXCD={EXCD}&PDNO={PDNO}"

headers = {
    "authorization": f"Bearer {ACCESS_TOKEN}",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET,
    "tr_id": "HHDFS00000300",  # 시세조회용 TR
    "custtype": "P"
}

# 요청 및 예외 처리
def get_price():
    try:
        response = requests.get(URL, headers=headers)
        print(f"[HTTP 응답 코드] {response.status_code}")
        data = response.json()

        if response.status_code == 200:
            rt_cd = data.get("rt_cd", "")
            if rt_cd == "0":
                price = data["output"]["stck_prpr"]
                print(f" 현재가(TQQQ): {price}")
            else:
                print(f" API 오류 코드: {data.get('msg_cd')} / {data.get('msg1')}")
        else:
            print(f" HTTP 오류 발생: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(" 예외 발생:", str(e))

# 자동 재시도 포함 실행
def run_test_with_retry(retries=3, delay_sec=5):
    for attempt in range(1, retries + 1):
        print(f"\n[시도 {attempt}] TQQQ 시세 조회 중...")
        get_price()
        if attempt < retries:
            print(f"⏳ {delay_sec}초 후 재시도...")
            time.sleep(delay_sec)

# 테스트 실행
run_test_with_retry()
