# 多 session 并发保护核查

当前没有完成可靠的跨独立 session 防撞设计。可以并行执行任务，但两个 session 共用项目工作目录时，没有已启用的机制保证它们不会同时修改同一个文件；Git 和交付检查也可能因此让一个任务停止等待或报错。该结论置信度高，依据实际入口源码与隔离复现；本次没有修改生产机制。

## 已有保护与缺口

| 层次 | 已有保护 | 未覆盖的风险 | 置信度 |
| --- | --- | --- | --- |
| 源文件编辑 | AGENTS 要求分配文件范围，Team worker 有共享文件避让指令 | 独立 session 没有强制文件所有权或编辑互斥；同一文件可能被覆盖 | 高 |
| OMX 状态 | 会话指针锁、按 session 划分状态目录、Team 任务 claim 锁 | 锁不覆盖任意源码文件、项目 Git 索引和交付流程；部分状态锁仍会等待或超时 | 高 |
| Git 操作 | Git 自身的短期元数据锁、远端历史检查、不强推 | 多步同步没有流程级互斥；共用索引和分支可能互相干扰；远端出现新提交时需要整合 | 高 |
| 自动提交范围 | 文件白名单、大小限制、验证 tree、准确交付标签 | `candidates()` 收集整个工作区，不区分任务所属 session，可能将另一任务改动一起暂存 | 高 |
| 交付状态 | tree 和证据一致性检查 | `pending.json`、`tag_receipt.json`、`sync_receipt.json` 是共享固定路径；另一流程可能覆盖状态或导致校验失败 | 高 |
| Stop 检查 | 判断整个仓库是否有未提交／未推送内容，重复 active hook 不再次阻止 | 不区分 session；其他任务或实时记录本的改动会触发当前 session 的继续提示 | 高 |
| 任务临时克隆 | 克隆内拥有自己的 Git 索引和工作目录，限定提交文件 | 部分任务只在交付阶段克隆；此前在主目录的编辑仍共享。克隆也不能消除远端同分支整合冲突 | 高 |

## 直接证据

- `analysis/scripts/project_git.sh:4`、`:8`：项目入口选择固定主目录和 `.project-git`，没有按 session 创建独立编辑工作区。
- `analysis/scripts/project_sync.py:30`、`:55`：候选文件取整个仓库的 modified/deleted/others，随后全部 add；没有 session 文件清单参数。
- `analysis/scripts/project_sync.py:50`、`:54`、`:88`：流程顺序为 fetch、检查远端祖先关系、准备并提交、push；未将整个流程放入互斥临界区。拒绝非快进是防止历史被覆盖的保护，不保证任务不会被整合要求阻塞。
- `analysis/scripts/project_sync.py:93`：交付后要求整个工作区干净，别的任务持续编辑也会使交付报错。
- `analysis/scripts/project_sync.py:103`：Stop 根据 cwd、整个仓库状态和上游引用判断；没有读取 `session_id`。
- `analysis/scripts/task_delivery.py:12`、`:83`、`:104`，`analysis/scripts/project_sync.py:96`：交付状态使用固定共享路径并直接写入。
- `analysis/project_conventions/sync_conventions.py:24`、`:37`：现有任务专用克隆是在交付时复制主工作区文件，不是所有 session 从开始即使用的统一隔离机制。
- `.codex/hooks.json:32` 注册 PreToolUse。实际运行入口 `analysis/vendor/oh-my-codex/dist/scripts/codex-native-hook.js:21643` 及对应源码 `src/scripts/codex-native-hook.ts:22598` 明确 PreToolUse 为 advisory-only；不能把残留路径分类函数当成已生效的文件写入拦截。
- OMX `analysis/vendor/oh-my-codex/src/hooks/session.ts:302`、`:318` 锁定 `session.json`／`session-owner.json` 指针；`src/mcp/state-paths.ts:688` 提供 session 状态目录隔离。
- OMX `analysis/vendor/oh-my-codex/src/team/state.ts:692`、`:721` 与 `src/team/state/tasks.ts:71` 锁定任务 claim／dispatch 记录；`src/team/worker-bootstrap.ts:311` 要求 worker 对共享文件编辑向 leader 报 blocked。这些不构成独立 session 源文件互斥。

## 隔离复现

实际命令：`python3 analysis/session_concurrency/audit.py`。程序只将生产函数的仓库和 Git 适配器指向 `/tmp` 内一次性小仓库，不运行真实同步、push 或生产 hook。

1. 同一个 fixture 工作区含 A、B 两个任务文件，实际 `project_sync.candidates()` 返回两者。
2. 在已提交且上游一致的 fixture 上先确认 Stop 放行，再新建任务文件；分别传入 A、B 的 `session_id`，实际 `stop_status()` 对两者返回相同 block。
3. `stop_hook_active: true` 时实际 Stop 返回空响应，证明有单次重复抑制，不等于已经按 session 隔离。
4. 两次顺序调用实际 `task_delivery.prepare()`：A 写入 pending 后，B 写入同一路径，读取到的 task 从 A 变为 B。无需运行真实竞争写入，即可证明该收据没有任务独立命名或占用拒绝。

四项检查通过表示上述保护边界被复现，不表示防撞问题已修复。证据见本目录 `verification.json`。

## 最小改进方向

1. 每个 session 从任务开始就在独立克隆或工作目录和分支中编辑。现有脚本更容易支持独立克隆；若采用 Git worktree，先适配 `.git` 指针文件识别和带主项目绝对路径的 hooks，不能直接承诺现有入口兼容。
2. 主工作区的整合与交付只由一个流程进行，并对整个整合／commit／push 流程加互斥锁。每个任务提交明确文件清单，交付状态按任务/session 存放；发生基础版本变化时先保留双方成果再整合。
3. Stop 只判断本任务的文件与交付状态，其他任务和实时记录本的未提交内容作为项目状态提示，不将当前已完成任务无限续作。任务清单只用于协调，不替代宿主写权限或授权。

独立编辑目录可以避免直接互相覆盖；合并同一文件的不同修改仍可能需要解决冲突。仅增加提示词、session ID 或普通建议性文件锁，不能保证所有直接文件写入都被阻止。

## 推断与未知

推断：现有共享目录加全局同步/Stop 逻辑足以解释本会话已经完成诊断后仍收到其他任务未提交文件提示的现象。本次隔离复现支持这个因果路径。

未知：本次没有证明真实项目发生过文件内容丢失，没有验证宿主每一次实际加载或信任了 hook，也没有重放真实同时编辑。已安装的 OMX Team 代码不能当作当前多个独立 session 正在使用有效 Team 的证据。

本次仅核查和提出建议；防撞机制实施、生产互斥和跨 session 端到端验收尚未进行。
