# 任务执行计划：WSL 普通 codex 命令接入员工隔离

- 创建日期：2026-10-08
- 状态：已完成；入口代码、真实回归和安装记录已正常提交推送并核对远端
- 用户授权记录：用户补充实际使用环境为 Ubuntu 20.04 的 WSL、Codex CLI，习惯直接用 `codex` 启动。本任务沿用此前明确要求完善每个 session 的员工并行设计，适配该现有使用方式；项目代码/配置完成验证后按持续授权提交推送。个人 Bash 配置写入只通过宿主真实审批，不变更系统 Codex 可执行文件、信任数据库或登录。

## 目标与范围

在 chx 项目中直接输入 `codex`，启动前先创建/选择独立员工工作区，再调用真实 CLI，收集成果。保留普通提示词、模型等参数；项目之外照常转交原始命令。只读帮助/版本等操作不创建员工。会扩大写范围的参数不能静默绕过隔离；恢复旧会话需要明确已有员工，不能伪称旧 cwd 自动迁移。

## 输入与依据

- 已实现 `session_coordinator.py`、18 组真实并发/沙箱回归、官方 CLI 与 hook 实际抓取资料。
- 实际只读核对：Bash，WSL2 内核，`/usr/bin/codex` 可发现；`/home/ys/.bashrc` 为普通文件，交互 shell 加载，无现有 codex 定义；根工作区只有用户实时记录本编辑。
- 原始 Ge/CsI、他人 software、现有用户记录本保持原样；不启动付费模型任务来验证命令分派。

## 预计文件与用途

| 路径 | 操作 | 用途 |
| --- | --- | --- |
| `analysis/scripts/codex_entry.py` | 新建 | 项目命令分派与幂等 Bash 接入安装 |
| `analysis/scripts/codex_shell.sh` | 新建 | Bash 中保留 `codex` 命令名，传递原始 argv 与真实二进制 |
| `analysis/scripts/session_coordinator.py` | 小幅修改 | 复用已验证 launcher，支持原生 argv 和显式可执行路径；不重复实现收集循环 |
| `analysis/wsl_codex_entry/test_entry.py` | 新建 | 假 CLI 真实子进程、argv/cwd、外部目录与参数边界验证；小型临时 Git 仓库 |
| `analysis/wsl_codex_entry/reports/` | 新建 | 实际测试、安装结果与使用说明 |
| `README.md`、`analysis/session_coordination/reports/usage.md`、本计划 | 更新 | 直接 codex 的工作方式、分组/恢复和明确限制 |
| `/home/ys/.bashrc` 及同文件系统的私有备份目录 | 宿主审批后追加一段并保留原文 | source 本项目版本化函数；备份0700目录/0600文件，位置记在本地忽略元数据，私人原文不提交 |

## 方法与执行

统计和绘图不适用：本任务为 CLI/Bash 接入与命令分派。

1. 保存计划后实现显式程序与最小真实进程测试；普通 CLI 转发不经 shell 拼接，隔离目录仍由既有 coordinator 创建。
2. 运行 `python3 analysis/wsl_codex_entry/test_entry.py`，验证两次普通启动进入不同目录、外部项目原样转发、已登记员工复用与防双启动、模型/提示参数、帮助版本不注册、危险写范围参数拒绝、安装幂等和 Bash 语法。只使用 /tmp 一次性仓库与假 CLI，不伪称实际模型会话已验证。
3. 因 launcher 程序变化重新运行既有 18 组真实并发/沙箱验收及 Git 同步回归；更新本轮证据，不能用旧指纹证明新程序。
4. 通过真实宿主审批将项目 source 段追加到用户 `.bashrc`，只读核对标记与 Bash 语法。在新交互 Bash 验证函数加载/帮助或版本，不启动模型、不改保护目录权限。
5. 使用明确文件清单按 task-tag 提交推送本次文件，保留实时记录本编辑；核对真实远端与准确标签。

## 验证与完成标准

- 在 Bash 交互 shell 的 `codex` 函数实际调用新入口；项目内编辑型新会话物理独立，项目外和只读 CLI 操作原样转发。
- 子进程 argv、cwd 和 workspace-write 选择实际可检查；拒绝绕过沙箱、额外写目录或重定位到主目录的参数，不改变宿主强制权限。
- Bash 原内容保留，安装可重复，不覆盖其他用户定义；真实审批失败时说明影响，不伪称已接入。
- 新接入及原并行机制都通过实际回归；模型登录、真实付费会话与每次 hook 信任加载仍如实区分。

## 进度与恢复记录

- 已完成：显式程序、普通命令路由、元 argv 转发、八组真实 Bash/子进程回归、变化后的18组并发/Git/bubblewrap和现有同步回归。`python3 analysis/wsl_codex_entry/verify.py` 实际退出 0；源码在整段验证期间保持稳定，结果保存 `reports/verification.json`。更新既有回归指纹，不拿旧证据证明新 launcher。
- 关键决策：只在项目范围路由 `codex`，复用现有 launcher；不替换系统命令，不把 shell 函数当作额外写权限。
- 安装结果：`python3 analysis/scripts/codex_entry.py --install-shell --bashrc /home/ys/.bashrc` 经真实宿主审批退出 0；原 Bash 内容保留，备份0600，唯一source标记。实际新交互 Bash 返回 codex=function，真实 `codex --version` 为0.161.0并退出0，安装核对见 `reports/installation.json`；未调用付费模型、改登录或信任。
- 安装核对修正：早期备份落在数据盘，chmod成功返回却不保留权限，实际核对连续发现0644。改为 Bash 原文件同文件系统的私有目录并核对0700/0600；旧的本任务生成副本只在新备份验证后清理。没有改变保护目录权限，不能把核对失败或仅chmod返回成功当作通过。最终安装记录如实保存此限制和迁移结果。
- 独立审查：code-reviewer APPROVE、architect CLEAR。修复输出路径、嵌套恢复、原生选项解析、非本地命令误路由、配置绕过和备份权限问题；确切边界记录在 `reports/review.md` 和 `usage.md`。当前已开的 Bash 需重新加载配置，新终端自动source；旧模型会话不自动迁移。
- 最终核对：私有备份迁移实际经审批退出0；个人Bash原4052字节逐字保留，source标记唯一，真实0700/0600，`reports/installation.json` passed。最后稳定源码 `verify.py` 全部检查退出0，备份修正复审 APPROVE。后续仅交付记录，不改变程序或冒充付费模型测试。
- 当前阻碍：无本次实现阻碍；真实模型与每次hook宿主加载未声称验收，namespace权限仍按实际宿主判断。
- 实际交付：16个明确本次文件正常提交推送，准确标签 `chx6-WSL普通命令并行`；现有同步程序实际核对真实远端并退出0，本地收据为pushed。本计划完成记录随后按同一稳定源码和已通过证据单独同步，不冒充重复测试。
- 完成边界：个人Bash原文/私有备份/运行注册不提交；实时记录本编辑原样保留，本次索引无暂存内容。新交互终端在项目里仍输入 `codex`；已有Bash进程需读取更新配置，旧Codex会话不自动迁移。
- 下一步：正常使用项目命令入口；无本次未完成实现。恢复员工使用明确ID，冲突/权限仍按既有实际控制端恢复，不能把shell函数作为新增授权。
