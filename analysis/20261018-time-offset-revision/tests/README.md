# 开发验证

本目录仅供开发和交付核查。正式使用说明位于项目 `time_offset/time_offset/README.md`，用户日常运行无需本目录。

从项目根执行：

```bash
make -C analysis/20261018-time-offset-revision/tests check
analysis/20261018-time-offset-revision/tests/build/verify check time_offset/time_offset_6015 1 266414896
```

测试编译单元直接编译正式实现以调用内部算法，自检通过单个friend声明核对事件包内部状态；没有复制另一套分析算法。正式可执行文件不包含自检或旧谱检查函数。测试二进制只生成在本目录忽略的 `build/` 中。

`self` 检查cut、固定事件包、正负W、Ge/CsI重复命中、参考排除、末包、flow、面积/协方差及合成双峰；临时ROOT样例检查错误输入、禁止覆盖、拟合关闭及混合tick。`check <结果文件前缀> <预期拟合0或1> [预期处理条数]` 只读核对ROOT/CSV/MD；`compare <a.root> <b.root>` 核对两套结果逐bin一致；`inspect <root> <谱名前缀>` 只读检查已有谱。

有限真实样本验证保持源ROOT只读，输出独立目录：

```bash
analysis/20261018-time-offset-revision/tests/build/verify sample 6015 /home/ys/data_401/data/chx_20260622/decode_data/data_C2_6015_6015_wave.root analysis/20261018-time-offset-revision/tests/build/sample 10000000 1
analysis/20261018-time-offset-revision/tests/build/verify check analysis/20261018-time-offset-revision/tests/build/sample/time_offset_6015 1 10000000
```

样本范围为原树零起始 `[0,10000000)`，不截断源文件。测试输出目录已存在时会拒绝覆盖。原完整执行与验证记录在同任务 `reports/`，历史命令保留执行时路径。
