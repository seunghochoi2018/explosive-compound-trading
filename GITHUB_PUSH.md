# GitHub에 푸시하는 방법

## 1단계: GitHub에서 새 저장소 만들기

1. https://github.com/new 접속
2. Repository name: `explosive-compound-trading`
3. Description: `백테스트 기반 복리 폭발 자동매매 시스템 - ETH +4654%, KIS +2634%`
4. Public 또는 Private 선택
5. **"Initialize this repository with a README" 체크 해제** (이미 로컬에 파일 있음)
6. "Create repository" 클릭

## 2단계: 로컬에서 푸시

```bash
cd C:\Users\user\Documents\코드5

# 원격 저장소 추가 (GitHub에서 복사한 URL 사용)
git remote add origin https://github.com/YOUR_USERNAME/explosive-compound-trading.git

# 푸시
git push -u origin master
```

## 3단계: 푸시 확인

GitHub 페이지 새로고침하면 파일들이 올라간 것을 확인할 수 있습니다.

---

## 빠른 푸시 (이미 저장소가 있다면)

```bash
cd C:\Users\user\Documents\코드5
git push
```

---

## 현재 커밋 상태

✅ 이미 커밋 완료:
- 통합 매니저 (unified_explosive_trader_manager.py)
- 원클릭 실행 (.bat)
- 한글 가이드
- README

커밋 메시지:
```
🚀 Add explosive compound trading strategy

백테스트 결과:
- ETH: 복리 +4,654% (승률 64.2%)
- KIS: 연 +2,634% (승률 55%)
```

이제 GitHub에 푸시만 하면 됩니다!
