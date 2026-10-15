# 单 ROOT 文件 time offset

`time_offset.cc` 与 `time_offset.hh` 构成一个 C++/ROOT 程序，Makefile 使用与 DecodeAndSortAll 相同的 `root-config` 编译入口。函数和关键算法附近附简要注释。旧 `time_offset/` 不删除，原 decoder、crate 配置、输入 ROOT 均不修改。

## 编译和运行

从项目根目录执行：

```bash
make -C timeOffset/time_offset check
timeOffset/time_offset/time_offset 6015 decode_data/data_C2_6015_6015_wave.root timeOffset/time_offset
```

输出为 `time_offset_6015.root`、`time_offset_6015.csv`、`time_offset_6015.md`。输出文件已存在时拒绝覆盖；重跑时在 `timeOffset/` 下新建结果目录并作为第三个参数。可选第四个参数限制条目数，省略或 0 表示处理全部条目。输出目录需预先存在，程序限制输出在可执行文件上一级的 `timeOffset/` 任务树内。

```bash
mkdir -p timeOffset/sample_new
timeOffset/time_offset/time_offset 6015 decode_data/data_C2_6015_6015_wave.root timeOffset/sample_new 1000000
```

ROOT 中打开 `c0_s2_ch4_24ns` 等对象即可查看 `time_fit` 拟合线；对应 `_2ns` 是原细谱。参考通道的谱刻意不填自配对。只为输入中实际出现的通道创建对象；无峰或失败通道仍保存谱。

## 输入、分组与符号

只读 `tree` 的 `ts,cid,sid,ch,sr`。保留 cid=0,1、sid=0..16，校验 ch=0..15。按原 decoder：sr=125/250 时每 tick 为 8 ns，sr=100/500 时为 10 ns；未知 sr 或读取失败立即报错。无 CFD、能量门、旧 offset 修正。

事件以第一条有效命中为起点，后续粗时间差不超过 1999 ns 归入同一事件，超出则关闭并另起事件；输入倒序也关闭事件，计数保存在 ROOT。事件结束时，参考 (0,2,5) 与同事件各目标通道配对。仿照 sort.cc：Ge 每通道留最后一次命中，CsI 留全部命中；参考采用最后一次命中；不自配对。文件末尾也处理最后一事件。

沿用本项目已确定的符号：`dt=t_reference-t_channel`，与外部 sort.cc 的相减方向相反；因此 `offset_ns` 加到目标时间。固定事件边界会遗漏边界两侧的近邻命中对，不能将此方法称为完整的 ±1999 ns 滑窗配对。

同一批候选对填两张谱：2 ns 谱有 1999 bins、范围 [-1999,1999] ns；24 ns 谱有 166 bins、范围 [-1992,1992] ns。粗谱左右剩余计数保留为下溢、上溢，CSV 明列，不参与拟合。原时间是 8/10 ns 格点，细谱的周期空 bin 并非物理多峰。

## 峰形与拟合

细谱只用于初始化和确定范围：25 个细 bin（50 ns）移动平均，估计中位本底，找主峰。至少 100 对且平滑峰高通过代码中的统计阈值才拟合。第二候选需离主峰至少 72 ns、高于主峰净高度的 20%，并有低于较小峰净高度 85% 的谷。峰尾延伸至净高度 5% 或噪声阈值，再向左右各扩展 96 ns 侧带，将区间对齐 24 ns bin 边界。

24 ns 谱上 ROOT `Fit` 使用 `SQLIRN`：Poisson likelihood、保存拟合结果、积分平均每个 bin、限定区间、不自动附加试探函数。拟合模型是单高斯加线性本底；出现第二候选时再试双高斯加线性本底。线性本底用两个非负端点表示，与 pol1 等价，但避免负期望计数。所有 seed、阈值和参数约束集中在 `FindShape`、`FitModel`，便于修改。

同一区间比较 BIC，双峰比单峰改善超过 10 才选择双峰；单峰无效而双峰有效时可选择双峰。要求拟合状态为 0、协方差状态至少 2、分量幅度超过三倍参数误差、峰宽和中心不触限制，双峰中心至少相隔 24 ns。额外列出 ROOT chi2 与 ndf，chi2/ndf>3 标为 `poor_fit_review`。这些门槛是实现启发式，不能证明所有谱都适合高斯模型。

CSV 的双峰分量按拟合参数顺序保存，不保证左右排序。双峰暂取较高拟合分量的中心为 offset，标记 `double_peak_review`；两个中心及误差均保留。失败或无峰行不填 offset。`reference` 固定为 0。拟合失败尝试仍附在 ROOT 中，紫色区分；有效候选线为红色。

误差是模型内拟合标准误，不包含模型选择、时间漂移或固定分组带来的系统误差。双峰、拟合质量差和边界通道需要回查，不作为自动通过的标定。本轮只生成结果表，不回填 crate、不量化为硬件 tick、不跨 run 评估。

## 验证范围

`make check` 含确定性的配对符号、Ge 重复覆盖、CsI 多次保留、参考排除、分箱及已知双高斯合成期望拟合检查。合成数据只在内存自检中使用，不混入真实输入结果。先使用真实前 100 万条检查，再处理完整 6015；本次具体数值见程序生成的同名 Markdown，执行与 ROOT 回读证据见 `../../analysis/20261015-single-run-offset/verification.json`。

只读检查了旧 `frozen_B_6050/training.root` 的直方图元数据与峰位；其中被检查的 24 ns 谱未附拟合函数。本次没有宣称已完成所有通道的人工视觉审查，也不把 ROOT 对象回读等同于视觉检查。ROOT 数据和编译文件留本地，不提交版本库。
