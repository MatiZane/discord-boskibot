@echo off
title Miku Discord Bot
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
if errorlevel 1 (
    echo.
    echo Bot zakonczyl prace z bledem. Nacisnij dowolny klawisz, aby zamknac...
    pause >nul
)
