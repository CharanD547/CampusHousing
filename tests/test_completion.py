"""Behavioral release checks for provider boundaries, isolation, recovery and week coverage."""
from dataclasses import replace
from datetime import date,datetime,timezone
import json
import sqlite3
import httpx
import pytest
from fastapi.testclient import TestClient
from roomwise.app import create_app
from roomwise.config import Settings
from roomwise.adapters.google_routes import GoogleRoutesAdapter
from roomwise.adapters.places import GooglePlaces
from roomwise.api.schemas import Commitment,Preferences
from tools.backend.backup import backup,restore


def test_every_week_occurrence_counted(client,request_body):
    request_body['routing_scope']='representative_week'
    request_body['commitments'][0]['weekdays']=['mon','wed','fri']
    response=client.post('/api/v1/comparisons',json=request_body)
    assert response.status_code==200
    for row in response.json()['candidate_results']:
        assert row['supported_commitments']==3 and row['total_commitments']==3
        assert [r['route_date'] for r in row['commute_estimates']]==['2026-10-26','2026-10-28','2026-10-30']


def test_places_header_scope_and_failures(tmp_path):
    calls=[]
    def provider(request):
        calls.append(request)
        assert request.headers['x-goog-api-key']=='private-places-test-key'
        assert 'reviews' not in request.headers['x-goog-fieldmask']
        assert 'key' not in request.url.params
        return httpx.Response(200,json={'places':[{'id':'p','displayName':{'text':'Test supermarket'},'googleMapsUri':'https://maps.google.com/?cid=123'}]})
    settings=Settings(tmp_path,places_enabled=True,places_api_key='private-places-test-key')
    places=GooglePlaces(settings,httpx.MockTransport(provider))
    assert places.nearby({'lat':37.2,'lon':-80.4},'groceries')['places'][0]['name']=='Test supermarket'
    assert places.nearby({'lat':37.2,'lon':-80.4},'groceries')['places'][0]['name']=='Test supermarket'
    assert len(calls)==2
    assert not any('places' in name for name in [p.name for p in tmp_path.iterdir()])
    disabled=GooglePlaces(replace(settings,places_enabled=False),httpx.MockTransport(provider))
    assert disabled.nearby({},'cafe')['status']=='unavailable'


