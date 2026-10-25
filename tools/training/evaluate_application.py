"""Run six local application cases and retain actual responses for qualitative review.

This is not an accuracy grader. It never reports target-data validation as inference.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid
import httpx

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from roomwise.config import Settings,now


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8001)
    parser.add_argument('--output',type=Path,default=ROOT/'var/rubric-review-20261025/application-evaluation.json')
    args=parser.parse_args();settings=Settings.from_env()
    headers={'Authorization':'Bearer '+settings.api_token} if settings.api_token else {}
    rows=[]
    with httpx.Client(base_url=f'http://127.0.0.1:{args.port}/api/v1',headers=headers,timeout=70) as client:
        catalog=client.get('/candidates');catalog.raise_for_status();catalog=catalog.json()['candidates']
        suite=json.loads((ROOT/'data/evaluation/submission-cases.json').read_text(encoding='utf-8'))
        for case in suite['cases']:
            candidate=next(c for c in catalog if c['property_id']==case['property_id'])
            comparison=client.post('/comparisons',json={'campus_id':'vt','revision':0,'route_date':'2026-10-25',
                'preferences':{'monthly_budget_per_person':1100,'household_size':2,'travel_modes':['walk']},
                'commitments':[],'candidate_ids':[candidate['id']]})
            comparison.raise_for_status();comparison=comparison.json();started=time.monotonic()
            response=client.post('/assistant/messages',json={'comparison_id':comparison['id'],'revision':0,
                'request_id':str(uuid.uuid4()),'candidate_ids':[candidate['id']],'question':case['question'],'history':[]})
            response.raise_for_status();body=response.json()
            row={**case,'candidate_id':candidate['id'],'latency_seconds':round(time.monotonic()-started,2),
                 'response':body,'review_status':'needs_qualitative_review'};rows.append(row)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps({'run_at':now(),'mode':'actual_application_requests','cases':rows,
                'limitation':suite['purpose']},indent=2),encoding='utf-8')
            print(case['id'],body.get('provider'),row['latency_seconds'],flush=True)


if __name__=='__main__':main()
