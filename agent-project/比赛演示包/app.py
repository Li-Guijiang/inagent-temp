"""
产线动态数据服务（MCP 连接器演示）－ 端口 5000
=============================================
为 5 个技能包提供"实时动态数据"的本地 MCP 服务，解决"数据静态/死数据"问题：

  - 每次请求都会重新生成动态采样数值（基于当前时间随机，非固定 seed）
  - 每次采样快照自动写入本地 SQLite（live_data/plant_live.db），实现"动态数据库，可查历史"
  - 支持按设备过滤；数值动态变化但保证每类告警（预警/严重/紧急）随机呈现，便于演示

端点：
  GET /api/device_warn          兼容旧接口（设备告警动态数据）
  GET /api/equipment            设备点检动态数据
  GET /api/quality              质量巡检动态数据
  GET /api/energy               能耗分析动态数据
  GET /api/process              工艺优化动态数据
  GET /api/traceability         质量追溯动态数据
  GET /api/history/<source>     查询某数据源的历史快照（数据库动态证明）
  GET /api/sources              列出全部数据源与最新采样时间

下游技能包切换方式：
  python scripts/data_fetch.py --source mcp
"""
import os
import random
import sqlite3
from datetime import datetime

from flask import Flask, jsonify, request

app = Flask(__name__)

# 项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(BASE_DIR, "skills")
LIVE_DB_DIR = os.path.join(BASE_DIR, "live_data")
LIVE_DB = os.path.join(LIVE_DB_DIR, "plant_live.db")

# 各数据源对应技能包
SOURCE_PACK = {
    "equipment": "equipment-inspection",
    "quality": "quality-inspection",
    "energy": "energy-analysis",
    "process": "process-optimization",
    "traceability": "quality-traceability",
}


