# time offset 第一阶段实施记录

## 当前正式成果：G004 v2

**主交付为 `final-candidates/`，实施及数值验收通过，等待主控完成独立QA、架构复审和版本整合。** 本批次在训练前固定weighted策略，使用此前未读取的entry [8M,12M)，没有把历史87或108项中的较好通道混入新结果。

| 组 | 训练run → 独立比较run | cid0通过 | cid1通过 | 已观测但未通过 | 未观测模板行 | 参考 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A | 6015 → 6019、6024、6028 | 24 | 0 | 120 | 271 | 1 |
| B | 6035 → 6045、6050 | 36 | 8 | 96 | 275 | 1 |
| C | 6054 → 6061、6065、6075、6078 | 32 | 3 | 118 | 262 | 1 |

合计103个组—通道记录，含92个cid0、11个cid1；不是103个独立物理地址。每组保留完整416模板行（每crate208行），只有全部指定比较run通过的预选候选改变offset；其余保留原offset和能量限。A的CsI仍全未校准，B/C也只部分通过。候选组编号区间不是对未取样run的校准证明；6041、6071未纳入本轮有限验证，6052硬件身份仍与A/B区分。原decoder/原crate未修改或运行，没有开展下一阶段decode。

关键产物：

- [A配置与状态](final-candidates/group_A/offsets.csv)、[B配置与状态](final-candidates/group_B/offsets.csv)、[C配置与状态](final-candidates/group_C/offsets.csv)，各同目录的crate0.dat/crate1.dat为候选配置。
- [真实输入、范围、最新tree cycle和共同时间轴](final-candidates/sources.csv)、[按crate的覆盖及失败原因](final-candidates/reasons.csv)。
- 每个 `frozen_*/frozen.root` 保存训练参数、区域、ROOT拟合和冻结候选；`physical_candidates.csv` 同时保存物理候选。每个 `validated_*/physical_candidates.csv` 与ROOT保存两候选的独立检验和严格半宽100/200/300ns净计数、误差。组目录CSV中的validation列仅对应第一个比较run，完整跨run数值见该组manifest指向的逐run表。

### 物理候选与共同时间轴

只有训练24ns双高斯满足status=0、covariance=3、不贴边、残差p>=0.01、峰距>=max(48ns,2倍较大sigma)，且两侧count区域各自通过数值质量时，才建立互不重叠的两峰区域。main取较高24ns峰所在区域的2ns净计数重心；weighted按两个区域的净面积加权，等于完整峰区净重心。两者的mu、误差、可生效offset、区域、策略和各半宽净计数均在首次holdout读取前冻结。无法可信分离时标single_or_unresolved，只保留overall，未虚构第二个峰；half-tick量化分支另行处理。

本批次训练形成29个可信分峰的组—通道：A为7个cid0，B为10个cid0和2个cid1，C为10个cid0。这是对有限训练谱的模型/计数判定，不是对双峰物理成因的确认。ROOT回查保存了拟合函数、结果及协方差；verifier从训练计数重算拟合残差、非重叠区域、净面积和候选，并重算冻结候选在holdout上的数值，不信任CSV状态文字。

例如B组 `(1,11,4)`：main训练中心 −75.049 ± 8.640 ns，offset −80 ns；weighted中心 −210.366 ± 8.961 ns，offset −210 ns。6045独立验证中，两者±100ns净计数分别为228.226 ± 15.740与203.226 ± 14.925；±200ns分别为342.282 ± 19.676与405.282 ± 21.217。6050也分别验证了同一冻结候选。不同半宽存在取舍，因此未用holdout选赢家；预先固定的weighted决定本次配置−210ns。详见 [B/6045两候选明细](final-candidates/validated_B_6045/physical_candidates.csv) 和 [B/6050明细](final-candidates/validated_B_6050/physical_candidates.csv)。

C采用80个预先固定的50k-entry slice：先全体只读预检，从有效core确定共同绝对时间边界，再将所有有效slice映射到同一组按时间顺序排列的16桶。slice和桶边缘都保留1999ns保护，缓存不跨slice，坏slice零贡献；完整all-pair双谱保留。训练6054为61有效/19拒绝；验证6061为60/20、6065为60/20、6075为63/17、6078为63/17。合成慢漂移反例证实旧“各slice第k块相加”能抵消漂移，而新有序桶能拒绝该反例。

各组CsI剩余限制仍以低统计为主：A的208行由103未观测、40无候选窗口、63侧带不足、2跨run缺失组成；B通过8行，其余有105未观测、5无窗口、69训练侧带不足、20验证侧带不足和1缺失；C通过3行，其余93未观测、15无窗口、96侧带不足和1验证背景不一致。没有降低门槛提高通过数。

