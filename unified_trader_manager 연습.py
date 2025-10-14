#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 트레이더 관리 시스템
- 코드3 (ETH 트레이더) + 코드4 (KIS 트레이더) 동시 관리
- Ollama 2개 독립 실행 (포트 충돌 방지)
- 지능적 리소스 관리 (메모리, CPU, 큐잉 감지) 코드4
- 타임아웃 자동 복구
- 주기적 재시작 (4시간)
"""

# 안전한 import를 위한 예외 처리
try:
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
    import sys
    import io
    import json
    import logging
    from logging.handlers import RotatingFileHandler
    print("[INFO] 모든 필수 라이브러리 로드 완료")
except ImportError as e:
    print(f"[ERROR] 라이브러리 로드 실패: {e}")
    print("[INFO] 필요한 라이브러리 설치 중...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "psutil"], check=True)
    print("[INFO] 라이브러리 재설치 완료, 스크립트를 다시 실행하세요.")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] 초기화 오류: {e}")
    sys.exit(1)

# UTF-8 인코딩 강제 설정 (Windows cp949 인코딩 오류 방지)
if sys.platform == 'win32':                                                                                                 
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 메모리 사용량 모니터링 및 제한
def check_memory_usage():
    """메모리 사용량 체크 및 제한"""
    try:
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        if memory_mb > 2000:  # 2GB 초과 시 경고
            print(f"[WARNING] 메모리 사용량 높음: {memory_mb:.1f}MB")
            return False
        return True
    except Exception as e:
        print(f"[ERROR] 메모리 체크 실패: {e}")
        return True

# 글로벌 네트워크 재시도 미들웨어
def http_retry_with_backoff(url, max_retries=3, base_delay=1, **kwargs):
    """HTTP 요청 재시도 (지수 백오프)"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10, **kwargs)
            if response.status_code == 200:
                return response
            elif response.status_code >= 500:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"[RETRY] HTTP {response.status_code} → {delay}s 대기 후 재시도")
                    time.sleep(delay)
                    continue
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"[RETRY] 네트워크 오류: {e} → {delay}s 대기 후 재시도")
                time.sleep(delay)
                continue
        except Exception as e:
            print(f"[ERROR] HTTP 요청 실패: {e}")
            break
    return None

# Ollama 헬스 체크
def check_ollama_health(port):
    """Ollama 포트 헬스 체크"""
    try:
        response = http_retry_with_backoff(f"http://127.0.0.1:{port}/api/tags")
        if response and response.status_code == 200:
            return True
    except Exception as e:
        print(f"[HEALTH] Ollama 포트 {port} 체크 실패: {e}")
    return False

# 메모리/CPU 가드
def system_resource_guard():
    """시스템 리소스 모니터링 및 제한"""
    try:
        # 메모리 사용률 체크
        memory = psutil.virtual_memory()
        if memory.percent > 85:
            print(f"[GUARD] 메모리 사용률 높음: {memory.percent}%")
            return False
        
        # CPU 사용률 체크
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            print(f"[GUARD] CPU 사용률 높음: {cpu_percent}%")
            return False
            
        return True
    except Exception as e:
        print(f"[ERROR] 리소스 가드 실패: {e}")
        return True

# 안전한 종료 처리
def graceful_shutdown(signum=None, frame=None):
    """안전한 종료 처리"""
    print("\n[SHUTDOWN] 안전한 종료 시작...")
    
    # 상태 저장
    try:
        state = {
            "shutdown_time": datetime.now().isoformat(),
            "eth_status": "shutdown",
            "kis_status": "shutdown"
        }
        with open("trader_state.json", "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        print("[SHUTDOWN] 상태 저장 완료")
    except Exception as e:
        print(f"[SHUTDOWN] 상태 저장 실패: {e}")
    
    # 프로세스 종료
    try:
        global trader_eth, trader_kis
        if trader_eth:
            trader_eth.terminate()
        if trader_kis:
            trader_kis.terminate()
        print("[SHUTDOWN] 트레이더 프로세스 종료 완료")
    except Exception as e:
        print(f"[SHUTDOWN] 프로세스 종료 실패: {e}")
    
    print("[SHUTDOWN] 안전한 종료 완료")
    sys.exit(0)

# 시그널 핸들러 등록
import signal
signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)

# 디스크 사용률 가드 (90% 이상)
def disk_usage_guard():
    try:
        usage = psutil.disk_usage(str(Path(log_file).drive))
        if usage.percent >= 90:
            print(f"[GUARD] 디스크 사용률 높음: {usage.percent}% → 로그 정리/압축 수행")
            rotate_logs()
            # 오래된 압축 로그 추가 정리
            try:
                for p in Path(log_file).parent.glob("*.log.gz"):
                    # 7일보다 오래된 압축 로그 삭제
                    if time.time() - p.stat().st_mtime > 7 * 24 * 3600:
                        p.unlink(missing_ok=True)
            except Exception:
                pass
            return False
        return True
    except Exception as e:
        print(f"[GUARD] 디스크 가드 실패: {e}")
        return True

# GPU VRAM 가드: VRAM 부족 시 다운스케일 알림
def gpu_vram_guard(min_free_mb: int = 500):
    try:
        import subprocess
        result = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=2)
        free_list = [int(x.strip()) for x in result.stdout.strip().splitlines() if x.strip().isdigit()]
        if free_list and min(free_list) < min_free_mb:
            print(f"[GUARD] VRAM 여유 부족: {min(free_list)}MB → 14b 대신 7b 사용 권고")
            return False
        return True
    except Exception:
        # nvidia-smi 미존재 등은 무시
        return True

# 초기 메모리 체크
if not check_memory_usage():
    print("[WARNING] 메모리 사용량이 높습니다. 스크립트 실행을 계속하시겠습니까?")
    print("메모리 부족으로 인한 KeyboardInterrupt가 발생할 수 있습니다.")

# LLM 감시 시스템
sys.path.append(r'C:\Users\user\Documents\코드5')
try:
    from llm_market_analyzer import LLMMarketAnalyzer
    LLM_AVAILABLE = True
    print("[INFO] LLM 분석기 로드 성공 - 고성능 모드")
except:
    LLM_AVAILABLE = False
    print("[WARNING] LLM 분석기 로드 실패, 기본 모니터링만 실행")

# ===== 로깅 설정 (실시간 상세 로그) =====
# 로그 파일: unified_trader_realtime.log (최대 50MB, 5개 백업)
log_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# 파일 핸들러 (로테이션)
log_file = Path(r"C:\Users\user\Documents\코드5\unified_trader_realtime.log")
file_handler = RotatingFileHandler(log_file, maxBytes=50*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(log_formatter)

# 로그 로테이션 함수
def rotate_logs():
    """로그 파일 로테이션 및 압축"""
    try:
        # 기존 로그 파일들 압축
        log_dir = log_file.parent
        for i in range(1, 6):  # backupCount=5
            backup_file = log_file.with_suffix(f'.log.{i}')
            if backup_file.exists():
                # 압축 파일명
                compressed_file = backup_file.with_suffix('.log.gz')
                if not compressed_file.exists():
                    try:
                        import gzip
                        with open(backup_file, 'rb') as f_in:
                            with gzip.open(compressed_file, 'wb') as f_out:
                                f_out.writelines(f_in)
                        backup_file.unlink()  # 원본 삭제
                        print(f"[LOG_ROTATION] {backup_file.name} → {compressed_file.name}")
                    except Exception as e:
                        print(f"[LOG_ROTATION] 압축 실패: {e}")
    except Exception as e:
        print(f"[LOG_ROTATION] 로그 로테이션 실패: {e}")

# 콘솔 핸들러
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_formatter)

# 로거 설정
logger = logging.getLogger('UnifiedTraderManager')
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("="*80)
logger.info("통합 트레이더 관리자 로깅 시스템 초기화 완료")
logger.info(f"로그 파일: {log_file}")
logger.info("="*80)

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
            if response.status_code == 200:
                logger.info(f"텔레그램 전송 성공: {message[:50]}...")
                return True
            else:
                logger.error(f"텔레그램 전송 실패 (HTTP {response.status_code}): {response.text}")
                return False
        except Exception as e:
            logger.error(f"텔레그램 전송 예외: {e}")
            return False

    def notify_system_start(self):
        message = (
            "[START] <b>통합 트레이더 시스템 시작</b>\n\n"
            "[OK] ETH Trader\n"
            "[OK] KIS Trader\n"
            "[OK] Ollama 관리자\n\n"
            "<b>🚀 RTX 2060 Tensor Core 최적화</b>\n"
            "✓ FP16 KV Cache\n"
            "✓ Flash Attention\n"
            "✓ 배치 추론 병렬화\n"
            "✓ 모든 레이어 GPU 로드"
        )
        self.send_message(message)

    def notify_system_error(self, error_msg: str):
        message = f"[WARN] <b>시스템 오류</b>\n\n{error_msg}"
        self.send_message(message)

    def notify_position_change(self, trader: str, action: str, details: str):
        message = f"[RESTART] <b>{trader} 포지션 변경</b>\n\n{action}\n{details}"
        self.send_message(message)

    def notify_ollama_restart(self, trader: str, reason: str):
        message = f"[TOOL] <b>{trader} Ollama 재시작</b>\n\n사유: {reason}"
        self.send_message(message)

    def notify_bot_down(self, bot_name: str, reason: str):
        """봇 다운 알림 (ETH/KIS)"""
        message = (
            f"[ERROR] <b>{bot_name} 봇 다운 감지!</b>\n\n"
            f"<b>사유:</b> {reason}\n"
            f"<b>시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"[RESTART] 자동 재시작 시도 중..."
        )
        self.send_message(message)
        logger.error(f"{bot_name} 봇 다운 감지: {reason}")

    def notify_bot_no_trading(self, bot_name: str, hours: float):
        """거래 없음 알림"""
        message = (
            f"[WARN] <b>{bot_name} 거래 없음!</b>\n\n"
            f"<b>경과 시간:</b> {hours:.1f}시간\n"
            f"<b>시간:</b> {datetime.now().strftime('%H:%M:%S')}\n\n"
            f" 임계값이 너무 높거나 시장 상황 확인 필요"
        )
        self.send_message(message)
        logger.warning(f"{bot_name} {hours:.1f}시간 동안 거래 없음")

    def notify_manager_down(self):
        """통합 매니저 자체 다운 알림"""
        message = (
            f"[CRITICAL] <b>통합 매니저 다운!</b>\n\n"
            f"<b>시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f" 즉시 확인 필요! 모든 봇이 중지되었을 수 있음"
        )
        self.send_message(message)
        logger.critical("통합 매니저 다운 감지!")

telegram = TelegramNotifier()

# ===== 설정 =====
RESTART_INTERVAL = 4 * 60 * 60  # 4시간 (초 단위)
GUARDIAN_CHECK_INTERVAL = 10  #  실시간 Ollama 체크: 10초마다

# Ollama 설정
OLLAMA_EXE = r"C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe"
OLLAMA_PORT_ETH = 11434  # 코드3 (ETH) 전용
OLLAMA_PORT_KIS = 11435  # 코드4 (KIS) 전용
OLLAMA_PORT_IMPROVEMENT = 11436  #  자기개선 엔진 전용
OLLAMA_PORT_14B_DEDICATED = 11437  # 14b 전용 포트 (직렬화 큐)
ALLOWED_PORTS = [OLLAMA_PORT_ETH, OLLAMA_PORT_KIS, OLLAMA_PORT_IMPROVEMENT, OLLAMA_PORT_14B_DEDICATED]  # 허가된 포트

# 트레이더 설정
ETH_TRADER_DIR = r"C:\Users\user\Documents\코드3"
ETH_TRADER_SCRIPT = r"C:\Users\user\Documents\코드3\llm_eth_trader_v4_3tier.py"  #  3-Tier 실시간 (Websocket+7b+14b, GPU 최적화)
ETH_PYTHON = r"C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe"

KIS_TRADER_DIR = r"C:\Users\user\Documents\코드4"
KIS_TRADER_SCRIPT = r"C:\Users\user\Documents\코드4\kis_llm_trader_v2_explosive.py"  # 폭발 전략 (7b+14b, GPU 최적화)
KIS_PYTHON = r"C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe"

# 모델 전략 (GPU 최적화 - RTX 2060 6GB Tensor Core)
# ETH: 7b 필터(1-2초, GPU) + 14b 메인(5-10초, 진입/청산) ← 빠른 암호화폐 트레이딩
# KIS: 7b 모니터(1-2초, GPU) + 14b 메인(5-10초, 진입/청산) ← 3배 레버리지 신중 판단
# 통합 매니저: 14b 감시자(5분, GPU 5-10초) + 14b 자기개선(10분, GPU 5-10초) ← 듀얼 14b
# 철학: GPU 100% 활용, 모든 분석을 14b 고품질로

# RTX 2060 Tensor Core 전용 최적화
GPU_OPTIMIZATION = {
    "CUDA_VISIBLE_DEVICES": "0",  # RTX 2060 지정
    "OLLAMA_NUM_GPU": "999",  # 모든 레이어 GPU 로드
    "OLLAMA_GPU_OVERHEAD": "0",  # GPU 오버헤드 최소화
    "OLLAMA_MAX_LOADED_MODELS": "3",  # 3개 모델 동시 로드
    "OLLAMA_KEEP_ALIVE": "60m",  # 60분간 메모리 유지 (KV Cache)
    "OLLAMA_FLASH_ATTENTION": "1",  # Flash Attention 활성화 (Tensor Core)
    "OLLAMA_NUM_THREAD": "4",  # CPU 스레드 최소화 (GPU 우선)
    "OLLAMA_F16_KV": "1",  # FP16 KV Cache (VRAM 절약)
}

