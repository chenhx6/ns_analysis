# 执行计划：Ge run.log 运行时间清单与 SVG 甘特图

- 创建／修订日期：2026-10-07
- 状态：已完成；CSV、每日 SVG、源日志核对及逐图视觉审查均完成
- 用户确认记录：2026-10-07 用户明确指令“开始执行两份计划”；按修订后的目录、SVG 格式及仅日志来源执行，不包含提交或推送
- 前置关联：通用脚本迁移与绘图技能见 `2026-10-07-analysis-layout-svg-qa.md`；若先执行本任务，使用当时实际存在的运行入口，不假定迁移已完成。

## 目标与范围

读取 `/home/ys/data_401/data/Ge/<run>/run.log`，统计各 run 的开始、结束、持续时间（分钟）和日志结束状态，输出 CSV 与 SVG 甘特图，供以后查找解码、gamma-gamma 符合矩阵的输入 run。

默认包括 `Ge/` 直属的数字 run 目录，排除 `Ge/test/`。存在目录但缺日志时保留记录；不存在的编号不虚构为异常运行。所有原始文件只读，不解码、不制作符合矩阵、不读取大型二进制内容。

本任务只以 `run.log` 为统计来源：不读取或核实实验记录，不输出实验备注、数据有效性、模块完整性或文件哈希验证列。日志结束状态仅描述日志所记录的终止信息，不用于判定物理数据可用性。

## 已核实的格式

- 根目录无单独的 `Ge/run.log`，日志位于各 run 子目录；已只读抽查 run6015、6021、6052、6079、6220、6231 和 test/6009。
- 样本含 `Start: YYYY-MM-DD HH:MM:SS` 和 `Stop : YYYY-MM-DD HH:MM:SS`，位于第 9–10 行。程序按字段识别，允许空格变化，不固定行号。
- 样本也含 `run time:` 整数，但单位未确认；本任务使用起止时间差，不使用该整数推算时长。
- 尚未发现已验证的“异常终止”标志；缺字段时保留事实和原因，不猜测结束方式。
- 日志的时间作为权威输入，不用人工记录或文件修改时间替换。日志没有时区字段，原样保留采集机墙钟时间，不自动转换时区。

## 预计建立或修改的文件

| 路径 | 操作 | 用途 |
| --- | --- | --- |
| `analysis/plans/2026-10-07-ge-run-log-timeline.md` | 更新 | 确认、进度、命令、关键决策和恢复记录 |
| `analysis/run_log/run_log.py` | 新建 | 日志解析、CSV、描述性清点和 Python/matplotlib 甘特图；一个程序完成，不拆多层框架 |
| `analysis/run_log/test_run_log.py` | 新建 | 一个标准库回归检查，覆盖缺字段、坏时间、多段和跨日处理 |
| `analysis/run_log/runs.csv` | 新建 | 每个实际 run 目录一行的运行时间清单 |
| `analysis/run_log/figures/gantt_YYYY-MM-DD.svg` | 新建 | 每个有可定位时间的日期一张甘特图；实际数量由日志日期决定 |
| `analysis/run_log/reports/run_log.md` | 新建 | 输入范围、日志指纹、字段及状态定义、无法解析清单和复现命令 |
| `analysis/run_log/reports/figure_qa.json` | 新建 | 每张最终 SVG 的自动检查及实际视觉审查记录 |
| `analysis/run_log/reports/svg_audit.json` | 实际新增 | 浏览器自动几何检查原始结果，视觉字段保留 pending，与最终审查证据区分 |
| `analysis/run_log/reports/data_verification.json` | 实际新增 | 独立程序核对全部 CSV 与原始日志的通过证据 |

先保存并提供程序文件链接，再运行。解析、筛选、数值汇总、CSV 和绘图逻辑均在显式程序文件中；报告中的数字和 run 列表由程序生成。没有正式结果前，不填写预计运行数量和时长。

## 方法与统计处理

### 解析与时长

- 一个 run 一行，同一 run 各模块共享日志时间，不把模块文件当作独立运行重复计数。
- 使用标准库 `pathlib/re/datetime/csv` 和已安装的 matplotlib；不为简单日志解析引入 pandas 或新依赖。
- `duration_min = (end_time - start_time).total_seconds() / 60`。保留秒级原始时间，CSV 分钟值输出至小数点后 6 位；绘图按原始起止时间定位。
- 缺字段、不可解析、重复起止段、结束早于开始均明确记录。可靠的单个时间可以保留，但无法唯一配对时不计算时长。
- 缺失时长留空，不填 0，不用下一 run 开始或文件修改时间补齐。真实零时长保留 0。
- 只做描述性清点：记录数、各状态数、缺失信息清单，以及有完整时间记录的持续时间总和；注明参与合计的记录数。重叠区间不把简单相加解释为实际采集覆盖时长。不做检验、置信区间或有效性推断。

### CSV 字段

| 字段 | 含义 |
| --- | --- |
| `run_id` | run 编号，连接实际原始目录 |
| `start_time`、`end_time` | 日志时间，格式 `YYYY-MM-DD HH:MM:SS`；缺失时为空 |
| `duration_min` | 起止时间差，分钟 |
| `end_status` | `normal / abnormal / unknown`，仅按日志证据分类 |
| `status_reason` | 分类或缺失原因，以及对应日志字段／行号 |
| `log_path` | 实际输入日志位置，便于追溯 |

CSV 用带 BOM 的 UTF-8，按 run 编号排序。删除上版的 `known_quality_note`、`quality_flags`、模块数、原始文件列表和内部运行计数列。

