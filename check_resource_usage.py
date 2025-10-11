#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""리소스 사용량 분석"""
import psutil
import sys

# UTF-8 인코딩
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 전체 시스템 리소스
mem = psutil.virtual_memory()
print(f"=== 시스템 리소스 ===")
print(f"RAM Total: {mem.total / 1024**3:.1f} GB")
print(f"RAM Used: {mem.used / 1024**3:.1f} GB ({mem.percent}%)")
print(f"RAM Available: {mem.available / 1024**3:.1f} GB")
print()

# 주요 프로세스 확인
print("=== 주요 프로세스 ===")
ollama_pids = []
python_pids = []

for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
    try:
        if proc.info['name'] == 'ollama.exe':
            mem_mb = proc.info['memory_info'].rss / 1024**2
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            port = ''
            if '11434' in cmdline:
                port = '(ETH)'
            elif '11435' in cmdline:
                port = '(KIS)'
            elif '11436' in cmdline:
                port = '(Self-Improvement)'
            print(f"Ollama PID {proc.info['pid']}: {mem_mb:.1f} MB {port}")
            ollama_pids.append((proc.info['pid'], mem_mb))
        elif proc.info['name'] in ['python.exe', 'pythonw.exe']:
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            if 'unified_trader_manager' in cmdline or 'llm_eth_trader' in cmdline or 'kis_llm_trader' in cmdline:
                mem_mb = proc.info['memory_info'].rss / 1024**2
                script_name = ''
                if 'unified_trader_manager' in cmdline:
                    script_name = '(Manager)'
                elif 'llm_eth_trader' in cmdline:
                    script_name = '(ETH Trader)'
                elif 'kis_llm_trader' in cmdline:
                    script_name = '(KIS Trader)'
                print(f"Python PID {proc.info['pid']}: {mem_mb:.1f} MB {script_name}")
                python_pids.append((proc.info['pid'], mem_mb))
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print()
print("=== 리소스 분석 ===")
total_ollama_mem = sum(mem for _, mem in ollama_pids) / 1024  # GB
total_python_mem = sum(mem for _, mem in python_pids) / 1024  # GB
total_trading_mem = total_ollama_mem + total_python_mem

print(f"Ollama 총 메모리: {total_ollama_mem:.2f} GB")
print(f"Python 총 메모리: {total_python_mem:.2f} GB")
print(f"트레이딩 시스템 총: {total_trading_mem:.2f} GB")
print(f"여유 메모리: {mem.available / 1024**3:.2f} GB")
print()

# 추가 투입 가능 여부
print("=== 리소스 추가 투입 가능 여부 ===")
available_gb = mem.available / 1024**3
if available_gb > 10:
    print(f"[OK] 여유 메모리 충분: {available_gb:.1f} GB")
    print("추가 가능:")
    print("  - 듀얼 앙상블 LLM (각 트레이더당 +8GB)")
    print("  - 더 큰 모델 (32b 모델: +16GB)")
    print("  - 추가 트레이더 (다른 종목)")
elif available_gb > 5:
    print(f"[WARN] 여유 메모리 보통: {available_gb:.1f} GB")
    print("제한적 추가 가능:")
    print("  - 작은 모델 추가 (8b 이하)")
elif available_gb > 2:
    print(f"[WARN] 여유 메모리 부족: {available_gb:.1f} GB")
    print("추가 권장하지 않음")
else:
    print(f"[ERROR] 메모리 부족: {available_gb:.1f} GB")
    print("현재 시스템 안정성 우선")
