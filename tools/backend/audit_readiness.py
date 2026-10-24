"""Read-only operational audit. Presence of credentials is not proof of provider access."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from roomwise.config import Settings


def audit(settings):
    catalog_path=settings.data_dir/'catalog.sqlite3'
    if not catalog_path.is_file():raise ValueError('Initialize the application before auditing its live catalog.')
    with sqlite3.connect(f'{catalog_path.resolve().as_uri()}?mode=ro',uri=True) as db:
        catalog=[json.loads(row[0]) for row in db.execute('SELECT body FROM housing_catalog ORDER BY rowid')]
        sources={key:json.loads(body) for key,body in db.execute('SELECT id,body FROM housing_sources')}
        for prop in catalog:prop['sources']=[sources[s['id']] for s in prop['sources']]
    rows=[]
    for prop in catalog:
        sources={s['id']:s for s in prop['sources']}
        for offer in prop['offers']:
            source=sources[offer['source_id']]
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(source['checked_at'].replace('Z','+00:00'))).total_seconds()/86400
            rows.append({'id':offer['id'],'property':prop['name'],'amount':offer['amount'],'basis':offer['basis'],
                         'period':offer['period'],'payment_count':offer.get('installments'),'source_url':source['url'],
                         'reviewed_at':source['checked_at'],'stale_over_7_days':age>7,
                         'status':'exact_price_unknown' if offer['amount'] is None else 'dated_asking_price_not_availability',
                         'unconfirmed_costs':offer['unknowns']})
    databases=[]
    for path in sorted(settings.data_dir.glob('*.sqlite3')):
        with sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro',uri=True) as db:
            result=db.execute('PRAGMA integrity_check').fetchall()
        databases.append({'file':path.name,'integrity':'ok' if result==[('ok',)] else 'failed'})
    return {'audited_at':datetime.now(timezone.utc).isoformat(),'operation':'local catalog/database inspection; no live rent availability verification',
            'catalog':{'offers':len(rows),'numeric_asking_prices':sum(r['amount'] is not None for r in rows),
                       'unknown_exact_prices':sum(r['amount'] is None for r in rows),'stale_offers':sum(r['stale_over_7_days'] for r in rows),'records':rows},
            'databases':databases,'configuration':{'maps_enabled':settings.maps_enabled,'places_enabled':settings.places_enabled,
                'routes_enabled':settings.routes_enabled,'routes_key_present':bool(settings.routes_api_key),
                'ai_enabled':settings.external_operations_enabled,'ai_provider':settings.ai_provider,
                'operator_token_present':bool(settings.api_token),'local_accounts_required':settings.accounts_required},
            'deployment_tools':{'docker':bool(shutil.which('docker')),'gcloud':bool(shutil.which('gcloud'))},
            'release_gates':['Successful live Routes request with an authorized Routes credential.',
                'Authorized Gemma weights, compatible optional training environment, actual training and held-out generation evaluation.',
                'Reviewed exact property/term/fee reconciliation for unresolved pricing; never fill unknowns with unrelated ranges.',
                'Established review reuse rights and exact property matches before review display or model processing.',
                'Cloud project/identity, durable persistence, secret injection, TLS and a tested container/cloud deployment.',
                'Verify provider restrictions and project quotas in the owner account; application attempt caps do not cap browser Maps billing.']}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path);args=parser.parse_args()
    result=audit(Settings.from_env())
    if args.report:args.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in result.items() if key!='catalog'},indent=2))
    print(json.dumps({key:value for key,value in result['catalog'].items() if key!='records'},indent=2))