def test_routes_buffer_modes_and_no_secret_leaks(tmp_path,monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return datetime(2026,10,24,tzinfo=timezone.utc)
    monkeypatch.setattr('roomwise.adapters.google_routes.datetime',Clock)
    calls=[]
    def provider(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200,json={'routes':[{'duration':'900s'}]})
    settings=Settings(tmp_path,routes_enabled=True,routes_api_key='private-route-test-key')
    adapter=GoogleRoutesAdapter(settings,httpx.MockTransport(provider))
    candidate={'id':'offer','property_id':'property','coordinate_basis':'representative_address','coordinates':{'lat':37.2,'lon':-80.4}}
    building={'id':'building','lat':37.22,'lon':-80.42}
    commitment=Commitment(id='class',building_id='building',weekdays=['mon'],arrival_time_local='09:00',arrival_buffer_minutes=15)
    prefs=Preferences(monthly_budget_per_person=1000,household_size=2,travel_modes=['transit','walk'])
    transit=adapter.estimate(candidate,building,commitment,'transit',date(2026,10,26),prefs)
    assert transit['status']=='supported' and transit['minutes']==15
    assert calls[0]['arrivalTime']=='2026-10-26T12:45:00Z'
    # Same property + destination + mode + arrival is deduplicated across offers only within this comparison.
    assert adapter.estimate({**candidate,'id':'other'},building,commitment,'transit',date(2026,10,26),prefs)['candidate_id']=='other'
    assert len(calls)==1
    adapter.estimate(candidate,building,commitment,'walk',date(2026,10,26),prefs)
    assert 'arrivalTime' not in calls[1]
    assert 'private-route-test-key' not in json.dumps(transit)
    denied=GoogleRoutesAdapter(settings,httpx.MockTransport(lambda request:httpx.Response(403,json={'error':{'message':'private-route-test-key'}})))
    failed=denied.estimate(candidate,building,commitment,'walk',date(2026,10,26),prefs)
    assert failed['minutes'] is None and failed['status']=='unavailable'
    assert 'private-route-test-key' not in json.dumps(failed)
    outside=adapter.estimate(candidate,building,commitment,'transit',date(2028,1,1),prefs)
    assert outside['status']=='unsupported'


def test_google_routes_not_retained_in_comparisons_or_briefs(tmp_path,request_body):
    settings=Settings(tmp_path,routes_enabled=True,routes_api_key='test-key')
    adapter=GoogleRoutesAdapter(settings,httpx.MockTransport(lambda request:httpx.Response(200,json={'routes':[{'duration':'999s'}]})))
    client=TestClient(create_app(settings,routing=adapter))
    request_body['commitments'][0]['building_id']='vt-0151'
    comparison=client.post('/api/v1/comparisons',json=request_body).json()
    assert comparison['candidate_results'][0]['commute_estimates'][0]['minutes']==16.65
    saved=client.app.state.store.get('comparisons',comparison['id'])
    assert all(not r['commute_estimates'] and r['supported_commitments']==0 for r in saved['candidate_results'])
    brief=client.post('/api/v1/briefs',json={'comparison_id':comparison['id'],'revision':1,'request_id':'one','selected_candidate_ids':['mill-2']}).json()
    assert brief['comparison']['candidate_results'][0]['commute_estimates']==[]
    assert '16.65' not in json.dumps(brief)


def test_browser_config_does_not_expose_private_keys(tmp_path):
    client=TestClient(create_app(Settings(tmp_path,maps_enabled=True,maps_javascript_api_key='public-browser-key',places_enabled=True,places_api_key='private-places-key',routes_api_key='private-routes-key')))
    config=client.get('/api/v1/maps/config').json()
    assert config['browser_key']=='public-browser-key' and config['places_available']
    assert 'private-' not in json.dumps(config)


def test_two_accounts_cannot_access_or_modify_each_others_records(tmp_path,request_body):
    app=create_app(Settings(tmp_path,accounts_required=True))
    alice,bob=TestClient(app),TestClient(app)
    assert alice.get('/api/v1/records').status_code==401
    first=alice.post('/api/v1/auth/register',json={'username':'alice','password':'unique-test-pass-alice'})
    second=bob.post('/api/v1/auth/register',json={'username':'bob','password':'unique-test-pass-bob'})
    assert first.status_code==second.status_code==200
    assert 'HttpOnly' in first.headers['set-cookie'] and 'SameSite=strict' in first.headers['set-cookie']
    body={'revision':0,'preferences':request_body['preferences'],'commitments':[]}
    assert alice.put('/api/v1/workspaces/shared-id',json=body).status_code==200
    assert bob.get('/api/v1/workspaces/shared-id').status_code==404
    assert bob.put('/api/v1/workspaces/shared-id',json=body).status_code==404
    request_body['commitments']=[]
    comparison=alice.post('/api/v1/comparisons',json=request_body).json()
    brief_request={'comparison_id':comparison['id'],'revision':1,'request_id':'one','selected_candidate_ids':['mill-2']}
    assert bob.post('/api/v1/briefs',json=brief_request).status_code==404
    brief=alice.post('/api/v1/briefs',json=brief_request).json()
    assert bob.get('/api/v1/briefs/'+brief['id']).status_code==404
    assert bob.get('/api/v1/records').json()['records']==[]
    assert bob.delete('/api/v1/records/briefs/'+brief['id']).status_code==404
    assert alice.post('/api/v1/auth/logout').status_code==200
    assert alice.get('/api/v1/workspaces/shared-id').status_code==401
    assert alice.post('/api/v1/auth/login',json={'username':'alice','password':'wrong-password-123'}).status_code==401
    assert alice.post('/api/v1/auth/login',json={'username':'ALICE','password':'unique-test-pass-alice'}).status_code==200
    assert alice.get('/api/v1/workspaces/shared-id').status_code==200
    assert alice.post('/api/v1/auth/logout',headers={'Origin':'https://other.test'}).status_code==403
    with sqlite3.connect(tmp_path/'accounts.sqlite3') as db:
        assert 'unique-test-pass' not in str(db.execute('SELECT * FROM users').fetchall())


def test_export_trash_restore_and_revisions(client,request_body):
    body={'revision':0,'preferences':request_body['preferences'],'commitments':[]}
    saved=client.put('/api/v1/workspaces/recover-me',json=body).json()
    exported=client.get('/api/v1/records/workspaces/recover-me/export').json()
    assert exported['record']==saved
    assert client.delete('/api/v1/records/workspaces/recover-me').status_code==200
    assert client.get('/api/v1/workspaces/recover-me').status_code==404
    assert client.put('/api/v1/workspaces/recover-me',json={**body,'revision':1}).status_code==409
    assert client.get('/api/v1/records').json()['records'][0]['deleted_at']
    assert client.post('/api/v1/records/workspaces/recover-me/restore').status_code==200
    assert client.get('/api/v1/workspaces/recover-me').json()==saved
    assert client.get('/api/v1/records/accounts/recover-me/export').status_code==422


def test_local_host_and_cross_site_provider_access_rejected(tmp_path):
    client=TestClient(create_app(Settings(tmp_path)))
    assert client.get('/api/v1/maps/config',headers={'Host':'untrusted.test'}).status_code==403
    assert client.get('/api/v1/properties/alight/nearby',headers={'Sec-Fetch-Site':'cross-site','Origin':'https://untrusted.test'}).status_code==403
    response=client.get('/api/v1/maps/config')
    assert response.status_code==200 and response.headers['X-Content-Type-Options']=='nosniff'


def test_explicit_local_operator_access_keeps_lan_protected(tmp_path):
    app=create_app(Settings(tmp_path,api_token='test-operator-token',local_operator_enabled=True))
    local=TestClient(app,base_url='http://127.0.0.1:8001',client=('127.0.0.1',50000))
    remote=TestClient(app,base_url='http://10.0.0.182:8001',client=('10.0.0.22',50000))
    assert local.get('/api/v1/health').status_code==200
    assert local.get('/api/v1/health',headers={'Host':'untrusted.test'}).status_code==401
    assert local.get('/api/v1/health',headers={'Origin':'https://untrusted.test'}).status_code==401
    assert local.get('/api/v1/health',headers={'Sec-Fetch-Site':'cross-site'}).status_code==403
    assert remote.get('/api/v1/health').status_code==401
    assert remote.get('/api/v1/health',headers={'Authorization':'Bearer test-operator-token'}).status_code==200


def test_public_access_serves_remote_visitors_without_a_token(tmp_path):
    remote=TestClient(create_app(Settings(tmp_path,public_access=True)),base_url='https://roomwise.example.run.app',client=('203.0.113.9',50000))
    assert remote.get('/api/v1/health').status_code==200
    assert remote.get('/api/v1/candidates').status_code==200
    # Cross-site API calls stay blocked even when the app is public.
    assert remote.get('/api/v1/maps/config',headers={'Sec-Fetch-Site':'cross-site','Origin':'https://untrusted.test'}).status_code==403
    closed=TestClient(create_app(Settings(tmp_path)),base_url='https://roomwise.example.run.app',client=('203.0.113.9',50000))
    assert closed.get('/api/v1/health').status_code==403


def test_backup_restore_detects_corruption_without_overwriting(tmp_path):
    source=tmp_path/'source';source.mkdir()
    (source/'.env').write_text('SECRET=never-backup')
    with sqlite3.connect(source/'example.sqlite3') as db:
        db.execute('CREATE TABLE sample(value TEXT)');db.execute("INSERT INTO sample VALUES ('preserved')")
    archive=tmp_path/'backup';manifest=backup(source,archive)
    assert len(manifest['files'])==1 and not (archive/'.env').exists()
    restored=tmp_path/'restored';restore(archive,restored)
    with sqlite3.connect(restored/'example.sqlite3') as db:assert db.execute('SELECT * FROM sample').fetchall()==[('preserved',)]
    with pytest.raises(ValueError,match='NEW directory'):restore(archive,restored)
    (archive/'example.sqlite3').write_bytes(b'corrupted')
    rejected=tmp_path/'rejected'
    with pytest.raises(ValueError,match='checksum'):restore(archive,rejected)
    assert not rejected.exists()
