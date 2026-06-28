@echo off
chcp 65001 >nul
title Newton-X System 2 Monitor
echo.
echo ================================================================
echo   Newton-X v2.0 -- System 2 Daemon + Monitor
echo   监控独立 Agent 的行为流，每 5 步触发 LLM 直觉分析
echo ================================================================
echo.
cd /d "C:\Users\16535\.claude\experiments\newton-x"
python system2_daemon.py
pause
