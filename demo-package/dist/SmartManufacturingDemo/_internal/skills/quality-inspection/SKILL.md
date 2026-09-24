---
name: quality-inspection
description: 质量巡检。对工厂各产线/设备的质检指标（漏检率、误检率、合格率、CPK）进行日常巡检、质量告警与改进建议生成。当用户说"质量巡检""检查产品质量""质检报告"时使用。基于江苏 8 家智能制造企业调研日志中的质检痛点场景预置巡检标准。
---

# 质量巡检 Skill

## 用途
对工厂各产线/设备的质检指标进行日常巡检、质量异常告警和工艺改进建议生成。

## 触发条件
- 用户说"质量巡检"、"检查产品质量"、"质检"
- 每日/每班定时任务触发
- 质检数据异常（漏检率上升、合格率下降）时触发

## 目录结构
```
/skills/quality-inspection/
├── SKILL.md              # 本说明文件
├── scripts/
│   ├── data_fetch.py     # 数据采集脚本（demo/MCP 两种数据源）
│   ├── analysis.py       # 分析算法（阈值判定 正常/预警/严重/紧急）
│   └── report_gen.py     # 报告生成（日报、告警文件、Excel 质量台账）
├── templates/
│   ├── daily_report.md   # 质量巡检日报模板
│   └── alert_template.md # 质量告警模板
└── docs/
    └── inspection_standards.md  # 质量巡检标准知识库（判定依据）
```

## 操作流程
1. 调用质检数据 MCP 拉取最近 24 小时质检数据（当前以 `data_fetch.py --source demo` 模拟；接入真实数据后切换 `--source mcp`，在 `_fetch_from_mcp` 中实现）
2. 加载质量巡检标准知识库 `docs/inspection_standards.md`
3. 对比质检数据与标准阈值（`analysis.py` 判定）
4. 生成质量巡检日报（正常/预警/严重/紧急）（`report_gen.py`）
5. 如有异常，通过企业微信 MCP 发送质量告警（当前为占位接口 `_send_wecom_alert`）
6. 保存报告并同步到 Excel 质量台账（`output/quality_ledger.xlsx`）

## 快速运行
```bash
cd skills/quality-inspection
python scripts/data_fetch.py
python scripts/analysis.py
python scripts/report_gen.py
```
执行产出：
- `output/analysis_result.json` —— 分析结果
- `output/quality_report_YYYYMMDD.md` —— 质量巡检日报
- `output/quality_alert_<等级>_<时间>.md` —— 质量告警文件
- `output/quality_ledger.xlsx` —— Excel 质量台账

## 关键参数
| 参数 | 说明 | 取值示例 |
| --- | --- | --- |
| 巡检对象范围 | 全部 / 指定产线 / 指定设备 | `--devices TJ-01,BJ-01`（默认全部） |
| 时间范围 | 日报 / 周报 / 月报 | `--hours 24/168/720`（默认24h） |
| 告警等级 | 预警（轻微）/ 严重 / 紧急 | analysis.py 自动判定 |

## 标准库覆盖的质检场景（对应 8 家企业调研痛点）
| 企业 | 覆盖产线 | 关键质检指标 |
| --- | --- | --- |
| 天钧精密 | 电池箱体弧焊产线 | 焊缝缺陷漏检率、一次通过率、抽检合格率 |
| 贝斯特精机 | 五轴加工中心、高精度珩磨机 | 关键尺寸 CPK、粗糙度、网纹合格率 |
| 禾派阁 | 通用机器视觉检测线 | 误检率、漏检率、检出率 |
| 聚晟视 | AI 视觉检测设备 | 准确率、误检率、漏检率 |
| 樵弋机器人 | UTG AOI、自动收片装置 | 崩边漏检率、误报率、缺陷分类准确率 |
| 赫伽力 | 纺织上纱AGV、复合移动机器人 | 上纱定位合格率、落纱合格率、差错率 |
| 国投融合 | DTiip 边缘网关 | 数据采集完整率、校验通过率 |
| 富强科技 | 非标装配自动化产线 | 一次装配合格率、扭矩合格率、工装定位精度 |

## 告警等级定义
| 等级 | 处置要求 |
| --- | --- |
| 预警 | 48小时内复核质量趋势，持续越界组织 QC 分析与工艺排查 |
| 严重 | 当班隔离批次，暂停该线放行，通知 QC 主管并排查根因 |
| 紧急 | 立即停线扣留相关批次，启动质量事故响应 |

## 扩展点
| 扩展项 | 位置 |
| --- | --- |
| 对接真实质检数据 MCP | `data_fetch.py::_fetch_from_mcp` |
| 对接企业微信 MCP 发送告警 | `report_gen.py::_send_wecom_alert` |
| 新增质量巡检标准 | `docs/inspection_standards.md` 表末尾追加 |
| 修改告警处置话术 | `analysis.py::ALERT_HINTS` |

## 依赖
- Python 3.6+，标准库；openpyxl（Excel 台账，已安装）
- 阈值参考企业调研资料与行业通用标准，正式使用前应由质量工程师校准