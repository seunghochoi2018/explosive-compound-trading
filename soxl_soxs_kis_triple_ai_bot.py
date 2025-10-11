#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOXL/SOXS KIS 자동화 트레이딩 봇 - 트리플 AI 시스템

 핵심 전략:
1. 7b 모델 3개 투입 (추세 분석, 진입 타이밍, 청산 타이밍)
2. 추세돌파 로직 (빠른 방향 전환)
3. 수익 보호 청산 (수수료 고려 즉시 청산)
4. 재진입 로직 (청산 후 방향 재평가)

 자동화 특화:
- 변동성 높은 SOXL/SOXS 활용
- 1분 분석 주기 (빠른 대응)
- 수익 나면 즉시 청산 (수수료 고려)
- 방향 전환 감지 즉시 반대 포지션
"""

import time
import json
import os
import sys
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 코드4 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TripleAIAnalyzer:
    """
    트리플 AI 분석 시스템
    - AI 1: 추세 분석 (Trend Analyzer)
    - AI 2: 진입 타이밍 (Entry Timer)
    - AI 3: 청산 타이밍 (Exit Timer)
    """

    def __init__(self, model_name: str = "qwen2.5:7b"):
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/generate"

        # Ollama 상태 체크
        try:
            import requests
            health_check = requests.get("http://localhost:11434/api/tags", timeout=3)
            if health_check.status_code == 200:
                print(f"[INIT] Ollama 연결 성공")
            else:
                print(f"[WARNING] Ollama 연결 불안정")
        except:
            print(f"[ERROR] Ollama 서버 미실행 - 룰 기반 분석으로 전환")

    def query_ollama(self, prompt: str) -> str:
        """Ollama LLM 쿼리 (타임아웃 짧게)"""
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 100  # 짧은 응답으로 제한
                    }
                },
                timeout=180  # 3분
            )

            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                print(f"[ERROR] Ollama API 오류: {response.status_code}")
                return ""

        except Exception as e:
            # 타임아웃 시 조용히 폴백
            return ""

    def ai1_trend_analysis(self, soxl_history: List[float], soxs_history: List[float]) -> Dict:
        """
        AI 1: 추세 분석 전문가

        역할: 시장의 전반적인 추세 방향 결정
        출력: LONG(SOXL), SHORT(SOXS), NEUTRAL
        """
        if len(soxl_history) < 10 or len(soxs_history) < 10:
            return {'trend': 'NEUTRAL', 'strength': 0, 'reason': '데이터 부족'}

        # 최근 데이터
        soxl_recent = soxl_history[-10:]
        soxs_recent = soxs_history[-10:]

        # 추세 계산
        soxl_trend = (soxl_recent[-1] - soxl_recent[0]) / soxl_recent[0] * 100
        soxs_trend = (soxs_recent[-1] - soxs_recent[0]) / soxs_recent[0] * 100

        # 변동성 계산
        soxl_volatility = sum(abs(soxl_recent[i] - soxl_recent[i-1]) / soxl_recent[i-1] for i in range(1, len(soxl_recent))) / len(soxl_recent) * 100

        prompt = f"""당신은 SOXL/SOXS 반도체 레버리지 ETF 추세 분석 전문가입니다.

 최근 10분 데이터:
- SOXL 추세: {soxl_trend:+.2f}%
- SOXS 추세: {soxs_trend:+.2f}%
- 변동성: {soxl_volatility:.2f}%

 임무: 현재 시장 추세 방향 결정

규칙:
1. SOXL 상승 > +2% → LONG
2. SOXS 상승 > +2% → SHORT
3. 변동성 > 3% + 추세 불명확 → NEUTRAL

