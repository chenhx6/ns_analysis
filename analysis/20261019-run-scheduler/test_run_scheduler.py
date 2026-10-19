"""Use disposable input files and a fake executable; never run scientific analysis."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'time_offset/time_offset/run.sh'


def case(runs, start='', end='', excluded=(), absent=(), pattern='data_C2_{run}_{run}_wave.root'):
    """Run the portable script elsewhere and infer concurrency from mock child events."""
    with tempfile.TemporaryDirectory(prefix='chx-run-scheduler-') as temporary:
        base = Path(temporary)
        folder = base / 'moved program'
        data = base / 'input data'
        folder.mkdir()
        data.mkdir()
        for run in range(1, 13):
            if run not in absent:
                (data / pattern.replace('{run}', str(run))).touch()
        text = SCRIPT.read_text()
        values = {'data_dir': '"../input data"', 'program': '"mock"',
                  'input_pattern': repr(pattern), 'runs': '(' + ' '.join(map(str, runs)) + ')',
                  'start_run': '"' + start + '"', 'end_run': '"' + end + '"',
                  'exclude_runs': '(' + ' '.join(map(str, excluded)) + ')'}
        for name, value in values.items():
            text, count = re.subn(r'^' + name + r'=.*$', lambda _: name + '=' + value, text, flags=re.M)
            assert count == 1, name
        (folder / 'run.sh').write_text(text)
        mock = folder / 'mock'
        mock.write_text('#!' + sys.executable + '\n' + '''import json, os, sys, time
from pathlib import Path
run = int(sys.argv[1])
def record(kind):
    fd = os.open('events.jsonl', os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    os.write(fd, (json.dumps([kind, run, os.getcwd()]) + '\\n').encode())
    os.close(fd)
record('start')
print('HIDDEN_STDOUT')
print('HIDDEN_STDERR', file=sys.stderr)
time.sleep(0.15 if run == 1 else 0.8)
record('end')
sys.exit(1 if run == 4 else 0)
''')
        mock.chmod(0o700)
        result = subprocess.run(['bash', str(folder / 'run.sh')], cwd=base,
                                capture_output=True, text=True, timeout=15)
        events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines()] if (folder / 'events.jsonl').exists() else []
        active = peak = 0
        for kind, run, cwd in events:
            assert cwd == str(folder)
            active += 1 if kind == 'start' else -1
            peak = max(peak, active)
            assert 0 <= active <= 5
        assert active == 0
        assert 'HIDDEN_' not in result.stdout + result.stderr
        return result, events, peak


def check():
    """Cover list/range/exclusion/missing inputs, deduplication and continuous refill."""
    subprocess.run(['bash', '-n', str(SCRIPT)], check=True)
    result, events, peak = case([1, 2, 3, 4, 5, 6, 7, 8, 9, 1], start="12", end="1", excluded=[3], absent=[8])
    assert result.returncode == 0 and result.stderr == ''
    assert result.stdout.splitlines() == ['运行：1 2 4 5 6 7 9', '排除：3', '缺失：8']
    assert sorted(run for kind, run, _ in events if kind == 'start') == [1, 2, 4, 5, 6, 7, 9]
    assert peak == 5
    assert next(i for i, e in enumerate(events) if e[:2] == ['start', 7]) < next(i for i, e in enumerate(events) if e[:2] == ['end', 2])
    result, events, _ = case([], start='1', end='6', excluded=[2, 4], absent=[5], pattern='wave_{run}.root')
    assert result.returncode == 0
    assert result.stdout.splitlines() == ['运行：1 3 6', '排除：2 4', '缺失：5']
    assert sorted(run for kind, run, _ in events if kind == 'start') == [1, 3, 6]
    result, events, _ = case([1, 2], excluded=[1, 2])
    assert result.returncode == 0 and not events
    result, events, _ = case([])
    assert result.returncode != 0 and not events
    result, events, _ = case([], start='6', end='1')
    assert result.returncode != 0 and not events
    result, events, _ = case(['bad'])
    assert result.returncode != 0 and not events
    print('PASS: list/range/exclusions/missing/dedup; maximum 5, refill, wait, child failure, /dev/null; portable path/pattern; invalid run configuration')


if __name__ == '__main__':
    check()
