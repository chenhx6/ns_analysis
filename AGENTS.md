# chx_20260622 项目约定

- 2026-10-18 用户明确归档旧 `time_offset/` 与 `timeOffset/`：已整体移至本地 `archive/20261018-time-offset/`。后续时间对齐程序以 `analysis/plans/process/2026-10-15-time-offset-revision.md` 为实施依据，重新建立 `timeOffset/time_offset/`；旧实现和结果仅为归档参考，不作为现行方法。归档不等于授权删除其中内容，本轮未启动新实现。

- 2026-10-15 用户确定：本项目研究方向为原子核结构，包括能级纲图、gamma 线强度、ADO、P 等参数和集体激发；借鉴 `zhangxin8069/configure` 的工作机制时，专业表述按本方向适配，不照搬 LQCD 或个人环境。本轮只适配提示词与工具工作流，不新增核谱分析程序。常规物理判断参照其自主、有证据、如实说明不确定性的边界，不额外增加逐项用户审批；本项目已有明确约定和宿主权限继续优先。

- 2026-10-15 用户要求：以后编写代码时，在相关函数处添加简要的功能注释，在重要算法程序行附近说明算法含义、关键条件或单位；注释保持简洁，与实际实现一致。
- 2026-10-15 time offset 新实现位于 `timeOffset/time_offset/`，单文件 C++/ROOT 分析范围和本轮方法见 `decisions/20261015-time-offset-single-run.md`；旧 `time_offset/` 保留作参考，本轮不删除、不沿用其多 run 流程。

## 任务计划与自主执行

- 2026-10-15 用户更正：只有用户主动要求制作计划时，才制作或输出 plan，包括单独的计划文件和回复中的计划。普通问答、查找、维护及其他任务不自动生成计划；不因任务复杂或技能、hooks 自动触发而另建计划。本条替代此前“每项任务先写计划”的要求。
- 范围明确的非危害操作可在任务范围内直接连续完成，无需额外确认。原始数据只读、危害系统和大规模删除等边界继续适用，宿主强制权限审批不能绕过。2026-10-07 用户持续授权：项目文件更改完成并验证后自动 commit 和 push 到本项目 Gitee 仓库，包括本次；其他对外发布与发送消息仍需对应授权。
- 用户主动要求制作计划时，使用 `analysis/plans/YYYY-MM-DD-short-task-name.md`，参考 `analysis/plans/_template.md`；科学处理计划沿用下文的专用位置。计划写明目标与范围、输入及依据、预计新建或修改的文件及用途、执行步骤与关键参数、统计方法、预计结果、验证标准和待确认事项。与任务无关的项写“不适用”及原因，不凑内容。以下计划内容与维护规则仅在用户已要求该计划时适用。
- 统计方法按任务说明分析单位、筛选条件、模型或检验、适用假设和不确定性处理；尚未确定的方法或参数标明“待确认”，不编造。预计结果说明交付文件、图表或指标，并区分待检验假设与已知事实，不预设显著性或具体数值。
- 计划保留状态、实际用户授权记录、已完成步骤、关键决策、结果位置和下一步。执行中及时更新；方法、输入范围或交付内容有实质变化时先修订计划，涉及危害、不可逆操作或超出已授权任务范围时再确认。
- 上下文压缩或会话恢复后，如有用户要求的对应计划，先读取再继续；没有计划时不补建。不得仅凭聊天摘要、计划状态或本地记录推定用户已授权执行。确认记录必须如实对应用户指令。

## 科学处理计划与长期决策

- 用户主动要求的科学数据处理计划放 `analysis/plans/process/`，讨论期间同步保存参数、方法、阶段边界和恢复检查点。2026-10-08 用户已明确要求的时间对齐计划为 `analysis/plans/process/20261008-time-offset.md`，用户已移动，沿用新位置，不另建项目根plans目录。常规项目维护不自动生成执行计划。
- 类 ADR 的长期记录使用项目一级 `decisions/`，文件名 `YYYYMMDD-topic.md`，保存用户确定的实验背景、分析目标、约定、理由和适用范围；代理建议、假设和已测事实分别标明。实质改变时新建记录并说明替代关系，普通进度更新处理计划。
- 开始或恢复相关科学任务时，先读取 `decisions/` 中适用且未被替代的记录和 `analysis/plans/process/` 对应计划，再核对最新用户指令。时间对齐读取 `decisions/20261008-time-offset.md`、`decisions/20261008-time-offset-method.md` 及最新 `decisions/20261009-time-offset-program.md`；不得因旧建议重新引入CFD、吸收片分段或异常根因调查。文档状态不代替实际授权。
- `decode_data/`、`time_offset/`、`run_log/` 为项目一级直接数据处理目录；任务程序、报告、小表、标定配置和回查数据按该任务目录集中保存。`analysis/` 主要用于间接处理、通用工具和项目维护，已有实验记录本留在原位置。此处用户明确的科学任务位置优先于下文及技能的 `analysis/` 默认目录；不批量迁移既有文件。
- `time_offset/` 第一阶段读取 `ts,cid,sid,ch,sr`，参考 `(cid,sid,ch)=(0,2,5)`，保留 `cid in {0,1}`、`sid>=2`，使用 `Delta t=t_reference-t_channel`、搜索窗 `[-1999,1999] ns` 和 `2/24 ns` 分箱。100–300ns后续符合窗为半宽；cid1双峰已由用户确认为同run同通道。用户已确定编译C++/ROOT处理主数据，写法参考DecodeAndSortAll，其余采用Python；峰选择、run分组和后续阶段边界从上述决策／计划读取，不凭记忆改参数。
- 2026-10-09用户明确：time_offset任务用一套可编译C++/ROOT程序完成读取、填谱、ROOT拟合及导出，配套cc与hh，写法参考DecodeAndSortAll；计划包含可渲染LaTeX算法公式供核对。不拆Python分析／绘图程序，不要求SVG或figures目录，直方图／拟合保存ROOT供打开回查。本任务采用上述交付范围，不强加下文的SVG交付与视觉检查要求；其他绘图任务的原约定继续适用。
- 原始 Ge/CsI 和他人的 software 目录继续禁止写入；仅在用户指定范围内只读参考其源程序。本轮允许读取 `/home/ys/data_401/data/software/event/`，不运行或改动。原 decoder、编译文件和原 crate 配置本轮不改；后续至少3路并发解码另按处理计划安排。

## analysis 目录组织

