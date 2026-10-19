"""Disposable ROOT input checks for the single-file PNG exporter."""
from pathlib import Path
import hashlib
import shutil
import struct
import subprocess
import sys
import tempfile

import ROOT

ROOT.gROOT.SetBatch(True)
PROJECT = Path(__file__).resolve().parents[2]
TOOL = PROJECT / 'time_offset/export_histograms.py'


def check():
    """Check suffixes, latest ROOT cycle, natural order, PNGs and read-only input."""
    with tempfile.TemporaryDirectory(prefix='chx-root-png-') as temporary:
        folder = Path(temporary)
        script = folder / 'export_histograms.py'
        shutil.copyfile(TOOL, script)
        filename = folder / 'time_offset_1.root'
        with ROOT.TFile(str(filename), 'RECREATE'):
            for name in ['cid0_sid2_ch10_24ns', 'cid0_sid2_ch2_24ns', 'cid0_sid2_ch2_2ns']:
                hist = ROOT.TH1D(name, name + ';Time difference [ns];Counts', 80, -400, 400)
                fit = ROOT.TF1('time_fit', 'gaus', -200, 200)
                fit.SetParameters(100, 20, 40)
                fit.SetLineColor(ROOT.kRed)
                for i in range(1, 81):
                    hist.SetBinContent(i, fit.Eval(hist.GetBinCenter(i)) + 2)
                hist.GetListOfFunctions().Add(fit.Clone())
                hist.Write()
                if name.endswith('_2ns'):
                    hist.Write()  # Same-name cycles must not duplicate exported images.
            ROOT.TNamed('metadata_24ns', 'not a histogram').Write()
        before = hashlib.sha256(filename.read_bytes()).hexdigest()
        for suffix, expected in [('_24ns', ['0001_cid0_sid2_ch2_24ns.png', '0002_cid0_sid2_ch10_24ns.png']),
                                 ('_2ns', ['0001_cid0_sid2_ch2_2ns.png']), ('_missing', [])]:
            output = folder / suffix
            subprocess.run([sys.executable, str(script), '1', suffix, str(output)], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            assert sorted(p.name for p in output.iterdir()) == expected
            for image in output.glob('*.png'):
                data = image.read_bytes()
                assert data[:8] == b'\x89PNG\r\n\x1a\n'
                width, height = struct.unpack('>II', data[16:24])
                assert width > 1000 and height > 700
        assert hashlib.sha256(filename.read_bytes()).hexdigest() == before
    print('PASS: suffix selection, TH1 filtering, latest cycles, channel order, PNG output, input unchanged')


if __name__ == '__main__':
    check()
