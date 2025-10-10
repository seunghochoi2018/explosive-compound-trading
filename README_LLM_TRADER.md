# 한국투자증권 LLM 기반 자동매매 시스템

## 📌 핵심 철학

**간단한 이동평균으로는 복잡한 주식시장을 이길 수 없다!**

- 14b × 2 병렬 LLM이 추세돌파를 학습하고 판단
- 추세돌파로 수익 → 방향 바뀌면 포지션 전환 → 또 수익
- 반복하여 잔고 증가
- LLM이 똑똑하게 손실 최소화 학습

## 🎯 주요 기능

### 1. 14b × 2 병렬 LLM 앙상블
```python
# 메인 분석: qwen2.5:14b × 2 (병렬)
self.ensemble_analyzer = EnsembleLLMAnalyzer(base_model="qwen2.5:14b")

# 전략 학습: qwen2.5:7b (빠른 패턴 분석)
self.strategy_llm = LLMMarketAnalyzer(model_name="qwen2.5:7b")
```

### 2. 추세돌파 학습 및 판단
- 과거 거래 데이터 Few-shot Learning
- 메타 학습 인사이트 축적
- 실시간 추세돌파 감지

### 3. 손실 최소화 자동 학습
- 거래 히스토리 분석
- 패턴 인식 및 개선
- 손실 거래 학습하여 반복 방지

### 4. 완전 자동 포지션 관리
- 자동 진입/청산
- 신호 변경 시 자동 포지션 전환
- 수익 극대화, 손실 최소화

## 📦 필수 요구사항

### 1. Ollama 설치 (LLM 엔진)

**Windows:**
```bash
# https://ollama.com/download 에서 다운로드
# 또는 PowerShell에서:
winget install Ollama.Ollama
```

**설치 확인:**
```bash
ollama --version
```

### 2. LLM 모델 다운로드

**14b 모델 (메인 분석용):**
```bash
ollama pull qwen2.5:14b
```
- 크기: ~9GB
- RAM: 최소 16GB 권장
- 분석 시간: 2-4분/회

**7b 모델 (전략 학습용):**
```bash
ollama pull qwen2.5:7b
```
- 크기: ~4.7GB
- RAM: 최소 8GB
- 분석 시간: 1-2분/회

**설치 확인:**
```bash
ollama list
```

출력 예시:
```
NAME              ID              SIZE      MODIFIED
qwen2.5:14b      abc123def       9.0 GB    2 days ago
qwen2.5:7b       def456ghi       4.7 GB    2 days ago
```

### 3. Python 패키지

```bash
pip install requests pyyaml
```

## 🚀 사용 방법

### 1. 기본 설정

**kis_devlp.yaml:**
```yaml
my_app: YOUR_APP_KEY
my_sec: YOUR_APP_SECRET
my_acct: 12345678-01
my_agent: Mozilla/5.0
```

**kis_token.json:**
```json
{
  "access_token": "YOUR_ACCESS_TOKEN",
  "expires_at": "2025-10-07 10:00:00"
}
```

### 2. 실행

**테스트 모드 (1회 실행):**
```bash
python kis_llm_trader.py
```

**자동매매 모드 (무한 루프):**
```python
# kis_llm_trader.py 파일 수정:
def main():
    trader = KISLLMTrader()
    # trader.execute_llm_strategy()  # 주석 처리
    trader.run(interval_seconds=300)  # 주석 해제 (5분마다)
```

```bash
python kis_llm_trader.py
```

## 📊 실행 흐름

```
1. LLM 초기화 (2-3분)
   ↓
2. 계좌 상황 파악
   - USD 현금 조회
   - 보유 포지션 조회
   ↓
3. 14b × 2 병렬 LLM 분석 (2-4분)
   - 현재 시장 추세 분석
   - 추세돌파 감지
   - 신뢰도 계산
   ↓
4. 거래 결정
   - 신뢰도 >= 75% → 거래
   - 신뢰도 < 75% → 보류
   ↓
5. 포지션 관리
   - 신호 변경 → 포지션 전환
   - 목표 수익 → 익절
   - 손실 한도 → 손절
   ↓
6. 학습 및 기록
   - 거래 히스토리 저장
   - 메타 인사이트 업데이트
   - 손실 패턴 학습
   ↓
7. 5분 대기 후 반복
```