- 2026-10-08 用户要求：新建文件和文件夹统一采用英文命名，使用 ASCII 英文字母、数字、连字符、下划线和点，避免乱码；文件内容可使用中文。已有路径迁移按具体任务处理，原始数据只读边界不变。
- 新建需要留存产物的任务使用 `analysis/YYYYMMDD-topic/`：日期为任务开始日（Asia/Shanghai），主题用简短英文 ASCII；程序和小型数据表放任务目录，图表放 `figures/`，需要保留的报告放 `reports/`。按实际产物建目录，不生成空 reports；只有确需多个程序文件时才增加代码子目录。
- 同一任务跨日沿用原目录；同日同主题优先复用，独立任务重名时增加主题限定或短序号。已有任务原地续作，旧目录不批量迁移。计划继续使用 `analysis/plans/YYYY-MM-DD-topic.md`，通用工具、公共依赖和大型数据目录保持各自用途。
- 2026-10-08 用户已将 run.log 输入数据处理目录移至项目根 `run_log/`，与 `decode_data/` 同级；沿用其中既有程序、小表、图表和报告。此目录作为明确例外，不移回 analysis；原始 Ge/CsI 仍只读。新建分析任务不再把程序、小表、图和报告分散到全局 `code/`、`results/`、`analysis_figure/` 和 `records/`。
- 通用项目脚本存放于 `analysis/scripts/`；原 `analysis/code/` 已按计划迁移，入口、hooks 和引用同步使用新路径。
- `analysis/plans/` 是集中计划目录；`analysis/vendor/`、`analysis/third_party/` 保留其公共依赖用途。大型数据仍放项目根目录的专用数据目录，不能因为按任务整理而搬入 `analysis/`。

## 可审查的程序与数据来源

- 可以只读检查文件，核实格式和方法。生成或改变科学数据、分析结果或图表的步骤，必须使用已保存、可检查且可复跑的程序，包括科学数据的解析、筛选、变换、统计、拟合、模拟、导出和绘图。可复用已有程序，不要求每次新建脚本；任务程序放对应任务目录，通用工具放 `analysis/scripts/`。
- 一般文件查找、只读检查、问答、配置调整和项目工作流缺陷修复可直接使用工具、命令或修改现有实现，无需额外新建执行脚本；实际代码修改和必要测试仍须保留。维护任务中若有科学结果生产步骤，该步骤仍须程序留档。按科学复现需要判断，不按命令长度、所用语言或任务名称判断。
- 需要科学复现时，交付提供程序链接、输入输出、实际命令及验证记录；用户要求计划时再在计划中列出程序路径、输入输出和拟运行命令。结果中的科学数据必须由程序读取真实输入并计算，模拟和估计须按已确认的方法明确标注，不能由 AI 猜测、补造或凭印象摘录；缺失项保留缺失及原因。

## 报告留存与回复

- 科学分析与图表交付、需要长期回查的方法或决策、需要保存证据链的复杂调查，以及用户明确要求报告的任务，应保存报告。复用已有相关报告，避免另写重复总结。
- 普通问答、内容查找、轻微文字或配置修改、边界清楚的小修复和无需长期保留的临时检查，默认不另建报告；回复交代结果和必要验证。程序留档与报告留存分别判断，无报告不免除必要测试、真实性核验和版本交付证据；计划只在用户主动要求时制作。
- 无报告任务若交付工具需要验证 JSON，优先复用有效证据，否则保存最小的 `analysis/YYYYMMDD-topic/verification.json`，无需创建 reports 或叙述性报告；有报告的任务将验证记录集中放在 reports 中。
- 回复采用信息完整的摘要：删除重复、套话和无关过程，不限定三行、固定字数或段落。不打开链接也应知道答案或主要改动、结果、关键依据或验证、影响结论的限制和未完成事项；按任务相关性取舍，不机械填表。
- 有报告时，回复概括目标、关键方法或改动、主要发现、验证及重要限制，附报告和关键产物链接；详细过程、完整数据及复现步骤留在报告。无报告时，在回复中直接提供理解和使用结果所需的信息。
- 不能只回复“完成”“已修复”或文件路径。科学结论保留关键数值、单位、适用条件和不确定性；修复交代原问题、现在的行为及验证范围。区分已验证事实、推断与建议，有阻碍时说明实际完成到哪一步。

## 绘图约定

- 以后本项目的图表统一使用 Python 绘制，预览和最终导出均由 Python 代码生成；不自动改用 R 或其他绘图后端。
- 不调用 AI 图像生成或编辑工具制作图片。数据图必须由可追溯的输入数据和 Python 绘图代码生成，防止图像错误表达数据关系；示意图同样使用 Python 绘制，并注明其示意性质。
- 今后生成的图表仅保存 SVG，不额外保存 PNG、PDF、TIFF 等副本。既有实验原始照片、截图作为来源材料保留，不因新导出约定删除或伪装为新图表。
- 绘图代码和必要记录写明数据来源、坐标轴、单位、筛选及变换、颜色或标记含义、输出文件和核对办法；交付时保留代码和绘图所用的数据表。用户主动要求绘图计划时再将这些信息列入计划。
- 每次绘图或修改图表后都要查看最终 SVG 的实际渲染，检查文字／图例堆叠、字符裁切、字体缺字、坐标轴、单位和数据关系，并记录审查结果；仅检查源码或程序退出码不能代替视觉审查。看不到渲染结果时如实报告未完成，不能宣称已审查通过。

## 数据边界

- 项目根目录为 `/home/ys/data_401/data/chx_20260622`。
- `/home/ys/data_401/data/Ge` 和 `/home/ys/data_401/data/CsI` 是原始数据目录。允许读取作为分析输入；禁止写入、修改、重命名、移动、删除或在其中生成任何输出。
- `/home/ys/data_401/data/software` 属于他人的分析目录。不在其中开展分析，也不修改、移动或删除其内容。
- 所有处理输出写入本项目。解码 ROOT 文件及其他中间数据放在项目根目录下的专用数据子目录，例如 `decode_data/`、`processed_data/`。
- `analysis/` 存放记录本、分析代码、配置、结果图及小型结果表。大型数据文件不放入此目录。

## 分析与记录

