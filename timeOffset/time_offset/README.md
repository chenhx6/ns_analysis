# 单文件时间对齐

从本目录运行：

```bash
make
./time_offset <run>
```

run 必填且必须为正整数；没有默认 run。编辑 `UserDefine.hh` 配置参考、输入路径与 `{run}` 命名模式、输出目录、整数闭区间 cut、sr/tick、事件窗、两套分箱和拟合开关。修改该头文件后 `make` 自动重编译。当前实验参考 `(0,2,5)`，Ge crate=0，CsI crate=1，W=1999 ns。输出相对运行目录，默认 `..` 即 `timeOffset/`；三个同名结果中任一个已存在即拒绝覆盖。

只读取 `ts,cid,sid,ch,sr`。时间戳 tick 为 sr=125/250 时8 ns，100/500时10 ns，不是ADC采样周期。按第一条通过cut的命中固定起点分包，使用绝对值W（含端点）；Ge每通道保留末次，CsI全部保留，参考取末次，末包也处理。输入倒序仅记录，不另切包。通道存储用实际地址map，取消cut不会受固定数组额外限制。负地址、未知sr、时间溢出、参考缺失等明确报错；保留的crate必须有配置的Ge/CsI命中保留规则。

同一配对的 `t_ref-t_channel` 同时填两套原始计数谱，无附加时间差cut。当前细谱2001 bins、[-2001,2001] ns，拟合谱168 bins、[-2016,2016] ns；分别2 ns与24 ns。非空谱置于ROOT顶层，参考不自配对，flow计数保留。`FIT_ENABLED=false` 仍输出ROOT、CSV、MD，不执行寻峰和拟合。

拟合使用细谱临时高斯平滑（50 ns FWHM）识别峰形；以主峰外300–600 ns外围的平滑计数密度中位数估计局部本底。独立第二峰需满足高度、分离和谷条件；对单峰后显著、连续平滑的肩部残差也提出第二分量候选。所有工程阈值集中在UserDefine，不设通道例外表。

峰尾左右分别扩展96 ns连续侧带块，用块平均密度二阶差分限制结构变化，保留局部/适度/较宽候选。区间落在完整粗bin边界，并排除事件窗外padding。最多两个高斯加直线，在第二套原始计数上调用 ROOT `SQLIRN`（Poisson likelihood、bin积分平均、协方差、不保存淘汰函数）。直线以两个非负端点参数化，与pol1同一模型族；TF1最后两个参数是左右本底端点值，不是pol1截距与斜率。

只在相同范围比较BIC，改善超过10才辅助选择双峰。优先保留侧带可描述、分量可分辨、不触边且峰尾充分覆盖的较宽候选。没有充分候选则保留局部数值解并标明诊断。总体、峰区和侧带deviance、协方差、边界和尾部外推分别检查；`deviance/ndf>3` 为经验回查提示。候选范围的final_mean跨度如实报告，不作为新增通过门槛。范围诊断保留单/双峰BIC；不跨范围比较BIC。

CSV中 `final_mean` 是完整高斯净面积加权中心，误差按联合协方差传播；ROOT保存选中总函数 `time_fit` 和 `<channel>_covariance`。参数顺序为每个高斯的峰高、均值、sigma，再接两个本底端点。`time_offset=q*trunc(final_mean/q)`，单位ns，正负均向零截断；加到目标通道时间，预计残余中心为 `final_mean-time_offset`。目标通道混合tick时time_offset留空。不会自动写回crate。

`reference` 行均值和偏移为0；`not_fitted/no_peak/fit_failed` 的结果数值留空；`review` 是需回查候选；`ok` 只表示当前工程检查通过。固定事件包跨包损失、分箱/量化、模型选择、范围变化及run内漂移不包含在统计误差中。双峰加权中心归零不能使两个峰合并，拟合收敛也不等于全部通道校准通过。

验证入口（真实样本不截断或改写源ROOT）：

```bash
make check
./verify sample 6015 /home/ys/data_401/data/chx_20260622/decode_data/data_C2_6015_6015_wave.root ../sample-final-fit 10000000 1
./verify sample 6015 /home/ys/data_401/data/chx_20260622/decode_data/data_C2_6015_6015_wave.root ../sample-final-off 10000000 0
./verify check ../sample-final-fit/time_offset_6015 1
./verify check ../sample-final-off/time_offset_6015 0
./verify compare ../sample-final-fit/time_offset_6015.root ../sample-final-off/time_offset_6015.root
./verify check ../time_offset_6015 1
```

`verify self` 覆盖cut、固定事件包、正负W、重复命中、末包、flow、面积权重/协方差、合成双峰及输入错误/FIT关闭/不覆盖等检查。`verify inspect <root> <hist-prefix>` 可只读诊断已有2ns/24ns谱；归档旧谱前缀为 `c0_s2_ch6` 等，新谱为 `cid0_sid2_ch6`，旧谱仅作可选方法回查。

完整运行的ROOT及编译产物留本地；源码、验证、CSV/MD同步Git。本次输出CSV/MD的相同副本保存在源码目录，用于现有版本白名单下留存；正常运行输出仍在UserDefine目录。实际命令、样本范围、代表通道与限制见 `execution.md`；机器证据见 `verification.json`。新程序依据最终实施计划；旧目录与结果保持归档原样。
