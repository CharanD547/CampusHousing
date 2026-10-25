/* Same-origin API integration. Missing providers never fall back to fixture results. */
const API = {ready:false, health:null, comparison:null, comparisonKey:null, comparing:false,
  comparisonError:null, sync:'starting', syncing:false, dirty:false, conflict:false,
  checklistPending:false, checklistError:null, checklistKey:null};
let workspaceTimer, comparisonTimer;
let workspaceID;
try {workspaceID=localStorage.getItem('roomwise.workspace');} catch(error) {storageOk=false;}
if (!workspaceID) {
  workspaceID='browser-'+requestID();
  try {localStorage.setItem('roomwise.workspace',workspaceID);} catch(error) {storageOk=false;}
}

async function api(path, options={}) {
  if (S.sim.aiFails && path==='/assistant/messages') throw new Error('AI service unavailable (test state). Turn off the test state to retry.');
  if (S.sim.offline) throw new Error('Offline: changes remain in this browser until you reconnect.');
  let token;try {token=sessionStorage.getItem('roomwise.token');} catch(error) {}
  const response=await fetch('/api/v1'+path,{...options,signal:options.signal || AbortSignal.timeout(path==='/assistant/messages' ? 65000:20000),
    headers:{'Content-Type':'application/json',...(token ? {Authorization:'Bearer '+token}:{}),...options.headers}});
  const body=await response.json();
  if (!response.ok) {
    const error=new Error(body.error?.message || 'The backend request could not finish.');
    error.status=response.status; error.code=body.error?.code; throw error;
  }
  return body;
}

function cleanPreferences(p=S.prefs) {
  const {campus_id,...preferences}=p;
  return {...preferences,move_in_date:preferences.move_in_date || null,move_out_date:preferences.move_out_date || null};
}
function cleanCommitments() { return []; }
function cleanChecklist(items=S.guide.checklist || []) {
  return items;
}
function comparisonInput() {
  return {campus_id:'vt',revision:S.revision,preferences:cleanPreferences(),commitments:cleanCommitments(),
    route_date:S.route_date,routing_scope:S.routing_scope || 'single_date',candidate_ids:[]};
}
function comparisonKey() { return JSON.stringify(comparisonInput()); }

function routingMeetingDates(commitment,date,scope) {
  if(scope!=='representative_week')return [date];
  const monday=parseDate(date);monday.setUTCDate(monday.getUTCDate()-(monday.getUTCDay()+6)%7);
  return DAYS.flatMap(([day],i)=>{if(!commitment.weekdays.includes(day))return [];const value=new Date(monday);value.setUTCDate(value.getUTCDate()+i);return [value.toISOString().slice(0,10)];});
}

function normalizeCandidate(c) {
  const price={...c.offer.price,amount:c.offer.price.amount==null ? null : Number(c.offer.price.amount),
    last_reviewed_at:campusDate(c.offer.price.last_reviewed_at)};
  return {...c,area:'Blacksburg, VA',offer:{...c.offer,price,lease:c.offer.contract,
    term:c.offer.price.term.label,byTheBed:c.offer.price.basis==='per_person',included:[],
    fees:c.offer.fees.map(f=>normalizeFee(f,c.sources))},evidence:[]};
}

// Structured fees keep their classification; legacy upfront rows keep the refundable flag.
const FEE_KIND={MANDATORY_RECURRING:'mandatory',MANDATORY_ONE_TIME:'one_time',REFUNDABLE_DEPOSIT:'refundable',
  CREDITED_PREPAYMENT:'credited',OPTIONAL_ADDON:'optional',CONDITIONAL_SITUATIONAL:'optional'};
