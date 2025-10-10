@echo off
chcp 65001 > nul
echo ====================================
echo   NVIDIA 자동매매 트레이더 런처
echo ====================================
echo.
echo 1. NVDA 주식 트레이더 (양방향)
echo 2. NVDL 롱 전용 트레이더 (2x ETF)
echo 3. 설정 확인
echo 4. 종료
echo.
set /p choice="선택하세요 (1-4): "

if "%choice%"=="1" goto nvda_trader
if "%choice%"=="2" goto nvdl_trader
if "%choice%"=="3" goto check_config
if "%choice%"=="4" goto exit

:nvda_trader
echo.
echo NVDA 주식 트레이더를 시작합니다...
python nvidia_stock_trader.py
pause
goto menu

:nvdl_trader
echo.
echo NVDL 롱 전용 트레이더를 시작합니다...
python nvdl_long_trader.py
pause
goto menu

:check_config
echo.
echo 설정 파일 확인 중...
if exist nvidia_config.json (
    echo nvidia_config.json 파일이 존재합니다.
    type nvidia_config.json
) else (
    echo nvidia_config.json 파일이 없습니다.
    echo 트레이더를 한 번 실행하여 설정 파일을 생성하세요.
)
echo.
pause
goto menu

:menu
cls
echo ====================================
echo   NVIDIA 자동매매 트레이더 런처
echo ====================================
echo.
echo 1. NVDA 주식 트레이더 (양방향)
echo 2. NVDL 롱 전용 트레이더 (2x ETF)
echo 3. 설정 확인
echo 4. 종료
echo.
set /p choice="선택하세요 (1-4): "

if "%choice%"=="1" goto nvda_trader
if "%choice%"=="2" goto nvdl_trader
if "%choice%"=="3" goto check_config
if "%choice%"=="4" goto exit

:exit
echo.
echo 프로그램을 종료합니다.
pause