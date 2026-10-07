#!/usr/bin/env python3
"""Read acquisition run.log files; export an auditable CSV and daily SVG timelines."""
import argparse
import csv
import hashlib
import re
import shlex
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
FIELDS = ['run_id', 'start_time', 'end_time', 'duration_min',
          'end_status', 'status_reason', 'log_path']


def inside(path, parent):
    return path == parent or parent in path.parents


def validate_paths(source, output):
    source, output = source.resolve(), output.resolve()
    if not source.is_dir():
        raise ValueError('Input directory does not exist: ' + str(source))
    forbidden = [PROJECT.parent / name for name in ('Ge', 'CsI', 'software')]
    if (not inside(output, PROJECT) or inside(output, source)
            or inside(source, output) or any(inside(output, p.resolve()) for p in forbidden)):
        raise ValueError('Output must be inside this project and separate from input data')
    if inside(source, (PROJECT.parent / 'software').resolve()):
        raise ValueError('The software directory is outside this task scope')
    return source, output


def parse_log(text, run_id, log_path):
    row = dict.fromkeys(FIELDS, '')
    row.update(run_id=str(run_id), log_path=str(log_path), end_status='unknown')
    fields = {'Start': [], 'Stop': []}
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r'^\s*(Start|Stop)\s*:\s*(.*?)\s*$', line)
        if match:
            fields[match[1]].append((number, match[2]))
    reasons, times = [], {}
    for key, column in [('Start', 'start_time'), ('Stop', 'end_time')]:
        entries = fields[key]
        if not entries:
            reasons.append(key + ' missing')
        elif len(entries) != 1:
            reasons.append(key + ' ambiguous at lines ' + ','.join(str(n) for n, _ in entries))
        else:
            number, value = entries[0]
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', value):
                    raise ValueError('timestamp format')
                times[key] = datetime.strptime(value, TIME_FORMAT)
                row[column] = value
                reasons.append('{} line {}'.format(key, number))
            except ValueError:
                reasons.append('{} invalid timestamp at line {}: {!r}'.format(key, number, value))
    if len(times) == 2:
        seconds = (times['Stop'] - times['Start']).total_seconds()
        if seconds < 0:
            reasons.append('Stop precedes Start; duration omitted')
        else:
            row['duration_min'] = '{:.6f}'.format(seconds / 60)
            row['end_status'] = 'normal'
            reasons.append('unique valid Start/Stop; normal end record only')
    row['status_reason'] = '; '.join(reasons)
    return row


def collect(source, selected=None):
    directories = sorted((p for p in source.iterdir() if p.is_dir()
                          and re.fullmatch(r'[0-9]+', p.name)), key=lambda p: (int(p.name), p.name))
    if selected is not None:
        missing = set(selected) - {p.name for p in directories}
        if missing:
            raise ValueError('Requested run directories missing: ' + ', '.join(sorted(missing)))
        directories = [p for p in directories if p.name in selected]
    rows, fingerprints = [], []
    for directory in directories:
        path = directory / 'run.log'
        if not inside(path.resolve(), source):
            raise ValueError('Log symlink escapes input directory: ' + str(path))
        row = dict.fromkeys(FIELDS, '')
        row.update(run_id=directory.name, log_path=str(path), end_status='unknown')
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            row['status_reason'] = 'run.log missing'
            fingerprints.append((str(path), 'missing'))
        else:
            fingerprints.append((str(path), hashlib.sha256(raw).hexdigest()))
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                row['status_reason'] = 'run.log is not valid UTF-8; timestamp parsing omitted'
            else:
                row = parse_log(text, directory.name, path)
        rows.append(row)
    if not rows:
        raise ValueError('No numeric run directories selected')
    return rows, fingerprints


def daily_segments(rows):
    """Map each date to (row, left hour, right hour, marker) entries."""
    days = defaultdict(list)
    for row in rows:
        start = datetime.strptime(row['start_time'], TIME_FORMAT) if row['start_time'] else None
        end = datetime.strptime(row['end_time'], TIME_FORMAT) if row['end_time'] else None
        if row['duration_min'] != '':
            current = start.replace(hour=0, minute=0, second=0)
            while current < end or (start == end and current.date() == start.date()):
                boundary = current + timedelta(days=1)
                left, right = max(start, current), min(end, boundary)
                days[current.date()].append((row, (left-current).total_seconds()/3600,
                                              (right-current).total_seconds()/3600,
                                              'zero' if start == end else 'interval'))
                current = boundary
        elif start is not None:
            hour = start.hour + start.minute / 60 + start.second / 3600
            days[start.date()].append((row, hour, hour, 'start'))
        elif end is not None:
            hour = end.hour + end.minute / 60 + end.second / 3600
            days[end.date()].append((row, hour, hour, 'end'))
    return days


