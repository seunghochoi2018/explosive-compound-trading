#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS 계좌 잔고 확인 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kis_api_manager import KISAPIManager
from api_config import get_kis_credentials

def check_kis_balance():
    """KIS 계좌 잔고 확인"""
    print("="*60)
    print("KIS 계좌 잔고 확인")
    print("="*60)
    
    try:
        # KIS API 연결
        creds = get_kis_credentials()
        api = KISAPIManager(
            app_key=creds['app_key'],
            app_secret=creds['app_secret'],
            account_no=creds['account_no']
        )
        
        # 잔고 조회
        print("\n[1] 현금 잔고 조회...")
        balance = api.get_balance()
        if balance:
            print(f"  현금 잔고: {balance.get('cash', 0):,.0f}원")
            print(f"  주식 평가금액: {balance.get('stock_value', 0):,.0f}원")
            print(f"  총 자산: {balance.get('total_asset', 0):,.0f}원")
        else:
            print("  [ERROR] 잔고 조회 실패")
            
        # 보유 종목 조회
        print("\n[2] 보유 종목 조회...")
        positions = api.get_positions()
        if positions:
            print(f"  보유 종목 수: {len(positions)}개")
            for pos in positions:
                print(f"    {pos.get('name', 'N/A')}: {pos.get('qty', 0)}주")
        else:
            print("  보유 종목 없음")
            
        # 계좌 정보
        print("\n[3] 계좌 정보...")
        account_info = api.get_account_info()
        if account_info:
            print(f"  계좌번호: {account_info.get('account_no', 'N/A')}")
            print(f"  계좌명: {account_info.get('account_name', 'N/A')}")
        
    except Exception as e:
        print(f"[ERROR] KIS 잔고 확인 실패: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    check_kis_balance()
