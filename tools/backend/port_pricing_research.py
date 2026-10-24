"""Port the Oct 24, 2026 pricing research audit into data/housing-seed.json.

Idempotent. Research values go into structured fields (fees, utility_matrix, advertised_range,
source_conflicts, operator_questions) under research_observation sources, which the calculator
lists but does not count. Only facts already present in reviewed snapshots change arithmetic:
Union's $6.79 per-installment fee and Alight's published annual totals.
"""
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
seed_path = ROOT / 'data/housing-seed.json'
seed = json.loads(seed_path.read_text(encoding='utf-8'))
props = {p['id']: p for p in seed['properties']}
AUDIT = '2026-10-24T00:00:00+00:00'
SCOPE = ('Oct 24, 2026 pricing research audit ("Empirical Pricing Reconciliation, Lease-Accounting Normalization, and '
         'Review-AI Governance Audit"). Values were transcribed from the audit and not re-verified against stored page '
         'text, so the calculator lists them without counting them until a reviewed manifest promotes the source.')


def research_source(id, url, title, excerpt, term='2027–28 where stated'):
    return dict(id=id, url=url, title=title, checked_at=AUDIT, excerpt=excerpt, applicable_term=term,
                review_status='research_observation', refresh_policy='manual_only', sha256=None, reviewed_at=None,
                review_scope=SCOPE)


def fee(id, label, classification, timing, basis, amount_min, amount_max=None, source_id=None, included=False, **extra):
    out = dict(id=id, label=label, classification=classification, timing_event=timing, scaling_basis=basis,
               amount_min=amount_min, amount_max=amount_max if amount_max is not None else amount_min,
               included_in_advertised_total=included, credits_target_fee_id=None, source_id=source_id, status='documented')
    out.update(extra)
    return out


def plan(name, low, high, sqft):
    return dict(name=name, minimum=low, maximum=high, square_feet=sqft)


def add_sources(pid, sources):
    have = {s['id'] for s in props[pid]['sources']}
    props[pid]['sources'].extend(s for s in sources if s['id'] not in have)


def update(pid, oid, **fields):
    offer = next(o for o in props[pid]['offers'] if o['id'] == oid)
    offer.update(fields)
    return offer


# ---------------------------------------------------------------- Foxridge
add_sources('foxridge', [
    research_source('foxridge-fees', 'https://www.foxridgeliving.com/gridmedia/img/fees.pdf', 'Foxridge fee schedule (PDF)',
                    'Refuse $7, internet $65 and rent billing $1.50 per unit per month; $125 move-out inspection.'),
    research_source('foxridge-rentcafe', 'https://www.rentcafe.com/apartments/va/blacksburg/foxridge-apartments-0/default.aspx',
                    'RentCafe: Foxridge and Hethwood', 'Rent ranges for 16 named floor plans; unit ids are waitlist buckets.'),
    research_source('foxridge-apartments-com', 'https://www.apartments.com/foxridge-apartment-homes-blacksburg-va/xrqgm5p/',
                    'Apartments.com: Foxridge', 'Reservation deposit applied toward the security deposit; totals round fees to $74.'),
])
fox_fees = [
    fee('foxridge-internet', 'Internet service', 'MANDATORY_RECURRING', 'PER_CALENDAR_MONTH', 'PER_UNIT', '65.00', source_id='foxridge-fees'),
    fee('foxridge-refuse', 'Refuse removal', 'MANDATORY_RECURRING', 'PER_CALENDAR_MONTH', 'PER_UNIT', '7.00', source_id='foxridge-fees'),
    fee('foxridge-billing', 'Rent billing fee', 'MANDATORY_RECURRING', 'PER_CALENDAR_MONTH', 'PER_UNIT', '1.50', source_id='foxridge-fees',
        note='Apartments.com and Homes.com round the three monthly fees to $74.00; the fee guide totals $73.50.'),
    fee('foxridge-application', 'Application fee', 'MANDATORY_ONE_TIME', 'AT_APPLICATION', 'PER_APPLICANT', '35.00', source_id='foxridge-fees'),
    fee('foxridge-admin', 'Administrative fee', 'MANDATORY_ONE_TIME', 'AT_MOVE_IN', 'PER_UNIT', '200.00', source_id='foxridge-fees'),
    fee('foxridge-move-out', 'Move-out inspection fee', 'MANDATORY_ONE_TIME', 'AT_MOVE_OUT', 'PER_UNIT', '125.00', source_id='foxridge-fees'),
    fee('foxridge-security-deposit', 'Security deposit', 'REFUNDABLE_DEPOSIT', 'AT_MOVE_IN', 'PER_UNIT', '400.00', '1500.00', source_id='foxridge-fees',
        note='Screening-dependent; RentCafe notes a $600 baseline.'),
    fee('foxridge-reservation', 'Reservation payment', 'CREDITED_PREPAYMENT', 'AT_APPLICATION', 'PER_UNIT', '200.00', source_id='foxridge-fees',
        credits_target_fee_id='foxridge-security-deposit', status='conflicting_sources',
        note='The fee guide credits it toward rent; Apartments.com says toward the security deposit. Either way it is not an extra cost.'),
]
fox_utils = dict(internet='EXCLUDED_FIXED_FEE', trash='EXCLUDED_FIXED_FEE', electricity='EXCLUDED_VARIABLE_USAGE',
                 water_sewer='UNKNOWN', heat='UNKNOWN', renters_insurance='PROVIDER_DEPENDENT')
