---
name: farmer
description: 监督与恢复 Codex Desktop/CLI 会话的瞬态故障（模型容量不足、限流、超时与临时不可用）；具备持久紧急停用与熔断保护。
triggers: [farmer, session-recovery, session-supervision, transient-recovery]
---

# farmer 会话监督与瞬态恢复

来源：`analysis/third_party/muIon-beam/.codex/skills/farmer/SKILL.md`；来源提交见 `analysis/third_party/sources.lock.json`。
farmer 专责 Codex 会话的瞬态中断监督与自动恢复，不负责任务关闭、发布或代码同步（由项目编排层和 task-tag 依据完成证据执行）。

## 核心机制与安全边界（ADR-008）

1. **持久紧急停用开关（Emergency Pause）**：
   - `_work/current/farmer/control.json`（或 `FARMER_CONTROL_PATH`）为本机持久控制开关。
   - 当 `disabled: true` 时，`ensure`、`start`、`once`、`retry` 均为无操作（no-op），绝不向队列发送消息。
   - 停用开关不受常规任务结束影响，必须由显式 `farmer.mjs enable` 解除。
2. **熔断器与尝试上限（Circuit Breaker）**：
   - `max_attempts` 默认严格限制为 3。
   - 若队列已接受但在 `watchdog_ms`（默认 30 秒）内未启动新 turn，状态转为 `queue-stuck` 熔断，绝不对同一 `event_key` 重复投递。
   - 达到最大尝试次数后转为 `manual-attention-required`，必须由用户新输入或显式 `farmer.mjs retry --session <id>` 解除熔断。
3. **跨进程原子锁（Recovery Lock）**：
   - 恢复队列投递受 `_work/current/farmer/recovery.lock` 保护（TTL 60 秒），自动检测并清理已退出的失效进程，防止并发恢复风暴。
4. **范围限定与只读审查**：
   - 仅监控工作区位于本项目（`/home/ys/data_401/data/chx_20260622`）的会话。
   - 读取 `$CODEX_HOME/sessions/**/*.jsonl` 会话事件，不读写内部 SQLite 数据库，不缓存用户提示词或模型输出正文。
   - 仅对白名单瞬态错误执行恢复：`server_overloaded`、`rate_limit_exceeded`、`temporarily_unavailable` 及模型容量超载等匹配项；认证、权限、取消、上下文超长、参数错误等硬性错误直接标记人工关注，绝不自动重试。
5. **恢复消息与上下文保留**：
   - 发送固定的恢复指令：
     ```text
     [farmer resume]
     Continue the existing task from the last completed checkpoint.
     Preserve the original objective, context, files, model, and current working state.
     Do not reinterpret the task or start a new one.
     ```
   - 保持原线程、模型与工作区上下文。

## 常用 CLI 命令

```bash
# 查看 farmer 运行状态与会话健康
node .agents/skills/farmer/farmer.mjs status

# 单次扫描并尝试恢复（支持 --dry-run）
node .agents/skills/farmer/farmer.mjs once
node .agents/skills/farmer/farmer.mjs once --dry-run

# 确保守护进程在后台运行
node .agents/skills/farmer/farmer.mjs ensure

# 前台启动监督循环
node .agents/skills/farmer/farmer.mjs start

# 停止正在运行的守护进程
node .agents/skills/farmer/farmer.mjs stop

# 紧急停用（禁止所有自动启动与恢复队列）
node .agents/skills/farmer/farmer.mjs disable --reason "user requested pause"

# 重新启用
node .agents/skills/farmer/farmer.mjs enable

# 手动清除熔断并针对指定会话重试
node .agents/skills/farmer/farmer.mjs retry --session <SESSION_ID>
```