### 验证、版本链与限制

真实生成程序的cc hash为 `ccc6edbf7cbb2e3b4e4f7ed81aecb833418cde0af08fb2d41b3af2553e11647c`（构建 `/tmp/time-offset-build.ivFgLt/`）。之后独立review发现失败reason需要JSON转义，当前cc hash为 `efff88f30da1362969a3f70222572af9ad4a23e50829a340938557c72b1f9941`；hh hash为 `febd8b8130884d36afd7bfb5b9b27b4f63fb15063d057ea9539fc668ed3dacf3`。后续变更仅为JSON序列化与3项失败报告测试，没有改科学算法、参数或重新读取真实holdout；主控已转达独立code-reviewer确认移除该差异后恢复原科学hash，并给出APPROVE。

最新实际验收：ROOT6.34.08/g++9.4.0无警告编译，24项工程与73项数值/模板/安全/候选测试通过；含引号、反斜杠、tab、CR、LF路径的失败报告经`python3 -m json.tool`独立解析通过；严格v2使命只读重算三组103项通过。构建 `/tmp/time-offset-build.IZEY2E/`，日志 `g004_json_fix_verification.log`。机器证据位于 `analysis/20261008-time-offset-design/completion.json` 和 `execution_verification.json`。本员工未提交outbox、未推送，也不自批最终QA/架构审查。

```bash
# 已有成果只读重算：
bash analysis/20261008-time-offset-design/validate_execution.sh --mission
# 原始新批次实际生成命令已记录在下方G004实施节；当前工作区不可重复消费已登记holdout。
```

mission/comparison清单使用绝对员工工作区路径：`/home/ys/data_401/data/chx_20260622/.omx/coordination/workspaces/time-offset-impl-20261009/time_offset/final-candidates/`。控制端应编译候选源码，再对该清单只读重算；源码、模板输入与ROOT产物的版本链保持原样。复制成果到根目录后，这些绝对清单仍依赖保留的员工目录，不能仅移动后宣称已独立重算。

结论限于列出的有限有效slice、计数背景/近似时间平稳性和预注册阈值。子块经验方差与Poisson传播取较大值，保留背景共享协方差，但不声称完整系统误差或严格覆盖率；四段侧带Pearson近似要求每段期望>=5。固定offset只平移双峰，不会消除峰距。本轮做了数值与ROOT对象回查，没有把它说成实际图形渲染审查。原始大ROOT未建立全文件前后哈希基线，证据为READ访问实现、输入元数据和冻结原模板逐行重算，不补造指纹证明。

## 历史实施与审查记录

下列G001–G003及v1结果保留恢复依据；其中87/108项和旧folded分桶均是历史，不是当前主交付。当前结果及版本以上文G004 v2为准。


## 实施计划与边界

状态：G001已由主代理复验；G002程序、有限真实数据与独立留出已完成本员工验收，扩量批次得到108个组—通道，其中12个CsI。待主代理独立审查和版本整合。早期阶段记录见下文，最终结论以“当前交付结果”节为准。
依据：主目录批准的 PRD/test-spec cycle 2，以及 20261008-time-offset 科学处理计划。用户已要求开始并继续第一阶段；本员工由主代理分配独立普通 Git 克隆，只改 time_offset/ 和 analysis/20261008-time-offset-design/。应用 chx-data-analysis、Ponytail 和说人话技能。原始数据、原 decoder、原 crate 只读。

1. 实现 time_offset.hh/cc：类型校验、有限区间流式 ROOT 读取、sr 对应 8/10 ns、连续 slice 边界、异常整块拒绝、核心参考保护区、所有候选对与 2/24 ns 双谱。
2. 同一 C++ 程序实现合成 ROOT 自检、诊断读取/对象重算验证入口。先编译并验证 G001；记录失败，不以合成结果当科学测量。
3. 后续 G002 在主代理检查点后开展有限真实样本；在同一程序完成格点背景、净计数重心、ROOT 拟合备选、冻结训练参数与独立留出、完整模板配置导出和严格 artifact 校验。

