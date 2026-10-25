"""Persistent UTC daily attempt budget; stores no provider content or keys."""
import sqlite3
from pathlib import Path
from roomwise.config import now


class ProviderBudget:
    def __init__(self, path, limit):
        self.path=Path(path);self.limit=max(0,limit)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS attempts(operation TEXT,created_at TEXT)')

    def take(self, operation):
        with sqlite3.connect(self.path,timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            used=db.execute('SELECT count(*) FROM attempts WHERE substr(created_at,1,10)=?',(now()[:10],)).fetchone()[0]
            if used>=self.limit:return False
            db.execute('INSERT INTO attempts VALUES (?,?)',(operation,now()))
            return True
