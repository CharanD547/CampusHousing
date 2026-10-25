/* Only the browser Maps key reaches this SDK. Places stays behind the server. */
const MAPS={loading:null,error:null,map:null,element:null,markers:[],contextKey:null};
const NEARBY={property:null,category:'groceries',radius:2500,mode:'walking',data:null,pending:false,error:null,serial:0,selected:null};
const NEARBY_CATEGORIES={groceries:'Groceries',restaurant:'Restaurants',gas_station:'Gas stations',cafe:'Cafes',pharmacy:'Pharmacies',library:'Libraries'};
const STREET={map:null,element:null,layer:null,context:null,error:null,observer:null,markers:[],nearbyMarkers:new Map()};

function layoutStreetMarkers() {
  const occupied=[];
  for(const {marker,label,selected} of STREET.markers) {
    const point=STREET.map.latLngToContainerPoint(marker.getLatLng());
    let offset=0;
    while(occupied.some(r=>Math.abs(point.x-r.x)<92 && Math.abs(point.y+offset-r.y)<40))offset+=42;
    occupied.push({x:point.x,y:point.y+offset});
    marker.setIcon(L.divIcon({className:'housing-marker'+(selected?' is-selected':''),
      html:`<span>${esc(label)}</span>`,iconSize:[86,34],iconAnchor:[43,34-offset]}));
  }
}