응답 형식 (JSON):
{{
  "trend": "LONG|SHORT|NEUTRAL",
  "strength": 0-100,
  "reason": "추세 근거"
}}"""

        response = self.query_ollama(prompt)

        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        # 폴백: 간단한 규칙 기반
        if soxl_trend > 2:
            return {'trend': 'LONG', 'strength': min(int(soxl_trend * 10), 100), 'reason': f'SOXL 상승 {soxl_trend:.2f}%'}
        elif soxs_trend > 2:
            return {'trend': 'SHORT', 'strength': min(int(soxs_trend * 10), 100), 'reason': f'SOXS 상승 {soxs_trend:.2f}%'}
        else:
            return {'trend': 'NEUTRAL', 'strength': 0, 'reason': '추세 불명확'}

    def ai2_entry_timing(self, trend: str, current_price: float, price_history: List[float],
                         position: Optional[str], learning_examples: str = "") -> Dict:
        """
        AI 2: 진입 타이밍 전문가

        역할: 추세 확인 후 최적 진입 시점 결정
        출력: ENTER(진입), WAIT(대기)
        """
        if len(price_history) < 5:
            return {'action': 'WAIT', 'confidence': 0, 'reason': '데이터 부족'}

        # 이미 포지션 있으면 진입 안 함
        if position:
            return {'action': 'WAIT', 'confidence': 0, 'reason': '포지션 보유 중'}

        # 추세 없으면 진입 안 함
        if trend == 'NEUTRAL':
            return {'action': 'WAIT', 'confidence': 0, 'reason': '추세 없음'}

        # 최근 가격 변화
        price_change = (current_price - price_history[-5]) / price_history[-5] * 100

        # 모멘텀 계산
        recent_momentum = sum(price_history[-3:]) / 3 - sum(price_history[-6:-3]) / 3
        momentum_pct = recent_momentum / current_price * 100

        prompt = f"""당신은 SOXL/SOXS 진입 타이밍 전문가입니다.

 현재 상황:
- 추세: {trend}
- 현재가: ${current_price:.2f}
- 5분 변화: {price_change:+.2f}%
- 모멘텀: {momentum_pct:+.3f}%

 임무: 진입 시점 결정

규칙:
1. LONG 추세 + 가격 상승 모멘텀 → ENTER
2. SHORT 추세 + 가격 하락 모멘텀 → ENTER
3. 추세와 모멘텀 불일치 → WAIT

 과거 학습 데이터:
{learning_examples}

응답 형식 (JSON):
{{
  "action": "ENTER|WAIT",
  "confidence": 0-100,
  "reason": "진입 근거"
}}"""

        response = self.query_ollama(prompt)

        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        # 폴백: 간단한 규칙
        if trend == 'LONG' and price_change > 0.5:
            return {'action': 'ENTER', 'confidence': 80, 'reason': f'상승 모멘텀 {price_change:.2f}%'}
        elif trend == 'SHORT' and price_change < -0.5:
            return {'action': 'ENTER', 'confidence': 80, 'reason': f'하락 모멘텀 {price_change:.2f}%'}
        else:
            return {'action': 'WAIT', 'confidence': 0, 'reason': '진입 조건 불충분'}

    def ai3_exit_timing(self, position: str, entry_price: float, current_price: float,
                       holding_minutes: int, trend_changed: bool) -> Dict:
        """
        AI 3: 청산 타이밍 전문가

        역할: 수익 보호 및 손실 제한
        출력: EXIT(청산), HOLD(보유)

         핵심: 수익이 나면 즉시 청산! (수수료 고려)
        """
        pnl_pct = (current_price - entry_price) / entry_price * 100

        # KIS 수수료: 약 0.25% (매수 + 매도)
        FEE_PCT = 0.25
        net_profit = pnl_pct - FEE_PCT

        prompt = f"""당신은 SOXL/SOXS 청산 타이밍 전문가입니다.

 현재 포지션:
- 종목: {position}
- 진입가: ${entry_price:.2f}
- 현재가: ${current_price:.2f}
- 손익: {pnl_pct:+.2f}%
- 순수익 (수수료 후): {net_profit:+.2f}%
- 보유 시간: {holding_minutes}분
- 추세 변경: {'예' if trend_changed else '아니오'}

 임무: 청산 시점 결정

 핵심 규칙:
1. 순수익 > 0% → 즉시 EXIT (수익 보호!)
2. 추세 변경 → 즉시 EXIT (방향 전환)
3. 손실 < -2% → 즉시 EXIT (손절)
4. 보유 > 30분 + 수익 없음 → EXIT (기회비용)

