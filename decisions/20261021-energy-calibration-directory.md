# 能量刻度标准程序与一级目录结构

- 日期：2026-10-21（Asia/Shanghai）
- 状态：用户已明确要求，作为核谱分析标准工具规范记录；适用于伽马能量自动刻度及后续探测器标定工程。
- 依据：2026-10-21 用户明确要求“我们的标准处理数据程序需要最终写在chx_20260622/下，比如decode_data、run_log、time_offset这类标准程序分析工具”，并将自动刻度程序正式确立在项目根目录一级工程 `calibration/energy/` 下。

## 目录约定与组织架构

本项目遵循原子核结构实验数据的集中式标准处理架构：直接产生或处理科学数据的一级标准分析工具直接置于项目根目录 `/home/ys/data_401/data/chx_20260622/` 下，统一采用可编译 C++/ROOT 或专用 Python 工具，便于跨运行与外部环境复用与迁移。

项目根目录下一级标准处理目录规划如下：
1. `decode_data/`：原始物理事件解码与排序程序（`DecodeAndSortAll/`），输出已解码 ROOT 数据。
2. `run_log/`：运行日志与束流状态解析工具及小表。
3. `time_offset/`：各探测器时间对齐分析程序与对齐结果表。
4. `calibration/`：实验探测系统标定工程（一级直接数据处理目录）：
   - `calibration/energy/`：伽马与带电粒子能量标定子工程。
     - `calibration/energy/autocal/`：自动能量刻度正式源码与配置目录，包含 `main.cc`、`autocal.hh`、`autocal.cc`、`peakfinder.hh`、`peakfinder.cc`、`UserDefine.hh`、`sources.csv`、`Makefile` 及 `README.md`。
     - `calibration/energy/<output-run>/`：指定运行的数据产物目录（例如 `calibration/energy/data_C1_6082_notwave/`），集中保存刻度系数表 `calibration.csv`、带有完整序列化峰拟合函数的直方图文件 `histograms.root`，以及逐通道的三面板回查图 `figures/*.svg`（2026-10-21 用户要求由 PNG 切换；既有 PNG 不因此删除）。
   - 今后其他标定（如探测效率标定、粒子鉴别标定）在 `calibration/` 下并行设立独立子目录（如 `calibration/efficiency/`）。

## 与 analysis 目录的边界

- `analysis/` 主要用于间接处理、通用脚本（`analysis/scripts/`）、开发期单元测试与模拟验收（`analysis/YYYYMMDD-topic/`），以及实验记录本（`analysis/experiment_log/`）。
- 冒烟测试、模拟验收、来源文献核验等开发期产物存放于 `analysis/20261020-energy-autocal/`，不混入 `calibration/` 正式源码与日常分析输出。
- 大型数据文件（如原始 ROOT 树、大型中间直方图）不存入 `analysis/`。

## 整数道内随机化：2026-10-21 用户决定

适用范围：自动能量刻度的 ADC 填谱、峰心坐标和后续刻度检查谱；不修改原始数据，不自动改变其他分析程序。

用户明确 evte 为整数，要求采用

$$u\sim U[0,1),\quad A=\operatorname{double}(evte)+u,\quad E=a_0+a_1A+a_2A^2.$$

读取分支仍使用原始 UShort_t；A、E 计算使用 double，不将加随机数的 A 截回整数。实现依据见 decoder r2root.cc 的 evte/s 及 autocal.cc 的类型检查。峰心拟合和能量应用必须使用同一坐标约定，不混用旧整数中心的系数。

用户确定的是道内均匀化的处理约定。硬件是否按 [k,k+1) 截断量化尚未核实，不能由整数类型推出；double 是程序数值表示，不是对核跃迁能谱“严格连续”的物理断言。道内随机化不恢复亚道测量信息，不提高探测器固有分辨率。

相对整数中心，A 的均值移动 +0.5 道，所加随机量方差为 1/12 道²。为避免半道系统偏移，本次需统一坐标重新拟合；不要只在旧系数应用阶段加随机数。旧参数与新参数的差异应区分坐标变换、随机化及拟合方法变化。单个 k 道内二次映射的均值为 E(k)+(a1+2*a2*k)/2+a2/3，不能用随意添加能量噪声替代。

实现建议（待验证，不标为已生效）：UserDefine.hh 提供开关和固定非零随机种子，ROOT provenance 记录发生器、种子和 [0,1) 区间；同一输入条目在不同扫描及配置下复用同一 u，导图不重抽。ADC 基础边界采用 [0,65536)，65535 加 u 不应丢到溢出；任意重分箱保留尾部余数并验证总计数守恒。

该方法可缓解整数格点映射到能量箱的人工结构，效果取决于增益、非线性和目标箱宽。对整数边界且宽度为整数的 ADC 箱，加入 u 不改变每箱计数，因此单道谱的统计毛刺仍需通过合适重分箱处理；不承诺完全消除所有伪结构。重分箱计数与滑动平滑分别处理：前者可用于独立计数的 Poisson 拟合，后者的箱间相关性不能忽略。

当前为方法决策，尚未由本轮实现、编译或实际运行验证。后续实施与验收见 analysis/plans/process/2026-10-21-energy-autocal_revise1.md；旧版运行证据不证明本约定已生效。
