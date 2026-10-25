from copy import deepcopy
import json
from pathlib import Path

import httpx
import pytest

from roomwise.adapters.places import GooglePlaces
from roomwise.api.errors import APIError
from roomwise.config import ROOT,Settings
from roomwise.repositories.catalog import CatalogRepository
from roomwise.repositories.provider_budget import ProviderBudget
from roomwise.services.comparison import candidates
from tools.backend.sync_catalog import sync_catalog


def test_catalog_update_is_previewable_archived_and_idempotent(tmp_path):
    repository=CatalogRepository(tmp_path)
    seed=json.loads((ROOT/'data/housing-seed.json').read_text(encoding='utf-8'))
    old=repository.catalog()
    seed['properties'][0]['offers'][0]['amount']='1420'
    preview=sync_catalog(repository,seed,{},False)
    assert preview['changed_properties']==['foxridge'] and repository.catalog()==old
    assert sync_catalog(repository,seed,{},True)['changed_properties']==['foxridge']
    assert not sync_catalog(repository,seed,{},True)['changed_properties']
    with repository.connect() as db:
        assert db.execute('SELECT count(*) FROM housing_catalog_versions').fetchone()[0]==1
    assert repository.catalog()[0]['offers'][0]['amount']=='1420'


def test_directory_separates_references_from_comparable_offers(client):
    data=client.get('/api/v1/housing-guide').json()
    assert len(data['communities'])==47
    assert sum(bool(c['catalog_property_id']) for c in data['communities'])==6
    assert all(c['evidence_status']=='guide_reference_only' for c in data['communities'])
    assert all(c['source_urls'] for c in data['communities'])
    assert all('lat' not in c and 'amount' not in c for c in data['communities'])


def test_nearby_categories_radius_distances_and_quota(tmp_path):
    requests=[]
    def provider(request):
        data=json.loads(request.content);requests.append(data)
        assert data['rankPreference']=='DISTANCE' and data['maxResultCount']==8
        assert data['locationRestriction']['circle']['radius']==1000
        assert 'reviews' not in request.headers['x-goog-fieldmask']
        return httpx.Response(200,json={'places':[{'id':'p','displayName':{'text':'Example'},
            'location':{'latitude':37.201,'longitude':-80.4}}]})
    settings=Settings(tmp_path,places_enabled=True,places_api_key='test')
    adapter=GooglePlaces(settings,ProviderBudget(tmp_path/'budget.sqlite3',3),httpx.MockTransport(provider))
    for category in ('restaurant','gas_station','groceries'):
        result=adapter.nearby({'lat':37.2,'lon':-80.4},category,1000)
        assert result['status']=='available' and result['places'][0]['distance_meters']==111
        assert result['storage_scope'].startswith('Live response only')
    assert requests[-1]['includedTypes']==['supermarket','grocery_store']
    assert adapter.nearby({'lat':37.2,'lon':-80.4},'restaurant')['status']=='unavailable'
    for category,radius in [('unknown',2500),('restaurant',500000)]:
        with pytest.raises(APIError):adapter.nearby({},category,radius)


def test_catalog_price_date_is_not_replaced_by_fee_date():
    prop=deepcopy(json.loads((ROOT/'data/housing-seed.json').read_text(encoding='utf-8'))['properties'][0])
    price_id=prop['offers'][0]['source_id']
    for source in prop['sources']:
        source['checked_at']='2026-10-01T00:00:00+00:00' if source['id']==price_id else '2026-10-24T00:00:00+00:00'
        source.pop('reviewed_at',None)
    assert candidates([prop])[0]['offer']['price']['last_reviewed_at'].startswith('2026-10-01')


def test_route_recomputations_preserve_reserved_nearby_capacity(tmp_path):
    budget=ProviderBudget(tmp_path/'budget.sqlite3',6,reserve_places=4)
    assert budget.take('routes') and budget.take('routes')
    assert not budget.take('routes')
    assert all(budget.take('places') for _ in range(4))
    assert not budget.take('places')


def test_all_guide_entries_are_explorable_with_traceable_prices(client,request_body):
    directory=client.get('/api/v1/housing-guide').json()['communities']
    catalog=client.get('/api/v1/candidates').json()['candidates']
    guide=[c for c in catalog if c.get('guide_reference')]
    assert len(guide)>41 and len(catalog)==68+len(guide)
    assert len({c['property_id'] for c in catalog})==47
    assert {c['guide_reference']['id'] for c in guide}=={c['id'] for c in directory if not c['catalog_property_id']}
    for candidate in guide:
        offer=candidate['offer']
        # Every guide-place price traces to an operator row or the guide's own text; nothing is filled in.
        if offer['price']['amount'] is not None:
            assert offer['price_confidence_tier'] in ('OPERATOR_OBSERVED','LISTING_OBSERVED','GUIDE_REFERENCE') and offer['unknown_costs']
        # Every guide place has a map point: operator-published, or a geocoded street address.
        assert candidate['coordinates'] is not None
        assert candidate['coordinate_basis'] in ('operator_community_point','geocoded_street_address')
    assert all(c['sources'][0]['review_status']!='reviewed' for c in guide)
    request_body.update(commitments=[],candidate_ids=[guide[0]['id'],'alight-east'])
    response=client.post('/api/v1/comparisons',json=request_body)
    assert response.status_code==200
    row=response.json()['candidate_results'][0]
    # Unverified prices never make a documented fit; one already over budget is still a real conflict.
    assert row['fit_state']=='conflict' if row['hard_conflicts'] else row['fit_state']=='insufficient_evidence'
    assert any('unconfirmed' in u for u in row['unknown_costs'])
    # A published eligibility rule is carried as a hard conflict on every plan at that place.
    legacy=[c for c in catalog if c['property_id']=='legacy-on-main-the-orchards']
    request_body.update(candidate_ids=[legacy[0]['id']])
    legacy_row=client.post('/api/v1/comparisons',json=request_body).json()['candidate_results'][0]
    assert legacy_row['fit_state']=='conflict' and any('students' in c for c in legacy_row['hard_conflicts'])


def test_guide_reference_nearby_does_not_spend_quota(tmp_path):
    class NoRequests:
        def take(self,*args):raise AssertionError('No verified point; provider must not be called')
    result=GooglePlaces(Settings(tmp_path,places_enabled=True,places_api_key='test'),NoRequests()).nearby({'lat':None,'lon':None},'groceries')
    assert result['status']=='unavailable' and not result['places']
