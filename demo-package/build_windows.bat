@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --windowed --onedir --name SmartManufacturingDemo ^
  --hidden-import http.server --hidden-import openpyxl --hidden-import openpyxl.styles ^
  --add-data "skills;skills" main.py
if errorlevel 1 (
  echo [错误] PyInstaller 构建失败，请先执行：python -m pip install -r requirements.txt
  exit /b 1
)
del /s /q "dist\SmartManufacturingDemo\_internal\skills\factory-console\*.log" >nul 2>nul
for /d /r "dist\SmartManufacturingDemo" %%D in (__pycache__) do @if exist "%%D" rmdir /s /q "%%D"
echo 构建完成：dist\SmartManufacturingDemo\SmartManufacturingDemo.exe
echo 运行示例：dist\SmartManufacturingDemo\SmartManufacturingDemo.exe --no-browser
endlocal
