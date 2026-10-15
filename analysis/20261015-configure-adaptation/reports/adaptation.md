# configure 工作机制的核结构适配

本次依据用户要求，仅参考公开仓库 <https://gitee.com/zhangxin8069/configure> 的提交 `43c216e8a2e755975633c163b38ad79bac7042d7`，按本项目实际能力增量吸收。用户明确：专业背景是原子核结构、能级纲图、gamma 线强度及 ADO、P 等参数、集体激发；本次不开发对应核谱程序，常规物理判断边界模仿来源的自主、有证据和诚实报告做法。用户未要求 plan，本次没有生成计划。

## 实际采用

- 共享专业与行为正文为 `analysis/scripts/agent-prompt.txt`。从物理、工程和联合视角出发，专业示例改成核谱与核结构研究；吸收 `phys-model/pure` 的对象、观测量、模型假设、适用范围、量纲、对称性、极限及误差核对。
- `co` 复用现有 `codex_entry.py` 和独立员工克隆，新会话向首条输入前置共享正文、实际员工路径及技能清单。普通 Codex 的模型、provider、登录和权限配置保持原有来源。真实 CLI 用参数数组启动，提示词和文件路径只作为数据传递。
- 原生 `skill-routing-hook.mjs` 复用共享正文。SessionStart 首次启动时，若 co 已传入同一正文则避免重复；clear/resume/fork/compact 的直接事件验证会重新输出正文。具体事件是否由宿主触发，仍受项目现有 matcher 和信任配置约束。UserPromptSubmit 保留自动路由和正文路径提醒。
- 扩展既有 `chx-data-analysis` 的研究上下文，保留原始数据、输入格式和处理边界；没有复制第二套同义技能目录，也没有修改 vendor 快照。
- `co_shell.sh` 只定义 co，安装器使用单独标记块与原文件备份。用户曾关闭的旧 codex source 保持关闭。历史恢复、管理命令和项目外调用保留原生语义，不把历史线程伪称为新隔离工作区。

## 上游全部 28 个技能的对应

下表记录复用与参考关系，不声称上游技能已经按原名安装。用户使用 `{~name}` 时，先查同名已安装技能；上游旧名按下表解释，只有实际需要才读取对应技能或使用真实角色。提示中的专业视角不代替工具的 `agent_type`。

| 上游技能 | 本项目采用方式 |
| --- | --- |
| `all`、`auto`、`make` | 常规任务由 executor 连续执行；需要长期编排时使用现有 OMX，并遵守用户明确目标授权；不引入默认无限循环 |
| `brainstorm`、`plan` | 复用 deep-interview、plan、ralplan 及 analyst/architect；仅用户主动要求才输出计划 |
| `dispatch`、`team` | 原生子代理、team、session_coordinator 的独立员工和串行整合 |
| `analy`、`pure` | analyze、explore/analyst；专业证据核对吸收进共享正文，论文阅读按需复用 Nature 技能 |
| `debug` | debugger 及根因调查；修复在授权范围由 executor 实施 |
| `diff`、`review` | git-master、code-review、ponytail-review 和实际 Git diff |
| `test`、`tdd` | 现有项目测试、test-engineer/verifier；需要时使用 ultraqa，不为简单任务扩建测试框架 |
| `optim`、`fast` | Ponytail 的最小可靠实现和实测性能证据；performance-goal 只在明确目标模式授权下使用 |
| `doctor` | 现有 doctor、verify_project_tools.py 与针对当前改动的检查 |
| `follow-up`、`go-on`、`research-notes` | 现有 go-on、wiki、nature-experiment-log、decisions 和用户已有任务记录，不新增并行日志体系 |
| `form`、`init` | 项目既有目录规则、skill、omx-setup 与必要的维护；不批量重排用户文件 |
| `report` | Nature 写作、阅读、汇报与科研图技能，以及项目按需报告规则 |
| `md-tex-sync` | 当前没有双格式同步请求；需要时再按现有 LaTeX 编辑能力处理，不新增同步器 |
| `phys-model` | 原子核结构专业提示词和 chx-data-analysis 中的统一物理核对链 |
| `tag` | 保留 task-tag 与本项目作者—任务标签、持续授权的验证后自动交付 |
| `skill-creator`、`up` | 现有系统 skill-creator、skill、evolution 和来源/镜像验证 |

上游 `configure-check.sh`、`coverage-report.sh` 的资源、镜像、入口检查由现有项目验证工具覆盖；本次补充实际 hook 生命周期回归。`task-scope.sh` 只推荐关键词链，不执行技能；本项目继续按意图和技能描述选择，不增加第二套固定关键词分流器。

## 专业与权限适配

- 格点 QCD、夸克传播子、Wilson 线、plaquette、PyQCU 专例及个人目录不进入运行提示词。没有照搬上游默认 CUDA 或单精度设置；精度、模型与参数由任务和误差要求确定。
- 常规物理判断不新增逐项人工审批。能级/跃迁解释和模型比较可自主提出、核对和报告，事实、推断和假说分别标明；缺失输入保留缺失，不预设 P 的定义、角度分组或实验数值。
- 沿用数据只读、科学程序留档、C++/ROOT 特定任务例外和 Python/SVG 绘图约定。研究背景本身不构成运行科学分析的请求。
- 不采用来源中的个人 provider、固定模型、danger-full-access、自动原生 goal 或默认答复当作真实用户批准的做法。这里的用户持续授权、明确范围和宿主审批优先，未额外请求重复授权。
- 不重复引入参考库的 hooks、Git hooks 或插件安装器；本项目已有原生 hooks 与交付检查。插件是否安装、启用和受信分别核对，本轮没有安装第三方插件，也不编辑信任数据库。

## 使用与验证

当前终端可 source `analysis/scripts/co_shell.sh` 后使用 co；新 Bash 终端的独立安装命令为 `python3 analysis/scripts/codex_entry.py --install-co-shell`。新会话首次文本输入自动加入研究正文；普通 resume/fork 和 review 管理路径保留原生语义，`co exec -` 的 stdin 形式暂用原始 codex。

可重复检查：

```bash
python3 analysis/20261015-configure-adaptation/test_prompt_hooks.py
python3 analysis/wsl_codex_entry/test_entry.py
```

前者实际运行 Node hook，验证正文注入、同哈希去重、恢复时重注入、逐次提示、项目外不注入、损坏输入/缺失正文报错、技能镜像及来源指纹。后者用本地 fake CLI 捕获实际 argv/cwd/env，核对 co 前置文本、员工隔离、管理/历史/参数语义、权限拒绝及只 co 安装行为；没有调用模型服务。员工各自的验证记录位于本任务目录。串行整合后的真实沙箱复测、推送状态以协调收据为准，不提前声明。

限制：自动选择技能仍由模型在任务上下文中执行；仅有清单不能证明所有技能已执行。Node 回归证明脚本输出，不能代替宿主的 hook 信任。真实模型生成行为和科研数据处理不属于本次测试。

来源版本和文件指纹见 `analysis/third_party/sources.lock.json` 的 `sources.configure`；MIT 许可保留于 `analysis/third_party/licenses/configure/LICENSE`。前次只读机制调查见 `analysis/20261015-configure-startup/reports/startup-mechanism.md`。
