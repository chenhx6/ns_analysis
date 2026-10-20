#!/usr/bin/env python3
"""Reproduce Sheet2 and verify cid=1 values, styles, and Excel sheet registration."""
import csv
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
from xml.etree import ElementTree as E
from zipfile import ZipFile

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[1]
spec = importlib.util.spec_from_file_location('fill_xlsx', ROOT / 'time_offset/time_offset/fill_xlsx.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
N = {'s': module.NS, 'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
     'p': 'http://schemas.openxmlformats.org/package/2006/relationships',
     'c': 'http://schemas.openxmlformats.org/package/2006/content-types',
     'a': 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties',
     'v': 'http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes'}


def verify(before, after, csv_dir):
    """Check every key/value against raw CSVs, independently of the producer."""
    with ZipFile(before) as old, ZipFile(after) as new:
        assert new.testzip() is None
        changed = {'[Content_Types].xml', 'xl/workbook.xml', 'xl/_rels/workbook.xml.rels', 'docProps/app.xml'}
        assert set(new.namelist()) - set(old.namelist()) == {'xl/worksheets/sheet2.xml'}
        for name in old.namelist():
            if name not in changed:
                assert old.read(name) == new.read(name), name
        book = E.fromstring(new.read('xl/workbook.xml'))
        sheets = book.findall('s:sheets/s:sheet', N)
        assert [s.get('name') for s in sheets] == ['Sheet1', 'Sheet2']
        rel_id = sheets[1].get('{' + N['r'] + '}id')
        rels = E.fromstring(new.read('xl/_rels/workbook.xml.rels'))
        assert next(r.get('Target') for r in rels if r.get('Id') == rel_id) == 'worksheets/sheet2.xml'
        types = E.fromstring(new.read('[Content_Types].xml'))
        assert any(t.get('PartName') == '/xl/worksheets/sheet2.xml' and
                   t.get('ContentType').endswith('worksheet+xml') for t in types)
        app = E.fromstring(new.read('docProps/app.xml'))
        assert [n.text for n in app.findall('a:TitlesOfParts/v:vector/v:lpstr', N)] == ['Sheet1', 'Sheet2']
        assert app.find('a:HeadingPairs/v:vector/v:variant/v:i4', N).text == '2'
        sheet1 = E.fromstring(old.read('xl/worksheets/sheet1.xml'))
        sheet2 = E.fromstring(new.read('xl/worksheets/sheet2.xml'))
        first_rows = sheet1.findall('s:sheetData/s:row', N)
        rows = sheet2.findall('s:sheetData/s:row', N)
        assert E.tostring(first_rows[0]) == E.tostring(rows[0])
        for tag in ('cols', 'sheetFormatPr'):
            assert E.tostring(sheet1.find('s:' + tag, N)) == E.tostring(sheet2.find('s:' + tag, N))
        shared = [''.join(s.itertext()) for s in E.fromstring(new.read('xl/sharedStrings.xml'))]
        headers = []
        for cell in rows[0]:
            label = (''.join(cell.find('s:is', N).itertext()) if cell.get('t') == 'inlineStr'
                     else shared[int(cell.find('s:v', N).text)])
            headers.append(label)
        assert headers[:3] == ['cid', 'sid', 'ch']
        runs = [int(label.split()[-1]) for label in headers[3:]]
        assert runs == [6015,6019,6024,6028,6035,6041,6045,6050,6054,6061,6065,6071,6075,6078]
        offsets = {}
        for run in runs:
            with (csv_dir / ('time_offset_' + str(run) + '.csv')).open(newline='') as f:
                offsets[run] = {tuple(int(r[k]) for k in ('cid', 'sid', 'ch')): r['time_offset']
                                for r in csv.DictReader(f)}
        keys = sorted({key for mapping in offsets.values() for key in mapping if key[0] == 1})
        assert len(keys) == 119 and len(rows) == 120
        assert sheet2.find('s:dimension', N).get('ref') == 'A1:Q120'
        counts = dict(matched=0, missing_zero=0, blank_offset=0)
        for index, (row, key) in enumerate(zip(rows[1:], keys), 2):
            assert row.get('r') == str(index) and len(row) == 17
            assert tuple(int(c.find('s:v', N).text) for c in list(row)[:3]) == key
            for template, cell in zip(first_rows[1], row):
                assert template.get('s') == cell.get('s')
            for cell, run in zip(list(row)[3:], runs):
                raw = offsets[run].get(key, '0')
                v = cell.find('s:v', N)
                assert v is None if not raw else Decimal(v.text) == Decimal(raw)
                assert cell.get('t') in (None, 'n')
                kind = 'missing_zero' if key not in offsets[run] else ('blank_offset' if raw == '' else 'matched')
                counts[kind] += 1
        return dict(channels=len(keys), runs=len(runs), verified_cells=len(keys)*len(runs), **counts)


def check():
    """Exercise real-data reproduction, format preservation, and duplicate-sheet refusal."""
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        for path in (TASK / 'inputs').glob('*.csv'):
            shutil.copy2(path, work / path.name)
        before = TASK / 'inputs/time_offset.before-cid1.xlsx'
        output = work / 'time_offset.xlsx'
        shutil.copy2(before, output)
        summary = module.add_cid1_sheet(output)
        result = verify(before, output, work)
        saved = TASK / 'time_offset_with_cid1.xlsx'
        if saved.exists():
            with ZipFile(saved) as a, ZipFile(output) as b:
                assert set(a.namelist()) == set(b.namelist())
                assert all(a.read(n) == b.read(n) for n in a.namelist())
        stable = output.read_bytes()
        try:
            module.add_cid1_sheet(output)
            raise AssertionError('Existing Sheet2 was overwritten')
        except ValueError as error:
            assert 'Sheet2 already exists' in str(error)
        assert output.read_bytes() == stable
        assert (work / 'time_offset.before-cid1.xlsx').read_bytes() == before.read_bytes()
        return dict(result=result, summary=summary,
                    checks=['all cid=1 keys and offsets', 'missing keys zero and empty offsets blank',
                            'Sheet1 and other unmodified ZIP parts byte-identical',
                            'headers, column widths, row format and cell styles copied',
                            'workbook relationships and content types registered',
                            'existing Sheet2 protected and original backup preserved'])


if __name__ == '__main__':
    print(json.dumps(check(), ensure_ascii=False, indent=2))
