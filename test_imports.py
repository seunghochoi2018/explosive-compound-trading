#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
라이브러리 import 테스트 스크립트
KeyboardInterrupt 오류 해결을 위한 단계별 테스트
"""

import sys
import os

def test_imports():
    """필수 라이브러리 import 테스트"""
    print("=" * 50)
    print("라이브러리 Import 테스트 시작")
    print("=" * 50)
    
    # 기본 라이브러리 테스트
    basic_libs = [
        'subprocess', 'time', 'os', 'sys', 'io', 'json', 
        'threading', 're', 'datetime', 'pathlib', 'collections'
    ]
    
    for lib in basic_libs:
        try:
            __import__(lib)
            print(f"✓ {lib}")
        except ImportError as e:
            print(f"✗ {lib}: {e}")
            return False
    
    # 외부 라이브러리 테스트
    external_libs = ['requests', 'psutil']
    
    for lib in external_libs:
        try:
            __import__(lib)
            print(f"✓ {lib}")
        except ImportError as e:
            print(f"✗ {lib}: {e}")
            print(f"[INFO] {lib} 설치 중...")
            try:
                import subprocess
                subprocess.run([sys.executable, "-m", "pip", "install", lib], check=True)
                print(f"✓ {lib} 설치 완료")
            except Exception as install_error:
                print(f"✗ {lib} 설치 실패: {install_error}")
                return False
    
    print("=" * 50)
    print("모든 라이브러리 테스트 완료!")
    print("=" * 50)
    return True

def test_memory():
    """메모리 사용량 테스트"""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        print(f"현재 메모리 사용량: {memory_mb:.1f}MB")
        
        if memory_mb > 1000:
            print("⚠️  메모리 사용량이 높습니다 (1GB 초과)")
            return False
        else:
            print("✓ 메모리 사용량 정상")
            return True
    except Exception as e:
        print(f"✗ 메모리 체크 실패: {e}")
        return False

def test_network():
    """네트워크 연결 테스트"""
    try:
        import requests
        response = requests.get("https://httpbin.org/get", timeout=5)
        if response.status_code == 200:
            print("✓ 네트워크 연결 정상")
            return True
        else:
            print(f"✗ 네트워크 응답 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 네트워크 연결 실패: {e}")
        return False

if __name__ == "__main__":
    print("통합 트레이더 관리자 사전 테스트")
    print("KeyboardInterrupt 오류 해결을 위한 진단")
    print()
    
    # 1. 라이브러리 테스트
    if not test_imports():
        print("\n❌ 라이브러리 테스트 실패")
        sys.exit(1)
    
    # 2. 메모리 테스트
    if not test_memory():
        print("\n⚠️  메모리 사용량이 높습니다")
        print("스크립트 실행 시 KeyboardInterrupt가 발생할 수 있습니다.")
    
    # 3. 네트워크 테스트
    if not test_network():
        print("\n⚠️  네트워크 연결에 문제가 있습니다")
        print("API 호출 시 타임아웃이 발생할 수 있습니다.")
    
    print("\n✅ 모든 테스트 완료!")
    print("이제 메인 스크립트를 실행할 수 있습니다.")
    print("\n실행 명령어:")
    print("python \"c:\\Users\\user\\Documents\\코드5\\unified_trader_manager 연습.py\"")
