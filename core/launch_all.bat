@echo off
chcp 65001 >nul

echo ============================================================
echo   Newton-X v2.0 Launcher
echo   Opening Monitor + Agent in separate windows...
echo ============================================================

REM Launch Monitor
start "NewtonX-Monitor" cmd /k "cd /d C:\Users\16535\.claude\experiments\newton-x && title Newton-X Monitor && python system2_daemon.py"

REM Launch Agent
start "NewtonX-Agent" cmd /k "cd /d C:\Users\16535\.claude\experiments\newton-x && title Newton-X Agent && python standalone_agent.py"

echo Done. Two windows should be open.
pause
