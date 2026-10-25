/* Only the browser Maps key reaches this SDK. Places stays behind the server. */
const MAPS={loading:null,error:null,map:null,element:null,markers:[],contextKey:null};
const NEARBY={property:null,category:'groceries',radius:2500,mode:'walking',data:null,pending:false,error:null,serial:0,selected:null};
const NEARBY_CATEGORIES={groceries:'Groceries',restaurant:'Restaurants',gas_station:'Gas stations',cafe:'Cafes',pharmacy:'Pharmacies',library:'Libraries'};
function googleMapShell(results) {
  const ids=results.filter(r=>r.cand.coordinates).map(r=>r.cand.id).join(',');
  return `<div class="map-card"><div class="google-map" data-offers="${esc(ids)}" style="height:560px;min-height:320px" aria-label="Google Maps housing locations"></div><div class="map-bar"><span>Approximate housing locations. Guide references without verified coordinates remain in the list and are not plotted. Select a marker to jump to that place.</span></div></div>`;
}
function loadGoogleMaps() {
  if (MAPS.loading) return MAPS.loading;
  MAPS.loading=new Promise((resolve,reject)=>{
    const timeout=setTimeout(()=>reject(new Error('Map loading timed out.')),15000);
    window.roomwiseMapsReady=()=>{clearTimeout(timeout);resolve();};
    window.gm_authFailure=()=>{MAPS.error='Google Maps authorization failed.';clearTimeout(timeout);reject(new Error(MAPS.error));render();};
    const script=document.createElement('script');
    const query=new URLSearchParams({key:API.maps.browser_key,v:'weekly',loading:'async',libraries:'marker',callback:'roomwiseMapsReady'});
    script.src='https://maps.googleapis.com/maps/api/js?'+query;
    script.onerror=()=>{clearTimeout(timeout);reject(new Error('Google Maps could not load.'));};
    document.head.appendChild(script);
  });
  return MAPS.loading;
}
async function hydrateGoogleMaps() {
  const targets=[...document.querySelectorAll('.google-map')];
  if (!targets.length) return;
  try {
    await loadGoogleMaps();
    for (let el of targets) {
      if (!el.isConnected || el.dataset.ready) continue;
      const offers=el.dataset.offers;
      const nearbyView=el.dataset.nearby==='true',className=el.className,label=el.getAttribute('aria-label');
      if (MAPS.element && MAPS.element!==el) {el.replaceWith(MAPS.element);el=MAPS.element;el.dataset.offers=offers;}
      el.dataset.nearby=String(nearbyView);el.className=className;el.setAttribute('aria-label',label);
      el.dataset.ready='true';MAPS.element=el;
      const map=MAPS.map || (MAPS.map=new google.maps.Map(el,{center:{lat:37.2296,lng:-80.4234},zoom:13,mapId:'DEMO_MAP_ID',mapTypeControl:false,streetViewControl:false}));
      const nearby=el.dataset.nearby==='true' && NEARBY.property===candidate(offers)?.property_id ? NEARBY.data:null;
      const contextKey=JSON.stringify([offers,S.commitments.map(c=>c.building_id),nearby?.places.map(p=>p.id)]);
      const shouldFit=MAPS.contextKey!==contextKey;MAPS.contextKey=contextKey;
      // Google marker elements detach when the parent view is replaced. Recreate them on
      // the retained map instance rather than assuming a matching context kept them alive.
      MAPS.markers.forEach(m=>m.map=null);MAPS.markers=[];
      const bounds=new google.maps.LatLngBounds(),seen=new Set();
      for (const id of el.dataset.offers.split(',')) {
        const c=candidate(id);if (!c?.coordinates || seen.has(c.property_id)) continue;seen.add(c.property_id);
        const position={lat:c.coordinates.lat,lng:c.coordinates.lon};bounds.extend(position);
        const marker=new google.maps.marker.AdvancedMarkerElement({map,position,title:c.property_name,gmpClickable:true});
        MAPS.markers.push(marker);
        marker.addEventListener('gmp-click',()=>{UI.selected=c.property_id;render();document.getElementById('card-'+c.property_id)?.scrollIntoView({block:'nearest',behavior:'smooth'});});
      }
      for (const [index,p] of (nearby?.places || []).entries()) {
        if (!p.location)continue;
        const position={lat:p.location.latitude,lng:p.location.longitude};bounds.extend(position);
        const badge=document.createElement('span');badge.className='nearby-pin';badge.textContent=String(index+1);
        const marker=new google.maps.marker.AdvancedMarkerElement({map,position,title:p.name,content:badge,gmpClickable:true});
        MAPS.markers.push(marker);
        marker.addEventListener('gmp-click',()=>{document.getElementById('nearby-place-'+index)?.scrollIntoView({block:'nearest',behavior:'smooth'});});
        if(p.id===NEARBY.selected)map.panTo(position);
      }
      if (shouldFit && !bounds.isEmpty()) {
        if(nearbyView && !nearby?.places.length) {map.setCenter(bounds.getCenter());map.setZoom(14);}
        else map.fitBounds(bounds,55);
      }
    }
  } catch(error) {MAPS.error=error.message;render();toast('Map unavailable. The coordinate overview and offer list remain available.');}
}
function nearbySection(c) {
  if(!c.coordinates)return `<section class="panel stack-sm"><h2>Explore the area</h2><p>This guide reference has no verified property point, so nearby results and distances are unavailable here.</p><a class="btn" href="https://www.google.com/maps/search/?${esc(new URLSearchParams({api:'1',query:c.property_name+' '+(c.address||'Blacksburg VA')}))}" target="_blank" rel="noopener noreferrer">Find this address in Google Maps ↗</a><p class="tiny">Confirm the exact property address and unit with the operator.</p></section>`;
  if(NEARBY.property!==c.property_id) {NEARBY.property=c.property_id;NEARBY.data=null;NEARBY.error=null;NEARBY.pending=false;NEARBY.selected=null;NEARBY.serial++;}
  const data=NEARBY.data;
  return `<section class="panel stack-sm" id="nearby-essentials"><h2>Life around ${esc(c.property_name)}</h2>
    <p class="small">Find nearby essentials from this property's approximate address. Search one category at a time; up to eight places are ranked by distance. Results stay in this view and are excluded from briefs and AI.</p>
    <div class="nearby-categories" role="group" aria-label="Nearby categories">${Object.entries(NEARBY_CATEGORIES).map(([key,label])=>`<button class="btn btn-sm" data-nearby-category="${key}" aria-pressed="${NEARBY.category===key}" ${NEARBY.pending?'disabled':''}>${label}</button>`).join('')}</div>
    <div class="nearby-controls"><div><label for="nearby-radius">Search radius</label><select class="input" id="nearby-radius">${[1000,2500,5000].map(n=>`<option value="${n}" ${n===NEARBY.radius?'selected':''}>${n/1000} km</option>`).join('')}</select></div>
    <div><label for="nearby-mode">Directions mode</label><select class="input" id="nearby-mode">${[['walking','Walk'],['driving','Drive'],['bicycling','Bike'],['transit','Transit']].map(([key,label])=>`<option value="${key}" ${key===NEARBY.mode?'selected':''}>${label}</option>`).join('')}</select></div></div>
    <button class="btn btn-primary" data-action="nearby-search" data-property="${esc(c.property_id)}" ${NEARBY.pending || !API.maps?.places_available?'disabled':''}>${NEARBY.pending?'Searching…':'Find '+NEARBY_CATEGORIES[NEARBY.category].toLowerCase()}</button>
    ${!API.maps?.places_available?'<p role="status">Nearby search is unavailable. Configure Places API access to search here.</p>':''}
    ${API.maps?.enabled && !MAPS.error?`<div class="google-map nearby-map" data-offers="${esc(c.id)}" data-nearby="true" aria-label="Map of this property and nearby places"></div>`:''}
    <div id="nearby-results" aria-live="polite" aria-busy="${NEARBY.pending}">${NEARBY.error?`<p role="alert">${esc(NEARBY.error)}</p>`:''}
    ${data?`<p class="small">${esc(data.reason)}</p>${data.status==='available'?`<img src="/assets/google-maps-attribution.svg" height="18" alt="Google Maps" style="height:18px;width:auto"><ol class="nearby-list">${data.places.map((p,index)=>`<li id="nearby-place-${index}"><div><b>${esc(p.name)}</b><p class="small">${esc(p.address || 'Address unavailable')}</p><p class="tiny">${p.distance_meters==null?'Distance unavailable':(p.distance_meters/1000).toFixed(2)+' km straight-line'}</p></div><div class="btn-row"><a class="btn btn-sm" href="${esc(nearbyDirections(c,p))}" target="_blank" rel="noopener noreferrer">${NEARBY.mode==='walking'?'Walk':NEARBY.mode==='driving'?'Drive':NEARBY.mode==='bicycling'?'Bike':'Transit'} directions ↗</a><a class="btn btn-sm" href="${esc(safeMapsURL(p.url))}" target="_blank" rel="noopener noreferrer">Google Maps ↗</a>${p.location?`<button class="btn btn-sm" data-nearby-focus="${index}">Show on map</button>`:''}</div>${(p.attributions||[]).map(a=>`<a class="tiny" href="${esc(safeMapsURL(a.providerUri))}" target="_blank" rel="noopener noreferrer">${esc(a.provider||'')}</a>`).join('')}</li>`).join('')}</ol>${!data.places.length?'<p>No results returned in this radius. Try a wider search; this does not prove no businesses exist.</p>':''}`:''}`:''}</div>
    <p class="tiny">Directions open in Google Maps from the property, not your device location. Opening hours, prices and accessibility are unverified. Search radius is not travel distance.</p></section>`;
}
function safeMapsURL(value) {try{const url=new URL(value);return url.protocol==='https:'?url.href:'#';}catch(error){return '#';}}
function nearbyDirections(c,p) {
  const params=new URLSearchParams({api:'1',origin:`${c.coordinates.lat},${c.coordinates.lon}`,
    destination:p.location?`${p.location.latitude},${p.location.longitude}`:p.address||p.name,
    destination_place_id:p.id,travelmode:NEARBY.mode});
  return 'https://www.google.com/maps/dir/?'+params;
}