- 编写处理程序时，明确区分只读输入路径和项目内输出路径；清理操作只能针对本项目内明确生成的文件。
- 运行大规模处理前，先确认输入格式、运行编号、通道映射和输出位置，并用有限样本验证。
- 保存可复现所需的输入文件或运行编号、参数、筛选条件、命令及结果位置到 `analysis/` 的记录中。
- 已有实验记录见 `analysis/experiment_log/record_analysis.md`；官方解码程序位于用户移动后的 `decode_data/DecodeAndSortAll/`。
- 2026-10-08 用户明确：`analysis/experiment_log/record_analysis.md` 是用户本人实时修改的记录本。保留用户编辑，普通差异不扩展为额外审查任务，不逐条核实、改写或反复请求确认；用户明确要求整理或分析时再处理。例行版本同步仍按持续授权保留记录，只做常规范围、大小和凭据检查。
- `DecodeAndSortAll/crate.dat`、`test.cc` 是原开发者的调试文件，保留；`run.sh` 是原项目自动调度脚本的底本，保留。静态搜索没有调用者或旧参数不构成删除这些源文件的依据。
- `decodeandsort` 单进程串行处理；批量加速在脚本层按 run 划分任务，限制同时后台运行的进程数。当前启用 Crate0（Ge）和 Crate1（CsI），两个命令行参数是两个 crate 的 run 编号，批处理起止区间由调度脚本展开。并行任务须使用不同输出文件，原始数据只读。
- 涉及本项目的数据分析时，自动读取 `.agents/skills/chx-data-analysis/SKILL.md`，遵循其中的数据格式和目录说明。

## 版本管理

- 2026-10-08 并行实施约定：每个员工/session 在任务开始前使用 `analysis/scripts/session_coordinator.py create` 建立独立普通 Git 克隆，再用 `launch` 或该目录的新 App session 工作；主目录作为管理及串行整合入口。一个任务可有多个员工，但每名员工有独立目录、索引、分支和文件范围；同任务的范围重叠先显式交接。session ID/登记信息仅用于协调，不代替真实权限、授权或物理隔离。
- 2026-10-08 用户补充：实际为 Ubuntu 20.04 的 WSL、Codex CLI，日常直接运行 `codex`。`analysis/scripts/codex_shell.sh` 的项目分派函数经个人 Bash source 接入后，在本项目新启动前创建独立员工；项目外/帮助/版本转交真实 CLI。未指定员工选择器的普通 resume/fork（含exec嵌套和原生全局参数）原样恢复真实CLI历史，不要求员工ID，不声明旧会话隔离；显式 `--chx-employee` 才恢复已有员工。`--chx-task`、`--chx-employee`、`--chx-scope` 用于分组和明确范围；管理模式输出路径限员工目录，危险 cwd/写范围/profile/远端或信任绕过参数不静默接受。工具编译资产读主安装绝对路径，不创建数据盘符号链接。用户注释source时保持关闭，不擅自重启；函数不改变宿主权限，既有会话不自动迁移，直接调用原始可执行文件不属于自动隔离入口。
- 员工用 `project_sync.py sync --check "<可重复验收命令>"` 冻结本地提交与 outbox；由启动器或管理 session 的 `session_coordinator.py collect` 串行整合。员工不得直接推送主分支。控制端重新核对冻结提交、在候选目录专用真实沙箱验收，并使用可信 Git 检查/hooks。合并冲突保留双方提交和独立冲突目录，释放整合锁；其他员工继续工作。无可用沙箱、网络/认证或宿主审批失败时保留状态，用 `integrate --submission <id>` 恢复，不降级为扩大权限执行。
- Stop 仅跟进当前员工的未交付工作，不因其他员工或实时记录本的未提交内容阻塞管理 session。根目录维护及记录本例行同步使用 `--files <明确文件列表>`，避免收集其他任务改动。根工作区有重叠编辑时保留编辑并记刷新待处理；员工成果的真实远端交付与根目录刷新分开记录。
- 隔离适用于经上述入口创建的新工作区；SessionStart 上下文不能重绑定已打开的宿主 cwd/沙箱，hook 也不构成所有工具的完整写入边界。既有 App session 用新员工目录或官方 Hand off/Worktree 功能重新隔离，不伪称已自动迁移。CLI 启动器使用 workspace-write，不把主目录或其他员工目录追加为可写范围。

- 远端仓库：`https://gitee.com/chx6/ns_analysis.git`。
- 跟踪项目约定、技能、hooks、必要配置，以及 `analysis/` 下的代码、记录和小型结果。
- 原始数据、中间数据、解码数据、编译产物、缓存和凭据不提交到 Git；不使用 Git LFS 上传这些数据。
- `.gitignore` 采用根目录白名单；新增项目基础文件或技能存放路径时同步更新白名单。
- `.githooks/` 存放可版本化的 Git hooks。通过 `analysis/scripts/project_git.sh` 配置和使用仓库；提交和推送前检查跟踪范围及单文件大小（默认上限 25 MiB）。`decode_data/DecodeAndSortAll/` 仅跟踪明确允许的官方源码及配置，解码数据和编译产物仍不提交。
- 每次项目文件更改完成并验证后自动 commit 和 push 到 `https://gitee.com/chx6/ns_analysis.git`，无需再次确认，包括规范、技能、hooks、计划、代码、记录和小型结果。提交前检查差异、跟踪范围及大小，获取远端历史；保留远端内容，不强制推送，不推所有标签。
- 自动交付使用 `analysis/scripts/project_sync.py sync --task "<简短中文任务>" --message "<提交说明>" --result "<真实成果>" --basis "<修改依据>" --evidence <实际验证JSON路径>`，路径遵循报告留存规则，机器验证证据不强制要求叙述性报告。复用已验证 Git tree；推送后核对真实远端，保持本次交付范围／索引干净。Stop 检查督促同步；真实阻碍需如实报告。
- 标签主要供用户阅读：名称为 `<Git作者>-<简短中文任务>`，说明填写修改者、执行协作、依据、改动、真实成果及验证结论。名称／说明不写 SHA256、提交编号或精确时间；内部验证仍保留。历史未知执行者标“未记录”，不能猜测；同名任务使用短序号，不覆盖旧标签。
- Git 元数据使用本地忽略的 `.project-git/`。`.agents/skills/` 是项目技能维护源，`.codex/skills/` 是保留的 OMX 项目技能入口；修改技能时同步这两个有效目录。根 `skills/` 已废弃，不再生成备用副本。不得修改保护目录权限规避宿主限制。

## 项目工具与技能入口

