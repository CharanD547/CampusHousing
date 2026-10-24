"""Optional local accounts. No email verification, recovery or cloud identity claims."""
from contextvars import ContextVar
from hashlib import pbkdf2_hmac, sha256
import hmac
import secrets
import sqlite3
import time
import uuid
from roomwise.api.errors import APIError

actor=ContextVar('roomwise_actor',default='local')


class Accounts:
    def __init__(self,directory):
        self.path=directory/'accounts.sqlite3'
        with sqlite3.connect(self.path) as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT UNIQUE,salt TEXT,password TEXT);
                CREATE TABLE IF NOT EXISTS sessions(digest TEXT PRIMARY KEY,owner TEXT,expires REAL);
                CREATE TABLE IF NOT EXISTS attempts(ip TEXT,created REAL);''')

    def authenticate(self,username,password,ip,register=False):
        username=username.strip().lower()
        with sqlite3.connect(self.path,timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM attempts WHERE created<?',(time.time()-3600,))
            count=db.execute('SELECT count(*) FROM attempts WHERE ip=?',(ip,)).fetchone()[0]
            total=db.execute('SELECT count(*) FROM attempts').fetchone()[0]
            if count>=30 or total>=300:raise APIError('auth_rate_limit','Too many account attempts. Try later.',429)
            db.execute('INSERT INTO attempts VALUES (?,?)',(ip,time.time()))
        with sqlite3.connect(self.path,timeout=10) as db:
            if register:
                salt=secrets.token_hex(16);owner=uuid.uuid4().hex
                digest=pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
                try:db.execute('INSERT INTO users VALUES (?,?,?,?)',(owner,username,salt,digest))
                except sqlite3.IntegrityError:raise APIError('account_unavailable','This account name is unavailable.',409)
            else:
                row=db.execute('SELECT id,salt,password FROM users WHERE username=?',(username,)).fetchone()
                salt=row[1] if row else '00'*16
                digest=pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
                if not row or not hmac.compare_digest(digest,row[2]):raise APIError('invalid_login','Account name or password is incorrect.',401)
                owner=row[0]
            token=secrets.token_urlsafe(32)
            db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
            db.execute('INSERT INTO sessions VALUES (?,?,?)',(sha256(token.encode()).hexdigest(),owner,time.time()+86400))
        return owner,token

    def owner(self,token):
        if not token or len(token)>200:return None
        with sqlite3.connect(self.path) as db:
            row=db.execute('SELECT owner FROM sessions WHERE digest=? AND expires>?',(sha256(token.encode()).hexdigest(),time.time())).fetchone()
        return row[0] if row else None

    def logout(self,token):
        with sqlite3.connect(self.path) as db:db.execute('DELETE FROM sessions WHERE digest=?',(sha256(token.encode()).hexdigest(),))
