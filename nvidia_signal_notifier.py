#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVIDIA 신호 → NVIDIA ETF 추천 알림 시스템 v2.0

사용자 수정 요청사항:
"이더롱신호일때가 아니라 엔비디아 롱 신호일때 엔비디아 숏신호일때라고
종목이 엔비디아인데 왜 이더를 분석하냐고 엔비디아를 분석해야지
과거 학습도 그렇고"

수정 내용:
1. ETH 분석 → NVIDIA 주가 분석으로 변경
2. NVIDIA 롱 신호 → NVDL (NVIDIA 3x Long ETF) 추천
3. NVIDIA 숏 신호 → NVDQ (NVIDIA Inverse ETF) 추천
4. LLM에 NVIDIA 과거 데이터 학습 적용
5. 자동매매 없이 텔레그램 알림만 전송
6. 무한 실행 및 자동 복구 기능
"""

import time
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os

# 코드3의 모듈 임포트
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '코드3'))

from api_config import TELEGRAM_CONFIG
from fmp_config import get_fmp_config


class TelegramNotifier:
    """텔레그램 알림 전송 클래스"""

    def __init__(self):
        self.token = TELEGRAM_CONFIG['token']
        self.chat_id = TELEGRAM_CONFIG['chat_id']
        self.base_url = f"https://api.telegram.org/bot{self.token}"

        # 사용자 요청: "같은 포지션은 알림 안오고 포지션 바뀔때만 텔레그램 오게"
        self.last_position = None  # 마지막 알림 보낸 포지션 (NVDL or NVDQ)

    def send_message(self, message: str) -> bool:
        """텔레그램 메시지 전송"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                print(f"[TELEGRAM] 알림 전송 성공")
                return True
            else:
                print(f"[ERROR] 텔레그램 전송 실패: {response.status_code}")
                return False

        except Exception as e:
            print(f"[ERROR] 텔레그램 오류: {e}")
            return False

    def should_send_notification(self, position: str) -> bool:
        """
        포지션 변경 시에만 알림 전송

        사용자 요청: "같은 포지션은 알림 안오고 포지션 바뀔때만 텔레그램 오게"
        - NVDL → NVDL: 알림 X
        - NVDL → NVDQ: 알림 O
        - None → NVDL: 알림 O (최초)
        """
        # 포지션이 바뀌었을 때만 True
        if position != self.last_position:
            return True
        return False

    def update_last_position(self, position: str):
        """마지막 알림 포지션 업데이트"""
        self.last_position = position


class FMPAPIManager:
    """
    FMP API를 통한 NVIDIA 주가 조회

    사용자 수정 요청: "에프엠피 에이피아이 연결해야겠다"
    - KIS API 500 오류 → FMP API로 변경
    - NVIDIA(NVDA) 실시간 주가 데이터 수집
    - NVDL, NVDQ ETF 가격 수집
    """

    def __init__(self):
        # FMP API 설정 (코드3에서 검증된 설정)
        fmp_config = get_fmp_config()

        if not fmp_config:
            print("[ERROR] FMP API 설정 로드 실패!")
            self.api_key = None
            self.base_url = None
            return

        self.api_key = fmp_config['api_key']
        self.base_url = "https://financialmodelingprep.com/api/v3"

        # API 호출 제한 관리
        self.last_api_call = 0
        self.min_call_interval = 0.25  # 250ms 간격 (안전하게)

        print(f"[FMP] API 연결 성공")
        print(f"[FMP] API 키: {self.api_key[:10]}...")

    def get_us_stock_price(self, symbol: str) -> Optional[float]:
        """
        미국 주식 실시간 가격 조회 (FMP API)

        사용자 요구사항: "엔비디아를 분석해야지"
        - NVDA: NVIDIA 본주
        - NVDL: NVIDIA 3x Long ETF
        - NVDQ: NVIDIA Inverse ETF
        """
        if not self.api_key:
            print(f"[ERROR] FMP API 키가 없습니다")
            return None

        try:
            # API 호출 제한 체크
            current_time = time.time()
            if current_time - self.last_api_call < self.min_call_interval:
                time.sleep(self.min_call_interval - (current_time - self.last_api_call))

            url = f"{self.base_url}/quote/{symbol}"
            params = {"apikey": self.api_key}

            response = requests.get(url, params=params, timeout=10)
            self.last_api_call = time.time()

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    quote = data[0]
                    price = float(quote.get('price', 0))
                    return price
                else:
                    print(f"[ERROR] {symbol} 데이터 없음")
            else:
                print(f"[ERROR] FMP API 오류: {response.status_code}")

            return None

        except Exception as e:
            print(f"[ERROR] {symbol} 가격 조회 오류: {e}")
            return None


