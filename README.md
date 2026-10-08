# chx_20260622 数据分析项目

本目录存放项目工作文件和处理后的数据。原始数据读取自同级的 `Ge/`、`CsI/`；同级 `software/` 属于他人，保持不操作。

已安装项目内 Ponytail、中英文说人话、Nature 全量技能、Crawl4AI 全部 Python extras，以及 OMX 原生 CLI、角色、提示词和 hooks。详细版本、调用方式与恢复步骤见 [安装说明](analysis/third_party/INSTALL.md)。运行环境与浏览器保存在本地 `.runtime/`，源代码、完整技能和配置随仓库同步。

This product includes software developed by UncleCode (https://x.com/unclecode) as part of the Crawl4AI project (https://github.com/unclecode/crawl4ai).

| 路径 | 用途 | Git 同步 |
| --- | --- | --- |
| `../Ge/`、`../CsI/` | 只读原始数据 | 否 |
| `../software/` | 他人的分析目录，不作操作 | 否 |
| `decode_data/`、`processed_data/` 等 | 解码文件和处理产生的中间数据 | 数据不提交；`decode_data/DecodeAndSortAll/` 的指定官方源码及配置除外 |
| `analysis/<任务名>/` | 任务程序、小型数据表、`figures/` 和 `reports/` | 是，排除编译产物和大型数据 |
| `analysis/scripts/`、`analysis/plans/` | 通用项目工具、待确认或执行中的计划 | 是 |
| `AGENTS.md`、`README.md`、`.gitignore` | 项目约定及版本管理说明 | 是 |
| `.agents/skills/` | 项目技能维护源 | 是 |
| `.codex/skills/` | OMX 项目技能入口 | 是 |
| `.githooks/`、`.codex/` | Git hooks、项目配置（排除本地状态和凭据） | 是 |
| `.project-git/` | `.git` 不可写时的本地 Git 元数据 | 否 |

具体规则见 [AGENTS.md](AGENTS.md)，实验记录见 [analysis/experiment_log/record_analysis.md](analysis/experiment_log/record_analysis.md)。技能维护源为 `.agents/skills/`，OMX 入口为 `.codex/skills/`；根 `skills/` 冗余副本已清理。技能与 hooks 按任务自动触发，报告和代码都应用 Ponytail，报告再配合语言和科研技能。安装没有写入全局技能目录。

新任务先在 `analysis/plans/` 写计划，随后在明确任务范围内连续执行非危害操作，无需额外确认；原始数据与宿主权限边界继续适用。绘图统一使用 Python，保留可查看的程序和来源数据表，只保存 SVG，并实际查看最终渲染以检查重叠、裁切、缺字和数据关系。

新建文件和文件夹使用英文 ASCII 命名，计划采用 `YYYY-MM-DD-short-task-name.md`，内容可写中文。`analysis/experiment_log/record_analysis.md` 是用户实时编辑的记录本；保留其编辑，按既有授权例行同步，普通差异不另行展开审查或反复追问。

## Git 使用

并行任务先为每名员工建立独立目录；同一任务用相同 `--task`、不同 `--employee` 和文件范围：

WSL/Bash 提供普通命令入口；个人 `.bashrc` 启用项目 `codex_shell.sh` 后，新交互终端在本项目直接输入 `codex`，会在启动前创建独立员工目录并调用真实 CLI，不必每次输入 Python 命令。编译资源直接读取主安装绝对路径，不依赖数据盘符号链接。普通 `codex resume`、`fork` 保留原生历史、argv和cwd，不要求员工ID，也不声明旧会话自动隔离；明确恢复员工用 `codex --chx-employee <已有ID> resume --last`。多人同任务用 `--chx-task`、`--chx-employee`、`--chx-scope`。项目外、帮助和版本照常转发，管理模式的边界越界参数明确拒绝。用户关闭source时保留其选择；临时可用 `command codex` 绕过函数。详见 [WSL 命令说明](analysis/wsl_codex_entry/reports/usage.md)。

```bash
python3 analysis/scripts/session_coordinator.py create --task spectrum --employee fit --scope analysis/spectrum/fit/ --scope analysis/plans/2026-10-08-spectrum-fit.md
python3 analysis/scripts/session_coordinator.py launch --employee fit
```

CLI 启动器限定员工工作区，自动收集本地提交并串行整合；App 中在 create 返回的 `workspace` 新开 session，再从管理 session 执行 `session_coordinator.py collect --employee fit`。同文件合并冲突保留双方成果和独立恢复目录，其他任务继续交付；员工编号没有固定数量上限，实际并发仍受机器与宿主限制。完整交接、验收、数据位置和恢复方法见 [员工协作说明](analysis/session_coordination/reports/usage.md)。已打开的 App 会话不能靠 hook 自动切换 cwd/沙箱。

目标远端：`https://gitee.com/chx6/ns_analysis.git`。

通过 `bash analysis/scripts/project_git.sh` 调用，优先使用有效的 `.git` 仓库；`.git` 不可写时使用项目内的 `.project-git/`。它设置版本化 hooks，并将 Git 命令传给所选仓库。尚无仓库时先初始化本地 `main` 分支。数据盘可能不支持执行权限，脚本会在临时目录中复制并执行 hooks，命令结束后清理副本；在当前数据盘上使用此脚本执行 Git 操作。提交前需要设置真实的作者姓名和邮箱。

```bash
bash analysis/scripts/project_git.sh status --short
bash analysis/scripts/project_git.sh config user.name "你的姓名"
bash analysis/scripts/project_git.sh config user.email "你的邮箱"
bash analysis/scripts/project_git.sh add AGENTS.md README.md .gitignore .agents/skills .codex .githooks analysis decode_data/DecodeAndSortAll
bash analysis/scripts/project_git.sh diff --cached --stat
bash analysis/scripts/project_git.sh commit -m "Document analysis project conventions"
bash analysis/scripts/project_git.sh fetch origin
```

首次推送前，检查远端默认分支和已有提交。远端为空时可执行 `bash analysis/scripts/project_git.sh push -u origin main`；远端已有历史时先合并项目文件到对应历史，解决冲突，再正常推送。不要强制推送。低层 Git 入口只执行所给命令；任务完成后的自动交付使用下述流程。

用户已授权今后文件更改完成并验证后自动提交、推送到本项目 Gitee 仓库，包括代码、规范、技能、计划和小型结果。`task-tag` 技能自动执行；员工提交需附 `--check "<验收命令>"`，管理目录例行交付附 `--files <明确文件列表>`。Stop 只跟进当前员工，不因其他任务或实时记录本改动反复阻止管理 session。推送成功以真实远端核对为准，阻碍如实报告。

```bash
python3 analysis/scripts/project_sync.py sync --task "<简短中文任务>" --message "<Description>" --result "<真实成果>" --basis "<修改依据>" --evidence analysis/<task>/reports/<verification>.json
```

该程序复用版本化 hooks 和已验证交付标签，禁止数据／凭据／大文件进入提交，不强推。推送收据保存在本地忽略目录，避免保存收据本身再次触发提交。

标签供人阅读：例如 `chx6-启用验证后的自动提交与推送`。展开说明可看到修改者、执行协作、依据、改动、成果和验证结论；同名任务用短序号区分，名称／说明不填时间戳、提交编号或 SHA256。

hooks 会拒绝白名单外的文件、数据文件、凭据文件、符号链接和超过 25 MiB 的文件。pre-push 同时检查拟推送的新提交，避免仅从当前版本删除大型文件却仍将其历史上传。需要同步新的目录类型时，明确调整 `.gitignore` 和检查脚本中的规则。

首次配置时受限网络无法解析 `gitee.com`；随后通过获准的网络访问连接成功，确认远端仓库为空。若在受限环境中同步再次遇到 DNS 错误，需要使用获准的网络连接重试。
