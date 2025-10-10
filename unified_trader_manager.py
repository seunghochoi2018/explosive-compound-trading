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

# 모델 전략 (메모리 최적화)
# 현재: ETH 16b×1 + KIS 16b×1 + Self-Improvement 16b×1 = 24.9GB (안정적 ⭐)
# 향후: 메모리 여유 시 듀얼 앙상블 재적용 가능

# ===== 리소스 모니터링 설정 =====
MAX_MEMORY_MB = 10 * 1024  # Ollama 메모리 상한: 10GB
MAX_CPU_PERCENT = 5.0  # 정상 상태 CPU: 5% 이하
RESPONSE_TIMEOUT = 10  # API 응답 타임아웃: 10초
QUEUE_DETECT_THRESHOLD = 60  # 큐잉 감지: 60초 이상 CPU 0%

# 응답 시간 추적 (최근 10개)
response_times_eth = deque(maxlen=10)
response_times_kis = deque(maxlen=10)

# ⭐ 거래/수익 모니터링 설정
TRADING_CHECK_INTERVAL = 30 * 60  # 30분마다 거래 현황 체크
ETH_TRADE_HISTORY = r"C:\Users\user\Documents\코드3\eth_trade_history.json"
KIS_TRADE_HISTORY = r"C:\Users\user\Documents\코드4\kis_trade_history.json"

# ⭐ 자기개선 엔진 설정 (통합) - 16b 단독 (메모리 최적화)
SELF_IMPROVEMENT_INTERVAL = 30 * 60  # 30분마다 자기 분석
IMPROVEMENT_REPORT_INTERVAL = 6 * 60 * 60  # 6시간마다 텔레그램 리포트
TELEGRAM_ALERT_INTERVAL = 6 * 60 * 60  # 6시간마다만 텔레그램 알림
OLLAMA_IMPROVEMENT_HOST = f"http://127.0.0.1:{OLLAMA_PORT_IMPROVEMENT}"
OLLAMA_IMPROVEMENT_MODEL = "deepseek-coder-v2:16b"  # 단독 모델
OLLAMA_IMPROVEMENT_TIMEOUT = 300  # ⭐ 5분으로 증가 (Triple Validation용)

# 자기개선 상태 추적
improvement_history_eth = []
improvement_history_kis = []
ETH_STRATEGY_FILE = r"C:\Users\user\Documents\코드3\eth_current_strategy.json"
KIS_STRATEGY_FILE = r"C:\Users\user\Documents\코드4\kis_current_strategy.json"

# ⭐ Option 4: Self-Improving Feedback Loop - 오류 패턴 학습
error_patterns_eth = []  # ETH 봇의 실패 패턴 (최근 100건)
error_patterns_kis = []  # KIS 봇의 실패 패턴 (최근 100건)
ERROR_PATTERN_FILE_ETH = r"C:\Users\user\Documents\코드3\eth_error_patterns.json"
ERROR_PATTERN_FILE_KIS = r"C:\Users\user\Documents\코드4\kis_error_patterns.json"

# ⭐ 백그라운드 학습 설정
FMP_API_KEY = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"  # FMP API 키
BACKGROUND_LEARNING_INTERVAL = 10 * 60  # 10분마다 백그라운드 학습
HISTORICAL_DATA_DAYS = 90  # 과거 90일간 데이터 학습 (충분한 데이터 확보)
learning_session_count = 0  # 학습 세션 카운터
background_learning_thread = None  # 백그라운드 학습 스레드