结束状态建议：唯一有效 Start/Stop 且无已核实异常终止记录时为 `normal`（正常结束记录）；有明确且语义已核实的异常终止标志时为 `abnormal`；其余为 `unknown`，保留原因。缺 Stop 只标“结束记录缺失／疑似未正常结束”，不声称已证实异常。若新格式无法确认，先保留 `unknown`，不能凭任意 error 字串判为异常。

## 绘图与审查

- 全部由 Python/matplotlib 根据 `runs.csv` 绘制，图像文件仅保存 SVG；不生成 PDF、PNG、TIFF 副本，不使用 AI 生成图片。
- 每日一张、每图单坐标轴：横轴为日期及一天内时间，纵轴为 run 编号；条形的左右端对应起止时间。按当日开始时间排列，采用可编辑 SVG 文字（`svg.fonttype = 'none'`）。
- 正常结束记录使用蓝色实心条，明确异常使用橙色纹理条，时间可定位但结束状态未知使用灰色纹理条。图例说明语义，不标“数据有效”或“数据无效”。
- 跨日区间按日期裁剪到各图，CSV 时长只计一次；恰在午夜结束时不画下一日零长度条。
- 只有开始时画开始标记，不虚构条长；真实零时长画点。无法定位的记录留在 CSV 和报告中，不伪造绘图坐标。
- 每张最终 SVG 都须实际渲染查看，检查标签／图例重叠、字符裁切、缺字、时间定位、状态映射和跨日关系；自动几何检查与视觉审查分别记录。缺少查看工具时报告未审查，不宣称通过。
- 如需栅格显示 SVG，仅在内存中临时渲染供视觉检查，不保存其他图片格式。绘图规范技能按关联计划安装；即使尚未安装，也需完成上述审查。

## 执行步骤与拟用命令

1. 用户确认后记录授权范围。检查当前 Python、matplotlib 和 SVG 查看途径；确认实际目录和日志未发生需要改变方法的新格式。
2. 保存 `run_log.py` 与检查文件，提供链接；先跑回归检查，再用 run6015、6021、6079、6231 做有限样本核对。
3. 小样本通过后读取全部正式 run 日志，生成 CSV；重新读取 CSV 绘图及生成数值报告。
4. 对最终 SVG 完成自动检查和逐图视觉审查，修正后重画、重查；保存真实检查结果及命令，更新本计划。
5. 交付程序、CSV、SVG 和报告后停止，不提交、推送或继续解码。

以下假设目录整理已完成，未完成时改用现有的 `analysis/code/project_runtime.py`，并记录实际命令：

```bash
python3 analysis/scripts/project_runtime.py python analysis/run_log/test_run_log.py
python3 analysis/scripts/project_runtime.py python analysis/run_log/run_log.py --input-dir /home/ys/data_401/data/Ge --output-dir analysis/run_log
```

实际 SVG 自动审查使用 `python3 analysis/scripts/project_runtime.py python .agents/skills/python-svg-qa/scripts/audit_svg.py`，显式传入 2025-06-07 至 2025-06-15 的九张 SVG，并指定 `--json-out analysis/run_log/reports/svg_audit.json`。完整原命令及逐图 `--preview-base64` 查看方式保存于 `reports/figure_qa.json`，没有使用 PDF 工具审查 SVG。

## 完成标准

- CSV 行数等于实际直属数字 run 目录数，每个 run 唯一；未混入测试目录，缺日志目录没有被遗漏。
- 有效时长与起止差一致；缺失与真实零时长可区分；所有结果均可追溯到日志及显式程序。
- 检查覆盖空白变化、跨日／多日、零时长、缺 Start/Stop、坏时间、负时长、重复起止与结束状态证据不足；测试数据不进入正式输出。
- 图形位置、标签和状态与 CSV 一致；跨日图中区间段合计与原区间一致；没有未经确认的时间填补。
- 保存的图片全部为 SVG；每张最终图都有实际视觉审查结论，自动检查失败和视觉错误已修正。
- 不读取实验记录作为统计输入，不添加数据有效性备注；原始目录无写入。

## 进度与恢复记录

- 已完成：显式程序、小样本、回归检查、全部日志统计、CSV、SVG、独立数据验证、自动几何检查和九张最终图的实际视觉审查。
- 实际结果：212 个 run，209 个起止完整；6027、6080、6228 缺 Stop，时长为空、状态 unknown。完整时长合计 8894.700000 分钟（run 时长相加，不是去重覆盖时间）；9 张每日 SVG。数字来自程序报告和独立核验文件。
- 实际命令：小样本使用 `.runtime/run_log_sample` 和 `--runs 6015 6021 6079 6231`；正式生成使用本计划中的两条主命令。追加核验：`python3 analysis/scripts/project_runtime.py python analysis/run_log/test_run_log.py --csv analysis/run_log/runs.csv --report analysis/run_log/reports/data_verification.json`。
- 验证：全部 CSV 起止值逐条匹配日志，分钟差及日志指纹通过；每张 SVG 自动几何与实际视觉检查均通过。程序及输出位置见本计划文件表与 `reports/run_log.md` 的图表索引。
- 未执行：无本任务必需工作剩余；未解码、计算符合矩阵、提交或推送。
- 本次变更：任务输出集中到 `analysis/run_log/`；仅 SVG；删除实验记录与质量备注，缩减 CSV；官方解码源码已由用户移到 `decode_data/DecodeAndSortAll/`，本任务不改动它。
- 下一步：交付后停止；后续查询或修改先读取本计划和真实结果，再按新任务保存计划。
