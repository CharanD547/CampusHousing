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
    CANDIDATES.push(item);API.comparison={candidate_results:[]};API.comparisonKey=comparisonKey();`,scope);
  return scope;
}

test('Explore includes guide places alongside priced properties by default',()=>{
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

test('Explore research badges do not promise that every listing meets preferences',()=>{
  const scope=context();
  vm.runInContext(`CANDIDATES.push({...item,id:'guide-plan',property_id:'guide-property',property_name:'Guide only place',
    coordinates:null,guide_reference:{zone:'Downtown',guide_price_summary:'Unverified reference'},
    offer:{...item.offer,price:{...item.offer.price,amount:null}}});
    API.comparison.candidate_results.push({candidate_id:'guide-plan',fit_state:'insufficient_evidence',known_recurring_subtotal:null,
      hard_conflicts:['Old conflict text'],unknown_costs:['Old unknown text'],notes:[],commute_estimates:[]});
    API.comparisonKey=comparisonKey();`,scope);
  const html=vm.runInContext('viewExplore()',scope);
  assert.doesNotMatch(html,/More evidence|have a conflict|Old conflict text|Old unknown text|cand-unknown/);
  assert.doesNotMatch(html,/flt-conflict|flt-insufficient/);
  assert.match(html,/published plan/);
  assert.match(html,/Research option/);
  assert.doesNotMatch(html,/Criteria match/);
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

test('new operator figures appear while an unconfirmed comparison price stays unknown',()=>{
  const scope=context();
  vm.runInContext(`item.offer.price.amount=null;item.guide_reference={guide_price_summary:'Old guide figure',
    evidence_update:{source_url:'https://example.test/operator',checked_at:'2026-10-25T02:00:00Z',
      billing_note:'Confirm basis and fees',prices:[{label:'B1',bedrooms:2,minimum:2000,maximum:2100}]}};`,scope);
  const html=vm.runInContext('planPrices(propertyGroups(compareAll())[0])',scope);
  assert.match(html,/\$2,000–\$2,100/);
  assert.match(html,/Operator source/);
  assert.equal(vm.runInContext('compareAll()[0].share',scope),null);
  assert.equal(vm.runInContext('compareAll()[0].fit',scope),'fit');
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


test('changing nearby category cancels a pending state so stale results cannot leave search stuck',async()=>{
 const scope=context();
 vm.runInContext(`render=()=>{};NEARBY.pending=true;NEARBY.serial=3;NEARBY.selected='old';NEARBY.data={places:[]};`,scope);
 await scope.clicks.at(-1)({target:{closest(selector){return selector==='[data-nearby-category]'?{dataset:{nearbyCategory:'pharmacy'}}:null;}}});
 assert.equal(vm.runInContext('NEARBY.pending',scope),false);
 assert.equal(vm.runInContext('NEARBY.category',scope),'pharmacy');
 assert.equal(vm.runInContext('NEARBY.serial',scope),4);
 assert.equal(vm.runInContext('NEARBY.data',scope),null);
 assert.equal(vm.runInContext('NEARBY.selected',scope),null);
});

test('map label collisions use compact pins without moving geographic anchors',()=>{
 const scope=context();const icons=[];
 scope.L={divIcon:options=>options};
 vm.runInContext(`STREET.map={latLngToContainerPoint:()=>({x:100,y:100})};`,scope);
 scope.icons=icons;
 vm.runInContext(`STREET.markers=[false,true,false].map(selected=>({selected,label:'$850',marker:{getLatLng:()=>[37.2,-80.4],setIcon:icon=>icons.push(icon)}}));layoutStreetMarkers();`,scope);
 assert.equal(icons.filter(i=>i.className.includes('is-compact')).length,2);
 assert.deepEqual(Array.from(icons[0].iconAnchor),[43,34]);
 assert.ok(icons.slice(1).every(i=>i.iconAnchor[0]===9 && i.iconAnchor[1]===9));
});

test('nearby distances and search radii display miles while requests retain meters',()=>{
 const scope=context();
 vm.runInContext(`API.maps={places_available:true};NEARBY.property=item.property_id;
   NEARBY.data={provider:'OpenStreetMap',status:'available',reason:'Mapped places',places:[
   {id:'osm-node-1',name:'Grocer',distance_meters:1609.344,url:'https://www.openstreetmap.org/node/1'}]};`,scope);
 const html=vm.runInContext('nearbySection(item)',scope);
 assert.match(html,/value="2500" selected>1.55 miles/);
 assert.match(html,/1.00 miles straight-line/);
 assert.doesNotMatch(html,/\bkm\b/);
 assert.equal(vm.runInContext('milesFromMeters(NaN)',scope),'Distance unavailable');
});

test('property ranges retain the upper asking figure and expose cautious source checks',()=>{
 const scope=context();
 vm.runInContext(`item.offer.advertised_range={minimum:'850',maximum:'1100'};
   item.sources=[{id:'rent',url:'https://example.test/rent',rent_recheck:{status:'amounts_present',checked_at:'2026-10-25T12:00:00Z'}}];
   item.offer.price.source_id='rent';`,scope);
 const html=vm.runInContext('planPrices(propertyGroups([compare(item,S.prefs,[])])[0])',scope);
 assert.match(html,/\$850–\$1,100/);
 const evidence=vm.runInContext('rentEvidenceSummary(item)',scope);
 assert.match(evidence,/Amounts found in source/);
 assert.match(evidence,/does not confirm its floor plan/);
 assert.match(evidence,/Confirm the exact unit/);
});

test('written quote request exposes missing facts without sending personal data',()=>{
 const scope=context();
 vm.runInContext(`item.lease_gaps={listed_fee_labels:[],questions:['Confirm the exact lease dates.','Provide all mandatory fees.']};`,scope);
 const html=vm.runInContext('leaseQuotePanel(item)',scope);
 assert.match(html,/No current written quote is stored/);
 assert.match(html,/Copy quote request/);
 assert.match(html,/Copying sends nothing to the operator/);
 const text=vm.runInContext('quoteRequestText(item)',scope);
 assert.match(text,/Selected plan: Two bedroom/);
 assert.match(text,/\[fill in\]/);
 assert.doesNotMatch(text,/monthly_budget|browser-/);
});