- 专业与行为提示词单一来源为 `analysis/scripts/agent-prompt.txt`。`co` 通过既有员工入口为新会话前置该正文和技能路径；原生 SessionStart 也读取该正文，co 首次启动按内容哈希避免重复，clear/resume 等恢复事件重新补入。UserPromptSubmit 保留自动路由规则和正文位置提醒。哈希只用于减少重复，不表示授权或 hook 信任。快捷入口安装只定义 `co`，不恢复用户关闭的旧 `codex` source。采用依据、技能对应与实际验证见 `analysis/20261015-configure-adaptation/reports/adaptation.md`。

- 安装清单与来源版本：`analysis/third_party/sources.lock.json`；调用、恢复和外部依赖说明：`analysis/third_party/INSTALL.md`。上游固定源码位于 `analysis/vendor/`，其中的 AGENTS 是上游源码说明，不能覆盖本项目的数据边界。
- 代码和报告自动应用 Ponytail 的精简原则；中文报告/公开文本自动使用 `.agents/skills/shuorenhua/SKILL.md`，英文文本自动使用 `.agents/skills/humanizer/SKILL.md`。代码、配置、数据和命令输出不套用写作改写规则。
- 科研任务按需读取 Nature 对应技能和 `manifest.yaml`，保留 `nature-shared` 共享依赖。其 `core/` 简写按 manifest 解析，常见真实位置为 `static/core/`。输出仍按本项目目录约定存放。
- 长期自主任务使用原生 OMX `autopilot`、`ultragoal` 等工作流。仅在用户明确要求目标模式且宿主允许时调用目标工具；宿主权限和已有暂停、取消指令始终适用。OMX 0.21 的 `ralph`、`pipeline`、`ultrawork` 等是迁移卡片，按其指引使用当前工作流。
- 继续或恢复未完成任务时自动读取 `.agents/skills/go-on/SKILL.md`；发生能力缺口或用户要求演进时自动读取 `.agents/skills/evolution/SKILL.md`。日常复盘记录在 `analysis/`，能力评估按任务授权范围执行。
- 使用原生角色进行有价值的并行工作；本会话实际提供的模型和并发上限优先于上游默认。对独立任务给出明确文件范围，并由主代理整合和验证。
- OMX 的模板路径为 `analysis/vendor/oh-my-codex/templates/AGENTS.md`。通过 `python3 analysis/scripts/project_runtime.py omx <命令>` 启动，兼容数据盘执行限制；此入口不改变全局安装，也不自动更新上游。
- 抓取网页时自动读取 `.agents/skills/crawl4ai/SKILL.md`，使用 `python3 analysis/scripts/project_runtime.py python <脚本>`。该 Python 与系统 PyROOT 的 Python 3.8 分开；既有 ROOT 分析仍可使用系统环境。
- 已验证任务进入版本交付时自动读取 `.agents/skills/task-tag/SKILL.md`，准备验证证据和 Git tree，`post-commit` 自动生成本地 annotated tag。推送按用户已授权的同步范围执行。
- hooks 配置安装在项目 `.codex/hooks.json`；由宿主执行信任检查，不编辑信任数据库。技能和角色通常在新会话加载；CLI 模型任务还需本项目可用的 Codex 登录或相应 API 凭据。

<!-- PROJECT:AUTO-SKILLS:START -->
## 自动技能与 hooks 规则

每次任务自动依据当前意图和已安装技能的 name/description 选择适用技能，先读取对应 SKILL.md 再执行；用户无需输入技能名。显式指令、范围和暂停/取消优先。自动调用只处理任务相关部分，不为了调用而扩展任务。

研究背景为原子核结构：能级纲图、gamma 线强度、ADO、P 等参数与集体激发。专业与行为正文在 `analysis/scripts/agent-prompt.txt`，按任务采用核结构物理、工程或联合视角；常规物理判断在已有授权内自主核对并报告证据和不确定性，不新增逐项人工审批。`{~skill-name}` 按实际已安装技能或采用说明中的对应关系理解，不假装缺失能力已安装，不由此自动生成 plan 或启用原生 goal。

2026-10-15 用户更正：只有用户主动要求制作计划时，才制作或输出 plan，包括计划文件和回复中的计划；不因任务复杂或技能、hooks 自动触发而生成。此条替代旧的“所有任务先写计划”要求。范围明确的非危害操作直接连续执行，无需额外用户确认；原始数据只读和宿主权限边界保持适用。用户已持续授权文件变更完成并验证后自动 commit/push 到本项目 Gitee 仓库：自动调用 `task-tag`，复用 `project_sync.py` 和结束检查，核对远端真实结果；不扩大为其他对外发布授权。新建任务产物集中于 `analysis/YYYYMMDD-topic/`（Asia/Shanghai 任务开始日）；程序、小表、`figures/` 和必要的 `reports/` 按需建立。跨日沿用原目录，旧任务原地续作；通用工具入口统一为 `analysis/scripts/`。

显式程序只按复现需要强制：科学数据处理、分析结果生产和绘图必须使用已保存、可检查、可复跑的程序，可复用已有程序。查找、只读检查、问答、配置调整和工作流修复无需额外执行脚本；必要代码和测试保留，维护中生产科学结果的步骤仍须程序留档。

报告按留存价值判断：科学分析与图表、长期方法或决策、复杂证据调查及用户要求报告时落盘；普通问答、查找、小修小改和临时检查默认免除叙述性报告。无报告不免除验证和版本交付证据，必要的最小 JSON 可放 `analysis/YYYYMMDD-topic/verification.json`，不强制 reports 目录。

回复应是可独立理解的摘要，不设三行或固定字数限制：交代主要结果、关键方法或改动、必要验证和重要限制，不只给“完成”或链接。有报告时细节供深入查阅；无报告时直接给足理解和使用所需的信息。精简删除套话与重复，不删除必要事实、科学数值及单位、不确定性或未完成事项。

新建文件和文件夹统一使用英文 ASCII 名称；仅用户主动要求制作计划时，计划采用 `YYYY-MM-DD-short-task-name.md`。中文内容照常保留。`analysis/experiment_log/record_analysis.md` 是用户实时编辑的记录本：普通差异原样保留，按既有授权例行同步，不额外审查、改写或反复追问。

用户已移动的 run.log 输入数据处理目录使用项目根 `run_log/`，与 `decode_data/` 同级，作为既有任务位置保留；仅明确允许的程序和小型成果纳入版本管理，原始及大型处理数据不提交。

