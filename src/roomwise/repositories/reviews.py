"""Local public-review research collection, isolated from published/AI evidence."""
import hashlib
import json
from pathlib import Path
import sqlite3
from roomwise.config import now


class ReviewRepository:
    def __init__(self, path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS collection_runs(id TEXT PRIMARY KEY,started_at TEXT,status TEXT,summary TEXT);
            CREATE TABLE IF NOT EXISTS source_policies(url TEXT PRIMARY KEY,retrieved_at TEXT,sha256 TEXT,notes TEXT);
            CREATE TABLE IF NOT EXISTS pages(url TEXT PRIMARY KEY,status INTEGER,review_count INTEGER,advertised_count INTEGER,sha256 TEXT,fetched_at TEXT,error TEXT);
            CREATE TABLE IF NOT EXISTS schools(slug TEXT PRIMARY KEY,name TEXT,reported_count INTEGER,observed_at TEXT);
            CREATE TABLE IF NOT EXISTS reviews(
              source_review_id TEXT PRIMARY KEY,school_slug TEXT,school_name TEXT,landlord_name TEXT,
              source_property_id TEXT,rating REAL,review_text TEXT,published_at TEXT,lease_period TEXT,
              ratings_json TEXT,tags_json TEXT,would_rent_again INTEGER,felt_safe INTEGER,
              content_sha256 TEXT,first_seen_at TEXT,last_seen_at TEXT,
              verification_status TEXT NOT NULL DEFAULT 'subjective_not_independently_verified',
              reuse_permission TEXT NOT NULL DEFAULT 'not_established',
              collection_scope TEXT NOT NULL DEFAULT 'user_requested_local_research');
            CREATE TABLE IF NOT EXISTS review_pages(source_review_id TEXT,url TEXT,PRIMARY KEY(source_review_id,url));
            CREATE INDEX IF NOT EXISTS review_school ON reviews(school_slug);
            ''')
            if 'text_scope' not in {r[1] for r in db.execute('PRAGMA table_info(reviews)')}:
                db.execute("ALTER TABLE reviews ADD COLUMN text_scope TEXT NOT NULL DEFAULT 'full_review_text'")

    def connect(self):return sqlite3.connect(self.path,timeout=15)

    def upsert(self, review, url):
        # Deliberate whitelist: never retain emails, accounts, author names, precise unit addresses, or raw page HTML.
        text=str(review.get('reviewText') or '').strip()
        if not text and (not review.get('id') or not isinstance(review.get('rating'),(int,float))):return False
        school=review.get('universitySlug','unknown')
        key=str(review.get('id') or hashlib.sha256((school+text+str(review.get('date'))).encode()).hexdigest())
        digest=hashlib.sha256(text.encode()).hexdigest();stamp=now()
        incoming_scope=review.get('text_scope','full_review_text')
        scope=incoming_scope if text else 'rating_only'
        ratings={k:review.get(k) for k in ('responsiveness','condition','fairness')}
        values=(key,school,review.get('universityName'),review.get('landlordName'),str(review.get('propertyId') or ''),
                review.get('rating'),text,review.get('date'),review.get('leaseDuration'),json.dumps(ratings),
                json.dumps(review.get('tags') or []),review.get('wouldRentAgain'),review.get('feltSafe'),digest,stamp,stamp)
        with self.connect() as db:
            exists=db.execute('SELECT text_scope FROM reviews WHERE source_review_id=?',(key,)).fetchone()
            if exists and incoming_scope=='public_snippet' and exists[0]=='full_review_text':
                db.execute('INSERT OR IGNORE INTO review_pages VALUES (?,?)',(key,url))
                return False
            db.execute('''INSERT INTO reviews(source_review_id,school_slug,school_name,landlord_name,source_property_id,
              rating,review_text,published_at,lease_period,ratings_json,tags_json,would_rent_again,felt_safe,
              content_sha256,first_seen_at,last_seen_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(source_review_id) DO UPDATE SET school_slug=excluded.school_slug,school_name=excluded.school_name,
              landlord_name=excluded.landlord_name,source_property_id=excluded.source_property_id,rating=excluded.rating,
              review_text=excluded.review_text,published_at=excluded.published_at,lease_period=excluded.lease_period,
              ratings_json=excluded.ratings_json,tags_json=excluded.tags_json,would_rent_again=excluded.would_rent_again,
              felt_safe=excluded.felt_safe,content_sha256=excluded.content_sha256,last_seen_at=excluded.last_seen_at''',values)
            db.execute('UPDATE reviews SET text_scope=? WHERE source_review_id=?',(scope,key))
            db.execute('INSERT OR IGNORE INTO review_pages VALUES (?,?)',(key,url))
        return not bool(exists)

    def summary(self):
        with self.connect() as db:
            count=db.execute('SELECT count(*) FROM reviews').fetchone()[0]
            schools=[dict(slug=s,reviews=n) for s,n in db.execute('SELECT school_slug,count(*) FROM reviews GROUP BY school_slug ORDER BY count(*) DESC')]
            pages=db.execute('SELECT count(*) FROM pages').fetchone()[0]
            failed=[dict(url=u,status=s,error=e) for u,s,e in db.execute('SELECT url,status,error FROM pages WHERE status!=200 OR error IS NOT NULL')]
            scopes=dict(db.execute('SELECT text_scope,count(*) FROM reviews GROUP BY text_scope'))
        return dict(unique_reviews=count,schools_with_reviews=len(schools),by_school=schools,pages_recorded=pages,failed_pages=failed,
                    text_coverage=scopes,reuse_permission='not_established',public_api_enabled=False,model_use_enabled=False)
