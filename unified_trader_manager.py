#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 트레이더 관리 시스템
- 코드3 (ETH 트레이더) + 코드4 (KIS 트레이더) 동시 관리
- Ollama 2개 독립 실행 (포트 충돌 방지)
- 지능적 리소스 관리 (메모리, CPU, 큐잉 감지)
- 타임아웃 자동 복구
- 주기적 재시작 (4시간)
"""
import subprocess
import time
import psutil
import os
import requests
from datetime import datetime
from pathlib import Path
from collections import deque
import threading
import re

# ===== 텔레그램 알림 =====
class TelegramNotifier:
    def __init__(self):
        self.bot_token = "7819173403:AAEwBNh6etqyWvh-GivLDrTJb8b_ho2ju-U"
        self.chat_id = "7805944420"
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_message(self, message: str):
        try:
            payload = {'chat_id': self.chat_id, 'text': message, 'parse_mode': 'HTML'}
            response = requests.post(self.base_url, data=payload, timeout=5)
            return response.status_code == 200
        except:
            return False

    def notify_system_start(self):
        message = "🚀 <b>통합 트레이더 시스템 시작</b>\n\n✅ ETH Trader\n✅ KIS Trader\n✅ Ollama 관리자"
        self.send_message(message)

    def notify_system_error(self, error_msg: str):
        message = f"⚠️ <b>시스템 오류</b>\n\n{error_msg}"
        self.send_message(message)

    def notify_position_change(self, trader: str, action: str, details: str):
        message = f"🔄 <b>{trader} 포지션 변경</b>\n\n{action}\n{details}"
        self.send_message(message)

    def notify_ollama_restart(self, trader: str, reason: str):
        message = f"🔧 <b>{trader} Ollama 재시작</b>\n\n사유: {reason}"
        self.send_message(message)

telegram = TelegramNotifier()

# ===== 설정 =====
RESTART_INTERVAL = 4 * 60 * 60  # 4시간 (초 단위)
GUARDIAN_CHECK_INTERVAL = 10  # ⭐ 실시간 Ollama 체크: 10초마다

# Ollama 설정
OLLAMA_EXE = r"C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe"
OLLAMA_PORT_ETH = 11434  # 코드3 (ETH) 전용
OLLAMA_PORT_KIS = 11435  # 코드4 (KIS) 전용
OLLAMA_PORT_IMPROVEMENT = 11436  # ⭐ 자기개선 엔진 전용
ALLOWED_PORTS = [OLLAMA_PORT_ETH, OLLAMA_PORT_KIS, OLLAMA_PORT_IMPROVEMENT]  # 허가된 포트

# 트레이더 설정
ETH_TRADER_DIR = r"C:\Users\user\Documents\코드3"
ETH_TRADER_SCRIPT = r"C:\Users\user\Documents\코드3\llm_eth_trader_v3_explosive.py"  # 폭발 전략 (14b)
ETH_PYTHON = r"C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe"

KIS_TRADER_DIR = r"C:\Users\user\Documents\코드4"
KIS_TRADER_SCRIPT = r"C:\Users\user\Documents\코드4\kis_llm_trader_v2_explosive.py"  # 폭발 전략 (14b)
KIS_PYTHON = r"C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe"

# 모델 업그레이드 전략 (공평하게!)
# 1단계: ETH 14b×1 + KIS 14b×1 = 16GB (완료)
# 2단계: ETH (16b+7b) + KIS (16b+7b) + Self-Improvement (16b+7b) = 29GB (현재 ⭐)
# 3단계: ETH 16b×2 + KIS 16b×2 + Self-Improvement 16b×2 = 48GB (메모리 충분시)

# ===== 리소스 모니터링 설정 =====
MAX_MEMORY_MB = 10 * 1024  # Ollama 메모리 상한: 10GB
MAX_CPU_PERCENT = 5.0  # 정상 상태 CPU: 5% 이하
RESPONSE_TIMEOUT = 10  # API 응답 타임아웃: 10초
QUEUE_DETECT_THRESHOLD = 60  # 큐잉 감지: 60초 이상 CPU 0%

# 응답 시간 추적 (최근 10개)
response_times_eth = deque(maxlen=10)
response_times_kis = deque(maxlen=10)

# ⭐ 거래/수익 모니터링 설정
TRADING_CHECK_INTERVAL = 60 * 60  # 1시간마다 거래 현황 체크
ETH_TRADE_HISTORY = r"C:\Users\user\Documents\코드3\eth_trade_history.json"
KIS_TRADE_HISTORY = r"C:\Users\user\Documents\코드4\kis_trade_history.json"

# ⭐ 자기개선 엔진 설정 (통합) - 16b + 7b 듀얼 앙상블!
SELF_IMPROVEMENT_INTERVAL = 60 * 60  # 1시간마다 자기 분석
IMPROVEMENT_REPORT_INTERVAL = 6 * 60 * 60  # 6시간마다 텔레그램 리포트
OLLAMA_IMPROVEMENT_HOST = f"http://127.0.0.1:{OLLAMA_PORT_IMPROVEMENT}"
OLLAMA_IMPROVEMENT_MODEL_PRIMARY = "deepseek-coder-v2:16b"  # 주 모델
OLLAMA_IMPROVEMENT_MODEL_SECONDARY = "qwen2.5:7b"  # 검증 모델
OLLAMA_IMPROVEMENT_TIMEOUT = 60

# 자기개선 상태 추적
improvement_history_eth = []
improvement_history_kis = []
ETH_STRATEGY_FILE = r"C:\Users\user\Documents\코드3\eth_current_strategy.json"
KIS_STRATEGY_FILE = r"C:\Users\user\Documents\코드4\kis_current_strategy.json"

# ===== 색상 출력 =====
def colored_print(message, color="white"):
    """색상 출력"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{colors.get(color, colors['white'])}[{timestamp}] {message}{colors['reset']}")

