# 单 ROOT 文件时间对齐：实施计划

- 创建：2026-10-15；定稿：2026-10-18。
- 状态：实施及完整数据验证完成；版本交付通过项目协调器串行整合，最终远端状态以交付收据为准。
- 实际授权：2026-10-18 用户明确授权修改程序、编译、必要检查及有限真实样本验证，通过后处理完整 `decode_data/data_C2_6015_6015_wave.root`，交付ROOT、CSV、简要MD并按项目规则同步；此前仅制作计划限制在本任务内解除。

## 1. 目标与范围

编写简单、可读、可复用的 C++/ROOT 程序：每次读取一个解码 ROOT 文件，生成各通道相对参考通道的两套时间差谱，按开关决定是否拟合第二套谱，输出 ROOT、CSV 和简要 MD。

程序结构参考 `decode_data/DecodeAndSortAll/`；事件包参考 `/home/ys/data_401/data/software/event/sort.cc:304`；时间戳换算和偏移截断依据 `decode_data/DecodeAndSortAll/r2root.cc:427`。外部源码、原始数据、原 decoder 和 crate 配置只读，旧 `time_offset/` 和 `timeOffset/` 已归档于本地 `archive/20261018-time-offset/`，新程序按本计划重新建立。

遵循 Ponytail：采用简单的 TimeOffset 类，不增加配置框架、人工例外表或预留接口。函数及关键算法行附简短注释。保留缺少 run、输入不可读、参数无效、参考被 cut 等必要检查。

## 2. 文件与使用方式

新源码建立于 `timeOffset/time_offset/`：

| 文件 | 职责 |
|---|---|
| `main.cc` | 检查 run 参数，创建 TimeOffset，调用 Process |
| `time_offset.hh` | 数据结构、类及接口声明 |
| `time_offset.cc` | 读取、事件包、填谱、拟合、结果输出 |
| `UserDefine.hh` | 用户按实验填写的参数 |
| `Makefile` | 使用 root-config 编译，正确依赖所有源码及 UserDefine |
| `README.md` | 简短配置与运行说明 |

执行形式：

```bash
cd timeOffset/time_offset
make
./time_offset <run>
```

直接 `make`，无需附加变量；修改 UserDefine 后自动重编译。run 必须从命令行传入，缺失或无效则打印用法并退出。UserDefine 不设默认 run。

本次验证输入为 `decode_data/data_C2_6015_6015_wave.root`。6015仅是验证样本，不写入算法或默认参数。输入地址、文件命名规则及输出目录由 UserDefine 配置；本实验输出目录设为项目内 `timeOffset/`。已有结果不直接覆盖。

## 3. UserDefine 配置

| 参数组 | 配置要求 |
|---|---|
| 输入与输出 | decode 文件地址/命名规则、树及字段名、输出目录 |
| 参考通道 | `REF_CID`、`REF_SID`、`REF_CH`，使用者显式填写 |
| 地址 cut | `CID_CUT_MIN/MAX`、`SID_CUT_MIN/MAX`、`CH_CUT_MIN/MAX` |
| 时间 | 事件窗 W（ns）、sr 对应时间戳 tick 的对照 |
| 第一套谱 | `HIST_X_MIN`、`HIST_X_MAX`、`HIST_BIN_NUMBER` |
| 第二套谱 | `FIT_HIST_X_MIN`、`FIT_HIST_X_MAX`、`FIT_HIST_BIN_NUMBER` |
| 拟合 | `FIT_ENABLED` 及必要的峰形判别参数 |

cut 使用整数闭区间，每端的 -1 表示不限制该端：

| MIN | MAX | 保留条件 |
|---:|---:|---|
| 0 | 1 | 0至1，包含端点 |
| -1 | -1 | 无该字段范围 cut |
| 2 | -1 | >=2 |
| -1 | 16 | <=16 |
| 5 | 5 | 只保留5 |

两端均启用时 MIN 不得大于 MAX。取消范围 cut 不取消输入有效性检查，也不能被固定数组暗中替代为另一种 cut。按实际通道地址组织存储；命中保留方式对应的机箱编号也由实验配置明确。

