#!/usr/bin/env python3
"""Record actual readable-tag regression, deployment and migration checks."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

import task_delivery

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT/'analysis/project_maintenance/reports/readable_tags_verification.json'


def main():
    checks = []
    result = subprocess.run(['python3','analysis/scripts/test_project_sync.py'], cwd=ROOT,
                            text=True, capture_output=True, timeout=60)
    checks.append({'name':'Actual Chinese tag, outcome annotation, short repeated-task suffix, historical rename and push tests',
                   'command':['python3','analysis/scripts/test_project_sync.py'], 'returncode':result.returncode,
                   'output':(result.stdout+result.stderr)[-14000:]})
    try:
        for name in ['task_delivery.py','project_sync.py','migrate_delivery_tags.py','install_project_sync.py']:
            compile((ROOT/'analysis/scripts'/name).read_text(), name, 'exec')
        lock = json.loads((ROOT/'analysis/third_party/sources.lock.json').read_text())
        expected = next(item['entry_sha256'] for item in lock['adaptations'] if item['directory']=='.agents/skills/task-tag')
        for base in ['.agents/skills/task-tag','.codex/skills/task-tag']:
            assert hashlib.sha256((ROOT/base/'SKILL.md').read_bytes()).hexdigest() == expected
        migration = json.loads((ROOT/'.omx/delivery/tag_migration.json').read_text())
        assert migration['status'] == 'remote-and-local-replaced' and len(migration['entries']) == 6
        names = []
        for item in migration['entries']:
            name = item['new']
            assert task_delivery.git('rev-parse', name+'^{}') == item['head']
            annotation = task_delivery.git('for-each-ref','--format=%(contents)','refs/tags/'+name)
            assert all(field in annotation for field in ['修改者：','执行协作：','基于：','改动：','成果：','验证：'])
            assert 'SHA256' not in annotation and item['head'] not in annotation
            assert not re.search(r'\d{10,}', name)
            assert subprocess.run(task_delivery.git_command('rev-parse','--verify','refs/tags/'+item['old']),
                                  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode != 0
            names.append(name)
        checks.append({'name':'Six historical tag targets preserved; readable annotations and local old-name removal; skill mirrors and syntax', 'returncode':0})
    except Exception as exc:
        names = []
        checks.append({'name':'Readable tag deployment and migration checks', 'returncode':1, 'output':str(exc)})
    output = {'status':'passed' if all(item['returncode']==0 for item in checks) else 'failed',
              'checks':checks, 'readable_tags':names,
              'notes':['Remote tag replacement was confirmed by migrate_delivery_tags.py; original tag objects retained in private backup refs.',
                       'Git internal commit/evidence identity checks remain; readable tag names and annotations omit machine hashes.']}
    REPORT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':output['status'],'tags':names,'report':str(REPORT)},ensure_ascii=False))
    return 0 if output['status']=='passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