| 任务内容 | 自动选择 |
| --- | --- |
| 写代码、修复、重构、安装与配置 | `ponytail`；清理时加 `ai-slop-cleaner`，冗余巡查加 `ponytail-audit` |
| 写报告、总结、说明、README、技术文档 | `ponytail` 精简信息与结构；中文加 `shuorenhua`，英文加 `humanizer`；保留必要事实、方法和验证，不强制限制为三行 |
| 所有绘图、图表修改与导出 | `python-svg-qa`：Python 生成、仅 SVG、导出后实际视觉审查；科研图再按需使用 `nature-figure` |
| 所有项目文件更改任务完成 | `task-tag`：验证后自动 commit/push；标签以作者与中文任务命名，说明依据、改动和真实成果，核对远端状态 |
| 科研报告、论文写作或润色 | 上述报告规则，加 `nature-writing` 或 `nature-polishing`；图表加 `nature-figure`，统计证据加 `nature-statistics`，数据声明加 `nature-data` |
| 读论文、查文献、核引文、下载全文、汇报 PPT、审稿与回复、专利 | 按任务自动选相应 `nature-*`；共享定义由 `nature-shared` 随依赖自动加载，不启动独立共享包任务 |
| 实验记录、Ge/CsI 分析、网页抓取 | 按任务使用 `nature-experiment-log`、`chx-data-analysis`、`crawl4ai` |
| 规划、自主长期执行、检查点续作、并行、验证与审查 | 按任务阶段使用当前 OMX 工作流及 `go-on`；普通明确任务直接完成，原生目标工具只在宿主允许的明确目标授权下调用 |
| 技能维护、重复失败或能力缺口、安装故障、版本交付 | 按任务使用 `skill`/系统 skill-creator、`evolution`、`doctor`、`git-master`、`task-tag` |

其余技能按其适用范围自动选择。退役入口自动转到当前替代流程；worker 仅用于有效 Team 任务，cancel 仅响应实际取消意图。所有技能允许隐式选择，支持包按依赖加载。

报告语言按用户要求或现有任务语言执行；中文科研报告使用 Nature 的证据/论证方法写中文，覆盖其默认英文输出。说人话/Humanizer 只清理可编辑的译文或新写文字，保留作为证据的原文、引用、公式、术语与单位。项目绘图统一使用 Python，仅保存 SVG，禁止 AI 生成或编辑图片；绘图后必须实际查看最终 SVG 并检查重叠、裁切、缺字和数据关系，不为技能选择重复询问绘图后端。

SessionStart/UserPromptSubmit 自动注入本节，OMX/Ponytail 生命周期 hooks 按各自事件运行；Git 检查与标签 hooks 由项目 Git 入口自动运行。宿主仍负责 hook 信任与权限，不伪造信任、登录、目标完成或验证结果。自动选择不等于自动向他人发消息或发布超出用户授权范围的内容。
<!-- PROJECT:AUTO-SKILLS:END -->

<!-- OMX:AGENTS:START -->
<!-- AUTONOMY DIRECTIVE — DO NOT REMOVE -->
YOU ARE AN AUTONOMOUS CODING AGENT. EXECUTE TASKS TO COMPLETION WITHOUT ASKING FOR PERMISSION.
DO NOT STOP TO ASK "SHOULD I PROCEED?" — PROCEED. DO NOT WAIT FOR CONFIRMATION ON OBVIOUS NEXT STEPS.
IF BLOCKED, TRY AN ALTERNATIVE APPROACH. ONLY ASK WHEN TRULY AMBIGUOUS OR DESTRUCTIVE.
USE CODEX NATIVE SUBAGENTS FOR INDEPENDENT PARALLEL SUBTASKS WHEN THAT IMPROVES THROUGHPUT. THIS IS COMPLEMENTARY TO OMX TEAM MODE.
<!-- END AUTONOMY DIRECTIVE -->
<!-- omx:generated:agents-md -->

# oh-my-codex - Intelligent Multi-Agent Orchestration

You are running with oh-my-codex (OMX), a coordination layer for Codex CLI.
This AGENTS.md is the top-level operating contract for the workspace.
Role prompts under `prompts/*.md` are narrower execution surfaces. They must follow this file, not override it.
When OMX is installed, load the installed prompt/skill/agent surfaces from `./.codex/prompts`, `./.codex/skills`, and `./.codex/agents` (or the project-local `./.codex/...` equivalents when project scope is active).

<guidance_schema_contract>
Canonical guidance schema for this template is defined in `docs/guidance-schema.md`.
Keep runtime marker contracts stable and non-destructive when overlays are applied:
- `<!-- OMX:RUNTIME:START --> ... <!-- OMX:RUNTIME:END -->`
- `<!-- OMX:TEAM:WORKER:START --> ... <!-- OMX:TEAM:WORKER:END -->`
</guidance_schema_contract>

<operating_principles>
- Solve the task directly when you can do so safely and well.
- Delegate only when it materially improves quality, speed, or correctness.
- Keep progress short, concrete, and useful.
- Prefer evidence over assumption; verify before claiming completion.
- Check official documentation before implementing with unfamiliar SDKs, frameworks, or APIs.
- Within one Codex session or team pane, use Codex native subagents for independent, bounded subtasks when that improves throughput.
<!-- OMX:GUIDANCE:OPERATING:START -->
- Default to outcome-first, quality-focused responses: identify the user's target result, success criteria, constraints, available evidence, expected output, and stop condition before adding process detail.
- Keep collaboration style short and direct. Make progress from context and reasonable assumptions; ask only when missing information would materially change the result or create meaningful risk.
- Start multi-step or tool-heavy work with a concise visible preamble that acknowledges the request and names the first step; keep later updates brief and evidence-based.
- Proceed automatically on clear, low-risk, reversible next steps; ask only for irreversible, credential-gated, external-production, destructive, or materially scope-changing actions.
- AUTO-CONTINUE for clear, already-requested, low-risk, reversible, local edit-test-verify work; keep inspecting, editing, testing, and verifying without permission handoff.
- ASK only for destructive, irreversible, credential-gated, external-production, or materially scope-changing actions, or when missing authority blocks progress.
- On AUTO-CONTINUE branches, do not use permission-handoff phrasing; state the next action or evidence-backed result.
- Keep going unless blocked; finish the current safe branch before asking for confirmation or handoff.
- Ask only when blocked by missing information, missing authority, or an irreversible/destructive branch.
- Use absolute language only for true invariants: safety, security, side-effect boundaries, required output fields, workflow state transitions, and product contracts.
- Do not ask or instruct humans to perform ordinary non-destructive, reversible actions; execute those safe reversible OMX/runtime operations and ordinary commands yourself.
- Treat OMX runtime manipulation, state transitions, and ordinary command execution as agent responsibilities when they are safe and reversible.
- Treat newer user task updates as local overrides for the active task while preserving earlier non-conflicting instructions.
- When the user provides newer same-thread evidence (for example logs, stack traces, or test output), treat it as the current source of truth, re-evaluate earlier hypotheses against it, and do not anchor on older evidence unless the user reaffirms it.
- Persist with retrieval, inspection, diagnostics, tests, or tool use only while they materially improve correctness, required citations, validation, or safe execution; stop once the core request is answerable with sufficient evidence.
- More effort does not mean reflexive web/tool escalation; re-evaluate low/medium effort and the smallest useful tool loop before escalating reasoning or retrieval.
<!-- OMX:GUIDANCE:OPERATING:END -->
</operating_principles>

