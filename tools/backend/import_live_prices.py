"""Rebuild catalog offers from data/housing-live-prices.json (one offer per live floor plan).

Property-level fees, utilities, operator questions and source conflicts are carried over from the
existing seed. Idempotent: running it twice produces the same seed.
"""
import json
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
seed_path = ROOT / 'data/housing-seed.json'
seed = json.loads(seed_path.read_text(encoding='utf-8'))
live = json.loads((ROOT / 'data/housing-live-prices.json').read_text(encoding='utf-8'))
# Optional directory of robots-aware fetch() records named <source_id>.json; those sources become reviewed.
fetched = {f.stem: json.loads(f.read_text(encoding='utf-8')) for f in Path(sys.argv[1]).glob('*.json')} if len(sys.argv) > 1 else {}
# Fetched page text is kept apart from the reviewed snapshots that historical price manifests quote.
snapshots_path = ROOT / 'data/housing-live-snapshots.json'
snapshots = json.loads(snapshots_path.read_text(encoding='utf-8')) if snapshots_path.exists() else {}
T = live['retrieved_at']
TIER = {'from': 'ADVERTISED_FROM', 'total_leasing_price': 'PUBLISHED_TOTAL_LEASING_PRICE', 'rate': 'PUBLISHED_ASKING_PRICE', 'base_rent': 'PUBLISHED_BASE_RENT', 'rent': 'PUBLISHED_ASKING_PRICE'}
LIVE_SCOPE = 'Operator page read {date} ({method}). Asking prices only; no unit availability guarantee.'


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


