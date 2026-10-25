"""Deterministic cost and bedroom checks; no provider or persistence dependencies."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

def money(value):
    return str(Decimal(str(value)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


class Conflict(ValueError):
    pass


RECURRING_TIMING = {'installment': 'PER_INSTALLMENT', 'monthly': 'PER_CALENDAR_MONTH'}
UPFRONT_TIMING = ('AT_APPLICATION', 'AT_MOVE_IN')
UNRESOLVED_UTILITY = ('EXCLUDED_VARIABLE_USAGE', 'PROVIDER_DEPENDENT', 'UNKNOWN')


def _span(fee):
    low, high = fee.get('amount_min'), fee.get('amount_max')
    if low is None and high is None: return None
    low = Decimal(low if low is not None else high); high = Decimal(high if high is not None else low)
    return low, high


def _scale(fee, occupants, leaseholders):
    """Household amount for one fee occurrence, or None when its charging basis can't be applied."""
    span = _span(fee)
    if span is None: return None
    basis = fee.get('scaling_basis')
    if basis == 'PER_UNIT': factor = 1
    elif basis in ('PER_BED_INSTALLMENT', 'PER_APPLICANT'): factor = occupants
    elif basis == 'PER_PRIMARY_LEASEHOLDER' and leaseholders: factor = leaseholders
    else: return None
    return span[0] * factor, span[1] * factor


def _bucket():
    return {'household_min': Decimal(0), 'household_max': Decimal(0), 'items': []}


def _close(bucket, occupants):
    return {'household_min': money(bucket['household_min']), 'household_max': money(bucket['household_max']),
            'per_person_min': money(bucket['household_min'] / occupants), 'per_person_max': money(bucket['household_max'] / occupants),
            'items': bucket['items']}


def fee_breakdown(offer, preferences, sources=None):
    """Five-bucket fee arithmetic over structured offer fees.

    Fees from reviewed sources and from the pricing research audit are both counted; each counted
    item records its evidence level, and research-only, conflicting or unconfirmed-inclusion fees
    produce notes. Only a required recurring fee with no published amount blocks a budget verdict.
    """
    sources = sources or {}
    occupants = preferences.get('household_size', 1)
    leaseholders = occupants if offer.get('contract') == 'individual' else 1
    recurring_timing = RECURRING_TIMING.get(offer.get('period'))
    recurring_household = Decimal(0)
    buckets = {k: _bucket() for k in ('one_time_nonrefundable', 'refundable_deposits', 'credited_prepayments', 'upfront_cash')}
    recurring, per_term, listed, included, unknown, notes = [], [], [], [], [], []
    research_counted = []
    for fee in offer.get('fees', []):
        statuses = [sources.get(key, {}).get('review_status') for key in (fee.get('source_id'), fee.get('basis_source_id')) if key]
        evidence = ('reviewed' if statuses and all(x == 'reviewed' for x in statuses)
                    else 'research' if 'research_observation' in statuses or not statuses else 'live')
        kind = fee.get('classification')
        amount = _scale(fee, occupants, leaseholders)
        item = {'id': fee['id'], 'label': fee['label'], 'classification': kind, 'scaling_basis': fee.get('scaling_basis'),
                'amount_min': fee.get('amount_min'), 'amount_max': fee.get('amount_max'), 'source_id': fee.get('source_id'),
                'evidence': evidence, 'included_in_totals': False}
        if fee.get('status') == 'conflicting_sources':
            notes.append(f"{fee['label']}: sources disagree. {fee.get('note', 'Confirm with the operator.')}")
        if kind in ('OPTIONAL_ADDON', 'CONDITIONAL_SITUATIONAL'):
            listed.append(item); continue
        if fee.get('included_in_advertised_total') is True:
            included.append(item); continue
        if amount is None:
            listed.append(item)
            if kind == 'MANDATORY_RECURRING': unknown.append(f"{fee['label']}: required, but its amount is not published.")
            else: notes.append(f"{fee['label']}: amount not published; ask the operator.")
            continue
        if kind == 'MANDATORY_RECURRING' and fee.get('included_in_advertised_total') is None:
            notes.append(f"{fee['label']} is counted as extra; it may already be in the listed price.")
        if evidence == 'research': research_counted.append(fee['label'])
        if kind == 'MANDATORY_RECURRING':
            if fee.get('timing_event') == 'PER_TERM':
                per_term.append({**item, 'included_in_totals': True, 'household_min': money(amount[0]), 'household_max': money(amount[1])}); continue
            if fee.get('timing_event') != recurring_timing or amount[0] != amount[1]:
                listed.append(item); notes.append(f"{fee['label']} is billed on a different schedule than the rent; listed but not added.")
                continue
            recurring_household += amount[0]
            recurring.append({**item, 'included_in_totals': True, 'household': money(amount[0]), 'per_person': money(amount[0] / occupants)})
            continue
        target = {'MANDATORY_ONE_TIME': 'one_time_nonrefundable', 'REFUNDABLE_DEPOSIT': 'refundable_deposits',
                  'CREDITED_PREPAYMENT': 'credited_prepayments'}.get(kind)
        if not target:
            listed.append(item); notes.append(f"{fee['label']}: charge type is not documented."); continue
        b = buckets[target]
        b['household_min'] += amount[0]; b['household_max'] += amount[1]
        b['items'].append({**item, 'included_in_totals': True, 'household_min': money(amount[0]), 'household_max': money(amount[1])})
        # A credited prepayment is paid early and offsets another charge; it is never extra cash.
        if target != 'credited_prepayments' and fee.get('timing_event') in UPFRONT_TIMING:
            u = buckets['upfront_cash']; u['household_min'] += amount[0]; u['household_max'] += amount[1]
            u['items'].append(fee['id'])
    if research_counted:
        notes.append('Counted from the Oct 24, 2026 pricing research (not yet operator-verified): ' + ', '.join(dict.fromkeys(research_counted)) + '.')
    utilities = offer.get('utility_matrix', {})
    utility_source = offer.get('utility_source_id')
    if utilities and sources.get(utility_source, {}).get('review_status') != 'reviewed':
        notes.append('Utility inclusions come from the pricing research and are not yet operator-verified.')
    notes.extend(f"{name.replace('_', ' ').capitalize()}: whether it is included is not confirmed." for name, state in utilities.items() if state == 'UNKNOWN')
    return {
        'recurring_fees_per_person': money(recurring_household / occupants), 'recurring_fees': recurring,
        'per_term_fees': per_term, 'included_fees': included, 'listed_not_counted': listed,
        **{k: _close(v, occupants) for k, v in buckets.items()},
        'unresolved_cost_categories': sorted(k for k, v in utilities.items() if v in UNRESOLVED_UTILITY),
        'utility_matrix': utilities, 'utility_source_id': utility_source,
        'unknowns': list(dict.fromkeys(unknown)), 'notes': list(dict.fromkeys(notes)),
    }


