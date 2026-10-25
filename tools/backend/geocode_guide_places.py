"""Geocode housing-guide addresses with the public US Census geocoder (no API key).

Writes data/housing-guide-geocodes.json: one approximate street-address point per guide place,
the address that matched, and which address segment was used. Multi-address entries use the
first segment that matches. Points are representative addresses, not unit entrances.
"""
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
import httpx

ROOT = Path(__file__).resolve().parents[2]
CENSUS = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress'
NOMINATIM = 'https://nominatim.openstreetmap.org/search'
AGENT = {'User-Agent': 'RoomwiseResearch/0.1 (student housing research; contact via repository)'}
SUFFIX = {'rd', 'road', 'dr', 'drive', 'st', 'street', 'ln', 'lane', 'ct', 'court', 'cir', 'circle', 'blvd', 'way', 'ave', 'ter', 'terrace', 'xing', 'ne', 'nw', 'se', 'sw', 'n', 's', 'e', 'w'}


def candidates(address):
    """Single street addresses to try, in order, from a guide address field."""
    out = []
    for part in re.split(r';|\s/\s|\(|\)', address):
        part = part.strip(' ,')
        if not re.search(r'\d', part): continue
        part = re.sub(r'(\d+)[A-Z]?\s*[–-]\s*\d+[A-Z]?', r'\1', part)          # 300–321 Edge Way -> 300 Edge Way
        part = re.sub(r'^(\d+)[A-Z](?=\s)', r'\1', part)                        # 1203J University Ter -> 1203 ...
        part = re.sub(r'\b[Uu]nit\s*\S+', '', part)
        m = re.match(r'^((?:\d+[A-Z]?,\s*)+)(\d+.*)$', part)                    # 202, 208, 216 Pheasant Run Dr
        if m:
            street = re.sub(r'^\d+[A-Z]?\s*', '', m.group(2))
            part = m.group(1).split(',')[0].strip() + ' ' + street
        for piece in re.split(r'\s&\s|,\s(?=\d)', part):
            piece = piece.strip(' ,')
            if re.match(r'^\d', piece): out.append(piece)
    return list(dict.fromkeys(out))


def street_words(text):
    return {w for w in re.findall(r'[a-z]+', text.lower()) if w not in SUFFIX}


def same_street(query, matched):
    # Guard against near-misses such as "344 Red Maple Dr" matching "344 Maple Ln".
    q, m = street_words(query), street_words(matched.split(',')[0])
    return bool(q) and q <= m


def nominatim(text):
    response = httpx.get(NOMINATIM, params={'q': text, 'format': 'jsonv2', 'limit': 1, 'countrycodes': 'us',
                                            'viewbox': '-80.50,37.28,-80.35,37.18', 'bounded': 1}, headers=AGENT, timeout=20)
    response.raise_for_status()
    rows = response.json()
    return rows[0] if rows else None


def geocode(street):
    query = urlencode({'address': f'{street}, Blacksburg, VA', 'benchmark': 'Public_AR_Current', 'format': 'json'})
    response = httpx.get(f'{CENSUS}?{query}', timeout=20)
    response.raise_for_status()
    matches = response.json()['result']['addressMatches']
    return matches[0] if matches else None


def main():
    guide = json.loads((ROOT / 'data/housing-guide.json').read_text(encoding='utf-8'))
    out = {'format': 'roomwise-guide-geocodes-v1', 'source': CENSUS, 'checked_at': datetime.now(timezone.utc).isoformat(), 'places': {}}
    for entry in guide['communities']:
        if entry.get('catalog_property_id'): continue
        result = None
        for street in candidates(entry['address']):
            time.sleep(0.3)
            try: match = geocode(street)
            except Exception: match = None
            if match and same_street(street, match['matchedAddress']):
                result = dict(lat=round(match['coordinates']['y'], 7), lon=round(match['coordinates']['x'], 7), query=street,
                              matched_address=match['matchedAddress'], basis='census_street_address')
                break
        if not result:
            # OpenStreetMap fallback: the street address, then the community name.
            for text in [f'{c}, Blacksburg, VA' for c in candidates(entry['address'])] + [f"{entry['name'].split('(')[0].strip()}, Blacksburg, VA"]:
                time.sleep(1.1)  # Nominatim usage policy: at most one request per second
                try: row = nominatim(text)
                except Exception: row = None
                if row:
                    result = dict(lat=round(float(row['lat']), 7), lon=round(float(row['lon']), 7), query=text,
                                  matched_address=row.get('display_name', '')[:160], basis='openstreetmap_nominatim')
                    break
        out['places'][entry['id']] = result or dict(unresolved=entry['address'])
        print(entry['id'][:40].ljust(41), (result or {}).get('matched_address', 'UNRESOLVED: ' + entry['address'][:50]))
    (ROOT / 'data/housing-guide-geocodes.json').write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
