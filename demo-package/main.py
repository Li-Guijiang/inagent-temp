"""命题 188 智能制造演示包的 Python 启动入口。

默认执行五个技能包流水线后启动控制台；现场重复演示时可使用
``--skip-pipelines`` 保留已有产物并快速启动。
"""
import argparse
import importlib.util
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
SKILLS = ROOT / "skills"
APP_DATA = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SmartManufacturingDemo"
DEFAULT_DATA_DIR = APP_DATA / "data"
DEFAULT_LOG_FILE = APP_DATA / "logs" / "smart-manufacturing-demo.log"
PIPELINES = (
    ("设备点检", "equipment-inspection"),
    ("质量巡检", "quality-inspection"),
    ("能耗分析", "energy-analysis"),
    ("工艺优化", "process-optimization"),
    ("质量追溯", "quality-traceability"),
)


def _run_pipeline(name, folder):
    if FROZEN:
        raise RuntimeError("安装版使用内置演示数据，不支持直接运行源码流水线")
    workdir = SKILLS / folder
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    for script in ("data_fetch.py", "analysis.py", "report_gen.py"):
        command = [sys.executable, str(workdir / "scripts" / script)]
        print("[pipeline] %s: %s" % (name, script), flush=True)
        subprocess.run(command, cwd=str(workdir), check=True, env=env)


def _load_console():
    path = SKILLS / "factory-console" / "app.py"
    spec = importlib.util.spec_from_file_location("factory_console_app", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载控制台模块: %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description="命题188智能制造演示包")
    parser.add_argument("--port", type=int, default=8848)
    parser.add_argument("--no-browser", action="store_true", help="启动后不自动打开浏览器")
    parser.add_argument("--skip-pipelines", action="store_true", help="跳过五个技能包流水线")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                        help="控制台运行时数据目录（默认 %%LOCALAPPDATA%%\\SmartManufacturingDemo\\data）")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE),
                        help="日志文件路径")
    args = parser.parse_args(argv)

    # PyInstaller 安装版不能把自身当作 Python 解释器再次执行；安装包已
    # 内置固定演示产物，动态上报和新报表写入用户目录。
    if not args.skip_pipelines and not FROZEN:
        try:
            for name, folder in PIPELINES:
                _run_pipeline(name, folder)
        except (OSError, subprocess.CalledProcessError) as exc:
            print("[error] 技能包流水线失败: %s" % exc, file=sys.stderr)
            return 1

    try:
        console = _load_console()
        server = console.create_server(args.port, args.data_dir, args.log_file)
    except Exception as exc:
        message = "[error] 控制台启动失败: %s" % exc
        print(message, file=sys.stderr)
        try:
            Path(args.log_file).parent.mkdir(parents=True, exist_ok=True)
            with open(args.log_file, "a", encoding="utf-8") as log:
                log.write(message + "\n")
        except OSError:
            pass
        if FROZEN:
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, message, "智能制造演示包启动失败", 0x10)
            except Exception:
                pass
        return 2
    url = "http://127.0.0.1:%d" % args.port
    print("[factory-console] 已启动: %s" % url, flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[factory-console] 已停止")
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException as exc:
        log_file = DEFAULT_LOG_FILE
        message = "[fatal] %s: %s" % (type(exc).__name__, exc)
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(message + "\n")
        except OSError:
            pass
        if FROZEN:
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, message, "智能制造演示包启动失败", 0x10)
            except Exception:
                pass
        raise
