from dataclasses import replace
import json

import httpx
from fastapi.testclient import TestClient

from roomwise.adapters.model import JSONModel
from roomwise.app import create_app
from roomwise.config import Settings


class FixtureModel:
    provider='test_fixture'
    model_id='synthetic_test_only'
    configured=True

    def __init__(self,invalid=False):self.calls=0;self.invalid=invalid

    def generate(self,prompt,schema):
        self.calls+=1
        return dict(answer='The known subtotal excludes unresolved costs.',answer_kind='evidence',
                    evidence_ids=['unrelated-source' if self.invalid else 'mill-plans'],candidate_ids=['mill-2'],
                    limitations=['Synthetic test answer, not model inference.'],next_questions=['Confirm mandatory costs?'])


def assistant_client(client,tmp_path,model,**kwargs):
    settings=Settings(tmp_path,external_operations_enabled=True,**kwargs)
    # Reuse the test campus boundary; real HTTP provider calls are never made.
    from roomwise.repositories.campus import CampusRepository
    campus=tmp_path/'campus.json'
    campus.write_text(json.dumps({'campuses':[{'id':'vt','name':'Test','buildings':[
        {'id':'test-classroom','label':'Test','source':'https://example.test','verified':True}]}]}))
    return TestClient(create_app(settings,campuses=CampusRepository(campus),assistant_model=model))


def message(browser,request_body):
    comparison=browser.post('/api/v1/comparisons',json=request_body).json()
    return dict(comparison_id=comparison['id'],revision=1,request_id='question',question='What costs are unresolved?',candidate_ids=['mill-2'])


def test_api_free_assistant_is_explicitly_deterministic(client,request_body):
    response=client.post('/api/v1/assistant/messages',json=message(client,request_body))
    assert response.status_code==200
    assert response.json()['status']=='complete' and response.json()['model_id'] is None
    assert response.json()['provider']=='local_rules'
    assert response.json()['result']['candidate_ids']==['mill-2']
    assert '$1300' in response.json()['result']['answer']


def test_local_helper_does_not_claim_reviews_safety_or_invent_external_answers(client,request_body):
    body=message(client,request_body)
    body['question']='Is this neighborhood safe according to reviews?'
    result=client.post('/api/v1/assistant/messages',json=body).json()['result']
    assert result['answer_kind']=='insufficient_evidence' and not result['evidence_ids']
    body['question']='What does per installment mean?'
    result=client.post('/api/v1/assistant/messages',json=body).json()['result']
    assert result['answer_kind']=='general' and 'not automatically' in result['answer']


def test_assistant_citations_idempotency_and_daily_limit(client,tmp_path,request_body):
    model=FixtureModel()
    browser=assistant_client(client,tmp_path,model,ai_daily_requests=1)
    body=message(browser,request_body)
    first=browser.post('/api/v1/assistant/messages',json=body).json()
    assert first['status']=='complete' and first['result']['evidence_ids']==['mill-plans']
    assert browser.post('/api/v1/assistant/messages',json=body).json()==first and model.calls==1
    body['question']='Different inputs'
    assert browser.post('/api/v1/assistant/messages',json=body).status_code==409
    body['request_id']='new-question'
    assert browser.post('/api/v1/assistant/messages',json=body).json()['error']['code']=='daily_limit'
    assert model.calls==1


def test_assistant_rejects_invalid_citations_and_wrong_revision(client,tmp_path,request_body):
    browser=assistant_client(client,tmp_path,FixtureModel(invalid=True))
    body=message(browser,request_body)
    assert browser.post('/api/v1/assistant/messages',json=body).json()['error']['code']=='provider_failure'
    body['revision']=0
    assert browser.post('/api/v1/assistant/messages',json=body).status_code==409


def test_google_and_custom_transport_are_server_side_and_model_checked(tmp_path):
    seen=[]
    answer={'answer':'Test'}
    def google(request):
        seen.append(request)
        assert request.headers['x-goog-api-key']=='test-key'
        return httpx.Response(200,json={'modelVersion':'gemma-test','candidates':[{'content':{'parts':[{'text':json.dumps(answer)}]}}]})
    settings=Settings(tmp_path,external_operations_enabled=True,ai_provider='google',ai_model='gemma-test',ai_api_key='test-key')
    assert JSONModel(settings,httpx.MockTransport(google)).generate('test',{})==answer
    assert 'test-key' not in str(seen[0].url) and 'test-key' not in repr(settings)
    def custom(request):
        return httpx.Response(200,json={'model':'roomwise-gemma','choices':[{'message':{'content':json.dumps(answer)}}]})
    local=replace(settings,ai_provider='openai_compatible',ai_model='roomwise-gemma',ai_api_key='')
    assert JSONModel(local,httpx.MockTransport(custom)).generate('test',{})==answer
