"""Explicitly apply the checked-in catalog, archiving replaced rows atomically.

Run without --apply to preview. Back up var first. Frozen comparisons and briefs
are never rewritten; old selections remain in those snapshots.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from roomwise.config import Settings, now
from roomwise.repositories.catalog import CatalogRepository
from roomwise.services.comparison import candidates
from roomwise.api.schemas import CatalogResponse


def sync_catalog(repository,seed,snapshots,apply=False):
    CatalogResponse.model_validate({'campus_id':'vt','candidates':candidates(seed['properties'])})
    ids=[p['id'] for p in seed['properties']]
    offers=[o['id'] for p in seed['properties'] for o in p['offers']]
    if len(set(ids))!=len(ids) or len(set(offers))!=len(offers):raise ValueError('Duplicate catalog IDs.')
    changed=[]
    with repository.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        for prop in seed['properties']:
            previous=db.execute('SELECT body FROM housing_catalog WHERE id=?',(prop['id'],)).fetchone()
            property_changed = not previous or json.loads(previous[0]) != prop
            source_ids={s['id'] for s in prop['sources']}
            if any(o['source_id'] not in source_ids for o in prop['offers']):raise ValueError('Missing price source.')
            if property_changed: changed.append(prop['id'])
            if not apply:continue
            db.execute('CREATE TABLE IF NOT EXISTS housing_catalog_versions(id TEXT PRIMARY KEY,property_id TEXT,created_at TEXT,body TEXT)')
            if previous and property_changed:
                digest=sha256(previous[0].encode()).hexdigest()
                db.execute('INSERT OR IGNORE INTO housing_catalog_versions VALUES (?,?,?,?)',(digest,prop['id'],now(),previous[0]))
            db.execute('INSERT INTO housing_catalog VALUES (?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',
                       (prop['id'],json.dumps(prop)))
            for source in prop['sources']:
                snapshot=snapshots.get(source['id'],{})
                text=snapshot.get('text','')
                prior=db.execute('SELECT body,text FROM housing_sources WHERE id=?',(source['id'],)).fetchone()
                if prior:
                    version=sha256((source['id']+prior[0]).encode()).hexdigest()
                    db.execute('INSERT OR IGNORE INTO housing_source_versions VALUES (?,?,?,?)',
                        (version,source['id'],json.dumps({'source_id':source['id'],'origin':'pre_catalog_sync','source':json.loads(prior[0])}),prior[1]))
                if not text and prior:text=prior[1]
                db.execute('INSERT INTO housing_sources VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body,text=excluded.text',
                    (source['id'],json.dumps(source),text))
    return {'applied':apply,'changed_properties':changed,'offers':len(offers)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    snapshots={}
    for name in ('housing-source-snapshots.json','housing-live-snapshots.json'):
        snapshots.update(json.loads((ROOT/'data'/name).read_text(encoding='utf-8')))
    print(json.dumps(sync_catalog(CatalogRepository(Settings.from_env().data_dir),
        json.loads((ROOT/'data/housing-seed.json').read_text(encoding='utf-8')),snapshots,args.apply),indent=2))
