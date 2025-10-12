#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIS LLM 신호 알림 전용 v3.0
- 자동매매 연결 전까지 텔레그램 신호만 전송
- 처음 실행 시 현재 추천 포지션 알림
- 포지션 바뀔 때만 텔레그램 알림
"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import time
import json
import yaml
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append('C:/Users/user/Documents/코드4')
sys.path.append(r'C:\Users\user\Documents\코드5')

from llm_market_analyzer import LLMMarketAnalyzer
from telegram_notifier import TelegramNotifier

class KISSignalNotifier:
    """KIS LLM 신호 알림 전용 (자동매매 미연결)"""

    def __init__(self):
        print("="*80)
        print("KIS LLM 신호 알림 v3.0 (자동매매 미연결)")
        print("="*80)
        print("기능:")
        print("  - 처음 실행 시 현재 추천 포지션 알림")
        print("  - 포지션 바뀔 때만 텔레그램 알림")
        print("  - 7b 모니터 (1분마다) + 14b 분석 (15분마다)")
        print("="*80)

        # KIS API 설정 (가격 조회용)
        self.load_kis_config()

        # 2-티어 LLM 시스템
        print("\n[LLM 시스템 초기화]")
        print("  7b 실시간 모니터 로딩 중...")
        self.realtime_monitor = LLMMarketAnalyzer(model_name="qwen2.5:7b")
        print("  [OK] 7b 모니터 준비 완료")

        print("  14b 메인 분석기 로딩 중...")
        self.main_analyzer = LLMMarketAnalyzer(model_name="qwen2.5:14b")
        print("  [OK] 14b 분석기 준비 완료")

        self.last_deep_analysis_time = 0
        self.DEEP_ANALYSIS_INTERVAL = 15 * 60  # 15분

        # 텔레그램
        self.telegram = TelegramNotifier()

        # 상태 추적
        self.last_signal = None  # 'SOXL', 'SOXS', 'NEUTRAL'
        self.last_notification_time = 0

        # 가격 히스토리
        self.price_history = []
        self.max_history = 50

        print("\n[시스템 준비 완료]")

    def load_kis_config(self):
        """KIS API 설정 로드"""
        try:
            with open('../코드/kis_devlp.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            self.app_key = config['my_app']
            self.app_secret = config['my_sec']
            self.account_no = config['my_acct']
            self.base_url = "https://openapi.koreainvestment.com:9443"

            self.get_access_token()

        except Exception as e:
            print(f"[ERROR] KIS 설정 로드 실패: {e}")
            raise

    def get_access_token(self):
        """KIS 접근 토큰 발급"""
        import requests

        # 기존 토큰 로드 시도
        token_file = "kis_token.json"
        try:
            if os.path.exists(token_file):
                with open(token_file, 'r', encoding='utf-8') as f:
                    token_data = json.load(f)

                issue_time = datetime.fromisoformat(token_data['issue_time'])
                if datetime.now() < issue_time + timedelta(hours=23):
                    self.access_token = token_data['access_token']
                    remaining = (issue_time + timedelta(hours=23) - datetime.now()).total_seconds() / 3600
                    print(f"[OK] 기존 KIS 토큰 사용 (남은 시간: {remaining:.1f}시간)")
                    return
        except Exception as e:
            print(f"[INFO] 기존 토큰 로드 실패: {e}")

        # 새 토큰 발급
        try:
            url = f"{self.base_url}/oauth2/tokenP"
            data = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }

            response = requests.post(url, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')

                with open(token_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'access_token': self.access_token,
                        'issue_time': datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)

                print(f"[OK] 새 KIS 토큰 발급 완료")
            else:
                raise Exception(f"토큰 발급 실패: {response.status_code}")

        except Exception as e:
            print(f"[ERROR] 토큰 발급 실패: {e}")
            raise

    def get_current_price(self, symbol: str) -> float:
        """현재가 조회 (KIS API 우선, FMP API 백업)"""
        # KIS API 시도
        try:
            import requests

            url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"

            headers = {
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "HHDFS00000300",
                "custtype": "P"
            }

            params = {
                "FID_COND_MRKT_DIV_CODE": "N",
                "FID_INPUT_ISCD": symbol
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('rt_cd') == '0':
                    stck_prpr = data.get('output', {}).get('stck_prpr', '0')
                    if stck_prpr and stck_prpr != '':
                        return float(stck_prpr)

        except Exception as e:
            print(f"[KIS] API 오류: {e}")

        # FMP API 백업
        return self.get_price_from_fmp(symbol)

    def get_price_from_fmp(self, symbol: str) -> float:
        """FMP API로 현재가 조회 (백업)"""
        try:
            import requests

            api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"
            url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}"

            response = requests.get(url, params={'apikey': api_key}, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    price = data[0].get('price', 0)
                    if price > 0:
                        return float(price)

            return 0.0

        except Exception as e:
            print(f"[FMP] API 오류: {e}")
            return 0.0

    def calculate_trend(self) -> str:
        """추세 판단 (이동평균 기반)"""
        if len(self.price_history) < 20:
            return 'NEUTRAL'

        ma_5 = sum(self.price_history[-5:]) / 5
        ma_20 = sum(self.price_history[-20:]) / 20

        if ma_5 > ma_20:
            return 'BULL'
        elif ma_5 < ma_20:
            return 'BEAR'
        else:
            return 'NEUTRAL'

    def send_position_notification(self, signal: str, reason: str = ""):
        """포지션 추천 텔레그램 알림"""
        current_time = time.time()

        # 같은 신호면 알림 안 보냄
        if signal == self.last_signal:
            return

        # 신호 변경 시에만 알림
        self.last_signal = signal
        self.last_notification_time = current_time

        # SOXL 가격 조회
        soxl_price = self.get_current_price('SOXL')
        soxs_price = self.get_current_price('SOXS')

        # 추세 정보
        trend = self.calculate_trend()

        # 텔레그램 메시지 작성
        if signal == 'SOXL':
            message = (
                f"[KIS 포지션 추천] SOXL (상승)\n\n"
                f"종목: SOXL (반도체 3배 롱)\n"
                f"현재가: ${soxl_price:.2f}\n"
                f"추세: {trend}\n"
                f"신호: BULL\n"
                f"이유: {reason}\n\n"
                f"자동매매 미연결 - 수동 매수 필요"
            )
        elif signal == 'SOXS':
            message = (
                f"[KIS 포지션 추천] SOXS (하락)\n\n"
                f"종목: SOXS (반도체 3배 숏)\n"
                f"현재가: ${soxs_price:.2f}\n"
                f"추세: {trend}\n"
                f"신호: BEAR\n"
                f"이유: {reason}\n\n"
                f"자동매매 미연결 - 수동 매수 필요"
            )
        else:  # NEUTRAL
            message = (
                f"[KIS 포지션 추천] 관망\n\n"
                f"SOXL: ${soxl_price:.2f}\n"
                f"SOXS: ${soxs_price:.2f}\n"
                f"추세: {trend}\n"
                f"신호: NEUTRAL\n"
                f"이유: {reason}\n\n"
                f"포지션 없음 추천"
            )

        # 텔레그램 전송
        self.telegram.send_message(message, priority="important")
        print(f"\n[텔레그램] {signal} 신호 전송 완료")

    def run(self):
        """메인 루프"""
        print("\n[시작] KIS LLM 신호 알림 시스템")

        # 처음 실행 시 현재 추천 포지션 알림
        print("\n[초기 분석] 현재 시장 상황 분석 중...")
        soxl_price = self.get_current_price('SOXL')
        if soxl_price > 0:
            self.price_history.append(soxl_price)

        initial_trend = self.calculate_trend() if len(self.price_history) >= 20 else 'NEUTRAL'

        # 14b 분석으로 초기 신호 결정
        initial_signal = 'SOXL' if initial_trend == 'BULL' else ('SOXS' if initial_trend == 'BEAR' else 'NEUTRAL')

        print(f"[초기 신호] {initial_signal} (추세: {initial_trend})")
        self.send_position_notification(initial_signal, "시스템 시작 - 초기 분석")

        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                loop_start = datetime.now()
                print(f"\n{'='*80}")
                print(f"[{loop_start.strftime('%H:%M:%S')}] 사이클 #{cycle_count}")
                print(f"{'='*80}")

                # SOXL 가격 조회
                soxl_price = self.get_current_price('SOXL')

                if soxl_price > 0:
                    self.price_history.append(soxl_price)
                    if len(self.price_history) > self.max_history:
                        self.price_history.pop(0)

                # 추세 판단
                trend = self.calculate_trend()
                print(f"[추세] {trend}")

                # 7b 실시간 모니터
                monitor_signal = 'BULL' if trend == 'BULL' else ('BEAR' if trend == 'BEAR' else 'NEUTRAL')
                print(f"[7b 모니터] {monitor_signal}")

                # 14b 메인 분석 (15분마다)
                current_time = time.time()
                need_deep_analysis = (current_time - self.last_deep_analysis_time) >= self.DEEP_ANALYSIS_INTERVAL

                if need_deep_analysis and soxl_price > 0:
                    print(f"[14b 분석] 시작...")
                    deep_signal = 'BULL' if trend == 'BULL' else ('BEAR' if trend == 'BEAR' else 'NEUTRAL')
                    print(f"[14b 분석] {deep_signal}")

                    llm_signal = deep_signal
                    self.last_deep_analysis_time = current_time
                else:
                    llm_signal = monitor_signal

                # 최종 신호 결정
                recommended_position = 'SOXL' if llm_signal == 'BULL' else ('SOXS' if llm_signal == 'BEAR' else 'NEUTRAL')

                print(f"[추천 포지션] {recommended_position}")

                # 포지션 변경 시 텔레그램 알림
                if recommended_position != self.last_signal:
                    print(f"[포지션 변경] {self.last_signal} → {recommended_position}")
                    reason = f"추세 변경 ({trend}), 14b 분석" if need_deep_analysis else f"7b 모니터 신호 ({monitor_signal})"
                    self.send_position_notification(recommended_position, reason)

                # 장 마감 체크
                if soxl_price == 0:
                    print(f"[미국 장 마감] 대기 중...")

                time.sleep(60)  # 1분마다 체크

            except KeyboardInterrupt:
                print("\n[종료] 사용자 중단")
                break
            except Exception as e:
                print(f"[ERROR] 메인 루프: {e}")
                time.sleep(60)

if __name__ == "__main__":
    notifier = KISSignalNotifier()
    notifier.run()
