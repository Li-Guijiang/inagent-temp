# -*- coding: utf-8 -*-
"""
工厂操作工控制台 - 后端服务（四大 Agent 版）
============================================
操作工视角业务界面，挂载 4 个 Agent 调用入口 + 能耗看板：

  A1 智能质检 Agent  → 质检上报        POST /api/quality/report
  A2 工艺知识 Agent  → 工艺文档智能解析  POST /api/agent/parse-process
  A3 产线数据 Agent  → 生产报表自动生成  GET  /api/agent/report
  A4 设备运维 Agent  → 设备告警        GET  /api/alerts
  车间看板           → 能耗看板        GET  /api/energy

所有 Agent 均使用 Python 标准库 + openpyxl 实现真实可运行逻辑（零外部服务依赖）。

启动：
    python app.py --port 8848
    浏览器访问 http://127.0.0.1:8848

数据来源（只读）：
    ../equipment-inspection/output/analysis_result.json   设备告警
    ../quality-inspection/output/analysis_result.json    质检总览
    ../energy-analysis/output/analysis_result.json       能耗看板
    ../process-optimization/output/analysis_result.json  工艺数据
    ../quality-traceability/output/analysis_result.json  追溯数据
质检上报记录：data/quality_reports.json
"""
import argparse
import json
import logging
import os
import re
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# Windows 控制台默认编码可能不支持中文，统一为 UTF-8
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSOLE_ROOT = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(CONSOLE_ROOT, "web")
DATA_DIR = os.path.join(CONSOLE_ROOT, "data")
REPORTS_DIR = os.path.join(CONSOLE_ROOT, "reports")
REPORTS_FILE = os.path.join(DATA_DIR, "quality_reports.json")
LOCK = threading.Lock()
MAX_BODY_BYTES = 1024 * 1024
LOGGER = logging.getLogger("factory-console")

DATA_SOURCES = {
    "alerts": os.path.join(SKILL_ROOT, "equipment-inspection", "output", "analysis_result.json"),
    "quality": os.path.join(SKILL_ROOT, "quality-inspection", "output", "analysis_result.json"),
    "energy": os.path.join(SKILL_ROOT, "energy-analysis", "output", "analysis_result.json"),
    "process": os.path.join(SKILL_ROOT, "process-optimization", "output", "analysis_result.json"),
    "traceability": os.path.join(SKILL_ROOT, "quality-traceability", "output", "analysis_result.json"),
}

PACK_NAMES = {
    "alerts": ["设备点检", "equipment-inspection"],
    "quality": ["质量巡检", "quality-inspection"],
    "energy": ["能耗分析", "energy-analysis"],
    "process": ["工艺优化", "process-optimization"],
    "traceability": ["质量追溯", "quality-traceability"],
}

# A2 工艺知识 Agent 的示例工艺文档（可在前端替换/上传自有文档）
SAMPLE_PROCESS_DOC = """# 电池箱体弧焊工艺参数卡（示例）
焊接电流：180 A
焊接电压：24 V
焊接速度：12 mm/s
保护气流量：15 L/min
送丝速度：8 m/min
焊枪倾角：75 度
预热温度：80 ℃
电流范围 170~190，电压范围 22~26"""


