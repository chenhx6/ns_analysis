#!/usr/bin/env python3
"""Exercise installed policy hooks and report-free delivery in temporary fixtures."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
REPORT = Path(__file__).parent/'reports/verification.json'
sys.path.insert(0, str(ROOT/'analysis/scripts'))
from check_git_content import RUN_LOG_FILES, permitted
import session_coordinator
import task_delivery


def run(argv, cwd=ROOT, **kwargs):
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=90, **kwargs)
    assert result.returncode == 0, (argv, result.stdout, result.stderr)
    return result.stdout


def verify():
    checks = []
    def passed(name, **details):
        checks.append(dict(name=name, returncode=0, **details))

    for name in ['ponytail', 'task-tag']:
        source = ROOT/'.agents/skills'/name/'SKILL.md'
        assert source.read_bytes() == (ROOT/'.codex/skills'/name/'SKILL.md').read_bytes()
        assert source.read_text().startswith('---\nname: '+name+'\n')
    lock = json.loads((ROOT/'analysis/third_party/sources.lock.json').read_text())
    for item in lock['project_overrides']:
        if item['directory'] == '.agents/skills/ponytail':
            assert hashlib.sha256((ROOT/item['directory']/item['file']).read_bytes()).hexdigest() == item['installed_sha256']
    item = next(x for x in lock['adaptations'] if x['directory'] == '.agents/skills/task-tag')
    assert hashlib.sha256((ROOT/item['directory']/'SKILL.md').read_bytes()).hexdigest() == item['entry_sha256']
    passed('Skill mirrors and installed provenance hashes')

    agents = (ROOT/'AGENTS.md').read_text()
    template = (ROOT/'analysis/plans/_template.md').read_text()
    for text in [agents, template]:
        assert 'YYYYMMDD-topic' in text and 'verification.json' in text
        assert '无需额外' in text and '可复跑' in text
    assert '执行逻辑必须保存在' not in template
    passed('Scientific reproduction retained; optional scripts/reports and dated directories documented')

    with tempfile.TemporaryDirectory(prefix='workflow-policy-') as temporary:
        fixture = Path(temporary)
        for name in ['AGENTS.md', '.codex/hooks.json', 'analysis/scripts/install_project_sync.py',
                     'analysis/scripts/ponytail_project_hook.cjs', 'analysis/scripts/skill-routing-hook.mjs',
                     'analysis/third_party/sources.lock.json']:
            dest = fixture/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text((ROOT/name).read_text().replace(str(ROOT), str(fixture)))
        for scope in ['.agents', '.codex']:
            for skill in ['ponytail', 'task-tag']:
                dest = fixture/scope/'skills'/skill
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/scope/'skills'/skill/'SKILL.md', dest/'SKILL.md')
        shutil.copytree(ROOT/'analysis/vendor/ponytail/hooks', fixture/'analysis/vendor/ponytail/hooks')
        # Reinstall twice in the fixture; never rewrite the real host configuration here.
        run([sys.executable, 'analysis/scripts/install_project_sync.py'], cwd=fixture)
        watched = ['.codex/hooks.json', '.agents/skills/task-tag/SKILL.md',
                   '.codex/skills/task-tag/SKILL.md', 'analysis/third_party/sources.lock.json']
        before = {name: (fixture/name).read_bytes() for name in watched}
        run([sys.executable, 'analysis/scripts/install_project_sync.py'], cwd=fixture)
        assert before == {name: (fixture/name).read_bytes() for name in watched}
        passed('Installer repeatability; generated delivery guidance preserves report exemption')

        config = json.loads((fixture/'.codex/hooks.json').read_text())
        commands = {}
        for event in ['SessionStart', 'UserPromptSubmit']:
            commands[event] = [item['command'] for group in config['hooks'][event] for item in group['hooks']
                               if 'ponytail_project_hook.cjs' in item['command']]
            assert len(commands[event]) == 1
            assert all('ponytail-activate.js' not in item['command'] and 'ponytail-mode-tracker.js' not in item['command']
                       for group in config['hooks'][event] for item in group['hooks'])

        def hook(event, prompt='', mode='full'):
            env = dict(os.environ, PONYTAIL_DEFAULT_MODE=mode)
            payload = json.dumps(dict(hook_event_name=event, cwd=str(fixture), prompt=prompt))
            output = run(['bash', '-c', commands[event][0]], cwd=fixture, env=env, input=payload)
            return json.loads(output or '{}').get('hookSpecificOutput', {}).get('additionalContext', '')

        for mode in ['lite', 'full', 'ultra']:
            text = hook('SessionStart', mode=mode)
            assert 'level: '+mode in text and 'Every delivery reply must stand on its own' in text
            assert 'at most three short lines' not in text and 'delete the explanation' not in text
            assert '| **'+mode+'** |' in text
            assert all('| **'+other+'** |' not in text for other in ['lite', 'full', 'ultra'] if other != mode)
        passed('Actual configured SessionStart emits project skill for lite/full/ultra without old hard limits')
        assert 'OFF' in hook('UserPromptSubmit', '/ponytail off')
        assert not (fixture/'.omx/ponytail/.ponytail-active').exists()
        assert 'level: ultra' in hook('UserPromptSubmit', '/ponytail ultra')
        assert (fixture/'.omx/ponytail/.ponytail-active').read_text() == 'ultra'
        assert hook('UserPromptSubmit', 'ordinary maintenance request') == ''
        assert 'OFF' in hook('UserPromptSubmit', 'stop ponytail')
        assert hook('SessionStart', mode='off') == ''
        passed('Actual configured UserPromptSubmit preserves mode changes, ordinary silence and deactivation')

        for event in ['SessionStart', 'UserPromptSubmit']:
            result = json.loads(run(['node', 'analysis/scripts/skill-routing-hook.mjs'], cwd=fixture,
                                    input=json.dumps(dict(hook_event_name=event, cwd=str(fixture)))))
            text = result['hookSpecificOutput']['additionalContext']
            for phrase in ['科学数据处理', '无需额外执行脚本', '默认免除叙述性报告',
                           '可独立理解的摘要', 'verification.json', '项目根 `run_log/`']:
                assert phrase in text, phrase
        passed('Both routing events emit scientific safeguards, exemptions, full summaries and run_log exception')

        (fixture/'.codex/skills/ponytail/SKILL.md').unlink()
        failed = subprocess.run(['bash', '-c', commands['SessionStart'][0]], cwd=fixture,
                                env=dict(os.environ, PONYTAIL_DEFAULT_MODE='full'), text=True,
                                input='{}', capture_output=True, timeout=15)
        assert failed.returncode != 0 and 'at most three short lines' not in failed.stdout
        passed('Missing project skill fails visibly instead of injecting stale upstream rules')

        evidence = fixture/'analysis/20261008-small-fix/verification.json'
        evidence.parent.mkdir(parents=True)
        evidence.write_text(json.dumps(dict(status='passed', checks=[dict(name='fixture', returncode=0)])))
        original = task_delivery.ROOT
        try:
            task_delivery.ROOT = fixture
            assert task_delivery.evidence(evidence.relative_to(fixture))[0] == evidence.relative_to(fixture).as_posix()
            moved = fixture/'run_log/reports/data_verification.json'
            moved.parent.mkdir(parents=True)
            moved.write_bytes(evidence.read_bytes())
            assert task_delivery.evidence(moved.relative_to(fixture))[0] == moved.relative_to(fixture).as_posix()
            for forbidden in [fixture/'run_log/raw.json', fixture.parent/'outside.json']:
                try:
                    task_delivery.evidence(forbidden)
                except ValueError:
                    pass
                else:
                    raise AssertionError('Out-of-scope evidence accepted')
            evidence.write_text(json.dumps(dict(status='passed', checks=[dict(name='fixture', returncode=1)])))
            try:
                task_delivery.evidence(evidence.relative_to(fixture))
            except ValueError:
                pass
            else:
                raise AssertionError('Failed evidence accepted')
        finally:
            task_delivery.ROOT = original
        passed('Delivery validator accepts analysis and allowed run_log evidence; rejects failed checks and escapes')

        # Check actual Git ignore behavior with a clean index and no project metadata mutation.
        shutil.copyfile(ROOT/'.gitignore', fixture/'.gitignore')
        run(['git', 'init', '--quiet'], cwd=fixture)
        rejected = ['run_log/raw.root', 'run_log/raw.csv', 'run_log/.env',
                    'run_log/__pycache__/x.pyc', 'run_log/reports/secrets.json', 'run_log/figures/new.svg']
        for name in sorted(RUN_LOG_FILES) + rejected:
            target = fixture/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
            output = run(['git', 'ls-files', '--others', '--exclude-standard', '--', name], cwd=fixture)
            expected = name in RUN_LOG_FILES
            assert bool(output.strip()) == expected, name
            assert permitted(name) == expected, name
        assert session_coordinator.relative('run_log/') == 'run_log/'
        passed('Git ignore, trusted content policy and employee scope agree on exact run_log allowlist')

    qa = json.loads((ROOT/'run_log/reports/figure_qa.json').read_text())
    for item in qa['reports']:
        path = ROOT/'run_log/figures'/Path(item['svg']).name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
    passed('All relocated SVGs preserve historical visual-audit fingerprints', figures=len(qa['reports']))
    output = run([sys.executable, 'run_log/test_run_log.py'])
    passed('Run-log parser, real project root and output boundary regression', output=output.strip())
    for name in ['analysis/scripts/install_project_sync.py', 'analysis/scripts/check_git_content.py',
                 'analysis/scripts/task_delivery.py',
                 'analysis/scripts/session_coordinator.py', 'analysis/scripts/verify_project_sync.py',
                 'analysis/scripts/check_layout.py']:
        compile((ROOT/name).read_text(), name, 'exec')
    run(['node', '--check', 'analysis/scripts/ponytail_project_hook.cjs'])
    passed('Changed Python and JavaScript syntax checks')
    for script in ['analysis/scripts/test_project_sync.py',
                   'analysis/session_coordination/test_coordination.py']:
        output = run([sys.executable, script])
        passed('Existing regression: '+script, command=[sys.executable, script], output=output[-16000:])
    with tempfile.TemporaryDirectory(prefix='workflow-entry-report-') as temporary:
        # Keep the original suite and SOURCE, relocating only its generated report.
        code = ('import runpy; n=runpy.run_path("analysis/wsl_codex_entry/test_entry.py"); '
                'f=n["main"]; f.__globals__["__file__"]=' + repr(temporary+'/test_entry.py') + '; f()')
        output = run([sys.executable, '-c', code])
        entry_checks = json.loads((Path(temporary)/'reports/entry_checks.json').read_text())
        assert entry_checks['status'] == 'passed'
        passed('Existing regression: analysis/wsl_codex_entry/test_entry.py',
               checks=entry_checks['checks'], output=output.strip())
    return dict(status='passed', checks=checks, limitations=[
        'Hooks executed as real subprocesses with installed configuration in temporary fixtures; host reload/trust not asserted.',
        'No model-generated reply quality guarantee, new rendering review, raw-data reanalysis or remote push in this check.'])


if __name__ == '__main__':
    result = verify()
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(status=result['status'], checks=len(result['checks']), report=str(REPORT)), ensure_ascii=False))