fox_questions = [
    'Exact 2027–28 lease start and end dates and available unit numbers for the chosen floor plan.',
    'Which buildings or phases include water, sewer or heat in rent versus billing them separately.',
    'Whether the $200 reservation payment credits toward the security deposit or first month’s rent.',
    'Maximum legal occupancy if residents share bedrooms (the “Shared Pricing” figures assume this).',
]
fox_conflicts = [
    dict(field='basis', values=[dict(value='“2 Roommates: From $690” shared pricing', source_id='foxridge-plans'),
                                dict(value='Whole-unit lease', source_id='foxridge-rentcafe')],
         resolution='Shared pricing is the minimum whole-unit rent divided by roommates sharing bedrooms; it is not an individual lease.'),
    dict(field='monthly_fees', values=[dict(value='$73.50', source_id='foxridge-fees'), dict(value='$74.00', source_id='foxridge-apartments-com')],
         resolution='Listing calculators round the $1.50 billing fee up. Use the fee guide.'),
]
fox_plans = {
    'foxridge-1': [plan('Burruss', '1359', '2083', '725'), plan('Dogwood', '1394', '2085', '693–767'), plan('Cascade', '1444', '2169', '863'),
                   plan('Spruce', '1504', '2168', '797–829'), plan('Bradford', '1597', '2270', '863–893')],
    'foxridge-2': [plan('Smithfield', '1447', '2390', '921–993'), plan('Grove', '1455', '2436', '921–993'), plan('Claytor', '1522', '2269', '930–1,038'),
                   plan('Draper', '1560', '2411', '1,025'), plan('Preston', '1604', '2599', '930–1,129'), plan('Chestnut', '1620', '2295', '1,086–1,255')],
    'foxridge-3': [plan('Willow', '1728', '2900', '1,008–1,080'), plan('Cedar', '1748', '2786', '1,225–1,255'), plan('Maple', '1760', '2692', '1,121–1,177')],
}
for oid, plans in fox_plans.items():
    extra = dict(uncovered_plans=[plan('Leyland (4 bedroom)', '2919', '4043', '1,860'), plan('Foxfield (5 bedroom)', '3564', '4984', '1,998')]) if oid == 'foxridge-3' else {}
    update('foxridge', oid, fees=fox_fees, utility_matrix=fox_utils, utility_source_id='foxridge-fees', price_confidence_tier='ADVERTISED_RANGE',
           advertised_range=dict(currency='USD', basis='whole_unit', period='calendar_month', source_id='foxridge-rentcafe',
                                 minimum=min(p['minimum'] for p in plans), maximum=max(p['maximum'] for p in plans), plans=plans,
                                 note='Advertised “from” ranges across units. A range minimum is not an available quote.', **extra),
           operator_questions=fox_questions, source_conflicts=fox_conflicts,
           unknowns=['Exact base rent needs a quote for a specific unit; only advertised ranges are documented.',
                     'The site still advertises 2026–27 leasing; 2027–28 dates and availability are unconfirmed.',
                     'Water, sewer and heat billing varies by building or phase and is unconfirmed.'])

