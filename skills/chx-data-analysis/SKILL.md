---
name: chx-data-analysis
description: 在 chx_20260622 项目中读取 Ge、CsI 探测器数据并编写分析代码、记录和图表，遵循项目的数据边界与结果存放规则。
---

# 项目数据分析

开始工作时读取项目根目录的 `AGENTS.md`；目录规则以该文件为准。Ge、CsI 原始数据仅作为只读输入，`../software/` 不作操作。代码、记录和小型结果放在 `analysis/`；大型处理结果放在项目内专用数据目录。

## 已知数据入口

- 原始数据：`../Ge/<run>/data_R<run>_M<module>.bin`、`../CsI/<run>/data_R<run>_M<module>.bin`；实际运行目录可能还含配置和日志。
- 已解码波形：`decode_data/data_C2_<first-run>_<last-run>_wave.root`。
- 解码实现及硬件映射：`analysis/code/DecodeAndSortAll/`，读取 `UserDefine.hh`、`r2root.cc` 和相关 `crate*.dat` 核实含义。
- 实验设置、探测器位置及采集卡变更：`analysis/record_analysis.md` 和其引用的图片。建立跨运行或跨探测器分析前先查看。

## ROOT 数据

已抽样验证 `data_C2_6028_6028_wave.root` 的树名为 `tree`。已知分支：`sr`、`pileup`、`outofr`、`cid`、`sid`、`ch`、`evte`、`ts`、`cfd`、`cfdft`、`cfds`、`ltra`、`data`。其中 `data` 是长度由 `ltra` 决定的无符号短整型数组；允许出现无波形的条目。其他文件使用前仍应检查树和分支。

PyROOT 已可用。文件可达数十 GB、树可含数亿条目：先检查元数据和有限样本，按任务启用所需分支并流式处理，避免一次性载入整个文件。ROOT 文件可能有多个同名树周期，正常读取最新周期，避免重复统计。

分析能量、时间或波形前核实采样率、时间戳单位、通道映射和刻度。不能把 `evte` 自动视为已刻度物理能量，或将条目数直接解释为物理符合事件数。保存运行编号、输入路径、参数、筛选条件和重现命令到分析记录。
