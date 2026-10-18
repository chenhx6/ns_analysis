# run 6015实施与验证

2026-10-18 用户将本次实现的项目一级目录 `timeOffset/` 重命名为 `time_offset/`。当前源码位于 `time_offset/time_offset/`，结果位于 `time_offset/`；下文实际执行命令、旧工作区路径和原始验证证据保留运行时记录。

本次依据定稿于2026-10-18的 `analysis/plans/process/2026-10-15-time-offset-revision.md` 以及用户本次明确实施授权。独立员工 `time-offset-impl` 在普通Git克隆中执行；旧time_offset/timeOffset归档、原decoder和crate配置、原始数据及外部software均未修改。仅读取授权的event/sort.cc作为事件包结构参考。

## 实现与实际命令

`main.cc`、`UserDefine.hh`、`time_offset.hh/.cc`、`Makefile` 和README建立于 `timeOffset/time_offset/`；验证程序为 `verify.cc`。ROOT 6.34.08、g++、C++17，直接make，函数及关键算法有简短注释。配置来自UserDefine，run必填。正式输出配置 `..`，从源码目录运行即写本工作区的timeOffset；完整结果交付到主项目同名目录，CSV/MD在源码目录留相同版本副本供现有白名单同步，ROOT与可执行文件不提交。

在员工目录的 `timeOffset/time_offset/` 执行：

```bash
make -j2 all verify
./verify self
./verify sample 6015 /home/ys/data_401/data/chx_20260622/decode_data/data_C2_6015_6015_wave.root ../sample-final-fit 10000000 1
./verify sample 6015 /home/ys/data_401/data/chx_20260622/decode_data/data_C2_6015_6015_wave.root ../sample-final-off 10000000 0
./verify check ../sample-final-fit/time_offset_6015 1
./verify check ../sample-final-off/time_offset_6015 0
./verify compare ../sample-final-fit/time_offset_6015.root ../sample-final-off/time_offset_6015.root
./time_offset 6015 > ../full-run.log 2>&1
./verify check ../time_offset_6015 1
```

有限样本是原ROOT零起始范围 `[0,10000000)`，没有临时截断输入文件。两种拟合开关均读取1000万条，得到7,380,959个事件包、372,624个含参考包和288张非空谱；两种开关各bin（含flow）计数一致。仅做文件读取格式、配对和输出等工程验证；样本统计量不足的通道不强行给值。正式完整范围 `[0,266414896)`，原ROOT只启用五个标量分支，波形/能量/CFD未参与。

## 核对与阈值依据

确定性检查覆盖-1端点cut、闭区间、正负W及固定起点、Ge末次/CsI全部、末次参考、末包、参考排除、正负2000ns普通bin、flow一致、目标tick正负向零截断。面积权重检查包含等面积中点、等高不等宽、分量交换、单分量极限、整体幅度缩放；联合协方差传播与中心差分一致。合成双峰仅用于内存检查，与实验结果分离。

I/O检查覆盖缺分支、未知sr、参考缺失、同通道混合tick、FIT关闭和不覆盖；10项接口/编译检查覆盖缺run/无效run、参考被cut、非法cut/轴范围和UserDefine重编译，详见 `interface_checks.json`。完整结果逐行回读ROOT/CSV，核对计数、非空谱、附加函数、面积加权中心、保存的联合协方差与CSV误差、截断值及状态/空值。

归档谱只作四个代表通道的方法回查，新谱全部重新读取真实输入生成。50ns FWHM平滑抑制量化格点；发现c0_s2_ch6为重叠肩峰，使用同区间单峰拟合后的显著平滑残差提出第二分量，再用原始计数likelihood/BIC选择，未加通道例外。c1_s3_ch7的变化本底使全局本底过低，改为主峰外300–600ns局部外围中位数估计，峰尾左右独立按96ns侧带块扩展，二阶差分4sigma限制结构变化。三个候选扩展尺度为1/2/4块，至多两个高斯加直线；BIC改善阈值10。宽区间依赖尾部外推时不优先选取。工程阈值在UserDefine集中保存，ROOT配置元数据同步记录。

独立只读代码审查发现侧带残差失配可能未单独标review，已修正并复核；语法/警告检查、有限样本回读复核均通过。没有把总体deviance下降当作峰位改善证据。此流程未另行制作计划或启用目标模式。

## 完整结果与限制

处理266,414,896/266,414,896条，全部通过地址cut；179,145,148个事件包，10,144,330个含参考包/参考命中，保留序列无时间倒序。145个观察通道含参考；288张非空原始计数谱，参考空谱不保存。144个目标通道数值拟合有效，其中单高斯85、双高斯59；23个ok，121个review，另1个reference。此处ok仅指当前工程条件下未触发回查，未执行独立物理校准验证或回写crate。

四个代表通道如下，均为review，误差仅是选中模型内统计标准误：

| 通道 | 模型 | final_mean ±统计误差(ns) | time_offset(ns) | 区间(ns) | deviance/ndf | 候选中心跨度(ns) |
|---|---|---:|---:|---|---:|---:|
| c0_s2_ch10 | gauss_pol1 | 15.344 ± 0.526 | 8 | [-360,336] | 27.632 | 1.526 |
| c0_s2_ch9 | gauss_pol1 | 24.341 ± 0.497 | 24 | [-432,456] | 10.067 | 0.884 |
| c0_s2_ch6 | double_gauss_pol1 | 68.942 ± 0.491 | 64 | [-480,456] | 4.654 | 0.407 |
| c1_s3_ch7 | gauss_pol1 | -154.498 ± 1.815 | -150 | [-672,264] | 3.177 | 33.700 |

最大候选范围中心跨度104.632ns，未设额外通过门槛，不能把它忽略或当成已包含的统计误差。c1_s3_ch7的较宽区间出现双分量候选且中心移至约-187.699ns、依赖尾部外推；最终保留较局部的单峰值-154.498ns，仍为review，范围敏感性33.700ns保留。c0_s2_ch6加权中心约68.942ns，其两个分量中心约9.894和94.418ns；校正只能移动加权中心，不能合并双峰。

回查原因可同时出现，逐通道完整细节见CSV：

- `deviance_ndf_gt_3`：100个通道。
- `peak_residual_structure`：118个通道。
- `sideband_model_mismatch`：27个通道。
- `tail_extrapolation`：3个通道。

Poisson/线性本底/最多两个高斯是本次限定模型，并不保证对全部谱形充分。deviance/ndf>3仅为经验提示，不作严格显著性检验。误差不含事件包跨界损失、模型选择、范围变化、run内漂移；固定事件包和瞬发近似按用户计划沿用，未新增其它搜索算法。参考0不等于独立绝对时间标定。没有绘制或导出图像；本任务按计划交付可由ROOT打开回查的直方图与函数。

结果位于 `timeOffset/time_offset_6015.root/.csv/.md`；完整运行本地日志位于同目录 `full-run.log`。源码目录的CSV/MD与输出副本逐字一致。机器验证证据见 `verification.json`；版本交付状态以真实收据及远端核对为准。
