from datetime import date
from types import SimpleNamespace
import pytest
from roomwise.adapters.bt_gtfs import journey
from roomwise.adapters.routing import UnconfiguredRoutingAdapter
from roomwise.api.errors import APIError
from roomwise.api.schemas import ComparisonInput
from roomwise.domain.costs import evaluate
from roomwise.services.gemma import EvidenceTools,explain


def test_stale_missing_and_conflicting_costs_never_pass():
    offer=dict(id='o',property_id='p',amount='800',basis='person',period='monthly',contract='individual',room='private',bedrooms=2,
               unknowns=['Electricity unconfirmed'],conflicts=[],start=None,end=None,annual_total=None)
    prefs=dict(budget=1000,household_size=1,room='private',start='2027-01-01',end='2028-01-01')
    result=evaluate(offer,prefs,dict(checked_at='2026-10-01',review_status='reviewed'),today=date(2026,10,24))
    assert result['checks']['budget']=='unknown' and result['stale']


def test_gtfs_never_expands_into_future_service():
    result=journey(dict(lat=37.21,lon=-80.39),'2027-08-20','09:00')
    assert result['status']=='unavailable' and result['journeys']==[]


def test_routing_unconfigured_returns_no_estimate(request_body):
    request=ComparisonInput.model_validate(request_body)
    result=UnconfiguredRoutingAdapter().estimate({'id':'p','coordinate_basis':'representative_address'},
          {'id':'b'},request.commitments[0],'walk',request.route_date,request.preferences)
    assert result['status']=='unavailable' and result['minutes'] is None


def test_model_cannot_publish_unsupported_citations_or_arithmetic():
    comparison={'input_revision':1,'candidate_results':[{'candidate_id':'p','evidence_ids':['source']} ]}
    class BadRuntime:
        def explain(self,*args):return dict(status='complete',model_id='gemma-test',input_revision=1,candidate_explanations=[
            dict(candidate_id='p',summary='Invented',preference_relevance='Budget',evidence_ids=['invented'],limitations=['none'],next_questions=['?'])])
    assert explain(BadRuntime(),comparison,None)['status']=='ai_unavailable'
    tools=EvidenceTools(comparison,None,max_calls=1)
    with pytest.raises(APIError):tools.call('publish_price',candidate_id='p')
    with pytest.raises(APIError):tools.call('get_comparison')
