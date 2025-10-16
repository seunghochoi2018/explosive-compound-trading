#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIS 트레이더를 완전히 독립적인 프로세스로 시작"""
import subprocess
import sys
import os

# 작업 디렉토리
os.chdir(r'C:\Users\user\Documents\코드5')

# Windows DETACHED_PROCESS 플래그
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

# KIS 트레이더를 완전히 독립적으로 시작
# stdout/stderr를 파일로 리다이렉트
with open('kis_output.log', 'w', encoding='utf-8') as log_file:
    process = subprocess.Popen(
        [sys.executable, '-u', 'kis_llm_trader_v2_explosive.py'],  # -u: unbuffered
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        close_fds=False
    )

    print(f"KIS 트레이더 시작됨: PID {process.pid}")
    print(f"로그 파일: kis_output.log")
    print("프로세스는 이 스크립트 종료 후에도 계속 실행됩니다.")
