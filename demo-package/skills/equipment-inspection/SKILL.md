---
name: equipment-inspection
description: 设备点检。对工厂设备进行日常点检、故障预警和维护建议生成。当用户说"设备点检""检查设备状态"、每日定时任务触发或设备数据异常时触发。基于江苏 8 家智能制造企业调研日志中的设备场景（五轴加工中心、弧焊机器人、视觉检测、AOI、纺织AGV、工业互联网网关、非标自动化产线等）预置了点检标准知识库。
---

# 设备点检 Skill

## 用途
对工厂设备进行日常点检、故障预警和维护建议生成。

## 触发条件
- 用户说"设备点检"、"检查设备状态"
- 每日定时任务触发
- 设备数据异常时触发

## 目录结构
```
/skills/equipment_inspection/
├── SKILL.md              # 本说明文件
├── scripts/
│   ├── data_fetch.py     # 数据采集脚本（演示模式生成模拟数据；MCP 模式对接设备数据源）
│   ├── analysis.py       # 分析算法（阈值对比，判定 正常/预警/严重/紧急）
│   └── report_gen.py     # 报告生成（日报、告警文件、Excel 台账同步）
├── templates/
│   ├── daily_report.md   # 日报模板
│   └── alert_template.md # 告警模板
└── docs/
    └── inspection_standards.md  # 点检标准知识库（analysis.py 的判定依据）
```

## 操作流程
1. 调用设备数据 MCP 拉取最近 24 小时运行数据（当前以 `data_fetch.py --source demo` 模拟；接入真实设备数据 MCP 后切换 `--source mcp`，在脚本 `_fetch_from_mcp` 中实现）
2. 加载点检标准知识库 `docs/inspection_standards.md`
3. 对比设备数据与标准阈值（`analysis.py` 判定：正常 → 预警 → 严重 → 紧急）
4. 生成点检报告（正常项/异常项/预警项）（`report_gen.py`）
5. 如有异常，通过企业微信 MCP 发送告警（当前为占位接口 `_send_wecom_alert`，接入后启用）
6. 将报告保存到指定目录并同步到 Excel 台账（`output/inspection_ledger.xlsx`）

## 快速运行
```bash
# 进入技能目录
cd skills/equipment_inspection

# 1. 采集数据（演示模式）
python scripts/data_fetch.py

# 2. 分析（对比阈值，产出告警清单）
python scripts/analysis.py

# 3. 生成日报+告警+台账
python scripts/report_gen.py
```
执行成功后产出：
- `output/analysis_result.json` —— 分析结果（设备级+参数级状态、告警清单）
- `output/daily_report_YYYYMMDD.md` —— 设备点检日报
- `output/alert_<等级>_<时间>.md` —— 告警文件（按预警/严重/紧急分级）
- `output/inspection_ledger.xlsx` —— Excel 点检台账（逐项追加）

## 关键参数
| 参数 | 说明 | 取值示例 |
| --- | --- | --- |
| 点检设备范围 | 全部 / 指定车间 / 指定设备 | data_fetch.py `--devices TJ-01,BJ-01`（默认全部） |
| 时间范围 | 日报 / 周报 / 月报 | data_fetch.py `--hours 24/168/720`（默认24h） |
| 告警等级 | 轻微（预警）/ 严重 / 紧急 | 由 analysis.py 按阈值自动判定 |

## 告警等级定义
| 等级 | 状态 | 处置要求 |
| --- | --- | --- |
| 预警 | 超出正常区，落在预警区 | 24小时内复核；持续越界联系设备工程师 |
| 严重 | 超出预警区，落在紧急区 | 当班处理、停止作业检查、必要时切换备用产线 |
| 紧急 | 超出紧急区 或 通信断连 | 立即停机检修，同步通知设备工程师与安全管理 |

## 与江苏智能制造调研成果的关联
点检标准知识库依据 8 家江苏智能制造企业调研日志中暴露的**设备运维痛点**预置：
- 无锡贝斯特精机（五轴加工中心、高精度珩磨机——精密件加工停机即影响头部客户交付）
- 江苏天钧精密（弧焊机器人、FSW 搅拌摩擦焊专机——焊接设备超温易致焊缝缺陷）
- 苏州禾派阁 / 苏州聚晟视（机器视觉检测设备——相机热漂移、光源衰减、误检率）
- 樵弋机器人（UTG 超薄玻璃 AOI、自动收片装置——崩边漏检、负压吸附）
- 江苏赫伽力（纺织上纱 AGV、复合移动机器人——电池/定位/温升）
- 国投融合（DTiip 工业互联网边缘网关——CPU/内存/丢包率）
- 苏州富强（非标装配自动化产线——气缸压力、PLC 通信、导轨润滑）

新设备接入时，在 `docs/inspection_standards.md` 中按表格结构追加一行即可，脚本无需改动。

## 扩展点
| 扩展项 | 位置 |
| --- | --- |
| 对接真实设备数据 MCP | `data_fetch.py::_fetch_from_mcp` |
| 对接企业微信 MCP 发送告警 | `report_gen.py::_send_wecom_alert` |
| 新增点检标准 | `docs/inspection_standards.md` 表末尾追加 |
| 修改告警处置话术 | `analysis.py::ALERT_HINTS` |
| 修改报表格版 | `templates/daily_report.md` / `templates/alert_template.md` |

## 依赖
- Python 3.6+
- 标准库：json / argparse / os / datetime / random
- 第三方：openpyxl（Excel 台账，已随环境安装）

## 注意事项
- 演示模式（demo）注入的异常项用于演示完整告警链路，可在 `data_fetch.py::DEMO_ANOMALIES` 中调整或移除。
- 生产环境请务必接入真实数据源，切勿使用演示数据做实际判定。
- 点检标准阈值为企业典型参考值，正式使用前应由设备工程师结合厂商手册校准。