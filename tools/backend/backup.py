"""Validated SQLite backups and restoration into a NEW directory only; never copies .env."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sqlite3
from datetime import datetime,timezone


def integrity(path):
    with sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro',uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:raise ValueError('Database integrity check failed: '+path.name)


def backup(source,destination):
    source,destination=Path(source).resolve(),Path(destination).resolve()
    if not source.is_dir():raise ValueError('Data directory does not exist.')
    files=sorted(source.glob('*.sqlite3'))
    if not files:raise ValueError('No databases found.')
    if destination.exists():raise ValueError('Choose a new destination; existing files are never overwritten.')
    destination.mkdir(parents=True,exist_ok=False)
    manifest={'format':'roomwise-sqlite-backup-v1','created_at':datetime.now(timezone.utc).isoformat(),
              'scope':'Individual consistent SQLite snapshots; not a transaction across all databases. Credentials, frontend cache and model weights excluded.','files':[]}
    for path in files:
        if path.is_symlink():raise ValueError('Symlink databases are not supported.')
        target=destination/path.name
        with sqlite3.connect(f'{path.as_uri()}?mode=ro',uri=True) as original,sqlite3.connect(target) as copy:original.backup(copy)
        integrity(target)
        manifest['files'].append({'name':path.name,'sha256':sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size})
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest


def restore(source,destination):
    source,destination=Path(source).resolve(),Path(destination).resolve()
    if destination.exists():raise ValueError('Restore requires a NEW directory; running data is never overwritten.')
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format')!='roomwise-sqlite-backup-v1' or not manifest.get('files'):raise ValueError('Unsupported or empty backup manifest.')
    seen=set()
    for entry in manifest['files']:
        name=entry['name'];path=source/name
        if Path(name).name!=name or '/' in name or '\\' in name or not name.endswith('.sqlite3') or name in seen:raise ValueError('Invalid database path.')
        seen.add(name)
        if path.is_symlink() or path.resolve().parent!=source:raise ValueError('Database must remain within the backup directory.')
        if sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Backup checksum mismatch: '+name)
        integrity(path)
    destination.mkdir(parents=True,exist_ok=False)
    for entry in manifest['files']:shutil.copy2(source/entry['name'],destination/entry['name'])
    return {'status':'restored','databases':len(manifest['files']),'destination':str(destination)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=['backup','restore']);parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    result=(backup if args.operation=='backup' else restore)(args.source,args.destination)
    print(json.dumps(result,indent=2))