# ---------------------------------------------------------------------------
# SQLite：动态数据库（每次采样快照入库，可查历史）
# ---------------------------------------------------------------------------
def _init_db():
    os.makedirs(LIVE_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(LIVE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            source TEXT NOT NULL,
            device_id TEXT NOT NULL,
            param TEXT NOT NULL,
            unit TEXT,
            current REAL,
            status TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_snap ON snapshots(source, device_id, param, ts)")
    conn.commit()
    conn.close()


def _save_snapshot(source, devices):
    """将一次动态采样整体写入 SQLite（每个参数一行）。"""
    conn = sqlite3.connect(LIVE_DB)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for dev in devices:
        for param, prm in dev["params"].items():
            rows.append((ts, source, dev["device_id"], param, prm["unit"],
                         prm["current"], prm.get("status", "")))
    conn.executemany(
        "INSERT INTO snapshots(ts, source, device_id, param, unit, current, status) "
        "VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()


def _latest_snapshots(source, limit=100):
    conn = sqlite3.connect(LIVE_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT * FROM snapshots WHERE source=? ORDER BY id DESC LIMIT ?", (source, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# 标准库解析（与各技能包 data_fetch.py 保持同一表结构）
# ---------------------------------------------------------------------------
def _load_standards(source):
    """从技能包 docs/inspection_standards.md 解析标准行。"""
    path = os.path.join(SKILLS_DIR, SOURCE_PACK[source], "docs", "inspection_standards.md")
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not (line.startswith("|") and line.endswith("|")):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 13 or cells[0] == "设备代码":
                continue
            try:
                rows.append({
                    "device_id": cells[0],
                    "device_name": cells[1],
                    "enterprise": cells[2],
                    "param": cells[3],
                    "unit": cells[4],
                    "normal_low": float(cells[5]),
                    "normal_high": float(cells[6]),
                    "warn_low": float(cells[7]),
                    "warn_high": float(cells[8]),
                    "crit_low": float(cells[9]),
                    "crit_high": float(cells[10]),
                })
            except ValueError:
                continue
    return rows


# ---------------------------------------------------------------------------
# 动态数值生成
# ---------------------------------------------------------------------------
def _gen_normal_series(r, rng, hours=24):
    """在正常区间内生成小时级序列（连接类恒为1）。"""
    lo, hi = r["normal_low"], r["normal_high"]
    if r["unit"] == "连接":
        return [1.0] * hours
    if lo == 0 and hi > 0:
        base = hi * 0.7
        spread = hi * 0.15
    elif hi == 0 and lo > 0:
        base = lo * 0.9
        spread = abs(lo) * 0.15
    elif lo < 0:
        base = (lo + hi) / 2
        spread = max(abs(hi - lo) * 0.12, 1e-3)
    else:
        base = (lo + hi) / 2
        spread = max(abs(hi - lo) * 0.12, 1e-3)
    series = []
    for _ in range(hours):
        v = base + rng.gauss(0, spread)
        if lo >= 0:
            v = max(0.0, v)
        series.append(round(v, 2))
    return series


def _inject_alert(r, rng, level):
    """把 r 对应参数戳到指定告警等级区间，返回异常值。

    level: '预警' / '严重' / '紧急'
    方向判断：normal_low==0 → 向上越界；否则按双向区间随机方向；连接类断连→紧急。
    百分比类（unit=%）向上越界时封顶 100%，避免出现 105%、186% 等物理不合理值。
    """
    if r["unit"] == "连接":
        return 0.0
    lo, hi = r["normal_low"], r["normal_high"]
    wl, wh = r["warn_low"], r["warn_high"]
    cl, ch = r["crit_low"], r["crit_high"]

    # 确定异常方向：1=高于上界，-1=低于下界
    # 高优型指标（正常区间在高位：如 95~100 / 85~100 的合格率、通过率、
    # 检出率、效率、覆盖率、锁定率），异常只向"低于下限"方向走，避免出现 186% 这类不真实数值
    # CPK 工艺能力指数同样"越高越好"，只向下越界（1.33 是标准门槛）
    if "CPK" in r["param"].upper() or (lo > 0 and 80 <= hi <= 100):
        direction = -1
    elif lo == 0:
        direction = 1
    elif hi == 0:
        direction = -1
    else:
        direction = rng.choice([1, -1])

    def _pick(a, b):
        if a is None or b is None:
            return None
        lo_v, hi_v = min(a, b), max(a, b)
        return lo_v + rng.random() * (hi_v - lo_v)

    base_norm = hi if direction == 1 else lo
    warn_b = wh if direction == 1 else wl
    crit_b = ch if direction == 1 else cl

    if level == "预警":
        if warn_b is not None and warn_b != base_norm:
            value = _pick(base_norm * 1.02 if direction == 1 and base_norm > 0 else base_norm,
                          warn_b * 0.98 if warn_b != 0 else warn_b) or base_norm
        else:
            value = (_pick(base_norm * 1.02, base_norm * 1.3) if direction == 1
                     else _pick(base_norm * 0.98, base_norm * 0.7))
    elif level == "严重":
        if crit_b is not None and crit_b != warn_b:
            value = _pick(warn_b * 1.02 if warn_b else base_norm * 1.05,
                          crit_b * 0.98 if crit_b else base_norm * 1.4) or base_norm
        else:
            value = (_pick(base_norm * 1.35, base_norm * 1.6) if direction == 1
                     else _pick(base_norm * 0.65, base_norm * 0.35))
    else:  # 紧急：超出 crit
        if crit_b is not None and crit_b != base_norm:
            value = (_pick(crit_b * 1.05, crit_b * 1.3) if direction == 1
                     else _pick(crit_b * 0.95, crit_b * 0.7))
        else:
            value = (_pick(base_norm * 1.7, base_norm * 2.0) if direction == 1
                     else _pick(base_norm * 0.3, base_norm * 0.1))

    if r["unit"] == "%" and direction == 1:
        value = min(value, 100.0)
    return round(float(value), 2)


def _status_of(r, value):
    """由值判定状态（与各包 analysis.py 判定规则一致）。"""
    lo, hi = r["normal_low"], r["normal_high"]
    wl, wh = r["warn_low"], r["warn_high"]
    cl, ch = r["crit_low"], r["crit_high"]

    def _in(v, low, high):
        return low <= v <= high

    if _in(value, lo, hi):
        return "正常"
    if _in(value, wl, wh):
        return "预警"
    if _in(value, cl, ch):
        return "严重"
    return "紧急"


def _collect_devices(source, rows, force_alert=(True, True, True)):
    """按标准库动态生成当前全部设备数据，并在各等级各注入一条以示展示完整。"""
    rng = random.Random()  # 每次请求独立随机，数据动态变化
    devices_map = {}
    for r in rows:
        d = devices_map.setdefault(r["device_id"], {
            "device_id": r["device_id"],
            "device_name": r["device_name"],
            "enterprise": r["enterprise"],
            "params": {},
        })
        d["params"][r["param"]] = {"unit": r["unit"], "current": None,
                                   "min": None, "max": None, "avg": None,
                                   "over_count": 0, "series": [], "status": ""}
    # 随机挑一批行用于注入告警（保证预警/严重/紧急各至少1条，且每次随机不同）
    alert_rows = rng.sample(rows, min(len(rows), 3))
    alert_levels = ["预警", "严重", "紧急"]
    alert_target = {}
    for i, r in enumerate(alert_rows):
        if force_alert[i]:
            alert_target[r["device_id"] + "|" + r["param"]] = alert_levels[i]

    for r in rows:
        key = r["device_id"] + "|" + r["param"]
        prm = devices_map[r["device_id"]]["params"][r["param"]]
        if key in alert_target:
            current = _inject_alert(r, rng, alert_target[key])
            series = _gen_normal_series(r, rng)
            series[-1] = current
            status = alert_target[key]
        else:
            series = _gen_normal_series(r, rng)
            current = series[-1]
            status = _status_of(r, current)
        prm.update({
            "current": current,
            "unit": r["unit"],
            "normal_range": f"{r['normal_low']}~{r['normal_high']}",
            "crit_range": f"{r['crit_low']}~{r['crit_high']}",
            "min": round(min(series), 2),
            "max": round(max(series), 2),
            "avg": round(sum(series) / len(series), 2),
            "over_count": sum(1 for v in series
                              if not (r["normal_low"] <= v <= r["normal_high"])),
            "series": series,
            "status": status,
        })
    # 设备级最严重状态聚合
    order = {"正常": 0, "预警": 1, "严重": 2, "紧急": 3}
    for d in devices_map.values():
        worst = "正常"
        worst_param = None
        for p, prm in d["params"].items():
            lv = order.get(prm["status"], 0)
            if lv > order[worst]:
                worst = prm["status"]
                worst_param = p
        d["status"] = worst
        d["worst_param"] = worst_param
    return list(devices_map.values())


def _build_response(source, device_ids=None):
    rows = _load_standards(source)
    if device_ids:
        rows = [r for r in rows if r["device_id"] in device_ids]
    devices = _collect_devices(source, rows)
    _save_snapshot(source, devices)
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": f"mcp(本地产线动态数据服务:{source})",
        "dynamic": True,
        "devices": devices,
    }


ALERT_HINTS = {
    "预警": "24小时内复核；若持续越界，联系相关工程师排查。",
    "严重": "当班处理；停止作业检查，必要时切换备用，并通报班组长。",
    "紧急": "立即停机/处置，同步通知工程师与安全管理。",
}

_STATUS_ORDER = ["正常", "预警", "严重", "紧急"]


def _build_analysis(source, device_ids=None):
    """实时生成分析结果（等价于技能包 analysis.py 的产物结构）：
    用于控制台每次刷新实时取数，不再依赖静态快照文件。
    """
    rows = _load_standards(source)
    if device_ids:
        rows = [r for r in rows if r["device_id"] in device_ids]
    devices = _collect_devices(source, rows)
    _save_snapshot(source, devices)

    summary = {"正常": 0, "预警": 0, "严重": 0, "紧急": 0}
    alerts = []
    for dev in devices:
        summary[dev["status"]] += 1
        for param, prm in dev["params"].items():
            if prm["status"] == "正常":
                continue
            alerts.append({
                "device_id": dev["device_id"],
                "device_name": dev["device_name"],
                "enterprise": dev["enterprise"],
                "param": param,
                "unit": prm["unit"],
                "value": prm["current"],
                "normal_range": prm["normal_range"],
                "crit_range": prm["crit_range"],
                "status": prm["status"],
                "over_count": prm.get("over_count", 0),
                "action_hint": ALERT_HINTS[prm["status"]],
            })
    alerts.sort(key=lambda a: _STATUS_ORDER.index(a["status"]), reverse=True)
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": f"live(动态实时:{source})",
        "summary": summary,
        "devices": devices,
        "alerts": alerts,
    }


# ---------------------------------------------------------------------------
# Flask 路由
# ---------------------------------------------------------------------------
@app.route("/api/device_warn")
def device_warn():
    """保留旧接口：设备告警动态数据（随机每次变化）。"""
    device_list = [
        {"device_id": "EQ001", "device_name": "数控加工中心A", "type": "加工设备"},
        {"device_id": "EQ002", "device_name": "精密检测仪B", "type": "质检设备"},
        {"device_id": "EQ003", "device_name": "输送线C", "type": "物流设备"},
        {"device_id": "EQ004", "device_name": "清洗机D", "type": "辅助设备"},
        {"device_id": "EQ005", "device_name": "空压机E", "type": "动力设备"},
    ]
    res_data = []
    for dev in device_list:
        temp = round(random.uniform(28.5, 76.2), 1)
        vibration = round(random.uniform(0.12, 4.8), 2)
        power = round(random.uniform(12.5, 48.6), 1)
        warn_level = "normal"
        warn_msg = "运行正常"
        if temp > 60 or vibration > 3.5:
            warn_level = "warning"
            warn_msg = "设备参数异常，请点检"
        if temp > 72 or vibration > 4.2:
            warn_level = "alarm"
            warn_msg = "严重告警，停机检查"
        res_data.append({
            "device_id": dev["device_id"],
            "device_name": dev["device_name"],
            "device_type": dev["type"],
            "temperature": temp,
            "vibration": vibration,
            "power_kW": power,
            "warn_level": warn_level,
            "warn_message": warn_msg,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    return jsonify(res_data)


@app.route("/api/<source>")
def skill_data(source):
    """动态数据端点：/api/equipment | quality | energy | process | traceability"""
    if source not in SOURCE_PACK:
        return jsonify({"ok": False, "msg": "未知数据源"}, ), 404
    devices_arg = request.args.get("devices", "")
    device_ids = [d.strip() for d in devices_arg.split(",") if d.strip()] or None
    return jsonify(_build_response(source, device_ids))


@app.route("/api/live/<source>")
def skill_live(source):
    """实时分析端点：每次请求现场生成动态数据并完成阈值判定，
    返回与分析产物一致的 summary/alerts/devices，供控制台实时刷新。
    """
    if source not in SOURCE_PACK:
        return jsonify({"ok": False, "msg": "未知数据源"}, ), 404
    devices_arg = request.args.get("devices", "")
    device_ids = [d.strip() for d in devices_arg.split(",") if d.strip()] or None
    return jsonify(_build_analysis(source, device_ids))


@app.route("/api/history/<source>")
def history(source):
    """历史快照查询：证明数据写入动态数据库、可追溯。"""
    if source not in SOURCE_PACK:
        return jsonify({"ok": False, "msg": "未知数据源"}, ), 404
    limit = min(int(request.args.get("limit", 100)), 1000)
    device = request.args.get("device", "")
    rows = _latest_snapshots(source, limit)
    if device:
        rows = [r for r in rows if r["device_id"] == device]
    return jsonify({"ok": True, "source": source, "count": len(rows), "rows": rows})


@app.route("/api/sources")
def sources():
    """列出全部数据源与库内已有采样数（动态数据库总览）。"""
    conn = sqlite3.connect(LIVE_DB)
    conn.row_factory = sqlite3.Row
    out = []
    for code in SOURCE_PACK:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt, MAX(ts) AS latest FROM snapshots WHERE source=?",
            (code,)).fetchone()
        out.append({"source": code, "pack": SOURCE_PACK[code],
                    "snapshots": row["cnt"], "latest_ts": row["latest"]})
    conn.close()
    return jsonify({"ok": True, "total": len(out), "sources": out})


@app.route("/")
def index():
    return jsonify({
        "ok": True,
        "name": "产线动态数据服务（MCP 连接器演示）",
        "dynamic": True,
        "endpoints": ["/api/device_warn", "/api/equipment", "/api/quality",
                      "/api/energy", "/api/process", "/api/traceability",
                      "/api/history/<source>", "/api/sources"],
        "note": "每次请求数据动态变化，并自动入库 live_data/plant_live.db",
    })


if __name__ == "__main__":
    _init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)