# ===== Ollama 헬스 체크 =====
def check_ollama_health(port):
    """Ollama 상태 체크 (메모리, CPU, 응답성)"""
    try:
        # 1. 프로세스 찾기
        ollama_proc = None
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
            try:
                if proc.info['name'] == 'ollama.exe':
                    cmdline = proc.info.get('cmdline', [])
                    # 환경변수로 포트 구분은 어려우므로 PID 추적 필요
                    # 일단 메모리 기준으로 체크
                    ollama_proc = proc
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not ollama_proc:
            return {"status": "not_running", "action": "restart"}

        # 2. 메모리 체크
        memory_mb = ollama_proc.info['memory_info'].rss / 1024 / 1024
        if memory_mb > MAX_MEMORY_MB:
            return {
                "status": "high_memory",
                "memory_mb": memory_mb,
                "action": "restart"
            }

        # 3. CPU 체크 (0%인데 요청 있으면 큐잉 의심)
        cpu_percent = ollama_proc.cpu_percent(interval=1)

        # 4. API 응답 체크 (⭐ 타임아웃 증가: 30초)
        start_time = time.time()
        try:
            response = requests.get(f"http://127.0.0.1:{port}/api/tags", timeout=30)
            response_time = time.time() - start_time

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "memory_mb": memory_mb,
                    "cpu_percent": cpu_percent,
                    "response_time": response_time
                }
            else:
                return {"status": "api_error", "action": "restart"}

        except requests.Timeout:
            return {
                "status": "timeout",
                "cpu_percent": cpu_percent,
                "action": "restart"
            }
        except requests.ConnectionError:
            # ⭐ 연결 오류여도 프로세스가 살아있으면 재시작 안함
            return {"status": "starting", "memory_mb": memory_mb}

    except Exception as e:
        return {"status": "error", "error": str(e), "action": "restart"}

def should_restart_ollama(health_status, response_times):
    """Ollama 재시작 필요 여부 판단 (지능적 판단)"""
    # 1. 명시적 재시작 필요
    if health_status.get("action") == "restart":
        reason = health_status.get("status")
        if reason == "high_memory":
            return True, f"메모리 과다 ({health_status['memory_mb']:.1f}MB > {MAX_MEMORY_MB}MB)"
        elif reason == "timeout":
            return True, f"API 타임아웃 (CPU: {health_status.get('cpu_percent', 0):.1f}%)"
        elif reason == "not_running":
            return True, "프로세스 종료됨"
        elif reason == "connection_error":
            return True, "연결 오류"
        else:
            return True, reason

    # 2. 응답 시간 패턴 분석 (최근 3개가 모두 5초 이상 → 큐잉)
    if len(response_times) >= 3:
        recent_3 = list(response_times)[-3:]
        if all(t > 5.0 for t in recent_3):
            avg_time = sum(recent_3) / 3
            return True, f"응답 지연 (평균 {avg_time:.1f}초)"

    # 3. CPU 0% + 응답 느림 (큐잉)
    cpu = health_status.get("cpu_percent", 0)
    response_time = health_status.get("response_time", 0)
    if cpu < 1.0 and response_time > 3.0:
        return True, f"큐잉 의심 (CPU: {cpu:.1f}%, 응답: {response_time:.1f}초)"

    return False, None

# ===== Ollama 관리 =====
def kill_all_ollama():
    """모든 Ollama 프로세스 종료"""
    try:
        subprocess.run(
            ["powershell", "-Command", "Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force"],
            timeout=10,
            capture_output=True
        )
        time.sleep(2)
        colored_print("Ollama 프로세스 모두 종료", "yellow")
    except Exception as e:
        colored_print(f"Ollama 종료 실패: {e}", "red")

def start_ollama(port):
    """Ollama 시작 (독립 인스턴스)"""
    try:
        # PowerShell 스크립트로 독립 실행
        ps_script = f'''
$env:OLLAMA_HOST = "127.0.0.1:{port}"
Start-Process -FilePath "{OLLAMA_EXE}" -ArgumentList "serve" -WindowStyle Hidden -PassThru
'''

        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=10
        )

        time.sleep(8)  # 초기화 대기 (증가)

        # 포트 확인
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        port_open = sock.connect_ex(('127.0.0.1', port)) == 0
        sock.close()

        if port_open:
            colored_print(f"Ollama 포트 {port} 시작 완료", "green")
            return True  # 프로세스 객체 대신 True 반환
        else:
            colored_print(f"Ollama 포트 {port} 시작 실패 (포트 미개방)", "red")
            return None

    except Exception as e:
        colored_print(f"Ollama 포트 {port} 시작 오류: {e}", "red")
        return None

