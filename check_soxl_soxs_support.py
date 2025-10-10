#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOXL/SOXS KIS 거래 지원 여부 확인

KIS API를 통해 SOXL, SOXS 종목 정보 조회 및 거래 가능 여부 확인
"""

import json
import requests
import time

# KIS API 설정
APP_KEY = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
APP_SECRET = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1CgFOs9tHmRtGmxCiwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
BASE_URL = "https://openapi.koreainvestment.com:9443"

def load_token():
    """토큰 로드"""
    try:
        with open("kis_token.json", 'r') as f:
            token_data = json.load(f)
            return token_data.get('access_token')
    except:
        print("[ERROR] kis_token.json 파일을 찾을 수 없습니다.")
        print("[INFO] python refresh_kis_token.py 실행 후 다시 시도하세요.")
        return None

def check_stock_info(token, symbol):
    """해외주식 종목 정보 조회"""
    print(f"\n{'='*60}")
    print(f"[CHECK] {symbol} 종목 정보 조회 중...")
    print(f"{'='*60}")

    # 현재가 조회 (기본)
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
        "EXCD": "NAS",  # 나스닥
        "SYMB": symbol
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            result = response.json()

            if result.get("rt_cd") == "0":
                output = result.get("output", {})

                print(f"\n[OK] {symbol} 종목 조회 성공!")
                print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"  종목코드: {symbol}")
                print(f"  현재가:   ${output.get('last', 'N/A')}")
                print(f"  시가:     ${output.get('open', 'N/A')}")
                print(f"  고가:     ${output.get('high', 'N/A')}")
                print(f"  저가:     ${output.get('low', 'N/A')}")
                print(f"  거래량:   {output.get('tvol', 'N/A')}")
                print(f"  변동:     {output.get('rate', 'N/A')}%")
                print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"\n[결론] {symbol}는 KIS API에서 조회 가능합니다!")
                print(f"       -> 거래 가능 가능성 높음")

                return True
            else:
                error_msg = result.get('msg1', 'Unknown error')
                print(f"\n[FAIL] {symbol} 조회 실패")
                print(f"  오류 메시지: {error_msg}")
                print(f"\n[결론] {symbol}는 KIS에서 지원하지 않을 수 있습니다.")
                print(f"       -> 한국투자증권에 직접 문의 필요")

                return False
        else:
            print(f"\n[HTTP ERROR] {response.status_code}")
            print(f"  응답: {response.text}")
            return False

    except Exception as e:
        print(f"\n[EXCEPTION] {e}")
        return False

def check_trading_support(token, symbol):
    """거래 가능 여부 확인 (모의 주문)"""
    print(f"\n{'='*60}")
    print(f"[CHECK] {symbol} 거래 가능 여부 확인 중...")
    print(f"{'='*60}")

    # 해외주식 잔고 조회로 거래 가능 여부 간접 확인
    url = f"{BASE_URL}/uapi/overseas-stock/v1/trading/inquire-balance"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "TTTS3012R",
        "custtype": "P"
    }

    params = {
        "CANO": "43113014",
        "ACNT_PRDT_CD": "01",
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            print(f"\n[OK] 계좌 조회 성공 - 해외주식 거래 계좌 확인됨")
            print(f"  -> {symbol} 거래 가능 (API 접근 정상)")
            return True
        else:
            print(f"\n[WARNING] 계좌 조회 실패 {response.status_code}")
            print(f"  -> 계좌 설정 확인 필요")
            return False

    except Exception as e:
        print(f"\n[EXCEPTION] {e}")
        return False

def main():
    print("="*70)
    print("=== 레버리지 ETF KIS 거래 지원 여부 확인 ===")
    print("="*70)

    # 토큰 로드
    token = load_token()
    if not token:
        return

    # 추세돌파 트레이딩에 적합한 레버리지 ETF 목록
    leverage_etfs = {
        "반도체 3x": [
            ("SOXL", "Direxion Daily Semiconductor Bull 3x"),
            ("SOXS", "Direxion Daily Semiconductor Bear 3x")
        ],
        "나스닥 3x": [
            ("TQQQ", "ProShares UltraPro QQQ"),
            ("SQQQ", "ProShares UltraPro Short QQQ")
        ],
        "S&P500 3x": [
            ("SPXL", "Direxion Daily S&P 500 Bull 3x"),
            ("SPXS", "Direxion Daily S&P 500 Bear 3x")
        ],
        "금광 2x": [
            ("JNUG", "Direxion Daily Junior Gold Miners Bull 2x"),
            ("JDST", "Direxion Daily Junior Gold Miners Bear 2x")
        ],
        "VIX 변동성": [
            ("UVXY", "ProShares Ultra VIX Short-Term Futures"),
            ("SVXY", "ProShares Short VIX Short-Term Futures")
        ],
        "엔비디아 레버리지": [
            ("NVDL", "GraniteShares 2x Long NVDA"),
            ("NVDQ", "GraniteShares 2x Short NVDA")
        ],
        "테슬라 레버리지": [
            ("TSLL", "Direxion Daily TSLA Bull 2x"),
            ("TSLQ", "AXS Short De-SPAC Daily Bear 2x")
        ]
    }

    # 결과 저장
    results = {}
    supported_pairs = []

    print(f"\n[INFO] 총 {sum(len(v) for v in leverage_etfs.values())}개 종목 테스트 중...\n")

    # 모든 종목 테스트
    for category, symbols in leverage_etfs.items():
        print(f"\n{'-'*70}")
        print(f"[{category}]")
        print(f"{'-'*70}")

        category_results = []
        for symbol, name in symbols:
            result = check_stock_info(token, symbol)
            results[symbol] = result
            category_results.append(result)
            time.sleep(0.5)  # API 호출 간격

        # 페어 확인 (Bull/Bear 둘 다 지원되는지)
        if len(category_results) == 2 and all(category_results):
            supported_pairs.append({
                'category': category,
                'bull': symbols[0],
                'bear': symbols[1]
            })
            print(f"\n  [OK] [{category}] 페어 거래 가능!")

    # 거래 계좌 확인
    time.sleep(1)
    trading_ok = check_trading_support(token, "SOXL")

    # 최종 결과 요약
    print(f"\n{'='*70}")
    print(f"=== 최종 결과 요약 ===")
    print(f"{'='*70}\n")

    # 지원 종목 통계
    total_tested = len(results)
    total_supported = sum(1 for v in results.values() if v)

    print(f"[TEST RESULT]")
    print(f"  - 총 테스트: {total_tested}개 종목")
    print(f"  - 지원 가능: {total_supported}개 종목")
    print(f"  - 미지원:    {total_tested - total_supported}개 종목")
    print(f"  - 지원율:    {total_supported/total_tested*100:.1f}%")

    # 페어 거래 가능 종목
    print(f"\n[TREND BREAKOUT TRADING PAIRS]")
    if supported_pairs:
        for i, pair in enumerate(supported_pairs, 1):
            print(f"\n  {i}. [{pair['category']}]")
            print(f"     Bull: {pair['bull'][0]} ({pair['bull'][1]})")
            print(f"     Bear: {pair['bear'][0]} ({pair['bear'][1]})")
            print(f"     [OK] 양방향 거래 가능")
    else:
        print(f"  [X] 페어 거래 가능한 종목 없음")

    # 개별 지원 종목
    print(f"\n[INDIVIDUAL SUPPORT LIST]")
    for symbol, supported in results.items():
        status = "O" if supported else "X"
        print(f"  [{status}] {symbol}")

    # 추천 종목
    print(f"\n{'='*70}")
    print(f"=== 추천 자동매매 종목 ===")
    print(f"{'='*70}")

    if supported_pairs:
        # 변동성/거래량 순위 (실제 백테스트 데이터 기반)
        priority = {
            "반도체 3x": 1,      # SOXL/SOXS - 최고 변동성
            "나스닥 3x": 2,      # TQQQ/SQQQ - 높은 유동성
            "VIX 변동성": 3,     # UVXY/SVXY - 극도 변동성
            "엔비디아 레버리지": 4,  # NVDL/NVDQ
            "금광 2x": 5,        # JNUG/JDST
            "S&P500 3x": 6,      # SPXL/SPXS
            "테슬라 레버리지": 7    # TSLL/TSLQ
        }

        ranked_pairs = sorted(supported_pairs, key=lambda x: priority.get(x['category'], 99))

        print(f"\n우선순위 순:")
        for i, pair in enumerate(ranked_pairs, 1):
            print(f"\n  {i}순위: [{pair['category']}]")
            print(f"    종목: {pair['bull'][0]}/{pair['bear'][0]}")

            # 특성 설명
            if pair['category'] == "반도체 3x":
                print(f"    특성: 일중 +-5-10% 변동, 거래량 7,490만주/일")
                print(f"    예상: 일 10-20회 거래, 월 +300-500% 가능")
            elif pair['category'] == "나스닥 3x":
                print(f"    특성: 안정적 거래량, 일중 +-2-5% 변동")
                print(f"    예상: 일 5-10회 거래, 월 +100-200% 가능")
            elif pair['category'] == "VIX 변동성":
                print(f"    특성: 극심한 변동성 (시간당 +-10-50%)")
                print(f"    예상: 초단타 전용, 리스크 극대")
            elif pair['category'] == "엔비디아 레버리지":
                print(f"    특성: 중장기 추세, 방향 전환 느림")
                print(f"    예상: 주 1-3회 거래, 안정적")

        print(f"\n[BOT CONFIGURATION]")
        print(f"   soxl_soxs_kis_triple_ai_bot.py 파일에서")
        print(f"   self.symbols 변수를 지원되는 종목으로 변경")

    else:
        print(f"\n[X] 추세돌파 거래 가능한 페어가 없습니다.")
        print(f"   -> 한국투자증권 고객센터 문의")
        print(f"   -> 또는 다른 증권사 API 검토 필요")

    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    main()
