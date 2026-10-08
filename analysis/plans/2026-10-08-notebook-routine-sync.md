# 任务执行计划：实时记录本例行同步

- 创建日期：2026-10-08
- 状态：原文快照和例行安全验证已完成；本次版本交付结果记录在 `.omx/delivery/notebook_sync_receipt.json`
- 用户授权记录：用户已持续授权项目文件验证后自动 commit/push；当前规则明确实时记录本的普通差异原样保留并例行同步，不额外审查、改写或反复确认。本次 Stop 提示后核对，仅该记录本尚未提交。

## 目标、范围与依据

原样保存 `analysis/experiment_log/record_analysis.md` 当前编辑，并完成正常推送；不改写文本、不分析实验内容、不检查图片或重新建立记录专项审查程序。只复用既有 Git 对象范围、文件大小和凭据文件排除检查。原始数据、照片、hooks、技能和生产协调程序不变。

## 文件与程序

| 路径 | 操作 | 用途 |
| --- | --- | --- |
| `analysis/experiment_log/record_analysis.md` | 原样提交当前编辑 | 用户实时记录 |
| 本计划 | 新建 | 例行交付范围与授权依据 |
| `analysis/notebook_sync/reports/verification.json` | 新建 | 实际版本安全检查的命令、退出码与输出 |

程序复用 `analysis/scripts/check_git_content.py`、`project_git.sh`、`project_sync.py`；无实验数据解析、统计、绘图或新增专项审查程序。

## 执行与验证

1. 在 `/tmp/chx-notebook-sync.*/checkout/` 从已提交历史建立隔离克隆，仅复制当前记录本和本计划。记录本只读复制，不修改主工作区。
2. 在克隆暂存这两个文件，执行 `git diff --cached --check` 和 `python3 analysis/scripts/check_git_content.py`（`GIT_DIR`、`GIT_WORK_TREE` 显式指向克隆），保存真实检查 JSON，再复制至克隆。检查只判定 Git 范围与对象安全，不证明实验内容。
3. 使用 `project_sync.py sync --task "记录本例行保存" --message "Save the current live notebook edits" --result "原样保存用户实时记录本编辑并完成例行版本同步" --basis "用户持续版本交付授权及实时记录本例行同步规则" --evidence analysis/notebook_sync/reports/verification.json`。复用既有作者与认证助手，不显示或提交凭据；fetch 后正常 push 当前分支及准确标签。
4. 核对真实远端后，快进原项目分支并仅更新本次三个文件的索引；保持记录本工作区内容原样。若期间用户继续编辑，保留较新内容，不恢复旧快照，也不因新编辑扩展专项审查。

## 完成标准与进度

- 当前快照通过常规对象检查、提交并正常推送；远端分支和准确标签核对一致，交付收据保存于本地忽略的 `.omx/delivery/`。
- 没有新编辑时主工作区和索引干净；有新编辑时如实说明剩余状态，不覆盖用户后续编辑。
- 已完成：必要只读检查、本计划、隔离克隆原样复制和两项常规 Git 检查；暂存差异检查及既有对象范围/大小/凭据文件排除程序均实际退出 0，证据已保存。输入记录为 5248 字节，原项目分支与上游一致，原项目索引无暂存改动。
- 当前阻碍：无；网络或宿主审批失败时保存已完成结果并如实报告，不绕过权限。
- 交付流程：随后由现有 `project_sync.py` 执行正常提交、准确标签推送与真实远端核验；收据保存到本地忽略的 `.omx/delivery/notebook_sync_receipt.json`。完成结果以收据和真实远端为准，不把此处计划文字当作已经推送的证据。
- 后续原则：用户继续编辑时保留新内容；本次不建立实验记录专项审查或防撞机制。
