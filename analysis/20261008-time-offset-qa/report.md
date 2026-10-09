# UltraQA Report

结果：固定源码的有界合成 QA 通过。重新编译无警告；24 项工程、73 项数值自检通过。27 条 CLI 命令和 48 条断言通过。独立 CLI 验证见 `verification.json` 中逐条命令、退出码、输出与断言。未发现需要移交实现人员的缺陷。

源码：`cc efff88f30da1362969a3f70222572af9ad4a23e50829a340938557c72b1f9941`；`hh febd8b8130884d36afd7bfb5b9b27b4f63fb15063d057ea9539fc668ed3dacf3`。运行前后哈希一致。

## 目标与范围

验证输入损坏不会伪造成功、输出不会覆盖链接目标、留出消费状态及冻结候选不能被静默篡改，并覆盖慢漂移及双峰候选的已修订逻辑。仅在临时目录生成 C++ 合成数据；不打开真实实验 ROOT 或留出区间，不修改实现目录。Python 只负责进程编排和结果断言。通过完整场景矩阵及清理后停止。

| 场景 | 实际结果与证据 |
|---|---|
| 正常结果 | 工程、数值自检及 diagnostic/invalid/validated/dual_validated 的 artifact 重算均退出 0 |
| 损坏 CLI/ROOT | 缺参数、重复参数、伪 ROOT 验证及读取退出 1；坏输入未产生扫描输出 |
| 坏 ledger 行在有效行之前、缺末尾换行 | verifier 与 validate 均退出 1；原 ledger 保留，未产生验证目录 |
| completion 符号链接／硬链接 | 均退出 1，目标字节保持一致 |
| 部分输出／重试 | 预存目录保留；已消费合成留出再次使用被拒绝，无新增结果 |
| 冻结及结果篡改 | 冻结 digest、offsets.csv、冻结与验证 physical_candidates.csv 的独立篡改均拒绝；恢复后重算通过 |
| 伪成功／缺失结果 | 原 passed=true 报告被严格 mission 重写为 passed=false，退出 3；合成单次验证不满足真实分组任务 |
| JSON 特殊字符 | 独立构造含引号、反斜杠、tab、CR 和 LF 的错误路径；mission 退出 3，文件与 stdout 均可解析且内容一致，reason 逐字符保留 |
| 慢漂移／双峰 | C++ 命名自检证明折叠时间桶可掩盖漂移而有序桶拒绝；两物理候选中心不同、独立冻结验证、训练后修改策略拒绝。此项为源码自检证据，不冒称独立实现算法 |

执行命令：

```bash
python3 analysis/20261008-time-offset-qa/qa.py --source /home/ys/data_401/data/chx_20260622/.omx/coordination/workspaces/time-offset-impl-20261009 --cc-sha256 efff88f30da1362969a3f70222572af9ad4a23e50829a340938557c72b1f9941 --hh-sha256 febd8b8130884d36afd7bfb5b9b27b4f63fb15063d057ea9539fc668ed3dacf3
```

普通进程上限 120 秒，编译和 C++ 自检上限 180 秒。四次运行均成功：前两轮覆盖初版固定源码；最终 JSON 转义修复后按新源码重新执行全部矩阵并新增独立 JSON roundtrip。未通过重试掩盖失败。第四轮补齐交付证据 status/checks 字段后完整重跑；最终 verification.json 对应第四轮完整输出，checks 记录整个 harness 的退出 0，各预期失败命令仍保留真实非零退出码。原科学源码 ccc6edbf7cbb2e3b4e4f7ed81aecb833418cde0af08fb2d41b3af2553e11647c 的 26 命令／43 断言证据保留在 verification-ccc6.json，不冒称新源码结果。

## 清理与限制

临时二进制、合成 ROOT、ledger、链接和部分输出均由 TemporaryDirectory 清理，证据确认临时目录不存在；无后台进程、实现源码修改或原始数据写入。仅保留本目录计划、可重复测试脚本、报告和 JSON。

中断恢复用预存部分输出和重复消费状态模拟，未发送真实 kill 信号。未验证磁盘耗尽或并发竞争。本 QA 不声称真实 A/B/C 标定完成或全部 run 可用；真实数据任务及独立科学审查由主控验收。合成验证中的故意失败是预期行为，不计作通过真实 mission。

ULTRAQA COMPLETE: Goal met after 4 bounded passes; scoped synthetic/CLI QA only.