document.addEventListener('change',event=>{
  if(event.target.id==='nearby-radius') {NEARBY.radius=Number(event.target.value);NEARBY.data=null;NEARBY.pending=false;NEARBY.serial++;render();}
  if(event.target.id==='nearby-mode') {NEARBY.mode=event.target.value;render();}
});
document.addEventListener('click',async event=>{
  const categoryButton=event.target.closest('[data-nearby-category]');
  if(categoryButton) {NEARBY.category=categoryButton.dataset.nearbyCategory;NEARBY.data=null;NEARBY.error=null;NEARBY.serial++;render();return;}
  const focus=event.target.closest('[data-nearby-focus]');
  if(focus) {NEARBY.selected=NEARBY.data?.places[Number(focus.dataset.nearbyFocus)]?.id;render();document.querySelector('.nearby-map')?.scrollIntoView({block:'center',behavior:'smooth'});return;}
  const button=event.target.closest('[data-action="nearby-search"]');if(!button)return;
  if(NEARBY.pending)return;
  const serial=++NEARBY.serial,property=button.dataset.property,category=NEARBY.category,radius=NEARBY.radius;
  NEARBY.pending=true;NEARBY.error=null;NEARBY.data=null;render();
  try {
    const data=await api('/properties/'+encodeURIComponent(property)+'/nearby?category='+encodeURIComponent(category)+'&radius='+radius);
    if(serial===NEARBY.serial && NEARBY.property===property)NEARBY.data=data;
  }catch(error){if(serial===NEARBY.serial)NEARBY.error=error.message;}
  finally{if(serial===NEARBY.serial){NEARBY.pending=false;render();}}
});
