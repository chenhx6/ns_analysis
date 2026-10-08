# 任务执行计划：实验记录同步

- 创建日期：2026-10-08
- 状态：记录专项审查已收束，后续按项目约定例行同步
- 用户授权记录：用户已持续授权项目文件更改验证后自动 commit/push；本次 Stop 检查提示存在未提交文件。按 go-on 恢复检查和 task-tag 同步，不据 hook 提示扩大权限。
- 后续用户指令：2026-10-08 用户明确该文件是本人实时修改的记录本，「无需过于关注他」。普通差异保留，不开展额外审查或反复请求确认；英文文件命名要求同时适用。

## 目标与范围

保存现有 `analysis/experiment_log/record_analysis.md` 编辑，不改写或恢复其内容。只验证文件安全、图片链接及版本范围；实验事实的准确性不在此次同步验证范围。

## 输入与依据

- 只读输入：该记录、其引用图片与当前 Git 差异。
- 既有改动：合并采集卡更换事件与配图、调整列表和空行、移除一条通道异常描述；用户已确认本人实时编辑，不推断其具体实验判断。
- 项目数据边界、根白名单、25 MiB 单文件限制和持续交付授权。

## 文件与执行方法

| 路径 | 操作 | 用途 |
| --- | --- | --- |
| `analysis/experiment_log/record_analysis.md` | 提交已有编辑 | 原样保留本地内容 |
| `analysis/experiment_log/verify_record.py` | 新建 | 只读检查 UTF-8、本地图片链接与大小 |
| `analysis/experiment_log/reports/sync_verification.json` | 新建 | 实际验证结果 |
| `analysis/experiment_log/reports/pending_record.diff` | 新建 | 当前实验记录差异，供用户核对审批 |
| 本计划 | 新建 | 范围、授权和恢复记录 |

上表是上一轮实际建立的临时检查文件，不代表长期维护需求。用户澄清后，已按 `2026-10-08-english-names-live-notebook.md` 删除未交付的 `verify_record.py`、验证 JSON 和差异副本；用户记录本及来源图片原样保留。

1. 保存计划和显式验证程序。
2. 运行 `python3 analysis/experiment_log/verify_record.py`，确保所引用文件存在且位于项目内；不修改图片，不生成图表。
3. 检查差异及新增文件，使用 `project_sync.py sync --task "实验记录同步" --evidence analysis/experiment_log/reports/sync_verification.json`；获取远端历史，正常推送并核对真实远端及工作区。

## 方法、预计结果与验证标准

统计不适用：此次仅保存文档编辑。交付原有记录、验证程序及 JSON；所有图片引用需有真实项目内文件，文本为有效 UTF-8，提交仍受现有 hooks 的对象范围与大小检查。`status: passed` 不表示实验内容已核实。

## 进度与限制

- 已完成：读取原任务计划、go-on/task-tag 技能和实际差异；保存并运行验证程序，UTF-8、单文件大小及 11 个本地图片引用均通过。
- 关键决策：保留用户实时编辑，不将其描述为 Codex 的编辑成果。上一轮检查曾通过 11 个图片引用；用户澄清后取消专项审查，删除多余程序/副本，按正常版本安全检查处理。
- 运行记录：`python3 analysis/experiment_log/verify_record.py`；首次运行发现 Python 3.8 的相对 `__file__` 路径不能直接做绝对路径比较，增加 `.resolve()` 后重新执行通过。
- 历史阻碍：上一轮命令在进程创建前被宿主自动审批拒绝，理由是实验记录作者未知且与 hook 任务无关。该次未提交或推送；用户现已明确本人编辑及无需额外关注的处理意图，不再以未知作者推断重复追问，后续审批使用最新用户证据。
- 结果位置：后续规则与验证见 `analysis/project_conventions/reports/verification.json`；实际推送收据 `.omx/delivery/sync_receipt.json`。
- 下一步：按新的英文命名与实时记录本约定完成例行同步，保持宿主权限边界。
