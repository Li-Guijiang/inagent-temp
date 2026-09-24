@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "ISCC="
if defined INNO_SETUP_HOME if exist "%INNO_SETUP_HOME%\ISCC.exe" set "ISCC=%INNO_SETUP_HOME%\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo [错误] 未找到 Inno Setup 6 编译器 ISCC.exe。
  echo 请安装 Inno Setup 6 后重试，或设置 INNO_SETUP_HOME 指向其安装目录。
  echo 构建步骤：先运行 build_windows.bat，再运行本脚本。
  exit /b 2
)
if not exist "dist\SmartManufacturingDemo\SmartManufacturingDemo.exe" (
  echo [错误] 缺少 dist\SmartManufacturingDemo，请先运行 build_windows.bat。
  exit /b 1
)
if exist "installer-output" rmdir /s /q "installer-output"
mkdir "installer-output"
"%ISCC%" "installer.iss"
if errorlevel 1 exit /b 1
echo 安装包已生成：installer-output\SmartManufacturingDemo-Setup.exe
endlocal
