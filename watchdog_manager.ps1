$ErrorActionPreference = "SilentlyContinue"

# 경로 설정
$managerPath = "C:\Users\user\Documents\코드5\unified_trader_manager 연습.py"

# 파이썬 실행 중인지, 해당 매니저가 포함된 프로세스가 있는지 확인
$pythonProcs = Get-Process -Name python -ErrorAction SilentlyContinue
$isRunning = $false
if ($pythonProcs) {
    foreach ($p in $pythonProcs) {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)").CommandLine
            if ($cmd -and $cmd -like "*unified_trader_manager 연습.py*") {
                $isRunning = $true
                break
            }
        } catch {}
    }
}

if (-not $isRunning) {
    Write-Output "[WATCHDOG] Manager not running. Starting..."
    Start-Process powershell -WindowStyle Hidden -ArgumentList "-Command python '$managerPath'"
} else {
    Write-Output "[WATCHDOG] Manager running."
}


