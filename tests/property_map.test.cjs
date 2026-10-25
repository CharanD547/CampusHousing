const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

function context() {
  const clicks=[];
  const scope=vm.createContext({console,crypto:require('node:crypto').webcrypto,AbortSignal,URL,URLSearchParams,
    setTimeout,clearTimeout,clicks,document:{addEventListener(name,fn){if(name==='click')clicks.push(fn);}},window:{addEventListener(){}},
    localStorage:{getItem:()=>null,setItem(){}},sessionStorage:{getItem:()=>null}});
  for(const name of ['data.js','core.js','api.js','views2.js','maps.js'])
    vm.runInContext(fs.readFileSync(path.join(__dirname,'../CampusHousing-main/src',name),'utf8'),scope);
  vm.runInContext(`const item=normalizeCandidate({id:'p-one',type:'offer',property_id:'p',property_name:'Test apartments',
    coordinates:{lat:37.2,lon:-80.4},sources:[],offer:{bedrooms:2,layout:'Two bedroom',fees:[],
    price:{amount:'850',basis:'per_person',frequency:'calendar_month',last_reviewed_at:TODAY,term:{label:'Test'}}}});
    CANDIDATES.push(item);`,scope);
  return scope;
}

test('Explore includes insufficient-evidence places alongside priced properties by default',()=>{
  const scope=context();
  vm.runInContext(`CANDIDATES.push({...item,id:'guide-plan',property_id:'guide-property',property_name:'Guide only place',
    coordinates:null,guide_reference:{zone:'Downtown',guide_price_summary:'Unverified reference'},
    offer:{...item.offer,price:{...item.offer.price,amount:null}}});`,scope);
  const initial=vm.runInContext('viewExplore()',scope);
  assert.equal((initial.match(/class="cand prop-card /g)||[]).length,2);
  assert.doesNotMatch(initial,/include-guide/);
  assert.match(initial,/property-price-range/);
  assert.match(initial,/street-map/);
  assert.match(initial,/Guide only place/);
});

test('duplicate floor plans cannot create duplicate property plans or map markers',()=>{
  const scope=context();
  vm.runInContext(`const mapRows=[compare(item,S.prefs,[]),compare(item,S.prefs,[]),
    {cand:{...item,id:'missing-point',property_id:'other',coordinates:null}},
    {cand:{...item,id:'invalid-point',property_id:'invalid',coordinates:{lat:NaN,lon:-80.4}}}];`,scope);
  assert.equal(vm.runInContext('propertyGroups(mapRows.slice(0,2))[0].plans.length',scope),1);
  assert.equal(vm.runInContext('mappedProperties(mapRows).length',scope),1);
  assert.match(vm.runInContext('streetMapShell(mapRows)',scope),/1 property on the map/);
});

test('new operator figures appear while an insufficient-evidence comparison price stays unknown',()=>{
  const scope=context();
  vm.runInContext(`item.offer.price.amount=null;item.guide_reference={guide_price_summary:'Old guide figure',
    evidence_update:{source_url:'https://example.test/operator',checked_at:'2026-10-25T02:00:00Z',
      billing_note:'Confirm basis and fees',prices:[{label:'B1',bedrooms:2,minimum:2000,maximum:2100}]}};`,scope);
  const html=vm.runInContext('planPrices(propertyGroups(compareAll())[0])',scope);
  assert.match(html,/\$2,000–\$2,100/);
  assert.match(html,/Operator source/);
  assert.equal(vm.runInContext('compareAll()[0].share',scope),null);
  assert.equal(vm.runInContext('compareAll()[0].fit',scope),'insufficient');
});

test('Show on map focuses the existing OSM pin without rerendering the page',async()=>{
  const scope=context();
  let scrollOptions;
  scope.document.querySelector=()=>({scrollIntoView(options){scrollOptions=options;}});
  vm.runInContext(`let rendered=0,focused=false,panned;
    render=()=>rendered++;
    NEARBY.data={provider:'OpenStreetMap',places:[{id:'osm-node-1',name:'Market',location:{latitude:37.21,longitude:-80.4}}]};
    STREET.map={panTo:position=>panned=position};STREET.nearbyMarkers.set('osm-node-1',{openTooltip:()=>focused=true});`,scope);
  await scope.clicks.at(-1)({target:{closest(selector){return selector==='[data-nearby-focus]'?{dataset:{nearbyFocus:'0'}}:null;}}});
  assert.equal(vm.runInContext('rendered',scope),0);
  assert.equal(vm.runInContext('focused',scope),true);
  assert.equal(vm.runInContext('NEARBY.selected',scope),'osm-node-1');
  assert.deepEqual(JSON.parse(vm.runInContext('JSON.stringify(panned)',scope)),[37.21,-80.4]);
  assert.equal(scrollOptions.behavior,'instant');
  const url=new URL(vm.runInContext('nearbyDirections(item,NEARBY.data.places[0])',scope));
  assert.equal(url.searchParams.get('destination'),'37.21,-80.4');
  assert.equal(url.searchParams.has('destination_place_id'),false);
});
