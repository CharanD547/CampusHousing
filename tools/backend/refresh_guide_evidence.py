"""Refresh missing guide evidence from named official operator pages; keep all entries.

Published asking figures remain research observations until billing basis, lease
dates and mandatory fees support comparison. Operator map points are address
references, not verified entrances. Run --apply after inspecting the report.
"""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT))
from roomwise.adapters.sources import fetch
from roomwise.config import now,Settings
from roomwise.services.guide_catalog import guide_properties
from roomwise.repositories.catalog import CatalogRepository
from tools.backend.sync_catalog import sync_catalog

# Official property pages linked by CMG's public property navigation.
CMG={
 'the-edge-apartments-townhomes':('the-edge-apts',('edge',)),
 'tech-terrace':('tech-terrace',('tech terrace',)),
 'the-lofts-at-316':('lofts-at-316',('lofts',)),
 'chase-apartments-the-chase':('chase',('chase',)),
 'chasewood-downs':('chasewood-downs',('chasewood',)),
 'shawnee-apartments':('shawnee-apartments',('shawnee',)),
 'cedar-pointe-apartments':('cedarpointe',('cedar pointe',)),
 'cedarfield-apartments-townhomes':('cedarfield-apts-townhomes',('cedarfield',)),
 'the-vue-apartments':('vue-apartments',('vue',)),
 'the-reserve-at-knollwood':('reserve-at-knollwood',('reserve at knollwood',)),
 'the-crossing-at-knollwood':('crossing-at-knollwood',('crossing',)),
 'knollwood-condominium':('knollwood-condos',('knollwood',)),
 'knollwood-townhomes':('knollwood-townhomes',('knollwood',)),
}
EXTRA={
 'haven-blacksburg-haven-on-north-main':'https://www.havenblacksburg.com/',
 'park37':'https://www.roostrealestategroup.com/park37',
 'brexx-at-blacksburg-the-retreat':'https://www.brexxblacksburg.com/floor-plans/',
}

class OperatorParser(HTMLParser):
    def __init__(self):
        super().__init__();self.blocks=[];self.heading=None;self.title=[];self.body=[];self.hidden=0;self.level=None;self.point=None
    def flush(self):
        if self.heading:self.blocks.append((' '.join(self.title).strip(),re.sub(r'\s+',' ',' '.join(self.body)).strip()))
        self.heading=None;self.title=[];self.body=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ('script','style','noscript'):self.hidden+=1
        if 'data-community' in attrs and 'data-lat' in attrs and 'data-lng' in attrs:
            lat,lon=float(attrs['data-lat']),float(attrs['data-lng'])
            if 37.15<lat<37.30 and -80.55<lon<-80.30:self.point={'lat':lat,'lon':lon}
        if tag in ('h2','h3'):
            self.flush();self.heading=tag;self.level=tag
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript'):self.hidden=max(0,self.hidden-1)
        if tag==self.level:self.level=None
    def handle_data(self,text):
        if self.hidden:return
        if self.level:self.title.append(text.strip())
        elif self.heading:self.body.append(text.strip())

def extract_cmg(html,prefixes):
    parser=OperatorParser();parser.feed(html);parser.flush();rows=[]
    for title,body in parser.blocks:
        if not any(prefix in title.casefold() for prefix in prefixes):continue
        match=re.search(r'(\$[\d,]+\.\d{2}(?:\s*[-–]\s*\$[\d,]+\.\d{2})?)\s+Apply Now',body)
        beds=re.search(r'(\d+)\s+bed\b',body)
        if not match or not beds:continue
        amounts=[float(s.replace('$','').replace(',','')) for s in re.findall(r'\$[\d,]+\.\d{2}',match[1])]
        row={'label':title,'bedrooms':int(beds[1]),'minimum':min(amounts),'maximum':max(amounts)}
        if row not in rows:rows.append(row)
    return rows,parser.point

def extract_extra(key,html,text):
    parser=OperatorParser();parser.feed(html);parser.flush();rows=[]
    if key.startswith('haven'):
        price=re.search(r'\$\s*([\d,]+)\s*[-–]\s*\$?\s*([\d,]+)\s*RENT\s*/\s*BED',text,re.I)
        if price:rows=[{'label':'Published rent per bed · 2–4 bedrooms','bedrooms':None,'minimum':float(price[1].replace(',','')),'maximum':float(price[2].replace(',',''))}]
    else:
        for title,body in parser.blocks:
            beds=re.search(r'(\d+)\s*Bed\b',body,re.I)
            if not beds:continue
            if key=='park37':prices=re.findall(r'(?:Rent|Furnished Rate):\s*\$([\d,]+)\s*/\s*room',body,re.I)
            else:prices=re.findall(r'Starting at\s*\$([\d,]+)',body,re.I)
            if not prices:continue
            amounts=[float(x.replace(',','')) for x in prices]
            row={'label':title,'bedrooms':int(beds[1]),'minimum':min(amounts),'maximum':max(amounts)}
            if row not in rows:rows.append(row)
    return rows,parser.point