程序：time_offset/time_offset.hh、time_offset/time_offset.cc。
验收入口：analysis/20261008-time-offset-design/validate_execution.sh。
证据：analysis/20261008-time-offset-design/execution_verification.json；ROOT 与二进制本地忽略。
统计条件：Delta=reference-channel；ref=(0,2,5)；cid 0/1、sid>=2、ch 0..15；2 ns 1999 bins [-1999,1999] 与 24 ns 167 bins [-2004,2004]；仅 |Delta|<=1999 的相同候选对入谱。只在可达格点估计背景，误差与独立验证待后续实施核验，不预设成功数值。
验收标准：编译无错误；合成测试覆盖 chunk 等价、跨身份隔离、未来异常/回退/溢出整块拒绝、保护区、最新 tree cycle、未知 sr 和量化；真实数据及最终配置验收独立记录。
待确认事项：无新增用户确认；真实峰区、侧带和异常跳变上限须在探索后冻结，不能凭假设标定。

## G001 实际结果

ROOT 6.34.08、g++ 9.4.0 编译通过，`-O2 -Wall -Wextra -Wpedantic` 无编译警告。`bash analysis/20261008-time-offset-design/validate_execution.sh` 通过 24 项合成工程自检；暴力枚举候选对与流式结果逐 bin 相同，chunk=1/2/7/29/1000 相同；已覆盖回退、极大未来值、溢出、未知 sr、同 tick 混合 sr、两端保护、最新 tree cycle、跨调用/run/slice 缓存隔离、符号和 signed16、ROOT 2→24 ns 重算与篡改拒绝。测试失败 fixture 故意保留为 tampered.root，正常 fixture 单独保留。

最新编译证据目录：`/tmp/time-offset-build.emU8q1/`。机器证据见 `analysis/20261008-time-offset-design/execution_verification.json`。

合成 CLI 运行：
```bash
/tmp/time-offset-build.emU8q1/time_offset --scan --input /tmp/time-offset-build.emU8q1/self-test/synthetic.root --output time_offset/g001-diagnostic-v2.root --ge-run 1 --csi-run 1 --group synthetic --slice synthetic-cli --begin 0 --end 5 --core-begin 1 --core-end 4 --chunk 1 --max-gap-ns 1000000000
/tmp/time-offset-build.emU8q1/time_offset --verify-artifacts time_offset/g001-diagnostic-v2.root
```
结果：5 条合成 hit、1 个受保护核心参考、2 个候选对；诊断 ROOT 重算通过。输入 provenance 的 synthetic 标志传播到输出，不能作为实验结果。早期 g001-diagnostic.root 使用旧版本且 synthetic 标签未传播，已由 v2 替代；保留作开发检查点，不参与验收。

当前 CLI 的 `--scan` 按半开 entry 区间读取，先只读预检查整 slice 时间顺序和最大间隔，再二次流式配对；内存不随 slice hit 数增长，仅保留窗口缓存和小谱。`--max-gap-ns` 默认 1e9 ns 是工程初值，真实探索后必须冻结，不是已测物理界限。原输出存在即拒绝覆盖。

尚未完成：格点背景及相关误差、ROOT 拟合候选、冻结/留出、完整模板配置和覆盖率、最终科学数值重算；当前 `--verify-artifacts` 仅验证诊断谱结构、整数计数、细粗谱重算及 invalid 零贡献，不能当完整任务通过证据。没有真实 ROOT 科学处理，没有可用标定结论。G001 源码与自检可交接，下一步按主代理检查点进入 G002。

## G002 实施计划补充（实施前）

主代理已实际重跑 G001 并进入 G002。继续同一源码，不另建分析语言。

统计拟实现：保留全部候选对的原 2/24 ns 谱；另将 core 时间均分为 16 个子块，统计用参考在每个子块边缘各排除 1999 ns，保证相邻统计子块不共享候选目标 hit。统计谱为这些子块之和，原全候选谱不删计数。平背景仅在参考/目标 tick 的 gcd 可达格点估计；侧带同一估计值的协方差传播至净信号和重心。为避免把共享 hit 的配对数当独立 Poisson，使用子块净计数/重心线性化投影的经验方差，并取其与 Poisson 传播方差的较大值；保存原子块计数、两种方差和适用假设。独立子块的时间平稳性仍是统计假设，侧带不一致、子块中心不稳定或统计不足的通道不校准。

输入训练谱后写冻结 ROOT：模板原文、训练计数、参数、候选及预登记 holdout 文件/run/slice/read/core。只有 freeze 完成并通过重算才能打开 holdout；验证只应用冻结 offset，使用完全相同峰区与侧带估计用于中心检验。一次 freeze 只消耗一次 holdout，消费记录在读取前创建；拒绝相同文件读取范围重叠。参数调整必须重建 freeze 并指定新 holdout，原消费记录保留。