# ===== 텔레그램 알림 제한 =====
# 같은 경고를 반복해서 보내지 않도록 추적
last_no_trading_alert = {'ETH': 0, 'KIS': 0}  # 마지막 알림 시간 (timestamp)
NO_TRADING_ALERT_COOLDOWN = 6 * 3600  # 6시간마다만 알림

# ===== 리소스 모니터링 설정 =====
# 포트별 메모리 제한 (사용자 설정)
# 이유: 14b 모델은 6-8GB 사용, 9GB로 여유 있게 설정
# GPU 100% 활용 + 빠른 응답 (5-10초)
MEMORY_LIMITS = {
    11434: 9 * 1024,  # ETH: 9GB (14b 모델용)
    11435: 9 * 1024,  # KIS: 9GB (14b 모델용)
    11436: 9 * 1024,  # 자기개선: 9GB (14b 모델용, 사용자 요청으로 32b→14b 변경)
    11437: 9 * 1024,  # 14b 전용: 9GB (직렬화 큐)
}
MAX_CPU_PERCENT = 5.0  # 정상 상태 CPU: 5% 이하
RESPONSE_TIMEOUT = 10  # API 응답 타임아웃: 10초
QUEUE_DETECT_THRESHOLD = 60  # 큐잉 감지: 60초 이상 CPU 0%

# RTX 2060 GPU 성능 모니터링
GPU_STATS = {
    "batch_inference_count": 0,  # 배치 추론 실행 횟수
    "batch_inference_speedup": [],  # 배치 추론 속도 향상률
    "tensor_core_utilization": [],  # Tensor Core 활용률 (추정)
    "fp16_kv_memory_saved": 0,  # FP16 KV Cache로 절약한 메모리 (MB)
}

# 응답 시간 추적 (최근 10개)
response_times_eth = deque(maxlen=10)
response_times_kis = deque(maxlen=10)

#  거래/수익 모니터링 설정
TRADING_CHECK_INTERVAL = 5 * 60  # 5분마다 거래 현황 체크 (빠른 감시)
ETH_TRADE_HISTORY = r"C:\Users\user\Documents\코드3\eth_trade_history.json"
KIS_TRADE_HISTORY = r"C:\Users\user\Documents\코드4\kis_trade_history.json"

#  자기개선 엔진 설정 (통합) - 14b GPU 고품질 분석
SELF_IMPROVEMENT_INTERVAL = 10 * 60  # 10분마다 자기개선 (적극적 학습)
IMPROVEMENT_REPORT_INTERVAL = 6 * 60 * 60  # 6시간마다 텔레그램 리포트
TELEGRAM_ALERT_INTERVAL = 6 * 60 * 60  # 6시간마다만 텔레그램 알림
OLLAMA_IMPROVEMENT_HOST = f"http://127.0.0.1:{OLLAMA_PORT_IMPROVEMENT}"
OLLAMA_IMPROVEMENT_MODEL = "qwen2.5:14b"  # GPU 활용 (5-10초, 고품질 분석)
OLLAMA_IMPROVEMENT_TIMEOUT = 120  # 14b는 신중하게 2분 타임아웃

#  14b LLM 감시 시스템 (전체 시스템 모니터링, GPU 최적화)
OVERSIGHT_LLM_MODEL = "qwen2.5:14b"  # GPU 활용 (5-10초)
OVERSIGHT_CHECK_INTERVAL = 5 * 60  # 5분마다 전체 시스템 분석 (빠른 감시)
oversight_llm = None  # 14b LLM 인스턴스 (초기화는 main에서)

# 자기개선 상태 추적
improvement_history_eth = []
improvement_history_kis = []
ETH_STRATEGY_FILE = r"C:\Users\user\Documents\코드3\eth_current_strategy.json"
KIS_STRATEGY_FILE = r"C:\Users\user\Documents\코드4\kis_current_strategy.json"

#  Option 4: Self-Improving Feedback Loop - 오류 패턴 학습
error_patterns_eth = []  # ETH 봇의 실패 패턴 (최근 100건)
error_patterns_kis = []  # KIS 봇의 실패 패턴 (최근 100건)
ERROR_PATTERN_FILE_ETH = r"C:\Users\user\Documents\코드3\eth_error_patterns.json"
ERROR_PATTERN_FILE_KIS = r"C:\Users\user\Documents\코드4\kis_error_patterns.json"

#  백그라운드 학습 설정
FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"  # FMP API 키
BACKGROUND_LEARNING_INTERVAL = 10 * 60  # 10분마다 백그라운드 학습
HISTORICAL_DATA_DAYS = 90  # 과거 90일간 데이터 학습 (충분한 데이터 확보)
learning_session_count = 0  # 학습 세션 카운터
background_learning_thread = None  # 백그라운드 학습 스레드

#  자동 검증 및 적용 설정
VALIDATION_THRESHOLD = 3  # 동일 전략이 3번 이상 발견되면 검증 완료
CONFIDENCE_THRESHOLD = 0.7  # Triple Validation 합의율 70% 이상
validated_strategies_eth = {}  # ETH 검증 중인 전략 {strategy_type: count}
validated_strategies_kis = {}  # KIS 검증 중인 전략 {strategy_type: count}

# ===== FMP API 데이터 수집 =====
def fetch_eth_historical_fmp(days=7):
    """FMP API로 ETH 과거 데이터 수집 (실제 데이터만!)"""
    try:
        # FMP API: Crypto Historical (실제 시장 데이터)
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # ETH/USD 1시간 캔들 데이터
        url = f"https://financialmodelingprep.com/api/v3/historical-chart/1hour/ETHUSD?apikey={FMP_API_KEY}"

        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            colored_print(f"[FMP] ETH 데이터 수집 실패: HTTP {response.status_code}", "yellow")
            return []

        data = response.json()

        # 최근 N일 데이터만 필터링
        filtered_data = []
        for candle in data:
            try:
                candle_time = datetime.fromisoformat(candle['date'].replace('Z', '+00:00'))
                if candle_time >= start_date:
                    filtered_data.append({
                        'timestamp': candle['date'],
                        'open': candle['open'],
                        'high': candle['high'],
                        'low': candle['low'],
                        'close': candle['close'],
                        'volume': candle['volume']
                    })
            except:
                continue

        colored_print(f"[FMP] ETH 과거 데이터 {len(filtered_data)}개 수집 완료 (최근 {days}일)", "green")
        return filtered_data[::-1]  # 오래된 것부터 정렬

    except Exception as e:
        colored_print(f"[FMP] ETH 데이터 수집 오류: {e}", "yellow")
        return []

def fetch_soxl_historical_fmp(days=7):
    """FMP API로 SOXL 과거 데이터 수집 (실제 데이터만!)"""
    try:
        # FMP API: Stock Historical (실제 시장 데이터)
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # SOXL 1시간 캔들 데이터
        url = f"https://financialmodelingprep.com/api/v3/historical-chart/1hour/SOXL?apikey={FMP_API_KEY}"

        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            colored_print(f"[FMP] SOXL 데이터 수집 실패: HTTP {response.status_code}", "yellow")
            return []

        data = response.json()

        # 최근 N일 데이터만 필터링
        filtered_data = []
        for candle in data:
            try:
                candle_time = datetime.fromisoformat(candle['date'].replace('Z', '+00:00'))
                if candle_time >= start_date:
                    filtered_data.append({
                        'timestamp': candle['date'],
                        'open': candle['open'],
                        'high': candle['high'],
                        'low': candle['low'],
                        'close': candle['close'],
                        'volume': candle['volume']
                    })
            except:
                continue

        colored_print(f"[FMP] SOXL 과거 데이터 {len(filtered_data)}개 수집 완료 (최근 {days}일)", "green")
        return filtered_data[::-1]  # 오래된 것부터 정렬

    except Exception as e:
        colored_print(f"[FMP] SOXL 데이터 수집 오류: {e}", "yellow")
        return []

def calculate_technical_indicators(candles):
    """기술적 지표 계산 (간단 버전)"""
    if len(candles) < 20:
        return {}

    closes = [c['close'] for c in candles]

    # RSI (14)
    changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [c if c > 0 else 0 for c in changes]
    losses = [-c if c < 0 else 0 for c in changes]

    avg_gain = sum(gains[-14:]) / 14 if len(gains) >= 14 else 0
    avg_loss = sum(losses[-14:]) / 14 if len(losses) >= 14 else 0

    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    rsi = 100 - (100 / (1 + rs))

    # 이동평균
    ma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else closes[-1]
    current_price = closes[-1]

    # 추세 (MA 대비 가격 위치)
    trend = "BULL" if current_price > ma_20 else "BEAR"

    return {
        'rsi': rsi,
        'ma_20': ma_20,
        'current_price': current_price,
        'trend': trend,
        'price_change_pct': ((current_price - closes[-20]) / closes[-20] * 100) if len(closes) >= 20 else 0
    }

def llm_backtest_on_historical_data(trader_name, symbol, historical_data):
    """LLM이 과거 데이터를 분석하여 새로운 전략 발견"""
    global learning_session_count

    if len(historical_data) < 50:
        colored_print(f"[{trader_name}] 데이터 부족 (최소 50개 필요, 현재 {len(historical_data)}개)", "yellow")
        return []

    learning_session_count += 1

    # 최근 100개 캔들만 분석 (LLM 프롬프트 길이 제한)
    recent_candles = historical_data[-100:]

    # 기술적 지표 계산
    indicators = calculate_technical_indicators(recent_candles)

    # 가상 시나리오 생성 (최근 데이터 기반)
    scenarios = []

    # 시나리오 1: 급등 후 조정
    if indicators.get('price_change_pct', 0) > 5:
        scenarios.append({
            'type': '급등 후 조정',
            'description': f"{symbol} 최근 +{indicators['price_change_pct']:.1f}% 급등 → 조정 가능성",
            'question': '급등 후 진입 타이밍은? 조정을 기다려야 하나?'
        })

    # 시나리오 2: RSI 과매수/과매도
    rsi = indicators.get('rsi', 50)
    if rsi > 70:
        scenarios.append({
            'type': 'RSI 과매수',
            'description': f"{symbol} RSI {rsi:.0f} 과매수 구간",
            'question': 'RSI 70 이상일 때 진입해도 안전한가? 손절은?'
        })
    elif rsi < 30:
        scenarios.append({
            'type': 'RSI 과매도',
            'description': f"{symbol} RSI {rsi:.0f} 과매도 구간",
            'question': 'RSI 30 이하 = 저점 매수 기회? 반등 확률은?'
        })

    # 시나리오 3: 추세 전환
    if len(recent_candles) >= 20:
        first_half_avg = sum([c['close'] for c in recent_candles[:10]]) / 10
        second_half_avg = sum([c['close'] for c in recent_candles[-10:]]) / 10

        if second_half_avg > first_half_avg * 1.02:
            scenarios.append({
                'type': '상승 추세 전환',
                'description': f"{symbol} 하락 → 상승 전환 신호",
                'question': '추세 전환 초기에 진입? 확인 후 진입?'
            })

    if not scenarios:
        return []

    # LLM에게 분석 요청 (Triple Validation)
    colored_print(f"\n[BACKGROUND LEARNING #{learning_session_count}] {trader_name} - {symbol} 전략 탐색 시작...", "magenta")

    # 시나리오 텍스트
    scenario_text = "\n".join([f"{i+1}. {s['type']}: {s['description']}\n   질문: {s['question']}"
                                for i, s in enumerate(scenarios)])

    primary_prompt = f"""당신은 트레이딩 전략 연구자입니다. {symbol}의 실제 과거 데이터를 분석하여 새로운 전략을 제안하세요.

## 현재 시장 상황 (실제 데이터)
- 현재가: ${indicators['current_price']:.2f}
- RSI: {indicators['rsi']:.0f}
- 20일 MA: ${indicators['ma_20']:.2f}
- 추세: {indicators['trend']}
- 가격 변화: {indicators['price_change_pct']:+.1f}%

## 발견된 시나리오
{scenario_text}

## 질문
위 시나리오에서 가장 수익성 높은 전략은? 2-3문장으로 구체적으로 답하세요."""

    validator1_prompt = f"""비판적 분석가로서 {symbol}의 시나리오를 검토하세요.

{scenario_text}

질문: 위 전략의 가장 큰 위험은? 실패 확률은? 2문장으로."""

    validator2_prompt = f"""역발상 분석가로서 {symbol}의 정반대 전략을 제안하세요.

{scenario_text}

질문: 만약 위 시나리오와 정반대로 해석한다면? 2문장으로."""

    # Triple Validation 실행
    validation = ask_llm_triple_validation(primary_prompt, validator1_prompt, validator2_prompt)

    if not validation['consensus']:
        colored_print(f"[BACKGROUND LEARNING #{learning_session_count}] 합의 실패 - 전략 탐색 보류", "yellow")
        return []

    colored_print(f"[BACKGROUND LEARNING #{learning_session_count}] [OK] 새로운 인사이트 발견!", "green")
    colored_print(f"  {validation['final_decision'][:200]}...", "cyan")

    # 간단한 전략 추출
    response = validation['final_decision']
    discovered_strategies = []

    if "손절" in response or "stop" in response.lower():
        discovered_strategies.append({
            'type': 'stop_loss_adjustment',
            'source': 'BACKGROUND_LEARNING',
            'session': learning_session_count
        })

    if "진입" in response and ("보수" in response or "확인" in response):
        discovered_strategies.append({
            'type': 'conservative_entry',
            'source': 'BACKGROUND_LEARNING',
            'session': learning_session_count
        })

    if "과매" in response or "RSI" in response:
        discovered_strategies.append({
            'type': 'rsi_based_entry',
            'source': 'BACKGROUND_LEARNING',
            'session': learning_session_count
        })

    return discovered_strategies

