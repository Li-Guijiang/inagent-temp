# -*- coding: utf-8 -*-
"""四大 Agent 接口自动化验证脚本。"""
import json
import urllib.request

base = "http://127.0.0.1:8848"


def get(p):
    return json.load(urllib.request.urlopen(base + p))


def post(p, obj):
    req = urllib.request.Request(
        base + p, data=json.dumps(obj).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


results = {"A1": False, "A2": False, "A3": False, "A4": False}

# ---- A1 智能质检 Agent ----
print("=== A1 智能质检 Agent (质检上报) ===")
q = get("/api/quality")
print("列表:", "ok=", q.get("ok"), "| agent=", q.get("agent"), "| 巡检项=", len(q.get("devices", [])))
r1 = post("/api/quality/report", {"line": "1号装配线", "batch": "B-20260922-A1",
                                  "result": "合格", "shift": "白班", "remark": "A1验证"})
print("上报:", r1.get("ok"), "| 记录=", r1.get("record", {}).get("id"))
results["A1"] = bool(q.get("ok")) and bool(r1.get("ok"))

# ---- A2 工艺知识 Agent ----
print("\n=== A2 工艺知识 Agent (工艺文档解析) ===")
doc = "焊接电流：180 A\n焊接电压：24 V\n保护气流量：15 L/min\n电流范围 170~190\n预热温度：80 ℃"
p = post("/api/agent/parse-process", {"doc_text": doc})
print("解析: ok=", p.get("ok"), "| agent=", p.get("agent"), "| 参数数=", p.get("param_count"))
for x in p.get("params", []):
    print("  ", x["name"], "=", x["value"], x.get("unit") or "", x.get("range") or "")
results["A2"] = bool(p.get("ok")) and p.get("param_count", 0) >= 1

# ---- A3 产线数据 Agent ----
print("\n=== A3 产线数据 Agent (生产报表生成) ===")
rep = get("/api/agent/report")
print("报表: ok=", rep.get("ok"), "| agent=", rep.get("agent"), "| 模块数=", rep.get("summary", {}).get("modules"))
for row in rep.get("rows", []):
    print(f"  {row['pack']}: 正常{row['normal']} 预警{row['warning']} 严重{row['severe']} 紧急{row['critical']} 告警{row['alerts']}")
print("Excel:", rep.get("excel_url"))
results["A3"] = bool(rep.get("ok")) and bool(rep.get("excel_url"))

# ---- A4 设备运维 Agent ----
print("\n=== A4 设备运维 Agent (设备告警) ===")
a = get("/api/alerts")
print("告警: ok=", a.get("ok"), "| agent=", a.get("agent"), "| 告警数=", len(a.get("alerts", [])))
for x in a.get("alerts", []):
    print(f"  [{x['status']}] {x['device_name']} {x['param']}={x['value']}{x['unit']}")
results["A4"] = bool(a.get("ok"))

print("\n" + "=" * 40)
for k, v in results.items():
    print(f"Agent {k}: {'✅ 调用正常' if v else '❌ 调用失败'}")
print("=" * 40)
print("全部通过" if all(results.values()) else "存在失败项")