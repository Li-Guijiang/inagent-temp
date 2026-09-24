# -*- coding: utf-8 -*-
"""
设备点检 Skill - 数据采集脚本
=============================
功能：拉取设备最近运行数据（演示模式生成模拟数据；生产环境可对接设备数据 MCP）。

用法示例：
    python data_fetch.py                        # 默认演示模式，拉取全部设备最近24h数据
    python data_fetch.py --devices TJ-01,BJ-01  # 指定设备
    python data_fetch.py --hours 48 --out ../data/device_data.json

说明：
- 真实部署时，将 `_fetch_from_mcp(device_id)` 替换为对设备数据 MCP 的调用，
  并将 `--source demo` 改为 `--source mcp`。
- 演示数据会注入若干异常项（预警/严重/紧急），用于展示完整告警链路。

依赖：Python 标准库（random/json/datetime/argparse），无第三方依赖。
"""
import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(SKILL_ROOT, "docs")
DATA_DIR = os.path.join(SKILL_ROOT, "data")
DEFAULTS = os.path.join(DATA_DIR, "device_data.json")

# 演示模式注入的异常（用于演示告警链路，可自由调整）
DEMO_ANOMALIES = {
    "TJ-01": {"焊枪温度": 66.5},      # 出正常区，落在预警区 → 预警
    "BJ-01": {"主轴振动": 3.0},        # 出预警区，落在紧急区 → 严重
    "FQ-01": {"PLC通信连接状态": 0.0},  # 连接断开 → 紧急
}


def _load_standards():
    """从标准知识库解析每台设备的点检项定义（与 analysis.py 共用同一数据源）。"""
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
    devices = {}
    for r in rows:
        devices.setdefault(r["device_id"], {
            "device_id": r["device_id"],
            "device_name": r["device_name"],
            "enterprise": r["enterprise"],
            "check_items": r["device_id"],  # 占位，按设备归组
        })
    return rows, devices


def _build_device_map(rows):
    """按设备代码聚合点检项。"""
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
    """为单个点检项生成 hours 个采样点（最近 hours 小时），返回 {值, 统计}。"""
    lo, hi = r["normal_low"], r["normal_high"]
    # PLC 连接状态等枚举型，正常时恒为1
    if r["unit"] == "连接":
        return [1.0] * hours
    if lo == 0 and hi > 0:
        base = hi * 0.7
    elif hi == 0 and lo > 0:
        base = lo * 0.9
    elif lo < 0:
        # 负值范围（如真空负压 kPa），保持符号
        base = (lo + hi) / 2
    else:
        base = (lo + hi) / 2
    spread = max(abs(hi - lo) * 0.12, 1e-3)
    series = []
    for _ in range(hours):
        v = base + rng.gauss(0, spread)
        # 非负区间才做非负钳制；负值区间（真空负压）保留原始符号
        if lo >= 0:
            v = max(0.0, v)
        series.append(round(v, 2))
    return series


def _fetch_from_mcp(device_id):
    """真实数据源接口（占位）。

    在接入真实设备数据 MCP 后，此函数改为从 MCP 拉取数据，
    返回结构与 `_fetch_demo` 保持一致即可，下游无需改动。
    """
    raise NotImplementedError("请将 --source 切换为 demo，或在此接入真实设备数据 MCP")


def _fetch_demo(device_ids, hours, rng):
    rows, _ = _load_standards()
    devices = _build_device_map(rows)
    device_list = []
    for device_id, device in devices.items():
        if device_ids and device_id not in device_ids:
            continue
        params = {}
        for r in device["items"]:
            series = _gen_series(r, rng, hours)
            current = series[-1]
            # 注入演示异常
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
    parser = argparse.ArgumentParser(description="设备点检 - 数据采集")
    parser.add_argument("--source", choices=["demo", "mcp"], default="demo",
                        help="数据来源：demo=模拟数据(默认)，mcp=对接设备数据MCP")
    parser.add_argument("--devices", default="",
                        help="指定设备（逗号分隔），默认全部")
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
        devices = [_fetch_from_mcp(d) for d in device_ids] if device_ids else []
        source = "mcp(真实设备数据)"

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
        "hours": args.hours,
        "devices": devices,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[data_fetch] 已采集 {len(devices)} 台设备、最近{args.hours}h 数据 → {args.out}")
    print(f"[data_fetch] 数据来源：{source}（随机种子 seed={args.seed}）")


if __name__ == "__main__":
    sys.exit(main())