#!/usr/bin/env python3
"""Install mirrored delivery guidance and explicit employee lifecycle hooks."""
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

1. 员工任务从 `session_coordinator.py create` 返回的独立工作区开始，使用 `launch` 启动 CLI，或在该目录新开 App session。同一任务多员工分别分配文件范围；原始 Ge/CsI 只读。主目录作为管理与整合入口，不在其中并发编辑任务源码。
2. 保存实际验证 JSON：`status: passed`、非空 `checks`、每项实际 `returncode: 0`。有报告的任务放在 `analysis/YYYYMMDD-topic/reports/`；无需报告时优先复用有效证据，否则保存最小的 `analysis/YYYYMMDD-topic/verification.json`，不强制 reports 目录或叙述性报告。日期为任务开始日（Asia/Shanghai），跨日和旧任务沿用原目录。代码或输入变更后重新检查，不把过期检查视为新行为通过。
3. 在员工工作区复用已有同步程序，并提供合并后可重跑的检查命令；可调用已有测试或工具，无需另建包装脚本：

```bash
python3 analysis/scripts/project_sync.py sync --task "<简短中文任务>" --message "<English imperative description>" --result "<真实成果>" --basis "<修改依据>" --evidence <实际验证JSON路径> --check "<已有测试或可重复验收命令>"
```

员工入口检查完整源码范围并冻结本地提交与 outbox，不直接推送主分支。CLI 启动器收集成果；App 手动工作区在管理 session 运行 `python3 analysis/scripts/session_coordinator.py collect --employee <id>`。`awaiting_collection` 只表示提交已保留，不能声称已推送。控制端在项目整合锁内合并、用候选目录专用真实沙箱重新验证，沿用可信对象检查与 hooks，正常推送并核对真实远端。无沙箱、合并冲突、网络或审批失败时保留成果；用 `integrate --submission <id>` 恢复，不强推、不回滚他人成果。

管理 session 的规范维护或实时记录本例行保存仍可使用上述同步程序，去掉员工 `--check`，并用 `--files <明确文件列表>` 限定交付；不收集其他员工文件。候选文件和 Git 对象继续受根白名单、25 MiB、数据与凭据文件排除检查。证据必须与暂存内容一致，不能拿旧证据证明合并后的行为。

4. 标签名称为 `<Git作者>-<简短中文任务>`；说明明确修改者、执行协作、基于什么、改动、真实成果和验证结论。没有历史执行记录时注明未记录，不猜测。名称与说明不写 SHA256、提交编号或精确时间；校验信息留在内部元数据。同名任务在不同提交使用 `-2` 等短序号，不能覆盖旧标签。

5. 正常推送当前分支及准确标签收据中的本次标签，不强推、不推所有标签。员工交付状态按 submission 保存；整合目录、冲突目录和本地收据不提交。核对真实远端，保留主目录的实时编辑；主目录刷新被本地改动阻止时记 `root_refresh_pending`，员工成果仍可已推送，不能丢弃主目录编辑。

Stop hook 只检查当前员工工作区。已冻结并等待收集的成果、冲突或恢复状态给出明确提示，不反复要求重复提交；无员工映射的管理 session 不因其他任务或实时记录本脏文件阻塞。hook 不联网，不修改宿主信任。SessionStart 只提供已登记工作区上下文，不能改变宿主 cwd/沙箱；隔离保障依赖正确的新会话启动入口。认证、网络或宿主审批失败需如实报告。

标签复用本项目已有 muIon-beam 适配；来源在 `analysis/third_party/`。技能两个入口同步维护，实际授权来自用户指令，hook／本地记录不扩大权限。
'''


def main():
    digest = hashlib.sha256(SKILL.encode()).hexdigest()
    for base in ['.agents/skills/task-tag', '.codex/skills/task-tag']:
        (ROOT/base/'SKILL.md').write_text(SKILL)
    hook_file = ROOT/'.codex/hooks.json'
    config = json.loads(hook_file.read_text())
    # Route existing Ponytail hooks through the project skill, preserving mode state.
    for event, entry in [('SessionStart', 'ponytail-activate.js'),
                         ('UserPromptSubmit', 'ponytail-mode-tracker.js')]:
        old = str(ROOT/'analysis/vendor/ponytail/hooks'/entry)
        new = str(ROOT/'analysis/scripts/ponytail_project_hook.cjs')
        for group in config['hooks'].get(event, []):
            for item in group.get('hooks', []):
                command = item.get('command', '')
                if old in command:
                    item['command'] = command.replace('"' + old + '"', '"' + new + '" ' + event)
    command = '"/usr/bin/python3" "' + str(ROOT/'analysis/scripts/session_coordinator.py') + '" hook'
    for event in ['SessionStart', 'Stop']:
        groups = config['hooks'].setdefault(event, [])
        for group in groups:
            group['hooks'] = [item for item in group.get('hooks', [])
                              if 'analysis/scripts/project_sync.py' not in item.get('command', '')
                              and 'analysis/scripts/session_coordinator.py' not in item.get('command', '')]
        groups[:] = [group for group in groups if group.get('hooks')]
        groups.append({'hooks': [{'type': 'command', 'command': command, 'timeout': 15}]})
    hook_file.write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n')
    lock_file = ROOT/'analysis/third_party/sources.lock.json'
    lock = json.loads(lock_file.read_text())
    item = next(item for item in lock['adaptations'] if item['directory'] == '.agents/skills/task-tag')
    item['entry_sha256'] = digest
    item['project_extension'] = 'Isolated employee delivery with explicit scope; verification evidence independent of prose reports'
    override = next(item for item in lock['project_overrides']
                    if item['directory'] == '.agents/skills/ponytail' and item['file'] == 'SKILL.md')
    override['installed_sha256'] = hashlib.sha256((ROOT/'.agents/skills/ponytail/SKILL.md').read_bytes()).hexdigest()
    override['reason'] = 'User requires self-contained concise replies and conditional program/report retention; hooks read the maintained project skill'
    lock_file.write_text(json.dumps(lock, ensure_ascii=False, indent=2)+'\n')
    print('Installed mirrored delivery guidance and employee SessionStart/Stop hooks; host trust unchanged')


if __name__ == '__main__':
    main()
