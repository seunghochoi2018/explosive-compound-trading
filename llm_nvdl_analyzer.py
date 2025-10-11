#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVDL/NVDQ 전용 LLM 시장 분석기
- NVIDIA 레버리지 ETF 특화 분석
- 반도체/AI 섹터 맥락 포함
- 변동성 높은 3x 레버리지 상품 최적화
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class NVDLLLMAnalyzer:
    def __init__(self, model_name: str = "qwen2.5:32b"):
        """
        NVDL/NVDQ 전용 LLM 분석기

        주석: 사용자 요청 "코드4 엔비디아봇에도 적용해"
        - qwen2.5:32b - 7b 대비 4배 이상 성능
        - NVDL 변동성에 더 정확한 대응

        Args:
            model_name: 사용할 LLM 모델명
        """
        print("=== NVDL/NVDQ LLM 분석 시스템 ===")

        self.model_name = model_name
        self.ollama_url = "http://localhost:11434"

        # NVDL/NVDQ 특화 프롬프트
        self.analysis_prompts = {
            'nvdl_analysis': """
당신은 NVIDIA 레버리지 ETF 전문 트레이더입니다. NVDL은 NVIDIA 3배 매수, NVDQ는 NVIDIA 3배 공매도 ETF입니다.

**핵심 목표: 포트폴리오 가치를 지속적으로 증가** 
- 사용자: "잔고기준으로 체크하면안돼? 이더잔고를 계속체크하니까 잔고가 계속 늘어나게끔 학습하면되잖아"
- 사용자: "그럼 자연스레 수수료도 인식할꺼고"
- 과거 거래 데이터에는 실제 포트폴리오 가치 변화가 기록됨
- 가격 수익이 나도 포트폴리오가 줄었다면 실패!
- 수수료는 자연스럽게 포트폴리오 변화에 반영됨

[현재 시장 상황]
- NVDL 가격: ${nvdl_price}
- NVDQ 가격: ${nvdq_price}
- 최근 NVDL 가격 추이: {nvdl_history}
- 최근 NVDQ 가격 추이: {nvdq_history}
- 상대적 강도: {relative_strength}
- 시간: {timestamp}

[기술적 분석]
- NVDL 모멘텀: {nvdl_momentum}%
- NVDQ 모멘텀: {nvdq_momentum}%
- 변동성: {volatility}%
- RSI 수준: {rsi_level}

[섹터 맥락]
- AI/반도체 섹터 동향
- 3x 레버리지 특성 (높은 변동성, 시간 가치 손실)
- 포지션 로테이션 신호

[현재 포지션]
- 보유 종목: {current_symbol}
- 포지션 손익: {position_pnl}%
- 보유 시간: {holding_time}

[과거 거래 학습 데이터] 📚 Few-shot Learning
사용자 요청: "과거 실제데이터를 학습해서 판단하는게 훨씬 좋지않아?"
{learning_examples}

 위 과거 사례를 참고하여 같은 실수를 반복하지 마세요!
- **성공 패턴**: 어떤 상황에서 포트폴리오 가치가 늘었는가?
- **실패 패턴**: 어떤 판단이 포트폴리오 가치 감소로 이어졌는가?
- **핵심**: 가격 수익이 나도 포트폴리오가 줄면 실패! 포트폴리오가 늘어야 성공!

다음 형식으로 응답하세요:
NVDL_SIGNAL: [0-100 점수] (NVDL 매수 신호)
NVDQ_SIGNAL: [0-100 점수] (NVDQ 매수 신호)
ROTATION_SIGNAL: [0-100 점수] (포지션 전환 신호)
HOLD_SIGNAL: [0-100 점수] (현 포지션 유지)
CONFIDENCE: [0-100 종합 신뢰도]
PRIMARY_RECOMMENDATION: [NVDL/NVDQ/HOLD/EXIT]
REASONING: [3줄 이내 핵심 근거]
RISK_WARNING: [HIGH/MEDIUM/LOW + 위험 요소]
EXPECTED_DURATION: [예상 포지션 보유 시간: 분 단위]
""",

            'risk_assessment': """
NVDL/NVDQ 리스크 관리 전문가로서 현재 포지션을 평가하세요.

[포지션 정보]
- 보유 종목: {symbol}
- 진입가: ${entry_price}
- 현재가: ${current_price}
- 손익률: {pnl_pct}%
- 보유 시간: {holding_minutes}분
- 일일 최대 손실: {daily_drawdown}%

[3x 레버리지 ETF 특성]
- 높은 변동성으로 인한 빠른 손익 변화
- 시간 가치 손실 (Time Decay)
- 장기 보유 시 위험 증가

[평가 요청]
EXIT_URGENCY: [0-100] (즉시 청산 필요성)
STOP_LOSS_PRICE: [권장 손절가]
TAKE_PROFIT_PRICE: [권장 익절가]
POSITION_SIZE_ADVICE: [REDUCE/MAINTAIN/INCREASE]
MAX_HOLD_TIME: [권장 최대 보유시간: 분]
RISK_LEVEL: [EXTREME/HIGH/MEDIUM/LOW]
"""
        }

        # 연결 테스트
        self.test_connection()

    def test_connection(self) -> bool:
        """Ollama 연결 테스트"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                available_models = [m['name'] for m in models]
                print(f"[LLM] Ollama 연결 성공")
                print(f"[LLM] 사용 가능한 모델: {available_models}")

                if self.model_name not in available_models:
                    print(f"[WARNING] {self.model_name} 모델이 없습니다.")
                    return False
                return True
            else:
                print(f"[ERROR] Ollama 연결 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Ollama 연결 오류: {e}")
            return False

    def query_llm(self, prompt: str, temperature: float = 0.1) -> str:
        """LLM에 질의"""
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

            # 진행 상황 로그 추가 (시간 정보 포함)
            from datetime import datetime
            import time
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"[{current_time}] [LLM_PROGRESS] LLM에 요청 전송 중... (모델: {self.model_name})")
            start_time = time.time()

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=data,
                timeout=1800  # 주석: 32b 모델용 타임아웃 증가 (30분, 두 봇 동시 실행 시 충분한 시간 확보)
            )

            if response.status_code == 200:
                elapsed_time = time.time() - start_time
                completion_time = datetime.now().strftime("%H:%M:%S")
                if elapsed_time >= 60:
                    time_str = f"{int(elapsed_time // 60)}분 {int(elapsed_time % 60)}초"
                else:
                    time_str = f"{elapsed_time:.1f}초"
                print(f"[{completion_time}] [LLM_PROGRESS] LLM 응답 수신 완료! (소요 시간: {time_str})")
                result = response.json()
                return result.get('response', '')
            else:
                print(f"[ERROR] LLM 질의 실패: {response.status_code}")
                return ""

        except Exception as e:
            print(f"[ERROR] LLM 질의 오류: {e}")
            return ""

    def analyze_nvdl_nvdq(self,
                         nvdl_price: float,
                         nvdq_price: float,
                         nvdl_history: List[float],
                         nvdq_history: List[float],
                         current_symbol: str = "NONE",
                         position_pnl: float = 0.0,
                         holding_minutes: int = 0,
                         learning_examples: str = None) -> Dict:
        """
        NVDL/NVDQ 종합 분석

        Returns:
            분석 결과 딕셔너리
        """

        if len(nvdl_history) < 3 or len(nvdq_history) < 3:
            return self._fallback_analysis()

        # 기술적 지표 계산
        nvdl_momentum = self._calculate_momentum(nvdl_history)
        nvdq_momentum = self._calculate_momentum(nvdq_history)
        volatility = self._calculate_volatility(nvdl_history + nvdq_history)
        relative_strength = nvdl_momentum - nvdq_momentum
        rsi_level = self._calculate_rsi(nvdl_history)

        # 보유 시간 표시
        if holding_minutes > 60:
            holding_time = f"{holding_minutes//60}시간 {holding_minutes%60}분"
        else:
            holding_time = f"{holding_minutes}분"

        # 학습 데이터 추가 (주석: 사용자 요청 "과거 실제데이터를 학습해서 판단")
        if not learning_examples:
            learning_examples = "과거 거래 기록 없음 (처음 시작)"

        # 프롬프트 구성 + Few-shot Learning
        prompt = self.analysis_prompts['nvdl_analysis'].format(
            nvdl_price=nvdl_price,
            nvdq_price=nvdq_price,
            nvdl_history=nvdl_history[-10:],
            nvdq_history=nvdq_history[-10:],
            relative_strength=f"{relative_strength:+.2f}%",
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            nvdl_momentum=f"{nvdl_momentum:+.2f}",
            nvdq_momentum=f"{nvdq_momentum:+.2f}",
            volatility=f"{volatility:.2f}",
            rsi_level=f"{rsi_level:.1f}",
            current_symbol=current_symbol,
            position_pnl=position_pnl,
            holding_time=holding_time,
            learning_examples=learning_examples
        )

        print(f"[LLM] NVDL/NVDQ 분석 중... (NVDL: ${nvdl_price}, NVDQ: ${nvdq_price})")

        # LLM 분석 실행
        llm_response = self.query_llm(prompt, temperature=0.1)

        # 응답 파싱
        analysis = self._parse_nvdl_response(llm_response)

        # 메타데이터 추가
        analysis['timestamp'] = datetime.now().isoformat()
        analysis['model_used'] = self.model_name
        analysis['raw_response'] = llm_response
        analysis['nvdl_momentum'] = nvdl_momentum
        analysis['nvdq_momentum'] = nvdq_momentum
        analysis['relative_strength'] = relative_strength

        return analysis

    def assess_position_risk(self,
                           symbol: str,
                           entry_price: float,
                           current_price: float,
                           pnl_pct: float,
                           holding_minutes: int,
                           daily_drawdown: float) -> Dict:
        """포지션 리스크 평가"""

        prompt = self.analysis_prompts['risk_assessment'].format(
            symbol=symbol,
            entry_price=entry_price,
            current_price=current_price,
            pnl_pct=pnl_pct,
            holding_minutes=holding_minutes,
            daily_drawdown=daily_drawdown
        )

        print(f"[LLM] 포지션 리스크 평가: {symbol} ({pnl_pct:+.2f}%)")

        llm_response = self.query_llm(prompt, temperature=0.05)

        return self._parse_risk_response(llm_response)

    def _calculate_momentum(self, prices: List[float]) -> float:
        """모멘텀 계산"""
        if len(prices) < 3:
            return 0.0
        return (prices[-1] - prices[-3]) / prices[-3] * 100

    def _calculate_volatility(self, prices: List[float]) -> float:
        """변동성 계산"""
        if len(prices) < 5:
            return 0.0

        changes = []
        for i in range(1, len(prices)):
            change = (prices[i] - prices[i-1]) / prices[i-1]
            changes.append(change)

        if not changes:
            return 0.0

        variance = sum((x - sum(changes)/len(changes))**2 for x in changes) / len(changes)
        return (variance ** 0.5) * 100

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """RSI 계산"""
        if len(prices) < period + 1:
            return 50.0

        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-change)

        if len(gains) < period:
            return 50.0

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _parse_nvdl_response(self, response: str) -> Dict:
        """NVDL 분석 응답 파싱"""
        result = {
            'nvdl_signal': 0,
            'nvdq_signal': 0,
            'rotation_signal': 0,
            'hold_signal': 0,
            'confidence': 0,
            'primary_recommendation': 'HOLD',
            'reasoning': '응답 파싱 실패',
            'risk_warning': 'HIGH - 파싱 실패',
            'expected_duration': 60,
            'parsed_successfully': False
        }

        try:
            lines = response.strip().split('\n')

            for line in lines:
                line = line.strip()
                if 'NVDL_SIGNAL:' in line:
                    result['nvdl_signal'] = self._extract_number(line)
                elif 'NVDQ_SIGNAL:' in line:
                    result['nvdq_signal'] = self._extract_number(line)
                elif 'ROTATION_SIGNAL:' in line:
                    result['rotation_signal'] = self._extract_number(line)
                elif 'HOLD_SIGNAL:' in line:
                    result['hold_signal'] = self._extract_number(line)
                elif 'CONFIDENCE:' in line:
                    result['confidence'] = self._extract_number(line)
                elif 'PRIMARY_RECOMMENDATION:' in line:
                    result['primary_recommendation'] = line.split(':', 1)[1].strip()
                elif 'REASONING:' in line:
                    result['reasoning'] = line.split(':', 1)[1].strip()
                elif 'RISK_WARNING:' in line:
                    result['risk_warning'] = line.split(':', 1)[1].strip()
                elif 'EXPECTED_DURATION:' in line:
                    result['expected_duration'] = self._extract_number(line)

            result['parsed_successfully'] = True

        except Exception as e:
            print(f"[WARNING] LLM 응답 파싱 오류: {e}")

        return result

    def _parse_risk_response(self, response: str) -> Dict:
        """리스크 평가 응답 파싱"""
        result = {
            'exit_urgency': 0,
            'stop_loss_price': 0,
            'take_profit_price': 0,
            'position_size_advice': 'MAINTAIN',
            'max_hold_time': 60,
            'risk_level': 'HIGH'
        }

        try:
            lines = response.strip().split('\n')

            for line in lines:
                line = line.strip()
                if 'EXIT_URGENCY:' in line:
                    result['exit_urgency'] = self._extract_number(line)
                elif 'STOP_LOSS_PRICE:' in line:
                    result['stop_loss_price'] = self._extract_number(line, allow_negative=True)
                elif 'TAKE_PROFIT_PRICE:' in line:
                    result['take_profit_price'] = self._extract_number(line, allow_negative=True)
                elif 'POSITION_SIZE_ADVICE:' in line:
                    result['position_size_advice'] = line.split(':', 1)[1].strip()
                elif 'MAX_HOLD_TIME:' in line:
                    result['max_hold_time'] = self._extract_number(line)
                elif 'RISK_LEVEL:' in line:
                    result['risk_level'] = line.split(':', 1)[1].strip()

        except Exception as e:
            print(f"[WARNING] 리스크 응답 파싱 오류: {e}")

        return result

    def _extract_number(self, text: str, allow_negative: bool = False) -> float:
        """텍스트에서 숫자 추출"""
        import re

        if allow_negative:
            match = re.search(r'-?\d+\.?\d*', text)
        else:
            match = re.search(r'\d+\.?\d*', text)

        if match:
            return float(match.group())
        return 0.0

    def _fallback_analysis(self) -> Dict:
        """LLM 실패 시 기본 분석"""
        return {
            'nvdl_signal': 50,
            'nvdq_signal': 50,
            'rotation_signal': 50,
            'hold_signal': 50,
            'confidence': 10,
            'primary_recommendation': 'HOLD',
            'reasoning': 'LLM 분석 실패 - 기본값 반환',
            'risk_warning': 'HIGH - 분석 실패',
            'expected_duration': 60,
            'parsed_successfully': False,
            'timestamp': datetime.now().isoformat(),
            'model_used': 'fallback'
        }

def main():
    """테스트 실행"""
    analyzer = NVDLLLMAnalyzer()

    # 샘플 데이터로 테스트
    nvdl_prices = [45.2, 46.1, 45.8, 47.2, 46.5]
    nvdq_prices = [18.8, 18.3, 18.5, 17.9, 18.2]

    print("\n=== NVDL/NVDQ 분석 테스트 ===")
    result = analyzer.analyze_nvdl_nvdq(
        nvdl_price=46.5,
        nvdq_price=18.2,
        nvdl_history=nvdl_prices,
        nvdq_history=nvdq_prices,
        current_symbol="NVDL",
        position_pnl=2.8,
        holding_minutes=45
    )

    print(f"NVDL 신호: {result['nvdl_signal']}/100")
    print(f"NVDQ 신호: {result['nvdq_signal']}/100")
    print(f"로테이션 신호: {result['rotation_signal']}/100")
    print(f"홀드 신호: {result['hold_signal']}/100")
    print(f"신뢰도: {result['confidence']}/100")
    print(f"추천: {result['primary_recommendation']}")
    print(f"근거: {result['reasoning']}")

if __name__ == "__main__":
    main()