"""Recheck every catalog rent source without silently replacing reviewed prices.

Amount mentions are a screening signal, not verification of a plan, billing basis,
lease term, fees or availability. Bounded retrieval respects robots restrictions.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from roomwise.adapters.sources import fetch, TextParser
from roomwise.services.guide_catalog import guide_properties


def amount_present(text, value):
    number = float(value)
    if not number.is_integer():
        variants = [f'{number:,.2f}', f'{number:.2f}']
    else:
        variants = [f'{int(number):,}', str(int(number))]
    return any(re.search(r'(?<![\d,.])\$?\s*' + re.escape(v) + r'(?:\.00)?(?![\d,.])', text) for v in variants)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--browser-dir', type=Path, help='Rendered evidence and manifest captured through the browser UI')
    args = parser.parse_args()
    load = lambda name: json.loads((ROOT / 'data' / name).read_text(encoding='utf-8'))
    properties = load('housing-seed.json')['properties'] + guide_properties(load('housing-guide.json'))
    folder = ROOT / 'var' / 'rent-recheck-20261025'
    folder.mkdir(parents=True, exist_ok=True)
    urls = sorted({s['url'] for p in properties for s in p['sources']
                   if any(o['source_id'] == s['id'] for o in p['offers']) and s.get('url')})

    def retrieve(url):
        try:
            record = fetch({'url': url}, include_html=True)
            parser = TextParser()
            parser.feed(record.pop('html'))
            record['text'] = re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()[:500_000]
            record['sha256'] = hashlib.sha256(record['text'].encode()).hexdigest()
            return url, record
        except Exception as error:
            return url, {'error': str(error)[:300], 'attempted_at': datetime.now(timezone.utc).isoformat()}

    with ThreadPoolExecutor(max_workers=4) as pool:
        records = dict(pool.map(retrieve, urls))
    browser = {}
    if args.browser_dir:
        manifest = json.loads((args.browser_dir / 'manifest.json').read_text(encoding='utf-8'))
        for key, item in manifest.items():
            path = args.browser_dir / (key + '.txt')
            if not path.exists():
                continue
            captured = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if (datetime.now(timezone.utc) - captured).total_seconds() > 86400:
                continue
            browser[key] = {'text': path.read_text(encoding='utf-8'), 'retrieved_at': captured.isoformat(), **item}
    report = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'All catalog properties; amount mentions do not verify billing basis, plan, term, fees or availability.',
              'properties': {}}
    for prop in properties:
        checks = []
        for source in prop['sources']:
            offers = [o for o in prop['offers'] if o['source_id'] == source['id']]
            if not offers:
                continue
            record = records.get(source.get('url'), {'error': 'No current online rent source.'})
            rendered = browser.get(prop['id'])
            if rendered and source.get('url') == rendered['source_url']:
                record = rendered
            amounts = sorted({float(n) for o in offers for n in
                              (o.get('amount'), (o.get('advertised_range') or {}).get('maximum')) if n is not None})
            missing = [n for n in amounts if not amount_present(record.get('text', ''), n)]
            checks.append({'source_id': source['id'], 'source_url': source.get('url'),
                           'status': 'unavailable' if 'error' in record else 'amounts_need_review' if missing else 'browser_amounts_present' if record is rendered else 'amounts_present',
                           'checked_at': record.get('retrieved_at') or record.get('attempted_at'),
                           'source_sha256': record.get('sha256'), 'error': record.get('error'),
                           'verification_url': record.get('verification_url', source.get('url')),
                           'amounts_checked': amounts, 'amounts_not_found': missing,
                           'note': 'Source retrieved; amount mentions alone do not verify the exact plan or rental quote.'})
        report['properties'][prop['id']] = {'name': prop['name'], 'plan_count': len(prop['offers']), 'sources': checks}
    (folder / 'source-snapshots.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    (folder / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if args.apply:
        (ROOT / 'data' / 'rent-source-recheck.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    counts = {}
    for prop in report['properties'].values():
        for check in prop['sources']:
            counts[check['status']] = counts.get(check['status'], 0) + 1
    print(json.dumps({'properties': len(properties), 'sources': len(urls), 'results': counts, 'applied': args.apply}))


if __name__ == '__main__':
    main()
