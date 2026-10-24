"""Structured fee arithmetic and the Oct 24, 2026 research port in the seed catalog."""
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
from roomwise.domain.costs import evaluate, fee_breakdown

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 24)
REVIEWED = dict(id='s', checked_at='2026-10-24', review_status='reviewed')
RESEARCH = dict(id='r', checked_at='2026-10-24', review_status='research_observation')
PREFS = dict(budget=1100, household_size=2, room='private', start='2027-08-20', end='2028-07-20')


def seed():
    return json.loads((ROOT / 'data/housing-seed.json').read_text(encoding='utf-8'))


def offer(**fields):
    base = dict(id='o', property_id='p', amount='1500', basis='unit', period='monthly', contract='unit', room='unknown', bedrooms=2,
                installments=12, start='2027-08-01', end='2028-07-31', annual_total=None, unknowns=[], conflicts=[], source_id='s', fees=[])
    return {**base, **fields}


def fee(id, classification, timing, basis, amount, high=None, source='s', included=False, **extra):
    return dict(id=id, label=id, classification=classification, timing_event=timing, scaling_basis=basis,
                amount_min=amount, amount_max=high or amount, included_in_advertised_total=included, source_id=source, **extra)


def test_per_unit_recurring_fees_split_by_household_using_exact_disclosure_sum():
    fees = [fee('internet', 'MANDATORY_RECURRING', 'PER_CALENDAR_MONTH', 'PER_UNIT', '65.00'),
            fee('refuse', 'MANDATORY_RECURRING', 'PER_CALENDAR_MONTH', 'PER_UNIT', '7.00'),
            fee('billing', 'MANDATORY_RECURRING', 'PER_CALENDAR_MONTH', 'PER_UNIT', '1.50')]
    result = evaluate(offer(fees=fees), PREFS, REVIEWED, today=TODAY)
    # $73.50 per unit, not the $74.00 listing sites round to, split across two residents.
    assert result['fees']['recurring_fees_per_person'] == '36.75'
    assert result['recurring_per_person'] == '786.75'
    assert result['term_total'] == '9441.00'


def test_research_observation_fees_are_listed_not_counted():
    fees = [fee('internet', 'MANDATORY_RECURRING', 'PER_CALENDAR_MONTH', 'PER_UNIT', '65.00', source='r')]
    result = evaluate(offer(fees=fees), PREFS, REVIEWED, today=TODAY, sources={'s': REVIEWED, 'r': RESEARCH})
    assert result['recurring_per_person'] == result['per_person'] == '750.00'
    assert result['fees']['listed_not_counted'][0]['included_in_totals'] is False
    assert result['status'] == 'review' and result['checks']['budget'] == 'unknown'
    assert any('research observation' in u for u in result['unknowns'])


def test_unreviewed_charging_basis_blocks_an_otherwise_reviewed_fee():
    fees = [fee('application', 'MANDATORY_ONE_TIME', 'AT_APPLICATION', 'PER_APPLICANT', '35.00', basis_source_id='r')]
    buckets = fee_breakdown(offer(fees=fees), PREFS, {'s': REVIEWED, 'r': RESEARCH})
    assert buckets['one_time_nonrefundable']['household_min'] == '0.00'
    assert buckets['listed_not_counted'][0]['id'] == 'application'


def test_credited_prepayment_is_never_extra_cash_and_deposit_ranges_stay_ranges():
    fees = [fee('application', 'MANDATORY_ONE_TIME', 'AT_APPLICATION', 'PER_APPLICANT', '35.00'),
            fee('admin', 'MANDATORY_ONE_TIME', 'AT_MOVE_IN', 'PER_UNIT', '200.00'),
            fee('move-out', 'MANDATORY_ONE_TIME', 'AT_MOVE_OUT', 'PER_UNIT', '125.00'),
            fee('deposit', 'REFUNDABLE_DEPOSIT', 'AT_MOVE_IN', 'PER_UNIT', '400.00', '1500.00'),
            fee('reservation', 'CREDITED_PREPAYMENT', 'AT_APPLICATION', 'PER_UNIT', '200.00', credits_target_fee_id='deposit')]
    b = fee_breakdown(offer(fees=fees), PREFS, {'s': REVIEWED})
    assert b['one_time_nonrefundable']['household_min'] == '395.00'  # 2 × $35 + $200 + $125 move-out
    assert (b['refundable_deposits']['household_min'], b['refundable_deposits']['household_max']) == ('400.00', '1500.00')
    assert b['credited_prepayments']['household_min'] == '200.00'
    # Upfront cash covers application, admin and deposit; the move-out fee and the credit are excluded.
    assert (b['upfront_cash']['household_min'], b['upfront_cash']['household_max']) == ('670.00', '1770.00')


def test_unconfirmed_and_included_fees_are_not_added():
    fees = [fee('tech', 'MANDATORY_RECURRING', 'PER_INSTALLMENT', 'PER_BED_INSTALLMENT', '40.00', included=None),
            fee('bundled', 'MANDATORY_RECURRING', 'PER_INSTALLMENT', 'PER_BED_INSTALLMENT', '6.00', included=True)]
    result = evaluate(offer(fees=fees, basis='person', period='installment', contract='individual', amount='900'), PREFS, REVIEWED, today=TODAY)
    assert result['recurring_per_person'] == '900.00'
    assert [f['id'] for f in result['fees']['included_fees']] == ['bundled']
    assert any('Not confirmed whether tech' in u for u in result['unknowns'])


