"""Describe missing quote evidence without treating absent fees as zero."""


def property_lease_gaps(prop):
    offers = prop.get('offers', [])
    fees = [f for o in offers for f in o.get('fees', [])]
    fee_labels = sorted({f.get('label', 'Unnamed charge') for f in fees})
    missing_amounts = sorted({f.get('label', 'Unnamed charge') for f in fees
                              if f.get('amount_min') is None and f.get('amount') is None})
    missing_dates = sum(not o.get('start') or not o.get('end') for o in offers)
    installment_offers = [o for o in offers if o.get('period') == 'installment']
    missing_count = sum(not o.get('installments') for o in installment_offers)
    unknown_basis = sum(o.get('basis') not in ('person', 'unit') for o in offers)
    questions = [
        'Please provide a dated written quote for the exact floor plan/unit and move-in date, with quote expiry and current availability.',
        ('Please provide the full mandatory fee schedule: application/admin charges, recurring charges, deposits and prepaid rent; state which are included in the advertised price.'
         if not fees else
         'Please confirm the complete mandatory fee schedule in writing, including which listed charges are included, refundable, credited or conditional.'),
        'Please state utility inclusions, usage-based charges and required services; unknown costs must not be treated as zero.',
    ]
    if unknown_basis:
        questions.append(f'Billing basis is unconfirmed for {unknown_basis} plan(s): is each figure per person/bed or for the whole unit?')
    if missing_dates:
        questions.append(f'Exact start/end dates are missing for {missing_dates} plan(s). Please provide the selected lease dates and early-termination terms.')
    else:
        questions.append('Please confirm that the published lease dates apply to the selected unit and move-in date.')
    if missing_count:
        questions.append(f'The payment count is missing for {missing_count} installment plan(s). Please state payment count, due dates, total rent and any proration.')
    else:
        questions.append('Please confirm payment frequency/count, due dates, total contractual rent and any proration.')
    if missing_amounts:
        questions.append('Please provide amounts or calculation rules for: ' + ', '.join(missing_amounts[:12]) + '.')
    questions.append('Please confirm joint versus individual liability, guarantor requirements and deposit deductions/refund rules.')
    update = (prop.get('guide_reference') or {}).get('evidence_update') or {}
    for gap in update.get('remaining_gaps', []):
        if gap not in questions:
            questions.append(str(gap))
    return {'property_id': prop['id'], 'property_name': prop['name'], 'plan_count': len(offers),
            'written_quote_status': 'not_collected', 'complete_fee_schedule_status': 'not_confirmed',
            'listed_fee_labels': fee_labels, 'fees_with_missing_amounts': missing_amounts,
            'plans_missing_lease_dates': missing_dates, 'installment_plans_missing_payment_count': missing_count,
            'plans_with_unknown_billing_basis': unknown_basis, 'questions': questions,
            'source_urls': sorted({s['url'] for s in prop.get('sources', []) if s.get('url')}),
            'limitation': 'Public asking figures and listed fees are not a current written operator quote. This is a research checklist, not legal advice.'}


def quote_request(gaps):
    return ('Subject: Written rental quote request - ' + gaps['property_name'] + '\n\n'
            'Hello, I am researching housing at ' + gaps['property_name'] + '.\n'
            'Selected floor plan/unit: [fill in]\nMove-in date and occupants: [fill in]\n\n'
            + '\n'.join(f'{i}. {q}' for i, q in enumerate(gaps['questions'], 1))
            + '\n\nThank you. Please send the quote and fee/lease disclosures in writing.\n')
