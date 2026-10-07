#!/usr/bin/env python3
"""Exercise real commits, tags, pushes and Stop decisions in disposable local repos."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch

import project_sync
import task_delivery
import migrate_delivery_tags


def command(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def check():
    canonical = project_sync.ROOT
    with tempfile.TemporaryDirectory(prefix='chx-sync-check-') as temporary:
        base = Path(temporary)
        root, remote = base/'project', base/'remote.git'
        root.mkdir()
        subprocess.run(['git', 'init', '--bare', str(remote)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['git', 'init', str(root)], check=True, stdout=subprocess.DEVNULL)
        command(root, 'symbolic-ref', 'HEAD', 'refs/heads/main')
        command(root, 'config', 'user.name', 'Sync fixture')
        command(root, 'config', 'user.email', 'fixture@example.invalid')
        command(root, 'remote', 'add', 'origin', str(remote))
        for name in ['project_git.sh', 'check_git_content.py', 'task_delivery.py']:
            destination = root/'analysis/scripts'/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(canonical/'analysis/scripts'/name, destination)
        shutil.copytree(canonical/'.githooks', root/'.githooks')
        shutil.copyfile(canonical/'.gitignore', root/'.gitignore')
        evidence = root/'analysis/check.json'
        evidence.write_text(json.dumps({'status':'passed', 'checks':[{'name':'Fixture initialized', 'returncode':0}]}))
        sample = root/'analysis/example.md'
        sample.write_text('real fixture content\n')
        (root/'analysis/ignored.root').write_bytes(b'excluded fixture')
        with patch.object(project_sync, 'ROOT', root), patch.object(project_sync, 'REMOTE', str(remote)), \
                patch.object(task_delivery, 'ROOT', root), patch.object(task_delivery, 'PENDING', root/'.omx/delivery/pending.json'):
            receipt = project_sync.sync('验证交付', 'Verify local automatic delivery', 'analysis/check.json', '真实提交、推送和标签已完成', '临时仓库检查')
            assert receipt['head'] == command(remote, 'rev-parse', 'main')
            assert receipt['tags'] and not command(root, 'status', '--porcelain')
            assert receipt['tags'] == ['Sync-fixture-验证交付']
            annotation = command(root, 'for-each-ref', '--format=%(contents)', 'refs/tags/'+receipt['tags'][0])
            assert '修改者：Sync fixture' in annotation and '成果：真实提交、推送和标签已完成' in annotation
            assert '基于：临时仓库检查' in annotation and 'SHA256' not in annotation
            assert receipt['head'] not in annotation
            assert command(remote, 'rev-parse', 'refs/tags/'+receipt['tags'][0]+'^{}') == receipt['head']
            legacy = 't-legacy-fixture-20261007000000-abcdef0'
            command(root, 'tag', '-a', legacy, receipt['head'], '-m', 'Legacy fixture annotation')
            project_sync.git('push', 'origin', 'refs/tags/'+legacy)
            with patch.object(migrate_delivery_tags, 'ROOT', root), \
                    patch.object(migrate_delivery_tags, 'BACKUP', root/'.omx/delivery/tag_migration.json'), \
                    patch.object(migrate_delivery_tags, 'MAPPING', [(legacy, '迁移历史标签', '原提交指向保留', '历史标签', '历史未记录')]):
                entries = migrate_delivery_tags.local()
                migrate_delivery_tags.publish(entries)
                assert entries[0]['new'] == 'Sync-fixture-迁移历史标签'
                assert command(remote, 'rev-parse', 'refs/tags/'+entries[0]['new']+'^{}') == receipt['head']
                assert project_sync.git('rev-parse', '--verify', 'refs/tags/'+legacy, check=False).returncode != 0
                assert command(root, 'rev-parse', 'refs/project-tag-backup/'+entries[0]['new']) == entries[0]['old_object']
                assert migrate_delivery_tags.local() == entries
            assert 'analysis/ignored.root' not in command(root, 'ls-files').splitlines()
            assert project_sync.stop_status({'hook_event_name':'Stop', 'cwd':str(root)}) == {}
            sample.write_text('updated fixture content\n')
            assert project_sync.stop_status({'hook_event_name':'Stop', 'cwd':str(root)})['decision'] == 'block'
            assert project_sync.stop_status({'hook_event_name':'Stop', 'cwd':str(base)}) == {}
            assert project_sync.stop_status({'hook_event_name':'Stop', 'cwd':str(root), 'stop_hook_active':True}) == {}
            second = project_sync.sync('验证交付', 'Verify updated automatic delivery', 'analysis/check.json', '更新内容已推送')
            assert second['tags'] == ['Sync-fixture-验证交付-2']
            project_sync.git('commit', '--allow-empty', '-m', 'Unpushed fixture')
            assert project_sync.stop_status({'hook_event_name':'Stop', 'cwd':str(root)})['decision'] == 'block'
            project_sync.sync('retry', 'No new file changes', 'analysis/check.json')
            assert command(root, 'rev-parse', 'HEAD') == command(remote, 'rev-parse', 'main')
            command(root, 'config', 'remote.origin.pushurl', str(base/'unauthorized.git'))
            try:
                project_sync.sync('wrong-destination', 'Must fail', 'analysis/check.json')
            except ValueError:
                pass
            else:
                raise AssertionError('Unauthorized remote was accepted')
            oversized = root/'analysis/oversized.md'
            with oversized.open('wb') as stream:
                stream.truncate(project_sync.MAX_BYTES+1)
            try:
                project_sync.candidates()
            except ValueError:
                pass
            else:
                raise AssertionError('Oversized file was accepted')
    print('PASS: actual local commit/push/tag, clean/dirty/unpushed/foreign/replayed Stop, remote destination and size boundaries')


if __name__ == '__main__':
    check()
