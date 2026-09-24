@echo off
rem ============================================================
rem  find_python.bat - locate a usable Python interpreter.
rem  Sets %%PY_CMD%% in the CALLER batch scope.
rem  Exit code 0 = found, 1 = not found.
rem  Candidates (in order):
rem    1) InAgent bundled python (common on competition laptops)
rem    2) plain "python" (rejects MS Store alias automatically)
rem    3) "python3"
rem    4) "py -3" launcher
rem============================================================
set "PY_CMD="

rem ---- Candidate 1: InAgent bundled python ----
set "C1=%APPDATA%\InAgent\resources\python\python.exe"
if exist "%C1%" (
    "%C1%" -c "import sys; sys.exit(0)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=%C1%"
        exit /b 0
    )
)

rem ---- Candidate 2: plain python (reject MS Store stub) ----
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys; sys.exit(0)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=python"
        exit /b 0
    )
)

rem ---- Candidate 3: python3 ----
where python3 >nul 2>nul
if not errorlevel 1 (
    python3 -c "import sys; sys.exit(0)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=python3"
        exit /b 0
    )
)

rem ---- Candidate 4: py launcher ----
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys; sys.exit(0)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py -3"
        exit /b 0
    )
)

exit /b 1