# ---------------------------------------------------------------- Windsor Hills
add_sources('windsor', [
    research_source('windsor-fees', 'https://www.windsorhillsapts.com/gridmedia/img/fees.pdf', 'Windsor Hills fee schedule (PDF)',
                    'Refuse $9 and rent billing $1.50 per unit per month; deposit $300–$500; $125 move-out inspection.'),
    research_source('windsor-rentcafe', 'https://www.rentcafe.com/apartments/va/blacksburg/windsor-hills/default.aspx',
                    'RentCafe: Windsor Hills', 'Rent ranges for seven named floor plans; unit ids are waitlist buckets.'),
    research_source('windsor-apartments-com', 'https://www.apartments.com/windsor-hills-apartments-blacksburg-va/kdpdh28/',
                    'Apartments.com: Windsor Hills', 'Totals add only $2/mo; deposit shown as $400–$1,500; $40 amenity fee listed.'),
    research_source('windsor-vt-offcampus', 'https://offcampus.vt.edu/housing/property/windsor-hills-apartments/1gptl24',
                    'VT Off-Campus Housing: Windsor Hills', '$40 per-applicant amenity fee due at move-in.'),
])
wh_fees = [
    fee('windsor-refuse', 'Refuse removal', 'MANDATORY_RECURRING', 'PER_CALENDAR_MONTH', 'PER_UNIT', '9.00', source_id='windsor-fees',
        note='Apartments.com leaves this out of its total monthly price.'),
    fee('windsor-billing', 'Rent billing fee', 'MANDATORY_RECURRING', 'PER_CALENDAR_MONTH', 'PER_UNIT', '1.50', source_id='windsor-fees'),
    fee('windsor-application', 'Application fee', 'MANDATORY_ONE_TIME', 'AT_APPLICATION', 'PER_APPLICANT', '30.00', source_id='windsor-fees'),
    fee('windsor-admin', 'Administrative fee', 'MANDATORY_ONE_TIME', 'AT_MOVE_IN', 'PER_UNIT', '200.00', source_id='windsor-fees'),
    fee('windsor-amenity', 'Amenity fee', 'MANDATORY_ONE_TIME', 'AT_MOVE_IN', 'PER_APPLICANT', '40.00', source_id='windsor-vt-offcampus',
        status='conflicting_sources', note='Listed by VT Off-Campus and Apartments.com but absent from the operator fee PDF.'),
    fee('windsor-move-out', 'Move-out inspection fee', 'MANDATORY_ONE_TIME', 'AT_MOVE_OUT', 'PER_UNIT', '125.00', source_id='windsor-fees'),
    fee('windsor-security-deposit', 'Security deposit', 'REFUNDABLE_DEPOSIT', 'AT_MOVE_IN', 'PER_UNIT', '300.00', '500.00', source_id='windsor-fees',
        status='conflicting_sources', note='Operator PDF says $300–$500; Apartments.com shows $400–$1,500, likely copied from Foxridge.'),
    fee('windsor-reservation', 'Reservation payment', 'CREDITED_PREPAYMENT', 'AT_APPLICATION', 'PER_UNIT', '200.00', source_id='windsor-fees',
        credits_target_fee_id='windsor-security-deposit'),
]
wh_utils = dict(trash='EXCLUDED_FIXED_FEE', electricity='EXCLUDED_VARIABLE_USAGE', water_sewer='EXCLUDED_VARIABLE_USAGE',
                internet='PROVIDER_DEPENDENT', renters_insurance='PROVIDER_DEPENDENT')
wh_questions = [
    'Live available units and 2027–28 lease dates for the chosen floor plan.',
    'Whether the $40 per-applicant amenity fee is charged in addition to the $200 administrative fee.',
    'Whether the security deposit is $300–$500 (operator PDF) or $400–$1,500 (Apartments.com).',
]
wh_plans = {
    'windsor-1': [plan('The Canterbury', '1234', '1851', '836'), plan('The Dover (with den)', '1250', '1875', '928–936')],
    'windsor-2': [plan('The Lincoln', '1403', '2105', '1,046'), plan('The Rochester (with den)', '1441', '2321', '1,138–1,146')],
    'windsor-3': [plan('The Lynford', '1680', '2520', '1,214'), plan('The Warwick (with den)', '1844', '2961', '1,306–1,314')],
}
for oid, plans in wh_plans.items():
    extra = dict(uncovered_plans=[plan('The Ripley (studio)', '1294', '1941', '389–536')]) if oid == 'windsor-1' else {}
    update('windsor', oid, fees=wh_fees, utility_matrix=wh_utils, utility_source_id='windsor-fees', price_confidence_tier='ADVERTISED_RANGE',
           advertised_range=dict(currency='USD', basis='whole_unit', period='calendar_month', source_id='windsor-rentcafe',
                                 minimum=min(p['minimum'] for p in plans), maximum=max(p['maximum'] for p in plans), plans=plans,
                                 note='Advertised ranges for a 12-month whole-unit lease. A range minimum is not an available quote.', **extra),
           operator_questions=wh_questions,
           source_conflicts=[dict(field='security_deposit', values=[dict(value='$300–$500', source_id='windsor-fees'),
                                                                    dict(value='$400–$1,500', source_id='windsor-apartments-com')],
                                  resolution='Unresolved; ask the operator.')],
           unknowns=['Exact base rent needs a quote for a specific unit; only advertised ranges are documented.',
                     'Live availability is unverified: listing sites disagree between 0 and 7 available units.'])

