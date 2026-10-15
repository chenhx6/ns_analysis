#!/usr/bin/env python3
"""Exercise actual routing-hook output in a small isolated project fixture."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def invoke(root, payload, digest=None, raw=None):
    """Run the registered implementation without host trust or model execution."""
    env = dict(os.environ)
    env.pop('CHX_CO_PROMPT_SHA256', None)
    if digest is not None:
        env['CHX_CO_PROMPT_SHA256'] = digest
    return subprocess.run(['node', str(root/'analysis/scripts/skill-routing-hook.mjs')],
                          input=raw if raw is not None else json.dumps(payload),
                          text=True, capture_output=True, env=env, timeout=15)


def main():
    """Check injection, lifecycle restoration and failure behavior from real output."""
    with tempfile.TemporaryDirectory(prefix='chx-profile-hooks-') as temporary:
        root = Path(temporary)/'project'
        scripts = root/'analysis/scripts'
        scripts.mkdir(parents=True)
        shutil.copyfile(ROOT/'analysis/scripts/skill-routing-hook.mjs', scripts/'skill-routing-hook.mjs')
        profile = (ROOT/'analysis/scripts/agent-prompt.txt').read_bytes()
        profile_path = scripts/'agent-prompt.txt'
        profile_path.write_bytes(profile)
        policy = 'fixture routing policy'
        (root/'AGENTS.md').write_text('<!-- PROJECT:AUTO-SKILLS:START -->\n'+policy+
                                    '\n<!-- PROJECT:AUTO-SKILLS:END -->\n')
        digest = hashlib.sha256(profile).hexdigest()
        payload = {'hook_event_name':'SessionStart', 'cwd':str(root), 'source':'startup'}
        for source, marker, count in [('startup',None,1),('startup',digest,0),
                                       ('startup','stale-profile',1),('clear',digest,1),
                                       ('resume',digest,1),('fork',digest,1),('compact',digest,1)]:
            payload['source'] = source
            run = invoke(root,payload,marker)
            assert run.returncode == 0,run.stderr
            output = json.loads(run.stdout)['hookSpecificOutput']
            assert output['hookEventName'] == 'SessionStart'
            context = output['additionalContext']
            assert context.count(profile.decode().strip()) == count,(source,marker)
            assert context.count(policy) == 1
        payload = {'hook_event_name':'UserPromptSubmit','cwd':str(root),'prompt':'解释一组跃迁的证据'}
        run = invoke(root,payload,digest)
        assert run.returncode == 0,run.stderr
        context = json.loads(run.stdout)['hookSpecificOutput']['additionalContext']
        assert policy in context and str(profile_path) in context
        assert profile.decode().strip() not in context
        for payload in [{'hook_event_name':'SessionStart','cwd':str(root.parent/'outside')},
                        {'hook_event_name':'Stop','cwd':str(root)}]:
            run = invoke(root,payload)
            assert run.returncode == 0 and not run.stdout
        payload = {'hook_event_name':'SessionStart','cwd':str(root),'source':'startup'}
        for raw in ['{broken', 'x'*(1024*1024+1)]:
            run = invoke(root,payload,raw=raw)
            assert run.returncode != 0 and not run.stdout
        profile_path.unlink()
        run = invoke(root,payload,digest)
        assert run.returncode != 0 and not run.stdout
        profile_path.write_text(' \n')
        run = invoke(root,payload)
        assert run.returncode != 0 and not run.stdout
    lock = json.loads((ROOT/'analysis/third_party/sources.lock.json').read_text())
    skill = ROOT/'.agents/skills/chx-data-analysis/SKILL.md'
    assert skill.read_bytes() == (ROOT/'.codex/skills/chx-data-analysis/SKILL.md').read_bytes()
    recorded = next(item for item in lock['adaptations'] if item['directory']=='.agents/skills/chx-data-analysis')
    assert hashlib.sha256(skill.read_bytes()).hexdigest() == recorded['entry_sha256']
    source = lock['sources']['configure']
    for name, expected in source['installed_files_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected,name
    print('PASS: actual startup injection/deduplication; clear/resume/fork/compact restoration; '
          'per-prompt reminders; outside/unused events; malformed/oversized/missing/empty failure; '
          'skill mirrors and source fingerprints.')


if __name__ == '__main__':
    main()