def effective_terms(offer):
    """Price, basis and period to compare. Range-only offers use their advertised starting price."""
    rng = offer.get('advertised_range')
    if offer.get('amount') is None and rng:
        return dict(amount=Decimal(rng['minimum']), amount_max=Decimal(rng['maximum']), from_range=True,
                    basis='unit' if rng.get('basis') == 'whole_unit' else 'person',
                    period='monthly' if rng.get('period') == 'calendar_month' else 'installment')
    amount = Decimal(offer['amount']) if offer.get('amount') is not None else None
    return dict(amount=amount, amount_max=None, from_range=False, basis=offer.get('basis'), period=offer.get('period'))


def evaluate(offer, preferences, source, today=None, sources=None):
    """Three-state evaluation. Conflicts and missing prices block; operator confirmations are notes."""
    today = today or date.today()
    sources = sources if sources is not None else {source.get('id'): source}
    # blocking_unknowns are offer-level gaps that keep the result at insufficient evidence (e.g. an unverified price source).
    unknown, notes = list(offer.get('blocking_unknowns', [])), list(offer.get('unknowns', []))
    conflicts = list(offer.get('conflicts', []))
    reasons = []
    checks = {}
    occupants = preferences.get('household_size', 1)
    bedrooms = offer.get('bedrooms')
    terms = effective_terms(offer)
    amount, basis = terms['amount'], terms['basis']
    priced = {**offer, 'basis': basis, 'period': terms['period']}
    # A new fee page cannot refresh an old rent quote.
    price_source = sources.get(offer.get('advertised_range', {}).get('source_id'), source) if terms['from_range'] else source
    latest = price_source.get('reviewed_at') or price_source.get('checked_at')
    stale = not latest or (today - date.fromisoformat(latest[:10])).days > 7
    if stale: unknown.append('Price sources are more than seven days old; refresh and review them.')
    if source.get('review_status') not in ('reviewed', 'live_observation', 'research_observation'): unknown.append('Source changed or awaits review.')
    if terms['from_range']:
        notes.append(f"Compared at the advertised starting price; this layout runs from ${amount:,.0f} to ${terms['amount_max']:,.0f}. Ask for a quote on a specific unit.")
    if basis == 'unit':
        per_person = amount / occupants if amount is not None else None
        reasons.append(f'Cost-sharing scenario: the whole-unit price divided by {occupants}. Each resident may remain responsible for the full lease.')
        room = 'private' if bedrooms and occupants <= bedrooms else 'shared' if bedrooms else 'unknown'
        if bedrooms and occupants > bedrooms:
            notes.append('Permission for this occupancy and bedroom sharing is not confirmed.')
        if preferences.get('room') == 'private' and room == 'shared':
            checks['room'] = 'conflict'; conflicts.append('There are fewer bedrooms than people in your household.')
        else: checks['room'] = 'unknown' if room == 'unknown' else 'fits'
    elif basis == 'person':
        per_person = amount; room = offer.get('room', 'unknown')
        checks['room'] = 'unknown' if room == 'unknown' else 'conflict' if preferences.get('room') == 'private' and room != 'private' else 'fits'
        if checks['room'] == 'conflict': conflicts.append('This offer does not document a private bedroom.')
        if occupants > 1: notes.append('Ask whether rooms in the same unit can be reserved together for your household.')
    else:
        per_person = None; room = 'unknown'; checks['room'] = 'unknown'
    if checks['room'] == 'unknown': notes.append('Confirm the bedroom arrangement with the operator.')
    fees = fee_breakdown(priced, preferences, sources)
    unknown.extend(fees['unknowns']); notes.extend(fees['notes'])
    recurring = per_person + Decimal(fees['recurring_fees_per_person']) if per_person is not None else None
    if preferences.get('individual_contract'):
        checks['contract'] = 'fits' if offer.get('contract') == 'individual' else 'conflict' if offer.get('contract') == 'unit' else 'unknown'
        if checks['contract'] == 'conflict': conflicts.append('This is a whole-unit lease; you requested an individual contract.')
        if checks['contract'] == 'unknown': notes.append('Confirm an individual contract is available.')
    budget = Decimal(str(preferences['budget']))
    checks['budget'] = 'unknown'
    if per_person is None or terms['period'] in (None, 'unknown'): unknown.append('No comparable price is documented.')
    elif recurring > budget:
        checks['budget'] = 'conflict'
        conflicts.append('Even the advertised starting price is over your budget.' if terms['from_range'] else 'The known recurring amount alone exceeds your payment budget.')
    elif not fees['unknowns'] and not stale:
        checks['budget'] = 'fits'
        if terms['from_range']:
            high = (terms['amount_max'] / occupants if basis == 'unit' else terms['amount_max']) + Decimal(fees['recurring_fees_per_person'])
            if high > budget: notes.append(f'Higher-priced units in this layout (up to ${high:,.2f} per person) would exceed your budget.')
    if fees['unresolved_cost_categories']:
        notes.append('Not included in the total: ' + ', '.join(x.replace('_', ' ') for x in fees['unresolved_cost_categories']) + '.')
    start, end = offer.get('start'), offer.get('end')
    if not start or not end:
        checks['dates'] = 'unknown'; notes.append('Confirm exact lease start and end dates with the operator.')
    elif start > preferences['start'] or end < preferences['end']:
        checks['dates'] = 'conflict'; conflicts.append('Published lease dates do not cover your intended stay.')
    else: checks['dates'] = 'fits'
    total = None
    if offer.get('annual_total') is not None:
        total = Decimal(offer['annual_total']) / (occupants if basis == 'unit' else 1)
        total_label = 'Published term total (scope shown in source)'
    elif not terms['from_range'] and amount is not None and offer.get('installments') and per_person is not None:
        total = recurring * offer['installments'] + sum(Decimal(f['household_min']) / occupants for f in fees['per_term_fees'])
        total_label = ('Payments plus known recurring fees over the documented installments; one-time charges and usage-based utilities excluded'
                       if fees['recurring_fees'] or fees['per_term_fees'] else 'Payments over the documented installments; extras excluded')
    else: total_label = 'Term commitment not fully documented'
    status = 'conflict' if conflicts else 'review' if unknown else 'fits'
    return dict(offer_id=offer['id'], property_id=offer['property_id'], status=status, checks=checks,
                per_person=money(per_person) if per_person is not None else None,
                recurring_per_person=money(recurring) if recurring is not None else None, fees=fees,
                price_confidence_tier=offer.get('price_confidence_tier'), period=terms['period'] or 'unknown',
                term_total=money(total) if total is not None else None, total_label=total_label, room=room,
                stale=stale, scenario=basis == 'unit', reasons=reasons, from_range=terms['from_range'],
                unknowns=list(dict.fromkeys(unknown)), conflicts=list(dict.fromkeys(conflicts)), notes=list(dict.fromkeys(notes)))
