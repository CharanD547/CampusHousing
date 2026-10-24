"""Refresh public VT building locations and BT timetable, retaining provenance locally."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import csv
import io
import json
from pathlib import Path
import sqlite3
import zipfile

import httpx

ROOT = Path(__file__).resolve().parents[2]
BUILDINGS = 'https://arcgis-central.gis.vt.edu/arcgis/rest/services/facilities/BasemapWithBuildings/FeatureServer/1'
GTFS = 'https://www.bt4uclassic.org/gtfs/google_transit.zip'


def building_records(payload, observed_at):
    if payload.get('error') or payload.get('exceededTransferLimit') or not payload.get('features'):
        raise ValueError('Incomplete building response; do not replace the catalog.')
    selected = []
    for feature in payload['features']:
        a = feature['attributes']
        number, name = str(a.get('bldg_num') or '').strip(), str(a.get('name') or '').strip()
        lat, lon = a.get('latitude'), a.get('longitude')
        if not name or number in ('', '<Null>') or a.get('status') != 'Existing Conditions':
            continue
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        # Explicit central Blacksburg scope; remote farms/campuses aren't classroom destinations.
        if not 37.215 <= lat <= 37.245 or not -80.445 <= lon <= -80.410:
            continue
        selected.append(dict(id='vt-' + number.lower(), label=name, building_number=number,
                             lat=lat, lon=lon, use=a.get('bldg_use'), verified=True,
                             verification_scope='Name, number and coordinate fields observed in official public GIS; classroom access and entrances not verified.',
                             coordinate_basis='official_gis_building_location', observed_at=observed_at,
                             source=BUILDINGS + '/query?f=json&where=objectid%3D' + str(int(a['objectid'])) + '&outFields=*&returnGeometry=false'))
    counts = Counter(b['id'] for b in selected)
    selected = [b for b in selected if counts[b['id']] == 1]
    if len(selected) < 20:
        raise ValueError('Insufficient unambiguous building identifiers; retain old catalog.')
    return sorted(selected, key=lambda b: (b['label'].casefold(), b['id']))


def main():
    observed = datetime.now(timezone.utc).isoformat()
    folder = ROOT / 'var'
    folder.mkdir(exist_ok=True)
    with httpx.Client(timeout=45, follow_redirects=False, headers={'User-Agent': 'RoomwiseResearch/1.0'}) as client:
        response = client.get(BUILDINGS + '/query', params=dict(f='json', where='1=1',
            outFields='objectid,name,bldg_num,status,bldg_use,latitude,longitude', returnGeometry='false', orderByFields='objectid'))
        response.raise_for_status()
        records = building_records(response.json(), observed)
        (folder / 'vt-buildings.source.json').write_bytes(response.content)
        campus = dict(campuses=[dict(id='vt', name='Virginia Tech', timezone='America/New_York',
            data_status='official_gis_building_locations', buildings=records,
            limitation='Central Blacksburg named existing buildings only. Building locations are not verified entrances, classroom inventories, accessible paths, or indoor journey times.')])
        temporary = ROOT / 'data/campuses.json.tmp'
        temporary.write_text(json.dumps(campus, indent=2) + '\n', encoding='utf-8')
        temporary.replace(ROOT / 'data/campuses.json')
        feed = client.get(GTFS)
        feed.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(feed.content)) as archive:
            required = ['feed_info', 'stops', 'routes', 'trips', 'stop_times', 'calendar_dates']
            tables = {name: list(csv.DictReader(io.TextIOWrapper(archive.open(name + '.txt'), encoding='utf-8-sig'))) for name in required}
        if not tables['feed_info'] or not tables['stops'] or not tables['stop_times']:
            raise ValueError('Incomplete timetable; retain old feed.')
        temporary = ROOT / 'data/bt-gtfs.zip.tmp'
        temporary.write_bytes(feed.content)
        temporary.replace(ROOT / 'data/bt-gtfs.zip')
    report = dict(observed_at=observed, buildings=len(records), source_features=len(response.json()['features']),
                  building_source=BUILDINGS, building_sha256=sha256(response.content).hexdigest(),
                  transit_source=GTFS, transit_sha256=sha256(feed.content).hexdigest(),
                  transit_feed_info=tables['feed_info'], transit_counts={k: len(v) for k,v in tables.items()},
                  routing_ready=False, limitation='A timetable and building points do not establish door-to-class routing.')
    with sqlite3.connect(folder / 'public-data.sqlite3') as db:
        db.execute('CREATE TABLE IF NOT EXISTS buildings (id TEXT PRIMARY KEY, record_json TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS collection_reports (observed_at TEXT PRIMARY KEY, report_json TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS transit_stops (id TEXT PRIMARY KEY, name TEXT, latitude REAL, longitude REAL, record_json TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS transit_routes (id TEXT PRIMARY KEY, short_name TEXT, long_name TEXT, record_json TEXT NOT NULL)')
        # Replace current inventory as a transaction so removed buildings cannot silently linger.
        db.execute('DELETE FROM buildings')
        db.executemany('INSERT INTO buildings VALUES (?,?)', [(b['id'], json.dumps(b)) for b in records])
        db.execute('DELETE FROM transit_stops')
        db.executemany('INSERT INTO transit_stops VALUES (?,?,?,?,?)',[(s['stop_id'],s['stop_name'],float(s['stop_lat']),float(s['stop_lon']),json.dumps(s)) for s in tables['stops']])
        db.execute('DELETE FROM transit_routes')
        db.executemany('INSERT INTO transit_routes VALUES (?,?,?,?)',[(r['route_id'],r['route_short_name'],r['route_long_name'],json.dumps(r)) for r in tables['routes']])
        db.execute('INSERT INTO collection_reports VALUES (?,?)', (observed, json.dumps(report)))
    (folder / 'vt-public-data.collection.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
