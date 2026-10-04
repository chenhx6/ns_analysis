# chx_20260622 数据分析项目

本目录存放项目工作文件和处理后的数据。原始数据读取自同级的 `Ge/`、`CsI/`；同级 `software/` 属于他人，保持不操作。

| 路径 | 用途 | Git 同步 |
| --- | --- | --- |
| `../Ge/`、`../CsI/` | 只读原始数据 | 否 |
| `../software/` | 他人的分析目录，不作操作 | 否 |
| `decode_data/`、`processed_data/` 等 | 解码文件和处理产生的中间数据 | 否 |
| `analysis/` | 记录本、代码、配置、结果图及小型结果表 | 是，排除编译产物和大型数据 |
| `AGENTS.md`、`README.md`、`.gitignore` | 项目约定及版本管理说明 | 是 |
| `skills/`、`.agents/skills/` | 项目技能 | 是 |
| `.githooks/`、`.codex/` | Git hooks、项目配置（排除本地状态和凭据） | 是 |
| `.project-git/` | `.git` 不可写时的本地 Git 元数据 | 否 |

具体规则见 [AGENTS.md](AGENTS.md)，实验记录见 [analysis/record_analysis.md](analysis/record_analysis.md)。项目技能位于 [skills/chx-data-analysis/SKILL.md](skills/chx-data-analysis/SKILL.md)，在当前环境中由项目约定指引读取；这不等同于已安装到全局技能目录。

## Git 使用

目标远端：`https://gitee.com/chx6/ns_analysis.git`。

通过 `bash analysis/code/project_git.sh` 调用，优先使用有效的 `.git` 仓库；`.git` 不可写时使用项目内的 `.project-git/`。它设置版本化 hooks，并将 Git 命令传给所选仓库。尚无仓库时先初始化本地 `main` 分支。数据盘可能不支持执行权限，脚本会在临时目录中复制并执行 hooks，命令结束后清理副本；在当前数据盘上使用此脚本执行 Git 操作。提交前需要设置真实的作者姓名和邮箱。

```bash
bash analysis/code/project_git.sh status --short
bash analysis/code/project_git.sh config user.name "你的姓名"
bash analysis/code/project_git.sh config user.email "你的邮箱"
bash analysis/code/project_git.sh add AGENTS.md README.md .gitignore skills .githooks analysis
bash analysis/code/project_git.sh diff --cached --stat
bash analysis/code/project_git.sh commit -m "Document analysis project conventions"
bash analysis/code/project_git.sh fetch origin
```

首次推送前，检查远端默认分支和已有提交。远端为空时可执行 `bash analysis/code/project_git.sh push -u origin main`；远端已有历史时先合并项目文件到对应历史，解决冲突，再正常推送。不要强制推送。上述脚本不自动提交、合并或推送。

hooks 会拒绝白名单外的文件、数据文件、凭据文件、符号链接和超过 25 MiB 的文件。pre-push 同时检查拟推送的新提交，避免仅从当前版本删除大型文件却仍将其历史上传。需要同步新的目录类型时，明确调整 `.gitignore` 和检查脚本中的规则。

首次配置时受限网络无法解析 `gitee.com`；随后通过获准的网络访问连接成功，确认远端仓库为空。若在受限环境中同步再次遇到 DNS 错误，需要使用获准的网络连接重试。
