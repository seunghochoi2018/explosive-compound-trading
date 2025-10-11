#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ LLM 강화 텔레그램 신호 알림 전용 프로그램
- 자동매매 없이 신호만 알림
- LLM 분석 추가로 더 정확한 신호
- 상세한 분석 정보 제공
- 수동 거래를 위한 완벽한 가이드
"""

import json
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import pickle
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 자체 모듈 임포트
from nvdl_nvdq_data_collector import NVDLNVDQDataCollector
from nvdl_nvdq_trading_model import NVDLNVDQTradingModel
from telegram_notifier import TelegramNotifier

@dataclass
class TradingSignal:
    """거래 신호 데이터 클래스"""
    timestamp: datetime
    symbol: str                    # 'NVDL' or 'NVDQ'
    action: str                    # 'BUY', 'SELL', 'HOLD'
    confidence: float              # 0.0 ~ 1.0
    current_price: float
    target_price: float            # 목표가
    stop_loss: float              # 손절가
    expected_return: float         # 예상 수익률 (%)
    holding_period: str           # 예상 보유 기간
    risk_level: str               # 'LOW', 'MEDIUM', 'HIGH'
    analysis: Dict                # 상세 분석 정보
    llm_analysis: str = ""        # LLM 분석 결과
    signal_id: str = None         # 고유 신호 ID

class LLMAnalyzer:
    """LLM 분석기 클래스"""

    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "qwen2.5:14b"  #  가장 똑똑한 14B 모델로 업그레이드!

    def analyze_nvidia_signals(self, nvdl_price: float, nvdd_price: float,
                             nvdl_indicators: Dict, nvdd_indicators: Dict) -> str:
        """NVIDIA 신호에 대한 LLM 분석"""

        # 기술적 지표 요약
        nvdl_rsi = nvdl_indicators.get('rsi', 50)
        nvdd_rsi = nvdd_indicators.get('rsi', 50)
        nvdl_trend = nvdl_indicators.get('trend_direction', '중립')
        nvdd_trend = nvdd_indicators.get('trend_direction', '중립')

        #  14B 모델 전용 복리효과 극대화 NVIDIA 추세 감지 프롬프트
        prompt = f""" 당신은 qwen2.5:14B 모델의 최고 지능을 활용하는 NVIDIA 복리 전문 AI 트레이더입니다.

 현재 NVIDIA 레버리지 ETF 분석:
- NVDL (3배 레버리지): ${nvdl_price:.2f}
- NVDD (인버스): ${nvdd_price:.2f}
- NVDL RSI: {nvdl_rsi:.1f} | NVDD RSI: {nvdd_rsi:.1f}
- NVDL 추세: {nvdl_trend} | NVDD 추세: {nvdd_trend}

 복리효과 극대화 목표:
1. 레버리지 ETF 추세 전환 조기 감지 → 즉시 신호 발송
2. 작은 움직임도 3배 레버리지로 증폭되므로 정확한 타이밍이 복리의 핵심
3. 손실 방지가 가장 중요 (3배 레버리지에서 손실은 더 크게 확대)

 14B 모델 지능 활용 포인트:
- NVIDIA 반도체 생태계와 AI 트렌드 상관관계 분석
- 레버리지 ETF 특성을 고려한 변곡점 감지
- 복리 관점에서 최적 진입/청산 시점 예측

 핵심 질문: 지금이 NVIDIA 추세 전환의 시작점인가?

