@echo off
chcp 65001 >nul
title 命题188 智能制造比赛演示 - 一键启动
echo ============================================================
echo   命题188 智能制造比赛演示 一键启动
echo   ① 依次运行 5 个技能包流水线（复现全部数据与报表）
echo   ② 启动工厂操作工控制台（四大 Agent + 能耗看板）
echo   ③ 自动验证四大 Agent 调用正常
echo   ④ 打开浏览器演示界面
echo   ⑤ 本地 MCP 数据端点：http://127.0.0.1:8848/mcp/*
echo ============================================================
echo.

echo [1/2] 运行五个技能包流水线并启动控制台 ...
cd /d "%~dp0"
start "factory-console" /b python main.py --port 8848
timeout /t 3 /nobreak >nul
echo [2/2] 验证四大 Agent ...
cd /d "%~dp0skills\factory-console"
python verify_agents.py
if errorlevel 1 (echo   [错误] Agent 验证失败 & pause & exit /b 1)

echo.
echo 四大 Agent 全部调用正常，正在打开演示界面...
start "" http://127.0.0.1:8848
echo.
echo ============================================================
echo   演示已就绪！操作工控制台地址：http://127.0.0.1:8848
echo   （在控制台窗口内 按 Ctrl+C 可停止服务）
echo ============================================================
pause >nul