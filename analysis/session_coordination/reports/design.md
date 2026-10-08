# 已实施的并行边界与依据

编辑隔离使用独立普通 Git 克隆；同一项目登记任务、员工与分配范围。源码不共享，交付按不可变请求串行汇合。相比在共享目录维护建议性文件锁，目录隔离直接避免员工写同一物理文件；相比共享 Git worktree，普通克隆也分离索引、refs、配置和交付状态，适配现有 `.project-git` 与脚本入口。

控制目录为主项目本地忽略的 `.omx/coordination/`；注册表短事务使用独立 flock 和原子替换，整合采用完整流程锁，员工提交/启动也各有锁。注册表没有固定员工上限；JSON 重写成本随员工数量增长，代码标明频繁更新数千员工时可换标准库 SQLite，当前不增加服务、外部数据库或其他编排框架。

员工只写自己的源码、Git 元数据和 outbox；控制端从登记信息核对真实目录和冻结 Git diff，拒绝伪造路径、基线或范围。实际用户授权来自任务指令，登记、原生 ID 和本地状态只是协调数据。收集器不把员工提供的 argv 或候选代码放到更大的无沙箱环境执行；候选验收在实际 bubblewrap 边界内进行，控制端执行的 Git/policy/hooks 保持可信固定来源。

请求状态包括 `submitted`、`integrating`、`delivered`、`conflict`、`needs_retry` 和 `queued`。冲突和失败各保留独立目录，不污染下一个整合。每个员工最多一份未完成请求；冲突经明确 resolve 改基线后可交新请求，历史冲突不删除。真实远端提交及准确标签用于恢复确认；主目录刷新与远端交付分开记录。

SessionStart 自动分配员工工作区并注入明确路径；重复 session 复用，同一组员工可使用 assign/create 分配任务范围。它不重绑定宿主 cwd/沙箱。CLI -C 加 workspace-write 和 App 在员工目录新建聊天是实际启动接入点；若旧管理目录会话继续工作，必须对工具使用明确员工路径，不能将上下文引导报告为硬权限限制。当前模型登录、宿主 hook 信任和实际模型调用不在文件协调验收的通过范围。

依据与选择：

| 来源 | 实际支持 | 本项目采用方式 |
| --- | --- | --- |
| OMX 固定源码 `1dcf51359f3caeeebfed0bcbeea867ff0838d533`，`src/team/state/tasks.ts`、`src/hooks/session.ts` | claim 的锁内重读、按任务登记及状态锁；其锁不覆盖任意源码编辑 | 借鉴短事务和任务范围，不把已安装 Team 当成跨独立 session 强制隔离 |
| [OpenAI 官方 Worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees) | 新聊天 Worktree；已有聊天 Hand off | 保留该宿主迁移入口说明；本员工执行层采用完整普通克隆 |
| [OpenAI 官方 hooks](https://learn.chatgpt.com/docs/hooks) | SessionStart 上下文；PreToolUse 并非完整强制边界；子代理可共用父 session ID | hooks 负责分配/提示/当前任务 Stop，不冒充所有写入的硬门禁 |
| [OpenAI CLI 参考](https://learn.chatgpt.com/docs/developer-commands) | -C/--cd 在 agent 开始前选择目录，sandbox 控制命令权限 | 明确启动新员工 CLI；不追加整个主项目写权限 |
| [Git worktree 官方资料](https://git-scm.com/docs/git-worktree) | 工作区各自有 HEAD/index，部分 refs/config/元数据共享 | 为兼容现有脚本且保持配置和收据独立，当前选择普通克隆 |
| 本机 Git、Python 标准库、已安装 bubblewrap | Git 版本控制、flock/原子文件操作、实际 namespace/write 边界 | 复用已安装能力，不安装 GitHub 新依赖、不改 OMX 固定上游 |

官方页面实际抓取于 2026-10-08；原 `developers.openai.com/codex/` 返回 308 到上述官方域，搜索地址返回 404，均记录于 `sources.json`，不是伪造搜索结果。正文和抓取程序保留，来源说明不把在线文档当成本地宿主每项功能已启用的证明。

已修复的审查发现及回归包括：更新吞掉未交付提交基线、相同目录范围重叠漏判、工作区父目录链接越界、证据父目录链接跨边界写入、可变 Git/协调元数据影响控制端执行、随机多份 outbox 顺序、根入口收集全部任务、员工 /tmp 不可写时 hook 失败。最终验收结果以本目录 `verification.json` 的实际命令和退出码为准；审查记录不能代替通过的测试。