def configure_runtime(data_dir=None, log_file=None):
    """配置运行时可写目录和日志；技能包数据仍保持只读。"""
    global DATA_DIR, REPORTS_DIR, REPORTS_FILE
    if data_dir:
        DATA_DIR = os.path.abspath(os.path.expanduser(data_dir))
    REPORTS_DIR = os.path.join(DATA_DIR, "reports")
    REPORTS_FILE = os.path.join(DATA_DIR, "quality_reports.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        LOGGER.warning("数据文件不存在: %s", path)
    except (OSError, ValueError) as exc:
        LOGGER.error("读取数据文件失败 %s: %s", path, exc)
    return None


def _load_reports():
    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        LOGGER.error("读取质检上报记录失败: %s", exc)
        return []


def _save_reports(reports):
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_path = REPORTS_FILE + ".tmp"
    with open(temp_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, REPORTS_FILE)


# ---------------------------------------------------------------------------
# A1 智能质检 Agent
# ---------------------------------------------------------------------------
def api_alerts():
    """设备告警：汇总全部设备状态 + 告警条（严重/紧急优先）。"""
    res = _load_json(DATA_SOURCES["alerts"])
    if not res:
        return {"ok": False, "msg": "暂无设备数据，请先运行设备点检流水线"}
    alerts = sorted(res.get("alerts", []),
                    key=lambda a: {"预警": 1, "严重": 2, "紧急": 3}.get(a["status"], 0),
                    reverse=True)
    return {
        "ok": True,
        "agent": "A4",
        "agent_name": "设备运维 Agent（设备告警）",
        "updated_at": res.get("data_time"),
        "summary": res.get("summary", {}),
        "alerts": alerts,
        "normal_count": sum(1 for d in res.get("devices", []) if d["status"] == "正常"),
        "total": len(res.get("devices", [])),
    }


def api_quality():
    """质检总览：台账概要 + 上报记录。"""
    res = _load_json(DATA_SOURCES["quality"])
    if not res:
        return {"ok": False, "msg": "暂无质检数据，请先运行质量巡检流水线"}
    reports = _load_reports()
    return {
        "ok": True,
        "agent": "A1",
        "agent_name": "智能质检 Agent（质检上报）",
        "updated_at": res.get("data_time"),
        "summary": res.get("summary", {}),
        "devices": res.get("devices", []),
        "submitted_today": len([r for r in reports if r.get("date") == datetime.now().strftime("%Y-%m-%d")]),
        "recent_reports": sorted(reports, key=lambda r: r.get("time", ""), reverse=True)[:20],
    }


def api_submit_report(payload):
    """A1 质检上报：操作工提交一条质检记录。"""
    required = {"line", "batch", "result"}
    if not isinstance(payload, dict) or not required.issubset(payload.keys()):
        return {"ok": False, "msg": "请完整填写工位、批次与结果"}
    allowed_results = {"合格", "待复检", "不合格"}
    values = {key: str(payload.get(key, "")).strip() for key in required}
    if any(not values[key] for key in ("line", "batch", "result")):
        return {"ok": False, "msg": "工位、批次与结果不能为空"}
    if values["result"] not in allowed_results:
        return {"ok": False, "msg": "质检结果必须是：合格、待复检或不合格"}
    if len(values["line"]) > 100 or len(values["batch"]) > 100:
        return {"ok": False, "msg": "工位和批次号长度不能超过 100 个字符"}
    report = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3],
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "shift": payload.get("shift", "白班"),
        "line": values["line"],
        "batch": values["batch"],
        "result": values["result"],
        "remark": str(payload.get("remark", "")).strip()[:500],
        "reported_by": str(payload.get("operator", "操作工")).strip()[:100] or "操作工",
    }
    with LOCK:
        reports = _load_reports()
        reports.append(report)
        _save_reports(reports)
    return {"ok": True, "record": report}


# ---------------------------------------------------------------------------
# A2 工艺知识 Agent：工艺文档智能解析
# ---------------------------------------------------------------------------
def _parse_process_text(text):
    """从工艺文档中提取结构化工艺参数。

    支持两类格式：
      1) 键值行：`参数名：数值 单位` / `参数名: 数值 单位`
      2) 含范围说明：`参数名 范围 a~b`（记录到 range 字段）
    """
    params = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "//", "-")):
            continue
        # 键值行：参数名：数值 单位
        m = re.match(r"^([\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z0-9（）()/\s]{0,24}?)[:：]\s*([-+]?\d+(?:\.\d+)?)\s*([^\s\d.,，;；]*)\s*$", line)
        if m:
            params.append({
                "name": m.group(1).strip(),
                "value": float(m.group(2)),
                "unit": m.group(3).strip(),
                "range": "",
            })
            continue
        # 参数 + 范围，如 "电流范围 170~190"
        m2 = re.match(r"^([\u4e00-\u9fa5A-Za-z0-9（）()/\s]{1,24}?)[\s]*([-+]?\d+(?:\.\d+)?)\s*[~～\-—]\s*([-+]?\d+(?:\.\d+)?)\s*([^\s\d.,，;；]*)\s*$", line)
        if m2:
            params.append({
                "name": m2.group(1).strip(),
                "value": round((float(m2.group(2)) + float(m2.group(3))) / 2, 2),
                "unit": m2.group(4).strip(),
                "range": f"{m2.group(2)}~{m2.group(3)}",
            })
    return params


