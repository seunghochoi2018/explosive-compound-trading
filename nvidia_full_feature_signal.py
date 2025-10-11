#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
완전 기능 NVIDIA LLM 신호 알림 시스템
- 에러 없는 단일 파일 구조
- 모든 기능 포함 (LLM, 기술적 지표, 텔레그램)
- NVDL/NVDD 전문 분석
"""

import json
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class FullFeatureNVIDIASignal:
    """완전 기능 NVIDIA 신호 시스템"""

    def __init__(self):
        # API 설정
        self.fmp_api_key = "5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI"

        # 텔레그램 설정
        self.telegram_token = "7819173403:AAEwBNh6etqyWvh-GivLDrTJb8b_ho2ju-U"
        self.chat_id = "7805944420"

        # LLM 설정
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "qwen2.5:7b"

        # 거래 설정
        self.config = {
            'check_interval': 300,      # 5분
            'min_confidence': 0.6,      # 최소 신뢰도 60%
            'max_daily_signals': 10,    # 일일 최대 신호
            'cooldown_period': 1800,    # 30분 쿨다운
        }

        # 상태 관리
        self.last_signals = {}
        self.signal_history = []
        self.daily_signal_count = 0
        self.last_reset_date = datetime.now().date()

        print("[OK] 완전 기능 NVIDIA LLM 신호 시스템 초기화 완료")

    def get_stock_data(self, symbol: str) -> Optional[Dict]:
        """주식 데이터 조회 (FMP API)"""
        try:
            # 현재 가격
            price_url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}"
            price_params = {"apikey": self.fmp_api_key}

            price_response = requests.get(price_url, params=price_params, timeout=10)
            if price_response.status_code != 200:
                return None

            price_data = price_response.json()
            if not price_data:
                return None

            current_price = price_data[0]["price"]
            change_percent = price_data[0]["changesPercentage"]
            volume = price_data[0]["volume"]

            # 기술적 데이터 (간단한 지표)
            technical_url = f"https://financialmodelingprep.com/api/v3/technical_indicator/1day/{symbol}"
            technical_params = {"apikey": self.fmp_api_key, "period": 14}

            try:
                tech_response = requests.get(technical_url, params=technical_params, timeout=10)
                tech_data = tech_response.json() if tech_response.status_code == 200 else []
            except:
                tech_data = []

            # RSI 계산 (기본값 사용)
            rsi = tech_data[0].get("rsi", 50) if tech_data else 50

            return {
                "symbol": symbol,
                "price": current_price,
                "change_percent": change_percent,
                "volume": volume,
                "rsi": rsi,
                "timestamp": datetime.now()
            }

        except Exception as e:
            print(f"[ERROR] {symbol} 데이터 조회 실패: {e}")
            return None

    def calculate_technical_indicators(self, data: Dict) -> Dict:
        """기술적 지표 계산"""
        try:
            price = data["price"]
            change_percent = data["change_percent"]
            rsi = data["rsi"]

            # 추세 방향
            if change_percent > 2:
                trend = "강한 상승"
            elif change_percent > 0:
                trend = "상승"
            elif change_percent > -2:
                trend = "하락"
            else:
                trend = "강한 하락"

            # 모멘텀 점수
            momentum_score = change_percent / 10.0  # -1 ~ 1 범위로 정규화

            # 변동성 (단순 계산)
            volatility = abs(change_percent) / 100.0

            # 지지/저항선 (단순 계산)
            support_level = price * (1 - volatility)
            resistance_level = price * (1 + volatility)

            # 거래량 추세
            volume_trend = "높음" if data["volume"] > 1000000 else "보통"

            return {
                "rsi": rsi,
                "trend_direction": trend,
                "momentum_score": momentum_score,
                "volatility": volatility,
                "support_level": support_level,
                "resistance_level": resistance_level,
                "volume_trend": volume_trend
            }

        except Exception as e:
            print(f"[ERROR] 기술적 지표 계산 실패: {e}")
            return {
                "rsi": 50,
                "trend_direction": "중립",
                "momentum_score": 0,
                "volatility": 0.02,
                "support_level": data["price"] * 0.98,
                "resistance_level": data["price"] * 1.02,
                "volume_trend": "보통"
            }

    def llm_analyze(self, nvdl_data: Dict, nvdd_data: Dict, nvdl_indicators: Dict, nvdd_indicators: Dict) -> str:
        """LLM 분석"""
        prompt = f"""당신은 NVIDIA 전문 투자 분석가입니다. 다음 정보를 분석하고 투자 의견을 제시해주세요:

