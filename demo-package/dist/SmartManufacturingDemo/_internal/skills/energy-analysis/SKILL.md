---
name: energy-analysis
description: 能耗分析。对工厂设备/产线的能耗指标（单位电耗、待机功耗、负载率、泄漏率、PUE）进行分析、能耗告警与节能建议生成。当用户说"能耗分析""能耗告警""节能分析"时使用。基于江苏 8 家智能制造企业调研日志中的设备与能耗场景预置分析标准。
---

# 能耗分析 Skill

## 用途
对工厂各设备/产线的能耗指标进行日常分析、能耗异常告警与节能降耗建议生成。

## 触发条件
- 用户说"能耗分析"、"节能分析"、"设备能耗"
- 每日/周/月定时任务触发
- 能耗数据异常（电耗突增、负载异常、泄漏率上升）时触发

## 目录结构
```
/skills/energy-analysis/
├── SKILL.md              # 本说明文件
├── scripts/
│   ├── data_fetch.py     # 数据采集脚本（demo/MCP 两种数据源）
│   ├── analysis.py       # 分析算法（阈值判定 正常/预警/严重/紧急）
│   └── report_gen.py     # 报告生成（日报、告警文件、Excel 能耗台账）
├── templates/
│   ├── daily_report.md   # 能耗分析日报模板
│   └── alert_template.md # 能耗告警模板
└── docs/
    └── inspection_standards.md  # 能耗分析标准知识库（判定依据）
```

## 操作流程
1. 调用能耗数据 MCP/能源管理系统拉取能耗数据（当前以 `data_fetch.py --source demo` 模拟；接入真实数据后切换 `--source mcp`，在 `_fetch_from_mcp` 中实现）
2. 加载能耗标准知识库 `docs/inspection_standards.md`
3. 对比能耗数据与标准阈值（`analysis.py` 判定）
4. 生能耗分析日报（正常/预警/严重/紧急）（`report_gen.py`）
5. 如有异常，通过企业微信 MCP 发送能耗告警（当前为占位接口 `_send_wecom_alert`）
6. 保存报告并同步到 Excel 能耗台账（`output/energy_ledger.xlsx`）

## 快速运行
```bash
cd skills/energy-analysis
python scripts/data_fetch.py
python scripts/analysis.py
python scripts/report_gen.py
```
执行产出：
- `output/analysis_result.json` —— 分析结果
- `output/energy_report_YYYYMMDD.md` —— 能耗分析日报
- `output/energy_alert_<等级>_<时间>.md` —— 能耗告警文件
- `output/energy_ledger.xlsx` —— Excel 能耗台账

## 关键参数
| 参数 | 说明 | 取值示例 |
| --- | --- | --- |
| 分析对象范围 | 全部 / 指定设备 | `--devices BJ-01,GT-01`（默认全部） |
| 时间范围 | 日报 / 周报 / 月报 | `--hours 24/168/720`（默认24h） |
| 告警等级 | 预警（轻微）/ 严重 / 紧急 | analysis.py 自动判定 |

## 标准库覆盖的能耗场景（对应 8 家企业调研痛点）
| 企业 | 覆盖设备 | 关键能耗指标 |
| --- | --- | --- |
| 天钧精密 | 弧焊工作站、FSW专机 | 单位件焊接能耗、压缩空气流量、主轴负载率 |
| 贝斯特精机 | 五轴加工中心、高精度珩磨机 | 单位件切削/珩磨电耗、待机功耗 |
| 禾派阁 | 通用机器视觉检测线 | 单线日耗电量、光源功率 |
| 聚晟视 | AI 视觉检测设备 | GPU 功耗、整机日耗电量 |
| 樵弋机器人 | UTG AOI、自动收片装置 | 单位片检测能耗、真空泵/伺服功耗 |
| 赫伽力 | 纺织上纱AGV、复合移动机器人 | 单班充电电量、驱动温升、充电效率 |
| 国投融合 | DTiip 边缘网关 | 机房 PUE、服务器 CPU 占用率 |
| 富强科技 | 非标装配自动化产线 | 单位产品装配能耗、气源系统泄漏率 |

## 告警等级定义
| 等级 | 处置要求 |
| --- | --- |
| 预警 | 48小时内复核能耗趋势，检查空转/待机，必要时调整排产 |
| 严重 | 当班开展专项能耗审计，锁定高能耗根因（负载、泄漏、温升） |
| 紧急 | 立即停机检查能耗急剧异常点，疑似故障/泄漏同步能源管理 |

## 扩展点
| 扩展项 | 位置 |
| --- | --- |
| 对接真实能耗数据 MCP | `data_fetch.py::_fetch_from_mcp` |
| 对接企业微信 MCP 发送告警 | `report_gen.py::_send_wecom_alert` |
| 新增能耗分析标准 | `docs/inspection_standards.md` 表末尾追加 |
| 修改告警处置话术 | `analysis.py::ALERT_HINTS` |

## 依赖
- Python 3.6+，标准库；openpyxl（Excel 台账，已安装）
- 能耗基线参考企业调研资料与行业通用水平，正式使用前应由能源工程师校准