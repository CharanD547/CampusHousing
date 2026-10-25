"""Start a separate loopback instance with fresh storage; exercise the production HTTP flow."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[2]


def verify(python,port=8003):
    with tempfile.TemporaryDirectory(prefix='roomwise-release-') as directory:
        token=secrets.token_urlsafe(32)
        env={**os.environ,'ROOMWISE_DATA_DIR':directory,'ROOMWISE_API_TOKEN':token,
             'ROOMWISE_MAPS_ENABLED':'false','ROOMWISE_PLACES_ENABLED':'false','ROOMWISE_ROUTES_ENABLED':'false',
             'ROOMWISE_EXTERNAL_ENABLED':'false','ROOMWISE_AI_PROVIDER':'disabled','ROOMWISE_ACCOUNTS_REQUIRED':'false',
             'ROOMWISE_LOCAL_OPERATOR_ENABLED':'false'}
        process=subprocess.Popen([str(python),'-m','uvicorn','roomwise.main:app','--app-dir','src','--host','127.0.0.1','--port',str(port)],
            cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        def call(path,body=None,method=None,auth=True):
            request=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=json.dumps(body).encode() if body is not None else None,
                method=method,headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if auth else {})})
            with urllib.request.urlopen(request,timeout=10) as response:
                content=response.read()
                return json.loads(content) if response.headers.get_content_type()=='application/json' else content.decode()
        try:
            for attempt in range(80):
                if process.poll() is not None:raise RuntimeError('Clean instance exited before becoming ready.')
                try:health=call('/api/v1/health');break
                except (urllib.error.URLError,TimeoutError):time.sleep(.1)
            else:raise RuntimeError('Clean instance did not become ready.')
            assert '<title>Roomwise</title>' in call('/',auth=False)
            assert 'Roomwise privacy' in call('/privacy',auth=False)
            try:call('/api/v1/records',auth=False);raise AssertionError('Bearer protection missing.')
            except urllib.error.HTTPError as error:assert error.code==401
            catalog=call('/api/v1/candidates')['candidates'];assert len(catalog)==304
            assert len({c['property_id'] for c in catalog})==44
            gaps=call('/api/v1/research/lease-gaps')
            assert gaps['priced_properties']==44 and len(gaps['properties'])==47
            assert all(c.get('lease_gaps',{}).get('written_quote_status')=='not_collected' for c in catalog)
            assert len(call('/api/v1/housing-guide')['communities'])==47
            buildings=call('/api/v1/campuses/vt/buildings')['buildings'];assert len(buildings)>=350
            request={'campus_id':'vt','revision':1,'route_date':'2026-10-26','routing_scope':'representative_week',
                     'preferences':{'monthly_budget_per_person':1100,'household_size':2,'travel_modes':['walk','transit']},
                     'commitments':[{'id':'lecture','building_id':'vt-0151','weekdays':['mon','wed'],'arrival_time_local':'09:00'},
                                    {'id':'lab','building_id':'vt-0174','weekdays':['fri'],'arrival_time_local':'14:00'}],
                     'candidate_ids':['alight-east','mill-2']}
            comparison=call('/api/v1/comparisons',request)
            assert len(comparison['candidate_results'])==2
            assert all(row['total_commitments']==3 and row['supported_commitments']==3 for row in comparison['candidate_results'])
            assert all(route['provider']=='bt_gtfs_local' for row in comparison['candidate_results'] for route in row['commute_estimates'])
            workspace={'revision':0,'preferences':request['preferences'],'commitments':request['commitments'],'routing_scope':'representative_week'}
            saved=call('/api/v1/workspaces/smoke',workspace,'PUT');assert saved['revision']==1
            base={'comparison_id':comparison['id'],'revision':1,'request_id':'smoke'}
            checklist=call('/api/v1/guide/checklist',{**base,'candidate_id':'alight-east'})
            brief=call('/api/v1/briefs',{**base,'selected_candidate_ids':['alight-east']})
            assert call('/api/v1/briefs/'+brief['id'])==brief
            helper=call('/api/v1/assistant/messages',{**base,'question':'What does per installment mean?','candidate_ids':['alight-east']})
            assert helper['provider']=='local_rules' and helper['status']=='complete'
            assert call('/api/v1/records/workspaces/smoke/export')['record']==saved
            call('/api/v1/records/workspaces/smoke',method='DELETE')
            call('/api/v1/records/workspaces/smoke/restore',{},'POST')
            assert call('/api/v1/workspaces/smoke')==saved
            return {'status':'passed','storage':'fresh temporary SQLite','runtime':str(python),'catalog_offers':len(catalog),
                    'buildings':len(buildings),'weekly_meetings':3,'http_flows':['public shell/privacy','bearer rejection','catalog/buildings','weekly comparison',
                    'workspace save','checklist','immutable brief reload','local assistant','export/trash/restore'],'live_provider_calls':0}
        finally:
            # A Windows venv launcher can spawn a child Python process. Stopping
            # only the launcher leaves the server holding temporary SQLite files.
            if os.name=='nt':
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW,check=False)
            else:process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--python',type=Path,required=True);parser.add_argument('--port',type=int,default=8003);parser.add_argument('--report',type=Path)
    args=parser.parse_args();result=verify(args.python.resolve(),args.port)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