# ---------------------------------------------------------------- Terrace View
add_sources('terrace', [
    research_source('terrace-fees', 'https://terraceviewblacksburg.com/fees', 'Terrace View fee disclosure',
                    'Per installment: technology $40, trash $10, utility billing $5. Application $50; admin $150 per primary leaseholder.'),
    research_source('terrace-zillow', 'https://www.zillow.com/apartments/blacksburg-va/terrace-view/5XnfjS/', 'Zillow: Terrace View',
                    'Per-room rents for Aug 21 availability; pet policy.', 'Aug 21, 2027 – Jul 31, 2028'),
    research_source('terrace-homes', 'https://www.homes.com/property/terrace-view-blacksburg-va/vy6l95q4xdchq/', 'Homes.com: Terrace View',
                    'Total monthly price $945 = $890 base + $55 fees.'),
])
tv_fees = [
    fee('terrace-technology', 'Technology fee', 'MANDATORY_RECURRING', 'PER_INSTALLMENT', 'PER_BED_INSTALLMENT', '40.00', source_id='terrace-fees', included=None),
    fee('terrace-trash', 'Trash fee', 'MANDATORY_RECURRING', 'PER_INSTALLMENT', 'PER_BED_INSTALLMENT', '10.00', source_id='terrace-fees', included=None),
    fee('terrace-utility-billing', 'Utility billing fee', 'MANDATORY_RECURRING', 'PER_INSTALLMENT', 'PER_BED_INSTALLMENT', '5.00', source_id='terrace-fees', included=None),
    fee('terrace-application', 'Application fee', 'MANDATORY_ONE_TIME', 'AT_APPLICATION', 'PER_APPLICANT', '50.00', source_id='terrace-fees'),
    fee('terrace-admin', 'Administrative fee', 'MANDATORY_ONE_TIME', 'AT_MOVE_IN', 'PER_PRIMARY_LEASEHOLDER', '150.00', source_id='terrace-fees'),
    fee('terrace-security-deposit', 'Security deposit', 'REFUNDABLE_DEPOSIT', 'AT_MOVE_IN', 'PER_BED_INSTALLMENT', '200.00', None, source_id='terrace-fees',
        amount_max_note='Up to 2× rent depending on qualification', status='conflicting_sources',
        note='$200 was shown for 1x1 Tier 3; the general policy is up to 2× rent.'),
    fee('terrace-pet-fee', 'Pet fee', 'OPTIONAL_ADDON', 'AT_MOVE_IN', 'PER_PET', '300.00', source_id='terrace-zillow', note='Dogs and cats, up to 2 pets.'),
    fee('terrace-pet-rent', 'Pet rent', 'OPTIONAL_ADDON', 'PER_INSTALLMENT', 'PER_PET', '45.00', source_id='terrace-zillow'),
]
tv_utils = dict(wifi='EXCLUDED_FIXED_FEE', trash='EXCLUDED_FIXED_FEE', electricity='EXCLUDED_VARIABLE_USAGE',
                shared_space_electricity='EXCLUDED_VARIABLE_USAGE', renters_insurance='PROVIDER_DEPENDENT')
