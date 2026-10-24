"""Single-user local adapter. Editable revisions and immutable server-owned snapshots."""
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from roomwise.api.errors import APIError
from roomwise.config import now
from roomwise.repositories.accounts import actor


class WorkspaceStore:
    def __init__(self, directory):
        self.path = Path(directory)/'workspaces.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY,body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS comparisons(id TEXT PRIMARY KEY,body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS briefs(id TEXT PRIMARY KEY,body TEXT NOT NULL,request_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS owners(collection TEXT,id TEXT,owner TEXT,PRIMARY KEY(collection,id));
                CREATE TABLE IF NOT EXISTS trash(collection TEXT,id TEXT,deleted_at TEXT,PRIMARY KEY(collection,id));
            ''')

    def check_owner(self,db,table,key):
        row=db.execute('SELECT owner FROM owners WHERE collection=? AND id=?',(table,key)).fetchone()
        if (row[0] if row else 'local')!=actor.get():
            raise APIError('not_found','Requested record was not found.',404)

    def own(self,db,table,key):
        db.execute('INSERT OR IGNORE INTO owners VALUES (?,?,?)',(table,key,actor.get()))

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def get(self, table, key):
        if table not in ('workspaces', 'comparisons', 'briefs'):
            raise ValueError('Unknown store collection.')
        with self.connect() as db:
            self.check_owner(db,table,key)
            if db.execute('SELECT 1 FROM trash WHERE collection=? AND id=?',(table,key)).fetchone():
                raise APIError('not_found','Requested record was not found.',404)
            row = db.execute(f'SELECT body FROM {table} WHERE id=?', (key,)).fetchone()
        if row is None:
            raise APIError('not_found', 'Requested record was not found.', 404)
        return json.loads(row[0])

    def save_workspace(self, key, body):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT body FROM workspaces WHERE id=?', (key,)).fetchone()
            if row:self.check_owner(db,'workspaces',key)
            if db.execute("SELECT 1 FROM trash WHERE collection='workspaces' AND id=?",(key,)).fetchone():
                raise APIError('record_in_trash','Restore this workspace before editing it.',409)
            revision = json.loads(row[0])['revision'] if row else 0
            if revision != body['revision']:
                raise APIError('revision_conflict', 'Workspace changed. Reload before saving.', 409)
            result = {**body, 'id': key, 'revision': revision+1, 'updated_at': now()}
            db.execute('INSERT OR REPLACE INTO workspaces VALUES (?,?)', (key, json.dumps(result)))
            self.own(db,'workspaces',key)
        return result

    def save_comparison(self, comparison):
        with self.connect() as db:
            db.execute('INSERT INTO comparisons VALUES (?,?)', (comparison['id'], json.dumps(comparison)))
            self.own(db,'comparisons',comparison['id'])

    def save_brief(self, request, snapshot):
        encoded = json.dumps(request, sort_keys=True)
        fingerprint = sha256(encoded.encode()).hexdigest()
        key = sha256((actor.get()+':'+request['comparison_id']+':'+request['request_id']).encode()).hexdigest()[:32]
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT body,request_hash FROM briefs WHERE id=?', (key,)).fetchone()
            if old:
                self.check_owner(db,'briefs',key)
                if db.execute("SELECT 1 FROM trash WHERE collection='briefs' AND id=?",(key,)).fetchone():
                    raise APIError('record_in_trash','Restore this brief before reusing the request.',409)
                if old[1] != fingerprint:
                    raise APIError('idempotency_conflict', 'This request ID was used for different brief content.', 409)
                return json.loads(old[0])
            result = {**snapshot, 'id': key, 'saved_at': now(), 'immutable': True}
            db.execute('INSERT INTO briefs VALUES (?,?,?)', (key, json.dumps(result), fingerprint))
            self.own(db,'briefs',key)
        return result

    def trash_record(self,table,key,restore=False):
        if table not in ('workspaces','briefs'):raise APIError('invalid_collection','Only workspaces and briefs support trash.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.check_owner(db,table,key)
            if not db.execute(f'SELECT 1 FROM {table} WHERE id=?',(key,)).fetchone():raise APIError('not_found','Record not found.',404)
            if restore:db.execute('DELETE FROM trash WHERE collection=? AND id=?',(table,key))
            else:db.execute('INSERT OR IGNORE INTO trash VALUES (?,?,?)',(table,key,now()))
        return {'id':key,'collection':table,'status':'restored' if restore else 'trashed','retention':'Retained locally until an operator performs a documented permanent purge.'}

    def records(self):
        result=[]
        with self.connect() as db:
            for table in ('workspaces','briefs'):
                rows=db.execute(f'''SELECT r.id,r.body,t.deleted_at FROM {table} r
                    LEFT JOIN owners o ON o.collection=? AND o.id=r.id
                    LEFT JOIN trash t ON t.collection=? AND t.id=r.id
                    WHERE coalesce(o.owner,'local')=? ORDER BY r.rowid DESC LIMIT 200''',(table,table,actor.get())).fetchall()
                for key,body,deleted in rows:
                    data=json.loads(body)
                    result.append({'id':key,'collection':table,'deleted_at':deleted,'updated_at':data.get('updated_at',data.get('saved_at'))})
        return result