完整五列模板原序导出；参考零，非校准行逐字保留，已校准行只改第三列，signed16 和输出路径保护。最终 verifier 从 ROOT 训练/验证计数及冻结参数重算所有数值、校准集合、CSV 和模板输出；全 unknown 仅诊断。

以上是实现方法，不是已测结果。先合成数值/模板/篡改测试，再有限真实训练样本；实际峰区和背景范围在训练后记录并冻结。

G002 首轮合成数值/模板检查已通过：2026-10-09 实际运行验收脚本，24 项配对检查及 17 项数值/模板检查通过，合成训练与独立合成验证均获得预置 160 ns 对齐；synthetic 仍强制科学完成 false。检查包括 lattice 背景、子块协方差、12 个边界扰动、旧非零值与能量范围保留、混合 sr 不校准、CSV 篡改、冻结摘要篡改、留出重复使用、训练/留出范围重叠、模板重复地址/参考非零/signed16/覆盖输入拒绝。证据在 `/tmp/time-offset-build.YqGSuU/`。发现一处未使用函数编译警告，已删除；随后重编译。

真实初轮探索拟读：A run6015、B run6035、C run6054，各 entry [0,2000000)，core [10000,1990000)，chunk=100000，异常 max-gap=1e9 ns。不打开预定独立留出 run6028/6045/6061。预定窗口先由训练 24 ns 最大 bin 提供可审查建议（gamma ±240ns，CsI ±480ns，初始两侧带 [-1800,-1200]/[1200,1800]ns）；实际训练检查后才冻结，宽相关平台/背景不可信通道保持 unknown。这些范围是探索参数，不是已验证结论。

真实初轮读取结果：6015 的 2M 条目 slice 有效，73403 个核心参考、53347 对；6035 同范围有效，111356 核心参考、113200 对。6054 [0,2M) 在读取第160318条时发现时间回退，整个 slice 拒绝，最终0对；不调查异常根因，也不将异常后的恢复自动当可信段。按独立明确 slice 另试6054 [2M,4M)，core [2010000,3990000)，其余参数不变；该新 slice 仍必须完整预检查。

6054 的第二个独立 2M slice 也因时间回退拒绝（读取122740条，最终0对）。先将6054列为未取得有效训练 slice 的诊断输入；训练改为尚未读取的6061 [0,2M)，并把C留出预登记改为6065 [0,2M)。这不从失效块中截取恢复区，不修改时序异常判据，也不声称6054的配置已验证。

6061 的首2M也因回退拒绝（检查75375条）；未放宽判据。C改用预先固定的50000-entry网格覆盖同一[0,2M)训练预算，40个互不重叠slice各自完整预检，失效slice全弃，所有有效slice入谱，逐slice范围/错误位置/贡献对数随ROOT保存。此选择只基于固定网格，不能根据峰质量或某次异常位置剪切。统计子块在各有效slice内分别加保护，再按子块序号合并方差投影；原全候选谱只包含有效slice，不跨slice配对。先在6054上重试固定网格，6061可保留作额外比较，C留出6065仍未打开。

固定网格的6054训练通过：请求40个50k slices，实际检查1753424条（失效slice在异常处停止预检），有效slice合计85677个核心参考和87208对。所有slice状态保存在ROOT slice_log，不宣称所有2M hit已采用。A/B新格式重跑产生相同pair/reference计数。

数值方法在首次真实留出前进一步固定：侧带拆成预定4段（每侧中点二分），各格点期望>=5时使用Pearson df=3检查平背景，避免只比较左右平均值漏掉侧内趋势。12个±1可达格点单边界扰动全部检查，任一失败不校准。新增严格半宽100/200/300ns的未修正/固定修正净计数及误差。精确半tick等距时保留上下两个合法offset、同半宽200ns计数；不默认向上，未确定唯一选择则标quantization_tie_unresolved并保留原配置。此时验证只比较两个冻结候选，不用留出重选offset。

首次真实留出前冻结的执行清单已保存为 `analysis/20261008-time-offset-design/run_execution.sh`：A训练6015，比较6019/6024/6028；B训练6035，比较6045/6050；C训练6054固定50k网格，比较6065/6075/6078首2M及6061未使用的[2M,4M)（其[0,2M)已探索，不能当独立验证）。A/B按整2M连续slice，C所有run统一固定50k网格。每组所有冻结文件先写入后才打开该组任一holdout。组配置取所有比较run的通过交集；任一比较失败的通道保持原配置。6041/6071本轮预算暂不加入，不能称全部14个文件完成验证。

