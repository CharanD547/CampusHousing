"""Composition root: routes depend on services, never on old frontend/inspection code."""
import hmac
import json
import re
import uuid
import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from roomwise.api.errors import APIError, error_response
from roomwise.api.schemas import AIExplanation, AssistantInput, AssistantResponse, BriefInput, CatalogResponse, ChecklistInput, ComparisonInput, ComparisonResponse, ExplanationInput, WorkspaceInput
from roomwise.adapters.model import JSONModel
from roomwise.services.assistant import AssistantService
from roomwise.adapters.gemma import UnconfiguredGemmaRuntime
from roomwise.adapters.routing import UnconfiguredRoutingAdapter
from roomwise.adapters.gtfs_routing import FallbackRoutingAdapter, GtfsRoutingAdapter
from roomwise.adapters.google_routes import GoogleRoutesAdapter
from roomwise.adapters.places import GooglePlaces
from roomwise.repositories.provider_budget import ProviderBudget
from roomwise.config import ROOT, Settings
from roomwise.repositories.catalog import CatalogRepository
from roomwise.repositories.campus import CampusRepository
from roomwise.repositories.evidence import EvidenceRepository
from roomwise.repositories.workspace import WorkspaceStore
from roomwise.repositories.accounts import Accounts,actor
from roomwise.api.schemas import AccountInput
from roomwise.services.comparison import ComparisonService, candidates, catalog_fingerprint
from roomwise.services.gemma import explain
from roomwise.services.guide import checklist


