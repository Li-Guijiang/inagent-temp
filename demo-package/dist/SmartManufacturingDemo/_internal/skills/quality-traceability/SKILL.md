---
name: quality-traceability
description: 质量追溯。对工厂追溯体系指标（批次追溯覆盖率、序列码赋码率、数据关联率、数据归档及时率、工单批次锁定率）进行分析、追溯断链告警与体系改进建议生成。当用户说"质量追溯""产品溯源""追溯断链"时使用。基于江苏 8 家智能制造企业调研日志中的追溯与数据孤岛痛点预置分析标准。
---

# 质量追溯 Skill

## 用途
对工厂追溯体系各环节的追溯指标进行日常分析、追溯断链告警与溯源体系改进建议生成。

## 触发条件
- 用户说"质量追溯"、"产品溯源"、"追溯分析"
- 每日/批/月度定时任务触发
- 追溯指标异常（覆盖率下降、归档及时率不足、数据断链）时触发

## 目录结构
```
/skills/quality-traceability/
├── SKILL.md              # 本说明文件
├── scripts/
│   ├── data_fetch.py     # 数据采集脚本（demo/MCP 两种数据源）
│   ├── analysis.py       # 分析算法（阈值判定 正常/预警/严重/紧急）
│   └── report_gen.py     # 报告生成（日报、告警文件、Excel 追溯台账）
├── templates/
│   ├── daily_report.md   # 质量追溯日报模板
│   └── alert_template.md # 追溯告警模板
└── docs/
    └── inspection_standards.md  # 质量追溯标准知识库（判定依据）
```

## 操作流程
1. 调用追溯系统/MES MCP 拉取追溯指标数据（当前以 `data_fetch.py --source demo` 模拟；接入真实数据后切换 `--source mcp`，在 `_fetch_from_mcp` 中实现）
2. 加载追溯标准知识库 `docs/inspection_standards.md`
3. 对比追溯指标与标准阈值（`analysis.py` 判定）
4. 生成质量追溯日报（正常/预警/严重/紧急）（`report_gen.py`）
5. 如有异常，通过企业微信 MCP 发送追溯告警（当前为占位接口 `_send_wecom_alert`）
6. 保存报告并同步到 Excel 追溯台账（`output/traceability_ledger.xlsx`）

## 快速运行
```bash
cd skills/quality-traceability
python scripts/data_fetch.py
python scripts/analysis.py
python scripts/report_gen.py
```
执行产出：
- `output/analysis_result.json` —— 分析结果
- `output/traceability_report_YYYYMMDD.md` —— 质量追溯日报
- `output/traceability_alert_<等级>_<时间>.md` —— 追溯告警文件
- `output/traceability_ledger.xlsx` —— Excel 追溯台账

## 关键参数
| 参数 | 说明 | 取值示例 |
| --- | --- | --- |
| 分析对象范围 | 全部 / 指定环节/平台 | `--devices GT-01,TJ-01`（默认全部） |
| 时间范围 | 日报 / 周报 / 月报 | `--hours 24/168/720`（默认24h） |
| 告警等级 | 预警（轻微）/ 严重 / 紧急 | analysis.py 自动判定 |

## 标准库覆盖的追溯场景（对应 8 家企业调研痛点与"全程可溯"要求）
| 企业 | 覆盖环节 | 关键追溯指标 |
| --- | --- | --- |
| 国投融合 | DTiip 工业互联网平台 | 批次追溯覆盖率、数据归档及时率、链路完整性 |
| 天钧精密 | 电池箱体弧焊产线 | 批次-成品绑定率、序列码赋码率、热处理记录关联率 |
| 贝斯特精机 | 五轴加工中心、高精度珩磨机 | 序列号追溯覆盖率、原材料批次关联率、参数存档完整率 |
| 禾派阁 | 通用机器视觉检测线 | 检测结果入库率、缺陷图像关联率 |
| 聚晟视 | AI 视觉检测设备 | 检测工单追溯完整率、模型判定记录留存率 |
| 樵弋机器人 | UTG AOI 检测设备 | 玻璃批次-缺陷数据关联率、检测报告生成及时率 |
| 赫伽力 | 纺织上纱AGV、复合移动机器人 | 上纱工序记录完整率、装配记录追溯完整率 |
| 富强科技 | 非标装配自动化产线 | 工单-批次锁定率、装配日志留存完整率 |

## 告警等级定义
| 等级 | 处置要求 |
| --- | --- |
| 预警 | 48小时内核查数据链路，补充缺失记录，防止追溯断链扩大化 |
| 严重 | 当班排查断链点，核实受影响批次范围，必要时通知客户质量部 |
| 紧急 | 立即冻结受影响批次销售发运，启动全面追溯核查，排除召回风险 |

## 扩展点
| 扩展项 | 位置 |
| --- | --- |
| 对接真实追溯系统/MES MCP | `data_fetch.py::_fetch_from_mcp` |
| 对接企业微信 MCP 发送告警 | `report_gen.py::_send_wecom_alert` |
| 新增追溯指标标准 | `docs/inspection_standards.md` 表末尾追加 |
| 修改告警处置话术 | `analysis.py::ALERT_HINTS` |

## 依赖
- Python 3.6+，标准库；openpyxl（Excel 台账，已安装）
- 追溯目标为企业调研资料与行业通用的"全程可溯"要求，正式使用前应由质量/IT 工程师结合体系文件校准