最终批次将写 `time_offset/final/`，旧research产物仅保留探索证据。所有统计阈值、窗口建议规则和取样网格均在此次首次真实留出前固定；后续不按失败holdout调参。预计产物为三组完整模板、逐通道状态和原ROOT回查，不预设成功数量。

## 首轮独立结果与一次扩量

首轮最终交集：A 25、B 30、C 32 个非参考目标通过，均cid0；cid1三个组均未校准。每组完整416模板行。程序 `--summarize` 从既有ROOT重算后输出 `final/reasons.csv`：cid1训练阶段A为7行侧带统计不足、96行不足100对未建立窗口、103行未观测、2行候选后跨run缺失；B为91行侧带不足、9行无窗口、105行未观测、3行候选后验证不足/缺失；C为80行侧带不足、35行无窗口、93行未观测。

鉴于主要限制是统计量，按主代理已授权有界增量做一次扩量：训练run6015/6035/6054均用新entry [4000000,8000000)，各4M预算；所有比较run也用新[4M,8M)，与首轮训练和已消耗holdout不重叠。A/B仍整slice，C仍50k固定网格；所有数值门槛、窗口建议规则和比较方法不变，完整先冻结再打开新holdout。此批次保存为 `time_offset/final-expanded/`，首轮不覆盖。若扩量后CsI仍未过关，按本轮边界保留未知，不能把gamma成功说成CsI对齐完成。实际命令：
```bash
bash analysis/20261008-time-offset-design/run_execution.sh /tmp/time_offset_g002 time_offset/final-expanded 4000000 4000000
```

## 清理计划与行为锁

按主代理要求应用 ai-slop-cleaner，范围仅本轮cc/hh和两个执行/验收shell入口。行为已由24项工程与24项数值/模板测试及既有冻结产物重算锁定。先查屏蔽失败的fallback、死码、重复和错误路径，再决定是否编辑；科学候选、阈值、计数和已消耗holdout不改。

只读盘点：未知sr拒绝换算并保留观测标记、无可信背景/扰动失败保留unknown、整slice错误先拒绝、网格仅合并预检查通过块，均为显式失败路径；扰动异常转失败、validation ledger异常清锁后重抛，不吞掉成功/失败证据。ROOT拟合是独立诊断备选，count方法不依赖拟合收敛，不能算masking fallback。无TODO或临时跳过门槛。早期unused函数和误导缩进已修复；本轮不为清理改动已冻结科学行为，也不增依赖/框架。补齐CLI帮助文字；无UI。本员工只报告盘点和复验，不自批最终review，交主代理独立审查。

验收边界复查发现每个批次自己的消费ledger只能防止同目录复用；为避免新批次目录意外重复使用同一holdout，改为任务级 `time_offset/validation_uses.csv`。已有两个批次ledger原样合并，不改变任何范围或冻结摘要，原文件仍保留；真实validation在读取前检查任务级所有已消费区间，verifier也核对每个已用区间及冻结摘要登记。独立/tmp合成fixture仍在自身目录保存ledger，避免污染真实任务。此为复用保护修复，不改已冻结科学数值或重新读holdout。

## 当前交付结果（扩量批次，待主代理独立审查）

主交付目录为 `final-expanded/`；`final/` 是首轮2M统计不足证据，不能把两轮中每通道较好的结果拼成一套。扩量批次全部参数在新holdout打开前冻结，组内所有指定比较run通过才改变模板第三列。

| 候选组与验证范围 | cid0 已校准目标 | cid1 已校准目标 | 已观测但未校准目标 | 未观测模板行 | 参考行 |
| --- | ---: | ---: | ---: | ---: | ---: |
| A：6015训练，6019/6024/6028验证 | 29 | 0 | 115 | 271 | 1 |
| B：6035训练，6045/6050验证 | 34 | 8 | 98 | 275 | 1 |
| C：6054训练，6061/6065/6075/6078验证 | 33 | 4 | 116 | 262 | 1 |

每组完整416行（每crate208行），共108个组—通道成功记录，其中96个gamma、12个CsI组—通道；这是按组计数，不是108个独立物理地址。各组原五列模板完整保留，未知项仍用原offset和能量上下限，不代表本轮测得零offset。A的CsI仍未完成对齐；B/C也只有上述少量CsI通过，不能称全部CsI已校准。

