# 관리자 권한으로 실행 필요
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "관리자 권한이 필요합니다. 관리자로 실행해주세요." -ForegroundColor Red
    pause
    exit
}

# 서비스 등록
$serviceName = "UnifiedTraderManager"
$servicePath = "C:\Users\user\Documents\코드5\start_trader_manager.bat"

# 기존 서비스 제거 (있다면)
if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
    Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
    sc.exe delete $serviceName
    Start-Sleep -Seconds 2
}

# 새 서비스 등록
sc.exe create $serviceName binPath= "cmd.exe /c $servicePath" start= auto DisplayName= "통합 트레이더 매니저"

if ($LASTEXITCODE -eq 0) {
    Write-Host "서비스 등록 완료: $serviceName" -ForegroundColor Green
    Start-Service -Name $serviceName
    Write-Host "서비스 시작 완료" -ForegroundColor Green
} else {
    Write-Host "서비스 등록 실패" -ForegroundColor Red
}

pause

