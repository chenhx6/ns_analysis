---
name: go-on
description: 任务需续作或恢复检查点时自动，读取本项目的 OMX Ultragoal 检查点并继续既定任务。
---

# 继续任务

先读取项目 `AGENTS.md`、当前用户指令和 `.omx/ultragoal/` 下现有 brief、goals、ledger；普通任务读取 `analysis/` 中最近的任务记录及 Git 差异。保留既定目标、已完成的步骤和用户提出的暂停或取消决定。

已有 OMX 计划时读取相邻 `ultragoal/SKILL.md`，运行 `python3 analysis/scripts/project_runtime.py omx ultragoal status`，按原生 handoff 继续未完成的 story。`autopilot` 仍保持其原生阶段契约。没有计划时自动继续普通任务；需要创建目标时遵守宿主工具的明确授权要求。恢复过程中不把中断误记为完成，不启动已取消的任务。

此入口将 muIon-beam 的瞬态恢复意图适配到 OMX 当前的持久化机制；不安装 muIon 的 Desktop farmer 守护进程。
