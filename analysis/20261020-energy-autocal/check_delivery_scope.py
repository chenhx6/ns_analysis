"""Check energy-calibration delivery scope without creating scientific data."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'analysis/scripts'))
from check_git_content import permitted
from session_coordinator import relative


def check():
    """Compare object policy and Git ignore rules for representative files."""
    allowed = ['autocal/main.cc', 'autocal/peakfinder.hh', 'autocal/UserDefine.hh',
               'autocal/Makefile', 'autocal/sources.csv', 'autocal/README.md',
               'run/calibration.csv', 'run/figures/cid0_sid2_ch5.png']
    blocked = ['autocal/autocal', 'autocal/main.o', 'run/histograms.root',
               'run/data.bin', 'autocal/credentials.json', 'autocal/auth.json',
               'autocal/build/temporary.cc']
    ordinary_git = (ROOT / '.git/HEAD').is_file() or (ROOT / '.git').is_file()
    git = ['git', '-C', str(ROOT)] if ordinary_git else [
        'git', '--git-dir=' + str(ROOT / '.project-git'), '--work-tree=' + str(ROOT)]
    for suffix, expected in [(p, True) for p in allowed] + [(p, False) for p in blocked]:
        name = 'calibration/energy/' + suffix
        assert permitted(name) == expected, name
        result = subprocess.run(git + ['check-ignore', '--no-index', '-v', name],
                                cwd=ROOT, capture_output=True, text=True)
        # Verbose check-ignore also returns matching negations; inspect the rule.
        assert result.returncode == 0 and '\t' in result.stdout, name
        rule = result.stdout.split('\t', 1)[0].rsplit(':', 1)[-1]
        assert rule.startswith('!') == expected, (name, rule)
    assert not permitted('calibration/unrelated/main.cc')
    assert relative('calibration/energy/') == 'calibration/energy/'
    print('Energy delivery scope passed: sources/results allowed; binaries/data/secrets excluded.')


if __name__ == '__main__':
    check()