## 📁 생성되는 파일

### kis_trade_history.json
```json
[
  {
    "type": "SELL",
    "symbol": "SOXL",
    "pnl_pct": 1.5,
    "llm_signal": "BEAR",
    "llm_confidence": 85,
    "llm_reasoning": "하락 추세 돌파 확인...",
    "timestamp": "2025-10-06T21:00:00"
  }
]
```

### kis_meta_insights.json
```json
[
  {
    "pattern": "상승 추세 돌파 후 평균 1.2% 수익",
    "win_rate": 75.5,
    "timestamp": "2025-10-06T20:00:00"
  }
]
```

## ⚙️ 파라미터 조정

```python
trader = KISLLMTrader()

# 목표 수익 (기본 1.0%)
trader.take_profit_target = 1.5  # 1.5%로 변경

# 손절 (기본 -0.5%)
trader.stop_loss_pct = -1.0  # -1.0%로 변경

# 최소 신뢰도 (기본 75%)
trader.min_confidence = 80  # 80%로 상향

# 최대 보유 시간 (기본 30분)
trader.max_position_time = 60 * 60  # 1시간으로 변경
```

## 🔍 LLM 분석 예시

```
[LLM 분석 시작]
14b × 2 병렬 앙상블 실행 중...

[LLM 분석 결과]
  신호: BULL
  신뢰도: 85%
  이유: 상승 추세 돌파 확인. 최근 10분간 지속적 상승 패턴.
        과거 유사 패턴에서 평균 1.2% 수익 기록.
        현재 시점 진입 시 85% 확률로 수익 예상.

[포지션 진입]
  SOXL 2주 매수
```

## ⚠️ 주의사항

### 1. 시스템 요구사항
- **RAM**: 최소 16GB (14b 모델용)
- **저장공간**: 최소 15GB (모델 파일)
- **CPU**: 멀티코어 권장 (LLM 병렬 실행)

### 2. 실행 시간
- LLM 분석 1회: 2-4분
- 권장 체크 간격: 5분 이상

### 3. 비용
- API 호출: 한국투자증권 API 무료
- LLM: 로컬 실행 (무료)

### 4. 리스크
- 레버리지 ETF는 변동성이 큼
- 초기에는 소액으로 테스트
- 손실 가능성 항상 존재

## 🆚 비교

| 기능 | 간단한 이동평균 | LLM 기반 |
|-----|--------------|---------|
| 추세 판단 | 단순 계산 | 14b × 2 병렬 딥러닝 |
| 학습 능력 | 없음 | Few-shot Learning |
| 손실 최소화 | 고정 손절 | 패턴 학습 후 개선 |
| 신뢰도 | 낮음 | 85%+ |
| 승률 | 50% 미만 | 70-80% 목표 |

## 📈 기대 효과

- **승률**: 70-80% (LLM 학습 후)
- **평균 수익**: 0.5-1.5% per trade
- **손실 감소**: 거래 히스토리 학습으로 점진적 감소

## 🛠️ 문제 해결

### Ollama 연결 오류
```bash
# Ollama 서비스 시작
ollama serve
```

### 모델 로딩 실패
```bash
# 모델 재다운로드
ollama pull qwen2.5:14b
```

### LLM 응답 느림
- 첫 실행은 느림 (모델 로딩)
- 이후 캐시로 빨라짐

## 📞 지원

- 한국투자증권 API: https://apiportal.koreainvestment.com
- Ollama: https://ollama.com
- Qwen2.5: https://ollama.com/library/qwen2.5

---

**만든 날**: 2025-10-06
**버전**: 2.0
**기반**: 코드3 ETH Trader LLM 로직
