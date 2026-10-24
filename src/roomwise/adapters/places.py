"""On-demand Places lookup; results are returned without server persistence or review text."""
import httpx
from roomwise.api.errors import APIError

CATEGORIES={'groceries':'supermarket','cafe':'cafe','pharmacy':'pharmacy','library':'library'}


class GooglePlaces:
    def __init__(self,settings,budget,transport=None):self.settings,self.budget,self.transport=settings,budget,transport

    def nearby(self,prop,category):
        if category not in CATEGORIES:raise APIError('invalid_category','Choose groceries, cafe, pharmacy or library.')
        if not self.settings.places_enabled or not self.settings.places_api_key:
            return {'status':'unavailable','places':[],'reason':'Nearby search is disabled or unconfigured.'}
        if not self.budget.take('places'):return {'status':'unavailable','places':[],'reason':'Daily Maps web-service request limit reached.'}
        try:
            with httpx.Client(timeout=8,transport=self.transport,follow_redirects=False) as client:
                response=client.post('https://places.googleapis.com/v1/places:searchNearby',
                    headers={'X-Goog-Api-Key':self.settings.places_api_key,
                             'X-Goog-FieldMask':'places.id,places.displayName,places.formattedAddress,places.googleMapsUri,places.attributions'},
                    json={'includedTypes':[CATEGORIES[category]],'maxResultCount':5,'rankPreference':'DISTANCE',
                          'locationRestriction':{'circle':{'center':{'latitude':prop['lat'],'longitude':prop['lon']},'radius':2500}}})
                response.raise_for_status();data=response.json()
            return {'status':'available','provider':'Google Maps','places':[{'id':p['id'],'name':p.get('displayName',{}).get('text','Place'),
                'address':p.get('formattedAddress'),'url':p.get('googleMapsUri'),'attributions':p.get('attributions',[])} for p in data.get('places',[])],
                'reason':'Nearby search within 2.5 km, ranked by distance. Not a travel-time estimate.',
                'attribution':'Google Maps','storage_scope':'Live response only; excluded from saved briefs and model training.'}
        except Exception:
            return {'status':'unavailable','places':[],'reason':'Google Places could not return a supported result. Check access, billing and quota.'}
