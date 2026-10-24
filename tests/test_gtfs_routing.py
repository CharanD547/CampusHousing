"""Local routing from the bundled Blacksburg Transit GTFS feed."""
from datetime import date, time
from types import SimpleNamespace
from roomwise.adapters.gtfs_routing import GtfsRoutingAdapter

MILL = dict(id='mill-2', coordinates={'lat': 37.2107303, 'lon': -80.39652582}, coordinate_basis='representative_address')
TORGERSEN = dict(id='vt-torgersen', lat=37.22975, lon=-80.42017)
PREFS = SimpleNamespace(arrival_buffer_minutes=10)


def commitment(arrival=time(9, 0)):
    return SimpleNamespace(id='c1', arrival_time_local=arrival, arrival_buffer_minutes=None, weekdays=['tue'])


def test_scheduled_bus_trip_arrives_before_the_buffer():
    route = GtfsRoutingAdapter().estimate(MILL, TORGERSEN, commitment(), 'transit', date(2026, 10, 27), PREFS)
    assert route['status'] == 'supported' and 0 < route['minutes'] < 60
    leg = route['context']['journey']
    assert leg['arrival'] <= '08:50' and leg['departure'] < leg['arrival']
    assert any('Direct trips only' in n for n in route['coverage_notes'])


def test_long_walks_drive_and_days_without_service_are_not_supported():
    router = GtfsRoutingAdapter()
    walk = router.estimate(MILL, TORGERSEN, commitment(), 'walk', date(2026, 10, 27), PREFS)
    assert walk['minutes'] is None and any('straight-line' in n for n in walk['coverage_notes'])
    assert router.estimate(MILL, TORGERSEN, commitment(), 'drive', date(2026, 10, 27), PREFS)['status'] == 'unsupported'
    no_service = router.estimate(MILL, TORGERSEN, commitment(), 'transit', date(2027, 3, 2), PREFS)
    assert no_service['status'] == 'unsupported' and no_service['minutes'] is None


def test_no_trip_before_service_starts():
    early = GtfsRoutingAdapter().estimate(MILL, TORGERSEN, commitment(time(5, 0)), 'transit', date(2026, 10, 27), PREFS)
    assert early['status'] == 'unsupported' and early['minutes'] is None


class StubPrimary:
    provider = 'google_routes'
    def __init__(self, status): self.status = status
    def estimate(self, candidate, building, commitment, mode, route_date, preferences):
        return dict(candidate_id=candidate['id'], commitment_id=commitment.id, mode=mode, status=self.status,
                    minutes=12 if self.status == 'supported' else None, provider=self.provider,
                    coverage_notes=['Routing time/attempt limit reached; remaining estimates are unavailable.'])


def test_google_result_wins_and_timetable_fills_gaps():
    from roomwise.adapters.gtfs_routing import FallbackRoutingAdapter
    day = date(2026, 10, 27)
    live = FallbackRoutingAdapter(StubPrimary('supported'), GtfsRoutingAdapter())
    assert live.estimate(MILL, TORGERSEN, commitment(), 'transit', day, PREFS)['provider'] == 'google_routes'
    capped = FallbackRoutingAdapter(StubPrimary('unavailable'), GtfsRoutingAdapter())
    filled = capped.estimate(MILL, TORGERSEN, commitment(), 'transit', day, PREFS)
    assert filled['provider'] == 'bt_gtfs_local' and filled['status'] == 'supported'
    assert 'bundled bus timetable' in filled['coverage_notes'][0]
    # Nothing to fall back to for driving: the Google result is returned unchanged.
    assert capped.estimate(MILL, TORGERSEN, commitment(), 'drive', day, PREFS)['provider'] == 'google_routes'