参考未配置、地址无效或被 cut 排除时，报错并终止。输入中未找到参考命中时明确报告，不生成成功标定结论。参考地址、实验路径及命名规则均为实验配置，不作为其他实验的默认值。

本实验填写值：参考 `(0,2,5)`，cid范围 `[0,1]`，sid范围 `[0,16]`，ch不附加用户范围cut，W=1999 ns。两谱设置如下：

| 对象 | xmin（ns） | xmax（ns） | bin数 | 实际bin宽 |
|---|---:|---:|---:|---:|
| 第一套：看细节 | -2001 | 2001 | 2001 | 2 ns |
| 第二套：较平滑、供拟合 | -2016 | 2016 | 168 | 24 ns |

三参数直接传入 TH1D，不另设 bin 宽、不强制对称范围。运行时打印范围、bin数及 `(xmax-xmin)/bin数`；校验范围递增、bin数为正整数。W与直方图轴范围独立配置。

## 4. 核心处理算法

### 4.1 读取与时间换算

只启用 `ts,cid,sid,ch,sr` 五个标量分支，应用地址 cut；不使用 CFD、波形、能量门或旧偏移表。

$$
t_i=q(sr_i)\,ts_i,\qquad
q(sr)=\begin{cases}8\ \mathrm{ns},&sr=125,250\\10\ \mathrm{ns},&sr=100,500.\end{cases}
$$

这是时间戳 tick，不是 ADC 采样周期。时间换算与相减使用整数 ns；未知 sr 或缺失必要分支报错。

### 4.2 事件包与配对

沿用 sort 的 `Process → ProcessEntry → EndEvent` 思路：

1. 第一条有效命中的时间设为固定起点 t0。
2. 满足 `|t_i-t0| <= W` 的命中加入当前事件包；否则处理当前包，以当前命中建立新包。t0不随新命中移动，也不必是参考命中。
3. Ge每通道保留最后一次命中，CsI保留每次；参考取包中最后一次参考命中。
4. 包中有参考时，与其它通道配对填谱；没有参考则跳过填谱。参考不自配对。文件末尾处理最后一个包。

按用户指定近似，相关带电粒子与gamma信号视为瞬发。通道延迟使未校正时间差在偏移附近形成峰，时间分辨造成展宽，偶然配对形成背景。固定事件包可能遗漏跨包近邻对，本任务不增加另一套搜索算法。

### 4.3 两套直方图与拟合开关

每个候选对计算：

$$
\Delta t=t_{\mathrm{ref}}-t_{\mathrm{channel}}.
$$

将同一 Delta t 分别填入两套直方图，不依赖 Rebin 对齐。两套谱始终生成；“较平滑”指第二套的较粗分箱，保存的仍是原始计数。

- `FIT_ENABLED=false`：保存两套非空谱，不寻峰、不调用 Fit、不附拟合线。
- `FIT_ENABLED=true`：第一套辅助识别峰形，在第二套原始计数上拟合，总拟合函数附在第二套谱上。

保留上下溢出计数供核对。拟合不将事件窗外的零计数 padding 当作本底侧带。

8/10 ns 是时间戳步长，不是额外直方图。同为8 ns的时间差落在8 ns格点，同为10 ns时落在10 ns格点；用2 ns分箱可出现周期空bin。8 ns与10 ns的差值可能落在2 ns格点。找峰时不把这种量化结构当成物理双峰。

### 4.4 峰形、区间与 ROOT 拟合

最多拟合两个相关高斯分量，模型为：

- 单峰：`gaus(0)+pol1(3)`。
- 双峰：`gaus(0)+gaus(3)+pol1(6)`。

处理步骤：

