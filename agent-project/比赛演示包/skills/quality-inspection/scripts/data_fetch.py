# -*- coding: utf-8 -*-
"""
质量巡检 Skill - 数据采集脚本
=============================
功能：拉取质检数据（演示模式生成模拟数据；生产环境可对接质检数据 MCP）。

用法示例：
    python data_fetch.py                        # 默认演示模式，拉取全部质检生产线24h数据
    python data_fetch.py --devices TJ-01,BJ-01  # 指定产线
    python data_fetch.py --hours 48 --out ../data/quality_data.json

说明：
- 演示数据会注入若干异常项（预警/严重/紧急），用于展示完整告警链路。
- 真实部署时，将 `_fetch_from_mcp(device_id)` 替换为对质检数据 MCP 的调用，
  并将 `--source demo` 改为 `--source mcp`。

依赖：Python 标准库，无第三方依赖。
"""
import argparse
import json
import os
import random
import sys
import time
from datetime import datetime

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(SKILL_ROOT, "docs")
DATA_DIR = os.path.join(SKILL_ROOT, "data")
DEFAULTS = os.path.join(DATA_DIR, "quality_data.json")

# 演示模式注入的异常（用于演示告警链路，可自由调整）
DEMO_ANOMALIES = {
    "TJ-01": {"焊缝缺陷漏检率": 1.2},      # 超出正常上限(1.0)，落在预警区(1.0~1.5) → 预警
    "BJ-01": {"关键尺寸CPK": 1.15},         # 低于预警下限(1.2)，落在严重区(1.2~1.0) → 严重
    "FQ-01": {"一次装配合格率": 85.0},      # 低于紧急下限(89) → 紧急
}


def _load_standards():
    """从标准知识库解析每台设备/产线的点检项定义（与 analysis.py 共用同一数据源）。"""
    path = os.path.join(DOCS_DIR, "inspection_standards.md")
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


def _build_device_map(rows):
    """按设备代码聚合巡检项。"""
    devices = {}
    for r in rows:
        d = devices.setdefault(r["device_id"], {
            "device_id": r["device_id"],
            "device_name": r["device_name"],
            "enterprise": r["enterprise"],
            "items": [],
        })
        d["items"].append(r)
    return devices


def _gen_series(r, rng, hours):
    """为单个巡检项生成 hours 个采样点，返回列表。"""
    lo, hi = r["normal_low"], r["normal_high"]
    if lo == 0 and hi > 0:
        base = hi * 0.7
    elif hi == 0 and lo > 0:
        base = lo * 0.9
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


def _fetch_from_mcp(device_ids=None):
    """从本地产线动态数据服务（app.py 端口5000）拉取实时质检数据。

    调用 https://127.0.0.1:5000/api/quality，返回结构与 `_fetch_demo` 一致。
    服务不可用（未启动）时自动回退到 demo 模拟数据并告警。
    """
    import json as _json
    import urllib.request as _urlreq

    endpoint = "http://127.0.0.1:5000/api/quality"
    if device_ids:
        endpoint += "?devices=" + ",".join(device_ids)
    try:
        with _urlreq.urlopen(endpoint, timeout=5) as resp:
            payload = _json.loads(resp.read().decode("utf-8"))
        devices = payload.get("devices") or []
        if not devices:
            raise ValueError("动态服务返回空质检对象列表")
        return devices
    except Exception as e:
        print(f"[quality-inspection/data_fetch][warn] 动态数据服务不可用({e})，本次回退到 demo 模拟数据")
        _rng = random.Random(time.time_ns())
        return _fetch_demo(device_ids, 24, _rng)


def _fetch_demo(device_ids, hours, rng):
    rows = _load_standards()
    devices = _build_device_map(rows)
    device_list = []
    for device_id, device in devices.items():
        if device_ids and device_id not in device_ids:
            continue
        params = {}
        for r in device["items"]:
            series = _gen_series(r, rng, hours)
            current = series[-1]
            anomaly = DEMO_ANOMALIES.get(device_id, {}).get(r["param"])
            if anomaly is not None:
                current = anomaly
                series[-1] = anomaly
            within = r["normal_low"] <= current <= r["normal_high"]
            over_count = 0 if within else 1
            params[r["param"]] = {
                "unit": r["unit"],
                "current": current,
                "min": round(min(series), 2),
                "max": round(max(series), 2),
                "avg": round(sum(series) / len(series), 2),
                "over_count": over_count,
                "series": series,
            }
        device_list.append({
            "device_id": device["device_id"],
            "device_name": device["device_name"],
            "enterprise": device["enterprise"],
            "params": params,
        })
    return device_list


def main():
    parser = argparse.ArgumentParser(description="质量巡检 - 数据采集")
    parser.add_argument("--source", choices=["demo", "mcp"], default="demo",
                        help="数据来源：demo=模拟数据(默认)，mcp=对接质检数据MCP")
    parser.add_argument("--devices", default="",
                        help="指定产线（逗号分隔），默认全部")
    parser.add_argument("--hours", type=int, default=24, help="拉取最近N小时，默认24")
    parser.add_argument("--seed", type=int, default=42, help="随机种子，保证可复现")
    parser.add_argument("--out", default=DEFAULTS, help="输出JSON路径")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    rng = random.Random(args.seed)
    device_ids = [d.strip() for d in args.devices.split(",") if d.strip()]

    if args.source == "demo":
        devices = _fetch_demo(device_ids, args.hours, rng)
        source = "demo(模拟生成)"
    else:
        devices = _fetch_from_mcp(device_ids)
        source = "mcp(本地产线动态数据服务)"

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "hours": args.hours,
        "devices": devices,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[quality-inspection/data_fetch] 已采集 {len(devices)} 个质检对象、最近{args.hours}h 数据 → {args.out}")
    print(f"[quality-inspection/data_fetch] 数据来源：{source}（随机种子 seed={args.seed}）")


if __name__ == "__main__":
    sys.exit(main())