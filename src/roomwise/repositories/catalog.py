"""Audited catalog and append-only source history. Separate from private workspaces."""
import hashlib
import json
from pathlib import Path
import sqlite3
from roomwise.config import ROOT
from roomwise.services.guide_catalog import guide_properties

class CatalogRepository:
    def __init__(self, directory):
        self.path = Path(directory) / 'catalog.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS housing_catalog(id TEXT PRIMARY KEY,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS housing_sources(id TEXT PRIMARY KEY,body TEXT NOT NULL,text TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS housing_source_versions(id TEXT PRIMARY KEY,source_id TEXT NOT NULL,body TEXT NOT NULL,text TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS housing_guide(id TEXT PRIMARY KEY,body TEXT NOT NULL);
            ''')
            guide_path=ROOT/'data/housing-guide.json'
            guide_entries=[]
            if guide_path.exists():
                guide=json.loads(guide_path.read_text(encoding='utf-8'))
                guide_entries=guide_properties(guide)
                for entry in guide['communities']:
                    db.execute('INSERT INTO housing_guide VALUES (?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',
                               (entry['id'],json.dumps(entry)))
            seed_path = ROOT / 'data/housing-seed.json'
            if seed_path.exists():
                seed = json.loads(seed_path.read_text(encoding='utf-8'))
                snapshots_path = ROOT / 'data/housing-source-snapshots.json'
                snapshots = json.loads(snapshots_path.read_text(encoding='utf-8')) if snapshots_path.exists() else {}
                for prop in seed['properties']+guide_entries:
                    # Guide entries are derived from data files, so they refresh; reviewed seed offers are inserted once.
                    if prop.get('guide_reference'):
                        db.execute('INSERT INTO housing_catalog VALUES (?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body', (prop['id'], json.dumps(prop)))
                    else:
                        db.execute('INSERT OR IGNORE INTO housing_catalog VALUES (?,?)', (prop['id'], json.dumps(prop)))
                    for source in prop['sources']:
                        snapshot = snapshots.get(source['id'], {})
                        text = snapshot.get('text', '')
                        source = {**source, 'sha256': source.get('sha256') or snapshot.get('sha256') or (hashlib.sha256(text.encode()).hexdigest() if text else None)}
                        db.execute('INSERT OR IGNORE INTO housing_sources VALUES (?,?,?)', (source['id'], json.dumps(source), text))
                        initial_id=hashlib.sha256(('seed:'+source['id']+':'+str(source.get('sha256'))+':'+source['checked_at']).encode()).hexdigest()[:32]
                        initial={**source,'id':initial_id,'source_id':source['id'],'retrieved_at':source['checked_at'],'changed':False,'origin':'reviewed_seed'}
                        db.execute('INSERT OR IGNORE INTO housing_source_versions VALUES (?,?,?,?)',(initial_id,source['id'],json.dumps(initial),text))

    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def catalog(self, db=None):
        if db is None:
            with self.connect() as connection: return self.catalog(connection)
        props = [json.loads(r[0]) for r in db.execute('SELECT body FROM housing_catalog ORDER BY rowid')]
        audit_path = ROOT / 'data/rent-source-recheck.json'
        audit = json.loads(audit_path.read_text(encoding='utf-8')).get('properties', {}) if audit_path.exists() else {}
        for prop in props:
            prop['sources'] = [self.source(s['id'], db=db) for s in prop['sources']]
            checks = audit.get(prop['id'], {}).get('sources', [])
            for source in prop['sources']:
                check = next((c for c in checks if c['source_id'] == source['id'] and c['source_url'] == source.get('url')), None)
                if check:
                    source['rent_recheck'] = check
        return props

    def source(self, key, db=None, with_text=False):
        if db is None:
            with self.connect() as connection: return self.source(key, connection, with_text)
        row = db.execute('SELECT body,text FROM housing_sources WHERE id=?', (key,)).fetchone()
        if not row: raise KeyError('Source not found')
        body = json.loads(row[0])
        if with_text: body['text'] = row[1]
        return body

