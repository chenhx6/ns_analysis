# 任务执行计划：恢复 Codex 启动与原生 resume

- 日期：2026-10-08
- 状态：修复和实际验收完成，正在提交本次明确范围
- 用户授权记录：用户报告启用 Bash 项目 source 后普通 codex 因数据盘 symlink ENOSYS 无法启动，基本 codex resume 也被阻止；本次修复已授权启动回归，先恢复可用性。保留用户已注释的 Bash source，不擅自重启/登录模型或迁移已有会话。项目验证后按持续授权提交推送，保留所有并行任务改动。

## 目标与输入

修复启动路径对符号链接的依赖，恢复无员工选择器的原生 resume/fork 行为，同时保留显式员工恢复的隔离。输入为用户真实 ENOSYS 日志、已有入口/coordinator/runtime 与回归；实际 `.bashrc` source 当前已由用户注释，不重新启用。现有失败员工 `cli-73974d2b461d4c45` 与其他工作区保留。

## 文件与方法

| 路径 | 操作与用途 |
| --- | --- |
| `analysis/scripts/session_coordinator.py` | 修复员工配置使用主安装的只读绝对资产路径，不创建 dist/node_modules symlink |
| `analysis/scripts/project_runtime.py` | 员工 OMX 入口使用共享只读安装源码，cwd/缓存仍在员工目录 |
| `analysis/scripts/codex_entry.py` | 未指定员工的原生 resume/fork 原样转交真实 CLI，不创建员工或更改原cwd |
| `analysis/wsl_codex_entry/test_entry.py`、`analysis/session_coordination/test_coordination.py` | 复用现有测试，补ENOSYS、原生恢复、实际资产路径和中断重试验证 |
| 既有相关 usage/README/AGENTS、本计划 | 更正普通resume与原生/员工模式的边界，不另建叙述报告 |
| `analysis/20261008-codex-startup-recovery/verification.json` | 本次最小机器证据，实际命令/退出码与限制 |

不涉及统计、图表或科学结果；无需额外执行脚本。先追踪所有调用者，保留现有并行工作流策略修改，不回滚 run_log 移动、用户记录本或未完成的规范任务。

## 执行与验收

1. 保存计划，先修正恢复转发与无链接员工配置。小样本在真实数据盘验证 mkdir/写普通文件和安装路径，无科学输入输出，不打开付费模型。
2. 复用并补小型临时仓库/假CLI测试，真实模拟 `Path.symlink_to` 抛 ENOSYS 时仍能员工启动；无需symlink的编译资产路径存在。无选择器 resume/fork、嵌套 exec resume 和保留原argv/cwd必须通过。
3. 现有18组并发/沙箱验收重新检查已变源码；沙箱权限需真实审批，不把mock或tmp文件系统当成该数据盘已验证。已失败员工创建可幂等恢复，不删除其目录。
4. 普通 codex 可用性以实际版本/帮助与真实入口路径检查为据，模型会话和付费调用未测试则明确。用户已注释个人Bash段保持不变；当前加载函数可用 `command codex` 临时绕过。
5. 仅同步本次明确文件，避开正在修改的规范、根迁移和记录本；实际远端验证前不声称推送。更新计划完成记录及最终使用方式。

## 风险与进度

- 已知根因：员工配置调用 symlink_to，在真实数据盘 ENOSYS；入口主动拒绝无员工绑定resume，是此前错误的功能限制。之前测试只在支持symlink的/tmp并用假CLI，没有覆盖真实安装路径。
- 当前其他任务同时更改 coordinator 和工作流策略；在现有内容上局部修复，不替换整文件。数据目录、信任、登录、保护权限不变。
- 已完成：移除员工配置所有symlink调用；编译资产指向主安装，员工runtime使用INSTALL_ROOT且保留cwd。普通resume/fork在管理验证前原样转交，补原生参数arity和中断creating重试；重试保留旧base。12组入口/实际子进程回归通过，模拟真实ENOSYS并验证无链接资产和员工cwd。用户真实失败ID创建在同一数据盘原目录恢复为active、旧base不变；实际Codex从该员工目录help退出0，source函数下真实resume --help退出0，不调用模型。
- 当前状态：用户注释的Bash source保持原样；原始数据/记录本/并行工作流策略任务不改写。原18组并发/沙箱回归在获准的真实namespace环境退出0；最小JSON保存实际命令、成功检查、源指纹及未开付费session的限制。
- 结果位置：`analysis/20261008-codex-startup-recovery/verification.json`，复用已有源码及测试，不新建叙述性报告或验证脚本。
- 只读复核：debugger核对无链接资产、员工cwd、原生resume参数arity、creating原地重试和原base保留，未发现剩余本次阻断项。其独立检查不冒充额外模型调用或完整测试重跑。
- 下一步：只读复核后按明确任务文件正常提交与真实远端核对，保留用户实时记录本和个人Bash注释状态。
