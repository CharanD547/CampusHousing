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

test('unknown prices stay unknown and example schedule provenance reaches the API',()=>{
  const scope=context();
  assert.equal(vm.runInContext('normalizeCandidate({...offer,offer:{...offer.offer,price:{...offer.offer.price,amount:null}}}).offer.price.amount',scope),null);
  assert.equal(vm.runInContext('cleanCommitments()[0].is_example',scope),true);
  assert.equal(vm.runInContext('Object.hasOwn(cleanCommitments()[0],"sample")',scope),false);
  assert.equal(vm.runInContext('cleanPreferences().move_in_date',scope),null);
  assert.equal(vm.runInContext('Object.hasOwn(cleanPreferences(),"campus_id")',scope),false);
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
