# 任务执行计划：多 session 并发保护核查

- 创建日期：2026-10-08
- 状态：核查与隔离验证已完成；核查记录按既有授权进行版本交付
- 用户授权记录：用户询问当前并行设计是否完成、能否避免同时修改同一文件导致 session 任务受阻；本次只读核查设计和隔离验证，不修改生产协调、hooks、技能或他人的工作文件。报告与验证记录按既有持续授权同步。

## 目标与范围

核实共享文件修改、Git 索引及分支、交付状态文件、远端推送和 Stop hook 的保护范围，回答是否已经具备可靠的跨 session 防撞机制。区分同一 session 内分工、OMX Team 内协调和多个独立 session 共享项目。给出有证据的缺口与最小改进建议，不把建议写成已实现功能。

## 输入与依据

只读输入为 `AGENTS.md`、`.codex/hooks.json`、`analysis/scripts/project_git.sh`、`project_sync.py`、`task_delivery.py`、相关验证程序及已安装 OMX 的 hook/session/锁实现。原始实验数据不涉及；实时记录本只检查 Git 状态，不改写或专项核实。

## 预计建立或修改的文件

| 项目内路径 | 操作 | 用途 |
| --- | --- | --- |
| `analysis/plans/2026-10-08-session-concurrency-audit.md` | 新建 | 范围、授权、进度与真实结果 |
| `analysis/session_concurrency/audit.py` | 新建 | 显式保存检查与临时仓库复现，不调用真实 push 或生产 hook |
| `analysis/session_concurrency/reports/verification.json` | 新建 | 真实检查结果，区分预期风险与程序检查通过 |
| `analysis/session_concurrency/reports/diagnosis.md` | 新建 | 并发保护范围、实际风险、证据与未核实事项 |

## 方法与统计处理

统计与绘图不适用：本任务检查程序控制流和并发边界，不计算实验结果。静态追踪实际写入路径和锁范围；若需复现，仅在 `/tmp` 内新建的微型仓库或目录测试。没有观察到数据损失时不声称已经丢失数据。

## 执行步骤

1. 计划落盘后，主代理检查项目 Git 与交付脚本；原生 `explore` 子代理只读核查已安装 OMX 的 session 状态锁是否覆盖实际源文件、Git 交付及独立 session。
2. 保存 `analysis/session_concurrency/audit.py`，再运行 `python3 analysis/session_concurrency/audit.py`。优先复用实际 `project_sync.py` 函数，在隔离微型仓库验证候选文件集合和 Stop 判断是否区分 session；不在真实项目重放竞争写入。
3. 保存报告，标明直接证据、推断、保护局限和建议；只有实际存在并经验证的保护才报告为已完成。
4. 检查本任务文件范围、差异、大小及真实远端历史；按 task-tag 同步本任务记录。生产工作区存在其他实时改动时，从已提交历史在 `/tmp/chx-concurrency-audit.*/checkout/` 建立隔离克隆，只复制上表四个文件；在克隆中运行现有 `project_sync.py sync --task "并发保护核查" --message "Audit independent session coordination boundaries" --result "完成多session并发保护核查，隔离复现四项现有边界，未改生产机制" --basis "用户并发问题、项目同步源码与实际隔离复现" --evidence analysis/session_concurrency/reports/verification.json`。核对远端后只快进本地分支和更新本任务文件索引，保留实时记录本。此为本次记录的交付方式，不报告成生产防撞机制已实现。

## 预计结果与验证标准

- 得到是否具备跨 session 文件保护的明确答案，以及源文件、Git/远端、交付收据、Stop 检查各层的能力边界。
- 交付显式检查程序、验证 JSON 和报告；生产脚本、记录本、权限及全局配置不变。
- 检查通过表示风险判断被源码或隔离复现支持，不表示已修复并发问题。
- 如无法安全同步或无法证明某项保护，说明真实限制；不强推或丢弃别的 session 改动。

## 风险与待确认事项

多 session 的全局文件锁或独立 worktree 尚未核实。不能用 session ID、本地计划文字或记录代替真实写权限/所有权；应用层隔离建议也不能承诺阻止所有手工文件写入。本次不扩大为防撞机制实施。

## 进度与恢复记录

- 已完成：必要只读检查、analyze/evolution 技能读取、计划保存、源码追踪和显式程序运行。`python3 analysis/session_concurrency/audit.py` 退出 0，四项隔离复现通过；报告已保存。
- 关键决策：采用 analyze 只读分析；报告应用已读取的 Ponytail/说人话，交付应用 task-tag。原生代理核查与主代理范围分离。
- 结果位置：`analysis/session_concurrency/reports/`。
- 原生代理结果：`explore` 只读核查实际 PreToolUse dist/source 与 OMX session/Team 锁。当前 PreToolUse 为 advisory-only；已有锁覆盖状态指针和任务记录，未覆盖独立 session 的任意源码编辑。未重放 hooks，不声称宿主实际执行每次 hook。
- 核查结论：跨独立 session 防撞设计尚未完成；候选文件和 Stop 不区分 session，共享 pending 可被后写覆盖，流程没有整段互斥。具体证据、推断和局限见 `reports/diagnosis.md`。
- 当前阻碍：分析无阻碍；本轮未获防撞机制实施指令，按用户询问范围交付现状核查与建议。
- 下一步：单独同步本次四个文件并核对真实远端，保留用户实时记录本；生产机制实施与跨 session 验收属于后续独立工作。
