#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국투자증권 계좌 잔고 직접 확인
"""

import requests
import json
import time
import hmac
import hashlib
from datetime import datetime

def get_kis_credentials():
    """KIS API 인증 정보"""
    return {
        'app_key': 'PS8Q7XGd9t5k2vL1mN6pR3sT9wY2zA5b',
        'app_secret': 'B8vK2mN6pR3sT9wY2zA5bC7dF1gH4jL8q',
        'account_no': '12345678-01'
    }

def get_kis_access_token():
    """KIS 액세스 토큰 발급"""
    try:
        creds = get_kis_credentials()
        
        url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        headers = {
            "content-type": "application/json"
        }
        data = {
            "grant_type": "client_credentials",
            "appkey": creds['app_key'],
            "appsecret": creds['app_secret']
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            return result.get('access_token')
        else:
            print(f"[ERROR] 토큰 발급 실패: {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] 토큰 발급 예외: {e}")
        return None

def get_kis_balance():
    """한국투자증권 계좌 잔고 조회"""
    print("="*60)
    print("한국투자증권 계좌 잔고 확인")
    print("="*60)
    
    try:
        # 액세스 토큰 발급
        print("\n[1] 액세스 토큰 발급 중...")
        token = get_kis_access_token()
        if not token:
            print("  [ERROR] 토큰 발급 실패")
            return
        
        print("  [OK] 토큰 발급 성공")
        
        # 계좌 잔고 조회
        print("\n[2] 계좌 잔고 조회 중...")
        creds = get_kis_credentials()
        
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": creds['app_key'],
            "appsecret": creds['app_secret'],
            "tr_id": "TTTC8434R"
        }
        
        params = {
            "CANO": creds['account_no'].split('-')[0],
            "ACNT_PRDT_CD": creds['account_no'].split('-')[1],
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('rt_cd') == '0':
                output = data.get('output', [])
                if output:
                    print(f"  [OK] 잔고 조회 성공")
                    print(f"  총 평가금액: {output[0].get('tot_evlu_amt', 0):,}원")
                    print(f"  현금 잔고: {output[0].get('dnca_tot_amt', 0):,}원")
                    print(f"  주식 평가금액: {output[0].get('scts_evlu_amt', 0):,}원")
                    
                    # 보유 종목
                    holdings = [item for item in output if float(item.get('hldg_qty', 0)) > 0]
                    if holdings:
                        print(f"\n  보유 종목 ({len(holdings)}개):")
                        for item in holdings:
                            name = item.get('prdt_name', 'N/A')
                            qty = item.get('hldg_qty', 0)
                            price = item.get('prpr', 0)
                            print(f"    {name}: {qty}주 @ {price:,}원")
                    else:
                        print("  보유 종목 없음")
                else:
                    print("  [ERROR] 잔고 데이터 없음")
            else:
                print(f"  [ERROR] API 오류: {data.get('msg1', 'Unknown error')}")
        else:
            print(f"  [ERROR] HTTP 오류: {response.status_code}")
            
    except Exception as e:
        print(f"[ERROR] 잔고 조회 실패: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    get_kis_balance()
