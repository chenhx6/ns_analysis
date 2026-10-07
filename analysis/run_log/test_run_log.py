#!/usr/bin/env python3
"""Small deterministic regression check; no raw inputs or plotting dependency."""
import argparse
import csv
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch
from run_log import PROJECT, collect, daily_segments, parse_log, validate_paths, main


def parse(text):
    return parse_log(text, '1', '/example/1/run.log')


def rejects(function, *args):
    try:
        function(*args)
    except (ValueError, FileExistsError):
        return
    raise AssertionError('Expected boundary or overwrite rejection')


def check():
    start = 'Start: 2025-06-07 23:30:00\n'
    stop = 'Stop : 2025-06-08 00:30:00\n'
    row = parse('  '+start+stop+'error count: 0\nrun time:\n99999')
    assert row['duration_min'] == '60.000000' and row['end_status'] == 'normal'
    assert 'line 1' in row['status_reason']
    segments = daily_segments([row])
    assert len(segments) == 2
    assert sum(s[2]-s[1] for ss in segments.values() for s in ss) == 1
    midnight = parse(start+'Stop: 2025-06-08 00:00:00')
    assert list(daily_segments([midnight])) == [date(2025, 6, 7)]
    multi = parse(start+'Stop: 2025-06-10 00:30:00')
    assert len(daily_segments([multi])) == 4
    zero = parse(start+'Stop: 2025-06-07 23:30:00')
    assert zero['duration_min'] == '0.000000'
    assert daily_segments([zero])[date(2025,6,7)][0][3] == 'zero'
    for text in ['', start, stop, start+start+stop, start+stop+stop,
                 'Start: garbage\n'+stop, start+'Stop: 2025-06-06 00:00:00',
                 'Start: 2025-02-30 00:00:00\n'+stop,
                 'Start: 2025-6-7 23:30:00\n'+stop]:
        bad = parse(text)
        assert bad['duration_min'] == '' and bad['end_status'] == 'unknown', text
    assert parse(start+start+stop)['start_time'] == ''
    assert daily_segments([parse(start)])[date(2025,6,7)][0][3] == 'start'
    assert daily_segments([parse(stop)])[date(2025,6,8)][0][3] == 'end'
    with tempfile.TemporaryDirectory(prefix='run-log-test-') as temporary, \
            patch('run_log.PROJECT', Path(temporary)):
        base = Path(temporary)
        source, output = base/'source', base/'output'
        source.mkdir()
        for name in ('2', '1', 'test'):
            (source/name).mkdir()
        (source/'1/run.log').write_text(start+stop)
        rows, fingerprints = collect(source)
        assert [r['run_id'] for r in rows] == ['1','2']
        assert rows[1]['status_reason'] == 'run.log missing' and len(fingerprints) == 2
        assert len(collect(source, ['1'])[0]) == 1
        rejects(collect, source, ['3'])
        assert validate_paths(source, output) == (source, output)
        for bad in [source, source/'out', base, Path('/tmp/outside-project')]:
            rejects(validate_paths, source, bad)
        output.symlink_to(source, target_is_directory=True)
        rejects(validate_paths, source, output)
        output.unlink()
        output.mkdir()
        (output/'figures').symlink_to(source, target_is_directory=True)
        rejects(main, ['--input-dir', str(source), '--output-dir', str(output)])
        (output/'figures').unlink()
        (output/'runs.csv').write_text('preserve me')
        rejects(main, ['--input-dir', str(source), '--output-dir', str(output)])
        assert (output/'runs.csv').read_text() == 'preserve me'
        (source/'1/run.log').unlink()
        (source/'1/run.log').symlink_to(base/'external.log')
        rejects(collect, source)
    print('PASS: parsing, ambiguity, missing/invalid/negative/zero times, daily clipping, input selection, paths, overwrite safety')


def verify_csv(path, source, report=None):
    """Independently compare exported rows with current raw log fields and hashes."""
    directories = {p.name for p in source.iterdir()
                   if p.is_dir() and re.fullmatch(r'[0-9]+', p.name)}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len(directories) == len({r['run_id'] for r in rows})
    assert {r['run_id'] for r in rows} == directories
    saved = (path.parent/'reports/run_log.md').read_text()
    counts, total_seconds, valid = Counter(), 0, 0
    for row in rows:
        log = source/row['run_id']/'run.log'
        assert row['log_path'] == str(log.resolve())
        counts[row['end_status']] += 1
        if not log.exists():
            assert row['end_status'] == 'unknown' and not row['duration_min']
            continue
        raw = log.read_bytes()
        assert '- `{}`：`{}`'.format(log, hashlib.sha256(raw).hexdigest()) in saved
        fields = {'Start': [], 'Stop': []}
        for line in raw.decode('utf-8-sig').splitlines():
            label, separator, value = line.partition(':')
            if separator and label.strip() in fields:
                fields[label.strip()].append(value.strip())
        for key, column in [('Start', 'start_time'), ('Stop', 'end_time')]:
            if len(fields[key]) == 1:
                assert row[column] == fields[key][0]
            else:
                assert not row[column]
        if row['duration_min']:
            delta = datetime.fromisoformat(row['end_time']) - datetime.fromisoformat(row['start_time'])
            seconds = delta.total_seconds()
            assert seconds >= 0 and abs(float(row['duration_min'])-seconds/60) <= .500001e-6
            assert row['end_status'] == 'normal'
            total_seconds += seconds
            valid += 1
        else:
            assert row['end_status'] == 'unknown'
    output = {'status': 'passed', 'checks': [
        {'name': 'All numeric source directories represented exactly once', 'returncode': 0},
        {'name': 'CSV timestamps and rounded minutes independently match raw logs', 'returncode': 0},
        {'name': 'Input log fingerprints still match extraction report', 'returncode': 0}],
        'csv_rows': len(rows), 'valid_durations': valid, 'status_counts': dict(counts),
        'sum_duration_min': total_seconds/60,
        'csv_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'command': [sys.executable] + sys.argv}
    if report:
        target = report.resolve()
        assert PROJECT in target.parents and target.suffix == '.json'
        with target.open('x', encoding='utf-8') as stream:
            json.dump(output, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    print(json.dumps(output, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path)
    parser.add_argument('--input-dir', type=Path, default=PROJECT.parent/'Ge')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.csv:
        verify_csv(args.csv, args.input_dir, args.report)
    else:
        check()
