const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

function context(cryptoOverride) {
  const storage=new Map();
  const scope=vm.createContext({console,crypto:cryptoOverride || require('node:crypto').webcrypto,AbortSignal,
    setTimeout,clearTimeout,document:{addEventListener(){}},window:{addEventListener(){}},
    localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},
    sessionStorage:{getItem:()=>null}});
  for (const name of ['data.js','core.js','api.js']) {
    vm.runInContext(fs.readFileSync(path.join(__dirname,'../CampusHousing-main/src',name),'utf8'),scope);
  }
  vm.runInContext(`
    const offer={id:'test-offer',property_id:'test-property',property_name:'Test only',coordinates:{lat:37.2,lon:-80.4},
      sources:[],offer:{price:{amount:'835',basis:'per_person',last_reviewed_at:TODAY,term:{label:'test'}},contract:'unknown',fees:[]}};
    const item=normalizeCandidate(offer);CANDIDATES.push(item);
    S.commitments=[{id:'class',building_id:'classroom',weekdays:['mon'],arrival_time_local:'09:00',sample:true}];
    BUILDINGS.push({id:'classroom',label:'Test classroom',short:'Test classroom'});
    API.comparison={candidate_results:[{candidate_id:'test-offer',fit_state:'insufficient_evidence',
      known_recurring_subtotal:'818.37',hard_conflicts:[],unknown_costs:['Test unresolved costs'],commute_estimates:[]}]};
    API.comparisonKey=comparisonKey();
  `,scope);
  return scope;
}

test('presentation takes the backend subtotal and never invents missing routes',()=>{
  const scope=context();
  assert.equal(vm.runInContext('compare(item,S.prefs,S.commitments).share.subtotal',scope),818.37);
  assert.equal(vm.runInContext('compare(item,S.prefs,S.commitments).commute.supported',scope),0);
  assert.equal(vm.runInContext('compare(item,S.prefs,S.commitments).commute.per[0].ests[0].minutes',scope),null);
  vm.runInContext('S.revision++',scope);
  assert.equal(vm.runInContext('compare(item,S.prefs,S.commitments).share',scope),null);
  assert.equal(vm.runInContext('compare(item,S.prefs,S.commitments).fit',scope),'insufficient');
});

test('unknown prices stay unknown and removed schedules never reach the API',()=>{
  const scope=context();
  assert.equal(vm.runInContext('normalizeCandidate({...offer,offer:{...offer.offer,price:{...offer.offer.price,amount:null}}}).offer.price.amount',scope),null);
  assert.equal(vm.runInContext('cleanCommitments().length',scope),0);
  assert.equal(vm.runInContext('comparisonInput().commitments.length',scope),0);
  assert.equal(vm.runInContext('cleanPreferences().move_in_date',scope),null);
  assert.equal(vm.runInContext('Object.hasOwn(cleanPreferences(),"campus_id")',scope),false);
  assert.equal(vm.runInContext("campusDate('2026-10-25T01:03:07Z')",scope),'2026-10-24');
});

test('frozen briefs use captured building names rather than mutable campus records',()=>{
  const scope=context();
  const label=vm.runInContext(`briefForDisplay({id:'brief',saved_at:TODAY,selected_candidate_ids:[],checklist:[],
    comparison:{input_revision:0,inputs:{preferences:S.prefs,route_date:TODAY,commitments:[{building_id:'classroom',weekdays:['mon'],arrival_time_local:'09:00'}]},
      building_snapshot:[{id:'classroom',label:'Frozen building name'}],catalog_snapshot:[],candidate_results:[]}}).commitments[0].building`,scope);
  assert.equal(label,'Frozen building name');
});

test('weekly coverage keeps each dated meeting instead of choosing one best trip for the week',()=>{
  const scope=context();
  vm.runInContext(`S.routing_scope='representative_week';S.route_date='2026-10-28';S.commitments[0].weekdays=['mon','wed','fri'];
    API.comparison.candidate_results[0].total_commitments=3;
    API.comparison.candidate_results[0].commute_estimates=[
      {commitment_id:'class',route_date:'2026-10-26',mode:'walk',status:'supported',minutes:10,coverage_notes:[]},
      {commitment_id:'class',route_date:'2026-10-28',mode:'walk',status:'unavailable',minutes:null,coverage_notes:[]},
      {commitment_id:'class',route_date:'2026-10-30',mode:'walk',status:'supported',minutes:45,coverage_notes:[]}];
    API.comparisonKey=comparisonKey();`,scope);
  assert.equal(vm.runInContext('compare(item,S.prefs,S.commitments).commute.total',scope),3);
  assert.equal(vm.runInContext('compare(item,S.prefs,S.commitments).commute.supported',scope),2);
  assert.equal(vm.runInContext('compare(item,S.prefs,S.commitments).commute.limiting.best.minutes',scope),45);
});

test('LAN HTTP works when secure-context randomUUID is absent',()=>{
  const webcrypto=require('node:crypto').webcrypto;
  const scope=context({getRandomValues:webcrypto.getRandomValues.bind(webcrypto)});
  const ids=vm.runInContext('[workspaceID,requestID(),requestID()]',scope);
  const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
  assert.match(ids[0],/^browser-/);
  assert.match(ids[1],uuid);assert.match(ids[2],uuid);assert.notEqual(ids[1],ids[2]);
});

