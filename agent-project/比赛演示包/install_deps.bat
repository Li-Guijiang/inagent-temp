@echo off
rem ============================================================
rem  One-click dependency installer for Competition 188 demo
rem  (uses find_python.bat, installs flask + openpyxl via mirror)
rem ============================================================
chcp 65001 >nul
title Competition 188 - Install Dependencies

echo ============================================================
echo   Installing dependencies: flask, openpyxl
echo   (Tsinghua PyPI mirror for faster download)
echo ============================================================

rem ---- locate python ----
call "%~dp0find_python.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] No usable Python found on this machine.
    echo   Option A: install Python 3.6+ and tick "Add python.exe to PATH"
    echo            https://www.python.org/downloads/
    echo   Option B: if this demo is inside InAgent, its bundled Python
    echo            should be auto-detected automatically.
    echo   Option C: run with a specific python, e.g.:
    echo            "C:\path\to\python.exe" install_deps.bat
    pause
    exit /b 1
)
echo   Using Python : %PY_CMD%
echo.

"%PY_CMD%" -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo   Installing flask ...
"%PY_CMD%" -m pip install flask -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (echo [ERROR] flask install failed & pause & exit /b 1)

echo.
echo   Installing openpyxl ...
"%PY_CMD%" -m pip install openpyxl -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (echo [ERROR] openpyxl install failed & pause & exit /b 1)

echo.
echo   Verifying ...
"%PY_CMD%" -c "import flask, openpyxl; print('flask OK, openpyxl', openpyxl.__version__)"
if errorlevel 1 (echo [ERROR] verification failed & pause & exit /b 1)

echo.
echo ============================================================
echo   Dependencies ready. Now double-click run_demo.bat
echo ============================================================
pause >nul