# -*- coding: utf-8 -*-
"""
设备点检 Skill - 分析算法脚本
=============================
功能：加载点检标准知识库，比对设备数据与阈值，输出正常/预警/严重/紧急状态与告警清单。

用法示例：
    python analysis.py                              # 使用默认数据文件分析
    python analysis.py --data ../data/device_data.json --out ../output/analysis_result.json

判定规则（与 docs/inspection_standards.md 一致）：
    正常 ≤ 正常区 < 预警 ≤ 预警区 < 严重 ≤ 紧急区 < 紧急
设备状态取该设备各点检项中最严重等级。
告警等级：预警=轻微；严重；紧急。

依赖：Python 标准库，无第三方依赖。
"""
import argparse
import json
import os
import sys
from datetime import datetime

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(SKILL_ROOT, "docs")
OUTPUT_DIR = os.path.join(SKILL_ROOT, "output")

STATUS_ORDER = ["正常", "预警", "严重", "紧急"]
STATUS_LEVEL = {"正常": 0, "预警": 1, "严重": 2, "紧急": 3}

ALERT_HINTS = {
    "预警": "24小时内复核；若持续越界，联系设备工程师排查。",
    "严重": "当班处理：停止作业检查，必要时切换备用产线，并通报班组长。",
    "紧急": "立即停机检修，同步通知设备工程师与安全管理，禁止带病运行。",
}


def _load_standards(path):
    """解析点检标准知识库 Markdown 表格。"""
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
                    "period": cells[11],
                    "note": cells[12],
                })
            except ValueError:
                continue
    return rows


def judge_status(value, spec):
    """单项状态判定。"""
    v = value
    # 连接类特殊处理：1=连接(正常) 0=断连(紧急)，标准表预警/紧急区填 1~0 表示不可比
    if spec["unit"] == "连接":
        return "紧急" if v <= 0 else "正常"
    if v < spec["crit_low"] or v > spec["crit_high"]:
        return "紧急"
    if v < spec["warn_low"] or v > spec["warn_high"]:
        return "严重"
    if v < spec["normal_low"] or v > spec["normal_high"]:
        return "预警"
    return "正常"


def analyze(data_path, standards_path):
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rules = _load_standards(standards_path)
    # 按设备代码建立索引
    rule_map = {}
    for r in rules:
        rule_map.setdefault(r["device_id"], []).append(r)

    devices_result = []
    alerts = []
    summary = {"正常": 0, "预警": 0, "严重": 0, "紧急": 0}

    for dev in data["devices"]:
        dev_id = dev["device_id"]
        specs = rule_map.get(dev_id, [])
        items = []
        device_worst = 0
        device_issue = None
        for spec in specs:
            param = spec["param"]
            prm = dev["params"].get(param)
            if prm is None:
                continue
            value = prm["current"]
            status = judge_status(value, spec)
            level = STATUS_LEVEL[status]
            items.append({
                "param": param,
                "unit": spec["unit"],
                "value": value,
                "min_24h": prm.get("min"),
                "max_24h": prm.get("max"),
                "avg_24h": prm.get("avg"),
                "over_count_24h": prm.get("over_count", 0),
                "status": status,
                "normal_low": spec["normal_low"],
                "normal_high": spec["normal_high"],
                "note": spec["note"],
            })
            if level > device_worst:
                device_worst = level
                device_issue = param
            if status != "正常":
                alerts.append({
                    "device_id": dev_id,
                    "device_name": spec["device_name"],
                    "enterprise": spec["enterprise"],
                    "param": param,
                    "unit": spec["unit"],
                    "value": value,
                    "normal_range": f"{spec['normal_low']}~{spec['normal_high']}",
                    "crit_range": f"{spec['crit_low']}~{spec['crit_high']}",
                    "status": status,
                    "over_count": prm.get("over_count", 0),
                    "action_hint": ALERT_HINTS[status],
                })

        dev_status = STATUS_ORDER[device_worst]
        summary[dev_status] += 1
        devices_result.append({
            "device_id": dev_id,
            "device_name": dev["device_name"],
            "enterprise": dev["enterprise"],
            "status": dev_status,
            "worst_param": device_issue,
            "items": items,
        })

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_time": data.get("generated_at"),
        "data_source": data.get("source"),
        "summary": summary,
        "devices": devices_result,
        "alerts": alerts,
    }


def main():
    parser = argparse.ArgumentParser(description="设备点检 - 分析算法")
    parser.add_argument("--data", default=os.path.join(SKILL_ROOT, "data", "device_data.json"),
                        help="设备数据JSON路径")
    parser.add_argument("--standards", default=os.path.join(DOCS_DIR, "inspection_standards.md"),
                        help="点检标准知识库路径")
    parser.add_argument("--out", default=os.path.join(OUTPUT_DIR, "analysis_result.json"),
                        help="分析结果输出路径")
    args = parser.parse_args()

    if not os.path.exists(args.data):
        print("[analysis] 错误：未找到设备数据文件，请先运行 data_fetch.py 生成数据。")
        sys.exit(1)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    result = analyze(args.data, args.standards)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    s = result["summary"]
    print(f"[analysis] 分析完成 → {args.out}")
    print(f"[analysis] 设备状态：正常 {s['正常']} 台 / 预警 {s['预警']} 台 / "
          f"严重 {s['严重']} 台 / 紧急 {s['紧急']} 台")
    print(f"[analysis] 共发现告警 {len(result['alerts'])} 条")
    for a in result["alerts"]:
        print(f"  - [{a['status']}] {a['device_id']} {a['device_name']} / {a['param']}"
              f"={a['value']}{a['unit']}（正常限 {a['normal_range']}）")


if __name__ == "__main__":
    sys.exit(main())