def plot_days(days, folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    plt.rcParams.update({'svg.fonttype': 'none', 'font.family': 'DejaVu Sans',
                         'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    colors = {'normal': '#0072B2', 'abnormal': '#D55E00', 'unknown': '#777777'}
    for day, segments in sorted(days.items()):
        segments.sort(key=lambda s: (s[1], int(s[0]['run_id'])))
        fig, ax = plt.subplots(figsize=(13, max(4.5, 2.5 + .30 * len(segments))))
        present = set()
        for y, (row, left, right, marker) in enumerate(segments):
            status = row['end_status']
            color = colors[status]
            if marker == 'interval':
                ax.barh(y, right-left, left=left, height=.65, color=color,
                        edgecolor=color, hatch=None if status == 'normal' else '//')
                present.add(status)
            else:
                ax.plot(left, y, marker={'zero': 'o', 'start': '>', 'end': '<'}[marker],
                        color=color, markersize=6, linestyle='none', clip_on=False)
                present.add(marker)
        ax.set_yticks(range(len(segments)))
        ax.set_yticklabels([s[0]['run_id'] for s in segments])
        ax.set_ylim(len(segments)-.4, -.6)
        ax.set_xlim(0, 24)
        ax.set_xticks(range(0, 25, 2))
        ax.set_xticklabels(['{:02d}:00'.format(h) for h in range(0, 25, 2)])
        ax.set_xlabel('Acquisition clock time (hours; timezone unspecified)')
        ax.set_ylabel('Run ID')
        ax.set_title('Ge acquisition log | {}'.format(day), pad=12)
        ax.grid(axis='x', alpha=.2)
        ax.set_axisbelow(True)
        handles = [Patch(facecolor=colors[s], hatch=None if s == 'normal' else '//',
                         label=s + ' end record') for s in colors if s in present]
        handles += [Line2D([], [], color='#555555', marker=m, linestyle='none', label=label)
                    for key, m, label in [('zero', 'o', 'Zero duration'),
                                         ('start', '>', 'Start only; no duration'),
                                         ('end', '<', 'Stop only; no duration')] if key in present]
        fig.legend(handles=handles, loc='lower center', ncol=min(3, len(handles)), frameon=False)
        fig.tight_layout(rect=(0, .08, 1, 1))
        fig.savefig(folder / ('gantt_{}.svg'.format(day)), format='svg')
        plt.close(fig)


def write_report(rows, fingerprints, source, output, command, days):
    counts = Counter(row['end_status'] for row in rows)
    durations = [(datetime.strptime(r['end_time'], TIME_FORMAT)
                  - datetime.strptime(r['start_time'], TIME_FORMAT)).total_seconds()/60
                 for r in rows if r['duration_min'] != '']
    lines = ['# Ge run.log 运行时间统计', '', '## 来源与复现', '',
             '- 只读输入：`{}`；仅直属数字目录，排除 test/。'.format(source),
             '- 输出目录：`{}`。'.format(output),
             '- 实际工作目录：`{}`。'.format(Path.cwd()),
             '- 实际命令：`{}`。'.format(command),
             '- 程序 SHA-256：`{}`。'.format(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
             '- 时间保留采集机墙钟值；日志无时区，不换算时区。', '',
             '## 描述性统计', '', '- run 数：{}。'.format(len(rows)),
             '- 结束状态：{}。'.format(', '.join('{}={}'.format(s, counts[s]) for s in ('normal','abnormal','unknown'))),
             '- 可计算时长：{} 个 run；合计 {:.6f} 分钟。'.format(len(durations), sum(durations)),
             '- 合计为各 run 时长之和，重叠会重复计入，不能视为实际覆盖时长。',
             '- 每个 run 一行；缺失时长为空，真实零时长为 0；CSV 分钟保留 6 位小数。',
             '- normal 仅表示唯一且非负的 Start/Stop 结束记录，不表示物理数据有效。',
             '- 未确认异常结束标志，因此不依据任意 error 字串分类 abnormal。',
             '- unknown 保留缺失、歧义或时间顺序问题，不推断实际结束方式。',
             '- 不读取实验记录、二进制数据或日志内的模块哈希作为判断依据。', '',
             '## SVG 与审查', '', '- {} 张每日 SVG，全部依据重新读取的 runs.csv 绘制。'.format(len(days)),
             '- 跨日按午夜拆分，恰在午夜结束不生成次日零长度条；未知时长仅画可定位标记。',
             '- 图中蓝色为正常结束记录，橙色为明确异常，灰色为未知；不代表数据有效性。',
             '- 最终 SVG 视觉审查待独立执行；本程序退出成功不等于审查通过。', '',
             '## 无法计算时长的记录', '']
    lines += ['- run{}：{}'.format(r['run_id'], r['status_reason']) for r in rows if r['duration_min'] == ''] or ['- 无。']
    lines += ['', '## 输入日志 SHA-256', '', '仅对实际读取的 run.log 字节计算指纹，不核验二进制文件。', '']
    lines += ['- `{}`：`{}`'.format(p, digest) for p, digest in fingerprints]
    (output / 'reports' / 'run_log.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=PROJECT.parent / 'Ge')
    parser.add_argument('--output-dir', type=Path, default=PROJECT / 'analysis/run_log')
    parser.add_argument('--runs', nargs='+', help='Optional exact run directory names for sample validation')
    args = parser.parse_args(argv)
    source, output = validate_paths(args.input_dir, args.output_dir)
    rows, fingerprints = collect(source, args.runs)
    days = daily_segments(rows)
    targets = [output/'runs.csv', output/'reports/run_log.md']
    targets += [output/'figures'/('gantt_{}.svg'.format(day)) for day in days]
    for path in targets:
        if not inside(path.resolve(), output):
            raise ValueError('Output symlink escapes output directory: ' + str(path))
        if path.exists() or path.is_symlink():
            raise FileExistsError('Refusing to overwrite existing output: ' + str(path))
    if (output/'figures').exists() and list((output/'figures').glob('gantt_*.svg')):
        raise FileExistsError('Existing timeline SVGs; use a fresh output directory')
    for name in ('figures', 'reports'):
        (output/name).mkdir(parents=True, exist_ok=True)
    with (output/'runs.csv').open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with (output/'runs.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    days = daily_segments(rows)
    plot_days(days, output/'figures')
    command = shlex.join([sys.executable] + sys.argv) if argv is None else shlex.join([sys.executable, str(Path(__file__).resolve())] + argv)
    write_report(rows, fingerprints, source, output, command, days)
    print('{} runs; {} daily SVGs; {}'.format(len(rows), len(days), output/'runs.csv'))


if __name__ == '__main__':
    main()
