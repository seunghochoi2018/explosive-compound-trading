# Windows 시작 프로그램에 Watchdog 등록
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\user\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\TradingWatchdog.lnk")
$Shortcut.TargetPath = "C:\Users\user\Documents\코드5\start_watchdog.bat"
$Shortcut.WorkingDirectory = "C:\Users\user\Documents\코드5"
$Shortcut.Description = "Trading System Watchdog - Auto Restart"
$Shortcut.WindowStyle = 7  # Minimized
$Shortcut.Save()

Write-Host "✅ Watchdog가 Windows 시작 프로그램에 등록되었습니다!"
Write-Host ""
Write-Host "이제 컴퓨터를 켤 때마다 자동으로 실행됩니다:"
Write-Host "  1. Watchdog 시작"
Write-Host "  2. 통합매니저 자동 시작"
Write-Host "  3. ETH + KIS 트레이더 자동 시작"
Write-Host ""
Write-Host "통합매니저가 중단되면 자동으로 재시작됩니다."
