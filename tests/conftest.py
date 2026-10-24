"""Tests use isolated storage and synthetic campus/routing adapters."""
import json
import pytest
from fastapi.testclient import TestClient
from roomwise.app import create_app
from roomwise.config import Settings
from roomwise.repositories.campus import CampusRepository


@pytest.fixture
def request_body():
    return dict(campus_id='vt',revision=1,route_date='2026-10-26',
                preferences=dict(monthly_budget_per_person=1000,household_size=2,travel_modes=['walk'],
                                 move_in_date='2027-08-20',move_out_date='2028-05-15'),
                commitments=[dict(id='c1',building_id='test-classroom',weekdays=['mon'],arrival_time_local='09:00')],
                candidate_ids=['mill-2','alight-east'])


class FixtureRouting:
    provider='synthetic_test_only'
    def estimate(self,candidate,building,commitment,mode,route_date,preferences):
        return dict(candidate_id=candidate['id'],commitment_id=commitment.id,mode=mode,minutes=15,
                    status='supported' if commitment.id=='c1' else 'unavailable',route_date=str(route_date),
                    provider=self.provider,context={'fixture':True},coverage_notes=[],evidence_ids=[])


@pytest.fixture
def client(tmp_path):
    campus=tmp_path/'test-campus.json'
    campus.write_text(json.dumps({'campuses':[{'id':'vt','name':'VT test fixture','timezone':'America/New_York','buildings':[
        {'id':'test-classroom','label':'Synthetic classroom','lat':37.0,'lon':-80.0,'source':'https://example.test/building','verified':True}]}]}))
    app=create_app(Settings(tmp_path/'records'),campuses=CampusRepository(campus),routing=FixtureRouting())
    with TestClient(app) as browser:yield browser
