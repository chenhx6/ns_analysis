# Hook failed 排查

当前最有力的解释是回复结束阶段的 Stop hook 超时，置信度中等。尚未取得包含具体 hook 名称、退出码或 stderr 的失败记录，不能认定根因或宣称修复。

| 排序 | 解释 | 置信度 | 依据 |
| --- | --- | --- | --- |
| 1 | Stop 阶段达到超时限制 | 中 | `hi` 的最后 token 记录到 task_complete 相隔 15.007 秒；同步 Stop hook 配置 timeout=15 |
| 2 | 某个 hook 执行错误或被宿主拒绝 | 未确定 | 当前持久化日志缺少命令退出结果，无法排除 |

## 直接证据

- `.codex/hooks.json` 注册 12 个处理项；Stop 包含 OMX 原生 hook（30 秒）与 `project_sync.py hook`（15 秒）。当前所有解释器与脚本入口均存在，不能用“入口缺失”解释当前故障。
- 本次会话 transcript 第 17 行记录时间为 `2026-10-08T01:32:56.771Z`，第 18 行 task_complete 为 `2026-10-08T01:33:11.778Z`；程序读取原始记录计算间隔 15.007 秒。
- 日志定位代理曾在 `/home/ys/.codex/logs_2.sqlite` 读取到相应时间的两条 `hook/started` 与两条 `hook/completed` 通知；正文仅有通知名称及连接数，没有结果字段。活动日志随后清理了这些行，因此此项只能作为先前只读观察，不能重新查询验证。
- 当前只读探测的三个 Git 操作总计约 0.17 秒。它们是同步 Stop hook 的主要 Git 检查，但探测未执行 hook 包装程序；不能据此反推故障时刻的速度。
- 本次会话已出现技能路由注入的规则，说明至少该 hook 曾成功输出上下文，不能把 failed 概括为全部 hook 失效。

## 推断与限制

结束阶段耗时接近 15 秒，支持 Stop 超时假设；仅靠时间关联不能区分具体 hook，更不能确定是磁盘延迟、命令耗时、输入管道等待还是宿主执行问题。程序入口存在也不能证明其运行成功。旧 9 月日志与当前故障无关。

没有更改 hook 配置、超时、信任记录或目录权限，没有重放可能改变 OMX 状态的 hook。若需要确认失败项，最小补充证据是界面失败条目的事件、命令和错误详情；不能仅凭猜测延长超时或关闭 hook。

## 复现诊断

程序：[inspect_hooks.py](../inspect_hooks.py)。实际运行命令：

```bash
python3 analysis/hook_failure/inspect_hooks.py --transcript /home/ys/.codex/sessions/2026/10/08/rollout-2026-10-08T09-31-56-01a11923-76c4-7580-be51-7465ae946493.jsonl
```

结果：[verification.json](verification.json)。其中 `status: passed` 只表示诊断数据收集与检查完成，不表示 hook 已修复或全部运行成功。失败的首次 transcript 字段匹配已按真实记录格式纠正后重新运行通过。

版本同步保留排查开始前已有的 `.codex/config.toml` 状态栏配置改动；其执行者未记录，不属于本次 hook 修复。