def create_app(settings=None, *, campuses=None, routing=None, gemma=None, assistant_model=None):
    settings=settings or Settings.from_env()
    app=FastAPI(title='Roomwise',version='1.0.0',description='Student housing decisions with source-backed prices and explicit provider coverage.')
    catalog=CatalogRepository(settings.data_dir)
    campuses=campuses or CampusRepository()
    store=WorkspaceStore(settings.data_dir)
    accounts=Accounts(settings.data_dir)
    evidence=EvidenceRepository(catalog)
    maps_budget=ProviderBudget(settings.data_dir/'maps-requests.sqlite3',settings.maps_daily_requests,
                               reserve_places=min(8,settings.maps_daily_requests//5))
    routing=routing or (FallbackRoutingAdapter(GoogleRoutesAdapter(settings,maps_budget),GtfsRoutingAdapter()) if settings.routes_enabled and settings.routes_api_key else GtfsRoutingAdapter())
    places=GooglePlaces(settings,maps_budget)
    gemma=gemma or UnconfiguredGemmaRuntime()
    comparisons=ComparisonService(catalog,campuses,routing,store)
    assistant=AssistantService(settings,assistant_model or JSONModel(settings))
    app.state.catalog,app.state.store= catalog,store
    if settings.allowed_origins:
        app.add_middleware(CORSMiddleware,allow_origins=list(settings.allowed_origins),allow_methods=['GET','POST','PUT','DELETE'],allow_headers=['Authorization','Content-Type','X-Request-ID'])

    @app.middleware('http')
    async def guard(request:Request, call_next):
        started=time.monotonic()
        supplied=request.headers.get('x-request-id','')
        request.state.request_id=supplied if re.fullmatch(r'[A-Za-z0-9_-]{1,80}',supplied) else uuid.uuid4().hex
        if not settings.api_token and request.url.hostname not in ('127.0.0.1','localhost','::1','testserver'):
            return error_response('local_host_required','Use the local Roomwise address.',403,request.state.request_id)
        if request.url.path.startswith('/api/') and request.headers.get('sec-fetch-site')=='cross-site' and request.headers.get('origin') not in settings.allowed_origins:
            return error_response('origin_rejected','Cross-site API requests are not allowed.',403,request.state.request_id)
        public_asset=request.method in ('GET','HEAD') and (request.url.path in ('/','/privacy','/terms') or request.url.path.startswith('/assets/'))
        local_operator=(settings.local_operator_enabled and request.client and request.client.host in ('127.0.0.1','::1')
                        and request.url.hostname in ('127.0.0.1','localhost','::1')
                        and request.headers.get('sec-fetch-site')!='cross-site'
                        and request.headers.get('origin',str(request.base_url).rstrip('/')).rstrip('/')==str(request.base_url).rstrip('/'))
        if settings.api_token and not public_asset and not local_operator:
            if not hmac.compare_digest(request.headers.get('authorization',''), 'Bearer '+settings.api_token):
                return error_response('unauthorized','Valid API bearer token required.',401,request.state.request_id)
        elif not settings.api_token and request.client and request.client.host not in ('127.0.0.1','::1','testclient'):
            return error_response('local_only','Configure access controls before serving remote clients.',403,request.state.request_id)
        try:
            length=int(request.headers.get('content-length','0') or 0)
        except ValueError:
            return error_response('invalid_length','Invalid content length.',400,request.state.request_id)
        if length>256000:
            return error_response('payload_too_large','Request exceeds the local API limit.',413,request.state.request_id)
        account_route=request.url.path.startswith('/api/v1/auth/') or request.url.path=='/api/v1/health'
        if settings.accounts_required and request.method not in ('GET','HEAD','OPTIONS'):
            origin=request.headers.get('origin')
            if origin and origin.rstrip('/')!=str(request.base_url).rstrip('/'):
                return error_response('origin_rejected','Use this application origin.',403,request.state.request_id)
        owner=accounts.owner(request.cookies.get('roomwise_session')) if settings.accounts_required else 'local'
        if settings.accounts_required and not owner and not public_asset and not account_route:
            return error_response('auth_required','Sign in to a local Roomwise account.',401,request.state.request_id)
        context=actor.set(owner or 'unauthenticated')
        try:response=await call_next(request)
        finally:actor.reset(context)
        response.headers['X-Request-ID']=request.state.request_id
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        logging.getLogger('uvicorn.error').info('roomwise_request %s',json.dumps({
            'request_id':request.state.request_id,'method':request.method,
            'route':getattr(request.scope.get('route'),'path','unmatched'),
            'status':response.status_code,'duration_ms':round((time.monotonic()-started)*1000,1)}))
        return response

    @app.exception_handler(APIError)
    async def domain_error(request,exc):
        return error_response(exc.code,exc.message,exc.status,request.state.request_id,exc.retryable)

    @app.exception_handler(RequestValidationError)
    async def input_error(request,exc):
        # Never echo submitted schedules or payloads into error bodies.
        return error_response('validation_error','Invalid request fields; see the versioned OpenAPI schema.',422,request.state.request_id)

    @app.exception_handler(HTTPException)
    async def http_error(request,exc):
        return error_response('not_found' if exc.status_code==404 else 'http_error','Requested API resource is unavailable.',exc.status_code,request.state.request_id)

    @app.exception_handler(Exception)
    async def unexpected_error(request,exc):
        return error_response('backend_failure','The operation could not finish. Saved records were retained.',500,
                              getattr(request.state,'request_id',uuid.uuid4().hex),True)

    @app.get('/')
    def root(): return FileResponse(ROOT/'CampusHousing-main/index.html', media_type='text/html')

    @app.get('/privacy',include_in_schema=False)
    def privacy():return FileResponse(ROOT/'CampusHousing-main/src/privacy.html',media_type='text/html')

    @app.get('/terms',include_in_schema=False)
    def terms():return FileResponse(ROOT/'CampusHousing-main/src/terms.html',media_type='text/html')

    app.mount('/assets',StaticFiles(directory=ROOT/'CampusHousing-main/src'),name='assets')

    @app.get('/api/v1/auth/status')
    def auth_status(request:Request):
        return {'required':settings.accounts_required,'owner':accounts.owner(request.cookies.get('roomwise_session')) if settings.accounts_required else 'local'}

    def account_response(request,body,register=False):
        if not settings.accounts_required:raise APIError('accounts_disabled','Local accounts are disabled.',409)
        owner,token=accounts.authenticate(body.username,body.password,request.client.host if request.client else 'local',register)
        response=JSONResponse({'owner':owner,'scope':'Local account on this server; no email recovery or cloud identity.'})
        response.set_cookie('roomwise_session',token,max_age=86400,httponly=True,samesite='strict',secure=request.url.scheme=='https')
        return response

    @app.post('/api/v1/auth/register')
    def register(body:AccountInput,request:Request):return account_response(request,body,True)

    @app.post('/api/v1/auth/login')
    def login(body:AccountInput,request:Request):return account_response(request,body)

    @app.post('/api/v1/auth/logout')
    def logout(request:Request):
        accounts.logout(request.cookies.get('roomwise_session',''))
        response=JSONResponse({'status':'signed_out'});response.delete_cookie('roomwise_session');return response

    @app.get('/api/v1/health')
    def health():
        return dict(status='ready',storage='isolated_local_accounts' if settings.accounts_required else 'single_user_local_sqlite',catalog_offers=len(candidates(catalog.catalog())),
                    dependencies={'verified_buildings':'ready' if any(c['buildings'] for c in campuses.campuses) else 'not_configured',
                                  'routing':getattr(routing,'provider','injected_adapter'),
                                  'gemma':'not_configured' if getattr(gemma,'model_id',None) is None else 'runtime_requires_verification',
                                  'reviews':'not_configured'},
                    assistant={'provider':assistant.model.provider,'model_id':assistant.model.model_id,
                               'status':'configured_requires_verification' if assistant.model.configured and settings.external_operations_enabled else 'not_configured',
                               'local_helper':'available_without_model',
                               'daily_request_limit':settings.ai_daily_requests},
                    external_operations_enabled=settings.external_operations_enabled,shared_pilot_ready=False)

    @app.get('/api/v1/campuses')
    def list_campuses(): return {'campuses':[{k:v for k,v in c.items() if k!='buildings'} for c in campuses.campuses]}

    @app.get('/api/v1/maps/config')
    def maps_config():
        return {'enabled':bool(settings.maps_enabled and settings.maps_javascript_api_key),
                'browser_key':settings.maps_javascript_api_key if settings.maps_enabled else '',
                'places_available':bool(settings.places_enabled and settings.places_api_key)}

    @app.get('/api/v1/properties/{property_id}/nearby')
    def nearby(property_id:str,category:str='groceries',radius:int=2500):
        prop=next((p for p in catalog.catalog() if p['id']==property_id),None)
        if not prop:raise APIError('unknown_property','Choose a catalog property.',404)
        return places.nearby(prop,category,radius)

    @app.get('/api/v1/housing-guide')
    def housing_guide():
        with catalog.connect() as db:
            rows=[json.loads(r[0]) for r in db.execute('SELECT body FROM housing_guide ORDER BY rowid')]
        return {'status':'research_directory','communities':rows,
                'scope':'Addresses and layouts extracted from the supplied guide. Guide price ranges, opinions and legal claims are not verified offers. Only linked catalog plans enter comparisons.'}

    @app.get('/api/v1/campuses/{key}/buildings')
    def buildings(key:str):
        campus=campuses.get(key)
        return {'campus_id':key,'status':'available' if campus['buildings'] else 'unavailable','buildings':campus['buildings']}

    @app.get('/api/v1/candidates',response_model=CatalogResponse)
    def list_candidates(campus_id:str='vt'):
        campuses.get(campus_id)
        return {'campus_id':campus_id,'candidates':candidates(catalog.catalog())}

    @app.get('/api/v1/evidence/{key}')
    def get_evidence(key:str): return evidence.get(key)

    @app.get('/api/v1/research/housing/{property_id}')
    def housing_research(property_id:str):
        if property_id not in {p['id'] for p in catalog.catalog()}:
            raise APIError('unknown_property','Choose a property in the catalog.',404)
        research=json.loads((ROOT/'data/housing-research-observations.json').read_text(encoding='utf-8'))
        return {'property_id':property_id,'reviewed_on':research['reviewed_on'],
                'status':'research_requires_offer_reconciliation','included_in_comparison_totals':False,
                'observations':[o for o in research['observations'] if o['property_id']==property_id]}

    @app.post('/api/v1/comparisons',response_model=ComparisonResponse)
    def compare(body:ComparisonInput): return comparisons.compare(body)

    def checked_comparison(body):
        result=store.get('comparisons',body.comparison_id)
        if result['input_revision']!=body.revision:
            raise APIError('revision_conflict','Comparison belongs to another input revision.',409)
        return result

    @app.post('/api/v1/assistant/messages',response_model=AssistantResponse)
    def assistant_message(body:AssistantInput):
        comparison=checked_comparison(body)
        if comparison['catalog_fingerprint']!=catalog_fingerprint(catalog.catalog()):
            raise APIError('comparison_stale','Catalog changed. Recompute before asking the assistant.',409)
        return assistant.answer(body,comparison,evidence)

    @app.post('/api/v1/ai/explain',response_model=AIExplanation)
    def ai_explain(body:ExplanationInput):
        comparison=checked_comparison(body)
        if comparison['catalog_fingerprint']!=catalog_fingerprint(catalog.catalog()):
            raise APIError('comparison_stale','Catalog changed. Recompute before generating an explanation.',409)
        runtime=gemma if settings.external_operations_enabled else UnconfiguredGemmaRuntime()
        return explain(runtime,comparison,evidence)

    @app.get('/api/v1/workspaces/{key}')
    def get_workspace(key:str): return store.get('workspaces',key)

    @app.put('/api/v1/workspaces/{key}')
    def put_workspace(key:str,body:WorkspaceInput):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',key): raise APIError('invalid_id','Use a bounded workspace ID.')
        allowed={c['id'] for c in candidates(catalog.catalog())}
        if not set(body.selected_candidate_ids)<=allowed: raise APIError('unknown_candidate','Choose catalog candidates.')
        return store.save_workspace(key,body.model_dump(mode='json'))

    @app.post('/api/v1/guide/checklist')
    def guide(body:ChecklistInput): return checklist(checked_comparison(body),body)

    @app.post('/api/v1/briefs')
    def save_brief(body:BriefInput):
        comparison=checked_comparison(body)
        allowed={c['candidate_id'] for c in comparison['candidate_results']}
        if len(set(body.selected_candidate_ids))!=len(body.selected_candidate_ids) or not set(body.selected_candidate_ids)<=allowed:
            raise APIError('unknown_candidate','Select distinct candidates in this comparison.')
        return store.save_brief(body.model_dump(mode='json'),
                               {'comparison':comparison,'selected_candidate_ids':body.selected_candidate_ids,
                                'checklist':[x.model_dump() for x in body.checklist],'ai_status':'not_included',
                                'notes':{key:value.model_dump() for key,value in body.notes.items() if key in body.selected_candidate_ids},
                                'origin':body.origin,
                                'scope':'Immutable research snapshot; checklist notes/status are user-supplied.'})

    @app.get('/api/v1/briefs/{key}')
    def get_brief(key:str): return store.get('briefs',key)

    @app.get('/api/v1/records/{collection}/{key}/export')
    def export_record(collection:str,key:str):
        if collection not in ('workspaces','comparisons','briefs'):raise APIError('invalid_collection','Choose workspaces, comparisons or briefs.')
        return {'format':'roomwise-record-v1','collection':collection,'record':store.get(collection,key)}

    @app.get('/api/v1/records')
    def list_records():return {'records':store.records(),'scope':'Current local operator or signed-in account. Latest 200 records per collection.'}

    @app.delete('/api/v1/records/{collection}/{key}')
    def trash_record(collection:str,key:str):return store.trash_record(collection,key)

    @app.post('/api/v1/records/{collection}/{key}/restore')
    def restore_record(collection:str,key:str):return store.trash_record(collection,key,True)

    return app
