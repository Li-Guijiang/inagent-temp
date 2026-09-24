# 命题188智能制造比赛演示包

这是一个可离线运行的 Windows 智能制造演示应用，保留五个技能包、四个 Agent 和原有演示数据。控制台使用 Python 标准库 HTTP 服务，Excel 台账使用 `openpyxl`。

## 快速启动

安装 Python 3.8+ 后，在项目目录执行：

```bat
python -m pip install -r requirements.txt
python main.py
```

常用参数：

```text
--port 8848             指定本地端口
--no-browser            不自动打开浏览器
--skip-pipelines        不重复运行五个技能包，直接使用已有产物
--data-dir runtime-data 质检上报与新报表的可写目录
--log-file runtime-data\console.log
```

浏览器访问 `http://127.0.0.1:8848`，健康检查为 `/api/health`。停止服务请在控制台按 `Ctrl+C`。端口已占用或输入无效时，程序会给出明确错误并返回非零退出码。

双击 `run_demo.bat` 可执行完整演示；它现在只是 Python 入口的 Windows 便捷包装。五个技能包仍可进入各自目录，按 `data_fetch.py → analysis.py → report_gen.py` 独立运行。

## 发布构建

执行 `build_windows.bat` 会使用 PyInstaller 生成 `dist\SmartManufacturingDemo\SmartManufacturingDemo.exe`（onedir/portable 目录）。构建机若无法安装依赖，源码启动仍可用：

```bat
python -m pip install -r requirements.txt
build_windows.bat
```

运行时生成的上报记录、报表、日志和缓存应放在 `--data-dir` 指定目录，不要把该目录作为发布包内容。`config.example.json` 是可复制修改的配置示例；目前命令行参数是唯一生效配置入口。

## 工程约定

- 所有源码、JSON 和 Markdown 使用 UTF-8。
- API 错误使用 4xx 状态码和 JSON `{"ok": false, "msg": "..."}` 返回，不静默吞错。
- 上报 JSON 采用临时文件 + `os.replace`，并在进程内加锁，避免并发写入损坏。
- 静态文件严格限制在 `web` 目录，报告下载只允许 `.xlsx` 文件名。
- `tests\` 提供核心 API、工艺解析、输入校验和健康检查的最小回归测试。

详细现场流程见《比赛演示说明文档.md》。

## Windows 安装版

先执行 `build_windows.bat` 生成 onedir 运行目录，再执行 `build_installer.bat`。后者会自动检测 Inno Setup 6 的 `ISCC.exe`，生成单文件 `installer-output\SmartManufacturingDemo-Setup.exe`。当前机器未安装 Inno Setup 时，脚本会明确提示，不会联网下载；安装器源码为 `installer.iss`。

安装版双击快捷方式即可启动，不依赖快捷方式的“起始位置”。安装文件位于程序目录，质检上报、综合报表和诊断日志写入 `%LOCALAPPDATA%\SmartManufacturingDemo\data` 与 `%LOCALAPPDATA%\SmartManufacturingDemo\logs`，卸载程序不会删除这些用户数据。安装版使用随包内置的演示数据，避免把安装目录当作可写目录。