数据来源、实际条目范围、tree最新cycle及计数见 `final-expanded/sources.csv`。所有正式训练/验证请求entry [4M,8M)，core [4010000,7990000)，chunk=100000。A/B slice均完整有效；C在80个固定50k slice中，训练6054有效60/拒绝20；验证6061为60/20、6065为61/19、6075为64/16、6078为62/18。拒绝块无任何谱/训练/验证贡献，全部逐块理由保留在ROOT `slice_log`。这不是对被拒绝数据或整个run的校准证明。

CsI扩量后的主要限制由 `final-expanded/reasons.csv` 给出。A：103行未观测、41行未达到建议窗口的100对条件、62行侧带不足、2行候选跨run缺失，208行全保留原值。B：8行通过，105行未观测、4行无窗口、69行训练侧带不足、20行验证侧带不足、1行扰动失败、1行跨run缺失。C：4行通过，93行未观测、13行无窗口、98行侧带不足。达到本轮一次有界扩量的停止点，不再调整门槛或针对同一holdout重复试选。

可回查数值例子（误差是本方法条件下的中心标准误）：B组 `(1,2,14)` 训练中心为 −210.655 ± 11.906 ns，写入/生效均 −210 ns，训练残差 −0.655 ns；其6045验证中心为 −219.366 ± 17.308 ns，6050也按同一冻结候选通过。C组 `(1,3,13)` 训练中心 −276.182 ± 17.687 ns，写入/生效均 −280 ns，残差 +3.818 ns；6061验证中心 −288.736 ± 13.596 ns，另外三个验证run也通过。完整精度和各run的100/200/300ns严格半宽净计数及误差见各 `validated_*/offsets.csv`。

组目录的 `offsets.csv` 是通过交集；其中validation数值列保留第一个比较run的明细，不能当所有run的汇总误差。`group_manifest.txt` 列出每个比较目录，逐run明细必须以各自CSV/ROOT为准。`group_*/crate0.dat` 和 `crate1.dat` 是本次候选配置；尚未回填原decoder，也未启动下一阶段解码。组编号区间A=6015–6029、B=6030–6051、C=6052–6079用于组织候选配置；未观测run不能直接宣称验证完成，6052硬件身份未与A/B合并。6041和6071没有进入本轮有限样本验证。

## 数值口径与适用限制

`Spectrum::fine/coarse`保存全部合法候选对；`blocks`仅保存每个统计子块保留core后的候选对，统计子块相隔至少3998ns，避免同一目标hit进入两个子块。对于C固定网格，每个有效slice先各自分16块并加时间保护，再按块序号合并投影；失效slice不参与。估值使用统计子块之和，原全候选谱仍供回查，二者计数不必相等。

侧带及峰区只取 `gcd(q_reference,q_channel)` 可达格点。设峰区格点数为n、侧带为m，b为侧带总计数/m；净计数与重心为

$$
N=\sum_{j\in R}H_j-n\widehat b,\qquad
\mu=\frac{\sum_{j\in R}x_jH_j-\widehat b\sum_{j\in R}x_j}{N}.
$$

净计数线性权重为 $a_j=1_R-(n/m)1_S$；重心一阶误差权重为

$$
w_j=\frac{(x_j-\mu)1_R}{N}-\frac{\sum_{\ell\in R}x_\ell-n\mu}{Nm}1_S.
$$

对任一投影v（净计数用a、中心用w、背景用$1_S/m$），保存计数并计算Poisson传播与16块经验方差的较大值：

$$
V_P=\sum_jv_j^2H_j,\quad z_k=\sum_jv_jH_{kj},\quad
V_B=\frac{K}{K-1}\sum_k(z_k-\overline z)^2,\quad V=\max(V_P,V_B),\quad K=16.
$$

同一侧带背景值对峰区各bin的协方差由这些共享权重传播，没有使用sqrt(net)冒充误差。块间近似独立、时间平稳及线性化仍是适用假设，不能因有限样本通过而证明整个实验满足。另要求至少8块净信号>=5且中心一致性p>=0.01。四段侧带Pearson检验用df=3、每段期望>=5的计数近似；低统计侧带保留unknown，不为获得通过而把空bin纳入背景。当前没有给出系统误差完整上限，也没有声称误差具有严格覆盖率保证。

训练和验证都要求net>=100、SNR>=5、可信背景及全部12种边界扰动通过，扰动中心变化<=目标q；验证中心差<=max(2q,3倍合并中心误差)。这些是本轮固定的质控初值，不是物理定律。2ns计数估值不依赖高斯拟合成功；另存24ns单/双高斯ROOT函数、拟合结果/协方差、边界状态、p值及同一有限峰区内的分量净面积/面积加权中心，作为诊断备选，未用不稳定拟合代替主估值。固定offset只平移双峰，不会消除双峰间距。没有导出SVG或另建Python分析程序；已做数值/对象回查，没有把这些检查说成实际渲染后的视觉审查。