test('property groups retain one entry and unknown plan prices never become zero or infinity',()=>{
  const scope=context();
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../CampusHousing-main/src/views2.js'),'utf8'),scope);
  vm.runInContext(`const rows=Array.from({length:6},(_,i)=>({cand:{id:'p-'+i,property_id:'p',offer:{bedrooms:2,layout:'2 bed',price:{amount:null,basis:'unknown',frequency:'other'}}},fit:'insufficient'}));`,scope);
  assert.equal(vm.runInContext('propertyGroups(rows).length',scope),1);
  const html=vm.runInContext('planPrices(propertyGroups(rows)[0])',scope);
  assert.match(html,/Price unconfirmed/);assert.match(html,/Billing basis unconfirmed/);
  assert.doesNotMatch(html,/Infinity|\$0/);
});

test('nearby directions start at property and carry chosen mode and destination place',()=>{
  const scope=context();
  vm.runInContext('const MAPS_TEST=true;',scope);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../CampusHousing-main/src/maps.js'),'utf8'),scope);
  scope.URLSearchParams=URLSearchParams;
  const url=new URL(vm.runInContext(`nearbyDirections(item,{id:'grocery-1',name:'Example store',location:{latitude:37.3,longitude:-80.5}})`,scope));
  assert.equal(url.searchParams.get('origin'),'37.2,-80.4');
  assert.equal(url.searchParams.get('destination_place_id'),'grocery-1');
  assert.equal(url.searchParams.get('travelmode'),'walking');
  assert.equal(url.searchParams.get('api'),'1');
});

test('structured fees keep their classification and research fees are marked as not counted',()=>{
  const scope=context();
  const fees=vm.runInContext(`normalizeCandidate({...offer,sources:[{id:'reviewed',review_status:'reviewed'},{id:'audit',review_status:'research_observation'}],
    offer:{...offer.offer,fees:[
      {id:'billing',label:'Billing',classification:'MANDATORY_RECURRING',timing_event:'PER_INSTALLMENT',scaling_basis:'PER_BED_INSTALLMENT',amount_min:'6.79',amount_max:'6.79',included_in_advertised_total:false,source_id:'reviewed'},
      {id:'internet',label:'Internet',classification:'MANDATORY_RECURRING',timing_event:'PER_CALENDAR_MONTH',scaling_basis:'PER_UNIT',amount_min:'65.00',amount_max:'65.00',included_in_advertised_total:false,source_id:'audit'},
      {id:'deposit',label:'Deposit',classification:'REFUNDABLE_DEPOSIT',timing_event:'AT_MOVE_IN',scaling_basis:'PER_UNIT',amount_min:'400.00',amount_max:'1500.00',source_id:'reviewed'},
      {id:'annual',label:'Annual fees',classification:'MANDATORY_RECURRING',timing_event:'PER_TERM',scaling_basis:'PER_BED_INSTALLMENT',amount_min:'155.00',amount_max:'155.00',source_id:'reviewed'},
      {label:'Application fee',amount:'35',refundable:false,basis:'unknown'}]}}).offer.fees`,scope).map(f=>({...f}));
  assert.deepEqual(JSON.parse(JSON.stringify(fees.map(f=>[f.kind,f.amount,f.research]))),[['mandatory',6.79,false],['mandatory',65,true],['refundable',400,false],['term',155,false],['one_time',35,false]]);
  assert.equal(fees[1].basis,'whole_unit');
  assert.equal(fees[2].amount_max,1500);
});


test('Compare explanations use the connected assistant and distinguish local fallback',async()=>{
  const scope=context();
  vm.runInContext(`render=()=>{};save=()=>{};S.shortlist=['test-offer'];
    let lastRequest;
    api=async(path,options)=>{lastRequest={path,body:JSON.parse(options.body)};return {status:'complete',provider:'openai_compatible',model_id:'roomwise-gemma-4-e4b-v2',result:{answer:'Evidence-based comparison',limitations:['Fees unknown'],next_questions:['Confirm fees'],evidence_ids:[]}};};`,scope);
  await vm.runInContext('runAI()',scope);
  assert.equal(vm.runInContext('lastRequest.path',scope),'/assistant/messages');
  assert.equal(vm.runInContext('lastRequest.body.candidate_ids[0]',scope),'test-offer');
  assert.equal(vm.runInContext('S.ai.result.model_id',scope),'roomwise-gemma-4-e4b-v2');
  assert.equal(vm.runInContext('S.ai.status',scope),'done');
  vm.runInContext(`api=async()=>({status:'complete',provider:'local_rules',model_id:null,fallback:{message:'Model response could not be verified'},result:{answer:'Local evidence summary',limitations:['Unknown costs'],next_questions:[],evidence_ids:[]}});`,scope);
  await vm.runInContext('runAI()',scope);
  assert.equal(vm.runInContext('S.ai.result.model_id',scope),null);
  assert.equal(vm.runInContext('S.ai.result.fallback.message',scope),'Model response could not be verified');
});

test('Compare discards a response when shortlist changes without a revision change',async()=>{
  const scope=context();
  vm.runInContext(`render=()=>{};save=()=>{};S.shortlist=['test-offer'];api=async()=>{S.shortlist=[];return {status:'complete',result:{answer:'Old selection'}}};`,scope);
  await vm.runInContext('runAI()',scope);
  assert.equal(vm.runInContext('S.ai.status',scope),'discarded');
});


test('guide neighborhoods render reference prices without requiring invented area coordinates or ranges',()=>{
  const scope=context();
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../CampusHousing-main/src/views2.js'),'utf8'),scope);
  vm.runInContext(`const guideRow={cand:{...item,type:'area',coordinates:null,guide_reference:{guide_price_summary:'Guide estimate: $700–$900 / bed'}},share:null};`,scope);
  const html=vm.runInContext('priceBlock(guideRow)',scope);
  assert.match(html,/Guide estimate: \$700–\$900/);
  assert.match(html,/not current verified quotes/);
  assert.doesNotMatch(html,/Infinity|NaN/);
});
