"""Direct scheduled bus examples within the feed's declared validity window."""
import csv
from datetime import date
from functools import lru_cache
import io
import math
import zipfile
from roomwise.config import ROOT


@lru_cache(maxsize=1)
def feed():
    path=ROOT/'data/bt-gtfs.zip'
    if not path.exists(): return None
    with zipfile.ZipFile(path) as archive:
        def rows(name): return list(csv.DictReader(io.TextIOWrapper(archive.open(name),encoding='utf-8-sig')))
        return {name:rows(name+'.txt') for name in ['feed_info','stops','routes','trips','stop_times','calendar_dates']}


def seconds(value):
    h,m,s=map(int,value.split(':')); return h*3600+m*60+s


def distance(a,b):
    lat1,lon1,lat2,lon2=map(math.radians,[a[0],a[1],b[0],b[1]])
    x=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371000*2*math.atan2(math.sqrt(x),math.sqrt(1-x))


def journey(prop,day,arrival):
    day=date.fromisoformat(day)
    if len(arrival)!=5: raise ValueError('Arrival must be HH:MM.')
    target=seconds(arrival+':00')
    hh,mm=map(int,arrival.split(':'))
    if not 0<=hh<=23 or not 0<=mm<=59: raise ValueError('Choose a valid arrival time.')
    data=feed()
    base={'scope':'Current scheduled stop-to-stop example; excludes walks, live delays and future service guarantees.',
          'source_url':'https://www.bt4uclassic.org/gtfs/google_transit.zip','date':day.isoformat(),'arrival_by':arrival,'journeys':[],'nearby_stops':[]}
    if not data: return {**base,'status':'unavailable','message':'Schedule data is unavailable.'}
    info=data['feed_info'][0]
    base['feed']={k:info.get(k) for k in ['feed_version','feed_start_date','feed_end_date']}
    d=day.strftime('%Y%m%d')
    if not info.get('feed_start_date','99999999')<=d<=info.get('feed_end_date','00000000'):
        return {**base,'status':'unavailable','message':'Schedule unavailable for this date. Select a day within the published feed coverage.'}
    if prop.get('lat') is None or prop.get('lon') is None:
        return {**base,'status':'unavailable','message':'Verified property coordinates are unavailable.'}
    nearby=[]
    for stop in data['stops']:
        meters=distance((prop['lat'],prop['lon']),(float(stop['stop_lat']),float(stop['stop_lon'])))
        if meters<=850: nearby.append({**stop,'distance_m':round(meters)})
    nearby=sorted(nearby,key=lambda s:s['distance_m'])[:5]
    base['nearby_stops']=[{'id':s['stop_id'],'name':s['stop_name'],'straight_line_m':s['distance_m'],'lat':float(s['stop_lat']),'lon':float(s['stop_lon'])} for s in nearby]
    starts={s['stop_id']:s for s in nearby}
    campus={s['stop_id']:s for s in data['stops'] if s['stop_name'].startswith(('Maroon Bay','Orange Bay'))}
    active={r['service_id'] for r in data['calendar_dates'] if r['date']==d and r['exception_type']=='1'}
    active-={r['service_id'] for r in data['calendar_dates'] if r['date']==d and r['exception_type']=='2'}
    trips={t['trip_id']:t for t in data['trips'] if t['service_id'] in active}
    routes={r['route_id']:r for r in data['routes']}
    times={}
    for row in data['stop_times']:
        if row['trip_id'] in trips and (row['stop_id'] in starts or row['stop_id'] in campus): times.setdefault(row['trip_id'],[]).append(row)
    found=[]
    for key,rows in times.items():
        for start in rows:
            if start['stop_id'] not in starts or start.get('pickup_type')=='1': continue
            depart=seconds(start['departure_time'])
            for end in rows:
                if end['stop_id'] not in campus or int(end['stop_sequence'])<=int(start['stop_sequence']) or end.get('drop_off_type')=='1': continue
                arrive=seconds(end['arrival_time'])
                if depart<=arrive<=target and target-arrive<=3600:
                    route=routes[trips[key]['route_id']]
                    found.append({'route':route['route_short_name'],'route_name':route['route_long_name'],'from_stop':starts[start['stop_id']]['stop_name'],
                                  'to_stop':campus[end['stop_id']]['stop_name'],'departure':start['departure_time'][:5],'arrival':end['arrival_time'][:5],
                                  'minutes':round((arrive-depart)/60),'distance_to_stop_m':starts[start['stop_id']]['distance_m']})
    found.sort(key=lambda j:(j['arrival'],j['departure']),reverse=True)
    unique=[]; seen=set()
    for trip in found:
        signature=(trip['route'],trip['departure'],trip['arrival'])
        if signature not in seen: unique.append(trip); seen.add(signature)
    return {**base,'status':'available' if unique else 'no_direct_trip','journeys':unique[:3],
            'message':'Direct scheduled trips to the campus transit center.' if unique else 'No supported direct trip found in this search window. Transfers and walking routes are not evaluated.'}
