"""Guide communities stay browsable while separately sourced evidence is added.

Each guide place becomes one offer per priced floor plan or listing: operator-observed rows when
research found them, otherwise rows parsed from the housing guide's own price text. Every amount
traces to one of those sources; billing basis is inferred only from explicit "/bed" or "/unit"
wording. These offers stay insufficient evidence until fees, lease terms and basis are confirmed.
"""
from copy import deepcopy
import json
import re
from roomwise.config import ROOT

NUMBER = r'\$?\s?(\d{1,3}(?:,\d{3})+|\d{3,5})(?:\.\d+)?'
RANGE = re.compile(NUMBER + r'(?:\s*[–-]\s*' + NUMBER + r')?')


def _load(name):
    path = ROOT / 'data' / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def _slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:48]


def _basis(text):
    text = text.lower()
    if re.search(r'/\s*(bed|person|room)|per\s+(bed|person|room)|room listing', text): return 'person'
    if re.search(r'/\s*unit|whole[- ]unit|apartment ·|per unit', text): return 'unit'
    return 'unknown'


def _bedrooms(label):
    if re.search(r'studio|\bS[1-4]\b', label, re.I): return 0
    m = re.search(r'(\d)\s*(?:BR|bd|bed)|(\d)\s*x\s*\d', label, re.I)
    return int(m.group(1) or m.group(2)) if m else None


def guide_rows(summary):
    """Price rows from guide text such as "1BR: 1,470– 1,556; 2BR: 1,845– 1,916"."""
    rows = []
    plain = re.sub(r'\([^)]*\)', '', summary)              # parenthetical figures are alternates (sublets, other units)
    # A summary-wide basis applies only to text with a single price; otherwise each price must state its own.
    overall = _basis(plain) if ';' not in summary and len(RANGE.findall(plain)) == 1 else 'unknown'
    for segment in summary.split(';'):
        labelled = re.findall(r'\$\s?([\d,]{3,})\s*\(([^)]+)\)', segment)
        if len(labelled) > 1:                                # "$1,350 (Wharton 2BR), $1,800 (703 Clay 2BR)"
            for amount, label in labelled:
                value = float(amount.replace(',', ''))
                if value >= 300:
                    rows.append(dict(label=label.strip(), bedrooms=_bedrooms(label), minimum=value, maximum=value,
                                     basis=overall, quote=f'${amount} ({label})'))
            continue
        main = re.sub(r'\([^)]*\)', '', segment)
        if ':' in main: label, rest = main.split(':', 1)
        else:
            match = RANGE.search(main)
            label, rest = (main[:match.start()], main[match.start():]) if match else ('', main)
            label = re.sub(r'\b(starts?|starting|from|at)\b', '', label, flags=re.I)
        match = RANGE.search(rest)
        if not match: continue
        low = float(match.group(1).replace(',', ''))
        high = float((match.group(2) or match.group(1)).replace(',', ''))
        if low < 300 or high < low: continue                 # stray figures such as fee notes
        label = re.sub(r'\s+', ' ', label).strip(' ,–-') or 'Guide price'
        # The basis belongs to the price it follows; a segment-wide word counts only when the segment has one price.
        basis = _basis(re.split(r'[$\d]', rest[match.end():match.end() + 14])[0])   # words up to the next price
        if basis == 'unknown' and len(RANGE.findall(main)) == 1: basis = _basis(main)
        rows.append(dict(label=label, bedrooms=_bedrooms(label), minimum=low, maximum=high,
                         basis=basis if basis != 'unknown' else overall, quote=segment.strip()))
    return rows


