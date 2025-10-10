@echo off
chcp 65001 > nul
echo ==========================================
echo   NVIDIA 롱/숏 자동매매 트레이더 시작
echo ==========================================
echo.
echo AI가 NVDL(롱)과 NVDD(숏)을 학습하고 자동매매합니다.
echo.
python nvidia_unified_trader.py
pause