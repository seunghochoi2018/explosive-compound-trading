#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS 페이퍼 트레이딩 모드 시작"""
import subprocess
import sys
import os

print("="*80)
print("KIS 페이퍼 트레이딩 모드 시작")
print("="*80)

# 환경 변수 설정
env = os.environ.copy()
env['KIS_PAPER_MODE'] = '1'  # 페이퍼 모드 플래그

print("\n[INFO] 페이퍼 모드 활성화")
print("[INFO] kis_llm_trader_v2_explosive.py 실행 중...")

# KIS 트레이더 실행
subprocess.Popen(
    [sys.executable, "kis_llm_trader_v2_explosive.py"],
    cwd=r"C:\Users\user\Documents\코드5",
    env=env,
    creationflags=subprocess.CREATE_NEW_CONSOLE
)

print("\n[SUCCESS] KIS 페이퍼 트레이딩 시작됨!")
print("="*80)