const FEE_FREQUENCY={PER_INSTALLMENT:'installment',PER_CALENDAR_MONTH:'calendar_month'};
const FEE_BASIS={PER_BED_INSTALLMENT:'per_person',PER_APPLICANT:'per_applicant',PER_PRIMARY_LEASEHOLDER:'per_leaseholder',PER_PET:'per_pet'};
function normalizeFee(f,sources) {
  const raw=f.amount ?? f.amount_min;
  const reviewed=[f.source_id,f.basis_source_id].filter(Boolean).every(id=>(sources||[]).find(s=>s.id===id)?.review_status==='reviewed');
  return {...f,label:f.label || f.name || 'Charge',amount:raw==null ? null:Number(raw),
    amount_max:f.amount_max==null ? null:Number(f.amount_max),
    kind:f.timing_event==='PER_TERM' ? 'term' : FEE_KIND[f.classification] || (f.refundable ? 'refundable' : 'one_time'),
    basis:f.scaling_basis==='PER_UNIT' || f.basis==='unit' ? 'whole_unit' : FEE_BASIS[f.scaling_basis] || f.basis || 'per_person',
    frequency:FEE_FREQUENCY[f.timing_event] || f.frequency,
    research:f.classification ? !reviewed : false};
}

function compare(cand,prefs,commitments) {
  const current=API.comparisonKey===comparisonKey();
  const result=current ? API.comparison?.candidate_results.find(r=>r.candidate_id===cand.id) : null;
  const per=commitments.flatMap(c=>{
    const b=building(c.building_id) || {short:'Unknown building',label:'Unknown building'};
    const matching=result?.commute_estimates.filter(e=>e.commitment_id===c.id) || [];
    const dates=[...new Set(matching.map(e=>e.route_date))];
    if (!dates.length) dates.push(...routingMeetingDates(c,S.route_date,S.routing_scope));
    return dates.map(date=>{
      const ests=prefs.travel_modes.map(mode=>{
        const r=matching.find(e=>e.mode===mode && e.route_date===date);
        return r ? {...r,context:r.coverage_notes.join(' ')} : {mode,status:'unavailable',minutes:null,context:'Comparison not available for these inputs.'};
      });
      return {c,b,date,ests,best:ests.filter(e=>e.status==='supported').sort((a,b)=>a.minutes-b.minutes)[0] || null};
    });
  });
  const supported=per.filter(x=>x.best);
  // Every catalog offer is a documented criteria match; conflicts and gaps are shown as notes.
  const fit='fit';
  const conflicts=[];
  const unknowns=[];
  const subtotal=result?.known_recurring_subtotal;
  const base=result?.cost_breakdown?.per_person ?? subtotal;
  const share=subtotal==null ? null : {base:Number(base),mandatory:Number(subtotal)-Number(base),subtotal:Number(subtotal),
    unknown:result.unknown_costs,complete:!result.unknown_costs.length,stale:daysBetween(cand.offer.price.last_reviewed_at,TODAY)>STALE_AFTER_DAYS,
    scenario:cand.offer.price.basis==='whole_unit',frequency:cand.offer.price.frequency,reviewed:cand.offer.price.last_reviewed_at};
  const checks=result?.notes || [];
  return {cand,fit,conflicts,unknowns,checks,share,commute:{per,supported:supported.length,
    within:supported.filter(x=>x.best.minutes<=prefs.max_commute_minutes).length,total:result?.total_commitments ?? per.length,
    limiting:[...supported].sort((a,b)=>b.best.minutes-a.best.minutes)[0] || null}};
}