tv_questions = [
    'The full Fall 2027 fee schedule: are the $40 technology, $10 trash and $5 billing fees on top of the listed per-bed rate?',
    'Why 1x1 Tier 3 shows $1,450 on the portal versus $1,445 on listing sites.',
    'Whether the Aug 21, 2027 – Jul 31, 2028 lease is billed in 12 or 11 installments.',
    'When the $200 deposit applies versus up to 2× rent.',
    'Individual versus joint lease options for the chosen tier, and whether rooms in one unit can be reserved together.',
]
tv_plans = {
    'terrace-1': [plan('1x1 Tier 3', '1445', '1445', None), plan('1x1 Tier 2', '1495', '1495', None), plan('1x1.5 townhome Tier 3', '1505', '1505', None)],
    'terrace-2': [plan('2x1 (renovation tiers)', '855', '910', None)],
    'terrace-4': [plan('4x2', '900', '920', None), plan('4x2.5 Tier 3', '949', '949', None)],
}
for oid, plans in tv_plans.items():
    extra = dict(uncovered_plans=[plan('3x1.5 rooms', '845', '935', '1,128'), plan('3x2 rooms', '890', '920', None)]) if oid == 'terrace-2' else {}
    conflicts = [dict(field='amount', values=[dict(value='$1,450 total monthly leasing price', source_id='terrace-plans'),
                                              dict(value='$1,445 base', source_id='terrace-zillow'), dict(value='$1,350', source_id='terrace-zillow')],
                      resolution='Unresolved; the portal fee pop-up could not be read.')] if oid == 'terrace-1' else []
    update('terrace', oid, fees=tv_fees, utility_matrix=tv_utils, utility_source_id='terrace-fees', price_confidence_tier='ADVERTISED_RANGE',
           advertised_range=dict(currency='USD', basis='per_person', period='installment', source_id='terrace-zillow',
                                 minimum=min(p['minimum'] for p in plans), maximum=max(p['maximum'] for p in plans), plans=plans,
                                 note='Per-bed listing rents for Aug 21, 2027 availability. Not an operator quote.', **extra),
           operator_questions=tv_questions, source_conflicts=conflicts,
           unknowns=['Exact per-bed rate needs a quote for a specific tier; only listing-site rents are documented.',
                     'Payment count (12 or 11 installments) and lease responsibility are unconfirmed.'])

# ---------------------------------------------------------------- Alight
add_sources('alight', [
    research_source('alight-onesheet', 'https://alight-blacksburg.com/one-sheet/', 'Alight one-sheet',
                    '4x2 East $829, 4x2 West $849, 2x1 Standard $949, With fireplace $999; prices include mandatory fees.',
                    'Aug 18, 2027 – Jul 24, 2028, 12 installments'),
])
alight_totals = {
    'alight-east': ('10175', '835', 'East', 'Total price: $10,175 - $10,415 | 2027-28 Academic Year Floorplan Choices: East $835 West $855'),
    'alight-west': ('10415', '855', 'West', 'Total price: $10,175 - $10,415 | 2027-28 Academic Year Floorplan Choices: East $835 West $855'),
    'alight-2': ('11615', '955', 'Standard', 'Total price: $11,615 - $12,143 | 2027-28 Academic Year Floorplan Choices: Standard $955 With fireplace $999'),
}
alight_plans_src = next(s for s in props['alight']['sources'] if s['id'] == 'alight-plans')
onesheet = {'alight-east': '829', 'alight-west': '849', 'alight-2': '949'}
for oid, (total, rate, label, quote) in alight_totals.items():
    offer = next(o for o in props['alight']['offers'] if o['id'] == oid)
    assert offer['amount'] == rate, (oid, offer['amount'])
    water = 'INCLUDED' if oid == 'alight-west' else 'EXCLUDED_VARIABLE_USAGE'
    offer['evidence'] = [e for e in offer['evidence'] if e.get('field') not in ('annual_total', 'utilities')] + [
        dict(field='annual_total', quote=quote, source_id='alight-plans', source_hash=alight_plans_src['sha256'], reviewed_at=alight_plans_src['reviewed_at'],
             note=f'{label} is the {"low" if label != "West" else "high"} end of the published range; ${total} − 12 × ${rate} = $155 in mandatory fees.'),
        dict(field='utilities', quote='Includes furnishings, in-unit laundry, high-speed Internet, water (included in West 4-bedroom), community amenities.',
             source_id='alight-plans', source_hash=alight_plans_src['sha256'], reviewed_at=alight_plans_src['reviewed_at']),
    ]
    update('alight', oid, annual_total=total, price_confidence_tier='PORTAL_QUOTE',
           fees=[
               fee(f'{oid}-mandatory-fees', 'Mandatory fees in the published annual total', 'MANDATORY_RECURRING', 'PER_TERM', 'PER_BED_INSTALLMENT', '155.00',
                   source_id='alight-plans', derivation=f'published annual total ${int(total):,} minus 12 installments of ${rate}',
                   note='Not itemized; payment timing is not published.'),
               fee(f'{oid}-deposit', 'Security deposit', 'CONDITIONAL_SITUATIONAL', 'AT_MOVE_IN', 'PER_BED_INSTALLMENT', None, source_id='alight-plans',
                   note='Waived for new applicants during the current promotion; approved guarantor or partial prepaid rent required.'),
           ],
           utility_matrix=dict(internet='INCLUDED', water=water, electricity='EXCLUDED_VARIABLE_USAGE', renters_insurance='UNKNOWN'), utility_source_id='alight-plans',
           operator_questions=['What the $155 in mandatory fees covers and when it is billed, and why the one-sheet lists rates $6 lower.',
                               'Application fee, administrative fee and security deposit for 2027–28 outside the current promotion.',
                               'Whether beds in the same unit can be reserved together for a household.'],
           source_conflicts=[dict(field='amount', values=[dict(value=f'${rate} per installment', source_id='alight-plans'),
                                                          dict(value=f'${onesheet[oid]} per installment, mandatory fees included', source_id='alight-onesheet')],
                                  resolution='The reviewed rates page is used. The $6 difference is unresolved.')],
           unknowns=['Mandatory fees ($155 per year in the published total) are not itemized and their payment timing is unknown.',
                     'Application and administrative charges, and the deposit outside the current promotion, are not published.'])