## 复现与验收

```bash
# 新独立工作区重现正式批次；当前工作区已有任务级holdout消费记录，拒绝把旧holdout重复当新验证。
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic $(root-config --cflags) time_offset/time_offset.cc $(root-config --libs) -o /tmp/time_offset
bash analysis/20261008-time-offset-design/run_execution.sh /tmp/time_offset time_offset/new-run 4000000 4000000
# 当前成果只读重算，不重开event holdout：
bash analysis/20261008-time-offset-design/validate_execution.sh --mission
```

最新实际验收通过：ROOT6.34.08、g++9.4.0无警告编译，24项配对/ROOT工程测试、25项数值/模板/留出边界测试通过，真实3组科学重算通过，108组—通道。对应日志 `time_offset/mission_verification_review.log`，构建/fixture目录 `/tmp/time-offset-build.3lFmnm/`；机器证据 `analysis/20261008-time-offset-design/completion.json` 与 `execution_verification.json`。synthetic试验仍显式scientific_complete=false；对synthetic/未组合工程产物执行mission的负测试明确非通过。

原始输入只以ROOT READ打开，程序只读原crate并逐行比较冻结原文；原decoder没有编译或运行。不存在原始大文件的全内容前后哈希基线，因此不宣称已完成逐字节原始数据指纹核对；保留实际输入路径/tree周期/条目范围，以及源码只读路径和模板一致性证据。ROOT和可执行文件本地忽略，小CSV/JSON/模板/来源清单进入交付范围。主代理尚需独立审查、整合与版本交付，本员工不自批最终审查或宣称远端推送成功。

## G003 独立审查修复计划（实施前）

主代理独立review发现两个边界缺陷：mission完成报告直接ofstream会跟随符号链接/硬链接；消费ledger的提取循环会在坏行处静默停止。此轮先修这两项，不改变科学数值或打开真实holdout。完成报告将拒绝符号链接、非普通文件和多硬链接，使用同目录独占临时文件，检查写入/flush/fsync/close后原子替换；失败mission也用同一安全入口。ledger将共用严格逐行解析器，要求引号路径、非负且begin<end区间、32位hex摘要、无多余列及完整行，任一坏行和读取失败都阻止消费/验证，不能在找到匹配后跳过剩余行。

回归：symlink/hardlink目标原始字节不变、非普通输出拒绝、普通报告安全替换；坏行在已登记区间前/后、截断行、错误digest/区间和多余字段全部拒绝，验证器也检查全文件。现有108组—通道仅只读重算保留；双峰主峰/加权候选正式比较与C时间有序统计块另列最小方案，未实现前不宣称已完成这些要求。

G003 HIGH/MEDIUM实际复验：无警告编译，24项工程测试和62项数值/模板/安全边界测试通过；旧108组—通道只读重算通过，没有重新打开真实event holdout。构建/fixtures `/tmp/time-offset-build.xn2g0f/`，日志 `time_offset/mission_verification_review_fix.log`。cc审查hash为 `83c47bce6340eb69c8fd0aa8b806af19a059daddae0bac8d298648398a9b4884`。完成报告alias测试包含失败mission路径、symlink和hardlink目标字节保持、普通文件替换；ledger测试包含坏行前/后/无换行/多列/错误摘要/错误区间/未引用路径、验证器全文件检查和拒绝后无新消费记录。实际18行真实ledger格式正常，未发现已发生的重复使用。

### 后续科学接口最小方案（尚未实现，提交主代理反馈）

