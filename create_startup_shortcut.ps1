$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\user\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\UnifiedTraderManager.lnk")
$Shortcut.TargetPath = "C:\Users\user\Documents\코드5\start_unified_trader.bat"
$Shortcut.WorkingDirectory = "C:\Users\user\Documents\코드5"
$Shortcut.Description = "Unified Trader Manager Auto Start"
$Shortcut.WindowStyle = 7  # Minimized
$Shortcut.Save()

Write-Host "Shortcut created successfully in Startup folder!"
