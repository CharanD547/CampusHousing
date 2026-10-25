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
        return dict(answer='The Mill: the known subtotal excludes unresolved costs.',answer_kind='evidence',
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


def test_off_topic_question_skips_model_and_is_refused_locally(client,tmp_path,request_body):
    model=FixtureModel()
    browser=assistant_client(client,tmp_path,model)
    body=message(browser,request_body)
    body['question']='What is the weather in Blacksburg today?'
    result=browser.post('/api/v1/assistant/messages',json=body).json()
    assert result['provider']=='local_rules' and model.calls==0
    assert result['result']['answer_kind']=='insufficient_evidence' and not result['result']['evidence_ids']


def test_evidence_answer_must_name_a_selected_property(client,tmp_path,request_body):
    class Unnamed(FixtureModel):
        def generate(self,prompt,schema):
            result=super().generate(prompt,schema)
            result['answer']='The known subtotal excludes unresolved costs.'
            return result
    browser=assistant_client(client,tmp_path,Unnamed())
    result=browser.post('/api/v1/assistant/messages',json=message(browser,request_body)).json()
    assert result['provider']=='local_rules' and result['fallback']['code']=='provider_failure'


def test_assistant_citations_idempotency_and_daily_limit(client,tmp_path,request_body):
    model=FixtureModel()
    browser=assistant_client(client,tmp_path,model,ai_daily_requests=1)
    body=message(browser,request_body)
    first=browser.post('/api/v1/assistant/messages',json=body).json()
    assert first['status']=='complete' and first['result']['evidence_ids']==['mill-plans']
    assert browser.post('/api/v1/assistant/messages',json=body).json()==first and model.calls==1
    body['question']='Different rent inputs'
    assert browser.post('/api/v1/assistant/messages',json=body).status_code==409
    body['request_id']='new-question'
    assert browser.post('/api/v1/assistant/messages',json=body).json()['error']['code']=='daily_limit'
    assert model.calls==1


def test_assistant_rejects_invalid_citations_and_wrong_revision(client,tmp_path,request_body):
    browser=assistant_client(client,tmp_path,FixtureModel(invalid=True))
    body=message(browser,request_body)
    result=browser.post('/api/v1/assistant/messages',json=body).json()
    assert result['fallback']['code']=='provider_failure' and result['provider']=='local_rules' and result['model_id'] is None
    body['revision']=0
    assert browser.post('/api/v1/assistant/messages',json=body).status_code==409


def test_model_cannot_invent_rent_or_omit_per_person_label(client,tmp_path,request_body):
    class WrongPrice(FixtureModel):
        def generate(self,prompt,schema):
            result=super().generate(prompt,schema)
            result['answer']='The rent is $1.'
            return result
    browser=assistant_client(client,tmp_path,WrongPrice())
    result=browser.post('/api/v1/assistant/messages',json=message(browser,request_body)).json()
    assert result['provider']=='local_rules' and result['fallback']['code']=='provider_failure'
    assert '$1300' in result['result']['answer'] and '$1.' not in result['result']['answer']


def test_model_cannot_turn_installment_into_term_total(client,tmp_path,request_body):
    class WrongPeriod(FixtureModel):
        def generate(self,prompt,schema):
            result=super().generate(prompt,schema)
            result['answer']='The whole-unit price is $1300 per 12-month term and $650 per person.'
            return result
    browser=assistant_client(client,tmp_path,WrongPeriod())
    result=browser.post('/api/v1/assistant/messages',json=message(browser,request_body)).json()
    assert result['provider']=='local_rules' and result['fallback']['code']=='provider_failure'
    assert 'per installment' in result['result']['answer']


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


def test_local_server_fenced_json_is_accepted_and_wrong_model_identity_rejected(tmp_path):
    answer={'answer':'Test'}
    def fenced(request):
        assert request.url.path=='/v1/chat/completions'
        content='```json\n'+json.dumps(answer)+'\n```'
        return httpx.Response(200,json={'model':'roomwise-gemma-4-e4b-v2','choices':[{'message':{'content':content}}]})
    settings=Settings(tmp_path,external_operations_enabled=True,ai_provider='openai_compatible',
                      ai_model='roomwise-gemma-4-e4b-v2',ai_base_url='http://127.0.0.1:8002/v1')
    assert JSONModel(settings,httpx.MockTransport(fenced)).generate('test',{})==answer
    def other(request):
        return httpx.Response(200,json={'model':'some-other-model','choices':[{'message':{'content':json.dumps(answer)}}]})
    import pytest
    with pytest.raises(ValueError,match='Unexpected model identity'):
        JSONModel(settings,httpx.MockTransport(other)).generate('test',{})


def test_compare_with_billing_words_summarizes_selected_properties(client,request_body):
    body=message(client,request_body)
    body['question']='Explain the differences between shortlisted options, including billing basis and missing costs.'
    result=client.post('/api/v1/assistant/messages',json=body).json()['result']
    assert result['answer_kind']=='evidence'
    assert result['candidate_ids']==['mill-2']
    assert 'The Mill' in result['answer'] and 'per installment' in result['answer']
    assert 'mill-plans' in result['evidence_ids']


def test_local_comparison_summary_follows_requested_shortlist_order(client,request_body):
    body=message(client,request_body)
    body['candidate_ids']=['alight-east','mill-2']
    result=client.post('/api/v1/assistant/messages',json=body).json()['result']
    assert result['candidate_ids']==body['candidate_ids']
    assert result['answer'].index('Alight')<result['answer'].index('The Mill')


def test_property_price_question_with_billing_words_keeps_sourced_plan_facts(client,request_body):
    body=message(client,request_body)
    body['question']='Explain the selected plan asking price and billing basis.'
    result=client.post('/api/v1/assistant/messages',json=body).json()['result']
    assert result['answer_kind']=='evidence'
    assert '$1300' in result['answer'] and 'mill-plans' in result['evidence_ids']
