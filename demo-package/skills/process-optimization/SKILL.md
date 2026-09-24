---
name: process-optimization
description: 工艺优化。对工厂设备/工序的工艺参数（焊接电流、转速、节拍、磨损、算法参数）进行分析、工艺偏离告警与改进建议生成。当用户说"工艺优化""工艺参数分析""工艺改进"时使用。基于江苏 8 家智能制造企业调研日志中的工艺与创新痛点预置分析标准。
---

# 工艺优化 Skill

## 用途
对工厂各设备/工序的工艺参数进行日常分析、工艺偏离告警与工艺改进建议生成。

## 触发条件
- 用户说"工艺优化"、"工艺参数分析"、"工艺改进"
- 每日/批/月度定时任务触发
- 工艺参数偏离（电流、转速、节拍、磨损超限）时触发

## 目录结构
```
/skills/process-optimization/
├── SKILL.md              # 本说明文件
├── scripts/
│   ├── data_fetch.py     # 数据采集脚本（demo/MCP 两种数据源）
│   ├── analysis.py       # 分析算法（阈值判定 正常/预警/严重/紧急）
│   └── report_gen.py     # 报告生成（日报、告警文件、Excel 工艺台账）
├── templates/
│   ├── daily_report.md   # 工艺优化日报模板
│   └── alert_template.md # 工艺告警模板
└── docs/
    └── inspection_standards.md  # 工艺优化标准知识库（判定依据）
```

## 操作流程
1. 调用工艺数据 MCP/SCADA 拉取工艺参数数据（当前以 `data_fetch.py --source demo` 模拟；接入真实数据后切换 `--source mcp`，在 `_fetch_from_mcp` 中实现）
2. 加载工艺标准知识库 `docs/inspection_standards.md`
3. 对比工艺参数与标准窗口（`analysis.py` 判定）
4. 生成工艺优化日报（正常/预警/严重/紧急）（`report_gen.py`）
5. 如有异常，通过企业微信 MCP 发送工艺告警（当前为占位接口 `_send_wecom_alert`）
6. 保存报告并同步到 Excel 工艺台账（`output/process_ledger.xlsx`）

## 快速运行
```bash
cd skills/process-optimization
python scripts/data_fetch.py
python scripts/analysis.py
python scripts/report_gen.py
```
执行产出：
- `output/analysis_result.json` —— 分析结果
- `output/process_report_YYYYMMDD.md` —— 工艺优化日报
- `output/process_alert_<等级>_<时间>.md` —— 工艺告警文件
- `output/process_ledger.xlsx` —— Excel 工艺台账

## 关键参数
| 参数 | 说明 | 取值示例 |
| --- | --- | --- |
| 分析对象范围 | 全部 / 指定设备/工序 | `--devices TJ-01,FQ-01`（默认全部） |
| 时间范围 | 日报 / 周报 / 月报 | `--hours 24/168/720`（默认24h） |
| 告警等级 | 预警（轻微）/ 严重 / 紧急 | analysis.py 自动判定 |

## 标准库覆盖的工艺场景（对应 8 家企业调研痛点）
| 企业 | 覆盖设备/工序 | 关键工艺指标 |
| --- | --- | --- |
| 天钧精密 | 弧焊工作站、FSW专机 | 焊接电流/速度/热输入偏差、搅拌头转速、顶锻压力 |
| 贝斯特精机 | 五轴加工中心、高精度珩磨机 | 刀具/珩磨头磨损率、切削利用率、换刀频次、节拍 |
| 禾派阁 | 视觉检测线 | 检测节拍超时率、光源亮度衰减 |
| 聚晟视 | AI 视觉检测设备 | 模型推理延迟、误检迭代周期 |
| 樵弋机器人 | UTG AOI 设备 | 成像灰度均匀度、算法漏检率 |
| 赫伽力 | 上纱AGV、复合移动机器人 | 上纱节拍、对位成功率、协同调度延迟 |
| 富强科技 | 非标装配自动化产线 | 节拍达成率、工艺参数稳定率 |
| 国投融合 | DTiip 边缘网关 | 数据采集时延 |

## 告警等级定义
| 等级 | 处置要求 |
| --- | --- |
| 预警 | 48小时内复核工艺趋势，必要时校准工艺窗口或调整参数设定值 |
| 严重 | 当班校正工艺参数，暂停该工序放行，工艺工程师介入确认 |
| 紧急 | 立即停线，封锁相关批次，工艺与质量联合排查防止不合格品流出 |

## 扩展点
| 扩展项 | 位置 |
| --- | --- |
| 对接真实工艺数据 MCP | `data_fetch.py::_fetch_from_mcp` |
| 对接企业微信 MCP 发送告警 | `report_gen.py::_send_wecom_alert` |
| 新增工艺优化标准 | `docs/inspection_standards.md` 表末尾追加 |
| 修改告警处置话术 | `analysis.py::ALERT_HINTS` |

## 依赖
- Python 3.6+，标准库；openpyxl（Excel 台账，已安装）
- 工艺窗口为企业调研资料中的典型参考值，正式使用前应由工艺工程师结合技术规范校准