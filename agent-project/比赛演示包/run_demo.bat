@echo off
rem ============================================================
rem  Competition 188 - Smart Manufacturing Demo One-Click Starter
rem  (ASCII-only batch; auto-detects python via find_python.bat)
rem ============================================================
chcp 65001 >nul
rem Force UTF-8 for all python sub-processes (avoid Chinese-print crashes)
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title Competition 188 - Smart Manufacturing Demo

set "ROOT=%~dp0"
set "SKILLS_DIR=%ROOT%skills"

rem ---- locate python ----
call "%ROOT%find_python.bat"
if errorlevel 1 (
    echo [ERROR] No usable Python found. Run install_deps.bat for guidance.
    pause
    exit /b 1
)
set "PY=%PY_CMD%"

echo ============================================================
echo   Competition 188 - Smart Manufacturing Demo
echo   Python      : %PY%
echo   0) Check environment (python / flask / openpyxl)
echo   1) Start dynamic MCP data service  (port 5000)
echo   2) Run 5 skill pipelines  (--source mcp dynamic mode)
echo   3) Start factory console          (port 8848)
echo   4) Auto verify 4 Agents
echo   5) Open browser
echo ============================================================
echo.

echo.
echo [0/6] Checking environment ...
"%PY%" "%ROOT%check_env.py"
if errorlevel 1 (echo   [ERROR] Environment check failed. Run install_deps.bat first. & pause & exit /b 1)

echo.
echo [START-5000] Launching dynamic data service ...
cd /d "%ROOT%"
start "MCP-5000" /min cmd /k "chcp 65001>nul & set PYTHONIOENCODING=utf-8& set PYTHONUTF8=1& python app.py"
timeout /t 3 /nobreak >nul

echo.
echo [1/6] equipment-inspection (mcp) ...
cd /d "%SKILLS_DIR%\equipment-inspection"
"%PY%" scripts\data_fetch.py --source mcp && "%PY%" scripts\analysis.py && "%PY%" scripts\report_gen.py
if errorlevel 1 (echo   [ERROR] equipment-inspection failed & pause & exit /b 1)

echo.
echo [2/6] quality-inspection (mcp) ...
cd /d "%SKILLS_DIR%\quality-inspection"
"%PY%" scripts\data_fetch.py --source mcp && "%PY%" scripts\analysis.py && "%PY%" scripts\report_gen.py
if errorlevel 1 (echo   [ERROR] quality-inspection failed & pause & exit /b 1)

echo.
echo [3/6] energy-analysis (mcp) ...
cd /d "%SKILLS_DIR%\energy-analysis"
"%PY%" scripts\data_fetch.py --source mcp && "%PY%" scripts\analysis.py && "%PY%" scripts\report_gen.py
if errorlevel 1 (echo   [ERROR] energy-analysis failed & pause & exit /b 1)

echo.
echo [4/6] process-optimization (mcp) ...
cd /d "%SKILLS_DIR%\process-optimization"
"%PY%" scripts\data_fetch.py --source mcp && "%PY%" scripts\analysis.py && "%PY%" scripts\report_gen.py
if errorlevel 1 (echo   [ERROR] process-optimization failed & pause & exit /b 1)

echo.
echo [5/6] quality-traceability (mcp) ...
cd /d "%SKILLS_DIR%\quality-traceability"
"%PY%" scripts\data_fetch.py --source mcp && "%PY%" scripts\analysis.py && "%PY%" scripts\report_gen.py
if errorlevel 1 (echo   [ERROR] quality-traceability failed & pause & exit /b 1)

echo.
echo [6/6] Starting factory console (port 8848) ...
cd /d "%SKILLS_DIR%\factory-console"
start "Console-8848" /min cmd /k "chcp 65001>nul & set PYTHONIOENCODING=utf-8& set PYTHONUTF8=1& python app.py --port 8848"
timeout /t 5 /nobreak >nul

echo.
echo ============================================================
echo   Verifying 4 Agents ...
echo ============================================================
"%PY%" verify_agents.py
if errorlevel 1 (echo   [ERROR] Agent verification failed & pause & exit /b 1)

echo.
echo ============================================================
echo   ALL CHECKS PASSED. Opening browser...
echo   Factory console : http://127.0.0.1:8848
echo   Dynamic MCP base : http://127.0.0.1:5000/api/sources
echo ============================================================
start "" http://127.0.0.1:8848
echo.
echo ============================================================
echo   Demo is ready. Keep windows "MCP-5000" and "Console-8848"
echo   open while presenting. This starter window can be closed.
echo   To stop services later: run stop_demo.bat
echo ============================================================
pause >nul