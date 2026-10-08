# 任务执行计划：独立 session 与协作任务防撞机制

- 创建日期：2026-10-08
- 状态：已完成，实现与验证记录已正常提交并推送；真实远端及准确标签核对通过
- 用户授权记录：2026-10-08 用户明确要求完善当前并行漏洞，将每个 session 作为员工，所有工作服务于 chx_20260622，支持多名员工及分组协作，保证工作不撞车，并允许参考 OMX 或 GitHub 方案。安全的实现、配置、验证和本项目 commit/push 使用既有持续授权；不变更宿主信任、登录、保护目录权限或数据边界。

## 目标与范围

实现可运行的 session/任务协调入口：从开始隔离员工编辑空间；同一项目登记任务、员工及协作关系；明确文件范围与交付状态；序列化整合与 Git 同步；并发冲突保留双方成果；Stop 只跟进当前任务。员工数量没有写死的小上限，实际并行模型任务、磁盘和 CPU 仍受宿主与本会话上限约束。

必须区分真实物理隔离、建议性文件声明及权限边界。仅有 session ID 或注册表不能充当宿主写权限。核实新 session 启动方式和 hooks 可提供的能力，不将提示词引导说成任意工具写入硬拦截。现有会话与实时记录本不强制搬移或回滚。

## 输入与依据

- 已提交核查：`analysis/session_concurrency/reports/diagnosis.md`、`audit.py` 和真实隔离复现结果。
- 本地实现：`analysis/scripts/project_git.sh`、`project_sync.py`、`task_delivery.py`、Git hooks、`.codex/hooks.json`、OMX 固定源码和配置。
- 当前根工作区及索引干净，Git 元数据仍是 `.project-git/`。
- 参考资料：优先已安装 OMX 的任务 claim、租约和状态锁；必要时核对 Git/OpenAI 官方资料及 GitHub 上游。来源、版本、可借鉴部分和未采用原因保存到本任务报告；避免为文件隔离引入大型框架。

## 预计建立或修改的文件

| 路径 | 操作 | 用途 |
| --- | --- | --- |
| `analysis/plans/2026-10-08-session-coordination.md` | 新建/更新 | 授权、设计决策、进展及验收 |
| `analysis/scripts/session_coordinator.py` | 预计新建 | 员工工作区、任务/协作注册、范围和序列化整合入口；具体接口经设计核实后记录 |
| `analysis/scripts/project_sync.py` | 修改 | 同步互斥、明确任务范围、任务状态与 Stop 隔离 |
| `analysis/scripts/task_delivery.py`、`project_git.sh` | 按必要性修改 | 独立仓库/工作区与交付状态适配，保留验证 tree 与既有标签语义 |
| `analysis/scripts/project_runtime.py`、`install_project_sync.py` | 修改 | 共享只读工具安装、员工本地缓存与可信交付/生命周期入口 |
| `analysis/session_coordination/test_coordination.py` | 新建 | 临时真实仓库的并发/冲突/恢复验证 |
| `analysis/session_coordination/verify.py` | 新建 | 收集实际验收结果与来源/语法检查 |
| `analysis/session_coordination/reports/` | 新建 | 设计、来源、验证 JSON、使用说明 |
| `AGENTS.md`、`README.md`、`.codex/hooks.json` | 按接入需要修改 | 员工入口、协作规则和经过验证的 hook 接入；保护路径通过真实宿主审批，不修改信任数据库 |
| `.agents/skills/task-tag/SKILL.md`、`.codex/skills/task-tag/SKILL.md` 等确需适配的技能 | 按必要性同步修改 | 双入口保持一致，避免旧同步规则重新收集所有 session 文件 |

运行时注册、锁、独立 checkout 和收据放本地忽略目录；原始/中间数据、凭据、员工临时 Git 元数据不提交。若需新增基础文件或工具路径，检查根白名单，不复制原始数据或大型处理文件到员工仓库。

## 方法与统计处理

不涉及实验统计或绘图。验证单位为可重现的并发操作与真实 Git 提交/推送结果；所有破坏性冲突场景只在 `/tmp` 一次性小仓库中运行。至少使用两个独立进程，不以串行 mock 代替互斥验证。不把有限验收外推为无限资源或所有任意手工写入的绝对安全。

