"""Recheck current catalog prices against freshly captured public operator pages.

Browser-only pages must be captured explicitly into var/source-refresh. Simple
HTML sources are retrieved through the robots-aware adapter. Missing/mismatched
plans stop the update. No provider keys, unit availability or old guide prices
are used. Re-run import_live_prices.py and sync_catalog.py after applying.
"""
import argparse
from datetime import datetime,timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from roomwise.adapters.sources import fetch


def price_pattern(amount):
    value=Decimal(amount)
    whole=str(int(value));grouped=f'{int(value):,}'
    return r'\$\s*(?:'+re.escape(grouped)+'|'+whole+r')(?:\.00)?(?![\d.])'


def recheck(directory,apply=False):
    path=ROOT/'data/housing-live-prices.json'
    live=json.loads(path.read_text(encoding='utf-8'));report=[]
    for pid,spec in live['properties'].items():
        source=spec['source'];target=directory/(source['id']+'.json')
        if pid in ('alight','mill'):
            record={**fetch({'url':source['url'],'refresh_policy':'manual_review'}),'url':source['url'],'method':'robots-aware fetch'}
            target.write_text(json.dumps(record),encoding='utf-8')
        else:record=json.loads(target.read_text(encoding='utf-8'))
        if record.get('url')!=source['url']:raise ValueError('Wrong captured source: '+pid)
        age=datetime.now(timezone.utc)-datetime.fromisoformat(record['retrieved_at'].replace('Z','+00:00'))
        if age.total_seconds()<0 or age.total_seconds()>3600:raise ValueError('Capture must be less than one hour old: '+pid)
        text=re.sub(r'\s+',' ',record['text']).strip();quotes=[]
        for plan in spec['plans']:
            name=re.sub(r'\s*\([^)]*\)','',plan['name'])
            if pid=='union' and 'Existing unit' in name:name=name.split()[0]+' - Existing Unit'
            if pid=='alight':name=name.split(',')[-1].strip()
            if pid=='mill':name=str(plan['bedrooms'])+' Bedroom'
            # Captured page content, not a private leasing API. Require the
            # floor-plan name and advertised price in a short local segment.
            marker=re.compile(re.escape(name),re.I)
            segments=[text[m.start():m.start()+900] for m in marker.finditer(text)]
            supported=next((segment for segment in segments if re.search(price_pattern(plan['amount']),segment)),None)
            if supported is None:raise ValueError(f'Price needs review: {pid} / {plan["name"]}')
            match=re.search(price_pattern(plan['amount']),supported)
            quote=supported[:match.end()]
            plan['verified_quote']=quote;quotes.append(quote)
        spec['verified_at']=record['retrieved_at'];spec['quote']=quotes[0]
        spec['verification']={'method':record['method'],'page_sha256':hashlib.sha256(text.encode()).hexdigest(),
                              'plans_checked':len(quotes),'availability_verified':False}
        report.append({'property':pid,'plans':len(quotes),'status':'price_confirmed','retrieved_at':record['retrieved_at']})
    live['retrieved_at']=datetime.now(timezone.utc).isoformat()
    live['scope']='Public operator asking prices rechecked on Oct 24, 2026 EDT. Per-source observation times retained; availability and a signed quote are unverified.'
    if apply:path.write_text(json.dumps(live,indent=2,ensure_ascii=False),encoding='utf-8')
    return {'applied':apply,'sources':report}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-dir',type=Path,default=ROOT/'var/source-refresh')
    parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    print(json.dumps(recheck(args.capture_dir,args.apply),indent=2))