현재 가격:
- NVDL (3배 레버리지 ETF): ${nvdl_data['price']:.2f} ({nvdl_data['change_percent']:+.2f}%)
- NVDD (-1배 ETF): ${nvdd_data['price']:.2f} ({nvdd_data['change_percent']:+.2f}%)

기술적 지표:
- NVDL RSI: {nvdl_indicators['rsi']:.1f}, 추세: {nvdl_indicators['trend_direction']}
- NVDD RSI: {nvdd_indicators['rsi']:.1f}, 추세: {nvdd_indicators['trend_direction']}

NVDL과 NVDD는 반대 방향으로 움직입니다:
- NVIDIA 상승 시: NVDL ↑, NVDD ↓
- NVIDIA 하락 시: NVDL ↓, NVDD ↑

분석 요청:
1. 현재 NVIDIA 시장 상황 평가
2. NVDL/NVDD 중 어느 것이 더 유리한지
3. 투자 타이밍과 리스크 수준
4. 구체적인 매매 전략 제안

200자 이내로 간결하고 실용적인 분석을 제공해주세요."""

        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                analysis = result.get('response', '').strip()
                return analysis
            else:
                return "LLM 분석 실패 - 서버 오류"

        except requests.exceptions.Timeout:
            return "LLM 분석 타임아웃 - 서버 과부하"
        except Exception as e:
            return f"LLM 분석 오류: {str(e)}"

    def generate_signal(self, symbol: str, data: Dict, indicators: Dict, llm_analysis: str) -> Optional[Dict]:
        """신호 생성"""
        try:
            current_price = data["price"]
            change_percent = data["change_percent"]
            rsi = indicators["rsi"]

            # 신호 결정 로직
            confidence = 0.0
            action = "HOLD"

            # RSI 기반 신호
            if symbol == "NVDL":
                if rsi < 30 and change_percent < -3:  # 과매도 + 큰 하락
                    action = "BUY"
                    confidence = 0.8
                elif rsi > 70 and change_percent > 3:  # 과매수 + 큰 상승
                    action = "SELL"
                    confidence = 0.7
                elif rsi < 40 and change_percent < -1:
                    action = "BUY"
                    confidence = 0.6
                elif rsi > 60 and change_percent > 1:
                    action = "SELL"
                    confidence = 0.6

            elif symbol == "NVDD":
                if rsi < 30 and change_percent < -3:  # NVDD 과매도 (NVIDIA 상승 시)
                    action = "BUY"
                    confidence = 0.8
                elif rsi > 70 and change_percent > 3:  # NVDD 과매수 (NVIDIA 하락 시)
                    action = "SELL"
                    confidence = 0.7
                elif rsi < 40 and change_percent < -1:
                    action = "BUY"
                    confidence = 0.6
                elif rsi > 60 and change_percent > 1:
                    action = "SELL"
                    confidence = 0.6

            # 최소 신뢰도 체크
            if confidence < self.config['min_confidence']:
                return None

            # 쿨다운 체크
            if self._is_in_cooldown(symbol):
                return None

            # 목표가/손절가 계산
            volatility = indicators["volatility"]

            if action == "BUY":
                target_price = current_price * (1 + volatility * 2)
                stop_loss = current_price * (1 - volatility * 1.5)
                expected_return = volatility * 200
            else:  # SELL
                target_price = current_price * (1 - volatility * 2)
                stop_loss = current_price * (1 + volatility * 1.5)
                expected_return = volatility * 200

            # 리스크 레벨
            if confidence > 0.8:
                risk_level = "LOW"
                holding_period = "단기 (1-3일)"
            elif confidence > 0.6:
                risk_level = "MEDIUM"
                holding_period = "중기 (3-7일)"
            else:
                risk_level = "HIGH"
                holding_period = "장기 (1-2주)"

            signal = {
                "timestamp": datetime.now(),
                "symbol": symbol,
                "action": action,
                "confidence": confidence,
                "current_price": current_price,
                "target_price": target_price,
                "stop_loss": stop_loss,
                "expected_return": expected_return,
                "holding_period": holding_period,
                "risk_level": risk_level,
                "indicators": indicators,
                "llm_analysis": llm_analysis,
                "signal_id": f"{symbol}_{int(time.time())}"
            }

            return signal

        except Exception as e:
            print(f"[ERROR] {symbol} 신호 생성 실패: {e}")
            return None

    def _is_in_cooldown(self, symbol: str) -> bool:
        """쿨다운 체크"""
        if symbol not in self.last_signals:
            return False

        last_time = self.last_signals[symbol]["timestamp"]
        cooldown_end = last_time + timedelta(seconds=self.config['cooldown_period'])

        return datetime.now() < cooldown_end

    def format_signal_message(self, signal: Dict) -> str:
        """신호 메시지 포맷팅"""
        action_emoji = "🟢" if signal["action"] == "BUY" else "🔴"
        risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}[signal["risk_level"]]

        price_change = ((signal["target_price"] - signal["current_price"]) / signal["current_price"]) * 100

        message_parts = [
            f"{action_emoji} **{signal['symbol']} {signal['action']} 신호**",
            "",
            f" **현재가**: ${signal['current_price']:.2f}",
            f" **목표가**: ${signal['target_price']:.2f} ({price_change:+.1f}%)",
            f"🛡️ **손절가**: ${signal['stop_loss']:.2f}",
            f" **신뢰도**: {signal['confidence']:.1%}",
            f"{risk_emoji} **리스크**: {signal['risk_level']}",
            f"⏰ **보유기간**: {signal['holding_period']}",
            f" **예상수익**: {signal['expected_return']:.1f}%",
            "",
            " **기술적 분석**:",
            f"• RSI: {signal['indicators']['rsi']:.1f}",
            f"• 추세: {signal['indicators']['trend_direction']}",
            f"• 모멘텀: {signal['indicators']['momentum_score']:.3f}",
            f"• 변동성: {signal['indicators']['volatility']:.1%}",
            f"• 지지선: ${signal['indicators']['support_level']:.2f}",
            f"• 저항선: ${signal['indicators']['resistance_level']:.2f}",
            "",
            " **AI 분석**:",
            f"{signal['llm_analysis']}",
            "",
            f"🕒 **발생시간**: {signal['timestamp'].strftime('%H:%M:%S')}",
            f"🆔 **신호ID**: {signal['signal_id']}",
            "",
            "📝 *이 신호는 참고용이며, 투자 책임은 본인에게 있습니다.*"
        ]

        return "\n".join(message_parts)

    def send_telegram(self, message: str) -> bool:
        """텔레그램 메시지 전송"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] 텔레그램 전송 실패: {e}")
            return False

    def send_signal_notification(self, signal: Dict):
        """신호 알림 전송"""
        try:
            message = self.format_signal_message(signal)
            success = self.send_telegram(message)

            if success:
                # 신호 기록 업데이트
                self.last_signals[signal["symbol"]] = {
                    "action": signal["action"],
                    "confidence": signal["confidence"],
                    "timestamp": signal["timestamp"]
                }

                # 신호 히스토리 저장
                self.signal_history.append({
                    "timestamp": signal["timestamp"].isoformat(),
                    "symbol": signal["symbol"],
                    "action": signal["action"],
                    "confidence": signal["confidence"],
                    "current_price": signal["current_price"],
                    "expected_return": signal["expected_return"]
                })

                # 카운터 증가
                self.daily_signal_count += 1

                print(f"[OK] {signal['symbol']} 신호 전송 완료: {signal['action']} (신뢰도: {signal['confidence']:.1%})")
            else:
                print(f"[FAIL] {signal['symbol']} 신호 전송 실패")

        except Exception as e:
            print(f"[ERROR] 신호 알림 전송 오류: {e}")

    def reset_daily_counter(self):
        """일일 카운터 리셋"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_signal_count = 0
            self.last_reset_date = today

    def run_analysis_cycle(self):
        """분석 사이클 실행"""
        try:
            print(f"\n[ANALYZE] 시장 분석 중... ({datetime.now().strftime('%H:%M:%S')})")

            # 데이터 수집
            nvdl_data = self.get_stock_data("NVDL")
            nvdd_data = self.get_stock_data("NVDD")

            if not nvdl_data or not nvdd_data:
                print("[ERROR] 가격 데이터 수집 실패")
                return

            print(f"[PRICE] NVDL: ${nvdl_data['price']:.2f} ({nvdl_data['change_percent']:+.2f}%)")
            print(f"[PRICE] NVDD: ${nvdd_data['price']:.2f} ({nvdd_data['change_percent']:+.2f}%)")

            # 기술적 지표 계산
            nvdl_indicators = self.calculate_technical_indicators(nvdl_data)
            nvdd_indicators = self.calculate_technical_indicators(nvdd_data)

            # LLM 분석
            print("[LLM] AI 분석 중...")
            llm_analysis = self.llm_analyze(nvdl_data, nvdd_data, nvdl_indicators, nvdd_indicators)
            print(f"[LLM] 분석 완료: {len(llm_analysis)}자")

            # 신호 생성 및 전송
            for symbol, data, indicators in [
                ("NVDL", nvdl_data, nvdl_indicators),
                ("NVDD", nvdd_data, nvdd_indicators)
            ]:
                signal = self.generate_signal(symbol, data, indicators, llm_analysis)

                if signal and signal["action"] in ["BUY", "SELL"]:
                    self.send_signal_notification(signal)
                elif signal:
                    print(f"[SKIP] {symbol} - 신뢰도 부족 ({signal['confidence']:.1%})")
                else:
                    print(f"[HOLD] {symbol} - 관망")

        except Exception as e:
            print(f"[ERROR] 분석 사이클 오류: {e}")

    def run(self):
        """메인 실행 루프"""
        print("[START] 완전 기능 NVIDIA LLM 신호 시스템 시작")
        print(f"[INFO] 체크 간격: {self.config['check_interval']//60}분")
        print(f"[INFO] 최소 신뢰도: {self.config['min_confidence']:.1%}")
        print(f"[INFO] 일일 최대 신호: {self.config['max_daily_signals']}개")
        print("=" * 50)

        while True:
            try:
                # 일일 카운터 리셋
                self.reset_daily_counter()

                # 일일 신호 제한 체크
                if self.daily_signal_count >= self.config['max_daily_signals']:
                    print(f"[LIMIT] 일일 신호 한도 달성 ({self.daily_signal_count}/{self.config['max_daily_signals']})")
                    time.sleep(self.config['check_interval'])
                    continue

                # 분석 사이클 실행
                self.run_analysis_cycle()

                print(f"[WAIT] {self.config['check_interval']//60}분 대기 중...")
                time.sleep(self.config['check_interval'])

            except KeyboardInterrupt:
                print("\n[EXIT] 사용자 중단 - 프로그램 종료")
                break
            except Exception as e:
                print(f"[ERROR] 시스템 오류: {e}")
                print("[RETRY] 1분 후 재시도...")
                time.sleep(60)

if __name__ == "__main__":
    signal_system = FullFeatureNVIDIASignal()
    signal_system.run()