def get_port_by_pid(pid):
    """PID로 사용 중인 포트 찾기"""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.pid == pid and conn.status == 'LISTEN':
                return conn.laddr.port
    except:
        pass
    return None

def get_ollama_processes():
    """실행 중인 Ollama 프로세스 목록 (상세 정보 포함)"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
        try:
            if proc.info['name'] and 'ollama.exe' in proc.info['name'].lower():
                pid = proc.info['pid']
                memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                port = get_port_by_pid(pid)
                processes.append({
                    'pid': pid,
                    'port': port,
                    'memory_mb': memory_mb,
                    'proc': proc
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes

def guardian_cleanup_rogue_ollama():
    """⭐ 불필요한 Ollama 프로세스 자동 정리 (실시간)"""
    procs = get_ollama_processes()
    if not procs:
        return

    killed = []
    for p in procs:
        pid = p['pid']
        port = p['port']
        memory_mb = p['memory_mb']

        # 1. app.exe는 항상 유지
        try:
            if 'app.exe' in str(p['proc'].name()):
                continue
        except:
            pass

        # 2. 포트 없는 프로세스 중 메모리 1GB 이상
        if port is None and memory_mb > 1024:
            try:
                p['proc'].kill()
                killed.append(f"PID {pid} (포트없음, {memory_mb:.0f}MB)")
                colored_print(f"[GUARDIAN] 정리: PID {pid} (포트없음, 메모리 {memory_mb:.0f}MB)", "red")
            except:
                pass
            continue

        # 3. 허가되지 않은 포트
        if port and port not in ALLOWED_PORTS:
            try:
                p['proc'].kill()
                killed.append(f"PID {pid} (포트 {port}, {memory_mb:.0f}MB)")
                colored_print(f"[GUARDIAN] 정리: PID {pid} (미허가 포트 {port}, {memory_mb:.0f}MB)", "red")
            except:
                pass
            continue

        # 4. 메모리 폭주 (8GB 초과)
        if memory_mb > 8 * 1024:
            try:
                p['proc'].kill()
                killed.append(f"PID {pid} (포트 {port}, 메모리폭주 {memory_mb:.0f}MB)")
                colored_print(f"[GUARDIAN] 정리: PID {pid} (메모리폭주 {memory_mb:.0f}MB)", "red")
            except:
                pass

    if killed:
        telegram.notify_system_error(f"불필요한 Ollama 정리: {', '.join(killed)}")
        time.sleep(2)  # 정리 후 대기

def ask_llm_for_analysis(prompt: str, use_ensemble: bool = True) -> str:
    """⭐ LLM에게 분석 요청 (11436 포트) - 16b + 7b 듀얼 앙상블"""
    try:
        # 1차: 16b 메인 분석
        response_16b = requests.post(
            f"{OLLAMA_IMPROVEMENT_HOST}/api/generate",
            json={
                "model": OLLAMA_IMPROVEMENT_MODEL_PRIMARY,
                "prompt": prompt,
                "stream": False
            },
            timeout=OLLAMA_IMPROVEMENT_TIMEOUT
        )

        if response_16b.status_code != 200:
            colored_print(f"[LLM 16b] 응답 오류: {response_16b.status_code}", "yellow")
            return ""

        result_16b = response_16b.json().get('response', '')

        # 2차: 7b 검증 (앙상블 사용 시)
        if use_ensemble and result_16b:
            verification_prompt = f"""다음은 16b 모델의 트레이딩 분석 결과입니다:

{result_16b}

이 분석이 타당한지 검증하고, 추가로 고려해야 할 중요한 사항이 있다면 1-2문장으로 간결하게 추가하세요."""

            response_7b = requests.post(
                f"{OLLAMA_IMPROVEMENT_HOST}/api/generate",
                json={
                    "model": OLLAMA_IMPROVEMENT_MODEL_SECONDARY,
                    "prompt": verification_prompt,
                    "stream": False
                },
                timeout=30  # 7b는 빠르므로 30초
            )

            if response_7b.status_code == 200:
                result_7b = response_7b.json().get('response', '')
                if result_7b and len(result_7b) > 10:
                    colored_print(f"[LLM 7b 검증] {result_7b[:100]}...", "cyan")
                    # 7b의 추가 인사이트가 있으면 병합
                    return f"{result_16b}\n\n[7b 검증] {result_7b}"

        return result_16b

    except requests.Timeout:
        colored_print(f"[LLM] 타임아웃 (60초 초과)", "yellow")
        return ""
    except Exception as e:
        colored_print(f"[LLM] 오류: {e}", "yellow")
        return ""

def llm_analyze_trades_for_improvement(trader_name, trades, performance):
    """⭐ LLM이 거래 패턴 분석 및 개선안 제시"""
    import json

    if len(trades) < 5:
        return []

    # 최근 20건만 분석
    recent_trades = trades[-20:]

    # 거래 요약
    trades_summary = []
    for t in recent_trades:
        summary = f"- {t.get('action', '?')}: {t.get('profit_pct', 0):+.2f}%, 보유 {t.get('hold_minutes', 0):.0f}분, 트렌드 {t.get('trend', '?')}"
        trades_summary.append(summary)

    trades_text = "\n".join(trades_summary)

    # LLM 프롬프트
    prompt = f"""당신은 트레이딩 전문가입니다. {trader_name} 봇의 거래 데이터를 분석하고 개선 방안을 제시하세요.