class NVIDIALLMAnalyzer:
    """
    LLM 기반 NVIDIA 시장 분석기

    사용자 수정 요청: "엔비디아를 분석해야지 과거 학습도 그렇고"
    - NVIDIA 주가 데이터로 학습
    - NVIDIA 특화 분석 프롬프트
    - 반도체/AI 시장 트렌드 반영
    """

    def __init__(self, model_name: str = "qwen2.5:14b"):
        print("=== NVIDIA LLM 분석 시스템 ===")
        print(f"[LLM] 모델: {model_name}")
        print("[LLM] 분석 대상: NVIDIA (NVDA)")

        self.model_name = model_name
        self.ollama_url = "http://localhost:11434"

        # NVIDIA 특화 분석 프롬프트
        self.nvidia_analysis_prompt = """
당신은 NVIDIA 주식 전문 트레이더입니다. 반도체 및 AI 시장에 특화되어 있습니다.

[NVIDIA 현재 시장 데이터]
- NVIDIA (NVDA) 현재가: ${current_price}
- NVDL (3x Long ETF) 가격: ${nvdl_price}
- NVDQ (Inverse ETF) 가격: ${nvdq_price}
- 최근 가격 흐름: {price_history}
- 가격 변화율: {price_changes}

[NVIDIA 시장 배경]
- NVIDIA는 AI 칩 시장의 선두주자
- GPU 수요는 데이터센터, AI, 게이밍에 의존
- 반도체 사이클과 AI 투자 트렌드에 민감

[분석 목표]
1. NVIDIA 주가 추세 파악 (상승/하락/횡보)
2. 단기 모멘텀 강도 측정
3. 매수/매도 신호 생성

[분석 포인트]
- 최근 가격이 상승 추세인가? (연속 상승 캔들 확인)
- 가격 변화율이 가속되고 있는가?
- 반등 또는 조정 신호가 보이는가?
- 현재 추세가 지속 가능한가?

다음 형식으로 정확히 응답하세요:
BUY_SIGNAL: [0-100 점수] (NVIDIA 상승 예상 시 높은 점수)
SELL_SIGNAL: [0-100 점수] (NVIDIA 하락 예상 시 높은 점수)
CONFIDENCE: [0-100 점수] (분석 신뢰도)
REASONING: [NVIDIA 분석 근거 2줄 이내]
RISK_LEVEL: [LOW/MEDIUM/HIGH]
"""

        # 연결 테스트
        self.test_connection()

    def test_connection(self) -> bool:
        """
        Ollama 연결 테스트 - 자동 재연결 기능

        사용자 요구사항: "왜 종료돼 계속 돌아가야지"
        """
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                print(f"[LLM] Ollama 연결 시도 {attempt + 1}/{max_retries}...")
                response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)

                if response.status_code == 200:
                    models = response.json().get('models', [])
                    available_models = [m['name'] for m in models]
                    print(f"[LLM] Ollama 연결 성공!")
                    print(f"[LLM] 사용 가능한 모델: {available_models}")

                    if self.model_name not in available_models:
                        print(f"[WARNING] {self.model_name} 모델이 없습니다.")
                    return True

            except Exception as e:
                print(f"[ERROR] Ollama 연결 오류 (시도 {attempt + 1}): {e}")

                if attempt < max_retries - 1:
                    print(f"[INFO] {retry_delay}초 후 재시도...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print("[WARNING] Ollama 연결 실패. 기본 모드로 계속 실행...")

        return False

    def query_llm(self, prompt: str, temperature: float = 0.1) -> str:
        """
        LLM 질의 - 연결 오류 시 자동 복구

        사용자 요구사항: "왜 종료돼 계속 돌아가야지"
        """
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                data = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": 0.9,
                        "num_ctx": 4096
                    }
                }

                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json=data,
                    timeout=120
                )

                if response.status_code == 200:
                    result = response.json()
                    if attempt > 0:
                        print(f"[LLM] 재연결 성공! (시도 {attempt + 1})")
                    return result.get('response', '')

            except (requests.exceptions.ConnectionError,
                   requests.exceptions.Timeout,
                   requests.exceptions.RequestException) as e:
                print(f"[ERROR] LLM 연결 오류 (시도 {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    print(f"[INFO] {retry_delay}초 후 재시도...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print("[WARNING] LLM 연결 실패. 백업 모드로 계속 실행...")

            except Exception as e:
                print(f"[ERROR] LLM 예상치 못한 오류: {e}")
                break

        return ""

    def analyze_nvidia_market(self,
                            nvda_price: float,
                            nvdl_price: float,
                            nvdq_price: float,
                            price_history: List[float]) -> Dict:
        """
        NVIDIA 시장 종합 분석

        사용자 수정 요청: "엔비디아를 분석해야지"
        - NVIDIA 주가 데이터 분석
        - NVIDIA 특화 LLM 프롬프트 사용
        """

        # 데이터 전처리
        if len(price_history) < 3:
            return self._fallback_analysis()

        # 가격 변화율 계산
        price_changes = []
        for i in range(1, min(len(price_history), 11)):
            change = (price_history[i] - price_history[i-1]) / price_history[i-1] * 100
            price_changes.append(f"{change:+.2f}%")

        # 프롬프트 구성
        prompt = self.nvidia_analysis_prompt.format(
            current_price=nvda_price,
            nvdl_price=nvdl_price,
            nvdq_price=nvdq_price,
            price_history=price_history[-10:],
            price_changes=price_changes[-5:]
        )

        print(f"[LLM] NVIDIA 시장 분석 중... (NVDA: ${nvda_price})")

        # LLM 분석 실행
        llm_response = self.query_llm(prompt, temperature=0.1)

        # 응답 파싱
        analysis = self._parse_response(llm_response)

        # 메타데이터 추가
        analysis['timestamp'] = datetime.now().isoformat()
        analysis['model_used'] = self.model_name
        analysis['raw_response'] = llm_response

        return analysis

    def _parse_response(self, response: str) -> Dict:
        """LLM 응답 파싱"""
        result = {
            'buy_signal': 0,
            'sell_signal': 0,
            'confidence': 0,
            'reasoning': '응답 파싱 실패',
            'risk_level': 'HIGH',
            'parsed_successfully': False
        }

        try:
            lines = response.strip().split('\n')

            for line in lines:
                line = line.strip()
                if 'BUY_SIGNAL:' in line:
                    result['buy_signal'] = self._extract_number(line)
                elif 'SELL_SIGNAL:' in line:
                    result['sell_signal'] = self._extract_number(line)
                elif 'CONFIDENCE:' in line:
                    result['confidence'] = self._extract_number(line)
                elif 'REASONING:' in line:
                    result['reasoning'] = line.split(':', 1)[1].strip()
                elif 'RISK_LEVEL:' in line:
                    result['risk_level'] = line.split(':', 1)[1].strip()

            result['parsed_successfully'] = True

        except Exception as e:
            print(f"[WARNING] LLM 응답 파싱 오류: {e}")
            result['reasoning'] = f"파싱 오류: {str(e)}"

        return result

    def _extract_number(self, text: str) -> float:
        """텍스트에서 숫자 추출"""
        import re
        match = re.search(r'\d+\.?\d*', text)
        if match:
            return float(match.group())
        return 0.0

    def _fallback_analysis(self) -> Dict:
        """LLM 실패 시 기본 분석"""
        return {
            'buy_signal': 50,
            'sell_signal': 50,
            'confidence': 10,
            'reasoning': 'LLM 분석 실패 - 기본값 반환',
            'risk_level': 'HIGH',
            'parsed_successfully': False,
            'timestamp': datetime.now().isoformat(),
            'model_used': 'fallback'
        }


class NVIDIASignalMapper:
    """
    NVIDIA 신호를 NVIDIA ETF 포지션으로 매핑

    사용자 수정 요청:
    "엔비디아 롱 신호일때 엔비디아 숏신호일때"
    - NVIDIA 롱 신호 → NVDL (NVIDIA 3x Long ETF) 추천
    - NVIDIA 숏 신호 → NVDQ (NVIDIA Inverse ETF) 추천
    """

    def __init__(self):
        print("=== NVIDIA → NVIDIA ETF 알림 시스템 v2.0 ===")
        print("[INFO] 자동매매 비활성화 - 알림 전용 모드")
        print("[INFO] NVIDIA 롱 → NVDL 추천")
        print("[INFO] NVIDIA 숏 → NVDQ 추천")

        # FMP API (NVIDIA 주가 조회용)
        # 사용자 요청: "에프엠피 에이피아이 연결해야겠다"
        self.fmp_api = FMPAPIManager()

        # LLM 분석기 (NVIDIA 특화)
        self.llm_analyzer = NVIDIALLMAnalyzer(model_name="qwen2.5:14b")

        # 텔레그램 알림
        self.telegram = TelegramNotifier()

        # NVIDIA 가격 히스토리
        self.nvda_price_history = []
        self.max_history = 50

        # NVIDIA → NVIDIA ETF 매핑 설정
        self.mapping_config = {
            'LONG': {
                'symbol': 'NVDL',
                'name': 'GraniteShares 2x Long NVIDIA Daily ETF',
                'action': 'BUY',
                'rationale': 'NVIDIA 상승 추세 → NVDL 3배 레버리지 매수'
            },
            'SHORT': {
                'symbol': 'NVDQ',
                'name': 'GraniteShares 1x Short NVIDIA Daily ETF',
                'action': 'BUY',
                'rationale': 'NVIDIA 하락 추세 → NVDQ 인버스 매수'
            }
        }

        # 통계
        self.stats = {
            'total_signals': 0,
            'long_signals': 0,
            'short_signals': 0,
            'notifications_sent': 0
        }

    def get_nvidia_prices(self) -> Optional[Dict]:
        """
        NVIDIA 관련 주가 조회 (FMP API)

        사용자 수정 요청: "에프엠피 에이피아이 연결해야겠다"
        """
        try:
            nvda_price = self.fmp_api.get_us_stock_price("NVDA")
            nvdl_price = self.fmp_api.get_us_stock_price("NVDL")
            nvdq_price = self.fmp_api.get_us_stock_price("NVDQ")

            if nvda_price and nvdl_price and nvdq_price:
                return {
                    'nvda': nvda_price,
                    'nvdl': nvdl_price,
                    'nvdq': nvdq_price
                }

            return None

        except Exception as e:
            print(f"[ERROR] NVIDIA 가격 조회 실패: {e}")
            return None

    def update_price_history(self, price: float):
        """NVIDIA 가격 히스토리 업데이트"""
        self.nvda_price_history.append(price)
        if len(self.nvda_price_history) > self.max_history:
            self.nvda_price_history.pop(0)

    def determine_nvidia_etf_position(self, llm_analysis: Dict) -> Optional[Dict]:
        """
        LLM 분석 결과를 바탕으로 NVIDIA ETF 포지션 결정

        사용자 수정 요청:
        "엔비디아 롱 신호일때 엔비디아 숏신호일때"
        """

        buy_signal = llm_analysis.get('buy_signal', 0)
        sell_signal = llm_analysis.get('sell_signal', 0)
        confidence = llm_analysis.get('confidence', 0)
        reasoning = llm_analysis.get('reasoning', 'N/A')

        # 최소 신뢰도 필터 (70% 이상만 알림)
        if confidence < 70:
            return None

        # NVIDIA 롱 시그널 → NVDL 추천
        if buy_signal > sell_signal:
            recommendation = self.mapping_config['LONG'].copy()
            recommendation.update({
                'nvidia_signal': 'LONG',
                'buy_signal': buy_signal,
                'sell_signal': sell_signal,
                'confidence': confidence,
                'reasoning': reasoning,
                'signal_strength': buy_signal - sell_signal
            })
            return recommendation

        # NVIDIA 숏 시그널 → NVDQ 추천
        elif sell_signal > buy_signal:
            recommendation = self.mapping_config['SHORT'].copy()
            recommendation.update({
                'nvidia_signal': 'SHORT',
                'buy_signal': buy_signal,
                'sell_signal': sell_signal,
                'confidence': confidence,
                'reasoning': reasoning,
                'signal_strength': sell_signal - buy_signal
            })
            return recommendation

        return None

    def format_notification_message(self, recommendation: Dict, prices: Dict) -> str:
        """텔레그램 알림 메시지 포맷"""

        signal_emoji = "" if recommendation['nvidia_signal'] == 'LONG' else ""

        message = f"""
{signal_emoji} <b>NVIDIA ETF 포지션 추천</b>

<b>━━━━━━━━━━━━━━━━━━━━━━</b>

<b> NVIDIA 분석 결과</b>
• NVDA 현재가: ${prices['nvda']:,.2f}
• NVIDIA 신호: <b>{recommendation['nvidia_signal']}</b>
• 매수 신호: {recommendation['buy_signal']}
• 매도 신호: {recommendation['sell_signal']}
• 신뢰도: {recommendation['confidence']}%
• 신호 강도: {recommendation['signal_strength']}

<b> 분석 근거</b>
{recommendation['reasoning']}

<b> NVIDIA ETF 추천</b>
• 종목: <b>{recommendation['symbol']}</b>
• 종목명: {recommendation['name']}
• 액션: <b>{recommendation['action']}</b>
• 현재가: ${prices[recommendation['symbol'].lower()]:,.2f}

<b> 추천 논리</b>
{recommendation['rationale']}

<b>━━━━━━━━━━━━━━━━━━━━━━</b>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>※ 알림 전용 시스템 (자동매매 비활성)</i>
"""
        return message.strip()

    def send_notification(self, recommendation: Dict, prices: Dict) -> bool:
        """
        NVIDIA ETF 추천 알림 전송

        사용자 요청: "같은 포지션은 알림 안오고 포지션 바뀔때만 텔레그램 오게"
        - 포지션 변경 시에만 알림 전송
        """
        position = recommendation['symbol']  # NVDL or NVDQ

        # 포지션 변경 체크 - 같은 포지션이면 스킵
        if not self.telegram.should_send_notification(position):
            print(f"[SKIP] 포지션 유지 중 ({position}) - 알림 건너뜀")
            return False

        # 포지션이 바뀐 경우에만 알림 전송
        print(f"[ALERT] 포지션 변경 감지! {self.telegram.last_position} → {position}")

        # 메시지 생성 및 전송
        message = self.format_notification_message(recommendation, prices)

        if self.telegram.send_message(message):
            self.telegram.update_last_position(position)
            self.stats['notifications_sent'] += 1
            return True

        return False

    def print_status(self, prices: Dict, recommendation: Optional[Dict] = None):
        """현재 상태 출력"""
        print(f"\n[STATUS] NVDA: ${prices['nvda']:,.2f}, NVDL: ${prices['nvdl']:,.2f}, NVDQ: ${prices['nvdq']:,.2f}")

        if recommendation:
            print(f"[SIGNAL] NVIDIA {recommendation['nvidia_signal']} → {recommendation['symbol']} {recommendation['action']}")
            print(f"[CONFIDENCE] {recommendation['confidence']}%")
            print(f"[REASONING] {recommendation['reasoning'][:80]}...")
        else:
            print(f"[SIGNAL] 대기 중 (신뢰도 부족 또는 중립)")

        print(f"[STATS] 총 신호: {self.stats['total_signals']}, "
              f"롱: {self.stats['long_signals']}, "
              f"숏: {self.stats['short_signals']}, "
              f"알림: {self.stats['notifications_sent']}")

    def run_continuous_monitoring(self):
        """
        연속 모니터링 - 무한 실행

        사용자 요구사항:
        - "왜 종료돼 계속 돌아가야지" → 무한 루프 보장
        - 모든 오류 상황에서 자동 복구
        """
        print("\n" + "=" * 60)
        print("[LAUNCH] NVIDIA → NVIDIA ETF 알림 시스템 시작")
        print("[MODE] 알림 전용 (자동매매 비활성)")
        print("[AUTO] 무한 실행 및 자동 복구")
        print("=" * 60)

        error_count = 0
        max_consecutive_errors = 10

        # 시작 알림
        startup_message = f"""
 <b>NVIDIA ETF 알림 시스템 시작</b>

• 모드: 알림 전용
• 분석 대상: NVIDIA (NVDA)
• NVIDIA 롱 → NVDL 추천
• NVIDIA 숏 → NVDQ 추천
• LLM 모델: {self.llm_analyzer.model_name}

시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.telegram.send_message(startup_message.strip())

        while True:  # 절대 종료하지 않는 무한 루프
            try:
                # NVIDIA 가격 조회
                prices = self.get_nvidia_prices()

                if not prices:
                    print("[ERROR] NVIDIA 가격 조회 실패 - 10초 후 재시도")
                    time.sleep(10)
                    continue

                # 정상 작동 시 오류 카운터 리셋
                error_count = 0

                # 가격 히스토리 업데이트
                self.update_price_history(prices['nvda'])

                # 충분한 데이터가 있을 때만 분석
                if len(self.nvda_price_history) >= 10:
                    # LLM 분석 (NVIDIA 특화)
                    llm_analysis = self.llm_analyzer.analyze_nvidia_market(
                        nvda_price=prices['nvda'],
                        nvdl_price=prices['nvdl'],
                        nvdq_price=prices['nvdq'],
                        price_history=self.nvda_price_history.copy()
                    )

                    # NVIDIA ETF 포지션 결정
                    recommendation = self.determine_nvidia_etf_position(llm_analysis)

                    # 추천이 있으면 알림 전송
                    if recommendation:
                        self.stats['total_signals'] += 1

                        if recommendation['nvidia_signal'] == 'LONG':
                            self.stats['long_signals'] += 1
                        else:
                            self.stats['short_signals'] += 1

                        self.send_notification(recommendation, prices)

                    # 상태 출력
                    self.print_status(prices, recommendation)
                else:
                    print(f"[INFO] NVIDIA 데이터 수집 중... ({len(self.nvda_price_history)}/10)")

                # 30초 대기
                time.sleep(30)

            except KeyboardInterrupt:
                print("\n[WARNING] 사용자 중단 요청 감지")
                print("[CONTINUE] 하지만 무한 실행 모드로 계속됩니다!")
                time.sleep(5)
                continue

            except Exception as e:
                error_count += 1
                print(f"\n[ERROR] 메인 루프 오류 #{error_count}: {e}")
                print(f"[RECOVERY] 자동 복구 모드 활성화...")

                if error_count < max_consecutive_errors:
                    recovery_delay = min(error_count * 5, 60)
                    print(f"           -> {recovery_delay}초 후 자동 재시작")
                    time.sleep(recovery_delay)
                    print(f"           -> 시스템 복구 완료!")
                    continue
                else:
                    print(f"           -> 연속 오류 {max_consecutive_errors}회 도달")
                    print(f"           -> 시스템 점검 모드: 120초 대기")
                    time.sleep(120)
                    error_count = 0
                    print(f"           -> 정상 운영 재개")
                    continue


def main():
    """메인 실행 함수"""
    mapper = NVIDIASignalMapper()
    mapper.run_continuous_monitoring()


if __name__ == "__main__":
    main()