응답 형식 (JSON):
{{
  "action": "EXIT|HOLD",
  "confidence": 0-100,
  "reason": "청산 근거"
}}"""

        response = self.query_ollama(prompt)

        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        # 폴백: 엄격한 수익 보호 규칙
        if net_profit > 0:
            return {'action': 'EXIT', 'confidence': 100, 'reason': f'수익 보호 {net_profit:.2f}% (수수료 제외)'}
        elif trend_changed:
            return {'action': 'EXIT', 'confidence': 100, 'reason': '추세 변경 감지'}
        elif pnl_pct < -2:
            return {'action': 'EXIT', 'confidence': 100, 'reason': f'손절 {pnl_pct:.2f}%'}
        elif holding_minutes > 30 and pnl_pct < 0:
            return {'action': 'EXIT', 'confidence': 80, 'reason': f'30분 경과 + 손실 {pnl_pct:.2f}%'}
        else:
            return {'action': 'HOLD', 'confidence': 50, 'reason': '보유 유지'}


class SOXLSOXSKISBot:
    """SOXL/SOXS KIS 자동화 트레이딩 봇"""

    def __init__(self):
        print("=" * 70)
        print("=== SOXL/SOXS KIS 자동화 트레이딩 봇 - 트리플 AI 시스템 ===")
        print("=" * 70)
        print("[*] 종목: SOXL (Bull 3x) / SOXS (Bear 3x)")
        print("[*] 전략: 추세돌파 + 수익 보호 청산")
        print("[*] AI 모델: qwen2.5:7b x 3개")
        print("=" * 70)

        # KIS API 설정
        self.load_kis_config()

        # 트리플 AI 분석기 초기화
        self.ai_analyzer = TripleAIAnalyzer(model_name="qwen2.5:7b")

        # 거래 상태
        self.symbols = {"SOXL": "반도체 3x Bull", "SOXS": "반도체 3x Bear"}
        self.current_position = None  # SOXL or SOXS
        self.entry_price = None
        self.entry_time = None
        self.last_trend = None

        # 가격 히스토리
        self.soxl_history = []
        self.soxs_history = []
        self.max_history = 50

        # 분석 주기
        self.analysis_interval = 60  # 1분마다 분석
        self.last_analysis_time = 0

        # 성능 추적
        self.stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'ai1_calls': 0,
            'ai2_calls': 0,
            'ai3_calls': 0,
            'direction_changes': 0
        }

        # 거래 기록 (학습용)
        self.trade_history = []
        self.learning_file = "soxl_soxs_trade_history.json"
        self.load_trade_history()

        # 상태 저장 파일
        self.state_file = "soxl_soxs_bot_state.json"
        self.load_state()

        # FMP API
        self.fmp_api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
        self.fmp_base_url = "https://financialmodelingprep.com/api/v3"

        print(f"[INIT] FMP API 실시간 가격 조회 활성화")
        print(f"[INIT] 분석 주기: {self.analysis_interval}초 (1분)")
        print(f"[INIT] 수익 보호: 수수료(0.25%) 고려 즉시 청산")

    def load_kis_config(self):
        """KIS API 설정 로드"""
        # KIS 계정 정보
        self.kis_app_key = "PSi3RlRt3DWtPPKTdYNALowIoeUBgM5mMLYO"
        self.kis_app_secret = "Q7LxW5oIlCeg+doJCkmPDgXw7uy8bjC7ACRQR1GrAzgCF3zH7LziMix/QJgweS+IRU+uM/3GPELXVeOGocKQnHZ+RPeH4bqR1CgFOs9tHmRtGmxCiwt3+1yp7yctt+bBc85eDrIsrX9KfOkrLY+wVuE1tthKYsDyiF2YKrOp/e1PsSD0mdI="
        self.account_num = "43113014"
        self.kis_base_url = "https://openapi.koreainvestment.com:9443"
        self.token_file = os.path.join(os.path.dirname(__file__), 'kis_token.json')

        # 토큰 로드 및 자동 재발급
        self.refresh_token_if_needed()

    def refresh_token_if_needed(self):
        """토큰 만료 체크 및 자동 재발급 (24시간 유효)"""
        try:
            # 기존 토큰 로드
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    self.kis_token = token_data.get('access_token')

                    # 기존 코드 호환 (expires_at 또는 token_expires)
                    self.token_expires = token_data.get('expires_at') or token_data.get('token_expires', 0)

                    # 토큰 유효 시간 체크 (24시간 = 86400초)
                    remaining_time = self.token_expires - time.time()

                    if remaining_time > 0:
                        remaining_hours = remaining_time / 3600
                        print(f"[INIT] KIS 토큰 유효 (만료까지 {remaining_hours:.1f}시간)")
                        return  # 유효하면 재발급 안 함!
                    else:
                        print(f"[WARNING] KIS 토큰 만료됨 (만료: {datetime.fromtimestamp(self.token_expires)})")
            else:
                print(f"[WARNING] KIS 토큰 파일 없음")

            # 토큰 만료되었을 때만 재발급
            print(f"[TOKEN] KIS 토큰 재발급 시작...")
            new_token = self.get_new_kis_token()

            if new_token:
                self.kis_token = new_token
                print(f"[SUCCESS] KIS 토큰 재발급 완료 (유효: 24시간)")
            else:
                print(f"[ERROR] KIS 토큰 재발급 실패")
                print(f"[INFO] 수동 재발급: python refresh_kis_token.py")
                self.kis_token = None

        except Exception as e:
            print(f"[ERROR] 토큰 로드 실패: {e}")
            self.kis_token = None

    def get_new_kis_token(self) -> Optional[str]:
        """KIS API 토큰 재발급"""
        try:
            url = f"{self.kis_base_url}/oauth2/tokenP"
            headers = {"content-type": "application/json; charset=utf-8"}
            data = {
                "grant_type": "client_credentials",
                "appkey": self.kis_app_key,
                "appsecret": self.kis_app_secret
            }

            response = requests.post(url, headers=headers, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                token = result.get("access_token")

                # 토큰 저장 (24시간 유효) - 기존 코드 호환
                token_data = {
                    "access_token": token,
                    "expires_at": time.time() + 23 * 3600,  # 23시간 (여유)
                    "created_at": time.time()
                }

                with open(self.token_file, 'w') as f:
                    json.dump(token_data, f, indent=2)

                return token
            else:
                print(f"[ERROR] 토큰 발급 실패: {response.status_code}")
                print(f"[ERROR] 응답: {response.text}")
                print(f"[INFO] refresh_kis_token.py를 직접 실행해주세요")
                return None

        except Exception as e:
            print(f"[ERROR] 토큰 발급 오류: {e}")
            return None

    def get_stock_price(self, symbol: str) -> float:
        """FMP API로 실시간 주식 가격 조회"""
        try:
            import requests
            url = f"{self.fmp_base_url}/quote/{symbol}"
            params = {'apikey': self.fmp_api_key}

            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                print(f"[ERROR] FMP API 오류: {response.status_code}")
                return 0.0

            data = response.json()

            if not data or len(data) == 0:
                print(f"[ERROR] {symbol} 데이터 없음")
                return 0.0

            price = float(data[0].get('price', 0))
            return price

        except Exception as e:
            print(f"[ERROR] {symbol} FMP 가격 조회 실패: {e}")
            return 0.0

    def update_price_history(self, soxl_price: float, soxs_price: float):
        """가격 히스토리 업데이트"""
        self.soxl_history.append(soxl_price)
        self.soxs_history.append(soxs_price)

        if len(self.soxl_history) > self.max_history:
            self.soxl_history.pop(0)
        if len(self.soxs_history) > self.max_history:
            self.soxs_history.pop(0)

    def load_trade_history(self):
        """거래 기록 로드"""
        try:
            if os.path.exists(self.learning_file):
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    self.trade_history = json.load(f)
                print(f"[LEARNING] 거래 기록 {len(self.trade_history)}개 로드")
            else:
                print(f"[LEARNING] 새로운 학습 시작")
        except Exception as e:
            print(f"[ERROR] 거래 기록 로드 실패: {e}")
            self.trade_history = []

    def save_trade_history(self):
        """거래 기록 저장"""
        try:
            with open(self.learning_file, 'w', encoding='utf-8') as f:
                json.dump(self.trade_history, f, ensure_ascii=False, indent=2)
            print(f"[SAVE] 거래 기록 저장: {len(self.trade_history)}개")
        except Exception as e:
            print(f"[ERROR] 거래 기록 저장 실패: {e}")

    def record_trade(self, symbol: str, entry_price: float, exit_price: float,
                    pnl_pct: float, holding_minutes: int, reason: str):
        """거래 기록"""
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': round(pnl_pct, 2),
            'holding_minutes': holding_minutes,
            'result': 'WIN' if pnl_pct > 0 else 'LOSS',
            'reason': reason
        }

        self.trade_history.append(trade_record)

        # 100개마다 저장
        if len(self.trade_history) % 10 == 0:
            self.save_trade_history()

    def load_state(self):
        """봇 상태 로드"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                self.current_position = state.get('current_position')
                self.entry_price = state.get('entry_price')

                entry_time_str = state.get('entry_time')
                if entry_time_str:
                    self.entry_time = datetime.fromisoformat(entry_time_str)

                self.stats.update(state.get('stats', {}))

                print(f"[LOAD] 상태 복원: {self.current_position or 'NO_POSITION'}")
        except Exception as e:
            print(f"[WARNING] 상태 로드 실패: {e}")

    def save_state(self):
        """봇 상태 저장"""
        try:
            state = {
                'current_position': self.current_position,
                'entry_price': self.entry_price,
                'entry_time': self.entry_time.isoformat() if self.entry_time else None,
                'stats': self.stats,
                'last_update': datetime.now().isoformat()
            }

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARNING] 상태 저장 실패: {e}")

    def get_learning_examples(self, limit: int = 20) -> str:
        """학습용 과거 거래 사례"""
        if not self.trade_history:
            return "과거 거래 없음"

        examples = []
        recent_trades = self.trade_history[-limit:] if len(self.trade_history) > limit else self.trade_history

        for i, trade in enumerate(recent_trades, 1):
            result = "" if trade['result'] == 'WIN' else ""
            examples.append(
                f"{i}. {trade['symbol']} ${trade['entry_price']:.2f}→${trade['exit_price']:.2f} "
                f"({trade['pnl_pct']:+.2f}%) {trade['holding_minutes']}분 {result}"
            )

        # 통계
        wins = sum(1 for t in self.trade_history if t['result'] == 'WIN')
        total = len(self.trade_history)
        win_rate = (wins / total * 100) if total > 0 else 0

        stats = f"통계: 총 {total}거래, 승률 {win_rate:.1f}%\n\n"

        return stats + "\n".join(examples)

    def execute_trade_kis(self, symbol: str, action: str, price: float) -> bool:
        """
        KIS API로 실제 거래 실행

        장전/장후 거래 지원:
        - 장전 거래 (Pre-market): 04:00-09:30 EST
        - 정규 거래 (Regular): 09:30-16:00 EST
        - 장후 거래 (After-hours): 16:00-20:00 EST
        """
        try:
            if not self.kis_token:
                print(f"[ERROR] KIS 토큰 없음")
                return False

            # KIS 해외주식 주문 API
            url = f"{self.kis_base_url}/uapi/overseas-stock/v1/trading/order"

            # 주문 구분: 장전/정규/장후
            now_utc = datetime.utcnow()
            hour = now_utc.hour

            # EST 시간대 계산 (UTC-5)
            est_hour = (hour - 5) % 24

            if 4 <= est_hour < 9.5:
                order_type = "34"  # 장전 거래
                session = "PRE-MARKET"
            elif 9.5 <= est_hour < 16:
                order_type = "00"  # 정규 거래
                session = "REGULAR"
            elif 16 <= est_hour < 20:
                order_type = "32"  # 장후 거래
                session = "AFTER-HOURS"
            else:
                print(f"[WARNING] 거래 시간 외 (EST {est_hour}시)")
                return False

            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "authorization": f"Bearer {self.kis_token}",
                "appkey": self.kis_app_key,
                "appsecret": self.kis_app_secret,
                "tr_id": "TTTT1002U" if action == "BUY" else "TTTT1006U",  # 매수/매도
                "custtype": "P"
            }

            data = {
                "CANO": self.account_num,
                "ACNT_PRDT_CD": "01",
                "OVRS_EXCG_CD": "NASD",  # 나스닥
                "PDNO": symbol,
                "ORD_QTY": "1",  # 수량
                "OVRS_ORD_UNPR": str(price),  # 가격
                "ORD_SVR_DVSN_CD": "0",  # 주문 서버 구분
                "ORD_DVSN": order_type  # 장전/정규/장후
            }

            print(f"[KIS_TRADE] {action} {symbol} @ ${price} ({session})")

            # 실제 주문 (주석 해제 시 실행)
            # response = requests.post(url, headers=headers, json=data, timeout=10)
            # if response.status_code == 200:
            #     result = response.json()
            #     print(f"[SUCCESS] 주문 성공: {result}")
            # else:
            #     print(f"[ERROR] 주문 실패: {response.status_code}")
            #     return False

            # 모의 거래로 대체
            print(f"[MOCK] 모의 주문 완료 (실거래 비활성화)")

        except Exception as e:
            print(f"[ERROR] 주문 실행 오류: {e}")
            return False

        if action == "SELL" and self.current_position:
            # 거래 기록
            holding_minutes = int((datetime.now() - self.entry_time).total_seconds() / 60)
            pnl_pct = (price - self.entry_price) / self.entry_price * 100

            self.record_trade(
                symbol=self.current_position,
                entry_price=self.entry_price,
                exit_price=price,
                pnl_pct=pnl_pct,
                holding_minutes=holding_minutes,
                reason="AI 청산 신호"
            )

        self.save_state()
        return True

    def make_decision(self, soxl_price: float, soxs_price: float):
        """트리플 AI 의사결정"""

        # AI 1: 추세 분석
        self.stats['ai1_calls'] += 1
        trend_analysis = self.ai_analyzer.ai1_trend_analysis(
            self.soxl_history, self.soxs_history
        )

        current_trend = trend_analysis['trend']
        trend_strength = trend_analysis['strength']

        print(f"\n[AI 1 - 추세] {current_trend} (강도: {trend_strength})")
        print(f"  └─ {trend_analysis['reason']}")

        # 추세 변경 감지
        trend_changed = False
        if self.last_trend and self.last_trend != current_trend and current_trend != 'NEUTRAL':
            trend_changed = True
            self.stats['direction_changes'] += 1
            print(f"[ 추세 변경] {self.last_trend} → {current_trend}")

        self.last_trend = current_trend

        # 포지션 있으면 AI 3: 청산 타이밍 체크
        if self.current_position:
            self.stats['ai3_calls'] += 1
            current_price = soxl_price if self.current_position == 'SOXL' else soxs_price
            holding_minutes = int((datetime.now() - self.entry_time).total_seconds() / 60)

            exit_decision = self.ai_analyzer.ai3_exit_timing(
                position=self.current_position,
                entry_price=self.entry_price,
                current_price=current_price,
                holding_minutes=holding_minutes,
                trend_changed=trend_changed
            )

            print(f"\n[AI 3 - 청산] {exit_decision['action']} (신뢰도: {exit_decision['confidence']})")
            print(f"  └─ {exit_decision['reason']}")

            if exit_decision['action'] == 'EXIT':
                # 청산 실행
                pnl_pct = (current_price - self.entry_price) / self.entry_price * 100
                self.execute_trade_kis(self.current_position, "SELL", current_price)

                self.stats['total_trades'] += 1
                self.stats['total_pnl'] += pnl_pct

                if pnl_pct > 0:
                    self.stats['wins'] += 1
                    print(f"[ 수익] {self.current_position} {pnl_pct:+.2f}%")
                else:
                    self.stats['losses'] += 1
                    print(f"[ 손실] {self.current_position} {pnl_pct:+.2f}%")

                # 포지션 초기화
                self.current_position = None
                self.entry_price = None
                self.entry_time = None

                # 청산 후 잠시 대기 (재진입 준비)
                time.sleep(2)

        # 포지션 없으면 AI 2: 진입 타이밍 체크
        if not self.current_position and current_trend != 'NEUTRAL':
            self.stats['ai2_calls'] += 1

            # 추세에 맞는 종목 선택
            target_symbol = 'SOXL' if current_trend == 'LONG' else 'SOXS'
            target_price = soxl_price if current_trend == 'LONG' else soxs_price
            target_history = self.soxl_history if current_trend == 'LONG' else self.soxs_history

            # 학습 데이터 가져오기
            learning_examples = self.get_learning_examples(limit=20)

            entry_decision = self.ai_analyzer.ai2_entry_timing(
                trend=current_trend,
                current_price=target_price,
                price_history=target_history,
                position=self.current_position,
                learning_examples=learning_examples
            )

            print(f"\n[AI 2 - 진입] {entry_decision['action']} (신뢰도: {entry_decision['confidence']})")
            print(f"  └─ {entry_decision['reason']}")

            if entry_decision['action'] == 'ENTER':
                # 진입 실행
                self.execute_trade_kis(target_symbol, "BUY", target_price)
                self.current_position = target_symbol
                self.entry_price = target_price
                self.entry_time = datetime.now()
                print(f"[ 진입] {target_symbol} @ ${target_price:.2f}")

    def print_status(self, soxl_price: float, soxs_price: float):
        """현재 상태 출력"""
        win_rate = (self.stats['wins'] / max(self.stats['total_trades'], 1)) * 100

        print(f"\n{'='*70}")
        print(f"[STATUS] SOXL: ${soxl_price:.2f} | SOXS: ${soxs_price:.2f}")
        print(f"[POSITION] {self.current_position or 'NONE'}")

        if self.current_position:
            current_price = soxl_price if self.current_position == 'SOXL' else soxs_price
            pnl = (current_price - self.entry_price) / self.entry_price * 100
            holding_time = (datetime.now() - self.entry_time).total_seconds() / 60
            print(f"[PNL] {pnl:+.2f}% (진입: ${self.entry_price:.2f}, 보유: {int(holding_time)}분)")

        print(f"[STATS] 거래: {self.stats['total_trades']} | 승률: {win_rate:.1f}% | 총손익: {self.stats['total_pnl']:+.2f}%")
        print(f"[AI] AI1: {self.stats['ai1_calls']} | AI2: {self.stats['ai2_calls']} | AI3: {self.stats['ai3_calls']} | 방향전환: {self.stats['direction_changes']}")
        print(f"{'='*70}")

    def run(self):
        """메인 트레이딩 루프"""
        print("\n[START] SOXL/SOXS KIS 자동화 봇 시작\n")

        while True:
            try:
                current_time = time.time()

                # 가격 조회
                soxl_price = self.get_stock_price("SOXL")
                soxs_price = self.get_stock_price("SOXS")

                if soxl_price <= 0 or soxs_price <= 0:
                    print("[ERROR] 가격 조회 실패")
                    time.sleep(30)
                    continue

                # 가격 히스토리 업데이트
                self.update_price_history(soxl_price, soxs_price)

                # 트리플 AI 분석 (1분마다)
                if current_time - self.last_analysis_time > self.analysis_interval:
                    if len(self.soxl_history) >= 10:
                        self.make_decision(soxl_price, soxs_price)
                    self.last_analysis_time = current_time

                # 상태 출력
                self.print_status(soxl_price, soxs_price)

                time.sleep(30)  # 30초 대기

            except KeyboardInterrupt:
                print("\n[STOP] 사용자 중단")
                break
            except Exception as e:
                print(f"[ERROR] 메인 루프 오류: {e}")
                time.sleep(60)

        print("[END] SOXL/SOXS KIS 자동화 봇 종료")


def main():
    bot = SOXLSOXSKISBot()
    bot.run()


if __name__ == "__main__":
    main()