1. 在TRAIN上使用已有24ns双高斯，仅在status=0、covariance=3、参数不贴边、净面积正、拟合残差p>=0.01且两中心距离>=max(48ns,2倍较大sigma)时界定可分离两峰。两中心之间的固定边界把原峰区分成互不重叠R1/R2；各区仍用2ns可达格点计数、同一可信侧带背景求净面积和净重心。较高24ns峰所在区为main候选；两区净面积加权中心为weighted候选，与完整区间净重心保持同口径。没有可信分峰就写single_or_unresolved，只保留overall候选，不能凭半tick或任意拆区伪造物理双峰。
2. 选择策略在训练前明确，默认weighted，可通过CLI预先指定main，不在holdout上选择。冻结main/weighted两候选的mu、q倍数、区域、来源和三种严格半宽净计数/误差。holdout沿用冻结区域与offset分别核验、比较同半宽，不重新拟合选择区域，不修改offset；最终只有预选候选通过才改变crate。现在已有的fit weighted仍只是诊断对象，不能宣称此比较已完成。
3. C网格先预检查所有固定slice，保存成功/失败状态，从有效core时间范围取得共同绝对时间边界。所有有效slice填同一组16个按时间排序的统计桶，桶边缘各排1999ns，避免此前“每slice第k块再相加”抵消慢漂移；每slice配对缓存与失效隔离不变，完整all-pair双谱不变。合成测试新增慢漂移检出、稳定信号通过、网格/chunk和全候选谱等价。
4. 新接口和规则完成合成回归后，使用尚未读取的各训练run及比较run的[8M,12M)，新训练先冻结，再读取新holdout。旧108成果保留为v1历史证据；新候选/时间桶使用明确新冻结格式。当前旧mission通过只证明v1计数子集和已实现边界，不能替代新增要求的最终使命验收。主代理负责批准接口与更新正式计划，本员工此时未读新真实区间。

## G004 实施记录（主代理已批准最小方案）

现按批准方案实施，不重新规划流程。新增版本只使用共同绝对时间16桶和TRAIN确定的物理main/weighted候选；默认策略weighted，在--scan之前由CLI/执行脚本固定，main须同样预先指定。v1仅只读核验历史，正式mission必须新版，不混合旧108结果。新真实训练和各不同run留出均限定尚未读取的[8M,12M)，先完成全部合成回归并冻结再读取。HIGH/MEDIUM安全修复保留。

G004稳定实现已实际通过：ROOT6.34.08/g++9.4.0无警告编译，24项工程与70项数值/模板/安全/新物理候选测试通过，构建 `/tmp/time-offset-build.ivFgLt/`，日志 `time_offset/g004_synthetic_stable.log`。慢漂移反例明确显示旧folded桶通过而新ordered桶拒绝；双峰合成样本main与weighted中心相差超过100ns，并保存两候选三种同半宽净计数、误差和独立验证。预先指定main会改变选中候选，训练后修改策略被拒绝，物理候选表篡改被拒绝。单峰/不可分离谱仅一overall候选，不把half-tick当物理两峰。

已向主代理和独立QA发送稳定审查hash：cc `ccc6edbf7cbb2e3b4e4f7ed81aecb833418cde0af08fb2d41b3af2553e11647c`，hh `febd8b8130884d36afd7bfb5b9b27b4f63fb15063d057ea9539fc668ed3dacf3`。新正式批次使用此固定binary，候选策略在训练前固定weighted：
```bash
bash analysis/20261008-time-offset-design/run_execution.sh /tmp/time-offset-build.ivFgLt/time_offset /home/ys/data_401/data/chx_20260622/.omx/coordination/workspaces/time-offset-impl-20261009/time_offset/final-candidates 4000000 8000000 weighted
```
所有training和不同run holdout范围均为[8M,12M)，未曾读取；组内全部freeze先保存再读取该组holdout，区间和摘要记任务级消费ledger。新增正式mission入口只认可v2，旧108仍可用--verify-artifacts历史重算，不能满足本轮候选比较使命。原completion已另存completion_legacy_v1.json，当前新结果尚未产生。

### G004 范围内清理盘点与 no-op 结论

应用ai-slop-cleaner，仅检查本轮cc/hh及执行/验收脚本；24+70项回归锁定行为后检查。v1读取是已存在历史artifact的明确只读格式兼容，正式mission拒绝v1；invalid slice整块拒绝、未知/弱通道保留旧值、不可可信分峰只保留overall均为有理由且带测试的fail-safe，不是掩盖失败的fallback。主峰未解析且策略main时直接unknown，不偷偷改用weighted。ledger/parser及安全报告写入异常均外传，临时输出清理由明确当前文件身份限定。没有新增TODO、静默绕过统计门槛或无人使用的通用模型框架。此次清理结论为no-op：编译/回归已通过，算法冻结后不因风格再改科学源码；最终review由独立代理负责。

## G004 独立审查 LOW 修复计划（实施前）

独立code-reviewer已只读重算新版三个组通过，但指出mission失败reason直接嵌入JSON：含引号、反斜杠或控制字符的错误路径会破坏completion.json。仅补JSON字符串转义并回归安全/tmp路径错误；不改任何统计、候选、冻结参数或已消费holdout。真实103项由旧生成hash `ccc6edbf...` 产生，新hash只修失败报告序列化，重新编译/合成测试后只读重算同一成果，版本链如实保留。
