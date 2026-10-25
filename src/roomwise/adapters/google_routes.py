"""Schedule-aware Google route requests with transient results and bounded attempts."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import re
import time
from zoneinfo import ZoneInfo
import httpx
from roomwise.adapters.routing import UnconfiguredRoutingAdapter
from roomwise.repositories.provider_budget import ProviderBudget

# Six properties x two classes x two modes is 24 distinct routes; plans at one property share them.
MAX_CALLS_PER_REQUEST=30


class GoogleRoutesAdapter:
    provider='google_routes'
    def __init__(self,settings,transport=None):
        self.settings,self.transport=settings,transport
        self.budget=ProviderBudget(settings.data_dir/'maps-requests.sqlite3',settings.maps_daily_requests)
        self.memo={};self.calls=0
        self.deadline=time.monotonic()+20

    def for_request(self):return GoogleRoutesAdapter(self.settings,self.transport)

    def estimate(self,candidate,building,commitment,mode,route_date,preferences):
        empty=UnconfiguredRoutingAdapter().estimate(candidate,building,commitment,mode,route_date,preferences)
        empty.update(provider=self.provider,coverage_notes=['Google route estimate unavailable.'],retention='transient')
        buffer=commitment.arrival_buffer_minutes if commitment.arrival_buffer_minutes is not None else preferences.arrival_buffer_minutes
        arrival=datetime.combine(route_date,commitment.arrival_time_local,ZoneInfo('America/New_York'))-timedelta(minutes=buffer)
        empty['context'].update(arrival_by=arrival.isoformat(),destination_basis=building.get('coordinate_basis','unverified'),attribution='Google Maps')
        key=(candidate['property_id'],building['id'],mode,arrival.isoformat())
        if key in self.memo:return {**deepcopy(self.memo[key]),'candidate_id':candidate['id'],'commitment_id':commitment.id}
        if not self.settings.routes_enabled or not self.settings.routes_api_key:return empty
        if mode=='transit' and not -7<=(arrival-datetime.now(timezone.utc)).total_seconds()/86400<=100:
            return {**empty,'status':'unsupported','coverage_notes':['Requested transit date is outside the provider window.']}
        remaining=self.deadline-time.monotonic()
        if remaining<0.1 or self.calls>=MAX_CALLS_PER_REQUEST:
            return {**empty,'coverage_notes':['Routing time/attempt limit reached; remaining estimates are unavailable.']}
        if not self.budget.take('routes'):
            return {**empty,'coverage_notes':['Daily Maps web-service request limit reached.']}
        self.calls+=1
        payload={'origin':{'location':{'latLng':{'latitude':candidate['coordinates']['lat'],'longitude':candidate['coordinates']['lon']}}},
                 'destination':{'location':{'latLng':{'latitude':building['lat'],'longitude':building['lon']}}},
                 'travelMode':{'walk':'WALK','bike':'BICYCLE','transit':'TRANSIT','drive':'DRIVE'}[mode]}
        if mode=='transit':payload['arrivalTime']=arrival.astimezone(timezone.utc).isoformat().replace('+00:00','Z')
        try:
            with httpx.Client(timeout=min(6,remaining),transport=self.transport,follow_redirects=False) as client:
                response=client.post('https://routes.googleapis.com/directions/v2:computeRoutes',json=payload,
                    headers={'X-Goog-Api-Key':self.settings.routes_api_key,'X-Goog-FieldMask':'routes.duration,routes.warnings'})
                response.raise_for_status();routes=response.json().get('routes',[])
            seconds=[float(r['duration'][:-1]) for r in routes if re.fullmatch(r'\d+(?:\.\d+)?s',r.get('duration',''))]
            if not seconds:return {**empty,'coverage_notes':['No supported route was returned; this does not prove the journey impossible.']}
            notes=['Building/address points are approximate; entrances and indoor walking are unverified.',
                   'Driving excludes parking search and the walk from parking.' if mode=='drive' else
                   'Transit includes provider journey components; future schedules can change.' if mode=='transit' else
                   'Static network estimate; selected arrival time does not establish future closures or accessibility.']
            result={**empty,'status':'supported','minutes':round(min(seconds)/60,2),'coverage_notes':notes+list(routes[0].get('warnings',[]))}
            self.memo[key]=deepcopy(result)
            return result
        except Exception:
            return {**empty,'coverage_notes':['Google Routes request failed or was denied. No replacement estimate was invented.']}
