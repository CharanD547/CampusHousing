"""Recover length-framed public pages and listing 'Show all' snippets; no private APIs."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode,urlsplit
import httpx

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from roomwise.adapters.offcampusreview import AGENT,BASE,PublicReviewCollector,listing_contexts,page_records
from roomwise.config import now
from roomwise.repositories.reviews import ReviewRepository


async def supplement(repo):
    collector=PublicReviewCollector(repo)
    with repo.connect() as db:
        retry=[r[0] for r in db.execute("SELECT url FROM pages WHERE (url LIKE '%/landlord/%' AND review_count=0) OR (url LIKE '%/school/%' AND review_count>0)")]
        for slug, in db.execute('SELECT slug FROM schools WHERE reported_count>0'):
            if BASE+'/school/'+slug not in retry:retry.append(BASE+'/school/'+slug)
        listing_urls=list(dict.fromkeys(r[0].split('?')[0] for r in db.execute("SELECT url FROM pages WHERE url LIKE '%/listings/%'")))
    run_id='supplement-'+now()
    with repo.connect() as db:db.execute('INSERT INTO collection_runs VALUES (?,?,?,?)',(run_id,now(),'running','{}'))
    processed_listing_ids=set()
    with repo.connect() as db:
        db.execute("UPDATE collection_runs SET status='interrupted' WHERE status='running' AND id!=?",(run_id,))
        completed_apis={r[0] for r in db.execute("SELECT url FROM pages WHERE url LIKE '%/api/reviews/for-listing%' AND status=200")}
    async with httpx.AsyncClient(timeout=25,follow_redirects=False,headers={'User-Agent':AGENT}) as client:
        robots=await client.get(BASE+'/robots.txt');robots.raise_for_status();collector.policy.parse(robots.text.splitlines())
        for index,url in enumerate(retry+listing_urls):
            status=0;error=None;count=0;advertised=None;digest=None
            try:
                status,html,final_url=await collector.fetch(client,url)
                if status!=200:raise ValueError('public_page_unavailable')
                digest=hashlib.sha256(html.encode()).hexdigest()
                rows,advertised,_=page_records(html)
                for row in rows:repo.upsert(row,final_url)
                count=len(rows)
                for listing in listing_contexts(html):
                    if listing['id'] in processed_listing_ids:continue
                    processed_listing_ids.add(listing['id'])
                    landlord=listing.get('landlord') or {};school=listing.get('school')
                    school_name=school.get('name') if isinstance(school,dict) else school
                    for scope in ('landlord','property'):
                        # Same read-only endpoint and scopes used by the site's public listing interface.
                        endpoint=BASE+'/api/reviews/for-listing?'+urlencode({'listingId':listing['id'],'scope':scope})
                        if endpoint in completed_apis:continue
                        api_status,payload,_=await collector.fetch(client,endpoint)
                        if api_status!=200:continue
                        snippets=json.loads(payload).get('reviews',[])
                        for snippet in snippets:
                            repo.upsert({**snippet,'reviewText':snippet.get('snippet',''),'text_scope':'public_snippet',
                                         'universitySlug':listing.get('schoolSlug') or landlord.get('universitySlug','unknown'),
                                         'universityName':school_name,'landlordName':landlord.get('name'),
                                         'propertyId':(listing.get('property') or {}).get('id') if scope=='property' else None},endpoint)
                        with repo.connect() as db:
                            db.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?)',
                                       (endpoint,api_status,len(snippets),None,hashlib.sha256(payload.encode()).hexdigest(),now(),None))
                if advertised is not None and count<advertised:error='review_count_gap'
            except (ValueError,httpx.HTTPError) as exc:error=str(exc) if isinstance(exc,ValueError) else type(exc).__name__
            with repo.connect() as db:db.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?)',(url,status,count,advertised,digest,now(),error))
            if collector.stop_reason:break
            if (index+1)%10==0:print(json.dumps({'supplement_pages':index+1,'reviews':repo.summary()['unique_reviews']}),flush=True)
    result=repo.summary();result.update(run_id=run_id,stop_reason=collector.stop_reason or 'supplement_complete')
    with repo.connect() as db:db.execute('UPDATE collection_runs SET status=?,summary=? WHERE id=?',('partial' if collector.stop_reason else 'complete',json.dumps(result),run_id))
    repo.path.with_suffix('.collection.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':asyncio.run(supplement(ReviewRepository(ROOT/'var/offcampusreview.sqlite3')))