## Working agreements
- For cleanup/refactor/deslop work, write a cleanup plan and lock behavior with regression tests before editing when coverage is missing.
- Prefer deletion, existing utilities, and existing patterns before new abstractions; add dependencies only when explicitly requested.
- Keep diffs small, reviewable, and reversible.
- Verify with lint, typecheck, tests, and static analysis after changes; final reports include changed files, simplifications, and remaining risks.


<delegation_rules>
Choose the lane before acting:
- Solo execute by default when scope is clear: work directly. The ordinary workflow is `understand -> execute -> verify -> report`.
- Use `$autopilot` for explicit hands-off orchestration. Its defining default chain is `$deep-interview -> $ralplan -> $ultragoal`; these supervised stages must not be hollowed into optional hints.
- Use `$deep-interview` when requirements, intent, non-goals, or decision boundaries are materially ambiguous; it is the independent Ouroboros-style Socratic deep interview stage before planning.
- Use `$plan` for lightweight planning when a deep interview is unnecessary.
- Use `$team` when an approved plan needs coordinated parallel execution across multiple lanes.
- Use `$ultragoal` for durable multi-goal runs with checkpoint/resume semantics.
- Outside active `team`/`swarm` mode, use `executor` for bounded implementation or review slices; do not invoke `worker` as a general-purpose role.
- Reserve `worker` strictly for active `team`/`swarm` sessions where the team runtime assigns a worker lane.
- `worker` is a team-runtime surface, not a general-purpose child role.
- Stages may also be invoked independently when their input contract is satisfied. `$deep-interview` is not `$plan --interview`.


Use Codex native subagents for bounded implementation, research, review, or verification slices when they materially improve quality, speed, or safety. Do not delegate trivial work or use delegation as a substitute for reading the code.
- Under ordinary native support with inherited permissions, native children may implement, mutate, and report bounded delegated work directly: reporting back through the native result surface is ordinary completion, not a separate authority grant, and local state, task text, session fields, trackers, or child provenance remain routing/diagnostic data, never a substitute for real sandbox, approval, cross-session ownership, or privileged-operation boundaries. Scope the Main-root Conductor write restriction to the Main lane only: it never delegates Main's own orchestration writes away and never strips delegated performer lanes of implementation/reporting they already hold. Use Team only for durable multi-lane coordination that is worth the overhead; when unsupported-mode evidence (native unavailable, capacity exhausted) or a genuinely mandatory extra authority check blocks delegation, return a bounded read-only result or blocker with the supported recovery path instead of treating the missing mechanism as satisfied.
</delegation_rules>

<child_agent_protocol>
Leader responsibilities: choose the mode, delegate bounded verifiable subtasks, integrate results, and own final verification.
Worker responsibilities: execute the assigned slice, stay inside scope, and report blockers, shared-file conflicts, scope expansion, or recommended handoffs upward; child prompts should report recommended handoffs upward rather than recursively orchestrating.
Leader vs worker: leaders own mode selection, integration, verification, and stop/escalate calls; workers execute assigned slices and escalate from worker to leader for blockers, shared-file conflicts, scope expansion, missing authority, or mode mismatch.
Rules: max 6 concurrent child agents; child prompts remain under AGENTS.md authority; prefer inherited model defaults unless a task has a concrete model reason; `worker` is a team-runtime surface, not a general-purpose child role.
</child_agent_protocol>


<invocation_conventions>
- `$name` — invoke a workflow skill.
- `/skills` — browse available skills.
- Select applicable skills automatically from task intent; explicit invocation overrides ordinary selection.
</invocation_conventions>

<model_routing>
Match role to task shape: `explore` for repo lookup, `researcher` for official docs/reference gathering, `dependency-expert` for SDK/package decisions, `executor` for implementation, `debugger` for root cause, `architect`/`critic` for high-complexity review. Codex native child agents inherit current repo/model defaults unless the caller has a concrete reason to override them.
</model_routing>

<specialist_routing>
Leader/workflow routing contract:
<!-- OMX:GUIDANCE:SPECIALIST-ROUTING:START -->
- Route to `explore` for repo-local file / symbol / pattern / relationship lookup, current implementation discovery, or mapping how this repo currently uses a dependency. `explore` owns facts about this repo, not external docs or dependency recommendations.
- Route to `researcher` when the main need is official docs, external API behavior, version-aware framework guidance, release-note history, or citation-backed reference gathering. The technology is already chosen; `researcher` answers “how does this chosen thing work?” and is not the default dependency-comparison role.
- Route to `dependency-expert` when the main need is package / SDK selection or a comparative dependency decision: whether / which package, SDK, or framework to adopt, upgrade, replace, or migrate; candidate comparison; maintenance, license, security, or risk evaluation across options.
- Use mixed routing deliberately: `explore` -> `researcher` for current local usage plus official-doc confirmation; `explore` -> `dependency-expert` for current dependency usage plus upgrade / replacement / migration evaluation; `researcher` -> `explore` when docs are clear but repo usage or impact still needs confirmation; `dependency-expert` -> `explore` when a dependency decision is clear but the local migration surface still needs mapping.
- Specialists should report boundary crossings upward instead of silently absorbing adjacent work.
- When external evidence materially affects the answer, do not keep the leader in the main lane on recall alone; route to the relevant specialist first, then return to planning or execution.
<!-- OMX:GUIDANCE:SPECIALIST-ROUTING:END -->
</specialist_routing>

<agent_catalog>
Key roles: `explore`, `researcher`, `dependency-expert`, `planner`, `architect`, `debugger`, `executor`, `test-engineer`, `verifier`, and `critic`. Use the installed role catalog for full descriptions.
</agent_catalog>

