# inAgent 能力证明链

本文件用于答辩时说明：本作品不是五个独立 Python 脚本，而是按 inAgent 的 **Skill / MCP / Agent / 定时批量调度** 能力组织的可运行闭环。

| inAgent 能力 | 本作品证据 | 现场演示方式 |
| --- | --- | --- |
| Skill 技能包 | `skills/*/SKILL.md`、`scripts/data_fetch.py`、`analysis.py`、`report_gen.py` | 打开任一技能包，展示标准、采集、分析、报告四段流水线 |
| Agent 专家协同 | A1 质检、A2 工艺、A3 产线、A4 设备四个控制台入口 | 打开 `http://127.0.0.1:8848`，按 A4→A1→A2→A3 演示 |
| MCP 连接器 | `skills/factory-console/app.py` 的本地数据服务端点与各技能包的统一数据结构 | 在终端调用 `/api/device`、`/api/quality`、`/api/energy`、`/api/process`、`/api/traceability`，展示返回 JSON |
| 批量调度 | `run_demo.bat` 按顺序运行五个技能包并执行 `verify_agents.py` | 双击脚本，展示五包流水线、控制台启动和四 Agent 验证结果 |
| 可审计产物 | 各技能包 `output/` 下的日报、分级告警和 `analysis_result.json` | 展示输入数据、告警结果、报告文件三类产物可以相互追溯 |

## 现场答辩口径

1. **Skill** 负责把行业标准固化为可复用能力；每个技能包均可独立运行。
2. **MCP** 负责把设备、质量、能耗、工艺、追溯数据以统一 JSON 合同提供给上层能力。
3. **Agent** 面向工厂操作工封装业务动作，不要求操作工理解脚本、模型或数据目录。
4. `run_demo.bat` 是可复现的批量调度入口，`verify_agents.py` 是自动化验收证据，不是人工口头承诺。

