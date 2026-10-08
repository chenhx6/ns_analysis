# 任务执行计划：英文命名与实时记录本约定

- 创建日期：2026-10-08
- 状态：已完成；规则、迁移、限定清理和初次正常版本交付均已核对
- 用户授权记录：用户要求「文件夹以及文件命名采用英文，防止乱码（记下来）」；并明确 `analysis/experiment_log/record_analysis.md` 是本人实时修改的记录本，无需过于关注。项目约定与任务文件验证后同步使用此前明确的持续 commit/push 授权。

## 目标与范围

将英文文件/目录命名和实时记录本的处理方式写入项目约定；将本会话新建的两份中文计划改为英文名。保留用户记录本的当前内容，不改写或科学审查，不因普通记录编辑反复追问。移除本次代理为无关记录编辑额外建立的临时审查程序与差异副本，保留真实过程说明。

## 输入与依据

只读查看现有 AGENTS.md、README.md、计划模板、两份本会话计划和当前 Git 差异；此前记录本改动的作者已由用户明确为本人。新出现的 `2026-10-08-Git状态报错诊断.md` 不属于本会话文件，不改动其内容或路径。现有来源照片、上游固定源码及原始数据不作批量重命名。

## 预计文件

| 路径 | 操作 | 用途 |
| --- | --- | --- |
| `AGENTS.md`、`README.md`、`analysis/plans/_template.md` | 修改 | 英文命名与实时记录本规则 |
| `analysis/plans/2026-10-08-hook-failure-diagnosis.md` | 从本会话中文计划重命名 | 保留原排查与交付记录 |
| `analysis/plans/2026-10-08-experiment-log-sync.md` | 从本会话中文计划重命名并更新 | 记录用户确认作者、取消多余专项关注 |
| `analysis/experiment_log/verify_record.py` 及本次 reports 中两个生成文件 | 删除 | 删除本会话未交付的多余审查程序和副本，不删除用户资料 |
| `analysis/project_conventions/verify_conventions.py` | 新建 | 验证约定与计划英文路径 |
| `analysis/project_conventions/sync_conventions.py` | 新建 | 在本地忽略的隔离克隆中调用已有同步工具，仅交付本任务文件；失败保留提交供重试 |
| `analysis/project_conventions/reports/verification.json` | 新建 | 本次实际验证证据 |

## 执行与验证

1. 保存本计划。先保留既有 Git 差异和文件来源，限定清理到本会话显式生成文件。
2. 更新约定、模板与计划路径，修正本任务文件内引用；不修改实时记录本。
3. 保存验证程序，运行 `python3 analysis/project_conventions/verify_conventions.py`；验证规则存在、两份计划新路径为 ASCII、旧路径已迁移、临时审查副本已移除。
4. 运行 `python3 analysis/project_conventions/sync_conventions.py`，在 `.omx/delivery/conventions-clone/` 隔离克隆中使用已有 task-tag/project_sync 工具同步明确列出的本任务文件，再以正常快进整合远端。用户记录本和并行任务的工作区编辑保持现状；不提交或推送它们，不因用户的实时编辑把交付扩大为新的审查任务。真实外部审批和并发编辑仍需如实处理。

统计与绘图不适用：本次是项目约定及文件组织变更，不计算实验结果、不生成图表。

## 进度与限制

- 已完成：必要只读检查和计划保存；读取 Ponytail/说人话/task-tag/go-on，清理部分按 ai-slop-cleaner 限定范围。清理无已交付程序消费者；本次记录验证曾实际通过 11 个图片链接，删除额外程序不影响用户记录和现有 Git 工具。
- 关键决策：命名约定用于后续新建文件和目录，迁移仅覆盖本会话中文计划；实时记录保持用户原文。
- 当前阻碍：无。上一轮宿主拒绝的记录编辑未纳入本次交付；用户已明确记录作者和处理意图。本任务通过正常权限审批，仅交付限定的规则与程序文件。
- 结果位置：本计划及 `analysis/project_conventions/reports/verification.json`；实际推送以 `.omx/delivery/sync_receipt.json` 为准。
- 已执行：规则、README、模板已更新；本会话两份计划已迁移；无关记录审查程序/副本已删除；`python3 analysis/project_conventions/verify_conventions.py` 实际通过。
- 网络记录：首次推送命令等待 60 秒超时；只读核对远端 main 已有并行 Git 诊断提交，但没有本次交付标签，尚不能声称本任务已推送。同步程序改为保留隔离克隆及失败提交，供正常重试；不增加隐藏网络行为或强推。
- 重试与诊断：第二次 push 仍等待 60 秒超时，但待推送提交保留在隔离克隆。独立代码审查无交付问题；debugger 离线验证 pre-push 1.068 秒退出 0，发现隔离克隆未继承主仓库既有 credential.helper，且环境有交互 ASKPASS。补齐已存在的认证助手配置，并仅对本次同步关闭交互 ASKPASS；认证内容不写入交付文件、不输出。此为现有 Git 配置兼容修复，无需安装工具或扩展任务。
- 实际成果：补齐既有认证助手配置后，正常推送及原仓库快进均成功；初次成功交付标签 `chx6-命名与记录约定-2`，远端 HEAD 与收据一致。本状态更新仍通过同一正常流程同步；最终收据为 `.omx/delivery/conventions_sync_receipt.json`。
- 下一步：后续新建文件与文件夹采用英文 ASCII 名称；保留用户实时记录本的工作区编辑，不另行审查。
