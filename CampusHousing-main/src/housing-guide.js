/* Guide references remain separate from operator-checked offers. No inferred coordinates. */
const DIRECTORY={data:null,error:null,loading:false,query:'',zone:''};
async function loadHousingGuide() {
  if(DIRECTORY.loading || DIRECTORY.data)return;
  DIRECTORY.loading=true;
  try{DIRECTORY.data=await api('/housing-guide');DIRECTORY.error=null;}
  catch(error){DIRECTORY.error=error.message;}
  finally{DIRECTORY.loading=false;if(route().name==='directory')render();}
}
function viewHousingDirectory() {
  if(!DIRECTORY.data && !DIRECTORY.loading && !DIRECTORY.error)queueMicrotask(loadHousingGuide);
  const entries=DIRECTORY.data?.communities || [],query=DIRECTORY.query.toLowerCase();
  const visible=entries.filter(c=>(!DIRECTORY.zone || c.zone===DIRECTORY.zone) && `${c.name} ${c.address} ${c.layouts}`.toLowerCase().includes(query));
  return `<div class="page-head"><div class="kicker">Virginia Tech area housing guide</div><h1 id="page-title" tabindex="-1">Explore the wider housing market</h1><p>The guide adds context across six areas of Blacksburg. Addresses and layouts below are research references; linked catalog plans carry their own checked prices and dates.</p></div>
    <section class="panel stack-sm"><h2>Compare the same things</h2><p>Keep whole-unit rent, per-person installments, deposits and optional charges separate. A roommate split is a scenario, not permission for that occupancy. Confirm the exact unit, lease dates and all mandatory charges with the operator.</p><p class="small">Guide price references below have not been checked against a current unit quote. Reputation rankings, safety claims and fixed bus frequencies are excluded from comparisons.</p></section>
    <div class="toolbar directory-toolbar"><div><label for="directory-query">Search names, addresses and layouts</label><input class="input" id="directory-query" value="${esc(DIRECTORY.query)}" placeholder="Try Cedar Pointe or Knollwood"></div><div><label for="directory-zone">Area</label><select class="input" id="directory-zone"><option value="">All areas</option>${[...new Set(entries.map(c=>c.zone))].map(zone=>`<option ${zone===DIRECTORY.zone?'selected':''}>${esc(zone)}</option>`).join('')}</select></div></div>
    <p role="status">${DIRECTORY.error?esc(DIRECTORY.error):!DIRECTORY.data?'Loading guide references…':`${visible.length} of ${entries.length} community and neighborhood references`}</p>
    <div class="directory-grid">${visible.map(c=>{
      const plans=CANDIDATES.filter(p=>p.property_id===c.catalog_property_id || p.guide_reference?.id===c.id),group=plans.length?propertyGroups(plans.map(p=>compare(p,S.prefs,S.commitments)))[0]:null;
      return `<article class="panel stack-sm"><div class="kicker">${esc(c.zone)}</div><h2>${esc(c.name)}</h2><p>${esc(c.address)}</p><p class="small">${esc(c.layouts)}</p>${group?planPrices(group):`<p class="small"><b>Guide price reference, unverified:</b> ${esc(c.guide_price_summary)}</p><p class="small">No operator-checked catalog plans yet. Verify current rates, fees and availability at the source.</p>`}<div class="btn-row">${group?`<a class="btn btn-sm" href="#property-${esc(group.lead.cand.id)}">Catalog plans, sources and nearby places</a>`:''}${c.source_urls.slice(0,2).map((url,i)=>`<a class="btn btn-sm" href="${esc(safeMapsURL(url))}" target="_blank" rel="noopener noreferrer">Guide reference ${i+1} ↗</a>`).join('')}</div><p class="tiny">Guide reference · address and layout require confirmation${c.zone==='Private rentals and neighborhoods'?' · listings within a neighborhood vary by owner':''}</p></article>`;
    }).join('')}</div>`;
}
document.addEventListener('input',event=>{if(event.target.id==='directory-query'){DIRECTORY.query=event.target.value;render();}});
document.addEventListener('change',event=>{if(event.target.id==='directory-zone'){DIRECTORY.zone=event.target.value;render();}});