# ---------------------------------------------------------------- Union
add_sources('union', [
    research_source('union-faq', 'https://www.unionblacksburg.com/blacksburg/union-blacksburg/faqs/', 'Union Blacksburg FAQ',
                    'Wi-Fi, water, sewer, trash, maintenance and pest control included; electricity billed through the resident portal.'),
    research_source('union-vt-offcampus', 'https://offcampus.vt.edu/housing/property/union-blacksburg/c93z2yf', 'VT Off-Campus Housing: Union',
                    'Utility - Billing Administrative Fee $6.79; application $35; administrative $200.'),
    research_source('union-forrent', 'https://www.forrent.com/va/blacksburg/union-blacksburg/eb396yp', 'ForRent: Union Blacksburg',
                    'Fee shown as $6.44; lease labelled “11 Month Lease”; insurance $14.50 or $10.75.'),
])
union_quotes = {
    'union-s1': ('1678', 'Total Monthly Leasing Price $1,684.79 Base Rent: $1,678/per installment'),
    'union-b2': ('1414', 'Total Monthly Leasing Price $1,420.79 Base Rent: $1,414/per installment'),
    'union-c1': ('1340', 'Total Monthly Leasing Price $1,346.79 Base Rent: $1,340/per installment'),
}
union_src = next(s for s in props['union']['sources'] if s['id'] == 'union-plans')
for oid, (rate, quote) in union_quotes.items():
    offer = next(o for o in props['union']['offers'] if o['id'] == oid)
    assert offer['amount'] == rate, (oid, offer['amount'])
    offer['evidence'] = [e for e in offer['evidence'] if e.get('field') != 'recurring_fee'] + [
        dict(field='recurring_fee', quote=quote, source_id='union-plans', source_hash=union_src['sha256'], reviewed_at=union_src['reviewed_at'],
             note='The total exceeds base rent by exactly $6.79 for every plan and tier on the reviewed page.')]
    update('union', oid, price_confidence_tier='PORTAL_QUOTE',
           fees=[
               fee('union-utility-billing', 'Utility billing administrative fee', 'MANDATORY_RECURRING', 'PER_INSTALLMENT', 'PER_BED_INSTALLMENT', '6.79',
                   source_id='union-plans', name_source_id='union-vt-offcampus',
                   note='Listing sites file it under move-in charges and some cached pages show $6.44; the reviewed portal adds it to every installment.'),
               fee('union-application', 'Application fee', 'MANDATORY_ONE_TIME', 'AT_APPLICATION', 'PER_APPLICANT', '35.00', source_id='union-vt-offcampus'),
               fee('union-admin', 'Administrative fee', 'MANDATORY_ONE_TIME', 'AT_MOVE_IN', 'PER_PRIMARY_LEASEHOLDER', '200.00', source_id='union-vt-offcampus'),
               fee('union-security-deposit', 'Security deposit', 'REFUNDABLE_DEPOSIT', 'AT_MOVE_IN', 'PER_BED_INSTALLMENT', None, source_id='union-vt-offcampus',
                   note='Depends on screening.'),
               fee('union-insurance', 'Liability insurance', 'CONDITIONAL_SITUATIONAL', 'PER_CALENDAR_MONTH', 'PER_BED_INSTALLMENT', '10.75', '14.50',
                   source_id='union-forrent', note='$14.50/mo property program, or $10.75/mo non-compliance coverage without your own policy.'),
           ],
           utility_matrix=dict(wifi='INCLUDED', water='INCLUDED', sewer='INCLUDED', trash='INCLUDED', pest_control='INCLUDED',
                               electricity='EXCLUDED_VARIABLE_USAGE'), utility_source_id='union-faq',
           operator_questions=['Whether the Aug 16, 2027 – Jul 17, 2028 lease is billed in 12 or 11 installments.',
                               'That the billing fee is $6.79, not the $6.44 cached on floor-plan subpages.',
                               'How the security deposit is set, and whether rooms in one unit can be reserved together.'],
           source_conflicts=[dict(field='installments', values=[dict(value='Annual, per installment', source_id='union-plans'),
                                                                dict(value='11 Month Lease', source_id='union-forrent')],
                                  resolution='Unresolved; term total stays undocumented.'),
                             dict(field='utility_billing_fee', values=[dict(value='$6.79', source_id='union-plans'), dict(value='$6.44', source_id='union-forrent')],
                                  resolution='The reviewed portal amount is used.')],
           unknowns=['Payment count (12 or 11 installments) is unconfirmed, so no term total is calculated.',
                     'Lease responsibility (individual or joint) and the security deposit are not documented.'])

