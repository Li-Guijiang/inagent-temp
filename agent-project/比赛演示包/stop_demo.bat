@echo off
rem ============================================================
rem  Stop the demo services (ports 5000 & 8848)
rem  Usage: double-click, or run: stop_demo.bat
rem ============================================================
chcp 65001 >nul
title Competition 188 - Stop Demo

echo ============================================================
echo   Stopping demo services (ports 5000 and 8848) ...
echo ============================================================

powershell -NoProfile -Command ^
  "$c = Get-NetTCPConnection -LocalPort 5000,8848 -State Listen -ErrorAction SilentlyContinue;" ^
  "if ($c) { $c | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Write-Host ('Killing PID ' + $_); Stop-Process -Id $_ -Force } } else { Write-Host 'No demo service found.' }"

echo.
echo ============================================================
echo   Done. Ports 5000 / 8848 released.
echo ============================================================
pause >nul