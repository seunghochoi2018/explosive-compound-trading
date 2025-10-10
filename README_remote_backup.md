# 통합 트레이더 관리 시스템

## 개요
코드3 (ETH 트레이더)와 코드4 (KIS 트레이더)를 동시에 관리하는 통합 시스템

## 주요 기능

### 1. Ollama 지능적 관리
- **독립 포트 실행**: ETH(11434), KIS(11435)
- **메모리 모니터링**: 10GB 초과 시 자동 재시작
- **큐잉 감지**: CPU 0% + 응답 지연 → 자동 재시작
- **타임아웃 자동 복구**: API 응답 없을 시 즉시 재시작
- **응답 시간 패턴 분석**: 최근 3회 연속 5초 이상 → 재시작

### 2. 트레이더 관리
- **자동 시작**: Ollama와 함께 자동 실행
- **크래시 복구**: 프로세스 종료 시 자동 재시작
- **독립 콘솔**: 각 트레이더 별도 창에서 실행

### 3. 주기적 재시작
- **4시간마다**: 전체 시스템 재시작 (GPU 메모리 정리)
- **순차 재시작**: ETH → KIS 순서로 재시작 (동시 충돌 방지)

### 4. 실시간 모니터링
- **1분마다**: Ollama 헬스 체크 + 상태 출력
- **메트릭**: 응답 시간, 메모리, CPU, 프로세스 상태

## 실행 방법

### 1. 모든 기존 프로세스 종료
```powershell
# Ollama 프로세스 종료
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force

# 트레이더 프로세스 종료 (필요시)
Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -like "*trader*"} | Stop-Process -Force
```

### 2. 통합 관리자 실행
```powershell
cd C:\Users\user\Documents\코드5
python unified_trader_manager.py
```

### 3. 실행 확인
다음과 같은 출력이 나오면 정상:
```
[HH:MM:SS] ======================================================================
[HH:MM:SS] 통합 트레이더 관리 시스템 시작
[HH:MM:SS] 재시작 주기: 4시간
[HH:MM:SS] ======================================================================

[HH:MM:SS] [OLLAMA] 시작 중...
[HH:MM:SS] Ollama 포트 11434 시작 완료 (PID: XXXXX)
[HH:MM:SS] Ollama 포트 11435 시작 완료 (PID: XXXXX)

[HH:MM:SS] [TRADER] 시작 중...
[HH:MM:SS] ETH Trader (코드3) 시작 완료 (PID: XXXXX, Ollama: 11434)
[HH:MM:SS] KIS Trader (코드4) 시작 완료 (PID: XXXXX, Ollama: 11435)

[HH:MM:SS] [MONITOR] 모니터링 시작 (Ctrl+C로 종료)

[HH:MM:SS] [STATUS] ETH: OK (Ollama: healthy, 응답: 0.5s, 메모리: 150MB) | KIS: OK (Ollama: healthy, 응답: 0.6s, 메모리: 140MB) | 다음 재시작: 4.0시간 후
```

## 자동 복구 시나리오

### 1. Ollama 타임아웃
```
[HH:MM:SS] [SMART_RESTART] ETH Ollama 재시작 필요: API 타임아웃 (CPU: 0.0%)
[HH:MM:SS] [SMART_RESTART] ETH Trader 종료 중...
[HH:MM:SS] [SMART_RESTART] ETH Ollama 재시작 중...
[HH:MM:SS] [SMART_RESTART] ETH Trader 재시작 중...
```

### 2. 메모리 과다
```
[HH:MM:SS] [SMART_RESTART] KIS Ollama 재시작 필요: 메모리 과다 (12000MB > 10240MB)
```

### 3. 큐잉 감지
```
[HH:MM:SS] [SMART_RESTART] ETH Ollama 재시작 필요: 큐잉 의심 (CPU: 0.2%, 응답: 5.8초)
```

### 4. 트레이더 크래시
```
[HH:MM:SS] [AUTO_RECOVERY] ETH Trader 크래시 → 재시작...
```

## 종료 방법
```
Ctrl + C
```
모든 프로세스 (트레이더 + Ollama) 자동 종료됨

## 설정 변경
`unified_trader_manager.py` 상단에서 변경 가능:

```python
# 재시작 주기
RESTART_INTERVAL = 4 * 60 * 60  # 4시간

# Ollama 메모리 상한
MAX_MEMORY_MB = 10 * 1024  # 10GB

# API 응답 타임아웃
RESPONSE_TIMEOUT = 10  # 10초

# 상태 체크 간격
check_interval = 60  # 1분
```

## 문제 해결

### Ollama 시작 실패
1. 포트가 이미 사용 중인지 확인:
   ```powershell
   netstat -ano | findstr "11434 11435"
   ```

2. 기존 프로세스 강제 종료:
   ```powershell
   Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force
   ```

### 트레이더 시작 실패
1. Python 경로 확인:
   - ETH: `C:\Users\user\PycharmProjects\PythonProject\.venv\Scripts\python.exe`
   - KIS: `C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe`

2. 스크립트 경로 확인:
   - ETH: `C:\Users\user\Documents\코드3\llm_eth_trader_v3_ensemble.py`
   - KIS: `C:\Users\user\Documents\코드4\kis_llm_trader.py`

### 지속적인 재시작
- Ollama 응답 시간이 지속적으로 느리면 모델 크기 확인
- GPU 메모리 부족 시 다른 프로그램 종료

## 로그 확인
각 트레이더는 별도 콘솔 창에서 실행되므로:
- ETH 트레이더 창: ETH 거래 로그
- KIS 트레이더 창: KIS 거래 로그
- 관리자 창: Ollama 헬스 체크 + 재시작 로그

## 장점
1. **Ollama 먹통 문제 해결**: 타임아웃/큐잉 자동 감지 및 복구
2. **포트 충돌 방지**: 독립 포트로 안정적 운영
3. **무인 운영 가능**: 4시간마다 자동 재시작 + 크래시 복구
4. **리소스 최적화**: 메모리/CPU 기반 지능적 재시작
