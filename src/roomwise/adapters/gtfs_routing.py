"""Local routing from the bundled Blacksburg Transit GTFS feed. No API key or network access.

Transit: direct scheduled trips from a stop near the home to a stop near the class building,
arriving before the class arrival time minus the buffer. Walking legs and walk-only trips are
estimated from straight-line distance with a detour factor; every result says so.
"""
from copy import deepcopy
from datetime import datetime, timedelta
from functools import lru_cache
from roomwise.adapters.bt_gtfs import distance, feed, seconds
from roomwise.adapters.routing import UnconfiguredRoutingAdapter

DETOUR = 1.3            # straight-line to street-path factor for walking estimates
WALK_M_PER_MIN = 80     # ~4.8 km/h
MAX_WALK_MIN = 45       # longer walks are reported unavailable
ORIGIN_STOP_M = 800
DEST_STOP_M = 900
WALK_NOTE = f'Walking time estimated from straight-line distance × {DETOUR} at {WALK_M_PER_MIN} m/min; not a routed path.'


def walk_minutes(meters):
    return meters * DETOUR / WALK_M_PER_MIN


@lru_cache(maxsize=1)
def index():
    data = feed()
    if not data: return None
    trips = {t['trip_id']: t for t in data['trips']}
    by_trip = {}
    for row in data['stop_times']:
        by_trip.setdefault(row['trip_id'], {})[row['stop_id']] = (int(row['stop_sequence']), row['arrival_time'], row['departure_time'],
                                                                  row.get('pickup_type'), row.get('drop_off_type'))
    services = {}
    for row in data['calendar_dates']:
        day = services.setdefault(row['date'], set())
        if row['exception_type'] == '1': day.add(row['service_id'])
        else: day.discard(row['service_id'])
    stops = [(s['stop_id'], s['stop_name'], float(s['stop_lat']), float(s['stop_lon'])) for s in data['stops']]
    routes = {r['route_id']: r for r in data['routes']}
    return dict(trips=trips, by_trip=by_trip, services=services, stops=stops, routes=routes)


def near(stops, point, radius):
    found = [(distance(point, (lat, lon)), sid, name) for sid, name, lat, lon in stops]
    return {sid: (meters, name) for meters, sid, name in sorted(found) if meters <= radius}


class GtfsRoutingAdapter:
    provider = 'bt_gtfs_local'

    def __init__(self):
        self.memo = {}

    def estimate(self, candidate, building, commitment, mode, route_date, preferences):
        # Every floor plan at a property shares its address, so route once per property and class.
        buffer = commitment.arrival_buffer_minutes if commitment.arrival_buffer_minutes is not None else preferences.arrival_buffer_minutes
        key = (candidate['coordinates']['lat'], candidate['coordinates']['lon'], building['id'], mode, route_date, commitment.arrival_time_local, buffer)
        if key not in self.memo:
            if len(self.memo) > 5000: self.memo.clear()
            self.memo[key] = self._estimate(candidate, building, commitment, mode, route_date, preferences)
        return {**deepcopy(self.memo[key]), 'candidate_id': candidate['id'], 'commitment_id': commitment.id}

    def _estimate(self, candidate, building, commitment, mode, route_date, preferences):
        result = UnconfiguredRoutingAdapter().estimate(candidate, building, commitment, mode, route_date, preferences)
        result.update(provider=self.provider)
        home = (candidate['coordinates']['lat'], candidate['coordinates']['lon'])
        dest = (building['lat'], building['lon'])
        buffer = commitment.arrival_buffer_minutes if commitment.arrival_buffer_minutes is not None else preferences.arrival_buffer_minutes
        arrive_by = datetime.combine(route_date, commitment.arrival_time_local) - timedelta(minutes=buffer)
        target = arrive_by.hour * 3600 + arrive_by.minute * 60
        result['context'].update(arrival_by=arrive_by.strftime('%H:%M'))
        if mode == 'walk':
            minutes = walk_minutes(distance(home, dest))
            if minutes > MAX_WALK_MIN:
                return {**result, 'coverage_notes': [f'Walk is longer than {MAX_WALK_MIN} minutes; not offered.', WALK_NOTE]}
            return {**result, 'status': 'supported', 'minutes': round(minutes), 'coverage_notes': [WALK_NOTE]}
        if mode != 'transit':
            return {**result, 'status': 'unsupported', 'coverage_notes': ['The local timetable router supports walking and Blacksburg Transit only.']}
        data = index()
        if not data:
            return {**result, 'coverage_notes': ['Blacksburg Transit schedule data is unavailable.']}
        active = data['services'].get(route_date.strftime('%Y%m%d'), set())
        if not active:
            return {**result, 'status': 'unsupported', 'coverage_notes': [f'No published Blacksburg Transit service on {route_date.isoformat()}.']}
        origins = near(data['stops'], home, ORIGIN_STOP_M)
        targets = near(data['stops'], dest, DEST_STOP_M)
        best = None
        for trip_id, stops in data['by_trip'].items():
            trip = data['trips'][trip_id]
            if trip['service_id'] not in active: continue
            for o, (o_m, o_name) in origins.items():
                if o not in stops or stops[o][3] == '1': continue
                o_seq, _, o_dep, _, _ = stops[o]
                for d, (d_m, d_name) in targets.items():
                    if d not in stops or stops[d][0] <= o_seq or stops[d][4] == '1': continue
                    walk_out = walk_minutes(d_m)
                    arrive = seconds(stops[d][1]) + walk_out * 60
                    if arrive > target or target - arrive > 3600: continue
                    walk_in = walk_minutes(o_m)
                    depart_home = seconds(o_dep) - walk_in * 60
                    total = (arrive - depart_home) / 60
                    # Prefer the latest departure from home, then the shortest trip.
                    key = (depart_home, -total)
                    if best is None or key > best[0]:
                        route = data['routes'][trip['route_id']]
                        best = (key, round(total), dict(route=route['route_short_name'], route_name=route['route_long_name'], from_stop=o_name,
                                                        to_stop=d_name, departure=o_dep[:5], arrival=stops[d][1][:5],
                                                        walk_to_stop_min=round(walk_in), walk_from_stop_min=round(walk_out)))
        if not best:
            return {**result, 'status': 'unsupported',
                    'coverage_notes': ['No direct Blacksburg Transit trip arrives in time from a stop near this home. Transfers are not evaluated.']}
        _, minutes, leg = best
        return {**result, 'status': 'supported', 'minutes': minutes, 'context': {**result['context'], 'journey': leg},
                'coverage_notes': [f"{leg['route']} {leg['route_name']}: {leg['from_stop']} {leg['departure']} → {leg['to_stop']} {leg['arrival']}.",
                                   f"Includes {leg['walk_to_stop_min']} min walking to the stop and {leg['walk_from_stop_min']} min from it; waiting at home before leaving is excluded.",
                                   'Direct trips only; transfers and live delays are not evaluated.', WALK_NOTE]}
