"""Deterministic cost and bedroom checks; no provider or persistence dependencies."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

def money(value):
    return str(Decimal(str(value)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


class Conflict(ValueError):
    pass


def evaluate(offer, preferences, source, today=None):
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
    if preferences.get('individual_contract'):
        checks['contract'] = 'fits' if offer.get('contract') == 'individual' else 'conflict' if offer.get('contract') == 'unit' else 'unknown'
        if checks['contract'] == 'conflict': conflicts.append('This is a whole-unit lease; you requested an individual contract.')
        if checks['contract'] == 'unknown': unknown.append('Individual-contract availability needs confirmation.')
    budget = Decimal(str(preferences['budget']))
    # Billing frequency is retained. An installment is never relabeled as a calendar month.
    checks['budget'] = 'unknown'
    if per_person is None or offer.get('period') == 'unknown': unknown.append('A comparable recurring price is not documented.')
    elif per_person > budget:
        checks['budget'] = 'conflict'; conflicts.append('The known recurring amount alone exceeds your payment budget.')
    elif not stale and source.get('review_status') == 'reviewed' and not offer.get('unknowns') and not offer.get('conflicts'):
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
        total = per_person * offer['installments']; total_label = 'Base payments over documented term; extras excluded'
    else: total_label = 'Term commitment not fully documented'
    status = 'conflict' if conflicts else 'review' if unknown or any(v == 'unknown' for v in checks.values()) else 'fits'
    return dict(offer_id=offer['id'], property_id=offer['property_id'], status=status, checks=checks,
                per_person=money(per_person) if per_person is not None else None, period=offer.get('period', 'unknown'),
                term_total=money(total) if total is not None else None, total_label=total_label, room=room,
                stale=stale, scenario=offer.get('basis') == 'unit', reasons=reasons,
                unknowns=list(dict.fromkeys(unknown)), conflicts=list(dict.fromkeys(conflicts)))


