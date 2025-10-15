@echo off
REM ============================================================
REM Ollama 전용 감시견 - 10초마다 체크
REM ============================================================
REM 거부 원인 분석:
REM 1. Ollama 프로세스는 있지만 포트 11434가 안 열림
REM 2. 초기화 실패 또는 크래시 후 좀비 프로세스
REM 3. 메모리 부족으로 모델 로드 실패
REM
REM 삼중 안전장치:
REM 1. 프로세스 존재 확인
REM 2. 포트 11434 LISTENING 확인
REM 3. API 응답 확인 (curl 테스트)
REM ============================================================

title Ollama Guardian - 10초마다 체크

echo.
echo ================================================================
echo   Ollama 전용 감시견
echo ================================================================
echo   삼중 체크:
echo   1. 프로세스 존재 (ollama.exe)
echo   2. 포트 11434 LISTENING
echo   3. API 응답 (/api/tags)
echo ================================================================
echo   10초마다 확인, 문제 발견 시 즉시 재시작
echo ================================================================
echo.

:LOOP
    echo [%TIME%] ==================== Ollama 체크 시작 ====================

    REM ===== 1단계: 프로세스 확인 =====
    tasklist | findstr "ollama.exe" >NUL
    if errorlevel 1 (
        echo [%TIME%] [FAIL 1/3] Ollama 프로세스 없음!
        goto RESTART_OLLAMA
    )
    echo [%TIME%] [OK 1/3] Ollama 프로세스 존재

    REM ===== 2단계: 포트 확인 =====
    netstat -ano | findstr ":11434" | findstr "LISTENING" >NUL
    if errorlevel 1 (
        echo [%TIME%] [FAIL 2/3] 포트 11434 닫힘!
        goto RESTART_OLLAMA
    )
    echo [%TIME%] [OK 2/3] 포트 11434 LISTENING

    REM ===== 3단계: API 응답 확인 =====
    curl -s --max-time 2 http://127.0.0.1:11434/api/tags >NUL 2>&1
    if errorlevel 1 (
        echo [%TIME%] [FAIL 3/3] API 응답 없음!
        goto RESTART_OLLAMA
    )
    echo [%TIME%] [OK 3/3] API 정상 응답

    echo [%TIME%] [ALL OK] Ollama 완벽하게 작동 중
    echo [%TIME%] 다음 체크까지 10초 대기...
    echo.
    timeout /t 10 /nobreak >nul
    goto LOOP

:RESTART_OLLAMA
    echo [%TIME%] ========================================
    echo [%TIME%] [CRITICAL] Ollama 재시작 시작!
    echo [%TIME%] ========================================

    REM 기존 프로세스 강제 종료
    echo [%TIME%] 1. 기존 Ollama 프로세스 종료 중...
    taskkill /F /IM ollama.exe 2>NUL
    timeout /t 2 /nobreak >nul

    REM Ollama 재시작
    echo [%TIME%] 2. Ollama 서버 시작 중...
    start "Ollama-Server" /MIN cmd /c ollama serve
    timeout /t 5 /nobreak >nul

    REM 재시작 확인
    echo [%TIME%] 3. 재시작 확인 중...
    curl -s --max-time 3 http://127.0.0.1:11434/api/tags >NUL 2>&1
    if errorlevel 1 (
        echo [%TIME%] [WARN] 재시작 확인 실패, 5초 더 대기...
        timeout /t 5 /nobreak >nul
    ) else (
        echo [%TIME%] [SUCCESS] Ollama 재시작 성공!
    )

    echo [%TIME%] ========================================
    echo.
    goto LOOP
