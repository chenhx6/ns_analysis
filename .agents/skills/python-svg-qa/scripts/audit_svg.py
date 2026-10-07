#!/usr/bin/env python3
"""Audit final SVG text geometry with Chromium; preview bytes never touch disk."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

PROJECT = next(parent for parent in Path(__file__).resolve().parents
               if (parent / 'AGENTS.md').is_file() and (parent / 'analysis').is_dir())


def validate_report(path, inputs):
    target = path.resolve()
    if (target.suffix != '.json' or PROJECT not in target.parents
            or any(target == source.resolve() for source in inputs)):
        raise ValueError('Report must be a project JSON file separate from SVG inputs')
    if path.exists() or path.is_symlink():
        raise FileExistsError('Refusing to overwrite report: ' + str(path))
    return target


GEOMETRY = r"""() => {
  const svg = document.documentElement;
  const rect = r => ({left:r.left, top:r.top, right:r.right, bottom:r.bottom});
  const texts = [...svg.querySelectorAll('text')].filter(el => {
    for (let n=el; n && n.nodeType===1; n=n.parentElement) {
      const s=getComputedStyle(n);
      if(s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0) return false;
    }
    return el.textContent.trim() && el.getBoundingClientRect().width>0;
  }).map((el,i) => {
    const clips=[];
    for(let n=el;n && n!==svg;n=n.parentElement) {
      if(getComputedStyle(n).clipPath!=='none') clips.push(getComputedStyle(n).clipPath);
    }
    return {index:i, text:el.textContent, ...rect(el.getBoundingClientRect()), clips};
  });
  return {canvas:rect(svg.getBoundingClientRect()), texts};
}"""


def classify(geometry):
    texts, canvas = geometry['texts'], geometry['canvas']
    outside, overlaps, clipped = [], [], []
    for text in texts:
        if (text['left'] < canvas['left'] - .5 or text['top'] < canvas['top'] - .5
                or text['right'] > canvas['right'] + .5
                or text['bottom'] > canvas['bottom'] + .5):
            outside.append(text['index'])
        if text['clips']:
            clipped.append(text['index'])
    # ponytail: quadratic scan suits figure labels; use a spatial index if very large SVGs need it.
    for i, a in enumerate(texts):
        for b in texts[i + 1:]:
            if (min(a['right'], b['right']) - max(a['left'], b['left']) > .5
                    and min(a['bottom'], b['bottom']) - max(a['top'], b['top']) > .5):
                overlaps.append([a['index'], b['index']])
    result = ('not_auditable' if not texts else 'fix_required' if outside
              else 'review_required' if overlaps or clipped else 'pass')
    return {'auto_result': result, 'checks': {'text_outside_canvas': outside,
            'text_overlap_candidates': overlaps, 'text_clip_paths_review': clipped}}


def audit(browser, path, preview=False):
    raw = path.read_bytes()
    report = {'svg': str(path.resolve()), 'sha256': hashlib.sha256(raw).hexdigest(),
              'visual_review': 'pending'}
    context = None
    try:
        root = ET.fromstring(raw)
        if root.tag != '{http://www.w3.org/2000/svg}svg':
            raise ValueError('Expected a namespaced SVG root')
        for element in root.iter():
            if element.tag.rsplit('}', 1)[-1] in {'script', 'foreignObject'}:
                raise ValueError('Active SVG content is not supported')
            for key, value in element.attrib.items():
                if key.rsplit('}', 1)[-1] == 'href' and not value.startswith(('#', 'data:')):
                    raise ValueError('External SVG references are not supported')
            css = ' '.join(element.attrib.values()) + (element.text or '')
            if '@import' in css or any(not value.strip(" \"'").startswith(('#', 'data:'))
                                      for value in re.findall(r'url\((.*?)\)', css, re.I)):
                raise ValueError('External CSS resources are not supported')
        context = browser.new_context(java_script_enabled=False, viewport={'width': 1600, 'height': 1200})
        page = context.new_page()
        url = 'https://svg-audit.invalid/figure.svg'
        blocked = []

        def route(request):
            if request.request.url == url and request.request.is_navigation_request():
                request.fulfill(body=raw, content_type='image/svg+xml', headers={
                    'Content-Security-Policy': "default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:; sandbox"})
            else:
                blocked.append(request.request.url)
                request.abort()

        page.route('**/*', route)
        page.goto(url, wait_until='load')
        page.evaluate('() => document.fonts.ready')
        geometry = page.evaluate(GEOMETRY)
        report.update(geometry)
        report.update(classify(geometry))
        report['blocked_resources'] = blocked
        if blocked:
            report['auto_result'] = 'not_auditable'
            report['error'] = 'External resources blocked; SVG is not self-contained'
        if preview:
            report['preview_png_base64'] = base64.b64encode(
                page.locator('svg').first.screenshot(type='png', animations='disabled')).decode('ascii')
    except Exception as exc:
        report.update(auto_result='not_auditable', error=str(exc))
    finally:
        if context:
            context.close()
    return report


def self_test(browser):
    assert validate_report(PROJECT / 'analysis/project_maintenance/reports/unused-svg-self-test.json', [])
    for path in [PROJECT.parent / 'Ge/1/run.log', PROJECT / 'AGENTS.md', PROJECT / 'analysis/scripts/check_layout.py']:
        try:
            validate_report(path, [])
        except (ValueError, FileExistsError):
            pass
        else:
            raise AssertionError('Unsafe report accepted: ' + str(path))
    cases = {
        'clear': ('<text x="10" y="30">clear</text>', 'pass'),
        'overlap': ('<text x="10" y="30">first</text><text x="10" y="30">second</text>', 'review_required'),
        'edge': ('<text x="190" y="30">clipped</text>', 'fix_required'),
        'outline': ('<path d="M10 10L20 20"/>', 'not_auditable'),
    }
    results = []
    with tempfile.TemporaryDirectory(prefix='svg-qa-') as directory:
        for name, (content, expected) in cases.items():
            path = Path(directory) / (name + '.svg')
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="80" viewBox="0 0 200 80">' + content + '</svg>')
            report = audit(browser, path)
            assert report['auto_result'] == expected, report
            results.append({'case': name, 'expected': expected, 'actual': report['auto_result']})
    return {'self_test': 'pass', 'cases': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('svg', nargs='*', type=Path)
    parser.add_argument('--json-out', type=Path)
    parser.add_argument('--preview-base64', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if not args.svg and not args.self_test:
        parser.error('provide SVG paths or --self-test')
    if args.json_out:
        args.json_out = validate_report(args.json_out, args.svg)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                output = self_test(browser) if args.self_test else {
                    'reports': [audit(browser, path, args.preview_base64) for path in args.svg]}
            finally:
                browser.close()
    except Exception as exc:
        output = {'auto_result': 'not_auditable', 'visual_review': 'pending', 'error': str(exc)}
    if args.json_out:
        saved = json.loads(json.dumps(output))
        for report in saved.get('reports', []):
            report.pop('preview_png_base64', None)
        with args.json_out.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(saved, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(output, ensure_ascii=False))
    results = [report['auto_result'] for report in output.get('reports', [])]
    if output.get('auto_result') == 'not_auditable' or 'not_auditable' in results:
        return 2
    return 1 if any(result != 'pass' for result in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
