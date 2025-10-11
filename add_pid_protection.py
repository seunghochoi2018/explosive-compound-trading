#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""통합매니저에 PID 파일 기반 중복 방지 기능 추가"""

def add_pid_protection():
    file_path = r"C:\Users\user\Documents\코드5\unified_trader_manager.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # PID 파일 관리 함수 추가
    pid_functions = '''
# ===== PID 파일 관리 (중복 실행 방지) =====
PID_FILE = Path(__file__).parent / ".unified_trader_manager.pid"

def check_already_running():
    """이미 실행 중인 인스턴스가 있는지 확인"""
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())

            # PID가 실제로 실행 중인지 확인
            if psutil.pid_exists(old_pid):
                try:
                    proc = psutil.Process(old_pid)
                    # unified_trader_manager 프로세스인지 확인
                    cmdline = ' '.join(proc.cmdline())
                    if 'unified_trader_manager' in cmdline:
                        return old_pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (ValueError, FileNotFoundError):
            pass

    return None

def write_pid_file():
    """현재 프로세스 PID를 파일에 저장"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except Exception as e:
        colored_print(f"[WARNING] PID 파일 생성 실패: {e}", "yellow")
        return False

def remove_pid_file():
    """PID 파일 삭제"""
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception as e:
        colored_print(f"[WARNING] PID 파일 삭제 실패: {e}", "yellow")

'''

    # colored_print 함수 다음에 PID 함수 추가
    if '# ===== PID 파일 관리 (중복 실행 방지) =====' not in content:
        content = content.replace(
            '# ===== Ollama 헬스 체크 =====',
            pid_functions + '# ===== Ollama 헬스 체크 ====='
        )

    # main() 함수에 중복 체크 추가
    main_check = '''def main():
    # 중복 실행 체크
    running_pid = check_already_running()
    if running_pid:
        colored_print(f"⚠️  통합매니저가 이미 실행 중입니다 (PID: {running_pid})", "red")
        colored_print("기존 프로세스를 종료하거나 중복 실행을 원하면 PID 파일을 삭제하세요:", "yellow")
        colored_print(f"   {PID_FILE}", "yellow")
        return

    # PID 파일 생성
    write_pid_file()
    colored_print(f"✅ PID 파일 생성 완료 (PID: {os.getpid()})", "green")

    colored_print("=" * 70, "cyan")'''

    content = content.replace('def main():\n    colored_print("=" * 70, "cyan")', main_check)

    # if __name__ == "__main__": 블록에 finally 추가
    if_main_block = '''if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        colored_print("\\n[INFO] 사용자 중단", "yellow")
    except Exception as e:
        colored_print(f"\\n[CRITICAL ERROR] {e}", "red")
        colored_print("[CRITICAL ERROR] 프로세스 정리 중...", "red")
        kill_all_ollama()
    finally:
        # PID 파일 정리
        remove_pid_file()
        colored_print("[CLEANUP] PID 파일 삭제 완료", "green")'''

    # 기존 if __name__ == "__main__": 블록 찾아서 교체
    if 'finally:' not in content:
        old_block = '''if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        colored_print(f"\\n[CRITICAL ERROR] {e}", "red")
        colored_print("[CRITICAL ERROR] 프로세스 정리 중...", "red")
        kill_all_ollama()'''

        content = content.replace(old_block, if_main_block)

    # 파일 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("PID protection added successfully!")

if __name__ == "__main__":
    add_pid_protection()
