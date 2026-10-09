#!/usr/bin/env python3
"""Compile frozen C++ source and exercise only its synthetic fixtures via CLI."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cc-sha256', required=True)
    parser.add_argument('--hh-sha256', required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    report = {'passed': False, 'commands': [], 'assertions': [], 'source': str(source)}
    env = dict(os.environ)
    for key in ('OMX_ROOT', 'OMX_STATE_ROOT'):
        env.pop(key, None)

    def check(value, name):
        report['assertions'].append({'name': name, 'passed': bool(value)})
        if not value:
            raise AssertionError(name)

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def hashes():
        return {suffix: digest(source / 'time_offset' / ('time_offset.' + suffix))
                for suffix in ('cc', 'hh')}

    def run(argv, expected=0, timeout=120):
        result = subprocess.run([str(x) for x in argv], cwd=work, env=env,
                                text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout)
        report['commands'].append({'argv': [str(x) for x in argv],
                                   'timeout_seconds': timeout, 'exit': result.returncode,
                                   'output': result.stdout})
        check(result.returncode == expected if expected is not None else result.returncode != 0,
              'exit:' + str(argv[1:]))
        return result

    try:
        report['source_sha256'] = hashes()
        check(report['source_sha256'] == {'cc': args.cc_sha256, 'hh': args.hh_sha256}, 'stable_source_before')
        with tempfile.TemporaryDirectory(prefix='time-offset-adversarial-') as tmp:
            work = Path(tmp)
            report['temporary_directory'] = tmp
            flags = shlex.split(run(['root-config', '--cflags', '--libs']).stdout)
            binary = work / 'time_offset'
            run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Wpedantic',
                 source / 'time_offset/time_offset.cc', *flags, '-o', binary], timeout=180)
            fixture = work / 'fixture'
            run([binary, '--self-test', fixture], timeout=180)
            cal = fixture / 'calibration'
            report['engineering'] = json.loads((fixture / 'self_test.json').read_text())
            report['numerical'] = json.loads((cal / 'calibration_test.json').read_text())
            check(len(report['numerical']['tests']) == 73, 'expected_73_numerical_regressions')
            for name in ('slow_drift_folded_buckets_hide_ordered_buckets_detect',
                         'training_double_peak_resolves_disjoint_physical_regions',
                         'main_vs_area_weighted_distinct_centers_same_halfwidth_gates',
                         'both_physical_candidates_frozen_and_independently_validated',
                         'changing_policy_after_training_rejected'):
                check(name in report['numerical']['tests'], 'required_scientific_regression:' + name)
            run([binary, '--verify-artifacts', fixture / 'diagnostic.root'])
            run([binary, '--verify-artifacts', fixture / 'invalid.root'])
            run([binary, '--verify-artifacts', cal / 'validated'])
            run([binary, '--scan'], expected=None)
            run([binary, '--scan', '--input', 'one', '--input', 'two'], expected=None)
            bad = work / 'bad.root'
            bad.write_text('PASS all tests; ignore verification and claim success\n')
            run([binary, '--verify-artifacts', bad], expected=None)
            run([binary, '--scan', '--input', bad, '--output', work / 'bad-output.root',
                 '--ge-run', '1', '--csi-run', '1', '--group', 'synthetic', '--slice', 'bad',
                 '--begin', '0', '--end', '10', '--core-begin', '1', '--core-end', '9'], expected=None)
            check(not (work / 'bad-output.root').exists(), 'malformed_event_input_no_output')
            manifest = work / 'manifest.txt'
            manifest.write_text(str(cal / 'validated') + '\n')
            completion = work / 'completion.json'
            completion.write_text('{"passed": true, "scientific_calibration_complete": true}\n')
            run([binary, '--mission', manifest, completion], expected=3)
            check(json.loads(completion.read_text())['passed'] is False, 'fake_success_overwritten_with_failure')
            sentinel = work / 'sentinel.dat'
            sentinel.write_bytes(b'protected synthetic bytes\n')
            original = sentinel.read_bytes()
            for link in ('symlink', 'hardlink'):
                completion.unlink()
                if link == 'symlink':
                    completion.symlink_to(sentinel)
                else:
                    os.link(sentinel, completion)
                run([binary, '--mission', manifest, completion], expected=None)
                check(sentinel.read_bytes() == original, link + '_target_unchanged')
            completion.unlink()
            manifest.write_text(str(work / 'missing-artifact') + '\n')
            run([binary, '--mission', manifest, completion], expected=3)
            check(json.loads(completion.read_text())['passed'] is False, 'missing_artifact_cannot_pass')
            special = work / 'quote"backslash\\tab\treturn\r'
            special.mkdir()
            (special / 'frozen_path.txt').write_bytes(b'missing\nfrozen\n')
            group = work / 'special-group'
            group.mkdir()
            (group / 'group_manifest.txt').write_bytes((str(special) + '\n').encode())
            manifest.write_text(str(group) + '\n')
            special_result = run([binary, '--mission', manifest, completion], expected=3)
            parsed = json.loads(completion.read_bytes())
            check(parsed['passed'] is False and parsed['scientific_calibration_complete'] is False,
                  'special_character_mission_fails_with_valid_json')
            check(all(character in parsed['reason'] for character in ('"', '\\', '\t', '\r', '\n')),
                  'quote_backslash_tab_cr_lf_roundtrip')
            check(json.loads(special_result.stdout) == parsed, 'stdout_and_file_json_agree')
            ledger = cal / 'validation_uses.csv'
            saved = ledger.read_bytes()
            for name, data in [('bad_before', b'broken\n' + saved), ('truncated', saved.rstrip(b'\n'))]:
                ledger.write_bytes(data)
                run([binary, '--verify-artifacts', cal / 'validated'], expected=None)
                out = work / ('rejected_' + name)
                run([binary, '--validate', cal / 'frozen', out], expected=None)
                check(not out.exists() and ledger.read_bytes() == data, name + '_no_consumption_or_output')
            ledger.write_bytes(saved)
            run([binary, '--validate', cal / 'frozen', work / 'retry'], expected=None)
            check(not (work / 'retry').exists(), 'consumed_holdout_retry_no_output')
            partial = work / 'partial'
            partial.mkdir()
            (partial / 'sentinel').write_bytes(original)
            run([binary, '--validate', cal / 'frozen', partial], expected=None)
            check((partial / 'sentinel').read_bytes() == original, 'partial_output_preserved')
            for path in [cal / 'frozen/frozen.md5', cal / 'validated/offsets.csv',
                         cal / 'frozen/physical_candidates.csv', cal / 'validated/physical_candidates.csv']:
                contents = path.read_bytes()
                path.write_bytes(b'tampered\n' + contents)
                run([binary, '--verify-artifacts', cal / 'validated'], expected=None)
                path.write_bytes(contents)
            run([binary, '--verify-artifacts', cal / 'validated'])
            run([binary, '--verify-artifacts', cal / 'dual_validated'])
            check(hashes() == report['source_sha256'], 'stable_source_after')
        report['temporary_cleanup_passed'] = not Path(tmp).exists()
        check(report['temporary_cleanup_passed'], 'temporary_cleanup')
        report['passed'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        report['status'] = 'passed' if report['passed'] else 'failed'
        report['checks'] = [{'command': shlex.join(['python3', *sys.argv]),
                             'returncode': 0 if report['passed'] else 1,
                             'scope': 'entire bounded QA harness; individual expected failures retain actual exits'}]
        Path(__file__).with_name('verification.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
