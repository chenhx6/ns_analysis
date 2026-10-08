#!/usr/bin/env python3
"""Exercise real commits, tags, pushes and Stop decisions in disposable local repos."""
import json
import multiprocessing
import os
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


def hold_delivery_lock(root, ready):
    project_sync.ROOT = root
    with project_sync.sync_lock(timeout=1):
        ready.send(True)
        ready.recv()


def check_lock(root):
    parent, child = multiprocessing.Pipe()
    process = multiprocessing.Process(target=hold_delivery_lock, args=(root, child))
    process.start()
    try:
        assert parent.poll(5) and parent.recv()
        try:
            with project_sync.sync_lock(timeout=0.1):
                raise AssertionError('Concurrent delivery acquired an occupied lock')
        except RuntimeError as error:
            assert 'busy' in str(error)
    finally:
        process.terminate()
        process.join(5)
        parent.close()
        child.close()
    assert not process.is_alive()
    with project_sync.sync_lock(timeout=1):
        pass  # OS releases the lock even after the owner exits abnormally.


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
            check_lock(root)
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
            # Explicit file delivery preserves a second task's tracked and untracked edits.
            sample.write_text('selected update\n')
            unrelated = root/'analysis/other.md'
            unrelated.write_text('another task\n')
            evidence.write_text(json.dumps({'status':'passed', 'checks':[{'returncode':0}], 'other':'unselected'}))
            command(root, 'add', 'analysis/other.md')
            try:
                project_sync.candidates(['analysis/example.md'])
            except ValueError as error:
                assert 'outside selected' in str(error)
            else:
                raise AssertionError('Unrelated staged work was accepted')
            command(root, 'reset', 'HEAD', '--', 'analysis/other.md')
            # Evidence must match the index even if an unrelated task edits the evidence file.
            try:
                project_sync.sync('选定交付', 'Selected only', 'analysis/check.json', '选择文件', files=['analysis/example.md'])
            except ValueError as error:
                assert 'Staged evidence' in str(error)
            else:
                raise AssertionError('Unstaged evidence accepted')
            command(root, 'restore', '--', 'analysis/check.json')
            task_delivery.prepare('待完成', 'analysis/check.json', '验证', files=['analysis/example.md'])
            pending = task_delivery.PENDING.read_bytes()
            task_delivery.prepare('待完成', 'analysis/check.json', '验证', files=['analysis/example.md'])
            try:
                task_delivery.prepare('另一个任务', 'analysis/check.json', '验证', files=['analysis/example.md'])
            except ValueError as error:
                assert 'outstanding' in str(error)
            else:
                raise AssertionError('Outstanding pending was overwritten')
            assert task_delivery.PENDING.read_bytes() == pending
            task_delivery.PENDING.unlink()  # Disposable fixture deliberately cancels preparation.
            # A tracked file owned by another task remains dirty throughout finalize.
            source = root/'analysis/scripts/check_git_content.py'
            source.write_text(source.read_text() + '\n# unrelated task edit\n')
            selected = project_sync.sync('选定交付', 'Selected only', 'analysis/check.json', '选择文件', files=['analysis/example.md'])
            assert command(root, 'show', '--format=', '--name-only', selected['head']) == 'analysis/example.md'
            assert unrelated.read_text() == 'another task\n' and source.read_text().endswith('# unrelated task edit\n')
            assert project_sync.stop_status({'hook_event_name':'Stop','cwd':str(root),'session_id':'native-other'}) == {}
            assert project_sync.stop_status({'hook_event_name':'Stop','cwd':str(root)})['decision'] == 'block'
            # Parent session Git environment must not redirect either repository helper.
            with patch.dict(os.environ, {'GIT_DIR':str(remote),'GIT_WORK_TREE':str(base),
                                         'GIT_INDEX_FILE':str(base/'foreign-index')}):
                assert task_delivery.git('rev-parse', '--show-toplevel') == str(root)
                assert project_sync.text('rev-parse', '--show-toplevel') == str(root)
            assert not (base/'foreign-index').exists()
            # Worktree .git pointer files resolve to an independent Git index.
            worktree = base/'linked'
            command(root, 'worktree', 'add', '-b', 'linked-test', str(worktree))
            assert (worktree/'.git').is_file()
            with patch.object(task_delivery, 'ROOT', worktree):
                assert task_delivery.git('rev-parse', '--show-toplevel') == str(worktree)
                assert Path(task_delivery.git_command()[1].split('=', 1)[1]) != root/'.git'
            script = worktree/'analysis/scripts/project_git.sh'
            assert subprocess.check_output(['bash', str(script), 'rev-parse', '--show-toplevel'], text=True).strip() == str(worktree)
            # Candidate-controlled hooks and validation scripts must never execute
            # in the integrator. Their payload is confined to this disposable fixture.
            sentinel = base/'candidate-ran'
            payload = 'from pathlib import Path\nPath(' + repr(str(sentinel)) + ').write_text("unsafe")\nraise SystemExit(1)\n'
            for name in ['task_delivery.py', 'check_git_content.py']:
                (root/'analysis/scripts'/name).write_text(payload)
            shell_payload = '#!/bin/sh\necho unsafe > "' + str(sentinel) + '"\nexit 1\n'
            (root/'analysis/scripts/project_git.sh').write_text(shell_payload)
            for name in ['pre-commit', 'post-commit', 'pre-push']:
                (root/'.githooks'/name).write_text(shell_payload)
            (root/'.omx/integration.json').write_text('{}')
            sample.write_text('trusted control update\n')
            trusted = project_sync.sync('可信交付', 'Use control scripts', 'analysis/check.json', '候选脚本未执行', files=['analysis/example.md'])
            assert trusted['head'] == command(remote, 'rev-parse', 'main')
            assert not sentinel.exists()
            (root/'.omx/employee.json').write_text('{}')
            managed_status = subprocess.run(['bash', str(canonical/'analysis/scripts/project_git.sh'),
                                             '--workspace', str(root), 'status', '--short'],
                                            env=dict(os.environ, TMPDIR='/nonexistent/chx-readonly-tmp'),
                                            capture_output=True, text=True)
            assert managed_status.returncode == 0, managed_status.stderr
            assert (root/'.omx/tmp').is_dir() and not list((root/'.omx/tmp').iterdir())
            blocked = subprocess.run(['bash', str(canonical/'analysis/scripts/project_git.sh'),
                                      '--workspace', str(root), 'push', 'origin', 'main'], capture_output=True, text=True)
            assert blocked.returncode != 0 and 'Employee pushes are disabled' in blocked.stderr
            (root/'.omx/employee.json').unlink()
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
    print('PASS: process lock/exited-owner recovery, pending isolation, selected-files isolation, Git environment isolation, native Stop; actual local commit/push/tag, clean/dirty/unpushed/foreign/replayed Stop, remote destination and size boundaries')


if __name__ == '__main__':
    check()