def api_parse_process(payload):
    """A2 工艺文档智能解析：解析文档 → 结构化参数 + 建议区间。"""
    if payload is not None and not isinstance(payload, dict):
        return {"ok": False, "msg": "请求体必须是 JSON 对象"}
    text = str((payload or {}).get("doc_text", "")).strip() or SAMPLE_PROCESS_DOC
    if len(text) > 100_000:
        return {"ok": False, "msg": "工艺文档不能超过 100000 个字符"}
    params = _parse_process_text(text)
    if not params:
        return {"ok": False, "msg": "未能从文档中识别到工艺参数，请检查格式（参数名：数值 单位）"}
    # 计算字段统计
    uniq_units = sorted({p["unit"] for p in params})
    return {
        "ok": True,
        "agent": "A2",
        "agent_name": "工艺知识 Agent（工艺文档智能解析）",
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lines": len(text.splitlines()),
        "param_count": len(params),
        "units": uniq_units,
        "params": params,
        "source": "示例工艺文档" if not (payload or {}).get("doc_text", "").strip() else "用户上传文档",
    }


# ---------------------------------------------------------------------------
# A3 产线数据 Agent：生产报表自动生成
# ---------------------------------------------------------------------------
def _pack_summary(key):
    res = _load_json(DATA_SOURCES[key])
    if not res:
        return {"pack": PACK_NAMES[key][0], "ok": False, "summary": {}, "alerts": 0, "updated": "-"}
    s = res.get("summary", {})
    alerts = res.get("alerts", [])
    return {
        "pack": PACK_NAMES[key][0],
        "code": key,
        "ok": True,
        "summary": s,
        "normal": s.get("正常", 0),
        "warning": s.get("预警", 0),
        "severe": s.get("严重", 0),
        "critical": s.get("紧急", 0),
        "alerts": len(alerts),
        "updated": res.get("data_time", "-"),
    }