# ⭐ 자동 검증 및 적용 설정
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

    colored_print(f"[BACKGROUND LEARNING #{learning_session_count}] ✅ 새로운 인사이트 발견!", "green")
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
    ⭐ 자동 검증 및 적용 시스템

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

        colored_print(f"[{trader_name}] 🔍 전략 '{strategy_type}' 발견 횟수: {current_count}/{VALIDATION_THRESHOLD}", "cyan")

        # 검증 완료 조건: N번 이상 발견
        if current_count >= VALIDATION_THRESHOLD:
            colored_print(f"[{trader_name}] ✅ 전략 '{strategy_type}' 검증 완료! ({current_count}번 발견)", "green")
            colored_print(f"[{trader_name}] 🚀 자동 적용 시작...", "green")

            # 자동 적용
            result = apply_strategy_improvements(
                trader_name,
                strategy_file,
                [{'type': strategy_type, 'source': f'AUTO_VALIDATED_{current_count}x'}],
                improvement_history
            )

            if result:
                applied.extend(result)
                colored_print(f"[{trader_name}] 🎉 전략 '{strategy_type}' 자동 적용 완료!", "green")

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
                    colored_print(f"[ETH] 💡 {len(eth_strategies)}개 새로운 전략 발견!", "cyan")

                    # ⭐ 자동 검증 및 적용 시스템 실행
                    global validated_strategies_eth
                    applied = auto_validate_and_apply_strategy(
                        "ETH",
                        eth_strategies,
                        validated_strategies_eth,
                        ETH_STRATEGY_FILE,
                        improvement_history_eth
                    )

                    if applied:
                        colored_print(f"[ETH] 🎉 {len(applied)}개 전략 자동 적용 완료!", "green")

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
                    colored_print(f"[KIS] 💡 {len(soxl_strategies)}개 새로운 전략 발견!", "cyan")

                    # ⭐ 자동 검증 및 적용 시스템 실행
                    global validated_strategies_kis
                    applied = auto_validate_and_apply_strategy(
                        "KIS",
                        soxl_strategies,
                        validated_strategies_kis,
                        KIS_STRATEGY_FILE,
                        improvement_history_kis
                    )

                    if applied:
                        colored_print(f"[KIS] 🎉 {len(applied)}개 전략 자동 적용 완료!", "green")

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

    # ⚠️ Ollama는 각 모델마다 별도의 runner 프로세스를 생성함
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
    """⭐ LLM에게 분석 요청 (11436 포트) - 16b 단독"""
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

