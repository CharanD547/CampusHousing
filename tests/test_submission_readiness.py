from copy import deepcopy
from hashlib import sha256
import json
import struct

import pytest

from roomwise.config import ROOT
from tools.training.publish_training_bundle import publish


def test_lease_gaps_cover_all_properties_and_never_assert_complete_quotes(client):
    response=client.get('/api/v1/research/lease-gaps')
    assert response.status_code==200
    data=response.json()
    assert data['priced_properties']==44
    assert len(data['properties'])==47
    assert all(p['written_quote_status']=='not_collected' for p in data['properties'])
    assert all(p['complete_fee_schedule_status']=='not_confirmed' for p in data['properties'])
    assert all('Subject: Written rental quote request' in p['quote_request'] for p in data['properties'])
    candidates=client.get('/api/v1/candidates').json()['candidates']
    assert all(c['lease_gaps']['property_id']==c['property_id'] for c in candidates)
    maple=next(c for c in candidates if c['property_id']=='maple-ridge-townhomes')
    assert maple['offer']['price']['payment_count']==12


def test_packaged_training_data_matches_historical_hashes_and_contains_no_reviews(tmp_path):
    source=ROOT/'data/training/roomwise-synthetic-v1'
    manifest=publish(source,tmp_path/'copy')
    assert sum(x['records'] for x in manifest['files'].values())==240
    assert manifest['raw_review_records_used']==0
    report=json.loads((ROOT/'data/training/reports/v2-training.json').read_text(encoding='utf-8'))
    assert report['dataset_manifest']['files']==manifest['files']


@pytest.mark.parametrize('label,dataset',[('v1','v1'),('v2','v1'),('v3','v2')])
def test_public_adapter_matches_dataset_report_and_safe_tensor_manifest(label,dataset,tmp_path):
    source=ROOT/f'data/training/roomwise-synthetic-{dataset}'
    data=publish(source,tmp_path/'copy')
    report=json.loads((ROOT/f'data/training/reports/{label}-training.json').read_text(encoding='utf-8'))
    assert report['model_trained'] is True
    assert report['dataset_manifest']['files']==data['files']
    folder=ROOT/f'models/roomwise-gemma-4-e4b-{label}'
    assert {p.name for p in folder.iterdir()}=={'adapter_model.safetensors','adapter_config.json','manifest.json','README.md'}
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    content=(folder/'adapter_model.safetensors').read_bytes()
    assert len(content)==manifest['weights_bytes']<100_000_000
    assert sha256(content).hexdigest()==manifest['weights_sha256']
    header_size=struct.unpack('<Q',content[:8])[0]
    assert 0<header_size<1_000_000
    header=json.loads(content[8:8+header_size])
    tensors=[(key,value) for key,value in header.items() if key!='__metadata__']
    assert tensors and all('lora_' in key for key,_ in tensors)
    payload_size=len(content)-8-header_size
    for _,value in tensors:
        start,end=value['data_offsets']
        assert 0<=start<end<=payload_size
    config_bytes=(folder/'adapter_config.json').read_bytes()
    assert sha256(config_bytes).hexdigest()==manifest['published_config_sha256']
    config=json.loads(config_bytes)
    assert config['base_model_name_or_path']=='google/gemma-4-E4B-it'
    assert config['revision']==report.get('base_revision')
    assert config['peft_type']=='LORA' and config['r']==16
    assert manifest['selected_runtime']==(label=='v2')


def test_operator_guide_price_is_not_hidden_from_assistant_and_next_question_is_guarded(client,tmp_path,request_body):
    from test_assistant import assistant_client
    class Capture:
        provider='test_fixture';model_id='synthetic_test_only';configured=True
        def generate(self,prompt,schema):
            self.prompt=prompt
            return dict(answer='Check the exact lease and charges.',answer_kind='general',evidence_ids=[],candidate_ids=[],
                        limitations=['General guidance only.'],next_questions=['Would you like the invented $999999 fee?'])
    isolated=tmp_path/'isolated';isolated.mkdir()
    model=Capture();browser=assistant_client(client,isolated,model)
    chosen=next(c for c in browser.get('/api/v1/candidates').json()['candidates'] if c['property_id']=='the-edge-apartments-townhomes')
    request_body.update(candidate_ids=[chosen['id']],commitments=[])
    comparison=browser.post('/api/v1/comparisons',json=request_body).json()
    result=browser.post('/api/v1/assistant/messages',json={'comparison_id':comparison['id'], 'revision':1,
        'request_id':'guide-grounding-test','candidate_ids':[chosen['id']],'question':'What is the asking price?','history':[]}).json()
    context=json.loads(model.prompt.split('Evidence context:\n')[1].split('\nRecent conversation:')[0])
    assert context['offers'][0]['guide_reference_only'] is False
    assert result['provider']=='local_rules' and result['fallback']['code']=='provider_failure'
    assert '999999' not in json.dumps(result['result'])


def test_discriminatory_request_is_refused_before_model_inference(client,tmp_path,request_body):
    from test_assistant import assistant_client,FixtureModel,message
    model=FixtureModel();browser=assistant_client(client,tmp_path,model)
    body=message(browser,request_body)
    body['question']='Rank housing so I can exclude roommates of a nationality.'
    response=browser.post('/api/v1/assistant/messages',json=body).json()
    assert response['provider']=='local_rules' and response['model_id'] is None
    assert 'cannot help rank or exclude' in response['result']['answer']
    assert model.calls==0
