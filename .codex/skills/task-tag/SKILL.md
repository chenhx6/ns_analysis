---
name: task-tag
description: 本项目任务经过验证并提交时自动建立本地 annotated Git tag，将交付提交绑定到实际检查证据。
---

# 任务交付标签

将实际检查结果保存为 `analysis/` 下的 JSON：`status` 为 `passed`，`checks` 为非空数组，每项含检查名称和实际 `returncode`。失败、暂停或只安装了文件时不记录为通过。

任务完成并进入已授权版本交付时自动，先暂存已检查的任务文件和证据，再执行：

```bash
python3 analysis/code/task_delivery.py prepare --task <task-name> --evidence analysis/<evidence-file>.json
bash analysis/code/project_git.sh commit -m "<task-description>"
```

`post-commit` 会核对准备时的 Git tree、当前 HEAD、工作区和证据摘要，自动创建 `t-<task>-<UTC>-<commit>` annotated tag。证据或代码发生变化时标签创建延期，应先重新验证。普通未准备的提交不产生标签。

标签在本地生成；用户要求推送时，正常推送分支和该标签的明确 ref。此能力借鉴 muIon-beam 的任务节点标签，源码来源记录位于 `analysis/third_party/muIon-beam/`；本项目不依赖其物理模型、Windows 路径或 Drive 镜像。
