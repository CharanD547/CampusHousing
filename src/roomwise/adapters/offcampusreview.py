"""Collect public review records served in page props; no login or hidden API access."""
import asyncio
from collections import deque
import hashlib
from html.parser import HTMLParser
import json
import re
import time
from urllib.parse import urljoin,urlsplit,urlunsplit
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET
import httpx
from roomwise.config import now

BASE='https://www.offcampusreview.com'
AGENT='RoomwiseResearch/1.0'


class Links(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            href=dict(attrs).get('href')
            if href:self.urls.append(href)


def public_url(url):
    parsed=urlsplit(urljoin(BASE,url))
    if parsed.scheme!='https' or parsed.netloc!='www.offcampusreview.com' or parsed.username or parsed.password:return None
    if parsed.path not in ('','/','/schools') and not re.match(r'^/(school/|landlord/|listings/)',parsed.path):return None
    if parsed.path.startswith('/landlord/') and parsed.path.split('/')[2] in ('dashboard','analytics','billing','documents','inquiries','profile','properties','reputation','reviews','settings','onboarding'):return None
    return urlunsplit((parsed.scheme,parsed.netloc,parsed.path or '/',parsed.query,''))


def flight_records(html):
    # Decode JSON only. Never eval/execute page scripts or interpret source text as instructions.
    chunks=[]
    for match in re.finditer(r'self\.__next_f\.push\((.*?)\)</script>',html,re.S):
        try:
            item=json.loads(match.group(1))
            if len(item)>1 and isinstance(item[1],str):chunks.append(item[1])
        except (ValueError,TypeError):continue
    # Flight T records are byte-length framed, not newline framed. Long reviews can
    # contain newlines and run directly into the following JSON record.
    stream=''.join(chunks).encode('utf-8');position=0;records=[];texts={};decoder=json.JSONDecoder()
    while position<len(stream):
        if stream[position:position+1] in (b'\n',b'\r'):
            position+=1;continue
        header=re.match(rb'([0-9a-fA-F]+):',stream[position:])
        if not header:
            next_line=stream.find(b'\n',position)
            if next_line<0:break
            position=next_line+1;continue
        key=header.group(1).decode();position+=header.end()
        text_header=re.match(rb'T([0-9a-fA-F]+),',stream[position:])
        if text_header:
            length=int(text_header.group(1),16);position+=text_header.end()
            texts[key]=stream[position:position+length].decode('utf-8',errors='replace');position+=length;continue
        # Imports/debug/error tags are not review payloads.
        while position<len(stream) and stream[position:position+1] in (b'I',b'D',b'E',b'J'):position+=1
        try:
            raw=stream[position:].decode('utf-8')
            record,end=decoder.raw_decode(raw)
            records.append(record);position+=len(raw[:end].encode('utf-8'))
        except (ValueError,UnicodeDecodeError):
            next_line=stream.find(b'\n',position)
            if next_line<0:break
            position=next_line+1
    def resolve(value):
        if isinstance(value,str) and value.startswith('$') and value[1:] in texts:return texts[value[1:]]
        if isinstance(value,dict):return {k:resolve(v) for k,v in value.items()}
        if isinstance(value,list):return [resolve(v) for v in value]
        return value
    return [resolve(x) for x in records]


def listing_contexts(html):
    contexts={}
    def walk(value):
        if isinstance(value,dict):
            if 'reviewsPreview' in value and 'landlord' in value and 'id' in value:
                contexts[value['id']]=value
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    for record in flight_records(html):walk(record)
    return list(contexts.values())


def page_records(html):
    records=flight_records(html)
    found={};advertised=[]
    def walk(value):
        if isinstance(value,dict):
            if 'reviewText' in value and (isinstance(value['reviewText'],str) or value['reviewText'] is None):
                key=str(value.get('id') or hashlib.sha256(str(value.get('reviewText') or '').encode()).hexdigest())
                found[key]=value
            if isinstance(value.get('reviews'),list) and isinstance(value.get('reviewCount'),int):
                advertised.append(value['reviewCount'])
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    for record in records:walk(record)
    parser=Links();parser.feed(html)
    return list(found.values()),max(advertised) if advertised else None,parser.urls


class PublicReviewCollector:
    def __init__(self,repository, *, interval=.5,max_pages=1500):
        self.repository=repository;self.interval=max(interval,.5);self.max_pages=max_pages
        self.policy=RobotFileParser();self.queue=deque();self.seen=set();self.next_request=0;self.requests=0
        self.stop_reason=None

    async def fetch(self,client,url):
        for redirect in range(4):
            if not self.policy.can_fetch(AGENT,url):raise ValueError('robots_disallowed')
            delay=self.next_request-time.monotonic()
            if delay>0:await asyncio.sleep(delay)
            self.next_request=time.monotonic()+self.interval;self.requests+=1
            async with client.stream('GET',url) as response:
                if response.status_code==429:
                    self.stop_reason='rate_limited';raise ValueError('rate_limited_collection_stopped')
                if response.status_code in (301,302,303,307,308):
                    target=public_url(urljoin(url,response.headers.get('location','')))
                    if not target:raise ValueError('redirect_outside_public_scope')
                    url=target;continue
                if response.status_code!=200:return response.status_code,'',url
                chunks=[];total=0
                async for chunk in response.aiter_bytes():
                    total+=len(chunk)
                    if total>4_000_000:raise ValueError('page_size_limit')
                    chunks.append(chunk)
                return response.status_code,b''.join(chunks).decode('utf-8',errors='replace'),url
        raise ValueError('redirect_limit')

    def enqueue(self,url):
        url=public_url(url)
        if url and url not in self.seen:
            self.seen.add(url);self.queue.append(url)

    async def run(self):
        run_id=now()
        with self.repository.connect() as db:db.execute('INSERT INTO collection_runs VALUES (?,?,?,?)',(run_id,run_id,'running','{}'))
        async with httpx.AsyncClient(timeout=25,follow_redirects=False,headers={'User-Agent':AGENT,'Accept':'text/html,application/json,application/xml'}) as client:
            robots=await client.get(BASE+'/robots.txt')
            if robots.status_code!=200:raise ValueError('Cannot verify robots access.')
            self.policy.parse(robots.text.splitlines())
            with self.repository.connect() as db:
                db.execute('INSERT OR REPLACE INTO source_policies VALUES (?,?,?,?)',
                           (BASE+'/robots.txt',now(),hashlib.sha256(robots.content).hexdigest(),robots.text))
                db.execute('INSERT OR REPLACE INTO source_policies VALUES (?,?,?,?)',
                           (BASE+'/terms-conditions',now(),'not_a_license',
                            'Terms reviewed October 24, 2026: contributors retain content ownership; no third-party reuse permission established. Local collection only; no public/API/model use.'))
            # These discovery endpoints are explicitly advertised by the public robots file.
            status,sitemap,_=await self.fetch(client,BASE+'/sitemap.xml')
            if status!=200:raise ValueError('Public sitemap unavailable.')
            urls=[node.text for node in ET.fromstring(sitemap).iter() if node.tag.endswith('}loc') and node.text]
            # VT pages first; global public discovery follows.
            for url in sorted(urls,key=lambda u:('virginia-tech' not in u,u)):self.enqueue(url)
            if self.policy.can_fetch(AGENT,BASE+'/api/universities'):
                status,directory,_=await self.fetch(client,BASE+'/api/universities')
                if status==200:
                    for school in json.loads(directory):
                        slug=school.get('slug')
                        if not slug or not re.fullmatch(r'[a-z0-9-]+',slug):continue
                        with self.repository.connect() as db:
                            db.execute('INSERT OR REPLACE INTO schools VALUES (?,?,?,?)',
                                       (slug,school.get('name'),school.get('totalReviews'),now()))
                        # Scan every advertised campus, including zero-count pages: counts can disagree across the site.
                        self.enqueue(BASE+'/school/'+slug)
            processed=0
            while self.queue and processed<self.max_pages and not self.stop_reason:
                url=self.queue.popleft();error=None;status=0;count=0;advertised=None;digest=None
                try:
                    status,html,final_url=await self.fetch(client,url)
                    if status==200:
                        digest=hashlib.sha256(html.encode()).hexdigest()
                        reviews,advertised,links=page_records(html)
                        for review in reviews:self.repository.upsert(review,final_url)
                        count=len(reviews)
                        for href in links:self.enqueue(urljoin(final_url,href))
                        if advertised is not None and count<advertised:
                            error='review_count_gap'
                    else:error='public_page_unavailable'
                except (ValueError,httpx.HTTPError) as exc:
                    error=str(exc) if isinstance(exc,ValueError) else type(exc).__name__
                with self.repository.connect() as db:
                    db.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?)',(url,status,count,advertised,digest,now(),error))
                processed+=1
                if processed%25==0:print(json.dumps({'pages':processed,'pending':len(self.queue),'reviews':self.repository.summary()['unique_reviews']}),flush=True)
            summary=self.repository.summary()
            summary.update(run_id=run_id,pages_this_run=processed,http_requests=self.requests,pending_pages=len(self.queue),
                           stop_reason=self.stop_reason or ('page_limit' if self.queue else 'public_frontier_exhausted'))
        with self.repository.connect() as db:
            db.execute('UPDATE collection_runs SET status=?,summary=? WHERE id=?',
                       ('complete' if not self.queue and not self.stop_reason else 'partial',json.dumps(summary),run_id))
        return summary
