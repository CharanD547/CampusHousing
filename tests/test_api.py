import pytest
from fastapi.testclient import TestClient
from roomwise.app import create_app
from roomwise.config import Settings


def test_catalog_and_removed_routes(client):
    data=client.get('/api/v1/candidates').json()['candidates']
    assert len(data)==18
    assert next(c for c in data if c['id']=='alight-east')['offer']['price']['amount']=='835'
    for path in ('/repair','/rehearsal','/investigate','/api/inspect','/api/housing/properties'):
        assert client.get(path).status_code==404


def test_unknown_building_and_campus(client,request_body):
    request_body['commitments'][0]['building_id']='made-up'
    response=client.post('/api/v1/comparisons',json=request_body)
    assert response.status_code==422 and response.json()['error']['code']=='unknown_building'
    request_body['campus_id']='other'
    assert client.post('/api/v1/comparisons',json=request_body).status_code==404


def test_real_default_readiness(tmp_path):
    client=TestClient(create_app(Settings(tmp_path)))
    buildings=client.get('/api/v1/campuses/vt/buildings').json()
    assert buildings['status']=='available' and len(buildings['buildings'])>=100
    assert all(b['verified'] and b['source'].startswith('https://arcgis-central.gis.vt.edu/') for b in buildings['buildings'])
    assert client.get('/api/v1/health').json()['dependencies']['gemma']=='not_configured'


def test_official_destinations_without_fabricated_routes(tmp_path,request_body):
    client=TestClient(create_app(Settings(tmp_path)))
    request_body['commitments']=[dict(id='lecture',building_id='vt-0151',weekdays=['mon'],arrival_time_local='09:00'),
                                 dict(id='lab',building_id='vt-0174',weekdays=['mon'],arrival_time_local='14:00')]
    response=client.post('/api/v1/comparisons',json=request_body)
    assert response.status_code==200
    for result in response.json()['candidate_results']:
        assert result['total_commitments']==2 and result['supported_commitments']==0
        assert all(r['minutes'] is None and r['status']=='unavailable' for r in result['commute_estimates'])


def test_cost_basis_and_bedroom_conflict(client,request_body):
    request_body['preferences']['household_size']=3
    comparison=client.post('/api/v1/comparisons',json=request_body).json()
    mill=next(x for x in comparison['candidate_results'] if x['candidate_id']=='mill-2')
    assert mill['known_recurring_subtotal']=='433.33' and mill['fit_state']=='conflict'
    assert mill['cost_breakdown']['scenario'] and mill['cost_breakdown']['checks']['budget']=='unknown'
    assert comparison['input_revision']==1


def test_partial_routes(client,request_body):
    request_body['commitments'].append({**request_body['commitments'][0],'id':'c2'})
    for result in client.post('/api/v1/comparisons',json=request_body).json()['candidate_results']:
        assert result['supported_commitments']==1 and result['total_commitments']==2
        assert result['fit_state']!='documented_fit'


def test_wrong_weekday(client,request_body):
    request_body['route_date']='2026-10-27'
    result=client.post('/api/v1/comparisons',json=request_body).json()['candidate_results'][0]
    assert result['supported_commitments']==0 and result['commute_estimates'][0]['status']=='unsupported'


def test_ai_off_checklist_preserves_progress(client,request_body):
    comparison=client.post('/api/v1/comparisons',json=request_body).json()
    payload={'comparison_id':comparison['id'],'revision':1,'request_id':'guide'}
    assert client.post('/api/v1/ai/explain',json=payload).json()['status']=='ai_unavailable'
    payload['candidate_id']='mill-2'
    generated=client.post('/api/v1/guide/checklist',json=payload).json()
    assert generated['wish_i_knew']['status']=='insufficient_evidence'
    items=generated['checklist'];items[0]['status']='done';items[0]['notes']='Confirmed by user.'
    payload['previous_items']=items
    again=client.post('/api/v1/guide/checklist',json=payload).json()
    assert again['checklist'][0]['id']==items[0]['id'] and again['checklist'][0]['status']=='done'
    assert again['checklist'][0]['notes']=='Confirmed by user.'
    payload['revision']=0
    assert client.post('/api/v1/guide/checklist',json=payload).status_code==409


def test_brief_immutable_and_idempotent(client,request_body):
    comparison=client.post('/api/v1/comparisons',json=request_body).json()
    body=dict(comparison_id=comparison['id'],revision=1,request_id='brief',selected_candidate_ids=['mill-2'])
    first=client.post('/api/v1/briefs',json=body).json()
    assert client.post('/api/v1/briefs',json=body).json()==first
    body['selected_candidate_ids']=['alight-east']
    assert client.post('/api/v1/briefs',json=body).status_code==409
    assert client.get('/api/v1/briefs/'+first['id']).json()==first


def test_workspace_revisions_and_error_privacy(client,request_body):
    body=dict(revision=0,preferences=request_body['preferences'])
    assert client.put('/api/v1/workspaces/example',json=body).json()['revision']==1
    assert client.put('/api/v1/workspaces/example',json=body).status_code==409
    response=client.post('/api/v1/comparisons',json={'private_schedule':'DO_NOT_ECHO'})
    assert response.status_code==422 and 'DO_NOT_ECHO' not in response.text
    assert response.json()['request_id']


def test_token_required_when_configured(tmp_path):
    client=TestClient(create_app(Settings(tmp_path,api_token='test-token')))
    assert client.get('/api/v1/candidates').status_code==401
    assert client.get('/api/v1/candidates',headers={'Authorization':'Bearer test-token'}).status_code==200


@pytest.mark.parametrize('change',[{'revision':-1},{'candidate_ids':['unknown']},
                                  {'commitments':[dict(id='x',building_id='test-classroom',weekdays=['mon','mon'],arrival_time_local='09:00')]}])
def test_invalid_contract(client,request_body,change):
    request_body.update(change)
    assert client.post('/api/v1/comparisons',json=request_body).status_code==422


def test_browse_without_schedule_stays_incomplete(client,request_body):
    request_body['commitments']=[]
    response=client.post('/api/v1/comparisons',json=request_body)
    assert response.status_code==200
    for row in response.json()['candidate_results']:
        assert row['total_commitments']==0 and row['fit_state']!='documented_fit'
        assert 'Add class commitments before judging commute coverage.' in row['unknown_costs']


def test_frontend_assets_and_server_owned_snapshot(client,request_body):
    assert '<title>Roomwise</title>' in client.get('/').text
    assert client.get('/assets/api.js').status_code==200
    comparison=client.post('/api/v1/comparisons',json=request_body).json()
    notes={'mill-2':{'questions':[{'id':'q1','text':'Which fees apply?','answer':'Awaiting office'}]}}
    brief=client.post('/api/v1/briefs',json=dict(comparison_id=comparison['id'],revision=1,request_id='notes-brief',
        selected_candidate_ids=['mill-2'],notes=notes)).json()
    assert brief['notes']['mill-2']['questions'][0]['answer']=='Awaiting office'
    assert any(c['id']=='mill-2' and c['property_name']=='The Mill' for c in brief['comparison']['catalog_snapshot'])
    assert client.get('/api/v1/briefs/'+brief['id']).json()==brief