function workspaceMessage() {
  if (!storageOk) return 'Browser storage is blocked. Backend sync: '+API.sync+'.';
  if (API.workspaceTrashed) return 'This workspace is in recoverable trash. Restore it in Data and reload to resume.';
  if (API.conflict) return 'Another tab changed this workspace. Reload before editing again; local changes are retained.';
  return API.sync==='saved' ? 'Saved in this browser and the local backend.' : 'Saved in this browser. Backend sync: '+API.sync+'.';
}
function renderConnectionStatus() {
  const el=document.getElementById('connection-status');
  if (!el) return;
  const h=API.health?.dependencies;
  el.innerHTML=`<b>${S.sim.offline ? 'Offline · using last loaded data' : API.comparing ? 'Updating comparison…' : API.comparisonError ? esc(API.comparisonError) : 'Connected to Roomwise'}</b>
    <span>${new Set(CANDIDATES.map(c=>c.property_id)).size} places · ${CANDIDATES.filter(c=>c.offer.price.amount!=null).length} priced plans · ${new Set(CANDIDATES.filter(c=>c.guide_reference).map(c=>c.property_id)).size} places with additional research · ${API.health?.assistant?.status==='configured_requires_verification'?'Gemma chat configured': 'Local research helper'}</span>
    ${API.account?.required ? '<button class="btn btn-sm" data-action="account-logout">Sign out</button>' : ''}
    ${API.comparisonError ? '<button class="btn btn-sm" data-action="refresh-comparison">Retry comparison</button>' : ''}
    ${API.workspaceTrashed ? '<span>Workspace is in recoverable trash. Restore it in Data and reload to resume.</span>' : API.conflict ? '<span>Workspace sync paused: another tab has saved changes. Your local draft is retained.</span><button class="btn btn-sm" data-action="resolve-workspace-conflict">Back up local draft and load server copy</button>' : ''}`;
}
function queueWorkspaceSave() {
  if (!API.ready || API.conflict) return;
  API.dirty=true; API.sync='pending';
  clearTimeout(workspaceTimer); workspaceTimer=setTimeout(syncWorkspace,500);
}
async function syncWorkspace() {
  if (API.syncing || !API.dirty || API.conflict || !API.ready) return;
  if (typeof prefErrors==='function' && prefErrors(S.prefs).length) {API.sync='waiting for valid preferences';renderConnectionStatus();return;}
  API.syncing=true; API.dirty=false;
  const body={revision:S.workspaceRevision || 0,preferences:cleanPreferences(),commitments:cleanCommitments(),
    selected_candidate_ids:S.shortlist,checklist:cleanChecklist(),questions:[],current_step:S.guide.current_step,
    completed_steps:S.guide.completed_steps,input_revision:S.revision,route_date:S.route_date,routing_scope:S.routing_scope || 'single_date',notes:S.notes,
    brief_ids:S.briefs.map(b=>b.id).slice(0,100),guide_started:S.guide.started,guide_candidate_ids:S.guide.selected_candidate_ids};
  try {
    const saved=await api('/workspaces/'+workspaceID,{method:'PUT',body:JSON.stringify(body)});
    S.workspaceRevision=saved.revision; API.sync='saved';S.pendingSync=API.dirty;
    localStorage.setItem(STORE_KEY,JSON.stringify(S));
  } catch(error) {
    API.sync=error.message;
    if (error.status===409) API.conflict=true;
  } finally {
    API.syncing=false;
    document.getElementById('store-note').textContent=workspaceMessage();
    renderConnectionStatus();
    if (API.dirty && !API.conflict) {clearTimeout(workspaceTimer);workspaceTimer=setTimeout(syncWorkspace,500);}
  }
}
function queueComparison() {
  if (!API.ready) return;
  API.checklistKey=null;
  API.checklistError=null;
  clearTimeout(comparisonTimer); comparisonTimer=setTimeout(()=>refreshComparison(),200);
}
async function refreshComparison() {
  if(typeof prefErrors==='function' && prefErrors(S.prefs).length) {API.comparing=false;API.comparisonError='Complete valid preferences to update this comparison.';renderConnectionStatus();return;}
  const body=comparisonInput(),key=JSON.stringify(body);
  API.comparing=true;API.comparisonError=null;renderConnectionStatus();
  try {
    const result=await api('/comparisons',{method:'POST',body:JSON.stringify(body)});
    if (comparisonKey()!==key) return;
    API.comparison=result;API.comparisonKey=key;
  } catch(error) {if (comparisonKey()===key) API.comparisonError=error.message;}
  finally {if (comparisonKey()===key) {API.comparing=false;render();}}
}
async function ensureComparison() {
  if (API.comparisonKey!==comparisonKey()) await refreshComparison();
  if (API.comparisonKey!==comparisonKey()) throw new Error(API.comparisonError || 'Wait for the current comparison.');
  return API.comparison;
}