def test_recurring_fee_on_a_different_schedule_is_not_mixed_into_the_subtotal():
    fees = [fee('monthly', 'MANDATORY_RECURRING', 'PER_CALENDAR_MONTH', 'PER_BED_INSTALLMENT', '10.00')]
    result = evaluate(offer(fees=fees, basis='person', period='installment', amount='900'), PREFS, REVIEWED, today=TODAY)
    assert result['recurring_per_person'] == '900.00'
    assert any('different schedule' in u for u in result['unknowns'])


def test_leaseholder_fees_scale_with_contract_scope():
    admin = [fee('admin', 'MANDATORY_ONE_TIME', 'AT_MOVE_IN', 'PER_PRIMARY_LEASEHOLDER', '150.00')]
    individual = fee_breakdown(offer(fees=admin, contract='individual'), PREFS, {'s': REVIEWED})
    joint = fee_breakdown(offer(fees=admin, contract='unit'), PREFS, {'s': REVIEWED})
    unknown = fee_breakdown(offer(fees=admin, contract='unknown'), PREFS, {'s': REVIEWED})
    assert individual['one_time_nonrefundable']['household_min'] == '300.00'
    assert joint['one_time_nonrefundable']['household_min'] == '150.00'
    assert unknown['one_time_nonrefundable']['household_min'] == '0.00' and unknown['unknowns']


def test_per_term_fee_reaches_term_total_once():
    term_fee = [fee('annual', 'MANDATORY_RECURRING', 'PER_TERM', 'PER_BED_INSTALLMENT', '155.00')]
    computed = evaluate(offer(fees=term_fee, basis='person', period='installment', amount='835'), PREFS, REVIEWED, today=TODAY)
    published = evaluate(offer(fees=term_fee, basis='person', period='installment', amount='835', annual_total='10175'), PREFS, REVIEWED, today=TODAY)
    assert computed['term_total'] == published['term_total'] == '10175.00'
    assert computed['recurring_per_person'] == '835.00'


def test_conflicting_sources_and_unknown_utilities_stay_visible():
    fees = [fee('deposit', 'REFUNDABLE_DEPOSIT', 'AT_MOVE_IN', 'PER_UNIT', '300.00', '500.00', status='conflicting_sources', note='listing says more')]
    result = evaluate(offer(fees=fees, utility_matrix={'water_sewer': 'UNKNOWN', 'electricity': 'EXCLUDED_VARIABLE_USAGE'}, utility_source_id='s'),
                      PREFS, REVIEWED, today=TODAY)
    assert any('sources disagree' in u for u in result['unknowns'])
    assert any(u.startswith('Water_sewer') for u in result['unknowns'])
    assert result['fees']['unresolved_cost_categories'] == ['electricity', 'water_sewer']


def test_seed_provenance_is_complete_and_research_never_becomes_a_price():
    for prop in seed()['properties']:
        sources = {s['id']: s for s in prop['sources']}
        for source in sources.values():
            if source['review_status'] != 'reviewed':
                assert source['review_status'] == 'research_observation' and source['refresh_policy'] == 'manual_only'
        for o in prop['offers']:
            for f in o.get('fees', []):
                assert f['source_id'] in sources and f.get('basis_source_id', f['source_id']) in sources
                assert f['classification'] in ('MANDATORY_RECURRING', 'MANDATORY_ONE_TIME', 'REFUNDABLE_DEPOSIT', 'CREDITED_PREPAYMENT',
                                                'CONDITIONAL_SITUATIONAL', 'OPTIONAL_ADDON')
            assert o.get('utility_source_id') in sources
            if o.get('advertised_range'):
                # Advertised ranges document the market; they are never converted into an offer amount.
                assert o['amount'] is None and o['price_confidence_tier'] == 'ADVERTISED_RANGE'
                assert sources[o['advertised_range']['source_id']]['review_status'] == 'research_observation'
            for conflict in o.get('source_conflicts', []):
                assert all(v['source_id'] in sources for v in conflict['values'])


def test_seed_reviewed_totals_reconcile_with_source_text():
    props = {p['id']: p for p in seed()['properties']}
    for o in props['alight']['offers']:
        # Published annual total = 12 installments + $155 mandatory fees for every plan.
        assert Decimal(o['annual_total']) == Decimal(o['amount']) * 12 + 155
    portal = {'union-s1': '1684.79', 'union-b2': '1420.79', 'union-c1': '1346.79'}
    for o in props['union']['offers']:
        sources = {s['id']: s for s in props['union']['sources']}
        result = evaluate(o, {**PREFS, 'household_size': 1}, sources[o['source_id']], today=TODAY, sources=sources)
        assert result['recurring_per_person'] == portal[o['id']]
        assert result['term_total'] is None  # 11 vs 12 installments is unresolved


def test_comparison_api_reports_reviewed_fees_in_subtotal(client, request_body):
    request_body['candidate_ids'] = ['union-b2', 'foxridge-2', 'mill-2']
    rows = {r['candidate_id']: r for r in client.post('/api/v1/comparisons', json=request_body).json()['candidate_results']}
    assert rows['union-b2']['known_recurring_subtotal'] == '1420.79'
    assert rows['foxridge-2']['known_recurring_subtotal'] is None
    assert rows['foxridge-2']['cost_breakdown']['fees']['recurring_fees'] == []
    assert rows['mill-2']['cost_breakdown']['fees']['refundable_deposits']['household_min'] == '900.00'
    catalog = {c['id']: c for c in client.get('/api/v1/candidates').json()['candidates']}
    assert catalog['foxridge-2']['offer']['advertised_range']['minimum'] == '1447'
    assert catalog['foxridge-2']['offer']['price']['amount'] is None