# ---------------------------------------------------------------- The Mill
add_sources('mill', [
    research_source('mill-apartments-com', 'https://www.apartments.com/the-mill-at-blacksburg-blacksburg-va/ydldhfr/', 'Apartments.com: The Mill',
                    'Application Fee Per Applicant. $35. Charged per applicant. Also shows an incorrect “By-The-Bed Leasing” badge.'),
])
for offer in props['mill']['offers']:
    deposit = next(u['amount'] for u in offer['upfront'] if u['label'] == 'Security deposit')
    update('mill', offer['id'], price_confidence_tier='PORTAL_QUOTE',
           fees=[
               fee(f"{offer['id']}-deposit", 'Security deposit', 'REFUNDABLE_DEPOSIT', 'AT_MOVE_IN', 'PER_UNIT', f'{deposit}.00', source_id='mill-plans'),
               fee('mill-application', 'Application fee', 'MANDATORY_ONE_TIME', 'AT_APPLICATION', 'PER_APPLICANT', '35.00', source_id='mill-plans',
                   basis_source_id='mill-apartments-com', note='Amount from the operator; the per-applicant basis comes from Apartments.com.'),
           ],
           utility_matrix=dict(water='INCLUDED', sewer='INCLUDED', trash='INCLUDED', recycling='INCLUDED',
                               electricity='EXCLUDED_VARIABLE_USAGE', internet='PROVIDER_DEPENDENT', renters_insurance='PROVIDER_DEPENDENT'),
           utility_source_id='mill-plans',
           operator_questions=['Exact physical move-in date in August 2027 and move-out date in July 2028.',
                               'How many units of this size remain for 2027–28.', 'The occupancy limit per bedroom.'],
           source_conflicts=[dict(field='contract', values=[dict(value='Pricing is per unit; joint and several responsibility', source_id='mill-plans'),
                                                             dict(value='“By-The-Bed Leasing” badge', source_id='mill-apartments-com')],
                                  resolution='The operator page governs: whole-unit joint lease.')],
           unknowns=['Exact physical move-in and move-out dates are not published; the 12 installments are due Aug 1 – Jul 1 and are not prorated.',
                     'Occupancy limit per bedroom and current availability are unconfirmed.'])

seed['research_port'] = '2026-10-24-pricing-research-audit'
seed_path.write_text(json.dumps(seed, indent=2, ensure_ascii=False), encoding='utf-8')
print('ported', sum(len(p['offers']) for p in seed['properties']), 'offers;', sum(len(p['sources']) for p in seed['properties']), 'sources')