def ask_llm_triple_validation(primary_prompt: str, validator1_prompt: str, validator2_prompt: str) -> dict:
    """
    ⭐ Option 1: Triple Validation System

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

    colored_print("[TRIPLE VALIDATION] 3중 검증 시작...", "cyan")

    # 1. Primary 분석 (주 분석기)
    colored_print("  [1/3] Primary 분석 중...", "cyan")
    primary_start = time.time()
    primary_response = ask_llm_for_analysis(primary_prompt)
    primary_time = time.time() - primary_start
    colored_print(f"  [1/3] Primary 완료 ({primary_time:.1f}초)", "green")

    # 2. Validator 1 분석 (비판적 검증)
    colored_print("  [2/3] Validator #1 (비판적 검증) 분석 중...", "cyan")
    val1_start = time.time()
    validator1_response = ask_llm_for_analysis(validator1_prompt)
    val1_time = time.time() - val1_start
    colored_print(f"  [2/3] Validator #1 완료 ({val1_time:.1f}초)", "green")

    # 3. Validator 2 분석 (반대 입장)
    colored_print("  [3/3] Validator #2 (반대 입장) 분석 중...", "cyan")
    val2_start = time.time()
    validator2_response = ask_llm_for_analysis(validator2_prompt)
    val2_time = time.time() - val2_start
    colored_print(f"  [3/3] Validator #2 완료 ({val2_time:.1f}초)", "green")

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

    colored_print(f"[TRIPLE VALIDATION] 합의 여부: {'✅ 동의 {}/3'.format(agreement_count) if consensus else '❌ 불일치'}",
                  "green" if consensus else "yellow")

    total_time = time.time() - primary_start
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
    """⭐ Option 4: 저장된 오류 패턴 로드"""
    import json
    try:
        with open(error_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_error_patterns(error_file: str, patterns: list):
    """⭐ Option 4: 오류 패턴 저장 (최근 100건만)"""
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
    ⭐ Option 4: Self-Improving Feedback Loop - 손실 거래에서 패턴 학습

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
        colored_print(f"[{trader_name}] 🔍 패턴 발견: {pattern['description']}", "yellow")

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
        colored_print(f"[{trader_name}] 🔍 패턴 발견: {pattern['description']}", "yellow")

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
        colored_print(f"[{trader_name}] 🔍 패턴 발견: {pattern['description']}", "yellow")

    # 기존 패턴에 추가
    error_patterns.extend(new_patterns)

    return new_patterns

def llm_analyze_trades_for_improvement(trader_name, trades, performance, error_patterns=None):
    """⭐ LLM이 거래 패턴 분석 및 개선안 제시 (Option 1 + Option 4 통합)"""
    import json

    if len(trades) < 5:
        return []

    # ⭐ Option 4: 먼저 오류 패턴 자동 학습
    if error_patterns is not None:
        new_patterns = analyze_losing_trades_for_patterns(trader_name, trades, error_patterns)
        if new_patterns:
            colored_print(f"[{trader_name}] 📚 새로운 오류 패턴 {len(new_patterns)}개 학습 완료", "cyan")

    # 최근 20건만 분석
    recent_trades = trades[-20:]

    # 거래 요약
    trades_summary = []
    for t in recent_trades:
        summary = f"- {t.get('action', '?')}: {t.get('profit_pct', 0):+.2f}%, 보유 {t.get('hold_minutes', 0):.0f}분, 트렌드 {t.get('trend', '?')}"
        trades_summary.append(summary)

    trades_text = "\n".join(trades_summary)

    # ⭐ Option 4: 오류 패턴을 프롬프트에 포함
    error_context = ""
    if error_patterns and len(error_patterns) > 0:
        recent_errors = error_patterns[-5:]  # 최근 5개만
        error_lines = []
        for err in recent_errors:
            error_lines.append(f"- {err.get('description', '알 수 없음')}")
        error_context = "\n\n## ⚠️ 최근 발견된 실패 패턴\n" + "\n".join(error_lines)
        error_context += "\n\n위 패턴을 고려하여 개선안을 제시하세요."

    # ⭐ Option 1: Triple Validation - 3가지 프롬프트 생성

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

    # ⭐ Triple Validation 실행
    validation_result = ask_llm_triple_validation(primary_prompt, validator1_prompt, validator2_prompt)

    if not validation_result['primary_response']:
        return []

    # 합의가 있을 때만 분석 결과 사용
    if validation_result['consensus']:
        llm_response = validation_result['final_decision']
        colored_print(f"[{trader_name}] ✅ 3중 검증 합의 ({validation_result['agreement_count']}/3)", "green")
        colored_print(f"[{trader_name}] [LLM 인사이트] {llm_response[:150]}...", "magenta")
    else:
        colored_print(f"[{trader_name}] ⚠️ 3중 검증 불일치 - 개선안 보류", "yellow")
        return []  # 합의 없으면 개선 안 함 (안전)

    # 간단한 키워드 기반 개선안 추출
    improvements = []

    if "횡보" in llm_response or "neutral" in llm_response.lower():
        improvements.append({'type': 'sideways_block', 'source': 'LLM_TRIPLE'})

    if ("손절" in llm_response or "stop" in llm_response.lower()) and ("늦" in llm_response or "tight" in llm_response.lower()):
        improvements.append({'type': 'tighten_stop_loss', 'source': 'LLM_TRIPLE'})

    if "보유" in llm_response or "hold" in llm_response.lower():
        improvements.append({'type': 'reduce_hold_time', 'source': 'LLM_TRIPLE'})

    # ⭐ Option 4: 오류 패턴 기반 개선안 추가
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

            # ⭐ Option 4: 오류 패턴 기반 개선안
            elif imp_type == 'enforce_trend_following':
                strategy['trend_check_enabled'] = True
                strategy['block_counter_trend'] = True  # 추세 역행 완전 차단
                applied.append(f"추세 역행 진입 차단 ({source})")
                colored_print(f"[{trader_name}] [개선 적용] 추세 역행 진입 차단 (출처: {source})", "green")

            elif imp_type == 'increase_min_confidence':
                old_conf = strategy.get('min_confidence', 75)
                new_conf = min(85, old_conf + 5)  # 최대 85%까지
                strategy['min_confidence'] = new_conf
                applied.append(f"최소 신뢰도 {old_conf}% → {new_conf}% ({source})")
                colored_print(f"[{trader_name}] [개선 적용] 최소 신뢰도 {old_conf}% → {new_conf}% (출처: {source})", "green")

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
    last_telegram_alert = time.time()  # ⭐ 텔레그램 알림 (6시간 제한)

    # ⭐ Option 4: 오류 패턴 로드
    global error_patterns_eth, error_patterns_kis
    error_patterns_eth = load_error_patterns(ERROR_PATTERN_FILE_ETH)
    error_patterns_kis = load_error_patterns(ERROR_PATTERN_FILE_KIS)
    colored_print(f"[SELF-IMPROVE] ETH 오류 패턴 {len(error_patterns_eth)}개 로드", "cyan")
    colored_print(f"[SELF-IMPROVE] KIS 오류 패턴 {len(error_patterns_kis)}개 로드\n", "cyan")

    # ⭐ 백그라운드 학습 스레드 시작
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
    colored_print(f"[TRADING] 거래/수익 모니터링 활성화 (30분마다 체크, 6시간마다 텔레그램)\n", "green")
    colored_print(f"[SELF-IMPROVE] 자기개선 엔진 활성화\n", "green")
    colored_print(f"  - Option 1: Triple Validation (3중 검증)\n", "green")
    colored_print(f"  - Option 4: Self-Improving Feedback Loop (오류 패턴 학습)\n", "green")
    colored_print(f"  - 30분마다 LLM 분석, 6시간마다 텔레그램 리포트\n", "green")
    colored_print(f"[BACKGROUND LEARNING] FMP API 과거 데이터 학습 활성화\n", "magenta")
    colored_print(f"  - 10분마다 ETH/SOXL 실제 데이터 수집 및 전략 탐색\n", "magenta")
    colored_print(f"  - 자동 검증: 동일 전략 {VALIDATION_THRESHOLD}번 발견 시 자동 적용\n", "magenta")
    colored_print(f"  - Triple Validation 합의율 {int(CONFIDENCE_THRESHOLD*100)}% 이상만 통과\n", "magenta")
    colored_print(f"  - 검증 완료된 전략은 즉시 실전 적용!\n", "magenta")

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
                else:
                    colored_print(f"✅ [ETH] {eth_health['message']}", "green")

                # KIS 상태
                if kis_health['alert']:
                    colored_print(f"⚠️  [KIS] {kis_health['message']}", "red")
                    if kis_health.get('warnings'):
                        for w in kis_health['warnings']:
                            colored_print(f"    - {w}", "yellow")
                else:
                    colored_print(f"✅ [KIS] {kis_health['message']}", "green")

                # ⭐ 텔레그램 알림은 6시간마다만
                if (current_time - last_telegram_alert) >= TELEGRAM_ALERT_INTERVAL:
                    # 종합 리포트 텔레그램 전송
                    report = f"📊 <b>거래 현황 리포트</b>\n\n"
                    report += f"<b>ETH:</b> {eth_health['message']}\n"
                    report += f"<b>KIS:</b> {kis_health['message']}\n\n"

                    if eth_health['alert'] or kis_health['alert']:
                        report += "⚠️ 문제 감지 - 자기개선 엔진이 분석 중입니다"
                    else:
                        report += "✅ 모든 봇 정상 작동 중"

                    telegram.send_message(report)
                    last_telegram_alert = current_time
                    colored_print("📱 텔레그램 알림 전송 완료 (다음 알림: 6시간 후)", "cyan")
                else:
                    time_until_next = (TELEGRAM_ALERT_INTERVAL - (current_time - last_telegram_alert)) / 3600
                    colored_print(f"📱 텔레그램 알림 생략 (다음 알림: {time_until_next:.1f}시간 후)", "yellow")

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

                        # ⭐ Option 1 + 4: LLM 분석 (Triple Validation + Error Pattern Learning)
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

                        # ⭐ Option 1 + 4: LLM 분석 (Triple Validation + Error Pattern Learning)
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
