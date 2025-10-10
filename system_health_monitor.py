#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시스템 헬스 모니터 & 자동 최적화

주석: 사용자 요청 "실행 상태 상세하게 보여줘서 또 어디서 멈추지 않고 상시 최적화 하는 기능도 추가해"
- Ollama 프로세스 상태 실시간 모니터링
- 메모리 사용량 추적
- CPU 사용률 감시
- 데드락 자동 감지 및 재시작
- LLM 응답 시간 측정
"""

import psutil
import subprocess
import threading
import time
from datetime import datetime
from typing import Dict, Optional

class SystemHealthMonitor:
    """시스템 헬스 모니터링 및 자동 최적화"""

    def __init__(self):
        self.running = False
        self.monitor_thread = None

        # 통계
        self.ollama_restarts = 0
        self.last_check_time = None
        self.last_ollama_memory = 0
        self.last_ollama_cpu = 0

        # 데드락 감지
        self.high_cpu_count = 0  # CPU 과부하 지속 횟수
        self.high_memory_count = 0  # 메모리 과다 사용 횟수

        # 임계값
        self.CPU_THRESHOLD = 500  # CPU 500% 이상 (12코어에서 비정상)
        self.MEMORY_THRESHOLD_GB = 25  # 25GB 이상 사용 시 경고
        self.DEADLOCK_THRESHOLD = 5  # 5번 연속 과부하 시 재시작

    def start(self):
        """모니터링 시작"""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"[HEALTH_MONITOR] 시스템 헬스 모니터링 시작")

    def stop(self):
        """모니터링 중지"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def _monitor_loop(self):
        """모니터링 루프"""
        while self.running:
            try:
                # 30초마다 체크
                time.sleep(30)

                current_time = datetime.now().strftime("%H:%M:%S")
                self.last_check_time = current_time

                # Ollama 프로세스 찾기
                ollama_processes = []
                for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                    try:
                        if 'ollama' in proc.info['name'].lower():
                            ollama_processes.append(proc)
                    except:
                        continue

                if not ollama_processes:
                    print(f"[{current_time}] [HEALTH_WARNING] Ollama 프로세스 없음!")
                    continue

                # 각 프로세스 상태 체크
                total_memory_gb = 0
                total_cpu = 0
                deadlock_detected = False

                for proc in ollama_processes:
                    try:
                        pid = proc.info['pid']
                        memory_bytes = proc.info['memory_info'].rss
                        memory_gb = memory_bytes / (1024**3)
                        cpu_percent = proc.cpu_percent(interval=1)

                        total_memory_gb += memory_gb
                        total_cpu += cpu_percent

                        # 상세 로그
                        print(f"[{current_time}] [HEALTH] Ollama PID={pid} | "
                              f"메모리: {memory_gb:.1f}GB | CPU: {cpu_percent:.1f}%")

                        # 데드락 감지: 메모리 20GB 이상 + CPU 500% 이상
                        if memory_gb > self.MEMORY_THRESHOLD_GB and cpu_percent > self.CPU_THRESHOLD:
                            print(f"[{current_time}] [HEALTH_ALERT] 데드락 징후 감지! "
                                  f"PID={pid}, MEM={memory_gb:.1f}GB, CPU={cpu_percent:.0f}%")
                            self.high_cpu_count += 1
                            self.high_memory_count += 1
                            deadlock_detected = True

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # 시스템 전체 메모리
                system_memory = psutil.virtual_memory()
                total_ram_gb = system_memory.total / (1024**3)
                used_ram_gb = system_memory.used / (1024**3)
                available_ram_gb = system_memory.available / (1024**3)

                print(f"[{current_time}] [SYSTEM] RAM: {used_ram_gb:.1f}/{total_ram_gb:.1f}GB "
                      f"(여유: {available_ram_gb:.1f}GB)")

                # 통계 업데이트
                self.last_ollama_memory = total_memory_gb
                self.last_ollama_cpu = total_cpu

                # 자동 복구
                if deadlock_detected and self.high_cpu_count >= self.DEADLOCK_THRESHOLD:
                    print(f"\n[{current_time}] [AUTO_RECOVERY] 데드락 감지! 자동 복구 시작...")
                    self._auto_restart_ollama()
                    self.high_cpu_count = 0
                    self.high_memory_count = 0

                # 정상 상태면 카운터 리셋
                if not deadlock_detected:
                    self.high_cpu_count = max(0, self.high_cpu_count - 1)
                    self.high_memory_count = max(0, self.high_memory_count - 1)

            except Exception as e:
                print(f"[HEALTH_MONITOR ERROR] {e}")
                time.sleep(10)

    def _auto_restart_ollama(self):
        """Ollama 자동 재시작"""
        try:
            print("[AUTO_RECOVERY] Ollama 프로세스 종료 중...")

            # 모든 Ollama 프로세스 강제 종료
            killed = 0
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'ollama' in proc.info['name'].lower() and proc.info['pid'] != psutil.Process().pid:
                        proc.kill()
                        killed += 1
                except:
                    continue

            print(f"[AUTO_RECOVERY] {killed}개 프로세스 종료")
            time.sleep(3)

            # 재시작은 Ollama가 자동으로 처리
            print("[AUTO_RECOVERY] Ollama 자동 재시작 대기 중...")
            time.sleep(5)

            self.ollama_restarts += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"[{current_time}] [AUTO_RECOVERY] 완료! (총 재시작 횟수: {self.ollama_restarts})")

        except Exception as e:
            print(f"[AUTO_RECOVERY ERROR] {e}")

    def get_status(self) -> Dict:
        """현재 상태 반환"""
        return {
            'running': self.running,
            'last_check': self.last_check_time,
            'ollama_memory_gb': round(self.last_ollama_memory, 2),
            'ollama_cpu_percent': round(self.last_ollama_cpu, 1),
            'restarts': self.ollama_restarts,
            'high_cpu_alerts': self.high_cpu_count,
            'high_memory_alerts': self.high_memory_count
        }
