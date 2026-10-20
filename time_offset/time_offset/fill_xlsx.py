#!/usr/bin/env python3
"""Fill time offset run columns from all sibling CSVs; preserve other XLSX parts.

Usage: python3 time_offset/time_offset/fill_xlsx.py time_offset/time_offset.xlsx
CSV files are read from the workbook directory. A .before-fill.xlsx backup
is kept locally on the first run. Missing channels become 0; empty CSV
offsets remain blank. Missing run columns are appended in run-number order;
existing channel rows and column positions are preserved.
Use --add-cid1-sheet to create Sheet2 from all cid=1 channels in those run
CSVs, copying Sheet1 formatting and leaving Sheet1 unchanged.
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


def write_workbook(workbook, original, updates, backup_suffix):
    """Write changed ZIP parts atomically; retain all unchanged parts and a backup."""
    backup = workbook.with_name(workbook.stem + backup_suffix + '.xlsx')
    if not backup.exists():
        backup.write_bytes(original)
    temporary = None
    try:
        with ZipFile(BytesIO(original)) as source:
            with tempfile.NamedTemporaryFile(dir=workbook.parent, suffix='.xlsx', delete=False) as stream:
                temporary = Path(stream.name)
                with ZipFile(stream, 'w') as target:
                    target.comment = source.comment
                    for info in source.infolist():
                        target.writestr(info, updates.get(info.filename, source.read(info.filename)))
                    for name in updates.keys() - set(source.namelist()):
                        target.writestr(name, updates[name])
        if workbook.read_bytes() != original:
            raise RuntimeError('Workbook changed during processing; no overwrite')
        shutil.copymode(workbook, temporary)
        temporary.replace(workbook)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def add_cid1_sheet(workbook):
    """Create Sheet2 using the union of cid=1 keys and the run columns of Sheet1."""
    workbook = Path(workbook).resolve()
    original = workbook.read_bytes()
    relationship_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    with ZipFile(BytesIO(original)) as source:
        book = minidom.parseString(source.read('xl/workbook.xml'))
        sheets = book.getElementsByTagNameNS(NS, 'sheet')
        if any(s.getAttribute('name').lower() == 'sheet2' for s in sheets):
            raise ValueError('Sheet2 already exists; preserve it without overwriting')
        first = next(s for s in sheets if s.getAttribute('name') == 'Sheet1')
        rels = minidom.parseString(source.read('xl/_rels/workbook.xml.rels'))
        relationships = list(rels.documentElement.childNodes)
        relationships = [r for r in relationships if r.nodeType == r.ELEMENT_NODE]
        first_rel = next(r for r in relationships
                         if r.getAttribute('Id') == first.getAttributeNS(relationship_ns, 'id'))
        first_path = first_rel.getAttribute('Target')
        first_path = first_path.lstrip('/') if first_path.startswith('/') else 'xl/' + first_path
        doc = minidom.parseString(source.read(first_path))
        shared_doc = minidom.parseString(source.read('xl/sharedStrings.xml'))
        shared = [text(s) for s in shared_doc.getElementsByTagNameNS(NS, 'si')]
        data = doc.getElementsByTagNameNS(NS, 'sheetData')[0]
        rows = children(data, 'row')
        headers = children(rows[0], 'c')
        if [value(c, shared) for c in headers[:3]] != ['cid', 'sid', 'ch']:
            raise ValueError('Expected cid/sid/ch in Sheet1 columns A/B/C')
        runs = {c.getAttribute('r').rstrip('0123456789'): RUN_HEADER.fullmatch(value(c, shared)).group(1)
                for c in headers[3:]}
        offsets = {col: read_offsets(workbook.parent / ('time_offset_' + run + '.csv'))
                   for col, run in runs.items()}
        # A row is present when any run contains that cid=1 channel, even with blank offset.
        keys = sorted({key for mapping in offsets.values() for key in mapping if key[0] == 1})
        if not keys:
            raise ValueError('No cid=1 channels in CSVs')
        template = rows[1]
        patterns = {c.getAttribute('r').rstrip('0123456789'): c for c in children(template, 'c')}
        for row in rows[1:]:
            data.removeChild(row)
        counts = {col: dict(run=run, matched=0, missing_zero=0, blank_offset=0)
                  for col, run in runs.items()}
        for index, key in enumerate(keys, 2):
            row = template.cloneNode(False)
            row.setAttribute('r', str(index))
            for header in headers:
                col = header.getAttribute('r').rstrip('0123456789')
                cell = patterns[col].cloneNode(False)
                cell.setAttribute('r', col + str(index))
                if cell.hasAttribute('t'):
                    cell.removeAttribute('t')
                if col in ('A', 'B', 'C'):
                    raw = str(key[ord(col) - ord('A')])
                else:
                    raw = offsets[col].get(key, '0')
                    kind = 'missing_zero' if key not in offsets[col] else (
                        'blank_offset' if raw == '' else 'matched')
                    counts[col][kind] += 1
                if raw:
                    prefix = cell.prefix
                    node = doc.createElementNS(NS, (prefix + ':' if prefix else '') + 'v')
                    node.appendChild(doc.createTextNode(raw))
                    cell.appendChild(node)
                row.appendChild(cell)
            data.appendChild(row)
        last_col = headers[-1].getAttribute('r').rstrip('0123456789')
        doc.getElementsByTagNameNS(NS, 'dimension')[0].setAttribute('ref', 'A1:' + last_col + str(len(keys) + 1))
        sheet_id = max(int(s.getAttribute('sheetId')) for s in sheets) + 1
        sheet_path = 'xl/worksheets/sheet' + str(sheet_id) + '.xml'
        if sheet_path in source.namelist():
            raise ValueError('Worksheet part already exists: ' + sheet_path)
        rel_id = 'rId' + str(max(int(r.getAttribute('Id')[3:]) for r in relationships) + 1)
        sheet = first.cloneNode(False)
        sheet.setAttribute('name', 'Sheet2')
        sheet.setAttribute('sheetId', str(sheet_id))
        sheet.setAttributeNS(relationship_ns, 'r:id', rel_id)
        first.parentNode.appendChild(sheet)
        relation = first_rel.cloneNode(False)
        relation.setAttribute('Id', rel_id)
        relation.setAttribute('Target', sheet_path[3:])
        rels.documentElement.appendChild(relation)
        types = minidom.parseString(source.read('[Content_Types].xml'))
        override = next(n for n in types.documentElement.childNodes
                        if n.nodeType == n.ELEMENT_NODE and n.getAttribute('PartName') == '/' + first_path)
        new_override = override.cloneNode(False)
        new_override.setAttribute('PartName', '/' + sheet_path)
        types.documentElement.appendChild(new_override)
        app = minidom.parseString(source.read('docProps/app.xml'))
        app_ns = app.documentElement.namespaceURI
        vt_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes'
        titles = app.getElementsByTagNameNS(app_ns, 'TitlesOfParts')[0]
        vector = titles.getElementsByTagNameNS(vt_ns, 'vector')[0]
        title = vector.getElementsByTagNameNS(vt_ns, 'lpstr')[0].cloneNode(False)
        title.appendChild(app.createTextNode('Sheet2'))
        vector.appendChild(title)
        vector.setAttribute('size', str(len(sheets) + 1))
        app.getElementsByTagNameNS(vt_ns, 'i4')[0].firstChild.data = str(len(sheets) + 1)
        updates = {sheet_path: doc.toxml(encoding='UTF-8'), 'xl/workbook.xml': book.toxml(encoding='UTF-8'),
                   'xl/_rels/workbook.xml.rels': rels.toxml(encoding='UTF-8'),
                   '[Content_Types].xml': types.toxml(encoding='UTF-8'),
                   'docProps/app.xml': app.toxml(encoding='UTF-8')}
    write_workbook(workbook, original, updates, '.before-cid1')
    return dict(sheet='Sheet2', cid=1, channels=len(keys), columns=counts)


def fill(workbook):
    """Discover runs, append missing columns, validate and replace atomically."""
    workbook = Path(workbook).resolve()
    original = workbook.read_bytes()
    discovered = sorted({m.group(1) for p in workbook.parent.glob('time_offset_*.csv')
                         for m in [re.fullmatch(r'time_offset_(\d+)\.csv', p.name)] if m}, key=int)
    if not discovered:
        raise ValueError('No time_offset_<run>.csv files beside workbook')
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
            template = next((c for c in children(rows[0], 'c')
                             if c.getAttribute('r').rstrip('0123456789') in runs), None)
            last_col = max(headers, key=lambda col: (len(col), col))
            last_number = 0
            for letter in last_col:
                last_number = last_number * 26 + ord(letter) - ord('A') + 1
            added = []
            for run in discovered:
                if run in runs.values():
                    continue
                last_number += 1
                number, col = last_number, ''
                while number:
                    number, remainder = divmod(number - 1, 26)
                    col = chr(ord('A') + remainder) + col
                cell = template.cloneNode(False) if template is not None else doc.createElementNS(NS, 'c')
                cell.setAttribute('r', col + rows[0].getAttribute('r'))
                cell.setAttribute('t', 'inlineStr')
                prefix = cell.prefix
                inline = doc.createElementNS(NS, (prefix + ':' if prefix else '') + 'is')
                label = doc.createElementNS(NS, (prefix + ':' if prefix else '') + 't')
                label.appendChild(doc.createTextNode('time offset ' + run))
                inline.appendChild(label)
                cell.appendChild(inline)
                rows[0].appendChild(cell)
                runs[col] = run
                added.append(col)
            if added:
                dimension = doc.getElementsByTagNameNS(NS, 'dimension')[0]
                first, last = dimension.getAttribute('ref').split(':')
                dimension.setAttribute('ref', first + ':' + added[-1] + re.search(r'\d+$', last).group())
                for row in rows:
                    row.setAttribute('spans', '1:' + str(last_number))
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
                        # Extend the original run-column style to newly created run columns.
                        if col in added:
                            pattern = cells.get(next(iter(runs)) + row.getAttribute('r'))
                            if pattern is not None and pattern.hasAttribute('s'):
                                cell.setAttribute('s', pattern.getAttribute('s'))
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
    write_workbook(workbook, original, updates, '.before-fill')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook', type=Path)
    parser.add_argument('--add-cid1-sheet', action='store_true', help='Create Sheet2 for cid=1; preserve Sheet1')
    args = parser.parse_args()
    action = add_cid1_sheet if args.add_cid1_sheet else fill
    print(json.dumps(action(args.workbook), ensure_ascii=False, indent=2))