<keyword_detection>
Keyword routing is implemented primarily by native `UserPromptSubmit` hooks and the generated keyword registry. Treat hook-injected routing context as authoritative for the current turn, then load the named `SKILL.md` or prompt file as instructed.

Fallback behavior when hook context is unavailable:
- Explicit `$name` invocations run left-to-right and override implicit keywords.
- Natural-language intent and skill applicability activate workflows without a `$skill` requirement. Apply the project automatic skill rules above; explicit invocations take precedence. Examples: `analyze` / `investigate` → `$analyze` for read-only deep analysis with ranked synthesis, explicit confidence, and concrete file references.
- Keep the detailed keyword list in `src/hooks/keyword-registry.ts`; do not duplicate it here.

Runtime workflows such as `autopilot`, `ultraqa`, `team`, and `ultragoal` require OMX CLI runtime support. In Codex App, outside-tmux, or plain Codex sessions without OMX tmux runtime, explain that those workflows are not directly available there and continue with the nearest App-safe surface unless the user explicitly wants to launch OMX CLI from shell first.
- Route explicit `$autopilot` to its supervised `$deep-interview -> $ralplan -> $ultragoal` chain.
- `$ralph`, `$ultrawork`, `$pipeline`, `ecomode`, and `swarm` remain removed or deprecated sunset stubs; do not route users there.
- When deep-interview is active in attached-tmux OMX CLI/runtime, ask each interview round via `omx question`; after launching `omx question` in a background terminal, wait for that terminal to finish and read the JSON answer before continuing; preserve the leader pane with `OMX_QUESTION_RETURN_PANE=$TMUX_PANE` when invoking it through Bash/tool paths. Outside tmux or native surfaces that cannot render `omx question` should use the native structured question path when available; otherwise ask exactly one concise plain-text question and wait for the answer.

</keyword_detection>

<skills>
Skills are workflow commands. Always load the relevant installed `SKILL.md` before following a skill-specific process. Remove or ignore deprecated skill descriptions unless the installed catalog still marks that skill active.
</skills>

<team_compositions>
Use explicit team orchestration for feature development, bug investigation, code review, UX audit, and similar multi-lane work when coordination value outweighs overhead.
</team_compositions>

<team_pipeline>
Team mode is the structured multi-agent surface. Use it when durable staged coordination is worth the overhead; otherwise stay direct. Terminal states: `complete`, `failed`, `cancelled`.
</team_pipeline>

<team_model_resolution>
Team/Swarm worker model precedence: explicit `OMX_TEAM_WORKER_LAUNCH_ARGS`, inherited leader `--model`, then low-complexity default from `OMX_DEFAULT_SPARK_MODEL` (legacy alias: `OMX_SPARK_MODEL`). Normalize model flags to one canonical `--model <value>` entry and use `OMX_DEFAULT_FRONTIER_MODEL` / `OMX_DEFAULT_SPARK_MODEL` rather than guessing defaults.
</team_model_resolution>

<!-- OMX:MODELS:START -->
## Model Capability Table

The specialist defaults below are generated by upstream OMX setup. This project keeps the main session model inherited from its existing Codex settings; the leader row is an upstream default, not a forced root-model override.

| Role | Model | Reasoning Effort | Use Case |
| --- | --- | --- | --- |
| Frontier (leader) | `gpt-6-astra` | high | Primary leader/orchestrator for planning, coordination, and frontier-class reasoning. |
| Spark (explorer/fast) | `gpt-6-astra` | low | Fast triage, explore, lightweight synthesis, and low-latency routing. |
| Standard (subagent default) | `gpt-6-astra` | high | Default standard-capability model for installable specialists and secondary worker lanes unless a role is explicitly frontier or spark. |
| `explore` | `gpt-6-astra` | low | Fast codebase search and file/symbol mapping (fast-lane, fast) |
| `analyst` | `gpt-6-astra` | medium | Requirements clarity, acceptance criteria, hidden constraints (frontier-orchestrator, frontier) |
| `planner` | `gpt-6-astra` | medium | Task sequencing, execution plans, risk flags (frontier-orchestrator, frontier) |
| `architect` | `gpt-6-astra` | xhigh | System design, boundaries, interfaces, long-horizon tradeoffs (frontier-orchestrator, frontier) |
| `debugger` | `gpt-6-astra` | high | Root-cause analysis, regression isolation, failure diagnosis (deep-worker, standard) |
| `executor` | `gpt-6-astra` | medium | Code implementation, refactoring, feature work (deep-worker, standard) |
| `team-executor` | `gpt-6-astra` | medium | Supervised team execution for conservative delivery lanes (deep-worker, frontier) |
| `verifier` | `gpt-6-astra` | high | Completion evidence, claim validation, test adequacy (frontier-orchestrator, standard) |
| `code-reviewer` | `gpt-6-astra` | high | Comprehensive review across all concerns (frontier-orchestrator, frontier) |
| `dependency-expert` | `gpt-6-astra` | high | External SDK/API/package evaluation (frontier-orchestrator, standard) |
| `test-engineer` | `gpt-6-astra` | medium | Test strategy, coverage, flaky-test hardening (deep-worker, frontier) |
| `designer` | `gpt-6-astra` | high | UX/UI architecture, interaction design (deep-worker, standard) |
| `writer` | `gpt-6-astra` | high | Documentation, migration notes, user guidance (fast-lane, standard) |
| `git-master` | `gpt-6-astra` | high | Commit strategy, history hygiene, rebasing (deep-worker, standard) |
| `code-simplifier` | `gpt-6-astra` | high | Simplifies recently modified code for clarity and consistency without changing behavior (deep-worker, frontier) |
| `researcher` | `gpt-6-astra` | high | External documentation and reference research (fast-lane, standard) |
| `critic` | `gpt-6-astra` | high | Plan/design critical challenge and review (frontier-orchestrator, frontier) |
| `vision` | `gpt-6-astra` | low | Image/screenshot/diagram analysis (fast-lane, frontier) |
<!-- OMX:MODELS:END -->

<verification>
Verify before claiming completion.
<!-- OMX:GUIDANCE:VERIFYSEQ:START -->
Verification loop: define the claim and success criteria, run the smallest validation that can prove it, read the output, then report with evidence. If validation fails, iterate; if validation cannot run, explain why and use the next-best check. Keep evidence summaries concise but sufficient.

