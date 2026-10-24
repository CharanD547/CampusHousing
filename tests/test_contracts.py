import json
from pathlib import Path
from roomwise.api.schemas import AIExplanation,ComparisonInput

ROOT=Path(__file__).resolve().parents[1]


def test_generated_contract_matches_live_api(client):
    generated=json.loads((ROOT/'contracts/v1.openapi.json').read_text(encoding='utf-8'))
    assert generated==client.app.openapi()
    for path in generated['paths']:
        assert path=='/' or path.startswith('/api/v1/')


def test_fixtures_are_labeled_and_schema_valid():
    request=json.loads((ROOT/'contracts/fixtures/comparison.request.json').read_text())
    response=json.loads((ROOT/'contracts/fixtures/ai-unavailable.response.json').read_text())
    assert request['fixture_mode'] is True and response['fixture_mode'] is True
    ComparisonInput.model_validate(request['payload'])
    AIExplanation.model_validate(response['payload'])