def _gen_excel_report(rows, path):
    """用 openpyxl 生成生产综合报表 xlsx。"""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "生产综合报表"
    ws.append(["生产综合报表", "", "", ""])
    ws.append(["生成时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "", ""])
    ws.append([])
    ws.append(["模块", "正常", "预警", "严重", "紧急", "告警数", "更新时间"])
    for r in rows:
        ws.append([r["pack"], r["normal"], r["warning"], r["severe"], r["critical"], r["alerts"], r["updated"]])
    for cell in ws[1]:
        cell.font = Font(bold=True, size=14)
    temp_path = path + ".tmp"
    wb.save(temp_path)
    os.replace(temp_path, path)
    return path


def api_production_report():
    """A3 生产报表自动生成：汇总全部技能包结果 → JSON 视图 + Excel 文件。"""
    keys = ["alerts", "quality", "energy", "process", "traceability"]
    rows = [_pack_summary(k) for k in keys]
    total_normal = sum(r["normal"] for r in rows)
    total_alert = sum(r["alerts"] for r in rows)
    summary = {
        "modules": len(keys),
        "total_normal": total_normal,
        "total_alerts": total_alert,
        "severe_or_critical": sum(1 for r in rows if r["severe"] + r["critical"] > 0),
    }
    # 生成 Excel 报表
    os.makedirs(REPORTS_DIR, exist_ok=True)
    xlsx_path = os.path.join(REPORTS_DIR,
                             f"production_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    try:
        _gen_excel_report(rows, xlsx_path)
        file_name = os.path.basename(xlsx_path)
    except (ImportError, OSError, ValueError) as e:
        xlsx_path, file_name = None, None
        _xlsx_err = "生成 Excel 失败：%s" % e
    return {
        "ok": True,
        "agent": "A3",
        "agent_name": "产线数据 Agent（生产报表自动生成）",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "rows": rows,
        "excel_url": f"/reports/{file_name}" if file_name else None,
        "excel_error": None if file_name else _xlsx_err,
    }


# ---------------------------------------------------------------------------
# 能耗看板
# ---------------------------------------------------------------------------
def api_energy():
    res = _load_json(DATA_SOURCES["energy"])
    if not res:
        return {"ok": False, "msg": "暂无能耗数据，请先运行能耗分析流水线"}
    return {
        "ok": True,
        "agent": "看板",
        "agent_name": "能耗看板",
        "updated_at": res.get("data_time"),
        "summary": res.get("summary", {}),
        "devices": res.get("devices", []),
        "abnormal": [a for a in res.get("alerts", []) if a["status"] != "正常"],
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, payload):
        return self._send(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def _static(self, relpath):
        root = os.path.abspath(WEB_DIR)
        path = os.path.abspath(os.path.join(root, relpath))
        if os.path.commonpath((root, path)) != root or not os.path.isfile(path):
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        ext = os.path.splitext(path)[1].lower()
        ctype = {"": "text/plain", ".html": "text/html; charset=utf-8",
                 ".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8",
                 ".svg": "image/svg+xml"}.get(ext, "application/octet-stream")
        with open(path, "rb") as f:
            return self._send(200, f.read(), ctype)

    def _reports(self, relpath):
        path = os.path.abspath(os.path.join(REPORTS_DIR, os.path.basename(relpath)))
        if not path.endswith(".xlsx") or not os.path.isfile(path):
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        with open(path, "rb") as f:
            return self._send(200, f.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            return self._static("index.html")
        if parsed.path.startswith("/static/"):
            return self._static(parsed.path[len("/static/"):])
        if parsed.path.startswith("/reports/"):
            return self._reports(parsed.path[len("/reports/"):])
        if parsed.path == "/api/alerts":
            return self._json(200, api_alerts())
        if parsed.path == "/api/quality":
            return self._json(200, api_quality())
        if parsed.path == "/api/energy":
            return self._json(200, api_energy())
        if parsed.path == "/api/agent/report":
            return self._json(200, api_production_report())
        if parsed.path == "/api/health":
            return self._json(200, {"ok": True, "service": "factory-console",
                                    "time": datetime.now().isoformat(timespec="seconds")})
        # Local line-MCP compatibility endpoints. They expose the same
        # normalized contracts used by the four business Agents, so a skill
        # can switch from demo files to a callable local service without
        # changing its downstream analysis code.
        mcp_routes = {
            "/mcp/device": api_alerts,
            "/mcp/quality": api_quality,
            "/mcp/energy": api_energy,
            "/mcp/process": lambda: {"ok": True, "source": "local-mcp", "data": _load_json(DATA_SOURCES["process"])},
            "/mcp/traceability": lambda: {"ok": True, "source": "local-mcp", "data": _load_json(DATA_SOURCES["traceability"])},
        }
        if parsed.path in mcp_routes:
            result = mcp_routes[parsed.path]()
            result["source"] = "local-mcp:8848"
            return self._json(200, result)
        return self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if length < 0 or length > MAX_BODY_BYTES:
                return self._json(413, {"ok": False, "msg": "请求体大小必须在 0 到 1 MB 之间"})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            LOGGER.warning("无效 JSON 请求 %s: %s", self.path, exc)
            return self._json(400, {"ok": False, "msg": "请求必须是有效的 UTF-8 JSON"})
        if parsed.path == "/api/quality/report":
            result = api_submit_report(payload)
            return self._json(200 if result.get("ok") else 400, result)
        if parsed.path == "/api/agent/parse-process":
            result = api_parse_process(payload)
            return self._json(200 if result.get("ok") else 400, result)
        return self._send(404, b"not found", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        LOGGER.info("%s", fmt % args)


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def create_server(port=8848, data_dir=None, log_file=None):
    if not 0 <= port <= 65535:
        raise ValueError("端口必须在 0 到 65535 之间")
    configure_runtime(data_dir, log_file)
    return ReusableThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description="工厂操作工控制台（四大 Agent）")
    parser.add_argument("--port", type=int, default=8848, help="监听端口（默认 8848）")
    parser.add_argument("--data-dir", help="运行时可写数据目录，默认 skills/factory-console/data")
    parser.add_argument("--log-file", help="日志文件路径")
    args = parser.parse_args(argv)
    try:
        server = create_server(args.port, args.data_dir, args.log_file)
    except (OSError, ValueError) as exc:
        LOGGER.error("控制台启动失败: %s", exc)
        return 2
    print(f"[factory-console] 操作工控制台已启动：http://127.0.0.1:{args.port}")
    print(f"[factory-console] 四大 Agent：A1质检上报 / A2工艺解析 / A3生产报表 / A4设备告警 ＋ 能耗看板")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[factory-console] 已停止")
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())