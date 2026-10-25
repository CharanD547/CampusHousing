"""Export a readable quote/fee follow-up list from the current reviewed catalog files."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from roomwise.services.guide_catalog import guide_properties
from roomwise.services.lease_gaps import property_lease_gaps


def main():
    load=lambda n:json.loads((ROOT/'data'/n).read_text(encoding='utf-8'))
    props=load('housing-seed.json')['properties']+guide_properties(load('housing-guide.json'))
    rows=sorted((property_lease_gaps(p) for p in props),key=lambda p:p['property_name'].casefold())
    (ROOT/'data/lease-evidence-gaps.json').write_text(json.dumps({'properties':rows,'scope':'Public catalog research gaps; no personalized written lease quotes are stored.'},indent=2)+'\n',encoding='utf-8')
    text=['# Fees and written lease quotes still needed','','All 44 priced properties still need a current individualized written operator quote and confirmation of the complete mandatory fee schedule. Listed fee records are useful evidence, but do not establish completeness. Three directory-only references also need current property-specific price evidence.','','For every property request: the exact unit/floor plan and move-in date; quote expiry and availability; all mandatory fees and utility charges; refund/credit treatment; exact lease dates, payment count and total rent; joint/individual liability and guarantor requirements. No message has been sent to an operator.','','## Property-specific follow-up','','| Property | Existing fee records | Lease evidence gaps |','|---|---|']
    for r in rows:
        fees=', '.join(r['listed_fee_labels']) or 'No structured fee amounts collected'
        gaps=[]
        if not r['plan_count']:gaps.append('Directory only; no sourced priced plan')
        if r['plans_missing_lease_dates']:gaps.append(f"Exact dates missing for {r['plans_missing_lease_dates']} plans")
        if r['installment_plans_missing_payment_count']:gaps.append('Installment payment count missing')
        if r['plans_with_unknown_billing_basis']:gaps.append('Billing basis missing')
        if r['fees_with_missing_amounts']:gaps.append('Missing amounts: '+', '.join(r['fees_with_missing_amounts']))
        if not gaps:gaps=['Confirm published dates/payment schedule for the selected unit']
        text.append('| '+r['property_name'].replace('|','/')+' | '+fees.replace('|','/')+' | '+'; '.join(gaps).replace('|','/')+' |')
    text+=['','## Detailed requests','']
    for r in rows:
        text+=['### '+r['property_name'],'']+[f'- {q}' for q in r['questions']]+['']
    (ROOT/'docs/FEES_AND_LEASE_QUOTES.md').write_text('\n'.join(text),encoding='utf-8')
    print(f"Exported {sum(bool(r['plan_count']) for r in rows)} priced properties and {sum(not r['plan_count'] for r in rows)} directory-only references.")


if __name__=='__main__':main()
