"""On-demand Places lookup; results are returned without server persistence or review text."""
import httpx
from math import asin, cos, radians, sin, sqrt
from roomwise.api.errors import APIError

CATEGORIES={'groceries':['supermarket','grocery_store'],'restaurant':['restaurant'],
            'gas_station':['gas_station'],'cafe':['cafe'],'pharmacy':['pharmacy'],'library':['library']}


def distance_meters(origin, location):
    if not location: return None
    lat, lon = location.get('latitude'), location.get('longitude')
    if lat is None or lon is None: return None
    a, b = radians(origin['lat']), radians(lat)
    d = sin((b-a)/2)**2 + cos(a)*cos(b)*sin(radians(lon-origin['lon'])/2)**2
    return round(6371000*2*asin(min(1,sqrt(d))))


class GooglePlaces:
    def __init__(self,settings,budget,transport=None):self.settings,self.budget,self.transport=settings,budget,transport

    def nearby(self,prop,category,radius=2500):
        if category not in CATEGORIES:raise APIError('invalid_category','Choose groceries, restaurant, gas_station, cafe, pharmacy or library.')
        if radius not in (1000,2500,5000):raise APIError('invalid_radius','Choose a 1, 2.5 or 5 km search radius.')
        if prop.get('lat') is None or prop.get('lon') is None:
            return {'status':'unavailable','places':[],'reason':'This guide reference has no verified property point. Confirm its address before using nearby search.'}
        if not self.settings.places_enabled or not self.settings.places_api_key:
            return {'status':'unavailable','places':[],'reason':'Nearby search is disabled or unconfigured.'}
        if not self.budget.take('places'):return {'status':'unavailable','places':[],'reason':'Daily Maps web-service request limit reached.'}
        try:
            with httpx.Client(timeout=8,transport=self.transport,follow_redirects=False) as client:
                response=client.post('https://places.googleapis.com/v1/places:searchNearby',
                    headers={'X-Goog-Api-Key':self.settings.places_api_key,
                             'X-Goog-FieldMask':'places.id,places.displayName,places.formattedAddress,places.googleMapsUri,places.location,places.attributions'},
                    json={'includedTypes':CATEGORIES[category],'maxResultCount':8,'rankPreference':'DISTANCE',
                          'locationRestriction':{'circle':{'center':{'latitude':prop['lat'],'longitude':prop['lon']},'radius':radius}}})
                response.raise_for_status();data=response.json()
            return {'status':'available','provider':'Google Maps','places':[{'id':p['id'],'name':p.get('displayName',{}).get('text','Place'),
                'address':p.get('formattedAddress'),'url':p.get('googleMapsUri'),'location':p.get('location'),
                'distance_meters':distance_meters(prop,p.get('location')),'attributions':p.get('attributions',[])} for p in data.get('places',[])],
                'property_id':prop['id'] if 'id' in prop else None,'category':category,'radius_meters':radius,
                'reason':f'Within {radius/1000:g} km, ranked by distance. Distances are straight-line from the approximate property point, not walking or driving routes.',
                'attribution':'Google Maps','storage_scope':'Live response only; excluded from saved briefs and model training.'}
        except Exception:
            return {'status':'unavailable','places':[],'reason':'Google Places could not return a supported result. Check access, billing and quota.'}
