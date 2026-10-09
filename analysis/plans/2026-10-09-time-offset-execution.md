# 执行计划：time offset第一阶段

- 创建日期：2026-10-09（Asia/Shanghai）；承接原任务和 `time_offset/`，不另建科学产物目录。
- 状态：Deep Interview交接完成，Ralplan第二轮Planner→Architect→Critic已批准；Ultragoal G001工程基础和G002历史有限标定完成；G003为review_blocked，G004新版真实批次strict mission通过，得到103条组—通道记录；最终报告序列化回归、Code Reviewer APPROVE及Architect CLEAR已通过；整合与版本交付仍进行中。旧108条历史记录不并入新版。
- 实际授权：用户本轮明确 `$autopilot $autoresearch 开始执行计划analysis/plans/process/20261008-time-offset.md`。此指令解除此前“暂不实现”的阶段限制，仅授权执行该计划的第一阶段；下一阶段批量decode仍不执行。

## 目标与边界

交付可编译的 `time_offset/time_offset.cc`、`time_offset.hh`，读取真实decode ROOT的五分支，配对填2／24ns谱、ROOT拟合和背景／峰位估计、量化offset、输出ROOT回查、offset CSV、分组crate配置及必要报告。实际研究结果用明确验证器及独立时间块校验，不能以模型口头判断结束。

原始Ge／CsI、他人的software、原DecodeAndSortAll源码、编译文件和原crate配置继续只读；实时实验记录本不修改。root管理入口只做计划、工作流、独立克隆协调和串行整合，实施者使用独立普通Git克隆及明确文件范围，不假称宿主cwd／沙箱已迁移。

## 输入与已确定方法

- 科学依据：`analysis/plans/process/20261008-time-offset.md`及decisions目录的三份当前相关记录。
- 输入：`decode_data/`当前14个ROOT（6015、6019、6024、6028、6035、6041、6045、6050、6054、6061、6065、6071、6075、6078）；读取最新tree周期和 `ts,cid,sid,ch,sr`。
- 参考(0,2,5)，cid只留0／1、sid>=2；time tick=8／10ns；Delta=reference−channel；初始窗±1999ns；2ns主计数定位、24ns识峰／拟合候选；各估值来源分别记录。
- 候选组A=6015–6029、B=6030–6051、C=6052–6079，最终配置按真实跨run／时间块证据合并或细分。对弱峰、不可辨背景及异常段明确未确定，不补造offset。
- Gaussian／侧带模型及参数先有限样本确认；拟合质量、实际生效修正、残差和±100／200／300ns半宽回查全部留证据。无SVG或Python分析程序，ROOT供回查。

## 产物与执行阶段

| 位置 | 用途 |
| --- | --- |
| `.omx/context/`、`.omx/interviews/`、`.omx/specs/` | 短上下文、Deep Interview真实需求交接、Autoresearch使命及评估器 |
| `.omx/plans/` | Planner草案、顺序Architect→Critic审查和同轮handoff |
| `.omx/ultragoal/` | 正式运行生成的目标和checkpoint账本，不手写伪造完成 |
| `time_offset/` | cc／hh、真实ROOT直方图／拟合、CSV、分组crate和report.md；编译及ROOT留本地 |
| `analysis/20261008-time-offset-design/` | 本任务已有维护验证目录，保存可复跑验收和实际证据，跨日沿用 |