for prop in seed['properties']:
    spec = live['properties'][prop['id']]
    T = spec.get('verified_at',live['retrieved_at'])
    date = datetime.fromisoformat(T.replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date().isoformat()
    term = '2027–28' if spec.get('start') else 'Lease dates unconfirmed'
    template = deepcopy(prop['offers'][0]) if prop['offers'] else {}
    src = spec['source']
    # The source the live prices came from: refreshed when it already exists, added otherwise.
    existing = next((s for s in prop['sources'] if s['id'] == src['id']), None)
    record = fetched.get(src['id'])
    body = dict(id=src['id'], url=src['url'], title=(existing or {}).get('title') or src['id'].replace('-', ' ').title(),
                checked_at=T, excerpt=spec['quote'][:120], applicable_term=term,
                review_status='reviewed' if record else 'live_observation', refresh_policy=(existing or {}).get('refresh_policy', 'manual_only'),
                sha256=record['sha256'] if record else None, reviewed_at=T if record else None,
                review_scope=LIVE_SCOPE.format(date=date,method=src['method']))
    if record:
        # Keep the full captured page private; the checked-in snapshot contains
        # short price locators only, rather than republishing marketing copy.
        selected=' '.join(p.get('verified_quote',spec['quote']) for p in spec['plans'])
        snapshots[src['id']] = dict(url=src['url'], text=selected, sha256=__import__('hashlib').sha256(selected.encode()).hexdigest(), retrieved_at=record['retrieved_at'])
        body['sha256']=snapshots[src['id']]['sha256']
    prop['sources'] = [body if s['id'] == src['id'] else s for s in prop['sources']] + ([] if existing else [body])
    extra = spec.get('also_confirmed_by')
    if extra:
        rec = fetched.get(extra['id'])
        for s in prop['sources']:
            if s['id'] == extra['id']:
                s.update(checked_at=T, excerpt=extra['quote'][:120], review_status='reviewed' if rec else 'live_observation',
                         sha256=rec['sha256'] if rec else s.get('sha256'), reviewed_at=T if rec else None, review_scope=LIVE_SCOPE.format(date=date,method='robots-aware fetch'))
        if rec: snapshots[extra['id']] = dict(url=extra['url'], text=rec['text'], sha256=rec['sha256'], retrieved_at=rec['retrieved_at'])

    shared_fees = [f for f in template.get('fees', []) if not f['id'].startswith(tuple(o['id'] for o in prop['offers']))]
    conflicts = [c for c in template.get('source_conflicts', []) if not (prop['id'] == 'alight' and c['field'] == 'amount')]
    offers = []
    for plan in spec['plans']:
        oid = plan.get('id') or f"{prop['id']}-{slug(plan['name'])}"
        fees = deepcopy(shared_fees)
        if prop['id'] == 'alight':
            yearly = int(plan['annual_total']) - 12 * int(plan['amount'])
            fees.append(dict(id=f'{oid}-mandatory-fees', label='Mandatory fees in the published annual total', classification='MANDATORY_RECURRING',
                             timing_event='PER_TERM', scaling_basis='PER_BED_INSTALLMENT', amount_min=f'{yearly}.00', amount_max=f'{yearly}.00',
                             included_in_advertised_total=False, credits_target_fee_id=None, source_id='alight-plans', status='documented',
                             derivation=f"published annual total ${int(plan['annual_total']):,} minus 12 installments of ${plan['amount']}",
                             note='Not itemized; payment timing is not published.'))
        if plan.get('deposit') and prop['id'] in ('mill', 'terrace'):
            fees = [f for f in fees if f['classification'] != 'REFUNDABLE_DEPOSIT']
            fees.append(dict(id=f'{oid}-deposit', label='Security deposit', classification='REFUNDABLE_DEPOSIT', timing_event='AT_MOVE_IN',
                             scaling_basis='PER_UNIT' if spec['basis'] == 'unit' else 'PER_BED_INSTALLMENT',
                             amount_min=f"{plan['deposit']}.00", amount_max=f"{plan['deposit']}.00", included_in_advertised_total=False,
                             credits_target_fee_id=None, source_id=src['id'], status='documented'))
        if spec['price_type'] == 'total_leasing_price':
            # The operator's "Total Monthly Leasing Price" already carries its required per-installment fees.
            for f in fees:
                if f['classification'] == 'MANDATORY_RECURRING' and f['timing_event'] == 'PER_INSTALLMENT':
                    f.update(included_in_advertised_total=True, note='Treated as included in the operator’s total monthly leasing price.')
        utilities = dict(template.get('utility_matrix', {}))
        if prop['id'] == 'alight':
            utilities['water'] = 'INCLUDED' if 'West' in plan['name'] else 'EXCLUDED_VARIABLE_USAGE'
        notes = [u for u in template.get('unknowns', []) if 'advertised ranges' not in u and 'Advertised “from” price' not in u]
        if spec['price_type'] == 'from':
            notes.insert(0, 'Advertised “from” price for this floor plan; ask for a quote on a specific unit.')
        offers.append(dict(
            id=oid, name=plan['name'], bedrooms=plan['bedrooms'], bathrooms=plan['bathrooms'], amount=plan['amount'],
            basis=spec['basis'], period=spec['period'], contract=spec.get('contract', template.get('contract', 'unknown')),
            room=spec.get('room', 'unknown'), installments=spec.get('installments'), start=spec.get('start'), end=spec.get('end'),
            annual_total=plan.get('annual_total'), term_label=term, advertised_occupants=None,
            upfront=[dict(label='Security deposit', amount=plan['deposit'], refundable=True, basis=spec['basis'])] if plan.get('deposit') else [],
            unknowns=notes, conflicts=[], property_id=prop['id'], source_id=src['id'],
            evidence=[dict(field='amount', quote=plan.get('verified_quote',spec['quote']), source_id=src['id'], reviewed_at=T, method=src['method'])],
            fees=fees, utility_matrix=utilities, utility_source_id=template.get('utility_source_id'),
            price_confidence_tier=TIER[spec['price_type']], operator_questions=template.get('operator_questions', []),
            source_conflicts=conflicts, plan_details={k: plan[k] for k in ('square_feet', 'tiers') if k in plan}))
    prop['offers'] = offers

seed['live_prices'] = T
seed_path.write_text(json.dumps(seed, indent=2, ensure_ascii=False), encoding='utf-8')
snapshots_path.write_text(json.dumps(snapshots, indent=2, ensure_ascii=False), encoding='utf-8')
print('offers:', {p['id']: len(p['offers']) for p in seed['properties']})
