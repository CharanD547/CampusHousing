"""Bounded, on-demand OpenStreetMap essentials lookup for the local street map."""
from copy import deepcopy
from math import isfinite
from threading import Lock
import time
import httpx
from roomwise.adapters.places import CATEGORIES,distance_meters
from roomwise.api.errors import APIError
from roomwise.config import now

FILTERS={'groceries':'["shop"~"^(supermarket|convenience|greengrocer)$"]',
 'restaurant':'["amenity"="restaurant"]','gas_station':'["amenity"="fuel"]',
 'cafe':'["amenity"="cafe"]','pharmacy':'["amenity"="pharmacy"]','library':'["amenity"="library"]'}

class OpenStreetMapPlaces:
    def __init__(self,transport=None):
        self.transport=transport
        self.cache={};self.lock=Lock()

    def nearby(self,prop,category,radius=2500):
        if category not in CATEGORIES:raise APIError('invalid_category','Choose a supported nearby category.')
        if radius not in (1000,2500,5000):raise APIError('invalid_radius','Choose a 0.62, 1.55 or 3.11 mile search radius.')
        lat,lon=prop.get('lat'),prop.get('lon')
        if lat is None or lon is None or not isfinite(lat) or not isfinite(lon):
            return {'status':'unavailable','places':[],'reason':'No sourced property point yet. The address-search map remains available.'}
        key=(lat,lon,category,radius)
        with self.lock:
            cached=self.cache.get(key)
            if cached and cached[0]>time.monotonic():return deepcopy(cached[1])
        query=f'[out:json][timeout:15];nwr(around:{radius},{lat},{lon}){FILTERS[category]}["name"];out center tags;'
        try:
            with httpx.Client(timeout=20,transport=self.transport,follow_redirects=False,
                    headers={'User-Agent':'RoomwiseLocal/1.0 (+https://github.com/CharanD547/CampusHousing)'}) as client:
                response=client.get('https://overpass.maprva.org/api/interpreter',params={'data':query})
                response.raise_for_status()
                if len(response.content)>1_000_000:raise ValueError('Nearby response is too large.')
                payload=response.json()
            if payload.get('remark') or not isinstance(payload.get('elements'),list):raise ValueError('Incomplete map response.')
            places=[];seen=set()
            for item in payload['elements']:
                tags=item.get('tags',{});point=item.get('center') or item
                if item.get('type') not in ('node','way','relation') or not tags.get('name'):continue
                location={'latitude':point.get('lat'),'longitude':point.get('lon')}
                if not all(isinstance(x,(int,float)) and isfinite(x) for x in location.values()):continue
                distance=distance_meters(prop,location)
                if distance is None or distance>radius:continue
                identity=(tags['name'].casefold(),round(location['latitude'],4),round(location['longitude'],4))
                if identity in seen:continue
                seen.add(identity)
                address=' '.join(str(tags.get(k,'')) for k in ('addr:housenumber','addr:street','addr:city')).strip()
                places.append({'id':f'osm-{item["type"]}-{item["id"]}','name':tags['name'],
                    'address':address or None,'url':f'https://www.openstreetmap.org/{item["type"]}/{item["id"]}',
                    'location':location,'distance_meters':distance,'attributions':[]})
            places.sort(key=lambda p:p['distance_meters'])
            result={'status':'available','provider':'OpenStreetMap','places':places[:8],
                'property_id':prop.get('id'),'category':category,'radius_meters':radius,'checked_at':now(),
                'reason':f'Mapped places within {radius/1609.344:.2f} miles, ranked by straight-line distance. Community map data may be incomplete; business hours and current operation are unverified.',
                'attribution':'© OpenStreetMap contributors','storage_scope':'Live response only; excluded from saved briefs and model training.'}
            with self.lock:self.cache[key]=(time.monotonic()+300,deepcopy(result))
            return result
        except (httpx.HTTPError,ValueError,KeyError,TypeError):
            return {'status':'unavailable','places':[],'reason':'The nearby map service could not complete this search. Try again or open the address in Google Maps.'}