async function runAI() {
  if (S.ai.status==='pending' || !S.shortlist.length) return;
  const revision=S.revision, ids=S.shortlist.slice(0,3), selection=JSON.stringify(ids);
  S.ai={flow:'assistant-v2',status:'pending',revision,selection,result:null};render();
  try {
    const comparison=await ensureComparison();
    const response=await api('/assistant/messages',{method:'POST',body:JSON.stringify({comparison_id:comparison.id,revision,request_id:requestID(),candidate_ids:ids,history:[],
      question:'Explain the differences between these shortlisted housing options. Use only the comparison and its sources: known costs and billing basis, fit, missing information, and what to ask next. Guide references are unverified, not current rental quotes.'})});
    if (S.revision!==revision || JSON.stringify(S.shortlist.slice(0,3))!==selection) {S.ai={...S.ai,status:'discarded'};return;}
    if (response.status!=='complete' || !response.result) throw new Error(response.error?.message || 'The explanation could not finish.');
    S.ai={...S.ai,status:'done',result:{...response.result,provider:response.provider,model_id:response.model_id,fallback:response.fallback}};
  } catch(error) {S.ai={...S.ai,status:'unavailable',reason:error.message};}
  finally {save();render();}
}

function queueChecklist() {
  if (API.checklistPending || API.checklistError) return;
  API.checklistPending=true;
  setTimeout(async()=>{
    try {
      const comparison=await ensureComparison();
      const revision=S.revision;
      const ids=guideCandidates().map(r=>r.cand.id).slice(0,3);
      const key=JSON.stringify([revision,ids]);
      const old=S.guide.checklist || [];
      const items=[];
      for (const id of ids) {
        const previous=old.filter(i=>i.candidate_id===id || i.origin==='user');
        const result=await api('/guide/checklist',{method:'POST',body:JSON.stringify({comparison_id:comparison.id,
          revision,request_id:requestID(),candidate_id:id,previous_items:cleanChecklist(previous)})});
        for (const item of result.checklist) if (!items.some(i=>i.id===item.id)) items.push({...item,candidate_id:id});
      }
      if (S.revision!==revision) return;
      S.guide.checklist=items;API.checklistKey=key;save();
    } catch(error) {API.checklistError=error.message;}
    finally {API.checklistPending=false;render();}
  },0);
}

