# time_offset单程序与ROOT回查

- 日期：2026-10-09（Asia/Shanghai）。
- 状态：用户已确定的程序和交付范围；用户已明确本轮“继续精简计划，暂不实现”。
- 依据：用户要求“只需要使用c++作出可以编译的time_offset程序”，包含decode读取、提取填谱、ROOT拟合及数据导出；不繁琐拆分，取消figures/*.svg，直接打开ROOT回查。
- 局部替代：[此前语言分工](20261008-time-offset-method.md)中time_offset任务的Python拟合／配置输出和SVG交付要求。其他项目工作仍按已确定的C++主数据处理、其余Python约定；本任务参考、五分支、时间单位、符号、搜索窗、分箱和分段策略不变。

## 程序与结果

一个显式C++源码 `time_offset/time_offset.cc`，独立编译为time_offset工具；组织与ROOT读写风格参考DecodeAndSortAll。读取、筛选、ns换算、候选配对、两种直方图、ROOT峰拟合、候选offset评估、CSV和多组crate配置导出均在该程序完成，不另建Python分析／绘图程序或通用框架。

必要交付只有源码、保存直方图／拟合函数与结果的ROOT文件、offset CSV、多个run组的crate0/1.dat、必要的Markdown说明。run范围、sr／tick、来源及处理参数优先随CSV／ROOT保存，不预先强制拆成多张映射表。ROOT和编译产物留本地，不提交数据或可执行文件。

## 回查与验收

本任务不要求SVG或其他导出图片，也不把SVG视觉审查列为完成前提。通过ROOT文件打开直方图、拟合和结果回查；检查对象可读、2/24ns bin宽、单位／参考／符号、拟合质量、修正后残差和组配置对应关系。对需要实际观察的谱形仍如实记录观察范围，不能将结构检查冒充看过图形。

本条是用户对time_offset交付方式的明确范围调整，不废止项目其他任务的Python／SVG绘图约定。原始数据、原decoder源码、原编译文件和原crate配置本轮继续保护；批量解码与至少3路并发属于下一阶段。

当前方法与进度见 [处理计划](../analysis/plans/process/20261008-time-offset.md)。
