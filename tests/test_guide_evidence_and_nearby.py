import httpx
import pytest
from roomwise.adapters.osm_places import OpenStreetMapPlaces
from roomwise.services.guide_catalog import guide_properties
from tools.backend.refresh_guide_evidence import extract_cmg

class Budget:
    def __init__(self):self.used=0
    def take(self,operation):self.used+=1;return self.used<=2

def test_research_parser_rejects_unrelated_property_and_uses_community_not_office():
    html='''<div data-community="Cedar Pointe" data-lat="37.200846" data-lng="-80.3987542"></div>
      <div class="office-map" data-lat="37.2288459" data-lng="-80.4137966"></div>
      <h3>Unrelated House</h3><p>4 bed $5,000.00 Apply Now</p>
      <h3>Cedar Pointe B1</h3><p>2 bed 2 bath $2,000.00 - $2,100.00 Apply Now</p>'''
    rows,point=extract_cmg(html,('cedar pointe',))
    assert len(rows)==1 and rows[0]['minimum']==2000 and rows[0]['maximum']==2100
    assert point=={'lat':37.200846,'lon':-80.3987542}

def test_research_prices_do_not_become_unsupported_comparison_quotes():
    guide={'document_sha256':'test','communities':[{'id':'p','name':'Test place','address':'Test street',
        'zone':'Campus','layouts':'2BR','source_urls':['https://example.test/guide'],'guide_price_summary':'Old reference'}]}
    evidence={'properties':{'p':{'status':'operator_observed','source_url':'https://example.test/operator',
        'checked_at':'2026-10-25T02:00:00Z','prices':[{'label':'B1','minimum':2000,'maximum':2100}],
        'coordinates':{'lat':37.2,'lon':-80.4},'billing_note':'Basis and fees unconfirmed.'}}}
    prop=guide_properties(guide,evidence)[0]
    assert prop['lat']==37.2 and prop['offers'][0]['amount'] is None
    assert prop['guide_reference']['evidence_update']['prices'][0]['minimum']==2000
    assert prop['sources'][-1]['url']=='https://example.test/operator'

def test_osm_nearby_sorts_deduplicates_limits_and_caches():
    budget=Budget();calls=[]
    def provider(request):
        calls.append(request)
        assert 'supermarket' in request.url.params['data'] and '2500' in request.url.params['data']
        return httpx.Response(200,json={'elements':[
            {'id':n,'type':'node','lat':37.2+n/10000,'lon':-80.4,'tags':{'name':f'Store {n}'}}
            for n in range(12,0,-1)] + [{'id':99,'type':'node','lat':37.8,'lon':-80.4,'tags':{'name':'Too far'}}]})
    adapter=OpenStreetMapPlaces(budget,httpx.MockTransport(provider))
    result=adapter.nearby({'id':'p','lat':37.2,'lon':-80.4},'groceries',2500)
    assert result['status']=='available' and result['provider']=='OpenStreetMap'
    assert len(result['places'])==8 and result['places'][0]['name']=='Store 1'
    assert result['places'][0]['url']=='https://www.openstreetmap.org/node/1'
    again=adapter.nearby({'id':'p','lat':37.2,'lon':-80.4},'groceries',2500)
    assert len(calls)==1 and budget.used==1 and again==result

def test_osm_missing_points_and_partial_errors_do_not_invent_places():
    budget=Budget()
    def provider(request):return httpx.Response(200,json={'remark':'timeout','elements':[]})
    adapter=OpenStreetMapPlaces(budget,httpx.MockTransport(provider))
    assert adapter.nearby({'lat':None,'lon':None},'groceries')['status']=='unavailable'
    assert budget.used==0
    assert adapter.nearby({'lat':37.2,'lon':-80.4},'groceries')['status']=='unavailable'