NVDL_BUY - 14B 지능으로 NVIDIA 상승 추세 감지, 복리를 위한 NVDL 매수 신호
NVDD_BUY - NVIDIA 하락 추세 감지, NVDD 매수로 하락장에서도 복리 기회
HOLD - 추세 지속 확신, 더 큰 복리 기회 대기

 14B 모델 최종 판단:"""

        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_ctx": 2048,  # 14B 모델용 확장 컨텍스트
                        "num_predict": 100  # 더 상세한 분석을 위한 긴 응답
                    }
                },
                timeout=45  # 14B 모델을 위한 충분한 시간
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

class NVDLNVDQLLMSignalNotifier:
    """NVDL/NVDQ LLM 강화 신호 알림 시스템"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.data_collector = NVDLNVDQDataCollector(api_key)
        self.trading_model = NVDLNVDQTradingModel(fmp_api_key=api_key)
        self.telegram = TelegramNotifier()
        self.llm_analyzer = LLMAnalyzer()

        # 설정
        self.config = {
            'check_interval': 300,     # 5분
            'min_confidence': 0.6,     # 최소 신뢰도
            'max_daily_signals': 10,   # 일일 최대 신호 수
            'cooldown_period': 1800,   # 같은 종목 재신호 간격 (30분)
        }

        # 상태 관리
        self.last_signals = {}         # 마지막 신호 기록
        self.signal_history = []       # 신호 히스토리
        self.daily_signal_count = 0    # 일일 신호 수
        self.last_reset_date = datetime.now().date()

        # 데이터 로드
        self.load_signal_history()

        print("[OK] NVDL/NVDQ LLM 강화 신호 알림 시스템 초기화 완료")

    def load_signal_history(self):
        """신호 히스토리 로드"""
        try:
            with open('nvdl_nvdd_llm_signal_history.json', 'r') as f:
                self.signal_history = json.load(f)
        except FileNotFoundError:
            self.signal_history = []

    def save_signal_history(self):
        """신호 히스토리 저장"""
        with open('nvdl_nvdd_llm_signal_history.json', 'w') as f:
            json.dump(self.signal_history, f, indent=2)

    def analyze_market_conditions(self) -> Dict:
        """시장 상황 분석"""
        try:
            # 데이터 수집
            nvdl_data = self.data_collector.get_stock_data('NVDL', period='1d', interval='5m')
            nvdd_data = self.data_collector.get_stock_data('NVDD', period='1d', interval='5m')

            if nvdl_data.empty or nvdd_data.empty:
                return None

            # 현재 가격
            nvdl_price = nvdl_data['Close'].iloc[-1]
            nvdd_price = nvdd_data['Close'].iloc[-1]

            # 기술적 지표 계산
            nvdl_indicators = self.data_collector.calculate_technical_indicators(nvdl_data)
            nvdd_indicators = self.data_collector.calculate_technical_indicators(nvdd_data)

            # LLM 분석 수행
            llm_analysis = self.llm_analyzer.analyze_nvidia_signals(
                nvdl_price, nvdd_price, nvdl_indicators, nvdd_indicators
            )

            return {
                'nvdl': {
                    'price': nvdl_price,
                    'data': nvdl_data,
                    'indicators': nvdl_indicators
                },
                'nvdd': {
                    'price': nvdd_price,
                    'data': nvdd_data,
                    'indicators': nvdd_indicators
                },
                'llm_analysis': llm_analysis,
                'timestamp': datetime.now()
            }

        except Exception as e:
            print(f"시장 상황 분석 오류: {e}")
            return None

    def generate_signal(self, symbol: str, market_data: Dict) -> Optional[TradingSignal]:
        """신호 생성"""
        try:
            symbol_data = market_data[symbol.lower()]
            data = symbol_data['data']
            indicators = symbol_data['indicators']
            current_price = symbol_data['price']

            # 기본 모델 예측
            features = self.trading_model.prepare_features(data, indicators)
            prediction = self.trading_model.predict(features)

            if prediction is None:
                return None

            action, confidence = prediction

            # 최소 신뢰도 체크
            if confidence < self.config['min_confidence']:
                return None

            # 쿨다운 체크
            if self._is_in_cooldown(symbol):
                return None

            # 목표가/손절가 계산
            volatility = indicators.get('volatility', 0.02)

            if action == 'BUY':
                target_price = current_price * (1 + volatility * 2)
                stop_loss = current_price * (1 - volatility * 1.5)
                expected_return = volatility * 200  # %
            else:  # SELL
                target_price = current_price * (1 - volatility * 2)
                stop_loss = current_price * (1 + volatility * 1.5)
                expected_return = volatility * 200  # %

            # 리스크 레벨 계산
            if confidence > 0.8:
                risk_level = 'LOW'
                holding_period = '단기 (1-3일)'
            elif confidence > 0.6:
                risk_level = 'MEDIUM'
                holding_period = '중기 (3-7일)'
            else:
                risk_level = 'HIGH'
                holding_period = '장기 (1-2주)'

            # 상세 분석 정보
            analysis = {
                'rsi': indicators.get('rsi', 50),
                'trend': indicators.get('trend_direction', '중립'),
                'momentum': indicators.get('momentum_score', 0),
                'volatility': volatility,
                'support': indicators.get('support_level', current_price * 0.95),
                'resistance': indicators.get('resistance_level', current_price * 1.05),
                'volume_trend': indicators.get('volume_trend', '보통')
            }

            # 신호 생성
            signal = TradingSignal(
                timestamp=datetime.now(),
                symbol=symbol,
                action=action,
                confidence=confidence,
                current_price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                expected_return=expected_return,
                holding_period=holding_period,
                risk_level=risk_level,
                analysis=analysis,
                llm_analysis=market_data['llm_analysis'],
                signal_id=f"{symbol}_{int(time.time())}"
            )

            return signal

        except Exception as e:
            print(f"{symbol} 신호 생성 오류: {e}")
            return None

    def _is_in_cooldown(self, symbol: str) -> bool:
        """쿨다운 체크"""
        if symbol not in self.last_signals:
            return False

        last_time = self.last_signals[symbol]['timestamp']
        cooldown_end = last_time + timedelta(seconds=self.config['cooldown_period'])

        return datetime.now() < cooldown_end

    def format_signal_message(self, signal: TradingSignal) -> str:
        """신호 메시지 포맷팅"""

        # 이모지 설정
        action_emoji = "🟢" if signal.action == "BUY" else "🔴"
        risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}[signal.risk_level]

        # 가격 변화 방향 계산
        price_change = ((signal.target_price - signal.current_price) / signal.current_price) * 100
        price_emoji = "" if price_change > 0 else ""

        message_parts = [
            f"{action_emoji} **{signal.symbol} {signal.action} 신호**",
            "",
            f" **현재가**: ${signal.current_price:.2f}",
            f" **목표가**: ${signal.target_price:.2f} ({price_change:+.1f}%)",
            f"🛡️ **손절가**: ${signal.stop_loss:.2f}",
            f" **신뢰도**: {signal.confidence:.1%}",
            f"{risk_emoji} **리스크**: {signal.risk_level}",
            f"⏰ **보유기간**: {signal.holding_period}",
            f" **예상수익**: {signal.expected_return:.1f}%",
            "",
            " **기술적 분석**:",
            f"• RSI: {signal.analysis['rsi']:.1f}",
            f"• 추세: {signal.analysis['trend']}",
            f"• 모멘텀: {signal.analysis['momentum']:.3f}",
            f"• 변동성: {signal.analysis['volatility']:.1%}",
            f"• 지지선: ${signal.analysis['support']:.2f}",
            f"• 저항선: ${signal.analysis['resistance']:.2f}",
            "",
            " **AI 분석**:",
            f"{signal.llm_analysis}",
            "",
            f"🕒 **발생시간**: {signal.timestamp.strftime('%H:%M:%S')}",
            f"🆔 **신호ID**: {signal.signal_id}",
            "",
            "📝 *이 신호는 참고용이며, 투자 책임은 본인에게 있습니다.*"
        ]

        return "\n".join(message_parts)

    def send_signal_notification(self, signal: TradingSignal):
        """신호 알림 전송"""
        try:
            message = self.format_signal_message(signal)
            success = self.telegram.send_message(message)

            if success:
                # 신호 기록 업데이트
                self.last_signals[signal.symbol] = {
                    'action': signal.action,
                    'confidence': signal.confidence,
                    'timestamp': signal.timestamp
                }

                # 신호 히스토리 저장
                self.signal_history.append({
                    'timestamp': signal.timestamp.isoformat(),
                    'symbol': signal.symbol,
                    'action': signal.action,
                    'confidence': signal.confidence,
                    'current_price': signal.current_price,
                    'expected_return': signal.expected_return,
                    'llm_analysis': signal.llm_analysis
                })

                # 카운터 증가
                self.daily_signal_count += 1

                print(f"[OK] {signal.symbol} LLM 신호 전송 완료: {signal.action} (신뢰도: {signal.confidence:.1%})")
            else:
                print(f"[FAIL] {signal.symbol} 신호 전송 실패")

        except Exception as e:
            print(f"신호 알림 전송 오류: {e}")

    def reset_daily_counter(self):
        """일일 카운터 리셋"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_signal_count = 0
            self.last_reset_date = today

    def run(self):
        """메인 실행 루프"""
        print("[START] NVDL/NVDQ LLM 강화 신호 알림 시스템 시작")
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

                print(f"\n[ANALYZE] 시장 분석 중... ({datetime.now().strftime('%H:%M:%S')})")

                # 시장 상황 분석
                market_data = self.analyze_market_conditions()

                if market_data is None:
                    print("[ERROR] 시장 데이터 수집 실패")
                    time.sleep(self.config['check_interval'])
                    continue

                print(f"[PRICE] NVDL: ${market_data['nvdl']['price']:.2f}")
                print(f"[PRICE] NVDD: ${market_data['nvdd']['price']:.2f}")
                print(f"[LLM] LLM 분석 완료")

                # 각 종목별 신호 생성
                for symbol in ['NVDL', 'NVDD']:
                    signal = self.generate_signal(symbol, market_data)

                    if signal and signal.action in ['BUY', 'SELL']:
                        self.send_signal_notification(signal)

                # 신호 히스토리 저장
                self.save_signal_history()

                print(f"[WAIT] {self.config['check_interval']//60}분 대기 중...")
                time.sleep(self.config['check_interval'])

            except KeyboardInterrupt:
                print("\n[EXIT] 사용자 중단 - 프로그램 종료")
                break
            except Exception as e:
                print(f"[ERROR] 시스템 오류: {e}")
                print("[RETRY] 1분 후 재시도...")
                time.sleep(60)

def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="NVDL/NVDQ LLM 강화 텔레그램 신호 알림 시스템")
    parser.add_argument('--api-key', type=str,
                       default="5j69XWnoSpoBvEY0gKSUTB0zXcr0z2KI",
                       help='FMP API 키')
    parser.add_argument('--interval', type=int, default=5,
                       help='체크 간격 (분)')
    parser.add_argument('--min-confidence', type=float, default=0.6,
                       help='최소 신뢰도 (0.0-1.0)')

    args = parser.parse_args()

    # 신호 알림 시스템 생성
    notifier = NVDLNVDQLLMSignalNotifier(args.api_key)

    # 설정 조정
    notifier.config['check_interval'] = args.interval * 60
    notifier.config['min_confidence'] = args.min_confidence

    # 실행
    notifier.run()

if __name__ == "__main__":
    main()