1. 按显式技能完成真实Deep Interview阶段：先事实和既有回答交接，压力检查剩余验收／未确定项边界，一次一问，不重复确定的物理设置。Autoresearch采用且只采用一种验证模式，默认建议mission-validator-script。
2. 保持Autopilot父状态，调用原生Planner→Architect→Critic顺序审查；本会话已提供真实agent_type路由，不调用不适用的adapted领导证明，也不拿本地文件当宿主权限。
3. 进入批准handoff后的Ultragoal：用官方命令生成durable goals，再按宿主工具实际状态启动goal。通过session_coordinator创建独立实施目录，源文件／验收文件范围显式分配。
4. 先保存源码，编译并做正负量化、混合tick、跨块／跨run配对、缺失参考／异常时间等小型检查，再对代表ROOT有限样本分析。根据真实谱决定侧带、峰区和可校准通道；统计不足有界扩大样本，参数每次改变留记录。
5. 用固定候选在留出时间块／独立run核验，完成研究验证器及必要回查；导出各组配置，未确定项单列。不开原decoder，不调度批量decode。
6. 执行必要清理和独立code-reviewer／architect最终审查；只有真实产物及验收齐备才终结目标／工作流。员工冻结提交与outbox，控制端真实沙箱串行整合，按既有授权同步Gitee，不强推。

## 完成标准、风险与恢复

- 可复跑编译／自检和研究结果验证器明确，不使用TODO或虚构command作为通过证据；ROOT与CSV／crate逐项一致，参考offset为0。
- 跨run不配对，异常时间不推进正常缓存；未知／弱信号不作为已证实0 offset；原始输入及原decoder／crate不变。
- 各group闭区间可追溯且覆盖目标编号范围，异常／缺失run的实际处理状态单列；不预设哪机箱一定稳定。
- 历史交付故障：前一文档提交356b72c曾因三次push超时未同步，当时远端为048c3e5；该状态仅是历史检查点。主代理已确认后续政策小成果996bb58实际推送且根目录刷新完成。本科学任务尚未冻结交付，不以政策同步代替本任务远端核验。
- 无可用工作流／真实沙箱／网络时保留真实状态与成果，使用受支持恢复路径，不伪造权限、角色、验证或完成。
- 实际用户边界确认：无可靠峰／背景通道保留原配置并标记未校准，继续其余通道；只把独立验证通过的通道称为校准成果。用户已选择按此边界启动，并多次要求继续。
- 工作流恢复：官方宿主doctor确认会话pointer usable，坏selector为CODEX_SESSION_ID；仅在官方状态命令中清除该selector。保留pointer，不凭隔离PID视图清理会话。Deep Interview完整spec／用户答复已存，补齐gate.status／spec_path字段，不伪造宿主权限。
- 共识进度：Planner三份文件位于.omx/plans；Architect初两次因模型容量失败，后续完成真实顺序审查。第二轮Architect与Critic均为APPROVE，交接证据为`.omx/plans/time-offset-consensus-handoff.json`；该文件仅是流程证据，不代替宿主权限。
- 当前下一步：由主控安全更新员工基线、冻结并串行整合成果，再核验本任务远端交付。新版[8M,12M)批次、最终回归与独立审查已通过；只读重算，不重开已消费留出，不改统计／参数。

## 本轮文档与工程检查点

- 文档员工在独立普通克隆 `time-offset-docs-20261009` 工作，只更新本计划、[科学处理计划](process/20261008-time-offset.md)、[程序决策](../../decisions/20261009-time-offset-program.md)及独立文档验证记录`analysis/20261008-time-offset-design-docs/verification.json`（主代理已追加登记）。先保留主目录两份计划的最新未提交内容，再更新执行状态和批准规则；不写代码、科学结果、实验记录本或工作流账本。
- G001依据代码员工的 `time_offset/report.md`：ROOT 6.34.08、g++ 9.4.0编译通过，`-O2 -Wall -Wextra -Wpedantic`无警告；`bash analysis/20261008-time-offset-design/validate_execution.sh`通过24项合成自检。覆盖混合tick、正负量化、chunk等价、跨run／slice隔离、异常整块拒绝、保护区、最新tree周期及诊断ROOT篡改拒绝。测试输入是synthetic，不是实验结果。
- G001诊断验收只证明谱结构、整数计数、细粗谱重算和invalid零贡献。后续G002历史批次已有数值／模板重算，但G003审查发现双峰候选比较及时间桶组织未覆盖原合同，故旧验收不能代替G004最终验收。
- 数字质控、冻结留出和完整模板保护以科学处理计划新增执行规则为准。初值来自批准的代理方案，不是永久实验参数；探索调整先记理由，首次留出前冻结。未校准保留原配置，至少一个非参考目标独立通过才可称部分可用，全部unknown仅诊断。
- G004新批次及最终审查结论已由主代理回传；本lane验证后停止，等待主控安全更新基线并协调冻结、串行整合和远端核验，不自行提交范围外文件。
- 文档验收：三份文档本地相对链接逐项检查；18个既有数学块与主目录原文逐字一致；加入G004的4个公式后，全部22个数学块均使用主项目KaTeX严格解析渲染；`git diff --check`检查空白。实际命令、返回码与三文档内容摘要保存在上述独立验证记录，代码lane证据不改。该检查只验证文档链接、公式可渲染和范围，不验证科学结果。