## 执行步骤

1. 保存计划。原生 architect 核查设计与边界；researcher 核对官方 session/worktree/hook 能力；explore 核查现有接入面。均限定只读，不互相覆盖文件，主代理整合。
2. 根据证据修订本计划和 `reports/design.md`：明确员工启动/加入、独立目录、共同任务、任务范围、数据输入输出、租约/退出/恢复、交付与冲突处理。实现前锁定最小可验收接口，不先造复杂调度服务。
3. 保存显式程序和真实并发回归用例，再修改生产入口；任务拆分给原生 executor 时明确文件所有权，不回滚他人修改。
4. 运行 `python3 analysis/session_coordination/test_coordination.py` 和 `python3 analysis/scripts/test_project_sync.py`。验证两个员工修改相同路径隔离、不同任务范围不混入、合作成果整合、冲突保留、同步互斥、进程异常释放锁、当前任务 Stop 范围以及路径/凭据/数据边界。
5. 核对受保护配置的真实接入和可用启动方式；无法在当前宿主自动改变 session cwd/沙箱时，提供并验证明确的隔离启动入口，报告必须满足的启动条件，不假装已将现有 App 会话切换。
6. 更新使用规则和验证证据，按 task-tag 通过现有同步程序正常 commit/push，核对真实远端和准确标签；清理只针对明确由本任务生成的临时资源，不大规模删除或处理其他 session。

## 验收与完成标准

- 员工工作区物理独立，创建/恢复幂等，不创建共享编辑索引；两个员工同文件编辑不能覆盖对方工作区。
- 员工可登记到同一协作任务，范围/状态可查询；另一个任务的文件和收据不混入本次交付。
- 共享主仓库整合和同步有完整流程互斥；并发远端变化不强推；内容冲突保留员工分支与完整产物，并返回可恢复的明确结果。
- Stop 对无当前任务或已交付任务不因其他任务/实时记录本的修改反复阻止；当前任务未提交/未交付仍能正确提示。
- 输入路径遍历、符号链接、越界输出和凭据文件受既有边界检查；不伪造 session 身份、权限、验证或模型任务启动成功。
- 有明确日常启动和多人协作命令、真实并发验证 JSON、证据来源、限制与恢复方法；最终同步到本项目 Gitee 并核对工作区状态。

## 风险与待确认事项

新 session 的宿主启动接口、PreToolUse 硬拦截能力、Git worktree 对 `.git` 指针和固定路径 hooks 的兼容性待核实。可依据真实环境选择独立克隆或受支持 worktree，不因普通实现选择反复询问；无法跨越的宿主限制须如实说明。既有任务需安全迁移，运行记录和源码范围不能仅以注册表推断用户授权。

## 进度与恢复记录

