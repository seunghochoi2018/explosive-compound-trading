@echo off
echo === LLM NVDL/NVDQ 트레이딩 시스템 시작 ===
echo.

echo [1/3] Ollama 서버 시작 중...
start "Ollama Server" /min "C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe" serve

echo [2/3] Ollama 서버 준비 대기 중...
timeout /t 10 /nobreak >nul

echo [3/3] NVDL/NVDQ 트레이더 시작...
cd /d "C:\Users\user\Documents\코드4"
python llm_nvdl_trader.py

echo.
echo === 트레이딩 시스템 종료 ===
pause