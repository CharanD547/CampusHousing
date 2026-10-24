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

    Only fees whose source has been reviewed against stored page text are counted. Research
    observations are listed with included_in_totals=False and reported as unknowns, never imputed.
    """
    sources = sources or {}
    occupants = preferences.get('household_size', 1)
    leaseholders = occupants if offer.get('contract') == 'individual' else 1 if offer.get('contract') == 'unit' else None
    recurring_timing = RECURRING_TIMING.get(offer.get('period'))
    recurring_household = Decimal(0)
    buckets = {k: _bucket() for k in ('one_time_nonrefundable', 'refundable_deposits', 'credited_prepayments', 'upfront_cash')}
    recurring, per_term, listed, included, unknown = [], [], [], [], []
    for fee in offer.get('fees', []):
        # Every source a fee depends on (amount and charging basis) must be reviewed before it counts.
        reviewed = all(sources.get(key, {}).get('review_status') == 'reviewed'
                       for key in (fee.get('source_id'), fee.get('basis_source_id')) if key is not None) and fee.get('source_id') is not None
        kind = fee.get('classification')
        amount = _scale(fee, occupants, leaseholders)
        item = {'id': fee['id'], 'label': fee['label'], 'classification': kind, 'scaling_basis': fee.get('scaling_basis'),
                'amount_min': fee.get('amount_min'), 'amount_max': fee.get('amount_max'), 'source_id': fee.get('source_id'),
                'included_in_totals': False}
        if fee.get('status') == 'conflicting_sources':
            unknown.append(f"{fee['label']}: sources disagree; {fee.get('note', 'confirm with the operator')}")
        if kind in ('OPTIONAL_ADDON', 'CONDITIONAL_SITUATIONAL'):
            listed.append(item); continue
        if not reviewed:
            listed.append(item); unknown.append(f"{fee['label']} comes from a research observation that has not been reviewed against stored source text; it is listed but not counted.")
            continue
        if fee.get('included_in_advertised_total') is True:
            included.append(item); continue
        if fee.get('included_in_advertised_total') is None and kind == 'MANDATORY_RECURRING':
            listed.append(item); unknown.append(f"Not confirmed whether {fee['label']} is already included in the listed price; it is not added.")
            continue
        if amount is None:
            listed.append(item); unknown.append(f"{fee['label']}: amount or charging basis is not documented.")
            continue
        if kind == 'MANDATORY_RECURRING':
            if fee.get('timing_event') == 'PER_TERM':
                per_term.append({**item, 'included_in_totals': True, 'household_min': money(amount[0]), 'household_max': money(amount[1])}); continue
            if fee.get('timing_event') != recurring_timing or amount[0] != amount[1]:
                listed.append(item); unknown.append(f"{fee['label']} is billed on a different schedule than the price or varies; it is not added to the recurring subtotal.")
                continue
            recurring_household += amount[0]
            recurring.append({**item, 'included_in_totals': True, 'household': money(amount[0]), 'per_person': money(amount[0] / occupants)})
            continue
        target = {'MANDATORY_ONE_TIME': 'one_time_nonrefundable', 'REFUNDABLE_DEPOSIT': 'refundable_deposits',
                  'CREDITED_PREPAYMENT': 'credited_prepayments'}.get(kind)
        if not target:
            listed.append(item); unknown.append(f"{fee['label']}: charge type is not documented."); continue
        b = buckets[target]
        b['household_min'] += amount[0]; b['household_max'] += amount[1]
        b['items'].append({**item, 'included_in_totals': True, 'household_min': money(amount[0]), 'household_max': money(amount[1])})
        # A credited prepayment is paid early and offsets another charge; it is never extra cash.
        if target != 'credited_prepayments' and fee.get('timing_event') in UPFRONT_TIMING:
            u = buckets['upfront_cash']; u['household_min'] += amount[0]; u['household_max'] += amount[1]
            u['items'].append(fee['id'])
    utilities = offer.get('utility_matrix', {})
    utility_source = offer.get('utility_source_id')
    if utilities and sources.get(utility_source, {}).get('review_status') != 'reviewed':
        unknown.append('Utility inclusions come from a research observation that has not been reviewed against stored source text.')
    return {
        'recurring_fees_per_person': money(recurring_household / occupants), 'recurring_fees': recurring,
        'per_term_fees': per_term, 'included_fees': included, 'listed_not_counted': listed,
        **{k: _close(v, occupants) for k, v in buckets.items()},
        'unresolved_cost_categories': sorted(k for k, v in utilities.items() if v in UNRESOLVED_UTILITY),
        'utility_matrix': utilities, 'utility_source_id': utility_source, 'unknowns': list(dict.fromkeys(unknown)),
    }


def evaluate(offer, preferences, source, today=None, sources=None):
    """Conservative three-state evaluation; an incomplete subtotal is not a budget pass."""
    today = today or date.today()
    unknown = list(offer.get('unknowns', []))
    conflicts = list(offer.get('conflicts', []))
    reasons = []
    checks = {}
    occupants = preferences.get('household_size', 1)
    bedrooms = offer.get('bedrooms')
    amount = Decimal(offer['amount']) if offer.get('amount') is not None else None
    stale = not source.get('checked_at') or (today - date.fromisoformat(source['checked_at'][:10])).days > 7
    if stale: unknown.append('Price source is more than seven days old; refresh and review it.')
    if source.get('review_status') != 'reviewed': unknown.append('Source changed or awaits review.')
    if offer.get('basis') == 'unit':
        per_person = amount / occupants if amount is not None else None
        reasons.append(f'Cost-sharing scenario: the whole-unit price divided by {occupants}. Each resident may remain responsible for the full lease.')
        room = 'private' if bedrooms and occupants <= bedrooms else 'shared' if bedrooms else 'unknown'
        if bedrooms and occupants > bedrooms:
            unknown.append('Permission for this occupancy and bedroom sharing is not confirmed.')
        if preferences.get('room') == 'private' and room == 'shared':
            checks['room'] = 'conflict'; conflicts.append('There are fewer bedrooms than people in your household.')
        else: checks['room'] = 'unknown' if room == 'unknown' else 'fits'
    elif offer.get('basis') == 'person':
        per_person = amount; room = offer.get('room', 'unknown')
        checks['room'] = 'unknown' if room == 'unknown' else 'conflict' if preferences.get('room') == 'private' and room != 'private' else 'fits'
        if checks['room'] == 'conflict': conflicts.append('This offer does not document a private bedroom.')
        if occupants > 1: unknown.append('Availability of rooms together for your household is not confirmed.')
    else:
        per_person = None; room = 'unknown'; checks['room'] = 'unknown'
    if checks['room'] == 'unknown': unknown.append('Bedroom privacy or occupancy basis needs confirmation.')
    fees = fee_breakdown(offer, preferences, sources if sources is not None else {source.get('id'): source})
    unknown.extend(fees['unknowns'])
    unknown.extend(f'{name.capitalize()}: whether it is included is not confirmed.' for name, state in fees['utility_matrix'].items() if state == 'UNKNOWN')
    recurring = per_person + Decimal(fees['recurring_fees_per_person']) if per_person is not None else None
    if preferences.get('individual_contract'):
        checks['contract'] = 'fits' if offer.get('contract') == 'individual' else 'conflict' if offer.get('contract') == 'unit' else 'unknown'
        if checks['contract'] == 'conflict': conflicts.append('This is a whole-unit lease; you requested an individual contract.')
        if checks['contract'] == 'unknown': unknown.append('Individual-contract availability needs confirmation.')
    budget = Decimal(str(preferences['budget']))
    # Billing frequency is retained. An installment is never relabeled as a calendar month.
    checks['budget'] = 'unknown'
    if per_person is None or offer.get('period') == 'unknown': unknown.append('A comparable recurring price is not documented.')
    elif recurring > budget:
        checks['budget'] = 'conflict'; conflicts.append('The known recurring amount alone exceeds your payment budget.')
    elif not stale and source.get('review_status') == 'reviewed' and not offer.get('unknowns') and not offer.get('conflicts') and not fees['unknowns']:
        checks['budget'] = 'fits'
    else: unknown.append('Known subtotal is within budget; missing costs prevent a full budget match.')
    start, end = offer.get('start'), offer.get('end')
    if not start or not end:
        checks['dates'] = 'unknown'; unknown.append('Exact lease dates need confirmation.')
    elif start > preferences['start'] or end < preferences['end']:
        checks['dates'] = 'conflict'; conflicts.append('Published lease dates do not cover your intended stay.')
    else: checks['dates'] = 'fits'
    total = None
    if offer.get('annual_total') is not None:
        total = Decimal(offer['annual_total']) / (occupants if offer.get('basis') == 'unit' else 1)
        total_label = 'Published term total (scope shown in source)'
    elif amount is not None and offer.get('installments') and start and end and per_person is not None:
        total = recurring * offer['installments'] + sum(Decimal(f['household_min']) / occupants for f in fees['per_term_fees'])
        total_label = ('Base payments plus reviewed recurring fees over documented term; one-time charges and usage-based utilities excluded'
                       if fees['recurring_fees'] or fees['per_term_fees'] else 'Base payments over documented term; extras excluded')
    else: total_label = 'Term commitment not fully documented'
    status = 'conflict' if conflicts else 'review' if unknown or any(v == 'unknown' for v in checks.values()) else 'fits'
    return dict(offer_id=offer['id'], property_id=offer['property_id'], status=status, checks=checks,
                per_person=money(per_person) if per_person is not None else None,
                recurring_per_person=money(recurring) if recurring is not None else None, fees=fees,
                price_confidence_tier=offer.get('price_confidence_tier'), period=offer.get('period', 'unknown'),
                term_total=money(total) if total is not None else None, total_label=total_label, room=room,
                stale=stale, scenario=offer.get('basis') == 'unit', reasons=reasons,
                unknowns=list(dict.fromkeys(unknown)), conflicts=list(dict.fromkeys(conflicts)))