def main(apply=False,from_preview=False,only_extra=False):
    path=ROOT/'data/housing-guide-evidence.json'
    evidence=json.loads(path.read_text()) if path.exists() else {'format':'roomwise-guide-evidence-v1','properties':{}}
    folder=ROOT/'var/guide-source-refresh';folder.mkdir(parents=True,exist_ok=True)
    if from_preview:
        from datetime import datetime,timezone
        evidence=json.loads((folder/'preview.json').read_text())
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(evidence['checked_at'])).total_seconds()
        if not 0<=age<3600:raise ValueError('Collect a fresh preview before applying.')
    report=[]
    for key,(slug,prefixes) in ({} if from_preview or only_extra else CMG).items():
        url='https://www.cmgleasing.com/property/'+slug+'/'
        try:
            record=fetch({'url':url},include_html=True)
            rows,point=extract_cmg(record.pop('html'),prefixes)
            address=re.search(r'Property Address:\s*(.*?)\s*Contact Us!',record['text'])
            update={'status':'operator_observed','source_url':url,'checked_at':record['retrieved_at'],
                'source_sha256':record['sha256'],'prices':rows,'coordinates':point,
                'address':address[1].strip() if address else None,
                'billing_note':'Operator-published asking figures. Confirm billing basis, required fees, lease dates and availability.',
                'location_note':'Approximate community address point published by the operator; not a verified entrance.'}
            evidence['properties'][key]=update
            (folder/(key+'.json')).write_text(json.dumps(record),encoding='utf-8')
            report.append({'property':key,'prices':len(rows),'mapped':bool(point),'status':'observed'})
        except Exception as error:
            previous=evidence['properties'].get(key,{})
            previous.update(last_attempt_at=now(),last_attempt_error=str(error)[:250])
            evidence['properties'][key]=previous
            report.append({'property':key,'status':'unavailable','reason':str(error)[:180]})
    for key,url in ({} if from_preview else EXTRA).items():
        try:
            record=fetch({'url':url},include_html=True)
            rows,point=extract_extra(key,record.pop('html'),record['text'])
            evidence['properties'][key]={'status':'operator_observed','source_url':url,'checked_at':record['retrieved_at'],
                'source_sha256':record['sha256'],'prices':rows,'coordinates':point,'address':None,
                'billing_note':('Published per-bed asking range. Confirm payment schedule, fees, exact unit and lease dates.' if key.startswith('haven') else 'Published per-room rates; ranges may include furnishing options. Confirm fees and payment schedule.' if key=='park37' else 'Published starting rates per person/bed. Confirm fees, payment schedule and lease dates.'),
                'location_note':'Operator community point where provided; otherwise use the address-search map.'}
            (folder/(key+'.json')).write_text(json.dumps(record),encoding='utf-8')
            report.append({'property':key,'prices':len(rows),'mapped':bool(point),'status':'observed'})
        except Exception as error:
            report.append({'property':key,'status':'unavailable','reason':str(error)[:180]})
    browser_path=ROOT/'data/housing-guide-browser-evidence.json'
    if browser_path.exists():
        browser=json.loads(browser_path.read_text(encoding='utf-8'))
        for key,record in browser.get('properties',{}).items():
            previous=evidence['properties'].get(key,{})
            if not previous.get('prices') or record['checked_at']>previous.get('checked_at',''):
                evidence['properties'][key]=record
    evidence['checked_at']=now()
    (folder/'preview.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    if apply:
        path.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        guide=json.loads((ROOT/'data/housing-guide.json').read_text())
        props=guide_properties(guide,evidence)
        sync_catalog(CatalogRepository(Settings.from_env().data_dir),{'properties':props},{},True)
    print(json.dumps({'applied':apply,'properties':report},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('--from-preview',action='store_true');parser.add_argument('--only-extra',action='store_true')
    args=parser.parse_args();main(args.apply,args.from_preview,args.only_extra)
