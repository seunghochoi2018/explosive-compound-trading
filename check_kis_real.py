#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국투자증권 실제 계좌 잔고 확인
"""

import yaml
import requests
import json
import time
import hmac
import hashlib
from datetime import datetime, timedelta

def load_kis_config():
    """KIS 설정 로드"""
    try:
        with open('kis_devlp.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"[ERROR] KIS 설정 로드 실패: {e}")
        return None

TOKEN_FILE = "kis_token.json"

def get_kis_access_token(force_refresh: bool = False):
    """KIS 액세스 토큰 (24시간 캐시)"""
    try:
        # 1) 캐시 사용 (24시간 유효)
        if not force_refresh:
            try:
                with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                token = saved.get('access_token')
                issued_at = saved.get('issued_at')
                if token and issued_at:
                    issued_dt = datetime.fromisoformat(issued_at)
                    if datetime.now() - issued_dt < timedelta(hours=24):
                        return token
            except Exception:
                pass

        # 2) 신규 발급
        config = load_kis_config()
        if not config:
            return None

        url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": config['my_app'],
            "appsecret": config['my_sec']
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            token = result.get('access_token')
            if token:
                with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
                    json.dump({
                        'access_token': token,
                        'issued_at': datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)
            return token
        else:
            print(f"[ERROR] 토큰 발급 실패: {response.status_code} - {response.text}")
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
        # 설정 로드
        config = load_kis_config()
        if not config:
            print("[ERROR] KIS 설정 로드 실패")
            return
            
        print(f"  앱키: {config['my_app'][:10]}...")
        print(f"  계좌번호: {config['my_acct']}")
        
        # 액세스 토큰 발급
        print("\n[1] 액세스 토큰 발급 중...")
        token = get_kis_access_token()
        if not token:
            print("  [ERROR] 토큰 발급 실패")
            return
        
        print("  [OK] 토큰 발급 성공")
        
        # 계좌 잔고 조회
        print("\n[2] 계좌 잔고 조회 중...")
        
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": config['my_app'],
            "appsecret": config['my_sec'],
            "tr_id": "TTTC8434R"
        }
        
        params = {
            "CANO": config['my_acct'].split('-')[0],
            "ACNT_PRDT_CD": config['my_acct'].split('-')[1],
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
        print(f"  HTTP 상태: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  응답 코드: {data.get('rt_cd', 'N/A')}")
            print(f"  응답 메시지: {data.get('msg1', 'N/A')}")
            
            if data.get('rt_cd') == '0':
                output = data.get('output', [])
                if output:
                    print(f"\n  [OK] 잔고 조회 성공")
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
            print(f"  응답: {response.text[:200]}")
            
    except Exception as e:
        print(f"[ERROR] 잔고 조회 실패: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    # 단일 토큰을 국내/해외 조회에 공용 사용
    token = get_kis_access_token()
    get_kis_balance()
    # ===== 해외주식 잔고 조회 (미국 840) =====
    try:
        print("\n" + "="*60)
        print("해외주식(미국) 잔고 확인")
        print("="*60)

        config = load_kis_config()
        if not (config and token):
            raise RuntimeError("KIS 설정/토큰 없음")

        url = "https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/inquire-balance"
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": config['my_app'],
            "appsecret": config['my_sec'],
            "tr_id": "TTTS3012R",
            "custtype": "P",
        }
        params = {
            "CANO": config['my_acct'].split('-')[0],
            "ACNT_PRDT_CD": config['my_acct'].split('-')[1],
            "WCRC_FRCR_DVSN_CD": "02",
            "NATN_CD": "840",
            "TR_MKET_CD": "01",
            "OVRS_EXCG_CD": "NASD",
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }

        resp = requests.get(url, headers=headers, params=params)
        print(f"  HTTP 상태: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            rt = data.get('rt_cd')
            msg = data.get('msg1')
            print(f"  응답 코드: {rt}")
            print(f"  응답 메시지: {msg}")

            if rt == '0':
                output = data.get('output', [])
                output1 = data.get('output1', [])  # 일부 응답은 output1 배열에 종목
                items = output1 if isinstance(output1, list) and output1 else output

                if items:
                    total_cash = 0.0
                    try:
                        # 예수금/현금성은 output의 특정 필드에 존재 가능
                        if isinstance(output, dict):
                            total_cash = float(output.get('ovrs_tot_pchs_amt', 0) or 0)
                    except Exception:
                        pass

                    print("\n  보유 종목:")
                    cnt = 0
                    for it in items:
                        try:
                            name = it.get('ovrs_pdno', 'N/A')
                            qty = it.get('ovrs_cblc_qty', it.get('hldg_qty', 0))
                            sym = it.get('ovrs_item_cd', it.get('pdno', ''))
                            prc = it.get('frst_bltn_excg_prc', it.get('prpr', 0))
                            print(f"    {sym or name}: {qty}주 @ {prc}")
                            cnt += 1
                        except Exception:
                            continue
                    if cnt == 0:
                        print("    (보유 종목 없음)")
                else:
                    print("  (조회할 내용이 없습니다)")
        else:
            print(f"  [ERROR] HTTP 오류: {resp.status_code}")
            print(f"  응답: {resp.text[:200]}")
    except Exception as e:
        print(f"[ERROR] 해외 잔고 조회 실패: {e}")
