#!/usr/bin/env python3
"""Fill existing time offset run columns from CSV; preserve other XLSX parts.

Usage: python3 time_offset/time_offset/fill_xlsx.py time_offset/time_offset.xlsx
CSV files are read from the workbook directory. A .before-fill.xlsx backup
is kept locally on the first run. Missing channels become 0; empty CSV
offsets remain blank. No run columns or channel rows are added.
"""
import argparse
import csv
from decimal import Decimal
from io import BytesIO
import json
from pathlib import Path
import re
import shutil
import tempfile
from xml.dom import minidom
from zipfile import ZipFile

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
RUN_HEADER = re.compile(r'time[ _]+offset[ _]+(\d+)', re.IGNORECASE)


def children(node, name):
    """Return direct spreadsheet children without depending on XML prefixes."""
    return [c for c in node.childNodes
            if c.nodeType == c.ELEMENT_NODE and c.localName == name]


def text(node):
    """Read text from an XML value or rich shared string."""
    return ''.join(c.data if c.nodeType in (c.TEXT_NODE, c.CDATA_SECTION_NODE)
                   else text(c) for c in node.childNodes)


def value(cell, shared):
    """Decode the cell formats used for channel addresses and headers."""
    if cell is None:
        return ''
    if cell.getAttribute('t') == 'inlineStr':
        return ''.join(text(t) for t in cell.getElementsByTagNameNS(NS, 't'))
    nodes = children(cell, 'v')
    raw = text(nodes[0]) if nodes else ''
    return shared[int(raw)] if cell.getAttribute('t') == 's' else raw


def read_offsets(path):
    """Read unique channel keys; keep unknown offsets distinct from zero (ns)."""
    offsets = {}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not {'cid', 'sid', 'ch', 'time_offset'} <= set(reader.fieldnames or []):
            raise ValueError('Missing CSV fields: ' + str(path))
        for row in reader:
            key = tuple(int(row[k]) for k in ('cid', 'sid', 'ch'))
            if key in offsets:
                raise ValueError('Duplicate channel {} in {}'.format(key, path))
            raw = row['time_offset'].strip()
            number = Decimal(raw) if raw else None
            if number is not None and not number.is_finite():
                raise ValueError('Non-finite offset in ' + str(path))
            offsets[key] = format(number, 'f') if number is not None else ''
    return offsets


def fill(workbook):
    """Validate all inputs, update existing run columns, then replace atomically."""
    workbook = Path(workbook).resolve()
    original = workbook.read_bytes()
    updates, summary = {}, []
    with ZipFile(BytesIO(original)) as source:
        shared = []
        if 'xl/sharedStrings.xml' in source.namelist():
            doc = minidom.parseString(source.read('xl/sharedStrings.xml'))
            shared = [text(s) for s in doc.getElementsByTagNameNS(NS, 'si')]
        for name in source.namelist():
            if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml', name):
                continue
            doc = minidom.parseString(source.read(name))
            rows = list(doc.getElementsByTagNameNS(NS, 'row'))
            if not rows:
                continue
            headers = {re.sub(r'\d+$', '', c.getAttribute('r')): value(c, shared).strip()
                       for c in children(rows[0], 'c')}
            if [headers.get(c) for c in ('A', 'B', 'C')] != ['cid', 'sid', 'ch']:
                continue
            runs = {col: RUN_HEADER.fullmatch(header).group(1)
                    for col, header in headers.items() if RUN_HEADER.fullmatch(header)}
            if not runs:
                continue
            offsets = {col: read_offsets(workbook.parent / ('time_offset_' + run + '.csv'))
                       for col, run in runs.items()}
            counts = {col: dict(run=run, matched=0, missing_zero=0, blank_offset=0)
                      for col, run in runs.items()}
            for row in rows[1:]:
                cells = {c.getAttribute('r'): c for c in children(row, 'c')}
                address = [value(cells.get(col + row.getAttribute('r')), shared)
                           for col in ('A', 'B', 'C')]
                if not any(address):
                    continue
                key = tuple(int(item) for item in address)
                for col in runs:
                    # Only absent channel keys get 0; an existing unknown stays blank.
                    raw = offsets[col].get(key, '0')
                    kind = 'missing_zero' if key not in offsets[col] else (
                        'blank_offset' if raw == '' else 'matched')
                    counts[col][kind] += 1
                    ref = col + row.getAttribute('r')
                    cell = cells.get(ref)
                    if cell is None:
                        prefix = doc.documentElement.prefix
                        cell = doc.createElementNS(NS, (prefix + ':' if prefix else '') + 'c')
                        cell.setAttribute('r', ref)
                        # Excel cell order is column order, including columns beyond Z.
                        order = lambda s: (len(s), s)
                        following = next((c for c in children(row, 'c')
                                          if order(re.sub(r'\d+$', '', c.getAttribute('r')))
                                          > order(col)), None)
                        row.insertBefore(cell, following)
                    if cell.hasAttribute('t'):
                        cell.removeAttribute('t')
                    for child in list(cell.childNodes):
                        cell.removeChild(child)
                    if raw:
                        prefix = cell.prefix
                        node = doc.createElementNS(NS, (prefix + ':' if prefix else '') + 'v')
                        node.appendChild(doc.createTextNode(raw))
                        cell.appendChild(node)
            updates[name] = doc.toxml(encoding='UTF-8')
            summary.append(dict(sheet_xml=name, columns=counts))
        if not updates:
            raise ValueError('No sheet with cid/sid/ch and time offset run headers')
        backup = workbook.with_name(workbook.stem + '.before-fill.xlsx')
        if not backup.exists():
            shutil.copy2(workbook, backup)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=workbook.parent, suffix='.xlsx', delete=False) as stream:
                temporary = Path(stream.name)
                with ZipFile(stream, 'w') as target:
                    target.comment = source.comment
                    for info in source.infolist():
                        target.writestr(info, updates.get(info.filename, source.read(info.filename)))
            if workbook.read_bytes() != original:
                raise RuntimeError('Workbook changed during processing; no overwrite')
            shutil.copymode(workbook, temporary)
            temporary.replace(workbook)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook', type=Path)
    args = parser.parse_args()
    print(json.dumps(fill(args.workbook), ensure_ascii=False, indent=2))
