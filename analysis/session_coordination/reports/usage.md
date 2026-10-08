# session 员工与共同任务

`chx_20260622` 是统一项目；员工各有独立普通 Git 克隆、分支和索引。一个任务可以登记多名员工，各自负责明确文件范围；成果通过提交汇合。登记数量没有固定上限，实际并发受模型、CPU、内存和磁盘约束。

## 开始工作

用户实际使用 Ubuntu 20.04 的 WSL 与 Codex CLI，习惯普通 `codex` 命令。Bash 的项目 source 函数已提供自动入口：新交互终端在本项目 `codex` 自动创建员工并进入其目录；同任务分组和已有员工恢复使用 `--chx-task`、`--chx-employee` 和 `--chx-scope`。详见 [WSL 普通命令接入](../../wsl_codex_entry/reports/usage.md)。下面的显式 Python 入口仍可用于管理或未加载该函数的 shell。

项目的 SessionStart hook 会按原生 session ID 自动分配员工目录，重复启动复用同一员工。它提供工作区路径和操作要求，不能改变已经打开的宿主 cwd 或沙箱。主目录打开的会话需对所有工具显式使用分配目录；要获得宿主对应的窄写权限，用下面的 CLI 入口，或在分配目录新开 App 聊天。hook 是否实际加载仍受宿主的信任检查控制，不修改信任数据库。

可在管理目录明确安排员工；`--scope` 可以是文件，也可以是带 `/` 的目录，计划文件也要纳入范围：

```bash
python3 analysis/scripts/session_coordinator.py create --task spectrum --employee fit --scope analysis/spectrum/fit/ --scope analysis/plans/2026-10-08-spectrum-fit.md
python3 analysis/scripts/session_coordinator.py launch --employee fit
```

另一个员工可使用相同 `--task spectrum`，不同 `--employee` 与不重叠范围。已经自动分配的员工在尚未编辑时可用 `assign --employee <id> --task spectrum --scope <path>` 安排到共同任务。子代理可能共用父 session ID；需要独立员工时显式创建另一目录，不能把子代理 ID 当作真实权限证明。

CLI 启动器在员工目录运行 `codex -C <workspace> --sandbox workspace-write`，不追加主目录或其他员工目录的写权限；同时控制端父进程收集 outbox。相同员工的两个受管理启动器会争用运行锁，第二个明确报忙，不会同时启动两个写入者。App 手动开在员工目录时，在管理 session 执行 `collect` 收集成果。

克隆只包含已提交源码和小型结果，不复制主目录的未提交编辑、原始/中间数据或凭据。忽略的 OMX dist/node_modules 直接使用主安装绝对路径，员工配置和 runtime 不创建符号链接，也不复制整套依赖；状态、缓存和 cwd 留在员工目录。生成的 `.codex/config.toml`、`.codex/hooks.json` 属于本地启动配置，员工不将它们提交；这些配置的规范维护在管理目录进行。

## 提交与汇合

员工先按项目约定保存计划、程序、实际验证 JSON，再在自己的目录提交：

```bash
python3 analysis/scripts/project_sync.py sync --task "能谱拟合" --message "Fit the measured spectrum" --result "<真实成果>" --evidence analysis/spectrum/fit/reports/verification.json --check "python3 analysis/spectrum/fit/verify.py"
```

`awaiting_collection` 表示本地提交和证据已冻结，尚未推送。员工不能通过项目 Git 入口直接 push。每名员工最多保留一份待整合请求；可继续编辑，但先收集前一份成果再提交下一份，避免顺序混淆。App 工作流的管理 session 使用：

```bash
python3 analysis/scripts/session_coordinator.py collect --employee fit
python3 analysis/scripts/session_coordinator.py status
```

控制端重新核对登记范围、基线、完整提交树、文件大小、模式和证据摘要。每次整合都有独立目录；项目锁覆盖读取远端、合并、重新验证、可信对象检查、提交、标签、正常推送和远端核对。合并后的真实检查结果重新写入交付证据，不沿用员工旧 JSON 证明最终 tree。

验收使用系统已安装的 bubblewrap：主文件系统只读，只开放候选源码目录写入，Git 与协调元数据另设只读，网络/PID 等命名空间隔离。控制端使用其可信 Git wrapper、policy 和标签程序，不执行候选中可变的 hooks。无 bubblewrap 或宿主禁止创建相应命名空间时保留 `needs_retry`，不使用扩大权限的无沙箱回退。当前 App 工具的外层沙箱会禁止该 namespace 操作，控制端执行需要真实宿主审批；普通终端中也以实际返回值判断可用性。

交付成功后自动尝试安全快进主目录与员工目录。用户正在修改记录本或同一文件时保留原文，不 stash、回滚或强行覆盖；主目录刷新未完成写 `root_refresh_pending`，与员工成果是否已推送分开记账。

## 冲突、交接与恢复

内容冲突写为 `conflict` 并保留原员工提交和本次整合目录；释放项目锁后其他任务照常交付。在管理 session 让冲突员工引入最新项目历史：

```bash
python3 analysis/scripts/session_coordinator.py resolve --employee fit
```

员工在自己的目录解决返回的冲突文件，完成合并提交，重新运行检查，再提交新的 outbox。原始冲突记录和快照保留。若只是网络、审批或资源暂时失败，使用 `integrate --submission <id>` 恢复；恢复先核对远端是否已经收到准确提交与标签，避免推送成功后记录中断造成重复提交。

同任务文件交接先由原员工提交/交付并保持目录干净，再在管理 session `release --employee <id> --path <原范围>`；新员工使用 `create` 或 `assign` 取得该范围。不会因为等待超过某个租约时间而偷走仍在工作的范围。锁文件不删除后重建，进程退出或异常被杀时由系统释放 flock。

`update --workspace <员工目录>` 只更新干净且不存在未交付提交的工作区；不能把尚未交付的员工 HEAD 改成新基线。Stop 只检查当前员工，已冻结待收集或有恢复状态时给出提示；其他员工和主目录实时记录本的修改不会让它重复续作。

## 数据与管理边界

读取 `/home/ys/data_401/data/Ge`、`CsI`，以及主项目已有大型输入时使用明确绝对只读路径。员工的独立项目根目录内仍按 `decode_data/`、`processed_data/` 等专用子目录输出大型数据，任务代码、小表和 SVG 仍集中于 `analysis/<task>/`。这些数据不提交；员工目录不自动删除，需将数据长期汇入主目录时另按明确输出范围处理，不通过共享数据目录符号链接开放主目录写权限。

管理 session 的约定维护和记录本例行保存使用原有同步程序，加 `--files <明确文件列表>`。它拒绝其他任务的暂存内容；主目录 `.project-git` 入口没有文件清单会明确拒绝，不再把整个脏工作区一起收集。

已打开的旧 session、直接写主目录的手工程序和绕过入口的编辑器不因此获得自动硬隔离。App 官方 Worktree/Hand off 是另一种可用的宿主迁移方式，但现有员工登记、scope/outbox 工作流要求使用本协调器返回的普通克隆；不能把未登记的任意 worktree 当作已经接入员工交付。