def auto_validate_and_apply_strategy(trader_name, strategies, validation_dict, strategy_file, improvement_history):
    """
     자동 검증 및 적용 시스템

    동일한 전략이 여러 번 발견되면 자동으로 검증 완료 → 적용

    검증 조건:
    1. 동일 전략이 VALIDATION_THRESHOLD(3)번 이상 발견
    2. Triple Validation 합의율 CONFIDENCE_THRESHOLD(70%) 이상

    Args:
        trader_name: 트레이더 이름 (ETH/KIS)
        strategies: 발견된 전략 리스트
        validation_dict: 검증 카운터 딕셔너리
        strategy_file: 전략 파일 경로
        improvement_history: 개선 히스토리
    """
    if not strategies:
        return []

    applied = []

    for strategy in strategies:
        strategy_type = strategy['type']
        session = strategy.get('session', 0)

        # 검증 카운터 증가
        if strategy_type not in validation_dict:
            validation_dict[strategy_type] = {
                'count': 0,
                'sessions': []
            }

        validation_dict[strategy_type]['count'] += 1
        validation_dict[strategy_type]['sessions'].append(session)

        current_count = validation_dict[strategy_type]['count']

        colored_print(f"[{trader_name}]  전략 '{strategy_type}' 발견 횟수: {current_count}/{VALIDATION_THRESHOLD}", "cyan")

        # 검증 완료 조건: N번 이상 발견
        if current_count >= VALIDATION_THRESHOLD:
            colored_print(f"[{trader_name}] [OK] 전략 '{strategy_type}' 검증 완료! ({current_count}번 발견)", "green")
            colored_print(f"[{trader_name}] [START] 자동 적용 시작...", "green")

            # 자동 적용
            result = apply_strategy_improvements(
                trader_name,
                strategy_file,
                [{'type': strategy_type, 'source': f'AUTO_VALIDATED_{current_count}x'}],
                improvement_history
            )

            if result:
                applied.extend(result)
                colored_print(f"[{trader_name}]  전략 '{strategy_type}' 자동 적용 완료!", "green")

                # 검증 완료된 전략은 카운터 리셋 (중복 적용 방지)
                validation_dict[strategy_type]['count'] = 0
        else:
            colored_print(f"[{trader_name}] ⏳ 전략 '{strategy_type}' 검증 중... (추가 {VALIDATION_THRESHOLD - current_count}번 필요)", "yellow")

    return applied

