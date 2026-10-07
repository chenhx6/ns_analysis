#!/usr/bin/env python3
"""Replace only six known machine tags with readable annotations on the same commits."""
import argparse
import json
from pathlib import Path

import project_sync
import task_delivery

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT/'.omx/delivery/tag_migration.json'
MAPPING = [
    ('t-install-project-skills-20261004201832-4178a26', '安装项目技能与运行环境',
     '项目技能、固定上游源码及可复现离线运行环境就绪；模型调用未验证', '项目配置记录和固定来源清单', '历史未记录'),
    ('t-cleanup-skills-auto-routing-20261005072402-5cc1792', '清理重复技能并启用自动调用',
     '删除根目录冗余技能副本，保留有效入口与支持资源，并由项目规则统一选择技能', '用户的技能去重要求和项目自动路由规则', '历史未记录'),
    ('t-cleanup-skills-auto-routing-20261005073156-67ff390', '修正交付标签的推送检查',
     '只检查目标远端尚未发布的历史，旧布局不再误拦截；数据历史仍被检查', '标签推送涉及已发布旧布局的问题', '历史未记录'),
    ('t-decoder-files-purpose-20261005081618-c9b8d71', '保留解码调试文件并说明并行调度',
     '保留原作者调试文件与调度底本，澄清各crate的run参数；未执行解码或并发改造', '用户提供的原开发用途及官方解码源码', '历史未记录'),
    ('t-automatic-project-delivery-20261007070536-6772008', '启用验证后的自动提交与推送',
     '完成自动同步程序、交付标签与Stop检查，隔离提交推送测试通过', '用户持续同步授权和已有Git交付脚本', 'Codex'),
    ('t-automatic-delivery-record-20261007071508-ff7a8fe', '记录自动交付的验证与同步结果',
     '保存用户配置、目录整理、run日志与同步规范已交付的实际记录', '同步程序读取的正式远端结果', 'Codex'),
]


def remote_tags():
    result = {}
    for line in project_sync.text('ls-remote', '--tags', 'origin').splitlines():
        oid, ref = line.split()
        if not ref.endswith('^{}'):
            result[ref[len('refs/tags/'):]] = oid
    return result


def local():
    if BACKUP.exists():
        entries = json.loads(BACKUP.read_text())['entries']
        assert {item['old'] for item in entries} == {item[0] for item in MAPPING}
        return entries
    entries = []
    for old, title, result, basis, executor in MAPPING:
        oid = task_delivery.git('rev-parse', 'refs/tags/'+old)
        assert task_delivery.git('cat-file', '-t', oid) == 'tag'
        head = task_delivery.git('rev-parse', old+'^{}')
        author = task_delivery.git('show', '-s', '--format=%an', head)
        expected = task_delivery.tag_name(author, title, head)
        # Private ref retains the original annotation object for an exact rollback.
        task_delivery.git('update-ref', 'refs/project-tag-backup/'+expected, oid)
        name = task_delivery.create_tag(head, title, result, basis, executor, '依据历史交付记录；本次核对标签提交指向一致')
        entries.append({'old':old, 'old_object':oid, 'head':head, 'new':name,
                        'new_object':task_delivery.git('rev-parse', 'refs/tags/'+name)})
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    BACKUP.write_text(json.dumps({'entries':entries, 'status':'new-local-tags-created'}, ensure_ascii=False, indent=2)+'\n')
    return entries


def publish(entries):
    assert project_sync.text('remote', 'get-url', '--push', '--all', 'origin').splitlines() == [project_sync.REMOTE]
    assert project_sync.text('remote', 'get-url', '--all', 'origin').splitlines() == [project_sync.REMOTE]
    remote = remote_tags()
    for item in entries:
        assert remote.get(item['old']) in (None, item['old_object']), 'Old remote tag changed; refusing replacement'
        assert remote.get(item['new']) in (None, item['new_object']), 'Readable name conflicts with remote tag'
        assert task_delivery.git('rev-parse', item['new']+'^{}') == item['head']
        assert task_delivery.git('rev-parse', 'refs/tags/'+item['new']) == item['new_object'], 'Local readable tag changed'
    project_sync.git('push', 'origin', *['refs/tags/'+item['new'] for item in entries])
    remote = remote_tags()
    deletions = []
    for item in entries:
        assert remote.get(item['new']) == item['new_object'], 'New remote tag not verified'
        if item['old'] in remote:
            assert remote[item['old']] == item['old_object'], 'Old tag changed after new tag push'
            deletions.append(':refs/tags/'+item['old'])
    if deletions:
        project_sync.git('push', 'origin', *deletions)
    remote = remote_tags()
    for item in entries:
        assert item['old'] not in remote and remote.get(item['new']) == item['new_object']
        old = project_sync.git('rev-parse', '--verify', 'refs/tags/'+item['old'], check=False)
        if old.returncode == 0:
            assert old.stdout.decode().strip() == item['old_object']
            task_delivery.git('tag', '-d', item['old'])
    BACKUP.write_text(json.dumps({'entries':entries, 'status':'remote-and-local-replaced'}, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status':'replaced', 'tags':[item['new'] for item in entries]}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    entries = local()
    if args.publish:
        publish(entries)
    else:
        print(json.dumps({'status':'prepared', 'tags':[item['new'] for item in entries]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
