@echo off
chcp 65001 > nul
setlocal
rem Chay GeoDraw tu chinh thu muc chua file .bat nay (khong phu thuoc o dia / ten thu muc)
set "ROOT=%~dp0"
cd /d "%ROOT%geodraw"
if errorlevel 1 (
    echo Khong tim thay thu muc "%ROOT%geodraw"
    pause
    exit /b 1
)

rem --- Tim Python: uu tien python\ ben canh tool, roi py launcher, roi python tren PATH ---
set "PY="
if exist "%ROOT%python\python.exe" set "PY="%ROOT%python\python.exe""
if not defined PY (
    py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
    python -c "import sys" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo Khong tim thay Python. Hay cai Python 3 ^(tick "Add python.exe to PATH"^)
    echo hoac dat thu muc python\ ben canh file .bat nay.
    pause
    exit /b 1
)

rem --- Cai thu vien con thieu (PyQt6) neu chua co ---
%PY% -c "import PyQt6.QtWidgets" >nul 2>&1
if errorlevel 1 (
    echo Dang cai thu vien can thiet ^(PyQt6^), chi lam lan dau...
    %PY% -m pip install -r "%ROOT%geodraw\requirements.txt"
    %PY% -c "import PyQt6.QtWidgets" >nul 2>&1
    if errorlevel 1 (
        echo Cai PyQt6 that bai. Kiem tra ket noi mang roi chay lai.
        pause
        exit /b 1
    )
)

if exist "%ROOT%error_log.txt" del "%ROOT%error_log.txt"

%PY% -u -W all main.py
set "CODE=%errorlevel%"
echo.
echo === Exit code: %CODE% ===
if exist "%ROOT%error_log.txt" (
    echo === Noi dung error_log.txt: ===
    type "%ROOT%error_log.txt"
)
pause
