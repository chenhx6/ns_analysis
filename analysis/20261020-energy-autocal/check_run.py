"""Repeatable delivery check: verify autocal, mock algorithms, and saved results."""
import csv
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CALIB = ROOT / 'calibration/energy/autocal'
CHECK = ROOT / 'analysis/20261020-energy-autocal/check_algorithm'
OUT = ROOT / 'calibration/energy/data_C1_6082_notwave'

def run(cmd, check=True):
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr}\n{p.stdout}")
    return p

def main():
    fixture = ROOT / 'analysis/20261020-energy-autocal/fixture.root'
    mock_out = ROOT / 'analysis/20261020-energy-autocal/mock-out'
    try:
        run(['make', '-C', str(CALIB), 'clean'])
        run(['make', '-C', str(CALIB)])
        run(['g++', '-O2', '-std=c++17', *run(['root-config', '--cflags']).stdout.split(),
             '-I' + str(CALIB), 'analysis/20261020-energy-autocal/check_algorithm.cc',
             str(CALIB / 'peakfinder.o'), str(CALIB / 'autocal.o'),
             str(CALIB / 'plotexport.o'),
             *run(['root-config', '--libs']).stdout.split(), '-lSpectrum', '-o', str(CHECK)])
        run([str(CHECK), str(fixture)])
        # Test error handling on incompatible branch types.
        assert run([str(CALIB / 'autocal'), '--input', str(fixture) + '.bad.root', '--output', str(OUT) + '.test'], check=False).returncode != 0
        # Source selection is intentionally not a command-line override.
        assert run([str(CALIB / 'autocal'), '--input', str(fixture), '--sources', 'bad_source', '--output', str(OUT) + '.test'], check=False).returncode != 0
        # Test mock tree execution and exclusion triple.
        if mock_out.exists():
            shutil.rmtree(mock_out)
        run([str(CALIB / 'autocal'), '--input', str(fixture), '--exclude', '0:42:9', '--output', str(mock_out)])
        run([str(CHECK), str(mock_out / 'histograms.root'), '201100', '2'])
        # Independently inspect real 6082 results.
        run([str(CHECK), str(OUT / 'histograms.root'), '8275299', '39'])
        rows = list(csv.DictReader((OUT / 'calibration.csv').open()))
        assert len(rows) == 39
        statuses = {r['status'] for r in rows}
        assert 'success' in statuses and 'poor_fit' in statuses
        assert len(list((OUT / 'figures').glob('*.svg'))) == 40
        assert not list((OUT / 'figures').glob('*.png'))
        import ROOT as root_module
        root_file = root_module.TFile.Open(str(OUT / 'histograms.root'), 'READ')
        assert root_file and not root_file.IsZombie()
        for key in root_file.GetListOfKeys():
            obj = key.ReadObj()
            if obj.GetName() == 'h2_energy_cal':
                continue
            assert obj.GetNbinsX() == 65536 and abs(obj.GetXaxis().GetBinWidth(1) - 1.) < 1e-12
        root_file.Close()
        print('Verification checks passed.')
    finally:
        # Clean up temporary verification artifacts so git tree remains pristine
        if mock_out.exists():
            shutil.rmtree(mock_out)
        for f in [fixture, Path(str(fixture) + '.bad.root'), CHECK]:
            if f.exists():
                f.unlink()

if __name__ == '__main__':
    main()
