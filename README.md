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

## Git 使用

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

首次推送前，检查远端默认分支和已有提交。远端为空时可执行 `bash analysis/scripts/project_git.sh push -u origin main`；远端已有历史时先合并项目文件到对应历史，解决冲突，再正常推送。不要强制推送。上述脚本不自动提交、合并或推送。


hooks 会拒绝白名单外的文件、数据文件、凭据文件、符号链接和超过 25 MiB 的文件。pre-push 同时检查拟推送的新提交，避免仅从当前版本删除大型文件却仍将其历史上传。需要同步新的目录类型时，明确调整 `.gitignore` 和检查脚本中的规则。

首次配置时受限网络无法解析 `gitee.com`；随后通过获准的网络访问连接成功，确认远端仓库为空。若在受限环境中同步再次遇到 DNS 错误，需要使用获准的网络连接重试。
