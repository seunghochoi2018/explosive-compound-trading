#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS LLM 신호 알림 시스템
- 14b × 2 병렬 LLM 분석 (원래 로직 그대로)
- 추세 판단 및 매수/매도 신호 생성
- 텔레그램으로 신호 알림
- 실제 주문 없음 (사용자가 직접 거래)
- 포지션 변경 감지 시 알림
"""

import os
import sys
import yaml
import json
import time
import requests
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

try:
    import psutil
except ImportError:
    print("[경고] psutil 모듈이 없습니다. pip install psutil 실행이 필요합니다.")
    psutil = None

class TelegramNotifier:
    """텔레그램 알림 시스템"""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        """텔레그램 알림 시스템 초기화"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(script_dir, "telegram_config.json")

        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.bot_token = config.get('bot_token', bot_token)
                self.chat_id = config.get('chat_id', chat_id)
        else:
            self.bot_token = bot_token or "7819173403:AAEwBNh6etqyWvh-GivLDrTJb8b_ho2ju-U"
            self.chat_id = chat_id or "7805944420"

        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(self, message: str, disable_notification: bool = False) -> bool:
        """텔레그램 메시지 전송"""
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_notification': disable_notification
            }
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[텔레그램 오류] {e}")
            return False

    def notify_trading_signal(self, signal: str, symbol: str, confidence: float,
                             reasoning: str, current_position: str = None,
                             current_pnl_pct: float = 0):
        """매매 신호 알림"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 이모지 선택
        if signal == 'BULL':
            emoji = "🟢"
            action = "매수 신호"
            target = "SOXL"
        elif signal == 'BEAR':
            emoji = "🔴"
            action = "매도/공매도 신호"
            target = "SOXS"
        else:
            emoji = "⚪"
            action = "대기"
            target = "없음"

        # 현재 포지션과 신호가 다른지 확인
        position_change = ""
        if current_position:
            if (signal == 'BULL' and current_position == 'SOXS') or \
               (signal == 'BEAR' and current_position == 'SOXL'):
                position_change = f"\n\n **포지션 전환 권장**\n현재: {current_position} (손익 {current_pnl_pct:+.2f}%)\n추천: {target}"

        message = f"""
{emoji} **LLM 분석 신호**

⏰ **시간**: {timestamp}

 **14b×2 LLM 판단**:
  - 신호: {action}
  - 종목: {target}
  - 신뢰도: {confidence:.0f}%

 **분석 근거**:
{reasoning}{position_change}

 **현재 포지션**: {current_position or '없음'}
        """.strip()

        self.send_message(message)

    def notify_position_change(self, old_pos: str, new_pos: str, usd_cash: float):
        """포지션 변경 감지 알림"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        message = f"""
 **포지션 변경 감지!**

⏰ **시간**: {timestamp}

 **변경 내용**:
  - 이전: {old_pos or '없음'}
  - 현재: {new_pos or '없음'}

 **USD 현금**: ${usd_cash:.2f}

 거래가 실행되었습니다.
        """.strip()

        self.send_message(message)

    def notify_start(self, initial_position: str, usd_cash: float):
        """시작 알림"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        message = f"""
 **KIS LLM 신호 알림 시작**

⏰ **시작 시간**: {timestamp}

 **분석 모델**: 14b × 2 병렬 LLM
 **전략**: 추세돌파 감지

