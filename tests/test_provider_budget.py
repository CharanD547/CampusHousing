from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import httpx

from roomwise.adapters.places import GooglePlaces
from roomwise.config import Settings
from roomwise.repositories.provider_budget import ProviderBudget


def test_shared_daily_attempts_are_atomic_and_persist_across_instances(tmp_path):
    path=tmp_path/'budget.sqlite3'
    budget=ProviderBudget(path,3)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:budget.take('places'),range(8)))
    assert sum(results)==3
    assert not ProviderBudget(path,3).take('routes')


def test_failed_google_requests_count_and_cap_prevents_next_network_call(tmp_path):
    calls=[]
    def provider(request):
        calls.append(request);return httpx.Response(403)
    settings=Settings(tmp_path,places_enabled=True,places_api_key='fixture-key',maps_daily_requests=1)
    places=GooglePlaces(settings,httpx.MockTransport(provider))
    point={'lat':37.2,'lon':-80.4}
    assert places.nearby(point,'cafe')['status']=='unavailable'
    assert 'limit reached' in places.nearby(point,'cafe')['reason']
    assert len(calls)==1
