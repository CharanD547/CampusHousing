"""Persistent attempt caps for chargeable Maps web-service calls. No provider content is cached."""
import sqlite3
from roomwise.config import now


class ProviderBudget:
    def __init__(self,path,limit,reserve_places=0):
        self.path,self.limit=path,limit
        self.reserve_places=max(0,min(limit,reserve_places))
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS attempts (operation TEXT, created_at TEXT)')

    def take(self,operation):
        with sqlite3.connect(self.path,timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            used=db.execute('SELECT count(*) FROM attempts WHERE substr(created_at,1,10)=?',(now()[:10],)).fetchone()[0]
            if used>=self.limit:return False
            if operation=='routes' and self.reserve_places:
                routes=db.execute("SELECT count(*) FROM attempts WHERE operation='routes' AND substr(created_at,1,10)=?",(now()[:10],)).fetchone()[0]
                if routes>=self.limit-self.reserve_places:return False
            db.execute('INSERT INTO attempts VALUES (?,?)',(operation,now()))
            return True
