#!/usr/bin/env python3
"""
통합 매니저 재시작 스크립트
- 기존 프로세스 종료 (자식 포함)
- 새 프로세스 시작
"""
import subprocess
import time
import os
import psutil

print("="*60)
print("통합 매니저 재시작")
print("="*60)

# 1. PID 파일 확인
pid_file = ".unified_trader_manager.pid"
if os.path.exists(pid_file):
    with open(pid_file, 'r') as f:
        old_pid = int(f.read().strip())

    print(f"\n[1] 기존 프로세스 종료 중... (PID: {old_pid})")

    try:
        parent = psutil.Process(old_pid)

        # 자식 프로세스 먼저 종료
        children = parent.children(recursive=True)
        for child in children:
            print(f"  - 자식 프로세스 종료: PID {child.pid}")
            child.terminate()

        # 부모 프로세스 종료
        parent.terminate()

        # 3초 대기
        gone, alive = psutil.wait_procs([parent] + children, timeout=3)

        # 강제 종료
        for p in alive:
            print(f"  - 강제 종료: PID {p.pid}")
            p.kill()

        print("[OK] 기존 프로세스 종료 완료")

    except psutil.NoSuchProcess:
        print("[INFO] 프로세스가 이미 종료됨")
    except Exception as e:
        print(f"[WARN] 종료 중 오류: {e}")

    # PID 파일 삭제
    try:
        os.remove(pid_file)
    except:
        pass

else:
    print("[INFO] PID 파일 없음, 프로세스 실행 중이 아닐 수 있음")

# 2. 대기
print("\n[2] 포트 정리 대기 중... (3초)")
time.sleep(3)

# 3. 새 프로세스 시작
print("\n[3] 새 통합 매니저 시작 중...")
subprocess.Popen(
    ["python", "unified_trader_manager.py"],
    creationflags=subprocess.CREATE_NEW_CONSOLE,
    cwd=os.path.dirname(os.path.abspath(__file__))
)

print("\n[OK] 통합 매니저 재시작 완료!")
print("="*60)