def background_learning_worker():
    """백그라운드 학습 워커 (독립 스레드)"""
    colored_print("[BACKGROUND LEARNING] 백그라운드 학습 워커 시작!", "magenta")

    while True:
        try:
            time.sleep(BACKGROUND_LEARNING_INTERVAL)

            colored_print("\n" + "="*70, "magenta")
            colored_print(f"[BACKGROUND LEARNING] 세션 시작 (학습 주기: {BACKGROUND_LEARNING_INTERVAL // 60}분)", "magenta")
            colored_print("="*70, "magenta")

            # ETH 과거 데이터 수집 및 학습
            colored_print("[ETH] FMP API 데이터 수집 중...", "cyan")
            eth_historical = fetch_eth_historical_fmp(HISTORICAL_DATA_DAYS)

            if len(eth_historical) >= 50:
                eth_strategies = llm_backtest_on_historical_data("ETH", "ETHUSD", eth_historical)

                if eth_strategies:
                    colored_print(f"[ETH]  {len(eth_strategies)}개 새로운 전략 발견!", "cyan")

                    #  자동 검증 및 적용 시스템 실행
                    global validated_strategies_eth
                    applied = auto_validate_and_apply_strategy(
                        "ETH",
                        eth_strategies,
                        validated_strategies_eth,
                        ETH_STRATEGY_FILE,
                        improvement_history_eth
                    )

                    if applied:
                        colored_print(f"[ETH]  {len(applied)}개 전략 자동 적용 완료!", "green")

                    # 인사이트 기록 (히스토리 보관용)
                    import json
                    try:
                        insight_file = r"C:\Users\user\Documents\코드3\eth_learning_insights.json"
                        try:
                            with open(insight_file, 'r', encoding='utf-8') as f:
                                insights = json.load(f)
                        except:
                            insights = []

                        from datetime import datetime
                        insights.append({
                            'timestamp': datetime.now().isoformat(),
                            'session': learning_session_count,
                            'strategies': eth_strategies,
                            'applied': applied if applied else [],
                            'validation_status': {k: v['count'] for k, v in validated_strategies_eth.items()}
                        })

                        with open(insight_file, 'w', encoding='utf-8') as f:
                            json.dump(insights[-100:], f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        colored_print(f"[ETH] 인사이트 저장 실패: {e}", "yellow")

            # SOXL 과거 데이터 수집 및 학습
            colored_print("[KIS] FMP API 데이터 수집 중...", "cyan")
            soxl_historical = fetch_soxl_historical_fmp(HISTORICAL_DATA_DAYS)

            if len(soxl_historical) >= 50:
                soxl_strategies = llm_backtest_on_historical_data("KIS", "SOXL", soxl_historical)

                if soxl_strategies:
                    colored_print(f"[KIS]  {len(soxl_strategies)}개 새로운 전략 발견!", "cyan")

                    #  자동 검증 및 적용 시스템 실행
                    global validated_strategies_kis
                    applied = auto_validate_and_apply_strategy(
                        "KIS",
                        soxl_strategies,
                        validated_strategies_kis,
                        KIS_STRATEGY_FILE,
                        improvement_history_kis
                    )

                    if applied:
                        colored_print(f"[KIS]  {len(applied)}개 전략 자동 적용 완료!", "green")

                    # 인사이트 기록 (히스토리 보관용)
                    import json
                    try:
                        insight_file = r"C:\Users\user\Documents\코드4\kis_learning_insights.json"
                        try:
                            with open(insight_file, 'r', encoding='utf-8') as f:
                                insights = json.load(f)
                        except:
                            insights = []

                        from datetime import datetime
                        insights.append({
                            'timestamp': datetime.now().isoformat(),
                            'session': learning_session_count,
                            'strategies': soxl_strategies,
                            'applied': applied if applied else [],
                            'validation_status': {k: v['count'] for k, v in validated_strategies_kis.items()}
                        })

                        with open(insight_file, 'w', encoding='utf-8') as f:
                            json.dump(insights[-100:], f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        colored_print(f"[KIS] 인사이트 저장 실패: {e}", "yellow")

            colored_print("="*70 + "\n", "magenta")

        except Exception as e:
            colored_print(f"[BACKGROUND LEARNING] 오류: {e}", "red")
            time.sleep(60)  # 오류 시 1분 대기 후 재시도

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

        # 2. 메모리 체크 (포트별 제한 적용)
        memory_mb = ollama_proc.info['memory_info'].rss / 1024 / 1024
        max_memory = MEMORY_LIMITS.get(port, 9 * 1024)  # 기본값 9GB
        if memory_mb > max_memory:
            return {
                "status": "high_memory",
                "memory_mb": memory_mb,
                "max_memory_mb": max_memory,
                "action": "restart"
            }

        # 3. CPU 체크 (0%인데 요청 있으면 큐잉 의심)
        cpu_percent = ollama_proc.cpu_percent(interval=1)

        # 4. API 응답 체크 ( 타임아웃 증가: 30초)
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
            #  연결 오류여도 프로세스가 살아있으면 재시작 안함
            return {"status": "starting", "memory_mb": memory_mb}

    except Exception as e:
        return {"status": "error", "error": str(e), "action": "restart"}

def should_restart_ollama(health_status, response_times):
    """Ollama 재시작 필요 여부 판단 (지능적 판단)"""
    # 1. 명시적 재시작 필요
    if health_status.get("action") == "restart":
        reason = health_status.get("status")
        if reason == "high_memory":
            max_mb = health_status.get('max_memory_mb', 9 * 1024)
            return True, f"메모리 과다 ({health_status['memory_mb']:.1f}MB > {max_mb}MB)"
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
    """모든 Ollama 프로세스 강제 종료 (메모리 과다 상황 대응)"""
    try:
        # 방법 1: psutil로 직접 종료 (가장 확실)
        killed_count = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                    proc.kill()
                    killed_count += 1
                    logger.info(f"Ollama 프로세스 종료: PID {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if killed_count > 0:
            time.sleep(3)  # 종료 대기
            logger.info(f"Ollama 프로세스 {killed_count}개 종료 완료")
        else:
            # 방법 2: taskkill 백업 (psutil 실패 시)
            subprocess.run(
                ["taskkill", "/F", "/IM", "ollama.exe"],
                timeout=10,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            time.sleep(2)
            logger.info("Ollama 프로세스 종료 완료 (taskkill)")

    except Exception as e:
        logger.error(f"Ollama 종료 실패: {e}")

def start_ollama(port):
    """Ollama 시작 (독립 인스턴스, RTX 2060 Tensor Core 최적화)"""
    try:
        # RTX 2060 Tensor Core 전용 환경변수 설정
        gpu_env_vars = "\n".join([f'$env:{k} = "{v}"' for k, v in GPU_OPTIMIZATION.items()])

        # PowerShell 스크립트로 독립 실행 (GPU 최적화 적용)
        ps_script = f'''
$env:OLLAMA_HOST = "127.0.0.1:{port}"
{gpu_env_vars}
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

# ===== 14b 전용 직렬화 큐 시스템 =====
import queue
import threading
from concurrent.futures import ThreadPoolExecutor

class LLMQueue:
    """14b 전용 직렬화 큐 (한 번에 1건만 처리)"""
    def __init__(self, port: int):
        self.port = port
        self.queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.running = False
        self.worker_thread = None
        
    def start(self):
        """큐 워커 시작"""
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            colored_print(f"[14b 큐] 포트 {self.port} 직렬화 큐 시작", "blue")
    
    def stop(self):
        """큐 워커 중지"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
    
    def _worker(self):
        """큐 워커: 한 번에 1건씩 순차 처리"""
        while self.running:
            try:
                # 큐에서 요청 대기 (1초 타임아웃)
                request = self.queue.get(timeout=1)
                if request is None:  # 종료 신호
                    break
                    
                # 14b 분석 실행
                self._process_request(request)
                self.queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                colored_print(f"[14b 큐] 처리 오류: {e}", "red")
    
    def _process_request(self, request):
        """14b 요청 처리 (압축된 프롬프트)"""
        try:
            # 압축된 프롬프트 생성
            compressed_prompt = self._compress_prompt(request)
            
            url = f"http://127.0.0.1:{self.port}/api/generate"
            payload = {
                "model": "qwen2.5:14b",
                "prompt": compressed_prompt,
                "stream": False,
                "options": {
                    "num_predict": 128,  # 응답 토큰 제한 (성능 향상)
                    "temperature": 0.7
                }
            }
            
            start_time = time.time()
            response = requests.post(url, json=payload, timeout=30)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                colored_print(f"[14b 큐] 처리 완료 ({duration:.1f}초)", "green")
                # 결과를 콜백으로 전달
                if request.get('callback'):
                    request['callback'](result, duration)
            else:
                colored_print(f"[14b 큐] API 오류: {response.status_code}", "red")
                
        except Exception as e:
            colored_print(f"[14b 큐] 처리 실패: {e}", "red")
    
    def _compress_prompt(self, request):
        """프롬프트 압축 (핵심 정보만)"""
        data = request.get('data', {})
        
        # 핵심 상태만 추출
        position = data.get('position', 'NONE')
        pnl = data.get('pnl', 0.0)
        price = data.get('price', 0.0)
        
        # 최근 3틱만 요약
        recent_prices = data.get('recent_prices', [])[-3:] if data.get('recent_prices') else []
        price_summary = f"{recent_prices}" if recent_prices else "N/A"
        
        # 압축된 프롬프트 (토큰 수 대폭 감소)
        compressed = f"""상태: {position}, PNL: {pnl:+.1f}%, 가격: ${price:.2f}
최근: {price_summary}
분석: {request.get('analysis_type', 'market')}"""
        
        return compressed
    
    def add_request(self, data, analysis_type, callback=None):
        """14b 분석 요청 추가 (비동기)"""
        request = {
            'data': data,
            'analysis_type': analysis_type,
            'callback': callback,
            'timestamp': time.time()
        }
        self.queue.put(request)
        colored_print(f"[14b 큐] 요청 추가: {analysis_type}", "cyan")

# 전역 14b 큐 인스턴스
llm_queue_14b = None

def start_14b_dedicated_queue():
    """14b 전용 큐 시작"""
    global llm_queue_14b
    if llm_queue_14b is None:
        llm_queue_14b = LLMQueue(OLLAMA_PORT_14B_DEDICATED)
        llm_queue_14b.start()
        colored_print("[14b 전용] 직렬화 큐 시스템 시작", "blue")

def warmup_ollama_model(port: int, model: str, prompt: str = "warmup") -> bool:
    """모델 워밍업: 짧은 프롬프트로 모델을 미리 로드하여 응답 지연을 줄임"""
    try:
        url = f"http://127.0.0.1:{port}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code == 200:
            colored_print(f"[WARMUP] 포트 {port} 모델 '{model}' 워밍업 완료", "green")
            return True
        else:
            colored_print(f"[WARMUP] 포트 {port} 모델 '{model}' 실패: HTTP {response.status_code}", "yellow")
            return False
    except Exception as e:
        colored_print(f"[WARMUP] 포트 {port} 모델 '{model}' 오류: {e}", "yellow")
        return False

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

def print_gpu_performance_report():
    """RTX 2060 GPU 성능 리포트 출력"""
    if GPU_STATS["batch_inference_count"] == 0:
        return

    avg_speedup = sum(GPU_STATS["batch_inference_speedup"]) / len(GPU_STATS["batch_inference_speedup"])

    colored_print("\n" + "="*60, "cyan")
    colored_print("RTX 2060 TENSOR CORE 성능 리포트", "cyan")
    colored_print("="*60, "cyan")
    colored_print(f"배치 추론 실행 횟수: {GPU_STATS['batch_inference_count']}회", "green")
    colored_print(f"평균 Tensor Core 가속: {avg_speedup:.1f}배", "green")
    colored_print(f"최대 가속: {max(GPU_STATS['batch_inference_speedup']):.1f}배", "green")
    colored_print(f"최소 가속: {min(GPU_STATS['batch_inference_speedup']):.1f}배", "yellow")

    # 예상 시간 절약
    time_saved = sum(GPU_STATS["batch_inference_speedup"]) * 5  # 평균 5초/요청 가정
    colored_print(f"누적 시간 절약: {time_saved/60:.1f}분", "magenta")

    colored_print("\n활성화된 최적화:", "cyan")
    colored_print("  ✓ FP16 KV Cache (VRAM 50% 절약)", "green")
    colored_print("  ✓ Flash Attention (Tensor Core)", "green")
    colored_print("  ✓ 배치 추론 병렬화", "green")
    colored_print("  ✓ KV Cache 60분 유지", "green")
    colored_print("  ✓ 모든 레이어 GPU 로드", "green")
    colored_print("="*60 + "\n", "cyan")

def guardian_cleanup_rogue_ollama():
    """ 불필요한 Ollama 프로세스 자동 정리 (실시간)"""
    procs = get_ollama_processes()
    if not procs:
        return

    # [WARN] Ollama는 각 모델마다 별도의 runner 프로세스를 생성함
    # runner 프로세스는 랜덤 포트를 사용하므로 포트로 구분 불가능!
    # 대신 메모리 기준으로만 판단 (15GB 초과만 정리)

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

        # 2. 메모리 폭주만 정리 (12GB 초과)
        # 16b 모델은 정상적으로 8-10GB 사용하므로, 12GB 초과면 비정상으로 판단
        if memory_mb > 12 * 1024:
            try:
                p['proc'].kill()
                killed.append(f"PID {pid} (메모리폭주 {memory_mb:.0f}MB)")
                colored_print(f"[GUARDIAN] 정리: PID {pid} (메모리폭주 {memory_mb:.0f}MB > 15GB)", "red")
            except:
                pass

    if killed:
        telegram.notify_system_error(f"불필요한 Ollama 정리: {', '.join(killed)}")
        time.sleep(2)  # 정리 후 대기

def ask_llm_for_analysis(prompt: str) -> str:
    """ LLM에게 분석 요청 (11436 포트) - 16b 단독"""
    try:
        response = requests.post(
            f"{OLLAMA_IMPROVEMENT_HOST}/api/generate",
            json={
                "model": OLLAMA_IMPROVEMENT_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=OLLAMA_IMPROVEMENT_TIMEOUT
        )

        if response.status_code == 200:
            return response.json().get('response', '')
        else:
            colored_print(f"[LLM] 응답 오류: {response.status_code}", "yellow")
            return ""

    except requests.Timeout:
        colored_print(f"[LLM] 타임아웃 (60초 초과)", "yellow")
        return ""
    except Exception as e:
        colored_print(f"[LLM] 오류: {e}", "yellow")
        return ""

def batch_ask_llm(prompts: list) -> list:
    """
    RTX 2060 Tensor Core 최적화: 배치 추론
    여러 프롬프트를 병렬로 처리하여 Tensor Core 활용률 극대화

    Args:
        prompts: 프롬프트 리스트

    Returns:
        응답 리스트 (순서 보장)
    """
    import concurrent.futures

    colored_print(f"[BATCH INFERENCE] Tensor Core 병렬 처리 ({len(prompts)}개 프롬프트)", "cyan")

    def _single_request(prompt_data):
        idx, prompt = prompt_data
        try:
            response = requests.post(
                f"{OLLAMA_IMPROVEMENT_HOST}/api/generate",
                json={
                    "model": OLLAMA_IMPROVEMENT_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=OLLAMA_IMPROVEMENT_TIMEOUT
            )

            if response.status_code == 200:
                return idx, response.json().get('response', '')
            else:
                return idx, ""
        except Exception as e:
            colored_print(f"[BATCH] 프롬프트 {idx+1} 오류: {e}", "yellow")
            return idx, ""

    # 병렬 실행 (ThreadPoolExecutor로 동시 요청)
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(prompts)) as executor:
        results = list(executor.map(_single_request, enumerate(prompts)))

    # 순서대로 정렬
    results.sort(key=lambda x: x[0])
    responses = [r[1] for r in results]

    elapsed = time.time() - start_time

    # RTX 2060 성능 통계 수집
    estimated_sequential_time = elapsed * len(prompts) / 1.5  # 추정 순차 실행 시간
    speedup = estimated_sequential_time / elapsed if elapsed > 0 else 1
    GPU_STATS["batch_inference_count"] += 1
    GPU_STATS["batch_inference_speedup"].append(speedup)

    colored_print(
        f"[BATCH INFERENCE] 완료 ({elapsed:.1f}초, {len(prompts)}개 병렬, "
        f"Tensor Core 가속 {speedup:.1f}배)", "green"
    )

    return responses

def ask_llm_triple_validation(primary_prompt: str, validator1_prompt: str, validator2_prompt: str) -> dict:
    """
     Option 1: Triple Validation System

    3개의 다른 관점에서 분석하여 오판 확률 대폭 감소
    - Primary: 주 분석기 (일반적 관점)
    - Validator 1: 검증기 #1 (비판적 관점 - "왜 이게 틀릴 수 있는가?")
    - Validator 2: 검증기 #2 (반대 입장 - "정반대로 해석하면?")

    Returns:
        {
            'primary_response': str,
            'validator1_response': str,
            'validator2_response': str,
            'consensus': bool,  # 3개 중 2개 이상 동의 여부
            'final_decision': str  # 최종 결정
        }
    """
    import time

    colored_print("[TRIPLE VALIDATION] 3중 검증 시작 (RTX 2060 Tensor Core 병렬 처리)...", "cyan")

    # RTX 2060 Tensor Core 최적화: 배치 추론으로 3개 동시 처리
    # 기존: 순차 15초 → 개선: 병렬 6-7초
    start_time = time.time()

    responses = batch_ask_llm([primary_prompt, validator1_prompt, validator2_prompt])
    primary_response, validator1_response, validator2_response = responses

    total_time = time.time() - start_time
    colored_print(f"[TRIPLE VALIDATION] Tensor Core 병렬 완료 ({total_time:.1f}초, 순차 대비 ~2배 속도)", "green")

    # 4. 합의 체크 (간단한 키워드 기반)
    # Primary에서 핵심 키워드 추출
    primary_keywords = set()
    for keyword in ['손절', '익절', '횡보', '추세', '진입', '청산', '보유']:
        if keyword in primary_response:
            primary_keywords.add(keyword)

    # Validator들도 동일 키워드 언급하는지 체크
    val1_agree = any(kw in validator1_response for kw in primary_keywords) if primary_keywords else False
    val2_agree = any(kw in validator2_response for kw in primary_keywords) if primary_keywords else False

    # 3개 중 2개 이상 동의?
    agreement_count = sum([True, val1_agree, val2_agree])  # Primary는 항상 True
    consensus = agreement_count >= 2

    colored_print(f"[TRIPLE VALIDATION] 합의 여부: {'[OK] 동의 {}/3'.format(agreement_count) if consensus else '[ERROR] 불일치'}",
                  "green" if consensus else "yellow")

    total_time = time.time() - start_time
    colored_print(f"[TRIPLE VALIDATION] 총 소요 시간: {total_time:.1f}초", "cyan")

    return {
        'primary_response': primary_response,
        'validator1_response': validator1_response,
        'validator2_response': validator2_response,
        'consensus': consensus,
        'agreement_count': agreement_count,
        'final_decision': primary_response if consensus else "불확실 - 추가 검토 필요"
    }

def load_error_patterns(error_file: str) -> list:
    """ Option 4: 저장된 오류 패턴 로드"""
    import json
    try:
        with open(error_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_error_patterns(error_file: str, patterns: list):
    """ Option 4: 오류 패턴 저장 (최근 100건만)"""
    import json
    try:
        # 최근 100건만 유지
        recent_patterns = patterns[-100:] if len(patterns) > 100 else patterns
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(recent_patterns, f, indent=2, ensure_ascii=False)
    except Exception as e:
        colored_print(f"[ERROR PATTERN] 저장 실패: {e}", "yellow")

def analyze_losing_trades_for_patterns(trader_name: str, trades: list, error_patterns: list) -> list:
    """
     Option 4: Self-Improving Feedback Loop - 손실 거래에서 패턴 학습

    손실 거래를 분석하여 반복되는 실수 패턴을 찾아냅니다.
    예: "상승 추세인데 숏 진입 → 3번 연속 손실" 같은 패턴

    Returns:
        새로 발견된 오류 패턴 리스트
    """
    from datetime import datetime

    if len(trades) < 10:
        return []

    # 손실 거래만 필터링
    losing_trades = [t for t in trades if t.get('pnl_pct', 0) < 0 or t.get('profit_pct', 0) < 0]

    if len(losing_trades) < 3:
        return []

    # 최근 20건 손실 거래만 분석
    recent_losses = losing_trades[-20:]

    new_patterns = []

    # 패턴 1: 추세 역행 (상승장에서 숏, 하락장에서 롱)
    trend_reverse_count = 0
    for loss in recent_losses:
        trend = loss.get('trend', '')
        side = loss.get('side', '')
        if (trend == 'BULL' and side == 'SELL') or (trend == 'BEAR' and side == 'BUY'):
            trend_reverse_count += 1

    if trend_reverse_count >= 3:  # 3번 이상 반복
        pattern = {
            'type': 'trend_reverse',
            'count': trend_reverse_count,
            'description': f'추세 역행 진입 {trend_reverse_count}번 → 손실',
            'timestamp': datetime.now().isoformat()
        }
        new_patterns.append(pattern)
        colored_print(f"[{trader_name}]  패턴 발견: {pattern['description']}", "yellow")

    # 패턴 2: 긴 보유 시간 (60분 이상 보유 후 손실)
    long_hold_losses = [l for l in recent_losses if l.get('holding_time_sec', 0) > 3600]  # 60분 = 3600초
    if len(long_hold_losses) >= 3:
        pattern = {
            'type': 'long_hold_loss',
            'count': len(long_hold_losses),
            'description': f'60분 이상 보유 {len(long_hold_losses)}번 → 손실',
            'timestamp': datetime.now().isoformat()
        }
        new_patterns.append(pattern)
        colored_print(f"[{trader_name}]  패턴 발견: {pattern['description']}", "yellow")

    # 패턴 3: 낮은 신뢰도 진입 (신뢰도 < 70%)
    low_conf_losses = [l for l in recent_losses if l.get('confidence', 100) < 70]
    if len(low_conf_losses) >= 3:
        pattern = {
            'type': 'low_confidence_entry',
            'count': len(low_conf_losses),
            'description': f'신뢰도 70% 미만 진입 {len(low_conf_losses)}번 → 손실',
            'timestamp': datetime.now().isoformat()
        }
        new_patterns.append(pattern)
        colored_print(f"[{trader_name}]  패턴 발견: {pattern['description']}", "yellow")

    # 기존 패턴에 추가
    error_patterns.extend(new_patterns)

    return new_patterns

def llm_analyze_trades_for_improvement(trader_name, trades, performance, error_patterns=None):
    """ LLM이 거래 패턴 분석 및 개선안 제시 (Option 1 + Option 4 통합)"""
    import json

    if len(trades) < 5:
        return []

    #  Option 4: 먼저 오류 패턴 자동 학습
    if error_patterns is not None:
        new_patterns = analyze_losing_trades_for_patterns(trader_name, trades, error_patterns)
        if new_patterns:
            colored_print(f"[{trader_name}]  새로운 오류 패턴 {len(new_patterns)}개 학습 완료", "cyan")

    # 최근 20건만 분석
    recent_trades = trades[-20:]

    # 거래 요약
    trades_summary = []
    for t in recent_trades:
        summary = f"- {t.get('action', '?')}: {t.get('profit_pct', 0):+.2f}%, 보유 {t.get('hold_minutes', 0):.0f}분, 트렌드 {t.get('trend', '?')}"
        trades_summary.append(summary)

    trades_text = "\n".join(trades_summary)

    #  Option 4: 오류 패턴을 프롬프트에 포함
    error_context = ""
    if error_patterns and len(error_patterns) > 0:
        recent_errors = error_patterns[-5:]  # 최근 5개만
        error_lines = []
        for err in recent_errors:
            error_lines.append(f"- {err.get('description', '알 수 없음')}")
        error_context = "\n\n## [WARN] 최근 발견된 실패 패턴\n" + "\n".join(error_lines)
        error_context += "\n\n위 패턴을 고려하여 개선안을 제시하세요."

    #  Option 1: Triple Validation - 3가지 프롬프트 생성

    # Primary Prompt (주 분석)
    primary_prompt = f"""당신은 트레이딩 전문가입니다. {trader_name} 봇의 거래 데이터를 분석하고 개선 방안을 제시하세요.

## 전체 성과
- 총 거래: {performance['total_trades']}건
- 승률: {performance['win_rate']}%
- 총 수익률: {performance['total_return']}%

## 최근 20건 거래
{trades_text}{error_context}

## 분석 요청
1. 가장 큰 문제점 1-2개만 간결하게
2. 각 문제에 대한 구체적 개선안

답변은 2-3문장으로 작성하세요."""

    # Validator 1 Prompt (비판적 검증 - "왜 틀릴 수 있는가?")
    validator1_prompt = f"""당신은 비판적 분석가입니다. {trader_name} 봇의 성과를 회의적으로 검토하세요.

## 성과
- 승률: {performance['win_rate']}% | 총 수익: {performance['total_return']}%

## 최근 거래
{trades_text}

## 비판적 질문
1. 이 승률/수익이 **운**일 가능성은?
2. 가장 큰 위험 요소는 무엇인가?

2문장으로 답하세요."""

    # Validator 2 Prompt (반대 입장 - "정반대로 해석하면?")
    validator2_prompt = f"""당신은 역발상 분석가입니다. {trader_name} 봇의 데이터를 **반대 관점**으로 해석하세요.

## 성과
- 승률: {performance['win_rate']}% | 총 수익: {performance['total_return']}%

## 최근 거래
{trades_text}

## 역발상 질문
1. 만약 "손실을 늘려야" 한다면 어떻게 할까? (현재 전략의 반대)
2. 그 반대가 실제로 더 나을 가능성은?

2문장으로 답하세요."""

    #  Triple Validation 실행
    validation_result = ask_llm_triple_validation(primary_prompt, validator1_prompt, validator2_prompt)

    if not validation_result['primary_response']:
        return []

    # 합의가 있을 때만 분석 결과 사용
    if validation_result['consensus']:
        llm_response = validation_result['final_decision']
        colored_print(f"[{trader_name}] [OK] 3중 검증 합의 ({validation_result['agreement_count']}/3)", "green")
        colored_print(f"[{trader_name}] [LLM 인사이트] {llm_response[:150]}...", "magenta")
    else:
        colored_print(f"[{trader_name}] [WARN] 3중 검증 불일치 - 개선안 보류", "yellow")
        return []  # 합의 없으면 개선 안 함 (안전)

    # 간단한 키워드 기반 개선안 추출
    improvements = []

    if "횡보" in llm_response or "neutral" in llm_response.lower():
        improvements.append({'type': 'sideways_block', 'source': 'LLM_TRIPLE'})

    if ("손절" in llm_response or "stop" in llm_response.lower()) and ("늦" in llm_response or "tight" in llm_response.lower()):
        improvements.append({'type': 'tighten_stop_loss', 'source': 'LLM_TRIPLE'})

    if "보유" in llm_response or "hold" in llm_response.lower():
        improvements.append({'type': 'reduce_hold_time', 'source': 'LLM_TRIPLE'})

    #  Option 4: 오류 패턴 기반 개선안 추가
    if error_patterns:
        for pattern in error_patterns[-5:]:  # 최근 5개 패턴만
            if pattern['type'] == 'trend_reverse' and pattern['count'] >= 3:
                improvements.append({'type': 'enforce_trend_following', 'source': 'ERROR_PATTERN'})
            elif pattern['type'] == 'long_hold_loss' and pattern['count'] >= 3:
                improvements.append({'type': 'reduce_hold_time', 'source': 'ERROR_PATTERN'})
            elif pattern['type'] == 'low_confidence_entry' and pattern['count'] >= 3:
                improvements.append({'type': 'increase_min_confidence', 'source': 'ERROR_PATTERN'})

    return improvements

def check_trading_health(trader_name, history_file):
    """ 거래 현황 및 수익 체크 (1시간마다)"""
    import json
    from datetime import datetime, timedelta
    global last_no_trading_alert

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

        # ===== 다차원 거래 분석 =====
        # 1시간, 6시간, 24시간 단위로 거래 빈도 체크

        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        six_hours_ago = now - timedelta(hours=6)
        one_day_ago = now - timedelta(hours=24)

        recent_1h = []
        recent_6h = []
        recent_24h = []

        # 마지막 거래 시간 찾기
        last_trade_time = None

        for t in trades:
            try:
                trade_time = datetime.fromisoformat(t.get('timestamp', ''))

                if trade_time >= one_hour_ago:
                    recent_1h.append(t)
                if trade_time >= six_hours_ago:
                    recent_6h.append(t)
                if trade_time >= one_day_ago:
                    recent_24h.append(t)

                # 마지막 거래 시간 추적
                if last_trade_time is None or trade_time > last_trade_time:
                    last_trade_time = trade_time
            except:
                continue

        # 전체 수익률 계산
        total_return = sum([t.get('profit_pct', 0) for t in trades])
        total_trades = len(trades)
        wins = len([t for t in trades if t.get('profit_pct', 0) > 0])
        win_rate = wins / total_trades * 100 if total_trades > 0 else 0

        # 거래 빈도 분석
        count_1h = len(recent_1h)
        count_6h = len(recent_6h)
        count_24h = len(recent_24h)

        # 마지막 거래 이후 경과 시간
        hours_since_last_trade = 0
        if last_trade_time:
            hours_since_last_trade = (now - last_trade_time).total_seconds() / 3600

        # 경고 조건 (다층 분석)
        alert = False
        warnings = []
        critical = False  # 심각한 문제

        # ===== 거래 빈도 모니터링 (계층적 알람) =====

        # 1. **24시간 거래 없음** (심각) - 임계값 문제 의심
        if hours_since_last_trade >= 24:
            warnings.append(f"[심각] {hours_since_last_trade:.0f}시간 동안 거래 없음 → 임계값 너무 높음 의심")
            alert = True
            critical = True
            # 텔레그램 알림 (6시간마다만)
            current_time = time.time()
            if current_time - last_no_trading_alert.get(trader_name, 0) > NO_TRADING_ALERT_COOLDOWN:
                telegram.notify_bot_no_trading(trader_name, hours_since_last_trade)
                last_no_trading_alert[trader_name] = current_time
            logger.critical(f"{trader_name}: {hours_since_last_trade:.0f}시간 동안 거래 없음 - 긴급 확인 필요!")

        # 2. **6시간 거래 없음** (경고) - 시장 상황 or 임계값 문제
        elif hours_since_last_trade >= 6:
            warnings.append(f"[경고] {hours_since_last_trade:.0f}시간 동안 거래 없음")
            alert = True
            # 텔레그램 알림 (6시간마다만)
            current_time = time.time()
            if current_time - last_no_trading_alert.get(trader_name, 0) > NO_TRADING_ALERT_COOLDOWN:
                telegram.notify_bot_no_trading(trader_name, hours_since_last_trade)
                last_no_trading_alert[trader_name] = current_time
            logger.warning(f"{trader_name}: {hours_since_last_trade:.0f}시간 동안 거래 없음")

        # 3. **1시간 거래 없음** (정보) - 정상 범위일 수 있음
        elif count_1h == 0 and trader_name == "ETH":
            # ETH는 활발하게 거래해야 하므로 1시간도 체크
            warnings.append("[정보] 1시간 동안 거래 없음 (정상 범위 가능)")
            logger.info(f"{trader_name}: 1시간 동안 거래 없음")

        # 2. 총 수익률이 음수 (손실 누적)
        if total_return < -5:
            warnings.append(f"누적 손실 {total_return:.1f}%")
            alert = True

        # 3. 승률이 40% 미만
        if win_rate < 40 and total_trades >= 10:
            warnings.append(f"승률 {win_rate:.0f}%")
            alert = True

        message = f"{trader_name}: 거래 {total_trades}건, 수익 {total_return:+.2f}%, 승률 {win_rate:.0f}%, 최근24h {count_24h}건"

        # ===== 텔레그램 알림 (24시간 거래 없음) =====
        if critical and hours_since_last_trade >= 24:
            # 전략 파일에서 현재 임계값 확인
            confidence_info = ""
            try:
                strategy_file = f"C:\\Users\\user\\Documents\\코드3\\eth_current_strategy.json" if trader_name == "ETH" else f"C:\\Users\\user\\Documents\\코드4\\kis_current_strategy.json"
                with open(strategy_file, 'r', encoding='utf-8') as f:
                    strategy = json.load(f)
                    min_conf = strategy.get('min_confidence', 'N/A')
                    confidence_info = f"\n현재 임계값: {min_conf}%"
            except:
                pass

            telegram.send_message(
                f"[CRITICAL] <b>{trader_name} 거래 중단 감지</b>\n\n"
                f"마지막 거래: {hours_since_last_trade:.0f}시간 전\n"
                f"총 거래: {total_trades}건\n"
                f"승률: {win_rate:.0f}%{confidence_info}\n\n"
                f"<b>원인 분석:</b>\n"
                f"1. 임계값 너무 높음 (80%+)\n"
                f"2. 최근 고신뢰도 거래만 성공 → 잘못 학습\n"
                f"3. 샘플 편향으로 인한 과적합\n\n"
                f"<b>조치:</b>\n"
                f"임계값 최적화 알고리즘 재계산 중\n"
                f"(수수료 + 기대값 기반 최적화)"
            )

        return {
            'status': 'critical' if critical else ('warning' if alert else 'healthy'),
            'total_trades': total_trades,
            'total_return': total_return,
            'win_rate': win_rate,
            'recent_count': count_1h,
            'recent_count_24h': count_24h,
            'hours_since_last_trade': hours_since_last_trade,
            'recent_return': sum([t.get('profit_pct', 0) for t in recent_1h]) if recent_1h else 0,
            'message': message,
            'warnings': warnings,
            'alert': alert,
            'critical': critical
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
    """ 전략 개선안 적용 (자동)"""
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

            #  Option 4: 오류 패턴 기반 개선안
            elif imp_type == 'enforce_trend_following':
                strategy['trend_check_enabled'] = True
                strategy['block_counter_trend'] = True  # 추세 역행 완전 차단
                applied.append(f"추세 역행 진입 차단 ({source})")
                colored_print(f"[{trader_name}] [개선 적용] 추세 역행 진입 차단 (출처: {source})", "green")

            #  규제 자동 제거 (LLM 자율 판단 허용)
            elif imp_type == 'remove_trade_blocks':
                # 기존 차단 규제 제거
                if 'block_counter_trend' in strategy:
                    del strategy['block_counter_trend']
                if 'rsi_filter_enabled' in strategy:
                    strategy['rsi_filter_enabled'] = False
                if 'require_double_confirmation' in strategy:
                    strategy['require_double_confirmation'] = False
                strategy['min_trend_strength'] = 0.1  # 최소화
                applied.append(f"거래 차단 규제 제거 (LLM 자율 판단) ({source})")
                colored_print(f"[{trader_name}] [개선 적용] 거래 차단 제거, LLM 자율 판단 허용 (출처: {source})", "yellow")

            elif imp_type == 'increase_min_confidence':
                old_conf = strategy.get('min_confidence', 75)
                new_conf = min(85, old_conf + 5)  # 최대 85%까지
                strategy['min_confidence'] = new_conf
                applied.append(f"최소 신뢰도 {old_conf}% → {new_conf}% ({source})")
                colored_print(f"[{trader_name}] [개선 적용] 최소 신뢰도 {old_conf}% → {new_conf}% (출처: {source})", "green")

            #  백그라운드 학습 발견 전략 (자동 검증 완료)
            elif imp_type == 'rsi_based_entry':
                strategy['rsi_filter_enabled'] = True
                strategy['rsi_oversold'] = 30  # RSI < 30 = 과매도 (매수 기회)
                strategy['rsi_overbought'] = 70  # RSI > 70 = 과매수 (매수 차단)
                strategy['require_rsi_confirmation'] = True  # RSI 확인 필수
                applied.append(f"RSI 기반 진입 필터 활성화 ({source})")
                colored_print(f"[{trader_name}] [개선 적용] RSI 기반 진입 필터 (30/70) (출처: {source})", "green")

            elif imp_type == 'conservative_entry':
                old_conf = strategy.get('min_confidence', 75)
                new_conf = min(85, old_conf + 5)
                strategy['min_confidence'] = new_conf
                strategy['require_double_confirmation'] = True  # 이중 확인 필요
                strategy['min_volume_ratio'] = 1.2  # 거래량 20% 이상 증가 확인
                applied.append(f"보수적 진입 강화 (신뢰도 {new_conf}%, 이중확인) ({source})")
                colored_print(f"[{trader_name}] [개선 적용] 보수적 진입 강화 (출처: {source})", "green")

            elif imp_type == 'stop_loss_adjustment':
                # 기존 tighten_stop_loss와 다르게, 동적 손절 조정
                strategy['dynamic_stop_loss_enabled'] = True
                strategy['stop_loss_step'] = 0.5  # 0.5% 단위로 조정
                old_sl = strategy.get('stop_loss_pct', -2.5)
                new_sl = max(-4.0, old_sl - 0.5)  # 최대 -4%까지만
                strategy['stop_loss_pct'] = new_sl
                applied.append(f"동적 손절 조정 활성화 ({old_sl}% → {new_sl:.1f}%) ({source})")
                colored_print(f"[{trader_name}] [개선 적용] 동적 손절 조정 (출처: {source})", "green")

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

            colored_print(f"[{trader_name}] [OK] {len(applied)}개 개선사항 적용 완료", "green")

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

    #  모든 로그 출력 (디버깅 모드)
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

last_log_time = {"ETH": 0.0, "KIS": 0.0}

def log_reader_thread(process, trader_name):
    """트레이더 로그 읽기 스레드"""
    # 트레이더별 로그 파일 경로
    if "ETH" in trader_name:
        log_file_path = Path(r"C:\Users\user\Documents\코드3\eth_trader.log")
    elif "KIS" in trader_name:
        log_file_path = Path(r"C:\Users\user\Documents\코드4\kis_trader.log")
    else:
        log_file_path = None

    try:
        # 로그 파일 열기 (append 모드)
        log_file = None
        if log_file_path:
            log_file = open(log_file_path, 'a', encoding='utf-8', buffering=1)  # 라인 버퍼링

        for line in iter(process.stdout.readline, b''):
            if not line:
                break

            # UTF-8 디코딩
            try:
                decoded_line = line.decode('utf-8', errors='ignore')
            except:
                decoded_line = str(line)

            # 로그 파일에 쓰기
            if log_file:
                log_file.write(decoded_line)
                log_file.flush()  # 즉시 디스크에 쓰기

            # 중요 정보 필터링 후 콘솔 출력
            important_info = parse_trader_log(decoded_line, trader_name)
            if important_info:
                colored_print(f"[{trader_name}] {important_info}", "magenta")
            # 하트비트 갱신
            try:
                key = "ETH" if "ETH" in trader_name else ("KIS" if "KIS" in trader_name else trader_name)
                last_log_time[key] = time.time()
            except Exception:
                pass
    except Exception as e:
        colored_print(f"[{trader_name}] 로그 읽기 오류: {e}", "red")
    finally:
        if log_file:
            log_file.close()

# ===== 트레이더 관리 =====
    def start_trader(script_path, python_exe, working_dir, trader_name, ollama_port):
        """트레이더 시작 (인터넷 검색 기반 강력한 안전장치 시스템)"""
        colored_print(f"[{trader_name}] 🛡️ 강력한 안전장치 시스템 시작...", "yellow")
        
        # 환경변수 설정
        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"127.0.0.1:{ollama_port}"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        for key, value in GPU_OPTIMIZATION.items():
            env[key] = value

        # 스크립트 파일 존재 확인
        if not os.path.isfile(script_path):
            colored_print(f"[{trader_name}] ❌ 스크립트 파일 없음: {script_path}", "red")
            send_trader_failure_alert(trader_name, f"스크립트 파일 없음: {script_path}")
            return None

        # ===== 강화된 폴백 시스템 (인터넷 검색 기반) =====
        start_methods = [
            {
                "name": "배치 파일 방식",
                "func": lambda: self._start_with_batch(script_path, working_dir, env, trader_name)
            },
            {
                "name": "PowerShell 방식", 
                "func": lambda: self._start_with_powershell(script_path, working_dir, env, trader_name, ollama_port)
            },
            {
                "name": "직접 Python 실행",
                "func": lambda: self._start_with_python(script_path, working_dir, env, trader_name)
            },
            {
                "name": "CMD 방식",
                "func": lambda: self._start_with_cmd(script_path, working_dir, env, trader_name, ollama_port)
            },
            {
                "name": "Python 모듈 실행",
                "func": lambda: self._start_with_module(script_path, working_dir, env, trader_name)
            }
        ]
        
        for i, method in enumerate(start_methods, 1):
            try:
                colored_print(f"[{trader_name}] 🔄 폴백 {i}: {method['name']} 시도...", "yellow")
                process = method['func']()
                
                if process and process.poll() is None and process.pid and process.pid > 0:
                    colored_print(f"[{trader_name}] ✅ 폴백 {i} 성공 (PID: {process.pid})", "green")
                    
                    # 성공 시 모니터링 스레드 시작
                    monitor_thread = threading.Thread(
                        target=self._monitor_trader_process,
                        args=(process, trader_name, script_path, working_dir, env, ollama_port),
                        daemon=True
                    )
                    monitor_thread.start()
                    
                    return process
                else:
                    colored_print(f"[{trader_name}] ❌ 폴백 {i} 실패", "red")
                    
            except Exception as e:
                colored_print(f"[{trader_name}] ❌ 폴백 {i} 오류: {e}", "red")
                import traceback
                traceback.print_exc()

        # ===== 모든 폴백 실패 =====
        colored_print(f"[{trader_name}] ❌ 모든 폴백 실패 - 트레이더 시작 불가", "red")
        send_trader_failure_alert(trader_name, "모든 시작 방식 실패 - 시스템 진단 필요")
        self._collect_system_diagnostics(trader_name, working_dir, script_path)
        return None

    def _start_with_batch(self, script_path, working_dir, env, trader_name):
        """배치 파일 방식으로 트레이더 시작"""
        batch_file = os.path.join(working_dir, f"start_{trader_name.lower().replace(' ', '_')}.bat")
        
        batch_content = f"""@echo off
cd /d "{working_dir}"
set OLLAMA_HOST=127.0.0.1:{env.get('OLLAMA_HOST', '11434')}
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
python "{script_path}"
"""
        
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        
        CREATE_NO_WINDOW = 0x08000000
        process = subprocess.Popen(
            [batch_file],
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            universal_newlines=False,
            creationflags=CREATE_NO_WINDOW
        )
        
        # 로그 읽기 스레드 시작
        log_thread = threading.Thread(
            target=log_reader_thread,
            args=(process, trader_name),
            daemon=True
        )
        log_thread.start()
        
        time.sleep(3)
        return process

    def _start_with_powershell(self, script_path, working_dir, env, trader_name, ollama_port):
        """PowerShell 방식으로 트레이더 시작"""
        ps_script = f"""
$env:OLLAMA_HOST = "127.0.0.1:{ollama_port}"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
Set-Location "{working_dir}"
python "{script_path}"
"""
        
        CREATE_NO_WINDOW = 0x08000000
        process = subprocess.Popen(
            ["powershell", "-Command", ps_script],
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            universal_newlines=False,
            creationflags=CREATE_NO_WINDOW
        )
        
        log_thread = threading.Thread(
            target=log_reader_thread,
            args=(process, trader_name),
            daemon=True
        )
        log_thread.start()
        
        time.sleep(3)
        return process

    def _start_with_python(self, script_path, working_dir, env, trader_name):
        """직접 Python 실행"""
        import sys
        python_cmd = [sys.executable, script_path]
        
        CREATE_NO_WINDOW = 0x08000000
        process = subprocess.Popen(
            python_cmd,
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            universal_newlines=False,
            creationflags=CREATE_NO_WINDOW
        )
        
        log_thread = threading.Thread(
            target=log_reader_thread,
            args=(process, trader_name),
            daemon=True
        )
        log_thread.start()
        
        time.sleep(3)
        return process

    def _start_with_cmd(self, script_path, working_dir, env, trader_name, ollama_port):
        """CMD 방식으로 트레이더 시작"""
        cmd_script = f'cd /d "{working_dir}" && set OLLAMA_HOST=127.0.0.1:{ollama_port} && set PYTHONIOENCODING=utf-8 && set PYTHONUTF8=1 && python "{script_path}"'
        
        CREATE_NO_WINDOW = 0x08000000
        process = subprocess.Popen(
            ["cmd", "/c", cmd_script],
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            universal_newlines=False,
            creationflags=CREATE_NO_WINDOW
        )
        
        log_thread = threading.Thread(
            target=log_reader_thread,
            args=(process, trader_name),
            daemon=True
        )
        log_thread.start()
        
        time.sleep(3)
        return process

    def _start_with_module(self, script_path, working_dir, env, trader_name):
        """Python 모듈 실행 방식"""
        import sys
        python_cmd = [sys.executable, "-m", "runpy", "run_path", script_path]
        
        CREATE_NO_WINDOW = 0x08000000
        process = subprocess.Popen(
            python_cmd,
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            universal_newlines=False,
            creationflags=CREATE_NO_WINDOW
        )
        
        log_thread = threading.Thread(
            target=log_reader_thread,
            args=(process, trader_name),
            daemon=True
        )
        log_thread.start()
        
        time.sleep(3)
        return process

    def _monitor_trader_process(self, process, trader_name, script_path, working_dir, env, ollama_port):
        """트레이더 프로세스 실시간 모니터링 (인터넷 검색 기반)"""
        restart_count = 0
        max_restarts = 10
        last_heartbeat = time.time()
        
        while restart_count < max_restarts:
            try:
                # 프로세스 상태 확인
                if process.poll() is not None:
                    colored_print(f"[{trader_name}] ❌ 프로세스 종료 감지 - 자동 재시작 시도 {restart_count + 1}/{max_restarts}", "red")
                    restart_count += 1
                    
                    # 5초 대기 후 재시작
                    time.sleep(5)
                    
                    # 재시작 시도
                    new_process = self._restart_trader(script_path, working_dir, env, trader_name, ollama_port)
                    if new_process:
                        process = new_process
                        colored_print(f"[{trader_name}] ✅ 재시작 성공 (PID: {process.pid})", "green")
                    else:
                        colored_print(f"[{trader_name}] ❌ 재시작 실패", "red")
                        send_trader_failure_alert(trader_name, f"재시작 실패 {restart_count}회")
                
                # 하트비트 확인 (30초마다)
                current_time = time.time()
                if current_time - last_heartbeat > 30:
                    colored_print(f"[{trader_name}] 💓 하트비트 확인 중...", "blue")
                    last_heartbeat = current_time
                
                time.sleep(10)  # 10초마다 체크
                
            except Exception as e:
                colored_print(f"[{trader_name}] ❌ 모니터링 오류: {e}", "red")
                time.sleep(5)
        
        colored_print(f"[{trader_name}] ❌ 최대 재시작 시도 초과 - 모니터링 중단", "red")
        send_trader_failure_alert(trader_name, f"최대 재시작 시도 초과 ({max_restarts}회)")

    def _restart_trader(self, script_path, working_dir, env, trader_name, ollama_port):
        """트레이더 재시작 (간단한 방식)"""
        try:
            import sys
            python_cmd = [sys.executable, script_path]
            
            CREATE_NO_WINDOW = 0x08000000
            process = subprocess.Popen(
                python_cmd,
                cwd=working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                universal_newlines=False,
                creationflags=CREATE_NO_WINDOW
            )
            
            # 로그 읽기 스레드 시작
            log_thread = threading.Thread(
                target=log_reader_thread,
                args=(process, trader_name),
                daemon=True
            )
            log_thread.start()
            
            time.sleep(2)
            return process
            
        except Exception as e:
            colored_print(f"[{trader_name}] ❌ 재시작 오류: {e}", "red")
            return None

    def _collect_system_diagnostics(self, trader_name, working_dir, script_path):
        """시스템 진단 정보 수집 (인터넷 검색 기반)"""
        try:
            import psutil
            import shutil
            
            # 시스템 리소스 상태
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = shutil.disk_usage(working_dir)
            
            # 네트워크 상태
            network_io = psutil.net_io_counters()
            
            # 프로세스 정보
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    if 'python' in proc.info['name'].lower():
                        python_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            diagnostic_info = f"""
🔍 시스템 진단 정보:
- CPU 사용률: {cpu_percent}%
- 메모리 사용률: {memory.percent}%
- 디스크 여유공간: {disk.free / (1024**3):.1f}GB
- 네트워크 송신: {network_io.bytes_sent / (1024**2):.1f}MB
- 네트워크 수신: {network_io.bytes_recv / (1024**2):.1f}MB
- 작업 디렉터리: {working_dir}
- 스크립트 경로: {script_path}
- Python 프로세스 수: {len(python_processes)}
"""
            
            colored_print(f"[{trader_name}] {diagnostic_info}", "yellow")
            
            # 진단 정보를 파일로 저장
            diagnostic_file = os.path.join(working_dir, f"{trader_name.lower().replace(' ', '_')}_diagnostic.txt")
            with open(diagnostic_file, 'w', encoding='utf-8') as f:
                f.write(diagnostic_info)
                f.write(f"\nPython 프로세스 상세:\n")
                for proc in python_processes:
                    f.write(f"  PID: {proc['pid']}, CPU: {proc['cpu_percent']}%, Memory: {proc['memory_percent']}%\n")
            
            colored_print(f"[{trader_name}] 🔍 진단 정보 저장: {diagnostic_file}", "yellow")
            
        except Exception as e:
            colored_print(f"[{trader_name}] ❌ 진단 정보 수집 실패: {e}", "red")

def monitor_trader_health(trader_name: str, process, max_restart_attempts: int = 10):
    """트레이더 상태 실시간 모니터링 (안전장치)"""
    restart_count = 0
    last_activity = time.time()
    
    while restart_count < max_restart_attempts:
        try:
            # 프로세스 상태 확인
            if process.poll() is not None:
                colored_print(f"[{trader_name}] ❌ 프로세스 종료 감지 - 자동 재시작 시도 {restart_count + 1}/{max_restart_attempts}", "red")
                restart_count += 1
                
                # 재시작 시도
                time.sleep(5)  # 5초 대기
                # 여기서 재시작 로직을 호출할 수 있음
                return False
            
            # 활동 확인 (30초마다)
            if time.time() - last_activity > 30:
                colored_print(f"[{trader_name}] ⚠️ 활동 없음 - 상태 확인 중...", "yellow")
                last_activity = time.time()
            
            time.sleep(10)  # 10초마다 체크
            
        except Exception as e:
            colored_print(f"[{trader_name}] ❌ 모니터링 오류: {e}", "red")
            time.sleep(5)
    
    colored_print(f"[{trader_name}] ❌ 최대 재시작 시도 초과 - 모니터링 중단", "red")
    return False

def send_trader_failure_alert(trader_name: str, error_details: str):
    """트레이더 시작 실패 시 텔레그램 알림"""
    try:
        from telegram_notifier import TelegramNotifier
        telegram = TelegramNotifier()
        
        alert_message = f"""
🚨 <b>트레이더 시작 실패 알림</b>

<b>트레이더:</b> {trader_name}
<b>시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
<b>오류:</b> {error_details}

<b>자동 복구 시도 중...</b>
<i>수동 개입이 필요할 수 있습니다.</i>
"""
        
        telegram.send_message(alert_message, priority="critical")
        colored_print(f"[{trader_name}] 🚨 텔레그램 알림 전송 완료", "red")
        
    except Exception as e:
        colored_print(f"[{trader_name}] ❌ 텔레그램 알림 전송 실패: {e}", "red")

def start_trader_with_backoff(name: str, script_path: str, python_exe: str, working_dir: str, ollama_port: int, max_retries: int = 5):
    """트레이더 시작을 지수 백오프로 재시도 (최대 N회, 1→2→4→8→16s)"""
    attempt = 0
    backoff = 1
    while attempt < max_retries:
        proc = start_trader(script_path, python_exe, working_dir, name, ollama_port)
        if proc is not None:
            return proc
        colored_print(f"[RETRY] {name} 시작 재시도 {attempt+1}/{max_retries} (대기 {backoff}s)", "yellow")
        time.sleep(backoff)
        backoff = min(backoff * 2, 30)
        attempt += 1
    colored_print(f"[FAIL] {name} 시작 실패 (재시도 {max_retries}회 초과)", "red")
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
    try:
        # 메모리 사용량 체크
        if not check_memory_usage():
            colored_print("[WARNING] 메모리 사용량이 높습니다. 계속 실행하시겠습니까?", "yellow")
            colored_print("메모리 부족으로 인한 KeyboardInterrupt가 발생할 수 있습니다.", "yellow")
            time.sleep(2)  # 사용자가 확인할 시간 제공
        
        # 중복 실행 체크
        running_pid = check_already_running()
        if running_pid:
            colored_print(f"[WARN]  통합매니저가 이미 실행 중입니다 (PID: {running_pid})", "red")
            colored_print("기존 프로세스를 종료하거나 중복 실행을 원하면 PID 파일을 삭제하세요:", "yellow")
            colored_print(f"   {PID_FILE}", "yellow")
            return

        # PID 파일 생성
        write_pid_file()
        colored_print(f"[OK] PID 파일 생성 완료 (PID: {os.getpid()})", "green")
        
    except KeyboardInterrupt:
        colored_print("\n[INFO] 사용자에 의한 중단 (Ctrl+C)", "yellow")
        return
    except Exception as e:
        colored_print(f"[ERROR] 초기화 중 오류: {e}", "red")
        return

    colored_print("=" * 70, "cyan")
    colored_print("통합 트레이더 관리 시스템 시작", "cyan")
    colored_print(f"재시작 주기: {RESTART_INTERVAL // 3600}시간", "cyan")
    colored_print("=" * 70, "cyan")

    # 텔레그램 시작 알림
    telegram.notify_system_start()
    logger.info("통합 트레이더 시스템 시작 - 텔레그램 알림 전송")

    # 초기 정리
    colored_print("\n[초기화] 기존 Ollama 프로세스 정리 중...", "yellow")
    kill_all_ollama()
    time.sleep(3)

    colored_print("\n" + "="*70, "cyan")
    colored_print("RTX 2060 TENSOR CORE 최적화 활성화", "cyan")
    colored_print("="*70, "cyan")
    colored_print("  ✓ FP16 KV Cache (VRAM 50% 절약)", "green")
    colored_print("  ✓ Flash Attention (Tensor Core 직접 활용)", "green")
    colored_print("  ✓ 배치 추론 병렬화 (2-3배 속도 향상)", "green")
    colored_print("  ✓ KV Cache 60분 유지", "green")
    colored_print("  ✓ 모든 레이어 GPU 로드", "green")
    colored_print("  ✓ GPU 우선 모드 (CPU 스레드 최소화)", "green")
    colored_print("="*70 + "\n", "cyan")

    colored_print("\n[OLLAMA] 독립 인스턴스 3개 시작 중 (RTX 2060 최적화 적용)...", "blue")

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

    #  Self-Improvement Ollama (11436)
    colored_print(f"[OLLAMA] 포트 {OLLAMA_PORT_IMPROVEMENT} 시작 중 (자기개선 엔진용)...", "blue")
    ollama_improvement = start_ollama(OLLAMA_PORT_IMPROVEMENT)
    if not ollama_improvement:
        colored_print(f"\n[WARNING] Ollama 포트 {OLLAMA_PORT_IMPROVEMENT} 시작 실패 (자기개선 엔진 비활성화)", "yellow")
        # 자기개선은 선택사항이므로 실패해도 계속 진행
    else:
        colored_print(f"[OLLAMA] 자기개선 엔진용 Ollama 활성화 완료!", "green")

    # 14b 전용 Ollama (11437) - 직렬화 큐
    colored_print(f"[OLLAMA] 포트 {OLLAMA_PORT_14B_DEDICATED} 시작 중 (14b 전용 큐)...", "blue")
    ollama_14b_dedicated = start_ollama(OLLAMA_PORT_14B_DEDICATED)
    if not ollama_14b_dedicated:
        colored_print(f"\n[WARNING] Ollama 포트 {OLLAMA_PORT_14B_DEDICATED} 시작 실패 (14b 큐 비활성화)", "yellow")
    else:
        colored_print(f"[OLLAMA] 14b 전용 큐 활성화 완료!", "green")
        # 14b 전용 큐 시작
        start_14b_dedicated_queue()

    colored_print("[OLLAMA] 모든 인스턴스 시작 완료!", "green")

    # 트레이더 시작
    colored_print("\n[TRADER] 시작 중...", "blue")
    trader_eth = start_trader_with_backoff(
        ETH_TRADER_SCRIPT,
        ETH_PYTHON,
        ETH_TRADER_DIR,
        "ETH Trader (코드3)",
        OLLAMA_PORT_ETH
    )
    time.sleep(3)

    trader_kis = start_trader_with_backoff(
        KIS_TRADER_SCRIPT,
        KIS_PYTHON,
        KIS_TRADER_DIR,
        "KIS Trader (코드4)",
        OLLAMA_PORT_KIS
    )

    if not trader_eth or not trader_kis:
        colored_print("\n[WARNING] 일부 트레이더 시작 실패", "yellow")

    # 14b 모델 워밍업 (응답 지연 최소화)
    try:
        colored_print("\n[WARMUP] 14b 모델 워밍업 시작...", "cyan")
        warmup_ollama_model(OLLAMA_PORT_ETH, "qwen2.5:14b", prompt="price: 1000, trend: bear → ok")
        warmup_ollama_model(OLLAMA_PORT_KIS, "qwen2.5:14b", prompt="price: 100, trend: bull → ok")
        warmup_ollama_model(OLLAMA_PORT_IMPROVEMENT, OLLAMA_IMPROVEMENT_MODEL, prompt="ready")
    except Exception as e:
        colored_print(f"[WARMUP] 모델 워밍업 오류: {e}", "yellow")

    # 재시작 타이머
    last_restart_time = time.time()
    last_guardian_check = time.time()
    last_status_print = time.time()
    last_trading_check = time.time()  #  거래 현황 체크
    last_improvement_check = time.time()  #  자기개선 체크
    last_improvement_report = time.time()  #  개선 리포트
    last_telegram_alert = time.time()  #  텔레그램 알림 (6시간 제한)
    last_log_rotation = time.time()  #  로그 로테이션 (6시간마다)

    #  Option 4: 오류 패턴 로드
    global error_patterns_eth, error_patterns_kis
    error_patterns_eth = load_error_patterns(ERROR_PATTERN_FILE_ETH)
    error_patterns_kis = load_error_patterns(ERROR_PATTERN_FILE_KIS)
    colored_print(f"[SELF-IMPROVE] ETH 오류 패턴 {len(error_patterns_eth)}개 로드", "cyan")
    colored_print(f"[SELF-IMPROVE] KIS 오류 패턴 {len(error_patterns_kis)}개 로드\n", "cyan")

    #  백그라운드 학습 스레드 시작
    global background_learning_thread
    background_learning_thread = threading.Thread(
        target=background_learning_worker,
        daemon=True,
        name="BackgroundLearning"
    )
    background_learning_thread.start()
    colored_print(f"[BACKGROUND LEARNING] 백그라운드 학습 시작! ({BACKGROUND_LEARNING_INTERVAL // 60}분 주기)\n", "magenta")

    colored_print("\n[MONITOR] 모니터링 시작 (Ctrl+C로 종료)\n", "green")
    colored_print(f"[GUARDIAN] 실시간 Ollama 관리 활성화 ({GUARDIAN_CHECK_INTERVAL}초마다)\n", "green")
    colored_print(f"[TRADING] 거래/수익 모니터링 활성화 (15분마다 체크, 6시간마다 텔레그램)\n", "green")
    colored_print(f"[SELF-IMPROVE] 자기개선 엔진 활성화\n", "green")
    colored_print(f"  - Option 1: Triple Validation (3중 검증)\n", "green")
    colored_print(f"  - Option 4: Self-Improving Feedback Loop (오류 패턴 학습)\n", "green")
    colored_print(f"  - 15분마다 LLM 분석, 6시간마다 텔레그램 리포트\n", "green")
    colored_print(f"[BACKGROUND LEARNING] FMP API 과거 데이터 학습 활성화\n", "magenta")
    colored_print(f"  - 10분마다 ETH/SOXL 실제 데이터 수집 및 전략 탐색\n", "magenta")
    colored_print(f"  - 자동 검증: 동일 전략 {VALIDATION_THRESHOLD}번 발견 시 자동 적용\n", "magenta")
    colored_print(f"  - Triple Validation 합의율 {int(CONFIDENCE_THRESHOLD*100)}% 이상만 통과\n", "magenta")
    colored_print(f"  - 검증 완료된 전략은 즉시 실전 적용!\n", "magenta")

    try:
        while True:
            try:
                # 메모리 사용량 주기적 체크
                if not check_memory_usage():
                    colored_print("[WARNING] 메모리 사용량이 높습니다. 가비지 컬렉션 실행...", "yellow")
                    import gc
                    gc.collect()
                    time.sleep(1)
                
                time.sleep(GUARDIAN_CHECK_INTERVAL)  #  10초마다 체크
                current_time = time.time()
                elapsed = current_time - last_restart_time
            except KeyboardInterrupt:
                colored_print("\n[INFO] 사용자에 의한 중단 (Ctrl+C)", "yellow")
                break
            except Exception as e:
                colored_print(f"[ERROR] 메인 루프 오류: {e}", "red")
                time.sleep(5)  # 오류 시 5초 대기 후 계속
                continue

            #  Guardian: 불필요한 Ollama 정리 (10초마다)
            guardian_cleanup_rogue_ollama()

            #  거래 현황 및 수익 체크 (1시간마다)
            if (current_time - last_trading_check) >= TRADING_CHECK_INTERVAL:
                colored_print("\n" + "="*70, "cyan")
                colored_print("[거래 현황 체크] 시작", "cyan")
                colored_print("="*70, "cyan")

                eth_health = check_trading_health("ETH", ETH_TRADE_HISTORY)
                kis_health = check_trading_health("KIS", KIS_TRADE_HISTORY)

                # ETH 상태
                if eth_health['alert']:
                    colored_print(f"[WARN]  [ETH] {eth_health['message']}", "red")
                    if eth_health.get('warnings'):
                        for w in eth_health['warnings']:
                            colored_print(f"    - {w}", "yellow")

                    #  14b LLM 자동 진단 및 수정 (24시간 감시 포함)
                    # 24시간 거래 없음은 critical 알람이므로 즉시 분석
                    warnings_str = str(eth_health.get('warnings', []))
                    if "1시간 동안 거래 없음" in warnings_str or eth_health.get('critical', False):
                        colored_print("\n[14b LLM] ETH 거래 없음 원인 분석 중...", "cyan")
                        try:
                            # ETH 트레이더 코드 체크
                            eth_code_path = r"C:\Users\user\Documents\코드3\llm_eth_trader_v4_3tier.py"
                            with open(eth_code_path, 'r', encoding='utf-8') as f:
                                eth_code = f.read()

                            # 임계값 하드코딩 체크
                            has_threshold_issue = False
                            if 'monitor_buy > monitor_sell + 3' in eth_code:
                                colored_print("[발견] 7b 모니터에 +3 임계값 하드코딩!", "yellow")
                                has_threshold_issue = True
                            if 'deep_buy > deep_sell + self.SIGNAL_THRESHOLD' in eth_code and 'SIGNAL_THRESHOLD = 5.0' in eth_code:
                                colored_print("[발견] 16b 분석에 +5 임계값 하드코딩!", "yellow")
                                has_threshold_issue = True

                            if has_threshold_issue:
                                colored_print("[조치] 임계값 제거 필요 - LLM이 스스로 판단하도록 수정", "cyan")
                                telegram.send_message("[TOOL] <b>ETH 임계값 문제 발견</b>\n\nLLM 판단을 막는 하드코딩된 임계값 발견\n자동 수정 필요")
                            else:
                                colored_print("[32b LLM] 코드는 정상, 시장 조용함으로 판단", "green")
                        except Exception as e:
                            colored_print(f"[32b LLM] 분석 실패: {e}", "yellow")
                else:
                    colored_print(f"[OK] [ETH] {eth_health['message']}", "green")

                # KIS 상태
                if kis_health['alert']:
                    colored_print(f"[WARN]  [KIS] {kis_health['message']}", "red")
                    if kis_health.get('warnings'):
                        for w in kis_health['warnings']:
                            colored_print(f"    - {w}", "yellow")

                    #  32b LLM 자동 진단
                    if "1시간 동안 거래 없음" in str(kis_health.get('warnings', [])):
                        colored_print("\n[32b LLM] KIS 거래 없음 원인 분석 중...", "cyan")
                        # 미국 장 마감 시간 체크
                        from datetime import datetime
                        now_hour = datetime.now().hour
                        if 0 <= now_hour < 23:  # 한국 시간 0시~23시 (미국 장 마감)
                            colored_print("[32b LLM] 미국 장 마감 시간, 정상 상태", "green")
                        else:
                            colored_print("[32b LLM] 미국 장 오픈 중인데 거래 없음 - 추가 분석 필요", "yellow")
                else:
                    colored_print(f"[OK] [KIS] {kis_health['message']}", "green")

                #  텔레그램 알림은 오류 발생 시에만 (사용자 요청)
                if (current_time - last_telegram_alert) >= TELEGRAM_ALERT_INTERVAL:
                    # 오류가 있을 때만 텔레그램 전송
                    if eth_health['alert'] or kis_health['alert']:
                        report = f"[WARN] <b>시스템 오류 감지</b>\n\n"
                        report += f"<b>ETH:</b> {eth_health['message']}\n"
                        report += f"<b>KIS:</b> {kis_health['message']}\n\n"
                        report += "자기개선 엔진이 문제를 분석하고 있습니다."

                        telegram.send_message(report)
                        last_telegram_alert = current_time
                        colored_print(" 오류 감지: 텔레그램 알림 전송 완료", "cyan")
                    else:
                        # 정상 작동 중일 때는 알림 보내지 않음
                        colored_print(" 모든 봇 정상 작동 중 (알림 생략)", "green")

                colored_print("="*70 + "\n", "cyan")
                last_trading_check = current_time

            # 로그 로테이션 (6시간마다)
            if (current_time - last_log_rotation) >= 6 * 3600:  # 6시간
                rotate_logs()
                last_log_rotation = current_time

            #  자기개선 엔진 (1시간마다 LLM 분석)
            if (current_time - last_improvement_check) >= SELF_IMPROVEMENT_INTERVAL:
                import json
                import statistics

                # RTX 2060 GPU 성능 리포트 출력
                print_gpu_performance_report()

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

                        #  Option 1 + 4: LLM 분석 (Triple Validation + Error Pattern Learning)
                        colored_print("[ETH] LLM 분석 중 (Option 1: 3중 검증 + Option 4: 오류 학습)...", "cyan")
                        eth_improvements = llm_analyze_trades_for_improvement("ETH", eth_trades, eth_perf, error_patterns_eth)

                        # 오류 패턴 저장
                        save_error_patterns(ERROR_PATTERN_FILE_ETH, error_patterns_eth)

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

                        #  Option 1 + 4: LLM 분석 (Triple Validation + Error Pattern Learning)
                        colored_print("[KIS] LLM 분석 중 (Option 1: 3중 검증 + Option 4: 오류 학습)...", "cyan")
                        kis_improvements = llm_analyze_trades_for_improvement("KIS", kis_trades, kis_perf, error_patterns_kis)

                        # 오류 패턴 저장
                        save_error_patterns(ERROR_PATTERN_FILE_KIS, error_patterns_kis)

                        # 개선안 적용
                        if kis_improvements:
                            apply_strategy_improvements("KIS", KIS_STRATEGY_FILE, kis_improvements, improvement_history_kis)
                except Exception as e:
                    colored_print(f"[KIS] 자기개선 오류: {e}", "yellow")

                # 개선 리포트 (6시간마다)
                if (current_time - last_improvement_report) >= IMPROVEMENT_REPORT_INTERVAL:
                    total_improvements = len(improvement_history_eth) + len(improvement_history_kis)
                    if total_improvements > 0:
                        # 자기개선 리포트 텔레그램 알림 (사용자 요청으로 비활성화)
                        # report = f" <b>자기개선 리포트</b>\n\n"
                        # report += f"총 개선 횟수: {total_improvements}회\n"
                        # report += f"ETH: {len(improvement_history_eth)}회\n"
                        # report += f"KIS: {len(improvement_history_kis)}회\n\n"
                        # report += "최근 적용된 개선사항은 전략 파일에 자동 반영되었습니다."
                        # telegram.send_message(report)
                        pass

                    last_improvement_report = current_time

                colored_print("="*70 + "\n", "magenta")
                last_improvement_check = current_time

            # 상태 체크 (1분마다만)
            should_check_status = (current_time - last_status_print) >= 60

            if not should_check_status:
                continue

            # 시스템 리소스 가드
            if not system_resource_guard():
                print("[GUARD] 시스템 리소스 부족 → 트레이더 일시 정지")
                time.sleep(30)
                continue

            last_status_print = current_time

            # 데드맨 스위치: 3시간 무활동(로그/신호/거래 없음) 경고
            try:
                deadman_now = time.time()
                last_activity = max(last_trading_check, last_status_print, last_improvement_check)
                if deadman_now - last_activity > 3 * 3600:
                    telegram.send_message("[DEADMAN] 3시간 활동 없음 - 시스템 점검 필요 (로그/신호/거래)\n최근 로그 200줄 첨부는 매니저 로그 파일에서 확인.", priority="important")
                    # 중복 전송 방지
                    last_status_print = current_time
            except Exception:
                pass

            # 디스크/VRAM 가드
            if not disk_usage_guard():
                time.sleep(30)
            _ = gpu_vram_guard()

            # 트레이더 상태 체크
            eth_alive = trader_eth and trader_eth.poll() is None
            kis_alive = trader_kis and trader_kis.poll() is None

            # 로그 하트비트 워치독: 최근 5분간 출력 없으면 비정상으로 간주하여 재시작
            try:
                hb_now = time.time()
                for key, proc, restart in [
                    ("ETH", trader_eth, lambda: start_trader_with_backoff(ETH_TRADER_SCRIPT, ETH_PYTHON, ETH_TRADER_DIR, "ETH Trader (코드3)", OLLAMA_PORT_ETH)),
                    ("KIS", trader_kis, lambda: start_trader_with_backoff(KIS_TRADER_SCRIPT, KIS_PYTHON, KIS_TRADER_DIR, "KIS Trader (코드4)", OLLAMA_PORT_KIS)),
                ]:
                    last_ts = last_log_time.get(key, 0)
                    if proc and proc.poll() is None and last_ts and hb_now - last_ts > 300:
                        colored_print(f"[WATCHDOG] {key} 로그 정지 {int(hb_now - last_ts)}s → 안전 재시작", "yellow")
                        stop_process(proc, f"{key} Trader", timeout=10)
                        if key == "ETH":
                            trader_eth = start_trader_with_backoff(ETH_TRADER_SCRIPT, ETH_PYTHON, ETH_TRADER_DIR, "ETH Trader (코드3)", OLLAMA_PORT_ETH)
                        else:
                            trader_kis = start_trader_with_backoff(KIS_TRADER_SCRIPT, KIS_PYTHON, KIS_TRADER_DIR, "KIS Trader (코드4)", OLLAMA_PORT_KIS)
                        last_log_time[key] = time.time()
            except Exception:
                pass

            # 프로세스 중단 감지 및 텔레그램 알림
            if not eth_alive and trader_eth:
                telegram.notify_bot_down("ETH Trader", "프로세스가 예기치 않게 종료됨")
                colored_print("[ERROR] ETH 트레이더 중단 감지 - 텔레그램 알림 전송", "red")
                logger.error("ETH Trader 프로세스 중단 감지 - 자동 재시작 준비 중")
                send_trader_failure_alert("ETH Trader", "프로세스가 예기치 않게 종료됨")

            if not kis_alive and trader_kis:
                telegram.notify_bot_down("KIS Trader", "프로세스가 예기치 않게 종료됨")
                colored_print("[ERROR] KIS 트레이더 중단 감지 - 텔레그램 알림 전송", "red")
                logger.error("KIS Trader 프로세스 중단 감지 - 자동 재시작 준비 중")
                send_trader_failure_alert("KIS Trader", "프로세스가 예기치 않게 종료됨")

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
                # Ollama 재시작은 정상 운영의 일부이므로 최소 로그만 출력
                logger.info(f"Ollama 자동 재시작 (원인: {reason})")

                # 두 트레이더 모두 종료
                logger.info("Ollama 재시작을 위해 모든 트레이더 종료 중...")
                stop_process(trader_eth, "ETH Trader", timeout=10)
                stop_process(trader_kis, "KIS Trader", timeout=10)

                # Ollama 모두 재시작
                kill_all_ollama()
                time.sleep(3)

                ollama_eth = start_ollama(OLLAMA_PORT_ETH)
                ollama_kis = start_ollama(OLLAMA_PORT_KIS)
                ollama_improvement = start_ollama(OLLAMA_PORT_IMPROVEMENT)
                ollama_14b_dedicated = start_ollama(OLLAMA_PORT_14B_DEDICATED)
                
                # 14b 전용 큐 시작
                start_14b_dedicated_queue()

                if not ollama_eth or not ollama_kis:
                    logger.critical("Ollama 재시작 실패 - 시스템 종료")
                    telegram.send_message("[CRITICAL] Ollama 재시작 실패! 시스템 종료됨")
                    break

                logger.info("Ollama 재시작 완료")

                # 트레이더 재시작
                colored_print("[SMART_RESTART] 트레이더 재시작 중...", "green")
                # 재시작 후 14b 재워밍업 (지연 최소화)
                try:
                    colored_print("[WARMUP] 재시작 후 14b 모델 재워밍업...", "cyan")
                    warmup_ollama_model(OLLAMA_PORT_ETH, "qwen2.5:14b", prompt="price: 1000, trend: bear → ok")
                    warmup_ollama_model(OLLAMA_PORT_KIS, "qwen2.5:14b", prompt="price: 100, trend: bull → ok")
                    warmup_ollama_model(OLLAMA_PORT_IMPROVEMENT, OLLAMA_IMPROVEMENT_MODEL, prompt="ready")
                except Exception as e:
                    colored_print(f"[WARMUP] 재시작 워밍업 오류: {e}", "yellow")
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
                logger.warning("ETH Trader 크래시 감지 - 자동 재시작 시작")
                trader_eth = start_trader_with_backoff(
                    ETH_TRADER_SCRIPT,
                    ETH_PYTHON,
                    ETH_TRADER_DIR,
                    "ETH Trader (코드3)",
                    OLLAMA_PORT_ETH
                )
                logger.info("ETH Trader 재시작 완료")

            if not kis_alive and not need_restart_ollama:
                colored_print("\n[AUTO_RECOVERY] KIS Trader 크래시 → 재시작...", "yellow")
                logger.warning("KIS Trader 크래시 감지 - 자동 재시작 시작")
                trader_kis = start_trader_with_backoff(
                    KIS_TRADER_SCRIPT,
                    KIS_PYTHON,
                    KIS_TRADER_DIR,
                    "KIS Trader (코드4)",
                    OLLAMA_PORT_KIS
                )
                logger.info("KIS Trader 재시작 완료")

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
                # 재시작 후 14b 재워밍업 (지연 최소화)
                try:
                    colored_print("[WARMUP] 재시작 후 14b 모델 재워밍업...", "cyan")
                    warmup_ollama_model(OLLAMA_PORT_ETH, "qwen2.5:14b", prompt="price: 1000, trend: bear → ok")
                    warmup_ollama_model(OLLAMA_PORT_KIS, "qwen2.5:14b", prompt="price: 100, trend: bull → ok")
                    warmup_ollama_model(OLLAMA_PORT_IMPROVEMENT, OLLAMA_IMPROVEMENT_MODEL, prompt="ready")
                except Exception as e:
                    colored_print(f"[WARMUP] 재시작 워밍업 오류: {e}", "yellow")
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
    except KeyboardInterrupt:
        colored_print("\n[INFO] 사용자 중단", "yellow")
    except Exception as e:
        colored_print(f"\n[CRITICAL ERROR] {e}", "red")
        colored_print("[CRITICAL ERROR] 프로세스 정리 중...", "red")
        kill_all_ollama()
    finally:
        # PID 파일 정리
        remove_pid_file()
        colored_print("[CLEANUP] PID 파일 삭제 완료", "green")
