@echo off
chcp 65001 > nul
cd /d "%~dp0geodraw"
"D:\Python\python.exe" -u -W all main.py
echo.
echo === Exit code: %errorlevel% ===
if exist "%~dp0error_log.txt" (
    echo === Noi dung error_log.txt: ===
    type "%~dp0error_log.txt"
)
pause