## G004恢复检查点（实现前历史记录）

主代理确认G001／G002已完成历史有限样本阶段；旧 `time_offset/final-expanded/` 为108条组—通道记录（96 gamma、12 CsI），按组重复地址计数，不能称108个独立地址。G003审查阻断最终交付；安全报告写入和严格消费ledger已修复，代码员工记录24项工程、62项数值／模板／安全测试及旧结果只读重算通过，但科学合同仍待G004补齐。

G004方案与公式见[科学计划](process/20261008-time-offset.md)新增章节。训练及跨run留出均预定全新entry [8000000,12000000)，沿用既定训练／比较run及固定slice策略，不挑选历史各批次较好通道混合成新结果。原始输入、旧freeze与消费记录保留，未提供新批次实测成功数。文档更新仅记录实施约定，不表示实现已通过审查；实际命令、数值和失败证据继续集中到代码lane的 `time_offset/report.md`。

## G004新版结果与最终质量门

新版 `time_offset/final-candidates/` strict mission通过，三个组共103条组—通道：A为24 gamma；B为36 gamma＋8 CsI；C为32 gamma＋3 CsI，合计92 gamma＋11 CsI。不是103个独立物理地址；A的CsI没有通过，其余未知保持原配置。旧108条只作历史证据，不跨批次拼接。

训练解析出的双峰为A 7 gamma、B 10 gamma＋2 CsI、C 10 gamma，其余为single_or_unresolved；双峰识别数不是最终校准成功数。数值、逐run来源和候选明细集中在 `time_offset/final-candidates/` 与 `time_offset/report.md`。

最终24项工程、73项数值自检通过；独立QA为27命令／48断言通过，包括JSON五类特殊字符roundtrip。Code Reviewer在LOW序列化问题修复后为APPROVE；Architect实际源码审查为CLEAR，领域不变量及三个group只读重算通过，29个解析双峰的加权代数最大误差为2.14e-14ns。主控也独立重编译、自检并重算现103条mission通过。以上是科学与质量门证据，不表示版本推送完成。

最终源码摘要：cc `efff88f30da1362969a3f70222572af9ad4a23e50829a340938557c72b1f9941`，hh `febd8b8130884d36afd7bfb5b9b27b4f63fb15063d057ea9539fc668ed3dacf3`；真实数据由cc `ccc6edbf7cbb2e3b4e4f7ed81aecb833418cde0af08fb2d41b3af2553e11647c`生成，最终版本只修JSON序列化，不改统计／参数、不重开留出，已只读复算同一成果。文档算法已对照实际源码；机器验证证据保存所核对源码摘要。

限制与交付：结论仅覆盖本轮有限样本和通过质控的组—通道，不代表全部run／CsI或被拒绝slice完成对齐。未观测和未校准模板项保留原值。ROOT、freeze及manifest仍依赖员工绝对产物目录 `/home/ys/data_401/data/chx_20260622/.omx/coordination/workspaces/time-offset-impl-20261009/time_offset/final-candidates/`；整合后不能仅因源码已提交就声称产物可迁移重算。主控负责安全基线更新及后续整合，文档lane保留四文件验证完成状态，按本次指令不自行提交范围外政策或抢写远端成功。
