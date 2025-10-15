@echo off
chcp 65001 > nul
echo [자동 시작] 통합 트레이더 매니저 시작...

cd /d "C:\Users\user\Documents\코드5"

:restart
echo [%date% %time%] 통합 트레이더 매니저 실행 중...
python "unified_trader_manager 연습.py"

echo [%date% %time%] 통합 트레이더 매니저 종료됨. 10초 후 재시작...
timeout /t 10 /nobreak > nul
goto restart

