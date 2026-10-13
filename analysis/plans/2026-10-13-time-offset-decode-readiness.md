# 计划：评估 time offset 配置用于实验 run 解码的覆盖范围

- 日期：2026-10-13（Asia/Shanghai）
- 状态：只读覆盖审计完成；不执行解码，不改变offset、crate或实验数据。
- 目标：判断现有 A/B/C crate 候选配置是否足以用于 131Ce 实验设计的 run 系列解码，并明确配置覆盖与实测验证覆盖的差别。
- 依据：用户本轮问题；`analysis/plans/process/20261008-time-offset.md`；`decisions/20261008-time-offset.md`、`decisions/20261008-time-offset-method.md`、`decisions/20261009-time-offset-program.md`；`time_offset/report.md` 与 `time_offset/final-candidates/`。
- 检查范围：run 分组及训练/验证清单、crate 覆盖与未校准通道、被验证和未验证 run、最终 mission/远端证据。
- 统计／判读方法：以模板 group-channel 记录及预登记训练/留出 run 为单位；分别判断“可供程序读取的分组候选配置”和“经独立验证支持可校准的通道/运行范围”；不外推到未测 run 或未校准通道。
- 实际结论：A/B/C均有可供decoder读取的完整crate模板，足以支持按组进行受控试解码；不足以把实验设计的run系列及所有通道称为已校准，也不足以直接当作全系列最终生产decode配置。按项目分析约定，计划、只读审计程序和机器验证证据已保存。
- 验证标准：只读读取所有现有decode ROOT树元数据；交叉核对run_log、v2 sources清单、A/B/C覆盖JSON及完整crate模板；列出未解码/未验证run、未校准通道及部署限制。
- 判读结论：若“足够”指候选crate文件结构可被decoder读取，并对已验证的分组和校准通道作试解码，则足够；若指对实验run系列全量生产解码后即可宣称所有相关探测器均时间对齐，则不足。需后续决定全系列run的有效清单、6052硬件配置落组方式、未验证run检查，以及未校准通道能否进入目标gamma-gamma/粒子-gamma分析。


## 只读审计结果

- `run_log/runs.csv` 在run 6015–6079内记录63个run ID（62条end_status=normal、6027一条unknown）；当前 `decode_data/` 只有14个对应ROOT，另外49个run ID尚无已解码ROOT文件。ROOT条目数范围为219,927,184–813,072,043，均大于12,000,000。
- v2训练/验证实际使用12个run：训练6015、6035、6054；独立验证6019、6024、6028、6045、6050、6061、6065、6075、6078。已有解码ROOT中的6041和6071没有用于本轮训练/验证。6052在run log中存在，但无当前decoded ROOT；计划记录该run硬件身份发生重排，须单独归档后才能决定用哪个组。
- A/B/C三个crate配置各保留完整两机箱模板（每crate208个数据行及header）。校准通过记录按组为A: cid0=24/cid1=0，B: 36/8，C: 32/3；这些是group-channel记录，不是跨组去重后的探测器数。模板中其余观测未知项或未观测项均保留原值。
- C组[8M,12M)划为每块50,000条记录：6054为61有效/19无效，6061为60/20，6065为60/20，6075和6078各63/17。
- 物理可执行性与校准充分性分开：候选crate文件存在且格式完整；但run组只由一个训练run和有限独立run支持，不能把范围中的每个run都视为已验证。下一阶段的按run配置选择、独立工作目录和至少3个decode进程调度尚未实施；本次未启动DecodeAndSortAll。
- 复核入口：`python3 -B analysis/20261013-time-offset-readiness/audit_run_coverage.py`；输出 `analysis/20261013-time-offset-readiness/verification.json`。审计只读ROOT条目/tree cycle、run log和已提交offset覆盖文件，不读取或改变原始Ge/CsI文件。
