#!/usr/bin/env python3
"""Reproduce extraction and check every cell plus unchanged workbook formatting."""
import csv
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import shutil
import tempfile
from xml.etree import ElementTree as E
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fill_xlsx', ROOT / 'time_offset/time_offset/fill_xlsx.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
N = {'s': module.NS}


def verify(before, after, csv_dir):
    """Independently compare numeric CSV values and the XML outside target cells."""
    checked = 0
    with ZipFile(before) as old, ZipFile(after) as new:
        assert new.testzip() is None
        assert old.namelist() == new.namelist()
        shared = [''.join(s.itertext()) for s in E.fromstring(old.read('xl/sharedStrings.xml'))]
        for name in old.namelist():
            if name != 'xl/worksheets/sheet1.xml':
                assert old.read(name) == new.read(name), name
                continue
            original, actual = E.fromstring(old.read(name)), E.fromstring(new.read(name))
            rows = actual.findall('s:sheetData/s:row', N)
            targets = {}
            for cell in rows[0]:
                label = (''.join(cell.find('s:is', N).itertext()) if cell.get('t') == 'inlineStr'
                         else shared[int(cell.find('s:v', N).text)])
                match = module.RUN_HEADER.fullmatch(label)
                if match:
                    with (csv_dir / ('time_offset_' + match[1] + '.csv')).open() as f:
                        targets[cell.get('r')[:-1]] = {
                            tuple(int(r[k]) for k in ('cid', 'sid', 'ch')): r['time_offset']
                            for r in csv.DictReader(f)}
            for row in rows[1:]:
                cells = {c.get('r'): c for c in row}
                key = tuple(int(cells[col + row.get('r')].find('s:v', N).text)
                            for col in ('A', 'B', 'C'))
                for col, offsets in targets.items():
                    cell = cells[col + row.get('r')]
                    raw = offsets.get(key, '0')
                    v = cell.find('s:v', N)
                    assert (v is None) if not raw else (module.Decimal(v.text) == module.Decimal(raw))
                    assert cell.get('t') in (None, 'n')
                    checked += 1
            old_header = original.find('s:sheetData/s:row', N)
            new_header = actual.find('s:sheetData/s:row', N)
            original_refs = {c.get('r') for c in old_header}
            for cell in list(new_header):
                if cell.get('r') not in original_refs:
                    assert cell.get('r').rstrip('0123456789') in targets
                    new_header.remove(cell)
            assert actual.find('s:dimension', N).get('ref') == 'A1:Q80'
            actual.find('s:dimension', N).attrib = dict(original.find('s:dimension', N).attrib)
            # Exclude the required range expansion and new columns from layout comparison.
            for old_row, new_row in zip(original.findall('s:sheetData/s:row', N), rows):
                assert new_row.get('spans') == '1:17'
                if old_row.get('spans') is None:
                    new_row.attrib.pop('spans', None)
                else:
                    new_row.set('spans', old_row.get('spans'))
            for sheet in (original, actual):
                for row in sheet.findall('s:sheetData/s:row', N)[1:]:
                    for cell in list(row):
                        if cell.get('r').rstrip('0123456789') in targets:
                            row.remove(cell)
            assert E.tostring(original) == E.tostring(actual)
            original_cells = {c.get('r'): c for c in E.fromstring(old.read(name)).findall('.//s:c', N)}
            for cell in E.fromstring(new.read(name)).findall('.//s:c', N):
                if cell.get('r') in original_cells:
                    assert cell.get('s') == original_cells[cell.get('r')].get('s')
    return checked


def check():
    """Exercise real inputs, absent keys, blanks, negative values, and failed writes."""
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        for file in (TASK / 'inputs').iterdir():
            shutil.copy2(file, work / file.name)
        book = work / 'time_offset.xlsx'
        summary = module.fill(book)
        count = verify(TASK / 'inputs/time_offset.xlsx', book, work)
        assert count == 1106
        assert [c['run'] for c in summary[0]['columns'].values()] == [
            '6015', '6019', '6024', '6028', '6035', '6041', '6045',
            '6050', '6054', '6061', '6065', '6071', '6075', '6078']
        if (TASK / 'time_offset.xlsx').exists():
            with ZipFile(book) as produced, ZipFile(TASK / 'time_offset.xlsx') as saved:
                assert all(produced.read(n) == saved.read(n) for n in produced.namelist())
        # A second fill reuses all headers and yields identical worksheet content.
        first = book.read_bytes()
        module.fill(book)
        with ZipFile(BytesIO(first)) as old, ZipFile(book) as new:
            assert all(old.read(n) == new.read(n) for n in old.namelist())
        # Synthetic CSV changes are confined to temporary files, never experimental inputs.
        path = work / 'time_offset_6015.csv'
        with path.open() as f:
            reader = csv.DictReader(f)
            fields, records = reader.fieldnames, list(reader)
        records = [r for r in records if (r['cid'], r['sid'], r['ch']) != ('0', '2', '4')]
        for row in records:
            if (row['cid'], row['sid'], row['ch']) == ('0', '2', '5'):
                row['time_offset'] = ''
            if (row['cid'], row['sid'], row['ch']) == ('0', '2', '6'):
                row['time_offset'] = '-16'
        with path.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
        module.fill(book)
        verify(TASK / 'inputs/time_offset.xlsx', book, work)
        stable = book.read_bytes()
        with path.open('a', newline='') as f:
            csv.DictWriter(f, fieldnames=fields).writerow(records[0])
        try:
            module.fill(book)
            raise AssertionError('Duplicate channel accepted')
        except ValueError as error:
            assert 'Duplicate channel' in str(error)
        assert book.read_bytes() == stable
        path.unlink()
        try:
            module.fill(book)
            raise AssertionError('Missing CSV accepted')
        except FileNotFoundError:
            pass
        assert book.read_bytes() == stable
        assert (work / 'time_offset.before-fill.xlsx').read_bytes() == (TASK / 'inputs/time_offset.xlsx').read_bytes()
        return dict(verified_cells=count, summary=summary,
                    checks=['all 14 runs and 1106 cells', 'new run headers and expanded range',
                            'second fill does not duplicate headers',
                            'every CSV value and missing key', 'existing empty offsets remain blank',
                            'negative values', 'unchanged styles and non-target XML',
                            'duplicate channel and missing CSV reject before writing', 'original backup preserved'])


if __name__ == '__main__':
    print(json.dumps(check(), ensure_ascii=False, indent=2))