1. 使用细谱的临时平滑副本识别主峰和可信第二峰，原始谱保持不变。平滑尺度以 ns 表示，约50 ns作为工程起值，换分箱后按实际bin宽换算。
2. 从峰尾向两侧寻找可由直线近似的侧带，左右独立扩展，允许不对称区间。连续本底结构变化限制扩展，单bin涨落不直接决定边界。
3. 保留少量连续候选区间，例如局部、适度扩展、较宽三档。每个区间包含完整相关峰区及两侧本底，不裁掉第二峰、不挖除坏bin。
4. 在第二套原始谱上使用 ROOT Poisson likelihood、bin积分平均进行拟合。幅度和sigma为正，拟合区间内本底与模型期望须有效。
5. 有双峰候选时，在相同区间比较单、双峰模型。BIC改善超过10作为双峰的辅助工程判据；不跨不同区间比较BIC。
6. 检查拟合状态、协方差、参数边界及峰区残差。优先选择具有充分且可描述侧带的区间，并报告候选区间间的final_mean变化。扩大范围导致deviance/ndf下降不能单独证明峰位改善。
7. 无稳定解、明显模型不符或峰参数无法分辨时标记review/失败，保留谱和诊断；不增加第三峰或人工例外表。

工程阈值在四个代表通道上核验后集中留在UserDefine；调整需记录依据。范围敏感性如实报告，不设置尚未验证的额外通过门槛。拟合收敛与科学可用性分别报告，deviance/ndf>3作为经验回查提示，不解释为严格显著性检验。

### 4.5 final_mean、面积与误差

单峰取 `final_mean=mu`。双峰按各高斯完整净面积加权：

$$
S_j=\frac{A_j\sigma_j\sqrt{2\pi}}{h},\qquad
o=\mathrm{final\_mean}=\frac{\mu_1S_1+\mu_2S_2}{S_1+S_2},
$$

其中 A 为高斯峰高，h为拟合谱bin宽。权重可直接用 `A_j*sigma_j`，公共因子相消。面积不含线性本底，不对重叠区域重复积分。峰尾严重依赖外推或分量无法分辨时标记需回查。

单峰误差取ROOT的mu标准误；双峰采用联合拟合协方差C传播。令 `w_j=A_j*sigma_j`、`S=w1+w2`：

$$
\operatorname{Var}(o)=JCJ^T,\quad
\frac{\partial o}{\partial\mu_j}=\frac{w_j}{S},\quad
\frac{\partial o}{\partial A_j}=\frac{\sigma_j(\mu_j-o)}{S},\quad
\frac{\partial o}{\partial\sigma_j}=\frac{A_j(\mu_j-o)}{S}.
$$

本底参数的显式导数为零。误差不包含模型选择、事件边界或run内漂移的系统影响；无有效协方差时不编造误差。

目标时间加o后，校正时间差为 `Delta t-o`。单峰中心移至零附近；双峰的加权中心归零，但两个峰不会合并。

### 4.6 decoder 截断值

DecodeAndSortAll将整型ns偏移除以目标通道tick再加到ts，整数除法向零截断。输出：

$$
\mathrm{time\_offset}=q\,\operatorname{trunc}(\mathrm{final\_mean}/q)\quad(\mathrm{ns}).
$$

例如q=8 ns时，+22.7 ns对应+16 ns，-22.7 ns对应-16 ns。该输出已是q的整数倍，可直接作为decoder的ns偏移值；预计残余中心为 `final_mean-time_offset`。不自动回填crate。

q从目标通道sr取得。同一通道出现不同q时，time_offset留空并说明原因；final_mean仍按实际拟合状态报告。

## 5. 输出约定

两种拟合开关状态都输出三个基础文件，目录按UserDefine设置：

| 文件 | 内容 |
|---|---|
| `time_offset_<run>.root` | 顶层两套非空直方图；拟合开启时第二套附拟合函数；保存参考及处理配置元数据 |
| `time_offset_<run>.csv` | 必含 `cid,sid,ch,final_mean,time_offset,status`；数值单位ns；附必要的误差、分量面积、模型和拟合区间 |
| `time_offset_<run>.md` | 简要记录输入/run、配置、处理条数、拟合状态统计及重点回查通道 |

直方图名为 `cid<cid>_sid<sid>_ch<ch>_<binWidth>`，例如 `cid0_sid2_ch10_2ns`、`cid0_sid2_ch10_24ns`；宽度按实际参数生成。

逐张检查 `GetEntries()>0` 后写出；参考不自配对，空白参考谱不保存。仅上下溢出有计数的谱保留并标记显示范围内无计数，不进行峰拟合。

CSV状态统一区分 `reference`、`not_fitted`、`no_peak`、`fit_failed`、`review`、`ok`。参考两数值为0；未拟合、无峰和失败时数值留空；可计算但需回查的候选值标review。不得用0替代未知结果，不把review当校准通过。

