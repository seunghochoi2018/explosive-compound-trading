# KIS LLM 학습형 트레이딩 시스템 (텔레그램 알림 버전)

## 특징

✅ **14b × 2 병렬 LLM 분석**
- qwen2.5:14b 모델 2개로 추세 돌파 감지
- 학습 데이터로 지속적으로 개선
- SOXL/SOXS 250일 백테스팅 데이터 포함

✅ **자동 학습 시스템**
- 포지션 변경 감지 시 자동으로 학습 데이터에 기록
- 승/패 패턴 분석으로 타이밍 개선
- kis_trade_history.json에 누적 저장

✅ **텔레그램 알림만 (자동 주문 없음)**
- LLM 분석 결과를 텔레그램으로 알림
- 실제 거래는 사용자가 직접 수동 실행
- 포지션 전환 권장 시 알림

✅ **Ollama 자동 시작**
- 프로그램 실행 시 Ollama 자동으로 11435 포트에서 시작
- 수동으로 bat 파일 실행할 필요 없음

## 실행 방법

### 하나의 명령으로 실행

```bash
python kis_llm_learner_with_telegram.py
```

이게 전부입니다! 프로그램이 자동으로:
1. Ollama 11435 포트로 시작
2. 텔레그램 연결 확인
3. 학습 데이터 로드 (kis_trade_history.json, kis_meta_insights.json)
4. 14b × 2 LLM 초기화
5. 5분마다 분석 시작

## 작동 방식

### 1. LLM 분석 (5분마다)
- 현재 시장 데이터 수집 (SOXL/SOXS 가격, 거래량)
- 14b × 2 병렬 LLM으로 추세 분석
- 학습 데이터(29건의 과거 거래)를 참고하여 판단
- 신뢰도 70% 이상이면 텔레그램 알림

### 2. 텔레그램 알림
```
🟢 LLM 분석 신호

⏰ 시간: 2025-10-09 15:30:00

🤖 14b×2 LLM 판단:
  - 신호: 매수 신호
  - 종목: SOXL
  - 신뢰도: 85%

💡 분석 근거:
상승 모멘텀 강화, 거래량 증가

📊 현재 포지션: 없음
```

### 3. 수동 거래
- 알림을 받으면 한국투자증권 앱/웹에서 직접 매매
- 시스템은 다음 분석 때 포지션 변경을 감지

### 4. 자동 학습
- 포지션이 변경되면 자동으로 감지
- 거래 결과(수익률, 진입/청산 가격 등)를 kis_trade_history.json에 저장
- 다음 분석부터 이 데이터를 학습에 활용

## 학습 데이터

### kis_trade_history.json
- SOXL/SOXS 250일 백테스팅 결과
- 59건의 거래 (29건 완료)
- 실제 거래 시 자동으로 추가됨

### kis_meta_insights.json
- 승률: 37.9%
- 평균 수익: +12.60%
- 평균 손실: -11.20%
- LLM이 이 패턴을 학습하여 타이밍 개선

## 분석 주기 변경

기본 5분 간격을 변경하려면 파일 끝부분 수정:

```python
# kis_llm_learner_with_telegram.py 마지막 부분
trader.run(interval_seconds=300)  # 5분
```

다른 주기로 변경:
```python
trader.run(interval_seconds=180)  # 3분
trader.run(interval_seconds=600)  # 10분
```

## 주의사항

### LLM 분석 시간
- 14b × 2 병렬 실행으로 1-2분 소요
- 너무 짧은 간격(1분 이하)은 권장 안 함

### 메모리 사용량
- 14b 모델은 약 8-10GB RAM 사용
- 최소 16GB RAM 권장

### 실제 거래는 본인 판단
- LLM 신호는 참고용
- 최종 결정은 본인이 해야 함
- 손실 책임은 본인에게 있음

## 프로그램 종료

터미널에서 `Ctrl+C` 키를 누르면 종료됩니다.

## 파일 구성

- `kis_llm_learner_with_telegram.py` - 메인 프로그램 ⭐ 이것만 실행!
- `generate_soxl_learning_data.py` - 학습 데이터 생성 (이미 실행됨)
- `kis_trade_history.json` - 거래 히스토리 (59건)
- `kis_meta_insights.json` - 학습 패턴
- `telegram_config.json` - 텔레그램 설정
- `kis_devlp.yaml` - KIS API 설정
- `kis_token.json` - API 토큰

## 학습 데이터 재생성

새로운 백테스팅 데이터로 학습을 다시 하려면:

```bash
python generate_soxl_learning_data.py
```

이 명령은:
1. FMP API로 SOXL/SOXS 최근 365일 데이터 수집
2. 이동평균 전략으로 백테스팅
3. kis_trade_history.json과 kis_meta_insights.json 생성
4. 기존 파일을 덮어씀

## 문제 해결

### Ollama 시작 실패
```
[경고] Ollama 시작 실패 - 수동으로 시작해주세요
```
- 수동으로 `start_ollama_11435.bat` 실행
- 또는 Ollama가 이미 실행 중일 수 있음 (무시 가능)

### LLM 응답 없음
- qwen2.5:14b 모델 확인:
  ```bash
  ollama list
  ```
- 없으면 다운로드:
  ```bash
  ollama pull qwen2.5:14b
  ```

### 텔레그램 연결 실패
- `telegram_config.json` 파일의 bot_token과 chat_id 확인

### API 오류
- `kis_devlp.yaml` 파일의 API 키 확인
- `kis_token.json` 만료 시 재생성 필요

## 기술 사양

- **LLM 모델**: qwen2.5:14b × 2 (병렬 앙상블)
- **학습 방식**: Few-shot Learning + 메타 인사이트
- **백테스팅 데이터**: SOXL/SOXS 250일 (29건 완료 거래)
- **Ollama 포트**: 11435
- **분석 간격**: 5분 (조정 가능)
- **알림**: 텔레그램
- **자동 주문**: 없음 (알림만)
