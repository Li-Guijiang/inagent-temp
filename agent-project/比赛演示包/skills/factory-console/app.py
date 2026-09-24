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
import os
import re
import sys
import threading
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# Windows 控制台默认编码可能不支持中文，统一为 UTF-8
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSOLE_ROOT = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(CONSOLE_ROOT, "web")
DATA_DIR = os.path.join(CONSOLE_ROOT, "data")
REPORTS_DIR = os.path.join(CONSOLE_ROOT, "reports")
REPORTS_FILE = os.path.join(DATA_DIR, "quality_reports.json")
LOCK = threading.Lock()

# 实时动态数据服务（端口5000）。控制台每次刷新优先实时取数，失败回退静态快照。
LIVE_BASE = "http://127.0.0.1:5000/api/live/"

DATA_SOURCES = {
    "alerts": os.path.join(SKILL_ROOT, "equipment-inspection", "output", "analysis_result.json"),
    "quality": os.path.join(SKILL_ROOT, "quality-inspection", "output", "analysis_result.json"),
    "energy": os.path.join(SKILL_ROOT, "energy-analysis", "output", "analysis_result.json"),
    "process": os.path.join(SKILL_ROOT, "process-optimization", "output", "analysis_result.json"),
    "traceability": os.path.join(SKILL_ROOT, "quality-traceability", "output", "analysis_result.json"),
}

LIVE_SOURCE = {
    "alerts": "equipment",
    "quality": "quality",
    "energy": "energy",
    "process": "process",
    "traceability": "traceability",
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


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _live_fetch(key):
    """从动态数据服务实时拉取分析结果；成功返回 dict，失败返回 None。"""
    try:
        url = LIVE_BASE + LIVE_SOURCE[key]
        with urllib.request.urlopen(url, timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _resolve(key, fields_ok=True):
    """优先实时取数；失败回退静态快照文件。返回 res dict 或 None。"""
    live = _live_fetch(key)
    if live and live.get("ok", True):
        return live
    return _load_json(DATA_SOURCES[key])


def _load_reports():
    try:
        with open(REPORTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save_reports(reports):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# A1 智能质检 Agent
# ---------------------------------------------------------------------------
def api_alerts():
    """设备告警：优先实时取数（每次刷新自动更新），失败回退静态快照。"""
    res = _resolve("alerts")
    if not res:
        return {"ok": False, "msg": "暂无设备数据，请先运行设备点检流水线"}
    alerts = sorted(res.get("alerts", []),
                    key=lambda a: {"预警": 1, "严重": 2, "紧急": 3}.get(a["status"], 0),
                    reverse=True)
    return {
        "ok": True,
        "agent": "A4",
        "agent_name": "设备运维 Agent（设备告警）",
        "live": "live" in res.get("data_source", ""),
        "updated_at": res.get("data_time"),
        "summary": res.get("summary", {}),
        "alerts": alerts,
        "normal_count": sum(1 for d in res.get("devices", []) if d["status"] == "正常"),
        "total": len(res.get("devices", [])),
    }


def api_quality():
    """质检总览：优先实时取数，保留上报记录。"""
    res = _resolve("quality")
    if not res:
        return {"ok": False, "msg": "暂无质检数据，请先运行质量巡检流水线"}
    reports = _load_reports()
    return {
        "ok": True,
        "agent": "A1",
        "agent_name": "智能质检 Agent（质检上报）",
        "live": "live" in res.get("data_source", ""),
        "updated_at": res.get("data_time"),
        "summary": res.get("summary", {}),
        "devices": res.get("devices", []),
        "submitted_today": len([r for r in reports if r.get("date") == datetime.now().strftime("%Y-%m-%d")]),
        "recent_reports": sorted(reports, key=lambda r: r.get("time", ""), reverse=True)[:20],
    }


def api_submit_report(payload):
    """A1 质检上报：操作工提交一条质检记录。"""
    required = {"line", "batch", "result"}
    if not payload or not required.issubset(payload.keys()):
        return {"ok": False, "msg": "请完整填写工位、批次与结果"}
    report = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3],
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "shift": payload.get("shift", "白班"),
        "line": payload["line"].strip(),
        "batch": payload["batch"].strip(),
        "result": payload["result"].strip(),
        "remark": payload.get("remark", "").strip(),
        "reported_by": payload.get("operator", "操作工"),
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
    text = (payload or {}).get("doc_text", "").strip() or SAMPLE_PROCESS_DOC
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
    res = _resolve(key)
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
    wb.save(path)
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
    except Exception as e:
        xlsx_path, file_name = None, None
        _xlsx_err = str(e)
    return {
        "ok": True,
        "agent": "A3",
        "agent_name": "产线数据 Agent（生产报表自动生成）",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "rows": rows,
        "excel_url": f"/reports/{file_name}" if file_name else None,
        "excel_error": None if file_name else (_xlsx_err if "xlsx_err" in dir() else "生成 xlsx 失败"),
    }


# ---------------------------------------------------------------------------
# 能耗看板
# ---------------------------------------------------------------------------
def api_energy():
    res = _resolve("energy")
    if not res:
        return {"ok": False, "msg": "暂无能耗数据，请先运行能耗分析流水线"}
    return {
        "ok": True,
        "agent": "看板",
        "agent_name": "能耗看板",
        "live": "live" in res.get("data_source", ""),
        "updated_at": res.get("data_time"),
        "summary": res.get("summary", {}),
        "devices": res.get("devices", []),
        "abnormal": [a for a in res.get("alerts", []) if a["status"] != "正常"],
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, relpath):
        path = os.path.abspath(os.path.join(WEB_DIR, relpath))
        if not path.startswith(os.path.abspath(WEB_DIR)) or not os.path.isfile(path):
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
            return self._send(200, json.dumps(api_alerts(), ensure_ascii=False).encode("utf-8"))
        if parsed.path == "/api/quality":
            return self._send(200, json.dumps(api_quality(), ensure_ascii=False).encode("utf-8"))
        if parsed.path == "/api/energy":
            return self._send(200, json.dumps(api_energy(), ensure_ascii=False).encode("utf-8"))
        if parsed.path == "/api/agent/report":
            return self._send(200, json.dumps(api_production_report(), ensure_ascii=False).encode("utf-8"))
        return self._send(404, b"not found", "text/plain; charset=utf-8")

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            payload = {}
        if parsed.path == "/api/quality/report":
            return self._send(200, json.dumps(api_submit_report(payload), ensure_ascii=False).encode("utf-8"))
        if parsed.path == "/api/agent/parse-process":
            return self._send(200, json.dumps(api_parse_process(payload), ensure_ascii=False).encode("utf-8"))
        return self._send(404, b"not found", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        sys.stdout.write("[console] %s\n" % (fmt % args))


def main():
    parser = argparse.ArgumentParser(description="工厂操作工控制台（四大 Agent）")
    parser.add_argument("--port", type=int, default=8848)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[factory-console] 操作工控制台已启动：http://127.0.0.1:{args.port}")
    print(f"[factory-console] 四大 Agent：A1质检上报 / A2工艺解析 / A3生产报表 / A4设备告警 ＋ 能耗看板")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[factory-console] 已停止")


if __name__ == "__main__":
    main()