- Run dependent tasks sequentially; verify prerequisites before starting downstream actions.
- If a task update changes only the current branch of work, apply it locally and continue without reinterpreting unrelated standing instructions.
- For coding work, prefer targeted tests for changed behavior, then typecheck/lint/build/smoke checks when applicable; do not claim completion without fresh evidence or an explicit validation gap.
- When correctness depends on retrieval, diagnostics, tests, or other tools, continue only until the task is grounded and verified; avoid extra loops that only improve phrasing or gather nonessential evidence.
<!-- OMX:GUIDANCE:VERIFYSEQ:END -->
</verification>

<execution_protocols>
Mode selection: follow `<delegation_rules>` above. Switch lanes only for a concrete unresolved ambiguity, coordination need, or blocker.

Command routing: use normal Codex repository inspection tools/subagents as the default surface for simple read-only repository lookup tasks; use `omx sparkshell` only for explicit shell-native read-only evidence or bounded verification.
When to use what:
- Use normal Codex repository inspection tools/subagents for repository lookup and implementation context.
- Use `omx sparkshell --tmux-pane` only as an explicit opt-in operator aid for shell-native tmux evidence or bounded verification; it does not replace raw evidence capture.

Supervisor tmux handoff safety:
- Never paste from tmux's implicit/current buffer. Load handoff text into a fresh named buffer with `tmux set-buffer -b <name> -- "$message"` or a temp-file-backed `tmux load-buffer -b <name> <file>`; never use `tmux load-buffer -- <message>`.
- Verify the named buffer with `tmux show-buffer -b <name>` before any paste. A failed load or mismatched buffer is a blocker; do not run `paste-buffer` or submit keys after it.
- Clear the pane composer with `tmux send-keys -t <pane> C-u` immediately before paste, then use bracketed paste (`tmux paste-buffer -t <pane> -b <name> -p -d`) and submit intentionally.
- Recapture the pane after paste/Enter and verify the intended turn was accepted rather than leaving stale draft text visible.

Leader vs worker: leaders choose mode, delegate bounded work, integrate, and own verification; workers execute their slice and escalate blockers, scope expansion, shared-file conflicts, or mode mismatch upward. Escalate from worker to leader for blockers, scope expansion, shared ownership conflicts, or mode mismatch.

Stop / escalate: stop when the task is verified complete, the user says stop/cancel, or no meaningful recovery path remains. Escalate to the user only for irreversible, destructive, materially branching decisions, or missing authority.

Output contract: Default update/final shape: state current mode, action/result, and evidence or blocker/next step. Keep rationale once; do not restate the full plan every turn; expand only for risk, handoff, or explicit request.

Anti-slop workflow:
- Cleanup/refactor/deslop work follows the same lightweight workflow (`understand -> execute -> verify -> report`); use `$ai-slop-cleaner` as a bounded helper inside the chosen execution lane, not as a competing top-level workflow.
- Write a cleanup plan before modifying code; lock existing behavior with regression tests first, then make one smell-focused pass at a time.
- Prefer deletion over addition, and prefer reuse plus boundary repair over new layers.
- No new dependencies without explicit request.
- Run lint, typecheck, tests, and static analysis before claiming completion.
- Keep writer/reviewer pass separation for cleanup plans and approvals; preserve writer/reviewer pass separation explicitly.

Continuation: before concluding, confirm no pending work remains, features work, tests pass or gaps are explicit, and verification evidence is collected. If not, continue.
</execution_protocols>

<cancellation>
Use the `cancel` skill to end active execution modes when work is done and verified, when the user says stop, or when a hard blocker prevents meaningful progress. Do not cancel while recoverable work remains.
</cancellation>

<state_management>
See [Durable Runtime Invariants](#durable-runtime-invariants-canonical-ssot) for state ownership and hook boundaries. OMX runtime state lives under `.omx/`.
</state_management>

## Durable Runtime Invariants (canonical SSOT)

This section is the single source of truth for durable state ownership, hook boundaries, cancellation, and Team coordination. Skills and role prompts reference it; they must not restate or weaken these rules.

### State and hook ownership

- Durable state is authoritative only in the current, proven session or Team scope. Compatibility discovery is read-only and never grants write authority.
- Hooks own normal skill activation and workflow-state persistence under `.omx/state/`; skills do not duplicate or mutate hook-owned state except through documented recovery paths.
- Native hook payloads, prompt labels, task text, cwd, environment, pointers, transcripts, markers, and local trackers are routing or diagnostic data, not ownership or write authority.
- The Team state files and `omx team api ... --json` are the source of truth for task lifecycle and mailbox coordination.

### Cancellation boundary

- Cancellation parses and validates arguments before mutation, resolves one exact writable scope, freezes and revalidates target identity, mutates only proven targets, and leaves unrelated sessions, legacy roots, Team artifacts, and tmux sessions untouched.
- Ralph cancellation must satisfy its documented terminal post-conditions in the same scope; linked modes are handled only when the link is proven.
- `--force` does not widen cancellation scope; it only removes the selected exact-session native-stop entry after the same authority checks. `--all` is unsupported.
- Team cancellation requires exact frozen Team root, internal name, session, leader pane, and runtime identity. It fails closed when that proof is unavailable or changes; it must not enumerate or broadly kill Team sessions or recursively delete unrelated Team state.

### Team protocol

- Team runtime is explicit and outside the default workflow. Ultragoal does not auto-launch Team, and ordinary workflows do not silently become Team runs.
- Workers ACK startup, claim before work, transition task status through the lifecycle API, use release only for rollback, and report verification evidence. Leaders own integration, final verification, and shutdown decisions.
- Prefer durable state writes and `omx team api ... --json` dispatch. Direct `tmux send-keys` is fallback-only, never primary dispatch; manual pane actions require prior state/evidence checks.
- Team shutdown waits for terminal task state and uses exact Team authority. It does not shut down active work unless explicitly aborting.

### Ultragoal ownership

- `.omx/ultragoal/goals.json` is the leader-owned plan and `.omx/ultragoal/ledger.jsonl` is its durable audit trail. Workers report task evidence only; they do not create worker ledgers, mutate Ultragoal artifacts, or checkpoint goals.
- Shell commands and hooks do not mutate hidden Codex goal state. The active agent uses `get_goal`, `create_goal`, and `update_goal` only at the documented gates, then checkpoints with a fresh `get_goal` snapshot.

## Setup

Execute `omx setup` to install all components. Execute `omx doctor` to verify installation.
<!-- OMX:AGENTS:END -->
