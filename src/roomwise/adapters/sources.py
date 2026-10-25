"""Bounded official-source retrieval. No user supplied URLs or redirects."""
import hashlib
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import httpx
from roomwise.config import now

AGENT = 'RoomwiseResearch/0.1'


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','noscript'): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script','style','noscript'): self.hidden=max(0,self.hidden-1)
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)


def fetch(source, *, include_html=False):
    if source.get('refresh_policy') == 'manual_only':
        raise ValueError('This source requires manual review on the official website.')
    url = source['url']; parsed = urlsplit(url)
    if parsed.scheme != 'https': raise ValueError('Only approved HTTPS sources can be refreshed.')
    # URLs come exclusively from the reviewed catalog, never model output or user input.
    with httpx.Client(timeout=12, follow_redirects=False, headers={'User-Agent':AGENT}) as client:
        robots = client.get(f'https://{parsed.netloc}/robots.txt')
        if robots.status_code == 200:
            policy=RobotFileParser(); policy.parse(robots.text.splitlines())
            if not policy.can_fetch(AGENT,url): raise ValueError('Automated access is restricted; review the official source manually.')
        elif robots.status_code not in (404,410):
            raise ValueError('Could not verify automated access. Review the source manually.')
        with client.stream('GET',url) as response:
            response.raise_for_status()
            if 'text/html' not in response.headers.get('content-type',''): raise ValueError('Source is not an HTML page.')
            chunks=[]; total=0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > 2_000_000: raise ValueError('Source exceeds the download limit.')
                chunks.append(chunk)
    html=b''.join(chunks).decode('utf-8',errors='replace')
    parser=TextParser(); parser.feed(html)
    text=re.sub(r'\s+',' ',' '.join(parser.parts)).strip()[:80_000]
    if len(text)<100: raise ValueError('Source contained too little readable evidence.')
    result={'text':text,'sha256':hashlib.sha256(text.encode()).hexdigest(),'retrieved_at':now()}
    if include_html:result['html']=html
    return result