def guide_properties(guide, enrichment=None, geocodes=None):
    if enrichment is None: enrichment = _load('housing-guide-evidence.json')
    if geocodes is None: geocodes = _load('housing-guide-geocodes.json')
    points = geocodes.get('places', {})
    result = []
    for entry in guide['communities']:
        if entry.get('catalog_property_id'): continue
        key = entry['id']; source_id = 'guide-' + key
        source = dict(id=source_id, type='guide_reference', title='Housing guide reference: ' + entry['name'],
            url=entry['source_urls'][0] if entry['source_urls'] else None, checked_at='2026-10-24',
            review_status='research_observation', refresh_policy='manual_only', reviewed_at=None, sha256=guide['document_sha256'],
            excerpt=entry['guide_price_summary'], review_scope='Imported from the supplied housing guide. Reference prices and layouts have not been verified against a current operator quote.')
        update = enrichment.get('properties', {}).get(key, {})
        geo = points.get(key) or {}
        point = update.get('coordinates') or ({'lat': geo['lat'], 'lon': geo['lon']} if geo.get('lat') is not None else {})
        basis_label = ('operator_community_point' if update.get('coordinates')
                       else 'geocoded_street_address' if point else 'unverified')
        reference = deepcopy(entry)
        if geo.get('lat') is not None and not update.get('coordinates'): reference['geocode'] = geo
        sources = [source]
        kind = {'operator_observed': 'operator', 'listing_observed': 'listing', 'eligibility_observed': 'operator'}.get(update.get('status'))
        operator = kind and update.get('prices')
        if kind:
            reference['evidence_update'] = update
            sources.append(dict(id='operator-guide-' + key, type=kind,
                title=('Listing evidence: ' if kind == 'listing' else 'Operator evidence: ') + entry['name'],
                url=update['source_url'], checked_at=update['checked_at'], review_status='research_observation',
                refresh_policy='manual_review', reviewed_at=None, sha256=update.get('source_sha256'),
                excerpt=update.get('eligibility') or ('Listing-site asking figures; not an operator quote.' if kind == 'listing'
                        else 'Published floor-plan asking figures and community address; billing basis and fees require confirmation.'),
                review_scope=update['billing_note']))
        # A published eligibility rule (e.g. income-restricted housing) is a hard conflict for every plan.
        eligibility = [update['eligibility']] if update.get('eligibility') else []
        guide_basis = _basis(entry['guide_price_summary'])
        if operator:
            rows = [dict(label=p['label'], bedrooms=p.get('bedrooms'), minimum=p['minimum'], maximum=p['maximum'],
                         basis=_basis(p.get('group_label', '')) if p.get('group_label') else guide_basis,
                         quote=f"{p['label']}: ${p['minimum']:,.0f}" + (f"–${p['maximum']:,.0f}" if p['maximum'] != p['minimum'] else ''))
                    for p in update['prices']]
            tier, row_source = ('LISTING_OBSERVED' if kind == 'listing' else 'OPERATOR_OBSERVED'), 'operator-guide-' + key
        else:
            rows = guide_rows(entry['guide_price_summary'])
            tier, row_source = 'GUIDE_REFERENCE', source_id

        def offer(oid, name, row=None):
            basis = (row or {}).get('basis', 'unknown')
            blocking = []
            if row:
                blocking.append('Price comes from ' + {'OPERATOR_OBSERVED': 'operator-published asking figures',
                                                       'LISTING_OBSERVED': 'a listing site, not an operator quote'}.get(tier, 'the housing guide, not a current operator quote') +
                                '; required fees, lease term and availability are unconfirmed.')
                if basis == 'unknown': blocking.append('Billing basis (per bed or whole unit) is not stated.')
            notes = ([f"{'Billing basis inferred from “/bed” or “/unit” wording' if basis != 'unknown' else 'Billing basis unconfirmed'}; ask the operator."] if row else
                     ['Guide price reference: ' + entry['guide_price_summary'],
                      'Verify the exact floor plan, current rent, billing basis, mandatory fees and availability with the operator.'])
            if row and row['maximum'] != row['minimum']:
                notes.insert(0, f"Published range ${row['minimum']:,.0f}–${row['maximum']:,.0f}; compared at the low end.")
            return dict(id=oid, name=name, bedrooms=(row or {}).get('bedrooms'), bathrooms=None,
                amount=f"{row['minimum']:.0f}" if row else None, basis=basis, period='monthly' if row else 'unknown',
                contract='unknown', room='unknown', installments=None, start=None, end=None,
                term_label='Exact term unverified', annual_total=None, upfront=[], unknowns=notes,
                blocking_unknowns=blocking, conflicts=list(eligibility), property_id=key, source_id=row_source if row else source_id,
                evidence=[dict(field='amount', quote=row['quote'], source_id=row_source)] if row else [],
                fees=[], utility_matrix={}, price_confidence_tier=tier if row else 'GUIDE_REFERENCE',
                source_conflicts=[], operator_questions=[], plan_details={'maximum': f"{row['maximum']:.0f}"} if row else {})

        offers, seen = [], set()
        for row in rows:
            oid = f"guide-{key}-{_slug(row['label'])}"
            while oid in seen: oid += '-2'
            seen.add(oid)
            offers.append(offer(oid, row['label'], row))
        if not offers:
            offers = [offer(source_id, entry['layouts'])]
        result.append(dict(id=key, name=entry['name'], address=update.get('address') or entry['address'],
            lat=point.get('lat'), lon=point.get('lon'), coordinate_basis=basis_label,
            listing_type='area' if entry['zone'] == 'Private rentals and neighborhoods' else 'property',
            guide_reference=reference, sources=sources, offers=offers))
    return result