function briefForDisplay(b) {
  const comparison=b.comparison,prefs={campus_id:'vt',...comparison.inputs.preferences};
  const catalog=new Map((comparison.catalog_snapshot || []).map(c=>[c.id,normalizeCandidate(c)]));
  const buildings=new Map((comparison.building_snapshot || []).map(x=>[x.id,x]));
  return {id:b.id,saved_at:b.saved_at,origin:b.origin || 'shortlist',revision:comparison.input_revision,
    prefs,routing_date:comparison.inputs.route_date,
    commitments:comparison.inputs.commitments.map(c=>({building:buildings.get(c.building_id)?.label || c.building_id,
      weekdays:c.weekdays,arrival:c.arrival_time_local,sample:!!c.is_example})),
    candidates:b.selected_candidate_ids.map(id=>comparison.candidate_results.find(r=>r.candidate_id===id)).filter(Boolean).map(r=>{
      const c=catalog.get(r.candidate_id);
      return {id:r.candidate_id,name:c?.property_name || r.candidate_id,type:'offer',
        fit:'fit',
        price:c?.offer.price || null,layout:c?.offer.layout || null,
        share:r.known_recurring_subtotal==null ? null:{subtotal:Number(r.known_recurring_subtotal),complete:false,stale:false},
        conflicts:[],unknowns:[],
        commute:comparison.inputs.commitments.flatMap(k=>routingMeetingDates(k,comparison.inputs.route_date,comparison.inputs.routing_scope).map(date=>{
          const route=r.commute_estimates.filter(e=>e.commitment_id===k.id && e.route_date===date && e.status==='supported').sort((a,b)=>a.minutes-b.minutes)[0];
          return {building:(buildings.get(k.building_id)?.label || k.building_id)+' · '+date,mode:route?.mode || null,minutes:route?.minutes ?? null};})),
        evidence:(c?.sources || []).map(e=>({id:e.id,source:e.title,observed_at:campusDate(e.checked_at)})),
        questions:b.notes?.[r.candidate_id]?.questions || []};
    }),ai:{status:b.ai_status},checklist:b.checklist};
}
async function saveServerBrief(origin) {
  if (API.savingBrief) return;
  if(origin==='guide' && (API.checklistPending || API.checklistKey!==JSON.stringify([S.revision,guideCandidates().map(r=>r.cand.id).slice(0,3)]))) {toast('Wait for the current checklist before saving this brief.');return;}
  API.savingBrief=true;
  try {
    const comparison=await ensureComparison();
    const ids=S.shortlist.slice(0,3);
    if (!ids.length) throw new Error('Shortlist at least one offer before saving.');
    const notes=Object.fromEntries(ids.filter(id=>S.notes[id]).map(id=>[id,S.notes[id]]));
    const b=await api('/briefs',{method:'POST',body:JSON.stringify({comparison_id:comparison.id,
      revision:S.revision,request_id:requestID(),selected_candidate_ids:ids,
      checklist:origin==='guide' ? cleanChecklist():[],notes,origin})});
    S.briefs.unshift(briefForDisplay(b));save();go('#brief-'+b.id);toast('Brief saved to the backend.');
  } catch(error) {toast(error.message);}
  finally {API.savingBrief=false;}
}

