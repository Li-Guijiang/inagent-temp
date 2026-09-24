# 命题188 智能制造比赛演示包

面向江苏智能制造企业的产业级 AI 智能体体系（五大技能包 + 四大 Agent 操作工控制台）。

## 一、仓库结构

| 路径 | 类型 | 说明 |
| --- | --- | --- |
| `demo-package/` | 源码与构建产物 | 演示程序工程。含 `main.py` 控制台入口、五个技能包、四个 Agent、PyInstaller 构建产物与 Inno Setup 打包脚本 |
| `agent-project/` | 智能体工程 | 智能体工作目录。含 `.inagent` 配置、9 个企业调研类技能、打包脚本 `pack_demo.py` 与运行数据 |
| `research-logs/` | 调研素材 | 8 篇江苏智能制造企业调研日志与 1 篇汇总总览 |
| `SmartManufacturingDemo-Setup.exe` | 交付物 | Windows 单文件安装包，由 Inno Setup 生成 |
| `命题188智能制造比赛演示包.zip` | 交付物 | 演示包压缩归档 |

### 1.1 demo-package 内部结构

```text
demo-package/
├── main.py                    控制台入口（Python 标准库 HTTP 服务）
├── run_demo.bat               一键启动：流水线 + 控制台 + 验证 + 浏览器
├── build_windows.bat          PyInstaller 构建脚本
├── build_installer.bat        Inno Setup 打包脚本
├── installer.iss              安装器源码
├── config.example.json        配置示例
├── pyproject.toml             工程配置
├── requirements.txt           依赖清单（openpyxl）
├── dist/                      已构建的 onedir 免安装程序
├── installer-output/          安装包输出目录（当前为空）
├── skills/                    五个技能包与操作工控制台
└── tests/                     核心 API 回归测试
```

### 1.2 agent-project 内部结构

```text
agent-project/
├── .inagent/                  智能体配置与技能定义
├── skills/                    五个技能包（含 SKILL.md）
├── pack_demo.py               演示包打包脚本
└── 比赛演示包/                 可独立拷贝运行的演示包与运行数据
```

## 二、运行方式

### 2.1 安装版（推荐现场演示）

1. 双击 `SmartManufacturingDemo-Setup.exe` 完成安装。
2. 双击桌面快捷方式启动，浏览器自动打开演示界面。
3. 质检上报、综合报表与诊断日志写入 `%LOCALAPPDATA%\SmartManufacturingDemo\`，卸载程序不删除该目录。

### 2.2 免安装版

1. 进入 `demo-package/dist/SmartManufacturingDemo/`。
2. 双击 `SmartManufacturingDemo.exe` 启动。

### 2.3 源码方式

```bat
cd demo-package
python -m pip install -r requirements.txt
python main.py
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--port 8848` | 指定本地端口 |
| `--no-browser` | 不自动打开浏览器 |
| `--skip-pipelines` | 跳过技能包流水线，直接使用已有产物 |
| `--data-dir runtime-data` | 质检上报与新报表的可写目录 |
| `--log-file runtime-data\console.log` | 指定日志路径 |

服务地址为 `http://127.0.0.1:8848`，健康检查为 `/api/health`，停止服务按 `Ctrl+C`。

### 2.4 演示包一键启动

```bat
cd agent-project\比赛演示包
run_demo.bat
```

脚本依次执行五个技能包流水线、启动控制台服务、校验四大 Agent、打开浏览器界面。

## 三、核心文档索引

| 文档 | 位置 |
| --- | --- |
| 比赛演示说明文档 | `demo-package/比赛演示说明文档.md` |
| 现场演示操作手册 | `agent-project/比赛演示包/现场演示操作手册.md` |
| 演示程序说明 | `demo-package/README.md` |
| 命题188 作业说明 | `agent-project/skills/命题188智能制造作业说明.md` |
| 江苏区域产业痛点调研报告 | `demo-package/江苏区域产业痛点调研报告.md` |
| 系统整体架构设计图 | `demo-package/系统整体架构设计图.md` |
| 降本增效量化指标表 | `demo-package/降低增数量化指标表.md` |
| OPC 商业化落地实施方案 | `demo-package/OPC商业化落地实施方案.md` |
| inAgent 能力证明链 | `demo-package/inAgent能力证明链.md` |

## 四、四大 Agent

| 编号 | 名称 | 入口 | 数据来源 |
| --- | --- | --- | --- |
| A1 | 智能质检 Agent | 质检上报 | quality-inspection 技能包 |
| A2 | 工艺知识 Agent | 工艺解析 | 内置工艺知识提取引擎 |
| A3 | 产线数据 Agent | 生产报表 | 五个技能包汇总 |
| A4 | 设备运维 Agent | 设备告警 | equipment-inspection 技能包 |

能耗分析、质量追溯两个技能包的数据汇入 A3 生产报表，能耗看板作为车间看板保留在首页。

## 五、说明

1. 演示数据使用固定随机种子（seed=42），可随时复现，保障现场演示稳定性。
2. 以下路径未纳入版本管理：`demo-package/installer-output/`（空目录）、`__pycache__`、`*.pyc`。
3. `demo-package/dist/` 与 `demo-package/tests/runtime-data/` 由工程内 `.gitignore` 声明为忽略项，本仓库为完整交付需要已强制纳入跟踪。
4. 所有源码、JSON 与 Markdown 文件编码均为 UTF-8。
