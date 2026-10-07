#!/usr/bin/env python3
"""Install only the project automatic-delivery skill and Stop check."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = '''---
name: task-tag
description: 项目文件更改完成后自动验证、commit、push；交付标签用作者与简短任务命名，以中文说明依据、改动和真实成果；Stop 检查督促完成同步。
---

# 自动提交、推送与交付标签

用户已持续授权本项目文件更改完成后自动 commit 和 push，包括代码、计划、规范、技能、hooks、记录和小型结果。先保存任务计划，执行并验证，然后连续完成同步，不再询问是否提交或推送；用户的暂停、取消或更新范围仍优先。

1. 检查当前差异和远端历史，保留用户更改。使用 `analysis/scripts/project_git.sh`，遵守根白名单、单文件 25 MiB 上限和数据／凭据排除；原始 Ge/CsI 只读。
2. 保存实际验证 JSON 到任务 reports/：`status: passed`、非空 `checks`、每项实际 `returncode: 0`。代码或输入变更后重新检查，不把过期检查视为新行为通过。
3. 使用可查看的同步程序：

```bash
python3 analysis/scripts/project_sync.py sync --task "<简短中文任务>" --message "<English imperative description>" --result "<真实成果>" --basis "<修改依据>" --evidence analysis/<task>/reports/<verification>.json
```

程序检查 origin 指向 `https://gitee.com/chx6/ns_analysis.git`、读取最新远端引用、检查候选文件和暂存对象，复用 `task_delivery.py prepare` 与 post-commit 绑定已验证 Git tree。必要的逻辑提交可先分组，最终交付提交准备总体证据和标签。

4. 标签名称为 `<Git作者>-<简短中文任务>`；说明明确修改者、执行协作、基于什么、改动、真实成果和验证结论。没有历史执行记录时注明未记录，不猜测。名称与说明不写 SHA256、提交编号或精确时间；校验信息留在内部元数据。同名任务在不同提交使用 `-2` 等短序号，不能覆盖旧标签。

5. 正常推送当前分支及准确标签收据中的本次标签，不强推、不推所有标签。核对远端分支 hash 等于本地 HEAD，工作区／索引干净。推送收据在本地忽略的 `.omx/delivery/sync_receipt.json`，不因写完成收据递归产生提交。

Stop hook 只检查本地 Git 状态，发现未提交／未推送工作时请求继续完成；不在 hook 中隐藏联网。重复停止避免无限循环。认证、网络或宿主审批失败时保留已完成提交并如实报告、继续可行恢复，不能伪称已推送；不能修改信任记录或权限绕过宿主。

标签复用本项目已有 muIon-beam 适配；来源在 `analysis/third_party/`。技能两个入口同步维护，实际授权来自用户指令，hook／本地记录不扩大权限。
'''


def main():
    digest = hashlib.sha256(SKILL.encode()).hexdigest()
    for base in ['.agents/skills/task-tag', '.codex/skills/task-tag']:
        (ROOT/base/'SKILL.md').write_text(SKILL)
    hook_file = ROOT/'.codex/hooks.json'
    config = json.loads(hook_file.read_text())
    command = '"/usr/bin/python3" "' + str(ROOT/'analysis/scripts/project_sync.py') + '" hook'
    groups = config['hooks'].setdefault('Stop', [])
    if not any(item.get('command') == command for group in groups for item in group.get('hooks', [])):
        groups.append({'hooks':[{'type':'command', 'command':command, 'timeout':15}]})
    hook_file.write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n')
    lock_file = ROOT/'analysis/third_party/sources.lock.json'
    lock = json.loads(lock_file.read_text())
    item = next(item for item in lock['adaptations'] if item['directory'] == '.agents/skills/task-tag')
    item['entry_sha256'] = digest
    item['project_extension'] = 'Automatic verified commit/push with readable author-change-outcome tags; native Stop checks pending delivery'
    lock_file.write_text(json.dumps(lock, ensure_ascii=False, indent=2)+'\n')
    cache = ROOT/'analysis/code/__pycache__'
    if cache.exists():
        expected = {'project_runtime.cpython-38.pyc', 'check_git_content.cpython-38.pyc', 'verify_project_tools.cpython-38.pyc'}
        assert {path.name for path in cache.iterdir()} <= expected, 'Unexpected legacy directory contents'
        for path in cache.iterdir():
            assert path.is_file() and not path.is_symlink()
            path.unlink()
        cache.rmdir()
    old = ROOT/'analysis/code'
    if old.exists():
        old.rmdir()
    print('Installed mirrored automatic-delivery skill and read-only Stop check; removed known legacy caches')


if __name__ == '__main__':
    main()