ROOT及编译文件不提交Git；源码、配置说明、小型CSV/MD和必要验证记录按项目规则同步。

## 6. 实施步骤与阶段交付

| 步骤 | 工作 | 完成依据 |
|---|---|---|
| 1 | 建立main.cc、UserDefine.hh、TimeOffset类及Makefile | 直接make成功；UserDefine变更触发重编译 |
| 2 | 实现整数cut、必传run、显式参考及路径配置 | 缺参/非法配置/参考被cut时明确退出 |
| 3 | 按sort事件包生成两谱，处理最后一个事件包 | 确定性命中样例核对配对、符号和计数 |
| 4 | 实现单/双峰及候选范围拟合 | 代表性已有谱回查与模型诊断 |
| 5 | 输出面积加权中心、误差、截断值及三个文件 | CSV与ROOT参数、正负截断值一致 |
| 6 | 有限真实样本验证，再处理完整6015 | 记录实际读取范围及完整运行命令；结果另存，不覆盖旧产物 |
| 7 | 更新README、简要执行报告和版本白名单 | 文件范围检查后提交并推送小型产物 |

已有谱仅作可选回查，归档位置为 `archive/20261018-time-offset/timeOffset/time_offset/time_offset_6015.root`；新实现使用真实输入重新填谱，以下通道作为验证样例：

| 通道 | 重点 |
|---|---|
| c0_s2_ch10 | 单峰且侧带较平稳，检查扩大范围 |
| c0_s2_ch9 | 单峰模型与中心稳定性 |
| c0_s2_ch6 | 双峰分解及面积加权中心 |
| c1_s3_ch7 | 变化本底下的局部拟合范围 |

有限样本使用保存的验证入口或小型验证程序，不临时截断输入文件；正式程序仍采用 `./time_offset <run>`。所有实际命令、样本条目范围、参数和验证结果保留在任务记录中。开始完整数据处理前，有限样本的读取、配对、保存检查必须通过。

## 7. 验收标准

- **接口与复用**：直接make；run必填；参考和实验参数来自UserDefine；改变run、参考、cut、分箱无需改核心算法。
- **cut与事件包**：-1端点、闭区间、绝对值W边界、Ge重复覆盖、CsI多命中、参考排除和末包处理均有可运行检查。
- **两套谱**：本实验分箱为2001 bins/±2001 ns与168 bins/±2016 ns；±2000 ns测试值落入普通bin。开关不影响两谱计数，包含flow后总计数一致；仅保存非空谱。
- **拟合与范围**：使用第二套原始计数；至多两个高斯加pol1。回查四个代表通道，保存实际拟合范围及范围敏感性；不以降低deviance/ndf为唯一成功条件。
- **面积与误差**：合成检查覆盖等面积中点、等高不等宽的sigma权重、交换分量不变、单分量极限和整体幅度缩放不变；协方差传播与数值差分一致。合成数据不混入实验结果。
- **截断与输出**：正负final_mean均向零截断，使用目标tick；ROOT顶层命名及拟合函数正确，CSV必要列齐全、空值/status正确，MD简短完整。FIT_ENABLED关闭仍生成三个文件。
- **结果边界**：工程验证与标定质量分别报告；对不可靠通道保留原因，不保证所有通道均能给出可靠offset。

## 8. 交接状态

用户已明确授权本计划实施。程序在独立工作区 `.omx/coordination/workspaces/time-offset-impl/timeOffset/time_offset/` 建立；真实输入只读，未改原decoder/crate或归档结果。已完成第6节步骤1–5及1000万条有限样本读入/配对/保存核对，步骤6已完成全部266,414,896条处理及ROOT/CSV回读：23个ok、121个review、1个reference，拟合收敛不代表校准通过；步骤7的源码、说明、结果副本及实际验证记录已备齐，交付采用项目协调器与可信检查/hooks。执行依据、命令、工程阈值与真实结果集中记录于 `timeOffset/time_offset/execution.md`；后续更新交付和验证状态，不另建计划。旧目录继续完整保留于归档，清单见 `analysis/20261018-archive-time-offset/manifest.json`。
