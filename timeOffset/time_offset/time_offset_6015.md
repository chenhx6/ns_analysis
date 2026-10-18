# 单文件时间对齐结果

输入：`/home/ys/data_401/data/chx_20260622/decode_data/data_C2_6015_6015_wave.root`；run=6015。

读取条目：266414896 / 266414896（零起始范围 [0,266414896)）；保留：266414896；地址cut排除：0。事件包：179145148；含参考包：10144330；参考命中：10144330；保留序列时间倒序：0。

配置：`ref=cid0_sid2_ch5;dt=t_ref-t_channel;window_ns=1999;Ge=0:last;CsI=1:all;fit=1;cid_cut=0:1;sid_cut=0:16;ch_cut=-1:-1;fine=-2001:2001:2001;fit_hist=-2016:2016:168;smooth_fwhm_ns=50;second_min_ns=72;bic_improvement=10;sideband_block_ns=96;min_pairs=100;peak_significance=5;second_height_fraction=0.2;valley_fraction=0.85;tail_fraction=0.05;shoulder_residual_fraction=0.05;local_background_ns=300:600;curvature_z=4;sigma_min_initial_ns=6:36;deviance_review=3;component_significance=3;sideband_blocks=1:2:4:;sr_ticks_ns=125:8|250:8|100:10|500:10|`。完整工程阈值见同版本 UserDefine.hh。

- ok：23
- reference：1
- review：121

数值拟合有效：144，其中双高斯：59。候选区间间 final_mean 最大跨度：104.632 ns。

final_mean 为高斯完整净面积加权中心，time_offset 为按目标tick向零截断的ns值；加到目标通道时间。误差来自同模型联合协方差，不含模型选择、事件包边界、范围选择或run内漂移的系统影响。review保留可计算候选，不代表校准通过；deviance/ndf>3只作经验回查提示。固定事件包会遗漏跨包近邻；双峰中心归零不使两峰合并。空谱不写ROOT，上下溢出保留；未拟合和失败数值留空。

CSV range_diagnostics 依次为 low:high:分量数:ROOT状态:协方差状态:final_mean:deviance:ndf:single_BIC:double_BIC；范围跨度仅是敏感性诊断，不设额外通过门槛。

重点回查通道：

- cid0_sid2_ch4: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid2_ch6: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid2_ch8: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid2_ch9: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid2_ch10: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid2_ch11: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid3_ch4: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid3_ch5: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid3_ch6: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid3_ch8: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid3_ch10: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid3_ch11: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid4_ch0: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid4_ch1: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid4_ch2: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid4_ch3: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid4_ch4: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid4_ch5: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid4_ch6: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid4_ch7: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid4_ch9: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid4_ch10: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid5_ch1: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid5_ch2: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid5_ch5: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid5_ch6: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid0_sid5_ch7: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid5_ch8: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid5_ch9: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid5_ch10: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid8_ch0: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid8_ch1: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid8_ch2: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid8_ch4: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid8_ch5: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid8_ch6: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid8_ch7: review deviance_ndf_gt_3;peak_residual_structure;
- cid0_sid8_ch10: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid2_ch0: review peak_residual_structure;
- cid1_sid2_ch6: review peak_residual_structure;
- cid1_sid2_ch7: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid2_ch9: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid2_ch10: review peak_residual_structure;
- cid1_sid2_ch12: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid2_ch13: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid2_ch14: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid2_ch15: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid1_sid3_ch0: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid1_sid3_ch1: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid3_ch4: review peak_residual_structure;
- cid1_sid3_ch5: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid1_sid3_ch7: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid3_ch8: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid3_ch9: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid3_ch10: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid1_sid3_ch12: review peak_residual_structure;
- cid1_sid3_ch14: review tail_extrapolation;sideband_model_mismatch;
- cid1_sid3_ch15: review tail_extrapolation;
- cid1_sid4_ch2: review peak_residual_structure;
- cid1_sid4_ch4: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid4_ch5: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid4_ch6: review peak_residual_structure;
- cid1_sid4_ch7: review peak_residual_structure;
- cid1_sid4_ch8: review peak_residual_structure;
- cid1_sid4_ch9: review peak_residual_structure;
- cid1_sid4_ch10: review peak_residual_structure;
- cid1_sid4_ch11: review peak_residual_structure;
- cid1_sid4_ch12: review peak_residual_structure;
- cid1_sid4_ch13: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid4_ch14: review peak_residual_structure;
- cid1_sid5_ch0: review peak_residual_structure;
- cid1_sid5_ch2: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid5_ch4: review peak_residual_structure;
- cid1_sid5_ch5: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid5_ch6: review peak_residual_structure;
- cid1_sid5_ch7: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid5_ch8: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid5_ch9: review peak_residual_structure;
- cid1_sid5_ch11: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid1_sid5_ch12: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid5_ch13: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid7_ch0: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid7_ch1: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid1_sid7_ch2: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid7_ch3: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid7_ch4: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid1_sid7_ch5: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid7_ch6: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid1_sid7_ch7: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid7_ch8: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid1_sid7_ch9: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid7_ch10: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid7_ch11: review deviance_ndf_gt_3;sideband_model_mismatch;
- cid1_sid7_ch12: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid7_ch13: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid7_ch15: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid8_ch0: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid8_ch1: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid8_ch2: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid8_ch3: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid8_ch4: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid8_ch5: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid8_ch6: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid8_ch7: review tail_extrapolation;deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid8_ch8: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid8_ch10: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid8_ch11: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid8_ch12: review peak_residual_structure;
- cid1_sid9_ch0: review deviance_ndf_gt_3;sideband_model_mismatch;peak_residual_structure;
- cid1_sid9_ch1: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid9_ch2: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid9_ch3: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid9_ch4: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid9_ch5: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid9_ch6: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid9_ch8: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid11_ch1: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid11_ch2: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid11_ch3: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid11_ch4: review deviance_ndf_gt_3;peak_residual_structure;
- cid1_sid11_ch5: review deviance_ndf_gt_3;peak_residual_structure;
