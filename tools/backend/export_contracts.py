"""Export actual OpenAPI and explicitly synthetic frontend fixtures without providers."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from roomwise.app import create_app
from roomwise.api.schemas import ComparisonInput
from roomwise.config import Settings


def export():
    with TemporaryDirectory(prefix='roomwise-contracts-') as directory:
        app=create_app(Settings(Path(directory)))
        target=ROOT/'contracts';target.mkdir(exist_ok=True)
        (target/'v1.openapi.json').write_text(json.dumps(app.openapi(),indent=2),encoding='utf-8')
    request=dict(campus_id='vt',revision=7,route_date='2026-10-26',
                 preferences=dict(monthly_budget_per_person=1100,household_size=2,travel_modes=['walk','transit']),
                 commitments=[dict(id='c1',building_id='fixture-building',weekdays=['mon'],arrival_time_local='09:00')],candidate_ids=['fixture-offer'])
    ComparisonInput.model_validate(request)
    fixture={'fixture_mode':True,'notice':'Synthetic integration input only. IDs are not live verified buildings or offers.',
             'payload':request}
    fixtures=target/'fixtures';fixtures.mkdir(exist_ok=True)
    (fixtures/'comparison.request.json').write_text(json.dumps(fixture,indent=2),encoding='utf-8')
    (fixtures/'ai-unavailable.response.json').write_text(json.dumps({'fixture_mode':True,'payload':{
        'input_revision':7,'model_id':None,'status':'ai_unavailable','candidate_explanations':[],
        'error':{'code':'gemma_not_configured','message':'No genuine runtime is configured.','retryable':False}}},indent=2),encoding='utf-8')
    print('Exported contracts/v1.openapi.json and labeled request/failure fixtures.')


if __name__=='__main__':export()
