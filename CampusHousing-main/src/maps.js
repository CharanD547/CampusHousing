/* Only the browser Maps key reaches this SDK. Places stays behind the server. */
const MAPS={loading:null,error:null,map:null,element:null,markers:[],contextKey:null};
function googleMapShell(results) {
  const ids=results.map(r=>r.cand.id).join(',');
  return `<div class="map-card"><div class="google-map" data-offers="${esc(ids)}" style="height:560px;min-height:320px" aria-label="Google Maps housing and campus locations"></div><div class="map-bar"><span>Approximate housing and campus building locations. Select a marker to select its offer. Entrances, parking and travel times are unverified.</span></div></div>`;
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
      if (MAPS.element && MAPS.element!==el) {el.replaceWith(MAPS.element);el=MAPS.element;el.dataset.offers=offers;}
      el.dataset.ready='true';MAPS.element=el;
      const map=MAPS.map || (MAPS.map=new google.maps.Map(el,{center:{lat:37.2296,lng:-80.4234},zoom:13,mapId:'DEMO_MAP_ID',mapTypeControl:false,streetViewControl:false}));
      const contextKey=JSON.stringify([offers,S.commitments.map(c=>c.building_id)]);
      const shouldFit=MAPS.contextKey!==contextKey;MAPS.contextKey=contextKey;
      // Google marker elements detach when the parent view is replaced. Recreate them on
      // the retained map instance rather than assuming a matching context kept them alive.
      MAPS.markers.forEach(m=>m.map=null);MAPS.markers=[];
      const bounds=new google.maps.LatLngBounds(),seen=new Set();
      for (const id of el.dataset.offers.split(',')) {
        const c=candidate(id);if (!c || seen.has(c.property_id)) continue;seen.add(c.property_id);
        const position={lat:c.coordinates.lat,lng:c.coordinates.lon};bounds.extend(position);
        const marker=new google.maps.marker.AdvancedMarkerElement({map,position,title:c.property_name,gmpClickable:true});
        MAPS.markers.push(marker);
        marker.addEventListener('gmp-click',()=>{UI.selected=c.id;render();document.getElementById('card-'+c.id)?.scrollIntoView({block:'nearest'});});
      }
      for (const c of S.commitments) {
        const b=building(c.building_id);if(!b)continue;
        const position={lat:b.lat,lng:b.lon};bounds.extend(position);
        MAPS.markers.push(new google.maps.marker.AdvancedMarkerElement({map,position,title:'Campus: '+b.label}));
      }
      if (shouldFit && !bounds.isEmpty()) map.fitBounds(bounds,55);
    }
  } catch(error) {MAPS.error=error.message;render();toast('Map unavailable. The coordinate overview and offer list remain available.');}
}
function nearbySection(c) {
  if (!API.maps?.places_available) return '';
  return `<section class="panel stack-sm"><h2>Nearby essentials</h2><p class="small">Search Google Maps within 2.5 km of this property. Results are live and excluded from saved briefs and AI context.</p><label for="nearby-category">Category</label><select class="input" id="nearby-category"><option value="groceries">Groceries</option><option value="cafe">Cafes</option><option value="pharmacy">Pharmacies</option><option value="library">Libraries</option></select><button class="btn" data-action="nearby-search" data-property="${esc(c.property_id)}">Find nearby places</button><div id="nearby-results" aria-live="polite"></div></section>`;
}
function safeMapsURL(value) {try{const url=new URL(value);return url.protocol==='https:'?url.href:'#';}catch(error){return '#';}}
document.addEventListener('click',async event=>{
  const button=event.target.closest('[data-action="nearby-search"]');if(!button)return;
  const target=document.getElementById('nearby-results'),category=document.getElementById('nearby-category').value;
  button.disabled=true;target.textContent='Searching nearby places…';
  try {
    const data=await api('/properties/'+encodeURIComponent(button.dataset.property)+'/nearby?category='+encodeURIComponent(category));
    if (!target.isConnected)return;
    target.innerHTML=`<p>${esc(data.reason)}</p>${data.status==='available'?`<div style="padding:10px 10px 5px"><img src="/assets/google-maps-attribution.svg" height="18" alt="Google Maps" style="height:18px;width:auto"></div><ul>${data.places.map(p=>`<li><a href="${esc(safeMapsURL(p.url))}" target="_blank" rel="noopener noreferrer">${esc(p.name)}</a><p class="small">${esc(p.address || '')}</p>${p.attributions.map(a=>`<a href="${esc(safeMapsURL(a.providerUri))}" target="_blank" rel="noopener noreferrer">${esc(a.provider || '')}</a>`).join('')}</li>`).join('')}</ul>${!data.places.length?'<p>No places returned; this is not proof that none exist.</p>':''}`:''}`;
  }catch(error){target.textContent=error.message;}finally{button.disabled=false;}
});
