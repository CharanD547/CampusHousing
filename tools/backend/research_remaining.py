"""Capture reviewed public-source research separately from authoritative live prices."""
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from roomwise.adapters.sources import fetch
from roomwise.config import now


def main():
    folder=ROOT/'var';folder.mkdir(exist_ok=True)
    observations=json.loads((ROOT/'data/housing-research-observations.json').read_text(encoding='utf-8'))
    urls=[o['url'] for o in observations['observations'] if not o['url'].endswith('.pdf')]
    urls+=['https://www.offcampusreview.com/terms-conditions','https://graduateschool.vt.edu/student-services/housing.html']
    results=[]
    with sqlite3.connect(folder/'public-data.sqlite3') as db:
        db.execute('CREATE TABLE IF NOT EXISTS research_observations (id TEXT PRIMARY KEY, record_json TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS research_sources (url TEXT PRIMARY KEY, observed_at TEXT, status TEXT, content_sha256 TEXT, text TEXT, limitation TEXT)')
        for observation in observations['observations']:
            db.execute('INSERT OR REPLACE INTO research_observations VALUES (?,?)',(observation['id'],json.dumps(observation)))
        for url in urls:
            time.sleep(.6)
            try:
                record=fetch({'url':url})
                values=(url,record['retrieved_at'],'retrieved',record['sha256'],record['text'],'Research only; no catalog price mutation.')
            except Exception as exc:
                values=(url,now(),'unavailable',None,None,str(exc)[:350])
            db.execute('INSERT OR REPLACE INTO research_sources VALUES (?,?,?,?,?,?)',values)
            results.append(dict(url=url,status=values[2],limitation=values[-1]))
    # School + exact reviewed subject aliases create research candidates, never automatic property assertions.
    aliases={'Foxridge Apartments':'foxridge','Alight':'alight','The union':'union','Terrace View':'terrace'}
    mappings=[]
    review_path=folder/'offcampusreview.sqlite3'
    if review_path.exists():
        with sqlite3.connect(review_path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS property_match_candidates (source_review_id TEXT PRIMARY KEY, canonical_property_id TEXT, status TEXT, limitation TEXT)')
            for subject,property_id in aliases.items():
                rows=db.execute("SELECT source_review_id FROM reviews WHERE school_slug='virginia-tech' AND landlord_name=?",(subject,)).fetchall()
                limitation='Same-school subject alias only; exact property/unit scope requires verification. Alight East/West split is unresolved. Not approved for public or model use.'
                db.executemany('INSERT OR REPLACE INTO property_match_candidates VALUES (?,?,?,?)',[(r[0],property_id,'needs_scope_verification',limitation) for r in rows])
                mappings.append(dict(property_id=property_id,review_count=len(rows),status='needs_scope_verification'))
            policy=next((r for r in results if 'terms-conditions' in r['url']),None)
            if policy and policy['status']=='retrieved':
                with sqlite3.connect(folder/'public-data.sqlite3') as sources:
                    url,observed,status,digest,text,limitation=sources.execute('SELECT * FROM research_sources WHERE url=?',(policy['url'],)).fetchone()
                db.execute('INSERT OR REPLACE INTO source_policies VALUES (?,?,?,?)',(url,observed,digest,'Terms revisited October 24, 2026; displayed update September 1, 2026. Third-party republication/model license not established.'))
    report=dict(observed_at=now(),observations=len(observations['observations']),source_access=results,review_subject_candidates=mappings,
                catalog_changed=False,review_publication_enabled=False)
    (folder/'remaining-research.collection.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