- 已完成：当前状态与既有实现检查、计划、独立 architect/explore/researcher 证据及实现。协调程序、同步互斥、限定文件、可信 hooks、员工本地 outbox 和真实并发测试均落盘。官方来源脚本和实际抓取正文保存到 `analysis/session_coordination/`，OpenAI 原域实际跳转至官方 learn.chatgpt.com，记录最终 URL；搜索页 404 如实保留。
- 关键决策：普通明确实现任务，不启用目标模式或退役工作流；使用现有标准库/Git能力优先，真实权限与数据边界不变。
- 设计已确定：标准 Git 克隆物理隔离；控制端短注册锁与完整整合锁分离；同任务重叠范围拒绝、显式释放交接；员工只写本地 outbox，启动器父进程或管理 session 收集。注册表仅作为协调事实，不提供权限。合并验证使用已安装 bubblewrap，根只读、候选目录可写、网络隔离；可信控制代码负责 Git/policy/tag，不执行候选可变 hooks 的扩大权限路径。
- 实际验收进展：同步回归真实临时提交/推送/标签、进程互斥/杀进程释放、限定文件、pending 覆盖拒绝、污染 Git 环境、可信 hooks 和员工本地临时目录均已通过。初次并发验收发现更新后 Stop 误阻止、工作区父目录符号链接越界，已修复并保留回归断言；新沙箱版在前九组通过后发现员工 hooks 临时目录落 /tmp，只绑定员工可写时失败，改为员工 `.omx/tmp/` 后待完整重跑。
- 宿主证据：默认外层沙箱禁止 bubblewrap 的 NETLINK_ROUTE；经真实审批只读测试 `bwrap --ro-bind / / --proc /proc --dev /dev --unshare-net --die-with-parent /bin/true` 实际退出 0。后续整合验收必须在允许运行该沙箱的控制端执行，不能假装默认外层已支持；不能用无沙箱回退替代。
- 接入限制：官方 SessionStart 不能修改现有宿主 cwd/沙箱，hook 覆盖不是完整强制边界。提供已文档支持的独立 CLI -C 启动与 App 指定员工目录入口，旧 App 会话没有自动迁移；CLI 认证和真实模型调用不作为文件/协调验收通过事项。启动器不扩大员工主目录写权限。
- 最终修复与验证：peer review 发现候选可变 Git/协调元数据、更新未交付提交基线、多份 outbox 顺序和不限定根提交，以及证据父目录链接跨边界写入；均修复并保留真实回归。最终 `python3 analysis/session_coordination/test_coordination.py` 在获准的真实 namespace 环境退出 0，18 组场景全部通过；生成回归来源指纹与 `reports/concurrency_checks.json`。证据只证明本机已覆盖场景，不外推无限资源或任意宿主。
- 安装结果：`python3 analysis/scripts/install_project_sync.py` 经真实宿主审批实际退出 0，同步 task-tag 双入口、对应指纹与 SessionStart/Stop 配置，未改宿主信任。自动 SessionStart 为不同 native session 分配不同克隆；相同 ID 幂等复用，assign 可安排到共享任务，原生子代理 ID 共用父 ID 的边界已写明。
- 实际程序与结果：`analysis/session_coordination/test_coordination.py`、`verify.py`、`fetch_docs.py`；报告在 `reports/`。控制端真实协作命令、冲突 resolve、更新防吞基线、App/CLI 接入与宿主限制见 `reports/usage.md`、`design.md`。
- 最终审查：code-reviewer 为 APPROVE、architect 为 CLEAR；两者只读审查不当作额外执行测试。主代理 `python3 analysis/session_coordination/verify.py` 退出 0，复核18组真实回归的稳定源码指纹、现有Git同步回归、技能镜像/指纹、配置和直接生命周期 JSON，以及四篇真实官方文档。报告 `reports/verification.json` 为 passed；后续仅文档与交付收据更新，程序逻辑不再改变。
- 当前阻碍：本次实现无未解决的已验证代码阻碍。控制端默认 App 外层禁止 bubblewrap namespace 时需真实宿主审批；旧 App 会话 cwd/沙箱不自动改变，实际模型登录/启动和每次 hook 宿主加载不包含在本次通过声明中。
- 交付：根管理同步强制 `--files`，本次只提交已验证的协调代码、测试、技能/hooks、计划和报告；用户新出现的实时记录本编辑保留，不能用本次程序验证证明实验内容。远端成功以 `.omx/delivery/sync_receipt.json` 与真实核对为准；运行注册/员工克隆/收据仍忽略，不递归提交收据。
- 实际交付结果：29 个明确任务文件正常提交并推送，准确标签为 `chx6-员工并行协作`。现有同步程序实际完成 fetch、范围/大小与暂存对象检查、验证tree、commit、准确标签push及真实远端核对，退出 0；本地收据 `.omx/delivery/sync_receipt.json` 为 pushed。本完成记录的后续文档提交仍使用同一已核对源码和通过证据，不重复冒充运行18组回归。
- 完成边界：本次文件及索引已交付；执行期间用户继续编辑的实时记录本保留，不混入功能提交，也不以本次检查证明实验内容。原始 Ge/CsI、他人 software、信任数据库和目录权限均未修改。
- 下一步：新任务由 SessionStart 自动分配或通过 create/launch/App 新工作区入口安排员工；同任务用 assign/create 分配范围。旧会话不自动迁移；本任务没有未完成的实现步骤。实际运行阻碍按 usage 中 collect/resolve/integrate 恢复，不丢弃其他员工成果。