async function initRoomwise() {
  if (API.initializing) return;
  API.initializing=true;API.ready=false;
  document.getElementById('main').innerHTML='<div class="wrap page"><h1>Roomwise</h1><p role="status">Loading housing evidence…</p></div>';
  try {
    const account=await api('/auth/status');API.account=account;
    if (account.required && account.owner) {
      const key='roomwise.account.'+account.owner;
      if (STORE_KEY!==key) {STORE_KEY=key;S=loadState() || defaultState();workspaceID='account-'+account.owner;}
    }
    const [health,catalog,maps]=await Promise.all([api('/health'),api('/candidates'),api('/maps/config')]);
    API.maps=maps;
    API.health=health;
    CANDIDATES.splice(0,CANDIDATES.length,...catalog.candidates.map(normalizeCandidate));
    LIVE_PRICES_AT=CANDIDATES.map(c=>c.offer.price.last_reviewed_at).sort().pop() || null;
    if (!CANDIDATES.length) throw new Error('No catalog offers are currently available.');
    const evidenceIDs=[...new Set(CANDIDATES.flatMap(c=>c.sources.map(s=>s.id)))];
    const evidence=await Promise.all(evidenceIDs.map(id=>api('/evidence/'+encodeURIComponent(id)).catch(()=>null)));
    for (const c of CANDIDATES) c.evidence=c.sources.map(s=>evidence.find(e=>e?.id===s.id) || {id:s.id,source_name:s.title,
      source_type:'operator',url:s.url,observed_at:s.checked_at,supports:'Source metadata; full evidence unavailable.'}).map(e=>({...e,observed_at:campusDate(e.observed_at)}));
    const properties=[...new Set(CANDIDATES.map(c=>c.property_id))];
    const research=await Promise.all(properties.map(id=>api('/research/housing/'+id).catch(()=>null)));
    for (const c of CANDIDATES) c.research=research.find(r=>r?.property_id===c.property_id)?.observations || [];
    try {
      const w=await api('/workspaces/'+workspaceID);
      if (S.pendingSync) {
        if (w.revision!==S.workspaceRevision) {API.conflict=true;API.sync='conflict; local changes retained';}
      } else {
      S.prefs={campus_id:'vt',...w.preferences};S.commitments=[];S.shortlist=w.selected_candidate_ids;
      S.notes=w.notes || {};S.workspaceRevision=w.revision;S.revision=w.input_revision || 0;S.route_date=w.route_date || TODAY;S.routing_scope=w.routing_scope || 'single_date';
      S.guide={...S.guide,current_step:w.current_step,completed_steps:w.completed_steps,checklist:w.checklist.length ? w.checklist:null,
        started:w.guide_started,selected_candidate_ids:w.guide_candidate_ids || []};
      // Canonical server snapshots restore briefs even when browser caches have been removed.
      const briefs=await Promise.all((w.brief_ids || []).map(id=>api('/briefs/'+id).catch(()=>null)));
      S.briefs=briefs.filter(Boolean).map(briefForDisplay);API.sync='saved';
      }
    } catch(error) {if (error.status!==404) throw error;}
    S.commitments=[];
    S.shortlist=S.shortlist.filter(id=>candidate(id));ROUTING_DATE=S.route_date;
    API.ready=true;save();render();await refreshComparison();
  } catch(error) {
    const tokenForm=error.code==='auth_required' ? '<form data-form="account"><p>This is a local server account. Use a unique password; email recovery is unavailable.</p><label for="account-name">Account name</label><input class="input" id="account-name" autocomplete="username" required minlength="3" maxlength="60" pattern="[A-Za-z0-9_-]+"><label for="account-password">Password (12 characters minimum)</label><input class="input" type="password" id="account-password" autocomplete="current-password" required minlength="12" maxlength="128"><button class="btn" type="submit" value="login">Sign in</button><button class="btn" type="submit" value="register">Create local account</button><p id="account-error" role="alert"></p></form>' : error.status===401 ? '<form data-form="api-token"><p>Use the Roomwise operator token from var/lan-access.txt on the server computer. This is not a Google API key. On the server itself, <a href="http://127.0.0.1:8001/">open local Roomwise</a> for automatic local access.</p><label for="api-token">Backend access token</label><input class="input" type="password" id="api-token" autocomplete="off"><button class="btn" type="submit">Connect</button></form>':'';
    document.getElementById('main').innerHTML=`<div class="wrap page"><h1>Roomwise could not connect</h1><p role="alert">${esc(error.message)}</p>${tokenForm}<button class="btn" data-action="retry-api">Retry</button></div>`;
  } finally {API.initializing=false;}
}

document.addEventListener('click',event=>{
  const action=event.target.closest('[data-action]')?.dataset.action;
  if (action==='account-logout') api('/auth/logout',{method:'POST'}).then(()=>{S=defaultState();API.ready=false;location.reload();}).catch(error=>toast(error.message));
  if (action==='refresh-comparison') refreshComparison();
  if (action==='retry-checklist') {API.checklistError=null;queueChecklist();}
  if (action==='resolve-workspace-conflict') {
    try {
      localStorage.setItem('roomwise.recovery.'+Date.now(),JSON.stringify(S));
      S.pendingSync=false;API.conflict=false;initRoomwise();
    } catch(error) {toast('Could not back up the local draft. Server copy was not loaded.');}
  }
});
document.addEventListener('submit',async event=>{
  if (event.target.dataset.form==='account') {
    event.preventDefault();
    const button=event.submitter;button.disabled=true;
    try {
      await api('/auth/'+(button.value==='register'?'register':'login'),{method:'POST',body:JSON.stringify({username:document.getElementById('account-name').value,password:document.getElementById('account-password').value})});
      await initRoomwise();
    }catch(error){document.getElementById('account-error').textContent=error.message;}finally{button.disabled=false;}
  }
  if (event.target.dataset.form==='api-token') {event.preventDefault();sessionStorage.setItem('roomwise.token',document.getElementById('api-token').value.trim());initRoomwise();}
});
window.addEventListener('online',()=>{S.sim.offline=false;queueWorkspaceSave();queueComparison();});
