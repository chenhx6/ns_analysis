# 执行计划：文件变更后自动提交与推送

- 日期：2026-10-07
- 状态：执行中
- 用户授权：今后更改文件后自动 commit 与 push，包括当前已完成任务；沿用先保存计划、再连续执行安全步骤的约定。

## 目标与范围

每次项目文件变更任务完成并验证后，自动检查跟踪范围及大小、提交并推送到 `https://gitee.com/chx6/ns_analysis.git`；结束 hook 检查是否仍有待提交或待推送工作，驱动代理完成同步。原始数据、解码结果、编译产物、缓存及凭据不进入 Git，保留远端历史，不强制推送。此次同步所有当前已审阅更改，包括用户的配置与实验记录修改。

通用工具保持 `analysis/scripts/`。只读检查发现旧 `analysis/code/` 剩下三个 `.pyc` 缓存；清理这些明确的缓存和空目录，不删除未知文件或原始数据。

## 预计文件

| 文件 | 操作与用途 |
| --- | --- |
| `analysis/plans/2026-10-07-automatic-git-sync.md` | 授权、步骤、进度和交付记录 |
| `analysis/scripts/project_sync.py` | 可查看的提交／推送程序及只读 Stop 检查；复用现有 Git 入口、内容检查和交付标签 |
| `analysis/scripts/test_project_sync.py` | 临时本地仓库与本地 bare 远端的实际检查，不连接正式远端 |
| `analysis/scripts/verify_project_sync.py` | 实际新增：当前同步程序、hook、技能、CSV／SVG 与差异的可运行整体验证 |
| `.agents/skills/task-tag/SKILL.md`、`.codex/skills/task-tag/SKILL.md` | 扩展已有交付技能为文件变更完成后自动验证、提交、推送的规范 |
| `.codex/hooks.json` | 加入 Stop 检查，保留现有 OMX／Ponytail hooks 和宿主信任机制 |
| `analysis/scripts/install_project_sync.py` | 按固定范围部署受保护的技能／hook，并登记指纹；不改变权限或信任记录 |
| `AGENTS.md`、`README.md`、安装说明及来源清单 | 更新持续同步授权、自动技能与当前调用方式 |
| `analysis/project_maintenance/reports/automatic_git_sync_verification.json` | 真实程序、边界、自检和既有结果的检查证据 |

不涉及统计检验。预计得到已配置的自动交付技能、结束检查和可复现的本次提交／推送；提交 hash 及推送结果以实际 Git 输出为准。

## 执行步骤

1. 检查差异、作者配置、分支和远端；拉取最新远端引用后确认没有需要合并的远端变化。当前分支 main，已有 origin/main 上游。
2. 先保存同步程序和测试文件，再运行隔离测试。提交前检查所有候选文件路径、单文件 25 MiB 上限和实际暂存对象；调用现有 `task_delivery.py` 绑定通过证据与 Git tree。
3. 更新技能、项目规则和 Stop hook：仍先写计划；安全更改验证完自动提交／推送。Stop 检查只读取本地状态，不在 hook 中暗中联网或绕过权限；重复停止时避免死循环，真实网络／认证／权限阻碍如实报告，不能声称已推送。
4. 正式提交按可独立审核的任务划分；最终交付提交绑定已验证 tree 并产生本地 annotated tag。实际推送包含分支及明确的本次交付标签，不推所有标签，不强推。
5. 验证远端分支 hash 与本地 HEAD 一致、工作区和索引干净，完成计划记录。本地收据可保存在忽略目录中，避免因写“推送完成”记录不断产生新的提交；受跟踪文件在提交前完成记录。

## 完成标准

- 当前改动均已检查并进入合法跟踪范围；原始／大型数据与凭据未暂存。
- 隔离测试实际完成提交、推送及标签检查，Stop 检查能发现脏工作区与未推送提交。
- 自动技能镜像与指纹一致，Stop hook 结构正确；不能把宿主尚未加载的 hook 称为已实际触发。
- 正式推送成功，远端分支等于本地 HEAD；若失败，保留已完成提交和明确错误，继续安全恢复，不伪造同步完成。

## 进度与恢复

- 已完成：同步程序、隔离仓库 commit/push/tag 及边界检查、当前 CSV 对原日志核对、技能双入口与指纹、实际 Stop CLI 输出、旧 code/ 缓存清理。当前专用证据在 `analysis/project_maintenance/reports/automatic_git_sync_verification.json`。
- 用户记录更新：实验记录在上次迁移后新增了标题和 run 汇总，本次原样保留；原迁移基线仍是历史证据，不用旧快照覆盖新正文。
- 当前步骤：Git 专用代理按作者偏好、目录／SVG 和 run.log 任务建立逻辑提交；主代理完成自动同步规范的最终验证提交、标签和正式推送。
- 下一步：调用已保存的 `project_sync.py`，核对真实远端结果；推送成功后保存实际交付记录并再次同步记录本身，本地收据保持忽略以避免递归。