function mappedProperties(results) {
  const seen=new Set();
  return results.filter(r=>{
    const c=r.cand,p=c.coordinates;
    if(seen.has(c.property_id) || !p || !Number.isFinite(p.lat) || !Number.isFinite(p.lon))return false;
    seen.add(c.property_id);return true;
  });
}
function streetMapShell(results,nearby=false) {
  const properties=mappedProperties(results);
  if(!properties.length)return `<div class="map-card panel"><h3>No mapped places in these results</h3><p>Try another search or include properties with checked address points.</p></div>`;
  if(STREET.error)return `<div class="map-card panel"><h3>Street map unavailable</h3><p>${esc(STREET.error)}</p><button class="btn" data-action="map-retry">Retry map</button></div>`;
  return `<div class="map-card"><div class="street-map ${nearby?'nearby-map':''}" data-nearby="${nearby}" data-offers="${esc(properties.map(r=>r.cand.id).join(','))}" role="region" aria-label="Street map of housing near Virginia Tech"></div><div class="map-bar"><b>${plural(properties.length,'property','properties')} on the map</b><span>Address points are approximate. ${nearby?'Numbered pins match the nearby results below.':'Select a marker to highlight its property.'}${results.length>properties.length?' Other places remain in the list; their detail pages include an address-search map.':''}</span><span class="tile-status" role="status"></span><a href="https://www.openstreetmap.org/fixthemap" target="_blank" rel="noopener noreferrer">Report a map issue ↗</a></div></div>`;
}
function hydrateStreetMap() {
  const target=document.querySelector('.street-map');
  if(!target || !target.getClientRects().length)return;
  if(!window.L) {STREET.error='The map library could not load. Check your connection and retry.';render();return;}
  let el=target;
  const offers=el.dataset.offers,className=el.className,label=el.getAttribute('aria-label'),nearbyView=el.dataset.nearby==='true';
  if(STREET.element && STREET.element!==el) {el.replaceWith(STREET.element);el=STREET.element;}
  el.dataset.offers=offers;el.dataset.nearby=String(nearbyView);el.classList.toggle('nearby-map',className.includes('nearby-map'));el.setAttribute('aria-label',label);
  if(!STREET.map) {
    STREET.element=el;
    STREET.map=L.map(el,{scrollWheelZoom:false}).setView([37.2296,-80.4234],13);
    const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
      maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(STREET.map);
    tiles.on('tileerror',()=>{const status=el.closest('.map-card')?.querySelector('.tile-status');if(status)status.textContent='Some map tiles could not load. Property markers remain available.';});
    tiles.on('tileload',()=>{const status=el.closest('.map-card')?.querySelector('.tile-status');if(status)status.textContent='';});
    STREET.layer=L.layerGroup().addTo(STREET.map);
    STREET.map.on('zoomend',layoutStreetMarkers);
    STREET.observer=new ResizeObserver(()=>{if(el.isConnected && el.getClientRects().length)STREET.map.invalidateSize({pan:false});});
    STREET.observer.observe(el);
  }
  STREET.map.invalidateSize({pan:false});
  STREET.layer.clearLayers();
  STREET.markers=[];
  STREET.nearbyMarkers.clear();
  const bounds=[];
  for(const id of offers.split(',')) {
    const c=candidate(id);if(!c?.coordinates)continue;
    const position=[c.coordinates.lat,c.coordinates.lon];bounds.push(position);
    const rows=CANDIDATES.filter(p=>p.property_id===c.property_id && p.offer.price.amount!=null);
    const low=Math.min(...rows.map(p=>p.offer.price.amount));
    const observations=c.guide_reference?.evidence_update?.prices || [];
    const label=rows.length?money(low):observations.length?money(Math.min(...observations.map(p=>p.minimum))):'Location';
    const selected=UI.selected===c.property_id;
    const marker=L.marker(position,{title:c.property_name,alt:c.property_name,
      icon:L.divIcon({className:'housing-marker'+(selected?' is-selected':''),html:`<span>${esc(label)}</span>`,iconSize:[86,34],iconAnchor:[43,34]})
    }).addTo(STREET.layer);
    marker.bindTooltip(esc(c.property_name),{direction:'top',offset:[0,-30]});
    STREET.markers.push({marker,label,selected});
    marker.on('click',()=>{UI.selected=c.property_id;render();document.getElementById('card-'+c.property_id)?.scrollIntoView({block:'nearest',behavior:'smooth'});});
  }
  const nearby=nearbyView && NEARBY.property===candidate(offers)?.property_id && NEARBY.data?.provider==='OpenStreetMap'?NEARBY.data:null;
  for(const [index,p] of (nearby?.places||[]).entries()) {
    if(!p.location)continue;
    const position=[p.location.latitude,p.location.longitude];bounds.push(position);
    const marker=L.marker(position,{title:p.name,alt:p.name,icon:L.divIcon({className:'nearby-marker',html:`<span class="nearby-pin">${index+1}</span>`,iconSize:[30,30],iconAnchor:[15,15]})}).addTo(STREET.layer);
    marker.bindTooltip(esc(p.name),{direction:'top'});
    STREET.nearbyMarkers.set(p.id,marker);
    marker.on('click',()=>document.getElementById('nearby-place-'+index)?.scrollIntoView({block:'nearest',behavior:'smooth'}));
    if(p.id===NEARBY.selected)marker.openTooltip();
  }
  const context=JSON.stringify([offers,nearby?.places.map(p=>p.id)]);
  if(STREET.context!==context && bounds.length) {
    if(bounds.length===1)STREET.map.setView(bounds[0],15);else STREET.map.fitBounds(bounds,{padding:[48,48],maxZoom:15});
    STREET.context=context;
  }
  const selectedPlace=nearby?.places.find(p=>p.id===NEARBY.selected);
  if(selectedPlace?.location)STREET.map.panTo([selectedPlace.location.latitude,selectedPlace.location.longitude]);
  layoutStreetMarkers();
}
function hydrateMaps() {
  hydrateStreetMap();
  hydrateGoogleMaps();
}
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
      const nearbyView=el.dataset.nearby==='true',className=el.className,label=el.getAttribute('aria-label'),style=el.style.cssText;
      if (MAPS.element && MAPS.element!==el) {el.replaceWith(MAPS.element);el=MAPS.element;el.dataset.offers=offers;}
      el.dataset.nearby=String(nearbyView);el.classList.toggle('nearby-map',nearbyView);el.style.cssText=style;el.setAttribute('aria-label',label);
      el.dataset.ready='true';MAPS.element=el;
      const map=MAPS.map || (MAPS.map=new google.maps.Map(el,{center:{lat:37.2296,lng:-80.4234},zoom:13,mapId:'DEMO_MAP_ID',mapTypeControl:false,streetViewControl:false}));
      google.maps.event.trigger(map,'resize');
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
  } catch(error) {MAPS.error=error.message;render();}
}
function nearbySection(c) {
  if(!c.coordinates) {
    const query=c.property_name+' '+(c.address||'')+' Blacksburg VA';
    return `<section class="panel stack-sm" id="nearby-essentials"><h2>Life around ${esc(c.property_name)}</h2><p class="small">Address-search map · exact property location is still unconfirmed.</p><iframe class="address-search-map" title="Address search for ${esc(c.property_name)}" src="https://maps.google.com/maps?${esc(new URLSearchParams({q:query,output:'embed'}))}" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe><a class="btn" href="https://www.google.com/maps/search/?${esc(new URLSearchParams({api:'1',query}))}" target="_blank" rel="noopener noreferrer">Open this area in Google Maps ↗</a><p class="tiny">This is an address search, not a verified location pin. Confirm the exact address before using distance estimates.</p></section>`;
  }
  if(NEARBY.property!==c.property_id) {NEARBY.property=c.property_id;NEARBY.data=null;NEARBY.error=null;NEARBY.pending=false;NEARBY.selected=null;NEARBY.serial++;}
  const data=NEARBY.data;
  if(!API.maps?.places_available) {
    const query=NEARBY_CATEGORIES[NEARBY.category]+' near '+c.address;
    const url='https://www.google.com/maps/search/?'+new URLSearchParams({api:'1',query});
    return `<section class="panel stack-sm" id="nearby-essentials"><h2>Life around ${esc(c.property_name)}</h2><p class="small">Explore the property on the street map, or open a current search for nearby essentials.</p>${schematicMap([{cand:c}])}<div class="nearby-categories" role="group" aria-label="Nearby categories">${Object.entries(NEARBY_CATEGORIES).map(([key,label])=>`<button class="btn btn-sm" data-nearby-category="${key}" aria-pressed="${NEARBY.category===key}">${label}</button>`).join('')}</div><a class="btn btn-primary" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Find ${esc(NEARBY_CATEGORIES[NEARBY.category].toLowerCase())} on Google Maps ↗</a><p class="tiny">Google Maps opens a search near the property address. Check current business details and travel directions there.</p></section>`;
  }
  return `<section class="panel stack-sm" id="nearby-essentials"><h2>Life around ${esc(c.property_name)}</h2>
    <p class="small">Find nearby essentials from this property's approximate address. Search one category at a time; up to eight places are ranked by distance. Results stay in this view and are excluded from briefs and AI.</p>
    <div class="nearby-categories" role="group" aria-label="Nearby categories">${Object.entries(NEARBY_CATEGORIES).map(([key,label])=>`<button class="btn btn-sm" data-nearby-category="${key}" aria-pressed="${NEARBY.category===key}" ${NEARBY.pending?'disabled':''}>${label}</button>`).join('')}</div>
    <div class="nearby-controls"><div><label for="nearby-radius">Search radius</label><select class="input" id="nearby-radius">${[1000,2500,5000].map(n=>`<option value="${n}" ${n===NEARBY.radius?'selected':''}>${n/1000} km</option>`).join('')}</select></div>
    <div><label for="nearby-mode">Directions mode</label><select class="input" id="nearby-mode">${[['walking','Walk'],['driving','Drive'],['bicycling','Bike'],['transit','Transit']].map(([key,label])=>`<option value="${key}" ${key===NEARBY.mode?'selected':''}>${label}</option>`).join('')}</select></div></div>
    <button class="btn btn-primary" data-action="nearby-search" data-property="${esc(c.property_id)}" ${NEARBY.pending || !API.maps?.places_available?'disabled':''}>${NEARBY.pending?'Searching…':'Find '+NEARBY_CATEGORIES[NEARBY.category].toLowerCase()}</button>
    ${!API.maps?.places_available?'<p role="status">Nearby search is unavailable. Configure Places API access to search here.</p>':''}
    ${API.maps?.enabled && !MAPS.error?`<div class="google-map nearby-map" data-offers="${esc(c.id)}" data-nearby="true" aria-label="Map of this property and nearby places"></div>`:streetMapShell([{cand:c}],true)}
    <div id="nearby-results" aria-live="polite" aria-busy="${NEARBY.pending}">${NEARBY.error?`<p role="alert">${esc(NEARBY.error)}</p>`:''}
    ${data?`<p class="small">${esc(data.reason)}</p>${data.status==='available'?`${data.provider==='OpenStreetMap'?'<p class="tiny">© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a></p>':'<img src="/assets/google-maps-attribution.svg" height="18" alt="Google Maps" style="height:18px;width:auto">'}<ol class="nearby-list">${data.places.map((p,index)=>`<li id="nearby-place-${index}"><div><b>${esc(p.name)}</b><p class="small">${esc(p.address || 'Address unavailable')}</p><p class="tiny">${p.distance_meters==null?'Distance unavailable':(p.distance_meters/1000).toFixed(2)+' km straight-line'}</p></div><div class="btn-row"><a class="btn btn-sm" href="${esc(nearbyDirections(c,p))}" target="_blank" rel="noopener noreferrer">${NEARBY.mode==='walking'?'Walk':NEARBY.mode==='driving'?'Drive':NEARBY.mode==='bicycling'?'Bike':'Transit'} directions ↗</a><a class="btn btn-sm" href="${esc(safeMapsURL(p.url))}" target="_blank" rel="noopener noreferrer">${data.provider==='OpenStreetMap'?'OpenStreetMap':'Google Maps'} ↗</a>${p.location?`<button class="btn btn-sm" data-nearby-focus="${index}">Show on map</button>`:''}</div>${(p.attributions||[]).map(a=>`<a class="tiny" href="${esc(safeMapsURL(a.providerUri))}" target="_blank" rel="noopener noreferrer">${esc(a.provider||'')}</a>`).join('')}</li>`).join('')}</ol>${!data.places.length?'<p>No results returned in this radius. Try a wider search; this does not prove no businesses exist.</p>':''}`:''}`:''}</div>
    <p class="tiny">Directions open in Google Maps from the property, not your device location. Opening hours, prices and accessibility are unverified. Search radius is not travel distance.</p></section>`;
}
function safeMapsURL(value) {try{const url=new URL(value);return url.protocol==='https:'?url.href:'#';}catch(error){return '#';}}
function nearbyDirections(c,p) {
  const params=new URLSearchParams({api:'1',origin:`${c.coordinates.lat},${c.coordinates.lon}`,
    destination:p.location?`${p.location.latitude},${p.location.longitude}`:p.address||p.name,
    travelmode:NEARBY.mode});
  if(!p.id?.startsWith('osm-'))params.set('destination_place_id',p.id);
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
  if(focus) {
    const place=NEARBY.data?.places[Number(focus.dataset.nearbyFocus)];
    if(!place?.location)return;
    NEARBY.selected=place.id;
    const {latitude,longitude}=place.location;
    if(NEARBY.data.provider==='OpenStreetMap') {
      STREET.map?.panTo([latitude,longitude]);STREET.nearbyMarkers.get(place.id)?.openTooltip();
    } else MAPS.map?.panTo({lat:latitude,lng:longitude});
    document.querySelector('.nearby-map')?.scrollIntoView({block:'center',behavior:'instant'});
    return;
  }
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