## 전체 성과
- 총 거래: {performance['total_trades']}건
- 승률: {performance['win_rate']}%
- 총 수익률: {performance['total_return']}%

## 최근 20건 거래
{trades_text}

## 분석 요청
1. 가장 큰 문제점 1-2개만 간결하게
2. 각 문제에 대한 구체적 개선안

답변은 2-3문장으로 작성하세요."""

    llm_response = ask_llm_for_analysis(prompt)

    if not llm_response:
        return []

    colored_print(f"[{trader_name}] [LLM 인사이트] {llm_response[:150]}...", "magenta")

    # 간단한 키워드 기반 개선안 추출
    improvements = []

    if "횡보" in llm_response or "neutral" in llm_response.lower():
        improvements.append({'type': 'sideways_block', 'source': 'LLM'})

    if ("손절" in llm_response or "stop" in llm_response.lower()) and ("늦" in llm_response or "tight" in llm_response.lower()):
        improvements.append({'type': 'tighten_stop_loss', 'source': 'LLM'})

    if "보유" in llm_response or "hold" in llm_response.lower():
        improvements.append({'type': 'reduce_hold_time', 'source': 'LLM'})

    return improvements

def check_trading_health(trader_name, history_file):
    """⭐ 거래 현황 및 수익 체크 (1시간마다)"""
    import json
    from datetime import datetime, timedelta

    try:
        # 거래 히스토리 로드
        with open(history_file, 'r', encoding='utf-8') as f:
            trades = json.load(f)

        if not trades:
            return {
                'status': 'no_trades',
                'message': f'{trader_name}: 거래 없음',
                'alert': True
            }

        # 최근 1시간 거래
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_trades = []
        for t in trades:
            try:
                trade_time = datetime.fromisoformat(t.get('timestamp', ''))
                if trade_time >= one_hour_ago:
                    recent_trades.append(t)
            except:
                continue

        # 전체 수익률 계산
        total_return = sum([t.get('profit_pct', 0) for t in trades])
        total_trades = len(trades)
        wins = len([t for t in trades if t.get('profit_pct', 0) > 0])
        win_rate = wins / total_trades * 100 if total_trades > 0 else 0

        # 최근 1시간 거래 분석
        recent_count = len(recent_trades)
        recent_return = sum([t.get('profit_pct', 0) for t in recent_trades]) if recent_trades else 0

        # 경고 조건
        alert = False
        warnings = []

        # 1. 1시간 동안 거래 없음 (ETH는 1분, KIS는 2분 주기라 최소 30건 이상 예상)
        if recent_count == 0:
            warnings.append("1시간 동안 거래 없음")
            alert = True

        # 2. 총 수익률이 음수 (손실 누적)
        if total_return < -5:
            warnings.append(f"누적 손실 {total_return:.1f}%")
            alert = True

        # 3. 승률이 40% 미만
        if win_rate < 40 and total_trades >= 10:
            warnings.append(f"승률 {win_rate:.0f}%")
            alert = True

        message = f"{trader_name}: 거래 {total_trades}건, 수익 {total_return:+.2f}%, 승률 {win_rate:.0f}%, 최근1h {recent_count}건"

        return {
            'status': 'healthy' if not alert else 'warning',
            'total_trades': total_trades,
            'total_return': total_return,
            'win_rate': win_rate,
            'recent_count': recent_count,
            'recent_return': recent_return,
            'message': message,
            'warnings': warnings,
            'alert': alert
        }

    except FileNotFoundError:
        return {
            'status': 'no_file',
            'message': f'{trader_name}: 거래 파일 없음',
            'alert': True
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'{trader_name}: 오류 {e}',
            'alert': False
        }

def apply_strategy_improvements(trader_name, strategy_file, improvements, improvement_history):
    """⭐ 전략 개선안 적용 (자동)"""
    import json

    if not improvements:
        return []

    try:
        # 현재 전략 로드
        try:
            with open(strategy_file, 'r', encoding='utf-8') as f:
                strategy = json.load(f)
        except:
            strategy = {
                'stop_loss_pct': -2.5,
                'max_hold_minutes': 60,
                'min_confidence': 75,
                'trend_check_enabled': True
            }

        applied = []

        for imp in improvements:
            imp_type = imp['type']
            source = imp.get('source', 'STAT')

            if imp_type == 'sideways_block':
                strategy['trend_check_enabled'] = True
                strategy['min_trend_strength'] = 0.3
                applied.append(f"횡보장 차단 활성화 ({source})")
                colored_print(f"[{trader_name}] [개선 적용] 횡보장 차단 (출처: {source})", "green")

            elif imp_type == 'tighten_stop_loss':
                old_sl = strategy.get('stop_loss_pct', -2.5)
                new_sl = min(-1.5, old_sl + 0.3)
                strategy['stop_loss_pct'] = new_sl
                applied.append(f"손절 {old_sl}% → {new_sl:.1f}% ({source})")
                colored_print(f"[{trader_name}] [개선 적용] 손절 {old_sl}% → {new_sl:.1f}% (출처: {source})", "green")

            elif imp_type == 'reduce_hold_time':
                old_hold = strategy.get('max_hold_minutes', 60)
                new_hold = max(20, old_hold - 10)
                strategy['max_hold_minutes'] = new_hold
                applied.append(f"보유시간 {old_hold}분 → {new_hold}분 ({source})")
                colored_print(f"[{trader_name}] [개선 적용] 보유시간 {old_hold}분 → {new_hold}분 (출처: {source})", "green")

        if applied:
            # 전략 저장
            with open(strategy_file, 'w', encoding='utf-8') as f:
                json.dump(strategy, f, indent=2, ensure_ascii=False)

            # 개선 히스토리 기록
            from datetime import datetime
            improvement_history.append({
                'timestamp': datetime.now().isoformat(),
                'trader': trader_name,
                'applied': applied
            })

            colored_print(f"[{trader_name}] ✅ {len(applied)}개 개선사항 적용 완료", "green")

        return applied

    except Exception as e:
        colored_print(f"[{trader_name}] 전략 적용 실패: {e}", "red")
        return []

# ===== 로그 파서 =====
def parse_trader_log(line, trader_name):
    """트레이더 로그에서 중요 정보 추출 + 텔레그램 알림"""
    line = line.strip()
    if not line:
        return None

    # ⭐ 모든 로그 출력 (디버깅 모드)
    # 단, 너무 많은 로그 방지를 위해 일부만 필터링
    skip_patterns = [
        r'^=+$',  # === 라인만
    ]

    for skip in skip_patterns:
        if re.match(skip, line):
            return None

    # 텔레그램 알림 (중요 이벤트만)
    if any(keyword in line for keyword in ['TREND_CHANGE', '청산 완료', 'PYRAMID', '진입 완료']):
        telegram.notify_position_change(trader_name, "포지션 변경", line)

    return line  # 모든 로그 반환!

def log_reader_thread(process, trader_name):
    """트레이더 로그 읽기 스레드"""
    try:
        for line in iter(process.stdout.readline, ''):
            if not line:
                break

            # UTF-8 디코딩
            try:
                decoded_line = line.decode('utf-8', errors='ignore')
            except:
                decoded_line = str(line)

            # 중요 정보 필터링
            important_info = parse_trader_log(decoded_line, trader_name)
            if important_info:
                colored_print(f"[{trader_name}] {important_info}", "magenta")
    except Exception as e:
        colored_print(f"[{trader_name}] 로그 읽기 오류: {e}", "red")

# ===== 트레이더 관리 =====
def start_trader(script_path, python_exe, working_dir, trader_name, ollama_port):
    """트레이더 시작 (로그 캡처)"""
    try:
        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"127.0.0.1:{ollama_port}"  # http:// 제거 (트레이더 내부에서 추가)
        env["PYTHONIOENCODING"] = "utf-8"

        process = subprocess.Popen(
            [python_exe, "-u", script_path],  # -u: unbuffered output
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,  # unbuffered
            universal_newlines=False  # 바이트 모드
        )

        # 로그 읽기 스레드 시작
        log_thread = threading.Thread(
            target=log_reader_thread,
            args=(process, trader_name),
            daemon=True
        )
        log_thread.start()

        time.sleep(2)

        if process.poll() is None:
            colored_print(f"{trader_name} 시작 완료 (PID: {process.pid}, Ollama: {ollama_port})", "green")
            return process
        else:
            colored_print(f"{trader_name} 시작 실패", "red")
            return None

    except Exception as e:
        colored_print(f"{trader_name} 시작 오류: {e}", "red")
        return None

def stop_process(process, name, timeout=30):
    """프로세스 정상 종료"""
    try:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=timeout)
                colored_print(f"{name} 정상 종료", "yellow")
            except subprocess.TimeoutExpired:
                process.kill()
                colored_print(f"{name} 강제 종료", "yellow")
        return True
    except Exception as e:
        colored_print(f"{name} 종료 실패: {e}", "red")
        return False

# ===== 메인 관리 루프 =====
def main():
    colored_print("=" * 70, "cyan")
    colored_print("통합 트레이더 관리 시스템 시작", "cyan")
    colored_print(f"재시작 주기: {RESTART_INTERVAL // 3600}시간", "cyan")
    colored_print("=" * 70, "cyan")

    # 텔레그램 시작 알림
    telegram.notify_system_start()

    # 초기 정리
    colored_print("\n[초기화] 기존 Ollama 프로세스 정리 중...", "yellow")
    kill_all_ollama()
    time.sleep(3)

    colored_print("\n[OLLAMA] 독립 인스턴스 3개 시작 중...", "blue")

    # ETH Ollama (11434)
    colored_print(f"[OLLAMA] 포트 {OLLAMA_PORT_ETH} 시작 중 (ETH Trader용)...", "blue")
    ollama_eth = start_ollama(OLLAMA_PORT_ETH)
    if not ollama_eth:
        colored_print(f"\n[ERROR] Ollama 포트 {OLLAMA_PORT_ETH} 시작 실패!", "red")
        return

    # KIS Ollama (11435)
    colored_print(f"[OLLAMA] 포트 {OLLAMA_PORT_KIS} 시작 중 (KIS Trader용)...", "blue")
    ollama_kis = start_ollama(OLLAMA_PORT_KIS)
    if not ollama_kis:
        colored_print(f"\n[ERROR] Ollama 포트 {OLLAMA_PORT_KIS} 시작 실패!", "red")
        kill_all_ollama()
        return

    # ⭐ Self-Improvement Ollama (11436)
    colored_print(f"[OLLAMA] 포트 {OLLAMA_PORT_IMPROVEMENT} 시작 중 (자기개선 엔진용)...", "blue")
    ollama_improvement = start_ollama(OLLAMA_PORT_IMPROVEMENT)
    if not ollama_improvement:
        colored_print(f"\n[WARNING] Ollama 포트 {OLLAMA_PORT_IMPROVEMENT} 시작 실패 (자기개선 엔진 비활성화)", "yellow")
        # 자기개선은 선택사항이므로 실패해도 계속 진행
    else:
        colored_print(f"[OLLAMA] 자기개선 엔진용 Ollama 활성화 완료!", "green")

    colored_print("[OLLAMA] 모든 인스턴스 시작 완료!", "green")

    # 트레이더 시작
    colored_print("\n[TRADER] 시작 중...", "blue")
    trader_eth = start_trader(
        ETH_TRADER_SCRIPT,
        ETH_PYTHON,
        ETH_TRADER_DIR,
        "ETH Trader (코드3)",
        OLLAMA_PORT_ETH
    )
    time.sleep(3)

    trader_kis = start_trader(
        KIS_TRADER_SCRIPT,
        KIS_PYTHON,
        KIS_TRADER_DIR,
        "KIS Trader (코드4)",
        OLLAMA_PORT_KIS
    )

    if not trader_eth or not trader_kis:
        colored_print("\n[WARNING] 일부 트레이더 시작 실패", "yellow")

    # 재시작 타이머
    last_restart_time = time.time()
    last_guardian_check = time.time()
    last_status_print = time.time()
    last_trading_check = time.time()  # ⭐ 거래 현황 체크
    last_improvement_check = time.time()  # ⭐ 자기개선 체크
    last_improvement_report = time.time()  # ⭐ 개선 리포트

    colored_print("\n[MONITOR] 모니터링 시작 (Ctrl+C로 종료)\n", "green")
    colored_print(f"[GUARDIAN] 실시간 Ollama 관리 활성화 ({GUARDIAN_CHECK_INTERVAL}초마다)\n", "green")
    colored_print(f"[TRADING] 거래/수익 모니터링 활성화 (1시간마다)\n", "green")
    colored_print(f"[SELF-IMPROVE] 자기개선 엔진 활성화 (1시간마다 LLM 분석, 6시간마다 리포트)\n", "green")

    try:
        while True:
            time.sleep(GUARDIAN_CHECK_INTERVAL)  # ⭐ 10초마다 체크
            current_time = time.time()
            elapsed = current_time - last_restart_time

            # ⭐ Guardian: 불필요한 Ollama 정리 (10초마다)
            guardian_cleanup_rogue_ollama()

            # ⭐ 거래 현황 및 수익 체크 (1시간마다)
            if (current_time - last_trading_check) >= TRADING_CHECK_INTERVAL:
                colored_print("\n" + "="*70, "cyan")
                colored_print("[거래 현황 체크] 시작", "cyan")
                colored_print("="*70, "cyan")

                eth_health = check_trading_health("ETH", ETH_TRADE_HISTORY)
                kis_health = check_trading_health("KIS", KIS_TRADE_HISTORY)

                # ETH 상태
                if eth_health['alert']:
                    colored_print(f"⚠️  [ETH] {eth_health['message']}", "red")
                    if eth_health.get('warnings'):
                        for w in eth_health['warnings']:
                            colored_print(f"    - {w}", "yellow")
                    telegram.notify_system_error(f"ETH 거래 경고: {', '.join(eth_health.get('warnings', []))}")
                else:
                    colored_print(f"✅ [ETH] {eth_health['message']}", "green")

                # KIS 상태
                if kis_health['alert']:
                    colored_print(f"⚠️  [KIS] {kis_health['message']}", "red")
                    if kis_health.get('warnings'):
                        for w in kis_health['warnings']:
                            colored_print(f"    - {w}", "yellow")
                    telegram.notify_system_error(f"KIS 거래 경고: {', '.join(kis_health.get('warnings', []))}")
                else:
                    colored_print(f"✅ [KIS] {kis_health['message']}", "green")

                # 종합 리포트 텔레그램 전송
                report = f"📊 <b>거래 현황 리포트</b>\n\n"
                report += f"<b>ETH:</b> {eth_health['message']}\n"
                report += f"<b>KIS:</b> {kis_health['message']}\n\n"

                if eth_health['alert'] or kis_health['alert']:
                    report += "⚠️ 문제 감지 - 자기개선 엔진이 분석 중입니다"
                else:
                    report += "✅ 모든 봇 정상 작동 중"

                telegram.send_message(report)

                colored_print("="*70 + "\n", "cyan")
                last_trading_check = current_time

            # ⭐ 자기개선 엔진 (1시간마다 LLM 분석)
            if (current_time - last_improvement_check) >= SELF_IMPROVEMENT_INTERVAL:
                import json
                import statistics

                colored_print("\n" + "="*70, "magenta")
                colored_print("[자기개선 엔진] LLM 분석 시작", "magenta")
                colored_print("="*70, "magenta")

                # ETH 분석 및 개선
                try:
                    with open(ETH_TRADE_HISTORY, 'r', encoding='utf-8') as f:
                        eth_trades = json.load(f)

                    if len(eth_trades) >= 10:
                        # 성과 계산
                        eth_perf = {
                            'total_trades': len(eth_trades),
                            'win_rate': len([t for t in eth_trades if t.get('profit_pct', 0) > 0]) / len(eth_trades) * 100,
                            'total_return': sum([t.get('profit_pct', 0) for t in eth_trades])
                        }

                        # LLM 분석
                        colored_print("[ETH] LLM 분석 중...", "cyan")
                        eth_improvements = llm_analyze_trades_for_improvement("ETH", eth_trades, eth_perf)

                        # 개선안 적용
                        if eth_improvements:
                            apply_strategy_improvements("ETH", ETH_STRATEGY_FILE, eth_improvements, improvement_history_eth)
                except Exception as e:
                    colored_print(f"[ETH] 자기개선 오류: {e}", "yellow")

                # KIS 분석 및 개선
                try:
                    with open(KIS_TRADE_HISTORY, 'r', encoding='utf-8') as f:
                        kis_trades = json.load(f)

                    if len(kis_trades) >= 10:
                        # 성과 계산
                        kis_perf = {
                            'total_trades': len(kis_trades),
                            'win_rate': len([t for t in kis_trades if t.get('profit_pct', 0) > 0]) / len(kis_trades) * 100,
                            'total_return': sum([t.get('profit_pct', 0) for t in kis_trades])
                        }

                        # LLM 분석
                        colored_print("[KIS] LLM 분석 중...", "cyan")
                        kis_improvements = llm_analyze_trades_for_improvement("KIS", kis_trades, kis_perf)

                        # 개선안 적용
                        if kis_improvements:
                            apply_strategy_improvements("KIS", KIS_STRATEGY_FILE, kis_improvements, improvement_history_kis)
                except Exception as e:
                    colored_print(f"[KIS] 자기개선 오류: {e}", "yellow")

                # 개선 리포트 (6시간마다)
                if (current_time - last_improvement_report) >= IMPROVEMENT_REPORT_INTERVAL:
                    total_improvements = len(improvement_history_eth) + len(improvement_history_kis)
                    if total_improvements > 0:
                        report = f"🧠 <b>자기개선 리포트</b>\n\n"
                        report += f"총 개선 횟수: {total_improvements}회\n"
                        report += f"ETH: {len(improvement_history_eth)}회\n"
                        report += f"KIS: {len(improvement_history_kis)}회\n\n"
                        report += "최근 적용된 개선사항은 전략 파일에 자동 반영되었습니다."
                        telegram.send_message(report)

                    last_improvement_report = current_time

                colored_print("="*70 + "\n", "magenta")
                last_improvement_check = current_time

            # 상태 체크 (1분마다만)
            should_check_status = (current_time - last_status_print) >= 60

            if not should_check_status:
                continue

            last_status_print = current_time

            # 트레이더 상태 체크
            eth_alive = trader_eth and trader_eth.poll() is None
            kis_alive = trader_kis and trader_kis.poll() is None

            # Ollama 헬스 체크 (지능적 관리)
            health_eth = check_ollama_health(OLLAMA_PORT_ETH)
            health_kis = check_ollama_health(OLLAMA_PORT_KIS)

            # 응답 시간 기록
            if health_eth.get("response_time"):
                response_times_eth.append(health_eth["response_time"])
            if health_kis.get("response_time"):
                response_times_kis.append(health_kis["response_time"])

            # Ollama 재시작 판단 (공유 체크)
            need_restart_ollama, reason = should_restart_ollama(health_eth, response_times_eth)

            if need_restart_ollama:
                colored_print(f"\n[SMART_RESTART] Ollama 재시작 필요: {reason}", "red")

                # 두 트레이더 모두 종료
                colored_print("[SMART_RESTART] 트레이더 종료 중...", "yellow")
                stop_process(trader_eth, "ETH Trader", timeout=10)
                stop_process(trader_kis, "KIS Trader", timeout=10)

                # Ollama 모두 재시작
                colored_print("[SMART_RESTART] Ollama 재시작 중...", "yellow")
                kill_all_ollama()
                time.sleep(3)

                ollama_eth = start_ollama(OLLAMA_PORT_ETH)
                ollama_kis = start_ollama(OLLAMA_PORT_KIS)
                ollama_improvement = start_ollama(OLLAMA_PORT_IMPROVEMENT)

                if not ollama_eth or not ollama_kis:
                    colored_print("[ERROR] Ollama 재시작 실패!", "red")
                    break

                # 트레이더 재시작
                colored_print("[SMART_RESTART] 트레이더 재시작 중...", "green")
                trader_eth = start_trader(
                    ETH_TRADER_SCRIPT,
                    ETH_PYTHON,
                    ETH_TRADER_DIR,
                    "ETH Trader (코드3)",
                    OLLAMA_PORT_ETH
                )
                trader_kis = start_trader(
                    KIS_TRADER_SCRIPT,
                    KIS_PYTHON,
                    KIS_TRADER_DIR,
                    "KIS Trader (코드4)",
                    OLLAMA_PORT_KIS
                )

                response_times_eth.clear()
                response_times_kis.clear()

            # 프로세스 복구 (크래시 시)
            if not eth_alive and not need_restart_ollama:
                colored_print("\n[AUTO_RECOVERY] ETH Trader 크래시 → 재시작...", "yellow")
                trader_eth = start_trader(
                    ETH_TRADER_SCRIPT,
                    ETH_PYTHON,
                    ETH_TRADER_DIR,
                    "ETH Trader (코드3)",
                    OLLAMA_PORT_ETH
                )

            if not kis_alive and not need_restart_ollama:
                colored_print("\n[AUTO_RECOVERY] KIS Trader 크래시 → 재시작...", "yellow")
                trader_kis = start_trader(
                    KIS_TRADER_SCRIPT,
                    KIS_PYTHON,
                    KIS_TRADER_DIR,
                    "KIS Trader (코드4)",
                    OLLAMA_PORT_KIS
                )

            # 주기적 재시작 (4시간)
            if elapsed >= RESTART_INTERVAL:
                colored_print("\n" + "=" * 70, "magenta")
                colored_print(f"{RESTART_INTERVAL // 3600}시간 경과 → 전체 재시작", "magenta")
                colored_print("=" * 70, "magenta")

                # 1. 트레이더 종료
                colored_print("\n[RESTART 1/3] 트레이더 종료 중...", "yellow")
                stop_process(trader_eth, "ETH Trader")
                stop_process(trader_kis, "KIS Trader")
                time.sleep(3)

                # 2. Ollama 재시작
                colored_print("[RESTART 2/3] Ollama 재시작 중...", "yellow")
                kill_all_ollama()
                time.sleep(3)

                ollama_eth = start_ollama(OLLAMA_PORT_ETH)
                ollama_kis = start_ollama(OLLAMA_PORT_KIS)
                ollama_improvement = start_ollama(OLLAMA_PORT_IMPROVEMENT)

                # 3. 트레이더 재시작
                colored_print("[RESTART 3/3] 트레이더 재시작 중...", "green")
                trader_eth = start_trader(
                    ETH_TRADER_SCRIPT,
                    ETH_PYTHON,
                    ETH_TRADER_DIR,
                    "ETH Trader (코드3)",
                    OLLAMA_PORT_ETH
                )
                time.sleep(3)

                trader_kis = start_trader(
                    KIS_TRADER_SCRIPT,
                    KIS_PYTHON,
                    KIS_TRADER_DIR,
                    "KIS Trader (코드4)",
                    OLLAMA_PORT_KIS
                )

                last_restart_time = current_time
                colored_print(f"\n[RESTART] 완료! 다음 재시작: {RESTART_INTERVAL // 3600}시간 후", "green")
                colored_print("=" * 70 + "\n", "magenta")

            # 상태 출력 (1분마다)
            colored_print(
                f"[STATUS] ETH: {'OK' if eth_alive else 'DEAD'} "
                f"(Ollama: {health_eth.get('status', 'unknown')}, "
                f"응답: {health_eth.get('response_time', 0):.1f}s, "
                f"메모리: {health_eth.get('memory_mb', 0):.0f}MB) | "
                f"KIS: {'OK' if kis_alive else 'DEAD'} "
                f"(Ollama: {health_kis.get('status', 'unknown')}, "
                f"응답: {health_kis.get('response_time', 0):.1f}s, "
                f"메모리: {health_kis.get('memory_mb', 0):.0f}MB) | "
                f"다음 재시작: {(RESTART_INTERVAL - elapsed) / 3600:.1f}시간 후",
                "cyan"
            )

    except KeyboardInterrupt:
        colored_print("\n\n[SHUTDOWN] 사용자 종료 요청", "yellow")
        colored_print("[SHUTDOWN] 모든 프로세스 종료 중...", "yellow")

        stop_process(trader_eth, "ETH Trader")
        stop_process(trader_kis, "KIS Trader")

        time.sleep(2)
        kill_all_ollama()

        colored_print("[SHUTDOWN] 완료", "green")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        colored_print(f"\n[CRITICAL ERROR] {e}", "red")
        colored_print("[CRITICAL ERROR] 프로세스 정리 중...", "red")
        kill_all_ollama()
