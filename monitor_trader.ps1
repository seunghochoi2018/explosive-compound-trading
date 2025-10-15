# 통합 트레이더 매니저 모니터링 스크립트
param(
    [int]$CheckInterval = 60  # 60초마다 체크
)

function Check-TraderManager {
    $pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
    $ollamaProcesses = Get-Process ollama -ErrorAction SilentlyContinue
    
    $ports = @(11434, 11435, 11436, 11437)
    $activePorts = @()
    
    foreach ($port in $ports) {
        $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($connection) {
            $activePorts += $port
        }
    }
    
    $status = @{
        PythonProcesses = $pythonProcesses.Count
        OllamaProcesses = $ollamaProcesses.Count
        ActivePorts = $activePorts.Count
        AllPortsActive = ($activePorts.Count -eq $ports.Count)
    }
    
    return $status
}

function Restart-TraderManager {
    Write-Host "[$(Get-Date)] 통합 트레이더 매니저 재시작 중..." -ForegroundColor Yellow
    
    # 기존 프로세스 종료
    Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*unified*" } | Stop-Process -Force
    Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force
    
    Start-Sleep -Seconds 5
    
    # 재시작
    Start-Process -FilePath "C:\Users\user\Documents\코드5\start_trader_manager.bat" -WindowStyle Hidden
    Write-Host "[$(Get-Date)] 통합 트레이더 매니저 재시작 완료" -ForegroundColor Green
}

# 메인 모니터링 루프
Write-Host "[$(Get-Date)] 통합 트레이더 매니저 모니터링 시작 (${CheckInterval}초 간격)" -ForegroundColor Cyan

while ($true) {
    $status = Check-TraderManager
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] 상태 체크:" -ForegroundColor White
    Write-Host "  Python 프로세스: $($status.PythonProcesses)개" -ForegroundColor Gray
    Write-Host "  Ollama 프로세스: $($status.OllamaProcesses)개" -ForegroundColor Gray
    Write-Host "  활성 포트: $($status.ActivePorts)/4개" -ForegroundColor Gray
    
    if (-not $status.AllPortsActive -or $status.PythonProcesses -lt 2) {
        Write-Host "[$timestamp] 문제 감지! 재시작 중..." -ForegroundColor Red
        Restart-TraderManager
    } else {
        Write-Host "[$timestamp] 정상 동작 중" -ForegroundColor Green
    }
    
    Start-Sleep -Seconds $CheckInterval
}

