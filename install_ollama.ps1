# Ollama 자동 설치 스크립트
Write-Host "Ollama 설치 시작..." -ForegroundColor Green

# 1. Ollama 다운로드 및 설치
$ollamaUrl = "https://ollama.com/download/windows"
Write-Host "Ollama 다운로드 중..." -ForegroundColor Yellow

try {
    # PowerShell로 Ollama 설치
    Invoke-WebRequest -Uri "https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.exe" -OutFile "$env:TEMP\ollama-installer.exe"
    
    Write-Host "Ollama 설치 실행 중..." -ForegroundColor Yellow
    Start-Process -FilePath "$env:TEMP\ollama-installer.exe" -ArgumentList "/S" -Wait
    
    Write-Host "Ollama 설치 완료!" -ForegroundColor Green
    
    # PATH에 Ollama 추가
    $ollamaPath = "$env:USERPROFILE\AppData\Local\Programs\Ollama"
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    
    if ($currentPath -notlike "*$ollamaPath*") {
        [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$ollamaPath", "User")
        Write-Host "PATH에 Ollama 추가 완료" -ForegroundColor Green
    }
    
    # 새 세션에서 PATH 적용
    $env:PATH = "$env:PATH;$ollamaPath"
    
    Write-Host "Ollama 설치 및 설정 완료!" -ForegroundColor Green
    Write-Host "새 PowerShell 창을 열어서 'ollama --version' 명령을 실행하세요." -ForegroundColor Cyan
    
} catch {
    Write-Host "자동 설치 실패: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "수동 설치를 진행하세요." -ForegroundColor Yellow
}

pause

