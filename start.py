#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 봇 간단 실행기
- 원클릭 실행
- 모든 과정 자동화
"""

import os
import sys
import subprocess
from datetime import datetime

def print_welcome():
    """환영 메시지"""
    print(" NVDL/NVDQ 텔레그램 알림 봇")
    print("=" * 50)
    print(" NVDL: 3x 레버리지 NVIDIA ETF")
    print(" NVDQ: 2x 역 레버리지 NASDAQ ETF")
    print(" 텔레그램 실시간 알림")
    print("=" * 50)

def check_files():
    """필요한 파일 확인"""
    required_files = [
        'main_integrated.py',
        'nvdl_nvdq_data_collector.py',
        'nvdl_nvdq_trading_model.py',
        'nvdl_nvdq_telegram_bot.py',
        'telegram_notifier.py',
        'position_analysis_reporter.py'
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print(f" 누락된 파일: {', '.join(missing_files)}")
        return False

    print(" 모든 파일이 준비되었습니다.")
    return True

def install_packages():
    """필요한 패키지 설치"""
    print(" 필요한 패키지 설치 중...")
    packages = [
        'requests',
        'pandas',
        'numpy',
        'scikit-learn',
        'matplotlib',
        'seaborn'
    ]

    try:
        for package in packages:
            print(f"   {package} 설치 중...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', package],
                         capture_output=True, check=True)
        print(" 패키지 설치 완료!")
        return True
    except subprocess.CalledProcessError as e:
        print(f" 패키지 설치 실패: {e}")
        return False

def main():
    """메인 실행"""
    print_welcome()

    # 파일 확인
    if not check_files():
        print("\n 필요한 파일들을 먼저 준비해주세요.")
        return

    # 패키지 설치
    try:
        import requests, pandas, numpy, sklearn
        print(" 필요한 패키지가 이미 설치되어 있습니다.")
    except ImportError:
        if not install_packages():
            return

    # 사용자 선택
    print("\n 실행 모드를 선택하세요:")
    print("1.  알림 모드 (추천)")
    print("2.  자동매매 모드")
    print("3.  분석 보고서만")

    while True:
        choice = input("\n선택 (1-3): ").strip()

        if choice == '1':
            # 알림 모드
            print("\n 알림 모드로 시작합니다...")
            print(" 포지션 변경 시 텔레그램으로 알림을 보냅니다.")
            subprocess.run([sys.executable, 'main_integrated.py'])
            break

        elif choice == '2':
            # 자동매매 모드
            print("\n 자동매매 모드는 실제 거래를 수행할 수 있습니다!")
            confirm = input("정말 자동매매 모드로 실행하시겠습니까? (yes/no): ").lower()

            if confirm in ['yes', 'y']:
                print("\n 자동매매 모드로 시작합니다...")
                subprocess.run([sys.executable, 'main_integrated.py', '--auto-trading'])
            else:
                print(" 메인 메뉴로 돌아갑니다.")
                continue
            break

        elif choice == '3':
            # 분석 보고서만
            print("\n 분석 보고서를 생성합니다...")
            subprocess.run([sys.executable, 'main_integrated.py', '--analysis'])
            break

        else:
            print(" 잘못된 선택입니다. 1-3 중에서 선택해주세요.")

    print(f"\n 실행 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()