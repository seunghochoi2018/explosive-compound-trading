# GitHub 로그인 가이드 (Device Activation)

## 🔐 로그인 절차

### 1. 배치 파일 실행
```
AUTO_GITHUB_PUSH.bat 더블클릭
```

### 2. 콘솔 창 확인 (중요!)
**검은 콘솔 창**에 다음과 같이 표시됩니다:

```
! First copy your one-time code: XXXX-XXXX
Press Enter to open github.com in your browser...
```

### 3. 코드 복사
**콘솔 창에 표시된 코드를 복사하세요!**
예: `A1B2-C3D4`

### 4. Enter 키 누르기
브라우저가 자동으로 열립니다:
```
https://github.com/login/device
```

### 5. 코드 입력
브라우저에서:
1. "Enter the code displayed on your device" 입력창에
2. **콘솔 창에서 복사한 코드** 붙여넣기 (예: A1B2-C3D4)
3. "Continue" 클릭

### 6. 권한 승인
```
Authorize GitHub CLI
✓ repo (Full control of private repositories)
✓ read:org (Read org and team membership)
✓ workflow (Update GitHub Action workflows)
```
→ **"Authorize github"** 클릭

### 7. 완료
콘솔 창으로 돌아가면:
```
✓ Authentication complete.
✓ Logged in as seunghochoi2018
```

---

## 📺 화면 예시

### 콘솔 창 (여기서 코드 복사!)
```
================================================================================
GitHub Auto Push Script
================================================================================

[인증] GitHub 로그인 필요

브라우저가 열립니다. GitHub 계정으로 로그인하세요.

계속하려면 아무 키나 누르십시오 . . .

! First copy your one-time code: A1B2-C3D4  ← 이 코드 복사!
Press Enter to open github.com in your browser...
```

### 브라우저 (여기에 코드 입력!)
```
Device Activation
@seunghochoi2018
Signed in as seunghochoi2018

Enter the code displayed on your device
[________________]  ← 여기에 A1B2-C3D4 붙여넣기

[Continue]
```

---

## ⚠️ 주의사항

### 1. 코드는 콘솔 창에!
- ❌ 앱에 안 뜸
- ❌ 브라우저에 안 뜸
- ✅ **검은 콘솔 창에 표시됨**

### 2. 코드는 8자리
```
형식: XXXX-XXXX
예: A1B2-C3D4
```

### 3. 코드 복사 방법
- 마우스로 드래그 → Ctrl+C
- 또는 콘솔 창 우클릭 → "표시" → 드래그 → Enter

### 4. 시간 제한
- 코드는 **15분간 유효**
- 시간 초과 시 배치 파일 다시 실행

---

## 🔄 다시 시도

### 코드를 놓쳤다면:
1. 콘솔 창 닫기
2. `AUTO_GITHUB_PUSH.bat` 다시 실행
3. 새 코드 받기
4. 다시 입력

### 이미 인증된 경우:
```
[OK] GitHub 인증 완료
```
→ 바로 푸시 진행됩니다!

---

## 🎯 전체 흐름 요약

```
1. AUTO_GITHUB_PUSH.bat 실행
   ↓
2. 콘솔 창에서 코드 확인 (예: A1B2-C3D4)
   ↓
3. 코드 복사 (Ctrl+C)
   ↓
4. Enter 키 (브라우저 자동 열림)
   ↓
5. 브라우저에 코드 붙여넣기
   ↓
6. Continue → Authorize
   ↓
7. 인증 완료!
   ↓
8. 자동으로 저장소 생성 + 푸시
```

---

## 📸 스크린샷 예시

### 콘솔 창 (코드 위치)
```
┌─────────────────────────────────────────────┐
│ GitHub Auto Push Script                     │
├─────────────────────────────────────────────┤
│                                             │
│ [인증] GitHub 로그인 필요                   │
│                                             │
│ 브라우저가 열립니다.                        │
│                                             │
│ ! First copy your one-time code: A1B2-C3D4 │ ← 여기!
│ Press Enter to open github.com...           │
│                                             │
└─────────────────────────────────────────────┘
```

### 브라우저 (입력 위치)
```
┌─────────────────────────────────────────────┐
│ Device Activation                           │
├─────────────────────────────────────────────┤
│                                             │
│ @seunghochoi2018                            │
│ Signed in as seunghochoi2018                │
│                                             │
│ Enter the code displayed on your device    │
│ ┌─────────────┐                            │
│ │ A1B2-C3D4   │ ← 콘솔에서 복사한 코드      │
│ └─────────────┘                            │
│                                             │
│ [ Continue ]                                │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 🆘 문제 해결

### Q: 콘솔 창이 너무 빨리 닫혀요
A: 배치 파일 마지막에 `pause` 있어서 안 닫힙니다.
   창이 보이지 않으면 작업 표시줄 확인

### Q: 코드가 안 보여요
A:
1. 콘솔 창 스크롤 위로 올리기
2. 또는 배치 파일 다시 실행

### Q: 코드를 잘못 입력했어요
A:
1. 브라우저에서 "Try again" 클릭
2. 또는 콘솔 창에서 다시 복사

### Q: 인증은 됐는데 푸시가 안 돼요
A:
```bash
# 수동으로 푸시
cd C:\Users\user\Documents\코드5
git push -u origin master
```

---

**코드는 콘솔 창에 표시됩니다! 검은 창을 보세요!** 🔍
