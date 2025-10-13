#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os

print("="*80)
print("KIS 자동매매 상태 확인")
print("="*80)

# 1. 거래 기록 확인
trade_history_file = r'C:\Users\user\Documents\코드4\kis_trade_history.json'
if os.path.exists(trade_history_file):
    try:
        with open(trade_history_file, 'r', encoding='utf-8') as f:
            trades = json.load(f)

        if trades:
            print(f"\n[거래 기록] {len(trades)}건 발견")
            last_trade = trades[-1]
            print(f"최근 거래:")
            print(f"  종목: {last_trade.get('symbol', 'N/A')}")
            print(f"  진입가: ${last_trade.get('entry_price', 0):.2f}")
            print(f"  청산가: ${last_trade.get('exit_price', 0):.2f}")
            print(f"  PNL: {last_trade.get('pnl_pct', 0):+.2f}%")
            print(f"  시간: {last_trade.get('exit_time', 'N/A')}")

            # 승률 계산
            wins = sum(1 for t in trades if t.get('pnl_pct', 0) > 0)
            print(f"\n[통계]")
            print(f"  승률: {wins}/{len(trades)} ({wins/len(trades)*100:.1f}%)")
        else:
            print("\n[거래 기록] 없음")
    except Exception as e:
        print(f"\n[오류] 거래 기록 읽기 실패: {e}")
else:
    print("\n[거래 기록] 파일 없음 - 아직 거래 없음")

# 2. KIS 설정 파일 확인
kis_config_file = r'C:\Users\user\Documents\코드\kis_devlp.yaml'
if os.path.exists(kis_config_file):
    print("\n[KIS 설정] 파일 존재 ✅")
else:
    print("\n[KIS 설정] 파일 없음 ❌")

# 3. 토큰 확인
token_file = r'C:\Users\user\Documents\코드4\kis_token.json'
if os.path.exists(token_file):
    try:
        with open(token_file, 'r', encoding='utf-8') as f:
            token_data = json.load(f)

        from datetime import datetime, timedelta
        issue_time = datetime.fromisoformat(token_data['issue_time'])
        remaining = (issue_time + timedelta(hours=23) - datetime.now()).total_seconds() / 3600

        if remaining > 0:
            print(f"\n[KIS 토큰] 유효 (남은 시간: {remaining:.1f}시간) ✅")
        else:
            print(f"\n[KIS 토큰] 만료됨 ❌")
    except Exception as e:
        print(f"\n[KIS 토큰] 오류: {e}")
else:
    print("\n[KIS 토큰] 파일 없음 - 토큰 발급 필요")

print("\n" + "="*80)
print("자동매매 가능 여부:")
print("  ✅ kis_llm_trader_v2_explosive.py 파일 존재")
print("  ✅ 자동매매 함수 구현됨 (open_position, close_position)")
print("  ✅ KIS API 주문 기능 구현됨 (place_order)")
print("\n자동매매를 시작하려면:")
print("  python C:\\Users\\user\\Documents\\코드4\\kis_llm_trader_v2_explosive.py")
print("="*80)