💼 **현재 포지션**: {initial_position or '없음'}
 **USD 현금**: ${usd_cash:.2f}

 매매 신호 알림을 시작합니다.
        """.strip()

        self.send_message(message)


class KISLLMSignalNotifier:
    """KIS LLM 신호 알림 시스템 (주문 없음)"""

    def __init__(self, config_path: str = "kis_devlp.yaml", enable_telegram: bool = True):
        """초기화"""
        print("="*80)
        print("KIS LLM 신호 알림 시스템 v1.0")
        print("14b × 2 병렬 LLM 분석 + 텔레그램 알림")
        print("="*80)

        # 스크립트 디렉토리
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # 텔레그램 알림
        self.enable_telegram = enable_telegram
        if self.enable_telegram:
            try:
                self.telegram = TelegramNotifier()
                print("[텔레그램] 알림 시스템 활성화")
            except Exception as e:
                print(f"[경고] 텔레그램 초기화 실패: {e}")
                self.enable_telegram = False

        # 설정 로드
        if not os.path.isabs(config_path):
            config_path = os.path.join(script_dir, config_path)

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 토큰 로드
        token_path = os.path.join(script_dir, 'kis_token.json')
        with open(token_path, 'r') as f:
            token_data = json.load(f)
            self.access_token = token_data['access_token']

        # 계좌번호
        acct_parts = self.config['my_acct'].split('-')
        self.cano = acct_parts[0]
        self.acnt_prdt_cd = acct_parts[1] if len(acct_parts) > 1 else "01"

        # API URL
        self.base_url = "https://openapi.koreainvestment.com:9443"

        # Ollama 설정
        self.ollama_url = "http://127.0.0.1:11435"  # 11435 포트 사용

        # 거래 설정
        self.exchange_cd = "NASD"
        self.currency = "USD"
        self.target_symbols = ['SOXL', 'SOXS']

        # 가격 히스토리
        self.price_history_1m = []
        self.max_history = 60

        # 신호 추적
        self.last_signal = None
        self.last_signal_time = None
        self.signal_count = 0

        # 포지션 추적 (변경 감지용)
        self.previous_position = None

        print(f"[초기화 완료]")
        print(f"  계좌: {self.cano}-{self.acnt_prdt_cd}")
        print(f"  Ollama: {self.ollama_url} (11435 포트)")
        print(f"  분석 모델: qwen2.5:14b × 2")
        print("="*80)

    def get_usd_cash_balance(self) -> Dict:
        """USD 현금 잔고 조회"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-psamount"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT3007R",
            "custtype": "P",
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": "AMEX",
            "OVRS_ORD_UNPR": "40.0",
            "ITEM_CD": "SOXL"
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}'}

            result = response.json()
            if result.get('rt_cd') != '0':
                return {'success': False, 'error': result.get('msg1', '')}

            output = result.get('output', {})
            ord_psbl_frcr_amt = float(output.get('ord_psbl_frcr_amt', '0').replace(',', ''))

            return {
                'success': True,
                'ord_psbl_frcr_amt': ord_psbl_frcr_amt
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_positions(self) -> List[Dict]:
        """보유 포지션 조회"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.config['my_app'],
            "appsecret": self.config['my_sec'],
            "tr_id": "JTTT3012R",
            "custtype": "P",
            "User-Agent": self.config.get('my_agent', 'Mozilla/5.0')
        }

        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": self.exchange_cd,
            "TR_CRCY_CD": self.currency,
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code != 200:
                return []

            result = response.json()
            if result.get('rt_cd') != '0':
                return []

            output1 = result.get('output1', [])
            positions = []

            for item in output1:
                symbol = item.get('ovrs_pdno', '')
                qty = float(item.get('ovrs_cblc_qty', '0'))

                if qty > 0 and symbol in self.target_symbols:
                    avg_price = float(item.get('pchs_avg_pric', '0'))
                    current_price = float(item.get('now_pric2', '0'))
                    eval_amt = float(item.get('ovrs_stck_evlu_amt', '0'))

                    pnl = eval_amt - (qty * avg_price)
                    pnl_pct = (pnl / (qty * avg_price) * 100) if avg_price > 0 else 0

                    positions.append({
                        'symbol': symbol,
                        'qty': qty,
                        'avg_price': avg_price,
                        'current_price': current_price,
                        'eval_amt': eval_amt,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })

            return positions
        except Exception as e:
            print(f"[ERROR] 포지션 조회 오류: {e}")
            return []

    def analyze_with_llm_parallel(self, market_data: Dict) -> Dict:
        """
        14b × 2 병렬 LLM 분석 (원래 로직)
        """
        print(f"\n[LLM 분석 시작] 14b × 2 병렬 실행")

        # 프롬프트 생성
        prompt = self._build_llm_prompt(market_data)

        # 2개 모델 병렬 호출
        results = []
        for i in range(2):
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": "qwen2.5:14b",
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "num_predict": 500
                        }
                    },
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    answer = result.get('response', '')
                    results.append(answer)
                    print(f"  [LLM {i+1}] 응답 완료 ({len(answer)}자)")
                else:
                    print(f"  [LLM {i+1}] 오류: HTTP {response.status_code}")
            except Exception as e:
                print(f"  [LLM {i+1}] 예외: {e}")

        # 결과 통합
        if len(results) >= 2:
            return self._parse_llm_results(results, market_data)
        else:
            # LLM 실패 시 기본 분석
            return self._fallback_analysis(market_data)

    def _build_llm_prompt(self, market_data: Dict) -> str:
        """LLM 프롬프트 생성"""
        prompt = f"""당신은 반도체 ETF 추세 분석 전문가입니다.

# 현재 시장 상황
- 현재 포지션: {market_data.get('current_position', '없음')}
- 현재 손익: {market_data.get('current_pnl_pct', 0):.2f}%
- 최근 가격 변화: {market_data.get('price_change_pct', 0):.2f}%
- 가격 추세: {market_data.get('price_trend', '알 수 없음')}

# 분석 요청
SOXL(3배 레버리지 상승) vs SOXS(3배 레버리지 하락) 중 어느 방향이 유리한지 판단하세요.

다음 형식으로 답변하세요:
SIGNAL: BULL (상승 추세 → SOXL) 또는 BEAR (하락 추세 → SOXS)
CONFIDENCE: 0-100 (신뢰도 %)
REASONING: 판단 근거 (2-3줄)

답변:"""
        return prompt

    def _parse_llm_results(self, results: List[str], market_data: Dict) -> Dict:
        """LLM 결과 파싱 및 통합"""
        signals = []
        confidences = []
        reasonings = []

        for result in results:
            lines = result.split('\n')
            signal = None
            confidence = 50
            reasoning = ""

            for line in lines:
                line = line.strip()
                if 'SIGNAL:' in line.upper():
                    if 'BULL' in line.upper():
                        signal = 'BULL'
                    elif 'BEAR' in line.upper():
                        signal = 'BEAR'
                elif 'CONFIDENCE:' in line.upper():
                    try:
                        confidence = int(''.join(filter(str.isdigit, line)))
                    except:
                        confidence = 50
                elif 'REASONING:' in line.upper():
                    reasoning = line.split(':', 1)[1].strip() if ':' in line else ""

            if signal:
                signals.append(signal)
                confidences.append(confidence)
                reasonings.append(reasoning)

        # 앙상블 결정
        if len(signals) >= 2:
            # 다수결
            bull_count = signals.count('BULL')
            bear_count = signals.count('BEAR')

            if bull_count > bear_count:
                final_signal = 'BULL'
                final_confidence = sum(c for s, c in zip(signals, confidences) if s == 'BULL') / bull_count
            elif bear_count > bull_count:
                final_signal = 'BEAR'
                final_confidence = sum(c for s, c in zip(signals, confidences) if s == 'BEAR') / bear_count
            else:
                # 동점이면 신뢰도 높은 쪽
                max_conf_idx = confidences.index(max(confidences))
                final_signal = signals[max_conf_idx]
                final_confidence = confidences[max_conf_idx]

            final_reasoning = " / ".join(reasonings)

            print(f"  [앙상블 결과] {final_signal} ({final_confidence:.0f}%)")

            return {
                'signal': final_signal,
                'confidence': final_confidence,
                'reasoning': final_reasoning
            }

        return self._fallback_analysis(market_data)

    def _fallback_analysis(self, market_data: Dict) -> Dict:
        """LLM 실패 시 기본 분석"""
        print("  [폴백] 기본 추세 분석 사용")

        price_change = market_data.get('price_change_pct', 0)

        if price_change > 1.0:
            return {
                'signal': 'BULL',
                'confidence': 60,
                'reasoning': f"상승 추세 감지 ({price_change:.2f}%)"
            }
        elif price_change < -1.0:
            return {
                'signal': 'BEAR',
                'confidence': 60,
                'reasoning': f"하락 추세 감지 ({price_change:.2f}%)"
            }
        else:
            return {
                'signal': 'NEUTRAL',
                'confidence': 50,
                'reasoning': "명확한 추세 없음"
            }

    def execute_analysis(self):
        """분석 실행 (메인 로직)"""
        print("\n" + "="*80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] LLM 분석 실행")
        print("="*80)

        # 1. 계좌 정보 조회
        buying_power = self.get_usd_cash_balance()
        positions = self.get_positions()

        if not buying_power['success']:
            print("[ERROR] USD 잔고 조회 실패")
            return

        usd_cash = buying_power['ord_psbl_frcr_amt']
        print(f"\n[계좌 현황]")
        print(f"  USD 현금: ${usd_cash:.2f}")

        current_position = None
        current_pnl_pct = 0
        current_price = 40.0

        if positions:
            pos = positions[0]
            current_position = pos['symbol']
            current_pnl_pct = pos['pnl_pct']
            current_price = pos['current_price']
            print(f"  보유: {current_position} {pos['qty']}주")
            print(f"  손익: {current_pnl_pct:+.2f}%")

            # 가격 히스토리 업데이트
            self.price_history_1m.append(current_price)
            if len(self.price_history_1m) > self.max_history:
                self.price_history_1m.pop(0)
        else:
            print(f"  보유: 없음")
            # 히스토리 초기화
            if len(self.price_history_1m) == 0:
                self.price_history_1m = [current_price] * 10

        # 포지션 변경 감지
        if self.previous_position != current_position:
            if self.previous_position is not None:  # 첫 실행 제외
                print("\n[포지션 변경 감지!]")
                if self.enable_telegram:
                    self.telegram.notify_position_change(
                        old_pos=self.previous_position,
                        new_pos=current_position,
                        usd_cash=usd_cash
                    )
            self.previous_position = current_position

        # 2. 시장 데이터 준비
        if len(self.price_history_1m) >= 2:
            price_change_pct = ((self.price_history_1m[-1] - self.price_history_1m[0]) /
                               self.price_history_1m[0] * 100)
        else:
            price_change_pct = 0

        market_data = {
            'current_position': current_position,
            'current_pnl_pct': current_pnl_pct,
            'price_change_pct': price_change_pct,
            'price_trend': "상승" if price_change_pct > 0 else "하락" if price_change_pct < 0 else "횡보"
        }

        # 3. LLM 분석
        analysis = self.analyze_with_llm_parallel(market_data)

        signal = analysis.get('signal')
        confidence = analysis.get('confidence', 0)
        reasoning = analysis.get('reasoning', '')

        print(f"\n[LLM 분석 결과]")
        print(f"  신호: {signal}")
        print(f"  신뢰도: {confidence:.0f}%")
        print(f"  근거: {reasoning}")

        # 4. 신호 변경 감지 및 알림
        if signal != self.last_signal and signal != 'NEUTRAL':
            print(f"\n[신호 변경] {self.last_signal} → {signal}")

            # 텔레그램 알림
            if self.enable_telegram and confidence >= 60:
                target_symbol = 'SOXL' if signal == 'BULL' else 'SOXS'
                self.telegram.notify_trading_signal(
                    signal=signal,
                    symbol=target_symbol,
                    confidence=confidence,
                    reasoning=reasoning,
                    current_position=current_position,
                    current_pnl_pct=current_pnl_pct
                )

            self.last_signal = signal
            self.last_signal_time = datetime.now()
            self.signal_count += 1

        print("="*80)

    def run(self, interval_seconds: int = 300):
        """메인 루프"""
        print(f"\n[신호 알림 시작]")
        print(f"  분석 간격: {interval_seconds}초")
        print(f"  종료: Ctrl+C\n")

        # 시작 알림
        if self.enable_telegram:
            positions = self.get_positions()
            buying_power = self.get_usd_cash_balance()

            initial_pos = positions[0]['symbol'] if positions else None
            usd_cash = buying_power.get('ord_psbl_frcr_amt', 0) if buying_power['success'] else 0

            self.telegram.notify_start(initial_pos, usd_cash)
            self.previous_position = initial_pos

        cycle = 0
        while True:
            try:
                cycle += 1
                print(f"\n[사이클 {cycle}]")

                self.execute_analysis()

                print(f"\n다음 분석까지 {interval_seconds}초 대기...")
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\n\n[종료] 사용자가 중단했습니다")
                break

            except Exception as e:
                print(f"\n[ERROR] 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(interval_seconds)


def start_ollama():
    """Ollama 11435 포트로 시작"""
    print("\n" + "="*80)
    print("Ollama 서버 확인 및 시작")
    print("="*80)

    # 기존 Ollama 프로세스 종료
    if psutil:
        print("기존 Ollama 프로세스 확인 중...")
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                    print(f"  종료: {proc.info['name']} (PID: {proc.pid})")
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(2)
    else:
        print("psutil 없음 - 기존 프로세스 확인 생략")

    # Ollama 11435 포트로 시작
    ollama_path = r"C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe"
    models_path = r"C:\Users\user\.ollama\models"

    print(f"\nOllama 시작 중...")
    print(f"  경로: {ollama_path}")
    print(f"  포트: 11435")
    print(f"  모델 경로: {models_path}")

    # 환경변수 설정
    env = os.environ.copy()
    env['OLLAMA_HOST'] = '127.0.0.1:11435'
    env['OLLAMA_MODELS'] = models_path

    # 백그라운드로 실행
    try:
        subprocess.Popen(
            [ollama_path, 'serve'],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        print("   Ollama 시작 완료")
    except Exception as e:
        print(f"   Ollama 시작 실패: {e}")
        print("  수동으로 start_ollama_11435.bat을 실행하세요")
        return False

    # 서버 준비 대기
    print("\nOllama 서버 준비 대기 중...")
    for i in range(10):
        try:
            response = requests.get("http://127.0.0.1:11435/api/tags", timeout=2)
            if response.status_code == 200:
                result = response.json()
                models = result.get('models', [])
                print(f"   Ollama 서버 준비 완료")
                print(f"  모델 개수: {len(models)}")
                return True
        except Exception as e:
            pass
        print(f"  대기 중... ({i+1}/10)")
        time.sleep(2)

    print("   Ollama 서버 응답 없음 (계속 진행)")
    return True


def main():
    """메인 실행"""
    # Ollama 자동 시작
    if not start_ollama():
        print("\n[경고] Ollama를 수동으로 시작해주세요")
        print("실행: start_ollama_11435.bat")
        sys.exit(1)

    print("\n" + "="*80)

    # 신호 알림 시스템 시작
    notifier = KISLLMSignalNotifier(enable_telegram=True)
    notifier.run(interval_seconds=300)  # 5분마다 분석


if __name__ == "__main__":
    main()
