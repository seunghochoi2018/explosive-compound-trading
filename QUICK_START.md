# 🚀 빠른 시작 가이드

## 원클릭 실행

```batch
더블클릭: START_EXPLOSIVE_TRADING.bat
```

그게 전부입니다! 🎉

---

## 실행되는 내용

### 1. Ollama 체크 (3초)
```
[메모리 체크] Ollama 모델 확인...
[OK] Ollama 실행 중
  - qwen2.5:7b: ~4.5GB (ETH용)
  - qwen2.5:14b: ~8GB (KIS용)

[전략] 순차 실행
  방법: ETH 30분 → KIS 30분 → 교대 실행
```

### 2. 텔레그램 알림
```
🚀 통합 매니저 시작

전략: Ollama 메모리 관리
ETH: 복리 +4,654%
KIS: 연 +2,634%
```

### 3. 연속 학습기 시작 (백그라운드)
```
🧠 연속 학습 시작

백그라운드에서 과거 데이터 분석
획기적 전략 발견 시 자동 교체
```

### 4. 트레이딩 시작
```
[사이클 1]
================================================================================

[2025-10-10 14:30:00] ETH 봇 실행 (30분)
[OK] ETH 봇 PID: 12345

  ETH 실행 중... 10/30분
  ETH 실행 중... 20/30분
  ETH 실행 중... 30/30분

[2025-10-10 15:00:00] ETH 봇 중지 (메모리 해제)
[OK] ETH 봇 중지

[2025-10-10 15:00:10] KIS 봇 실행 (30분)
[OK] KIS 봇 PID: 12346

  KIS 실행 중... 10/30분
  KIS 실행 중... 20/30분
  KIS 실행 중... 30/30분

[2025-10-10 15:30:00] KIS 봇 중지 (메모리 해제)
[OK] KIS 봇 중지

[사이클 1 완료]
```

### 5. 연속 학습 (1시간마다)
```
[학습 사이클 1] 2025-10-10 16:00:00
================================================================================

--- ETH 전략 탐색 ---
[전략 탐색] ETH 분석 중...
현재 전략: Explosive Compound v1
  기준 성능: 4,654%

테스트할 전략: 30개
  진행: 50/30...

[결과] 현재 전략이 최적

--- KIS 전략 탐색 ---
[전략 탐색] KIS 분석 중...
현재 전략: SOXL 10-hour v1
  기준 성능: 2,634%

테스트할 전략: 25개

🚀 획기적 전략 발견! (테스트 15/25)
  복리 수익: 3,156.8%
  승률: 58.2%
  거래 수: 234/280
  파라미터: {'max_holding_min': 480, 'min_holding_min': 60, 'avoid_trend_opposite': True}

[검증] KIS 새 전략 검증 중...
[통과] 검증 완료
  개선도: 1.20x
  복리 수익: 3,156.8%
  승률: 58.2%

[배포] KIS 전략 교체
[백업] 현재 전략 저장: strategy_backup_kis_20251010_160022.json
[완료] 전략 배포 완료
  파일: C:/Users/user/Documents/코드4/kis_current_strategy.json
```

### 6. 텔레그램 알림 (획기적 전략 발견 시)
```
🚀 획기적 전략 발견 & 배포!

자산: KIS
전략: SOXL v2 (Auto-learned 2025-10-10)

성능:
  복리 수익: 3,156.8%
  승률: 58.2%
  거래 수: 234

⚠️ 검증 기간:
  손절: -3.5%
  50거래 후 자동 조정
```

---

## 중지 방법

콘솔 창에서:
```
Ctrl + C
```

자동으로:
- ETH 봇 중지
- KIS 봇 중지
- 학습기 중지
- 모니터 중지
- 텔레그램 알림: "⚠️ 통합 매니저 종료"

---

## 실시간 확인

### 콘솔 창
```
[사이클 2]
================================================================================
[2025-10-10 15:30:10] ETH 봇 실행 (30분)
[OK] ETH 봇 PID: 12347
  ETH 실행 중... 10/30분
```

### 텔레그램
- 시작 알림
- 학습 시작 알림
- 전략 발견 알림
- 사이클 완료 알림
- 거래 알림 (각 봇)

### 로그 파일
```
C:\Users\user\Documents\코드5\unified_manager.log
```

---

## 성능 확인

### ETH
```bash
python -c "import json; f=open('C:/Users/user/Documents/코드3/eth_trade_history.json','r',encoding='utf-8'); data=json.load(f); print(f'총 거래: {len(data)}건'); wins=[t for t in data if t.get('pnl_pct',0)>0]; print(f'승률: {len(wins)/len(data)*100:.1f}%') if data else print('데이터 없음')"
```

### KIS
```bash
python -c "import json; f=open('C:/Users/user/Documents/코드4/kis_trade_history.json','r',encoding='utf-8'); data=json.load(f); print(f'총 거래: {len(data)}건'); wins=[t for t in data if t.get('pnl_pct',0)>0]; print(f'승률: {len(wins)/len(data)*100:.1f}%') if data else print('데이터 없음')"
```

---

## 전략 확인

### ETH 현재 전략
```bash
type C:\Users\user\Documents\코드3\eth_current_strategy.json
```

### KIS 현재 전략
```bash
type C:\Users\user\Documents\코드4\kis_current_strategy.json
```

---

## 문제 해결

### Q: 봇이 멈춥니다
A:
1. Ctrl+C로 중지
2. START_EXPLOSIVE_TRADING.bat 다시 실행

### Q: Ollama 체크에서 멈춥니다
A: 이제 3초 후 자동으로 건너뜁니다 (수정됨)

### Q: 학습기가 전략을 못 찾습니다
A: 정상입니다. 현재 전략이 이미 최적일 수 있습니다.

### Q: 텔레그램 알림이 안 옵니다
A:
```bash
cd C:\Users\user\Documents\코드4
python -c "from telegram_notifier import TelegramNotifier; t=TelegramNotifier(); t.send_message('테스트')"
```

---

## 다음 단계

✅ 시스템 실행 (완료)
⏳ 100거래 수집 (진행 중)
⏳ 전략 검증 (자동)
⏳ 성능 최적화 (자동 학습)

---

**🚀 복리 폭발 시작!**

현재 성능:
- ETH: +4,654% (백테스트)
- KIS: +2,634% (백테스트)

자동 학습으로 더 나은 전략 발견 중...
```
