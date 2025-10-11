import time
import subprocess
import os
from datetime import datetime

class RestartManager:
    def __init__(self, restart_interval_hours=6):
        """
        주기적 재시작 관리자
        :param restart_interval_hours: 재시작 주기 (시간 단위, 기본 6시간)
        """
        self.restart_interval = restart_interval_hours * 3600  # 초 단위로 변환
        self.last_restart = time.time()

    def kill_processes(self):
        """Ollama 및 Python 프로세스 종료"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 프로세스 종료 중...")

        # Ollama 프로세스 종료 (여러 번 시도)
        print("  Ollama 종료 중...")
        for attempt in range(3):
            try:
                subprocess.run(['taskkill', '/F', '/IM', 'ollama.exe'],
                             capture_output=True, timeout=30)
                print(f"   Ollama 프로세스 종료 (시도 {attempt+1})")
                break
            except subprocess.TimeoutExpired:
                print(f"   Ollama 종료 timeout (시도 {attempt+1}/3)")
                if attempt < 2:
                    time.sleep(5)
            except Exception as e:
                print(f"   Ollama 종료 실패: {e}")
                break

        # Python 트레이더 프로세스 종료 (현재 스크립트 제외)
        print("  Python 프로세스 종료 중...")
        try:
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                                  capture_output=True, text=True, timeout=30)

            # 현재 PID 제외하고 모두 종료
            current_pid = os.getpid()
            for line in result.stdout.split('\n')[1:]:  # 헤더 제외
                if 'python.exe' in line.lower():
                    parts = line.split(',')
                    if len(parts) >= 2:
                        pid = parts[1].strip('"')
                        if pid.isdigit() and int(pid) != current_pid:
                            try:
                                subprocess.run(['taskkill', '/F', '/PID', pid],
                                             capture_output=True, timeout=5)
                                print(f"   Python PID {pid} 종료")
                            except:
                                pass
        except Exception as e:
            print(f"   Python 종료 실패: {e}")

        # 정리 대기
        time.sleep(5)
        print("   프로세스 정리 완료")

    def start_ollama(self):
        """Ollama 서버 시작 (두 포트 - 코드3: 11434, 코드4: 11435)"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Ollama 서버 시작 중...")

        # 포트 11434 시작 (ETH 봇용)
        try:
            bat_path = r"C:\Users\user\Documents\코드3\start_ollama_11434.bat"
            if os.path.exists(bat_path):
                subprocess.Popen(['start', 'cmd', '/k', bat_path], shell=True)
                print("   Ollama 11434 (ETH) 시작")
            else:
                print(f"   {bat_path} 파일 없음")
        except Exception as e:
            print(f"   Ollama 11434 시작 실패: {e}")

        time.sleep(3)

        # 포트 11435 시작 (KIS 봇용)
        try:
            ps_path = r"C:\Users\user\Documents\코드4\start_ollama_11435.ps1"
            if os.path.exists(ps_path):
                subprocess.Popen(['powershell', '-File', ps_path],
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
                print("   Ollama 11435 (KIS) 시작")
            else:
                print(f"   {ps_path} 파일 없음")
        except Exception as e:
            print(f"   Ollama 11435 시작 실패: {e}")

        # Ollama 초기화 대기
        time.sleep(10)
        print("   Ollama 서버 시작 완료")

    def start_bots(self):
        """트레이딩 봇 시작"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 트레이딩 봇 시작 중...")

        # ETH 봇 시작
        try:
            eth_bot_path = r"C:\Users\user\Documents\코드3\llm_eth_trader.py"
            if os.path.exists(eth_bot_path):
                subprocess.Popen(['python', eth_bot_path],
                               cwd=r"C:\Users\user\Documents\코드3",
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
                print("   ETH 봇 시작")
            else:
                print(f"   {eth_bot_path} 파일 없음")
        except Exception as e:
            print(f"   ETH 봇 시작 실패: {e}")

        time.sleep(5)

        # KIS 봇 시작
        try:
            kis_bot_path = r"C:\Users\user\Documents\코드4\kis_llm_trader.py"
            if os.path.exists(kis_bot_path):
                subprocess.Popen(['python', kis_bot_path],
                               cwd=r"C:\Users\user\Documents\코드4",
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
                print("   KIS 봇 시작")
            else:
                print(f"   {kis_bot_path} 파일 없음")
        except Exception as e:
            print(f"   KIS 봇 시작 실패: {e}")

        time.sleep(5)
        print("   트레이딩 봇 시작 완료")

    def perform_restart(self):
        """전체 재시작 수행"""
        print("\n" + "="*60)
        print(f"[재시작 시작] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        # 1단계: 프로세스 종료
        self.kill_processes()

        # 2단계: Ollama 재시작
        self.start_ollama()

        # 3단계: 봇 재시작
        self.start_bots()

        # 재시작 시간 기록
        self.last_restart = time.time()

        print("="*60)
        print(f"[재시작 완료] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"다음 재시작: {self.restart_interval/3600:.1f}시간 후")
        print("="*60 + "\n")

    def run(self):
        """주기적 재시작 모니터링"""
        print("\n[주기적 재시작 관리자 시작]")
        print(f"  재시작 주기: {self.restart_interval/3600:.1f}시간")
        print(f"  종료: Ctrl+C\n")

        try:
            while True:
                # 경과 시간 계산
                elapsed = time.time() - self.last_restart
                remaining = self.restart_interval - elapsed

                # 재시작 필요 확인
                if remaining <= 0:
                    self.perform_restart()
                else:
                    # 상태 출력 (10분마다)
                    hours = remaining / 3600
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"다음 재시작까지: {hours:.1f}시간")
                    time.sleep(600)  # 10분 대기

        except KeyboardInterrupt:
            print("\n[주기적 재시작 관리자 종료]")


if __name__ == "__main__":
    # 재시작 주기: 6시간
    manager = RestartManager(restart_interval_hours=6)

    # 시작 시 즉시 재시작 (GPU 메모리 정리)
    print("\n[초기 재시작 수행] GPU 메모리 정리를 위한 초기 재시작...")
    manager.perform_restart()

    # 주기적 모니터링 시작
    manager.run()
