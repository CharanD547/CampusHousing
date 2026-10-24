/* ---------- Explore ---------- */
function bandOf(r) {
  const lim = r.commute.limiting;
  if (!r.commute.total) return { key: 'none', label: 'No schedule' };
  if (r.commute.supported < r.commute.total) return { key: 'none', label: `${r.commute.supported}/${r.commute.total} routed` };
  const m = lim.best.minutes;
  if (m > S.prefs.max_commute_minutes) return { key: 'over', label: `${m} min` };
  if (m <= 15) return { key: 'short', label: `${m} min` };
  return { key: 'mid', label: `${m} min` };
}

function schematicMap(results, opts = {}) {
  if (S.sim.mapFails) return `<div class="map-card panel"><h3>Map unavailable</h3><p>Every offer is still available in the list.</p><button class="btn" data-action="map-retry">Retry map</button></div>`;
  if (API.maps?.enabled && !MAPS.error) return googleMapShell(results);
  const destinations=S.commitments.map(c=>building(c.building_id)).filter(Boolean);
  const points=[...CANDIDATES.map(c=>({lat:c.coordinates.lat,lon:c.coordinates.lon})),...destinations];
  const lats=points.map(p=>p.lat),lons=points.map(p=>p.lon);
  const minLat=Math.min(...lats)-.003,maxLat=Math.max(...lats)+.003,minLon=Math.min(...lons)-.003,maxLon=Math.max(...lons)+.003;
  const xy=p=>[70+(p.lon-minLon)/(maxLon-minLon)*860,620-(p.lat-minLat)/(maxLat-minLat)*540];
  const seen=new Set();
  const markers=results.filter(r=>{if(seen.has(r.cand.property_id))return false;seen.add(r.cand.property_id);return true;}).map(r=>{
    const c=r.cand,[x,y]=xy({lat:c.coordinates.lat,lon:c.coordinates.lon});
    return `<g class="mk" tabindex="0" role="button" aria-label="${esc(c.property_name)}" data-action="select" data-id="${esc(c.id)}" transform="translate(${x},${y})"><circle r="12" fill="var(--ink)"/><text x="${x>750 ? -17:17}" text-anchor="${x>750 ? 'end':'start'}" y="5" font-size="18" fill="var(--ink)">${esc(c.property_name)}</text></g>`;
  }).join('');
  const buildings=destinations.map(b=>{const [x,y]=xy(b);return `<g transform="translate(${x},${y})"><rect x="-6" y="-6" width="12" height="12" fill="var(--amber)"/><text x="12" y="-10" font-size="16">${esc(b.short)}</text></g>`;}).join('');
  return `<div class="map-card"><svg viewBox="0 0 1000 700" role="img" aria-label="Geographic overview of housing and selected campus buildings"><rect width="1000" height="700" fill="var(--map-bg)"/>${markers}${buildings}<text x="35" y="45" font-size="18">N ↑ · building and property locations</text></svg><div class="map-bar"><span>Coordinate overview: one marker per property. Select individual offers from the list. No street network or travel-time shading is shown. Property address points and VT GIS building locations are approximate destinations, not verified entrances.</span></div></div>`;
}

function candCard(r) {
  const c = r.cand, sel = c.id === UI.selected;
  const top = r.conflicts[0] || r.unknowns[0];
  return `<li class="cand ${sel ? 'sel' : ''}" id="card-${c.id}" data-action="select" data-id="${c.id}">
    <div class="cand-photo" style="--pos:${PHOTO_POS[c.id] || '47% 50%'}" aria-hidden="true"></div>
    <div class="cand-top">
      <div><div class="cand-name"><button type="button" data-action="select" data-id="${c.id}" aria-pressed="${sel}">${esc(c.property_name)}</button></div><div class="cand-area">${esc(typeLabel(c.type))} · ${esc(c.area)}${c.offer ? ' · ' + esc(c.offer.layout) : ''}</div></div>
      ${fitChip(r.fit)}
    </div>
    ${priceBlock(r)}
    <div class="cand-meta"><span>${coverageDots(r)}<b>${coverageText(r)}</b></span></div>
    ${top ? `<div class="cand-unknown ${r.conflicts.length ? 'bad' : ''}">${r.conflicts.length ? I.x : I.q}<span>${esc(top.text)}${(r.conflicts.length + r.unknowns.length) > 1 ? ` <span class="small">+${r.conflicts.length + r.unknowns.length - 1} more</span>` : ''}</span></div>` : ''}
    <div class="cand-meta">${freshness(r)}${demoChip()}</div>
    <div class="cand-actions"><a class="btn btn-sm" href="#property-${c.id}">Details and sources</a><button class="btn btn-sm btn-quiet" data-action="evidence" data-id="${c.id}">Evidence</button>${c.type === 'offer' ? shortlistBtn(c.id) : ''}</div>
  </li>`;
}

function viewExplore() {
  const q = UI.query.trim().toLowerCase();
  let all = S.sim.emptyInventory ? [] : compareAll();
  const total = all.length;
  let rs = all.filter((r) => UI.filters[r.fit] && (!q || (r.cand.property_name + ' ' + r.cand.area + ' ' + (r.cand.address || '')).toLowerCase().includes(q)));
  rs.sort((a, z) => FIT_ORDER[a.fit] - FIT_ORDER[z.fit] || a.cand.property_name.localeCompare(z.cand.property_name));
  const counts = { fit: 0, conflict: 0, insufficient: 0 };
  all.forEach((r) => counts[r.fit]++);
  const list = !total
    ? `<div class="empty"><h3>No reviewed places to show</h3><p>The reviewed collection is empty right now. That says nothing about how many apartments exist in Blacksburg, only that none have passed review here yet.</p><button class="btn btn-sm" data-action="sim-off" data-key="emptyInventory">Reload the collection</button></div>`
    : !rs.length
      ? `<div class="empty"><h3>Nothing matches “${esc(UI.query)}”</h3><p>Search covers place names, areas and streets in the reviewed collection.</p><button class="btn btn-sm" data-action="clear-search">Clear search and filters</button></div>`
      : `<ul class="cand-list">${rs.map(candCard).join('')}</ul>`;
  return `
  <div class="page-head"><div class="kicker">Explore · Blacksburg, VA</div><h1 tabindex="-1" id="page-title">Places near Virginia Tech</h1><p>${total} reviewed places, checked against revision ${S.revision} of your needs and ${plural(S.commitments.length, 'class', 'classes')}. Grouped by status, never by a hidden score.</p></div>
  <div class="explore">
    <div>
      <div class="toolbar"><div class="explore-tools">
        <div class="search"><label class="sr" for="q">Search places</label>${I.search}<input class="input" id="q" type="search" placeholder="Search by name, area or street" value="${esc(UI.query)}" data-ui="query" autocomplete="off"></div>
        <div class="filter-row" role="group" aria-label="Filter by status">
          ${['fit', 'insufficient', 'conflict'].map((k) => `<label class="fchip"><input type="checkbox" id="flt-${k}" data-filter="${k}" ${UI.filters[k] ? 'checked' : ''}><span>${FIT_META[k].icon}${FIT_META[k].label} <span class="num">${counts[k]}</span></span></label>`).join('')}
        </div>
      </div></div>
      <div class="results-meta"><span aria-live="polite">${plural(rs.length, 'place')} shown, by status then A to Z</span><button class="btn btn-sm map-mobile-toggle" data-action="toggle-map" aria-expanded="${UI.mapOpen}">${UI.mapOpen ? 'Hide map' : 'Show map'}</button></div>
      ${list}
    </div>
    <div class="map-wrap ${UI.mapOpen ? '' : 'collapsed'}">${total ? schematicMap(rs) : ''}</div>
  </div>`;
}

/* ---------- Property detail ---------- */
function feeRows(o, kind, hh) {
  return o.fees.filter((f) => f.kind === kind).map((f) => {
    const share = f.amount == null ? null : f.basis === 'whole_unit' ? f.amount / hh : f.amount;
    const range = f.amount_max != null && f.amount_max !== f.amount ? `–${money2(f.amount_max)}` : '';
    const notCounted = f.research || f.included_in_advertised_total == null && f.kind === 'mandatory' && f.classification;
    const status = f.research ? 'Research observation; not counted until reviewed' : notCounted ? 'Not confirmed whether already in the price; not added' : f.status === 'conflicting_sources' ? 'Sources disagree' : '';
    return `<tr><td>${esc(f.label)}<div class="tiny">${f.amount == null ? 'Amount not published' : `${money2(f.amount)}${range} ${BASIS_LABEL[f.basis] || ''} ${f.frequency ? FREQ_LABEL[f.frequency] : ''}`}${f.note ? ' · ' + esc(f.note) : ''}</div>${status ? `<div class="tiny" style="color:var(--unsure)">${status}</div>` : ''}</td><td class="r ${share == null ? 'unk' : ''} num">${share == null ? 'Unknown' : (notCounted ? '<s>' : '') + money2(share) + range + (notCounted ? '</s>' : '')}</td></tr>`;
  }).join('');
}

function housingResearch(c) {
  if (!c.research?.length) return '';
  const label=k=>k.replaceAll('_',' ');
  return `<section class="panel stack-sm"><h2>Additional pricing evidence</h2><p class="small">These observations are not included in the comparison totals. Confirm the exact unit, term and which fees are already included.</p>${c.research.map(o=>{
    const f=o.facts;let facts='';
    if(f.ranges) facts='<ul>'+f.ranges.map(r=>`<li>${esc(r.layout)} · ${r.bedrooms} bedrooms: ${money(r.minimum)}–${money(r.maximum)}; billing basis needs confirmation</li>`).join('')+'</ul>';
    for(const key of ['monthly','per_installment','one_time']) if(f[key]) facts+=`<p class="small"><b>${esc(label(key))}:</b> ${Object.entries(f[key]).map(([k,v])=>esc(label(k))+': '+money2(Number(v))).join(' · ')}</p>`;
    if(f.security_deposit_range) facts+=`<p class="small">Screening-dependent security deposit: ${money(f.security_deposit_range[0])}–${money(f.security_deposit_range[1])}.</p>`;
    if(f.advertised_total_monthly_leasing_price) facts+=`<p>${esc(f.layout)}: ${money(f.advertised_total_monthly_leasing_price)} advertised leasing total; ${fmtDate(f.lease_start)}–${fmtDate(f.lease_end)}.</p>`;
    return `<div>${facts}<p class="small">${esc(o.limitation)}</p><a href="${esc(o.url)}" target="_blank" rel="noopener noreferrer">Read original disclosure ↗</a></div>`;
  }).join('')}</section>`;
}

const UTILITY_STATE = { INCLUDED: 'Included', EXCLUDED_FIXED_FEE: 'Covered by a listed fee', EXCLUDED_VARIABLE_USAGE: 'You pay by usage', PROVIDER_DEPENDENT: 'You arrange', UNKNOWN: 'Not confirmed' };

// Structured evidence from the pricing research: ranges, fees, utilities, conflicts and operator questions.
function pricingEvidence(c) {
  const o = c.offer, a = o.advertised_range, hh = S.prefs.household_size;
  const sourceName = (id) => (c.sources || []).find((s) => s.id === id)?.title || id;
  const util = Object.entries(o.utility_matrix || {});
  const blocks = [];
  if (a) blocks.push(`<h3>Advertised range</h3><p><b class="num">${money(a.minimum)}–${money(a.maximum)}</b> ${BASIS_LABEL[a.basis === 'whole_unit' ? 'whole_unit' : 'per_person']} ${FREQ_LABEL[a.period] || ''}</p>
    <ul class="small">${a.plans.map((p) => `<li>${esc(p.name)}: ${money(p.minimum)}${p.maximum !== p.minimum ? '–' + money(p.maximum) : ''}${p.square_feet ? ` · ${esc(p.square_feet)} sq ft` : ''}</li>`).join('')}${(a.uncovered_plans || []).map((p) => `<li>Also: ${esc(p.name)} ${money(p.minimum)}–${money(p.maximum)}</li>`).join('')}</ul>
    <p class="tiny">${esc(a.note)} Source: ${esc(sourceName(a.source_id))}.</p>`);
  if (a && o.fees.length) {
    const kinds = [['mandatory', 'Recurring'], ['one_time', 'One-time, not refunded'], ['refundable', 'Refundable deposits'], ['credited', 'Paid early, credited later'], ['optional', 'Optional or situational']];
    blocks.push(kinds.filter(([k]) => o.fees.some((f) => f.kind === k)).map(([k, l]) => `<table class="ledger"><caption>${l}</caption><tbody>${feeRows(o, k, hh)}</tbody></table>`).join(''));
  }
  const utilReviewed = (c.sources || []).find((s) => s.id === o.utility_source_id)?.review_status === 'reviewed';
  if (util.length) blocks.push(`<h3>Utilities and services</h3>${utilReviewed ? '' : '<p class="tiny" style="color:var(--unsure)">From a research observation (' + esc(sourceName(o.utility_source_id)) + '); not yet confirmed against a reviewed source.</p>'}<ul class="small">${util.map(([k, v]) => `<li>${esc(k.replaceAll('_', ' '))}: ${UTILITY_STATE[v] || esc(v)}</li>`).join('')}</ul>`);
  if (o.source_conflicts?.length) blocks.push(`<h3>Where sources disagree</h3><ul class="small">${o.source_conflicts.map((x) => `<li>${esc(x.field.replaceAll('_', ' '))}: ${x.values.map((v) => `${esc(v.value)} (${esc(sourceName(v.source_id))})`).join(' vs ')}. ${esc(x.resolution)}</li>`).join('')}</ul>`);
  if (o.operator_questions?.length) blocks.push(`<h3>Ask the leasing office</h3><ul class="small">${o.operator_questions.map((q) => `<li>${esc(q)}</li>`).join('')}</ul>`);
  if (!blocks.length) return '';
  return `<section class="panel stack-sm" aria-labelledby="h-pe-${c.id}"><h2 id="h-pe-${c.id}">Pricing research</h2><p class="small">From the Oct 24, 2026 pricing research. Only amounts from reviewed sources are counted in the comparison.</p>${blocks.join('')}</section>`;
}

function priceDetail(r) {
  const c = r.cand, p = S.prefs;
  if (c.type === 'area') {
    const a = c.area_range;
    return `<section class="panel stack-sm"><h2>Area rent range</h2><div class="price-hero"><span class="amt num">${money(a.min)}–${money(a.max)}</span><span class="basis">${BASIS_LABEL[a.basis]} ${FREQ_LABEL[a.frequency]}</span></div>
      ${asyncNotice('unsure', 'This is a range for the area, not an offer', 'It summarizes reviewed listings nearby. Pick a specific place to see a real price you could ask for.')}</section>`;
  }
  if (!c.offer || !r.share) return `<section class="panel stack-sm"><h2>Price</h2><div class="price-hero"><span class="amt" style="color:var(--unsure);font-size:2rem">Price needs confirmation</span></div>
    ${asyncNotice('unsure', 'No reviewed price for this offer', 'An exact comparable price is not established in the catalog. Nothing is filled in from a different plan or promotional range.', '<p class="small" style="margin-top:6px">Ask: What is the rent per person or per unit, and which fees are required?</p>')}</section>`;
  const o = c.offer, pr = o.price, sh = r.share, hh = p.household_size;
  const termTotal = pr.payment_count ? `<p class="small">${pr.payment_count} ${pr.frequency === 'installment' ? 'installments' : 'monthly payments'} documented, so the term's base rent is <b class="num">${money(pr.amount * pr.payment_count)}</b> ${BASIS_LABEL[pr.basis]}.${!sh.complete ? ' Required costs with unknown amounts are not included.' : ''}</p>` : '<p class="small">Payment count not documented, so no term total is shown.</p>';
  return `<section class="panel stack-sm" aria-labelledby="h-price">
    <div class="panel-head"><h2 id="h-price">What it costs</h2>${freshness(r)}</div>
    <div class="price-hero"><span class="amt num">${money(pr.amount)}</span><span class="basis">${BASIS_LABEL[pr.basis]} ${FREQ_LABEL[pr.frequency]}</span></div>
    <p class="small">${esc(o.layout)} · ${o.lease === 'individual' ? 'Individual lease' : o.lease === 'joint' ? 'Joint lease' : 'Lease responsibility unconfirmed'} · ${esc(o.term)}${pr.frequency === 'installment' ? '. Installments are payments on the lease schedule, not calendar months.' : ''}</p>
    ${o.correction ? asyncNotice('unsure', `Price corrected on ${fmtDate(o.correction.corrected_on)}`, esc(o.correction.note) + ' Two sources disagreed; the rendered operator page is used.') : ''}
    ${pr.basis === 'whole_unit' ? `<div class="scenario"><b>Splitting scenario, not a lease term</b><span class="small">${money(pr.amount)} ÷ ${hh} people = ${money2(pr.amount / hh)} each. On a joint lease, every signer can be held responsible for the full ${money(pr.amount)} if someone doesn't pay.</span></div>` : ''}
    <table class="ledger">
      <caption>Recurring, your share</caption>
      <tbody>
        <tr><td>Base rent${pr.basis === 'whole_unit' ? ` <span class="tiny">(÷ ${hh})</span>` : ''}</td><td class="r num">${money2(sh.base)}</td></tr>
        ${feeRows(o, 'mandatory', hh)}
        ${o.unknown_costs.filter((u) => !o.fees.some((f) => f.amount == null && u.startsWith(f.label))).map((u) => `<tr><td>${esc(u)}</td><td class="r unk">Unknown</td></tr>`).join('')}
        <tr class="total"><td>${sh.complete ? 'Recurring total per person' : 'Known subtotal per person (incomplete)'}</td><td class="r num">${money2(sh.subtotal)}</td></tr>
      </tbody>
    </table>
    ${o.included.length ? `<p class="small">Included in rent: ${o.included.map(esc).join(', ')}.</p>` : ''}
    ${o.fees.some((f) => f.kind === 'optional') ? `<table class="ledger"><caption>Optional extras</caption><tbody>${feeRows(o, 'optional', hh)}</tbody></table>` : ''}
    ${o.fees.some((f) => f.kind === 'refundable') ? `<table class="ledger"><caption>Refundable deposits</caption><tbody>${feeRows(o, 'refundable', hh)}</tbody></table>` : ''}
    ${o.fees.some((f) => f.kind === 'one_time') ? `<table class="ledger"><caption>One-time, not refunded</caption><tbody>${feeRows(o, 'one_time', hh)}</tbody></table>` : ''}
    ${termTotal}
    ${o.fees.filter((f) => f.kind === 'term').map((f) => `<p class="small">Plus ${money2(f.amount)} ${esc(f.label.toLowerCase())}${f.derivation ? ` (${esc(f.derivation)})` : ''}. ${esc(f.note || '')}</p>`).join('')}
    <p class="tiny">Source: ${esc(c.evidence[0].source_name)}, reviewed ${fmtDate(pr.last_reviewed_at)}. <button class="linkish" data-action="evidence" data-id="${c.id}">Open evidence</button></p>
  </section>`;
}

function commuteDetail(r) {
  if (!r.commute.total) return `<div class="empty"><h3>No classes to route to</h3><p>Add your schedule and each class gets its own route from here.</p><a class="btn btn-sm" href="#schedule">Add classes</a></div>`;
  return `<section class="panel stack-sm" aria-labelledby="h-routes"><h2 id="h-routes">Every route checked</h2>
    ${r.commute.per.some(x=>x.ests.some(e=>e.provider==='google_routes')) ? '<div style="padding:10px 10px 5px"><img src="/assets/google-maps-attribution.svg" height="18" alt="Google Maps" style="height:18px;width:auto"></div><p class="tiny">Live Google Maps estimates. Saved briefs exclude these provider results and require fresh route checks.</p>' : ''}
    <div class="cmp-scroll" style="border:0;background:none"><table class="ledger" style="min-width:420px"><thead><tr><th>Class</th><th>Mode</th><th class="r">Time</th></tr></thead><tbody>
    ${r.commute.per.map((x) => x.ests.map((e, i) => `<tr><td>${i === 0 ? `<b>${esc(x.b.short)}</b><div class="tiny">${esc(x.date)} by ${fmtTime(x.c.arrival_time_local)}</div>` : ''}</td><td>${modeIcon(e.mode)} ${MODE_LABEL[e.mode]}<div class="tiny">${esc(e.context)}</div></td><td class="r num">${e.status === 'supported' ? `<b>${e.minutes} min</b>` : '<span class="unk">No supported estimate</span>'}</td></tr>`).join('')).join('')}
    </tbody></table></div>
    <p class="tiny">Origin: ${esc(r.cand.coordinate_basis.toLowerCase())}. Routed for ${fmtDay(ROUTING_DATE)} with provider availability shown above. Missing estimates remain unknown.</p>
  </section>`;
}

function fitSummary(r) {
  return `<section class="panel stack-sm" aria-labelledby="h-fit"><div class="panel-head" style="margin:0"><h2 id="h-fit">Against your needs</h2>${fitChip(r.fit)}</div>
    ${!r.conflicts.length && !r.unknowns.length ? '<p class="small">Every check passed with current sources: budget, bedrooms, lease and all routed classes.</p>' : ''}
    <ul class="check-list">${r.conflicts.map((x) => `<li><span style="color:var(--conflict)">${I.x}</span><span>${esc(x.text)}</span></li>`).join('')}${r.unknowns.map((x) => `<li><span style="color:var(--unsure)">${I.q}</span><span>${esc(x.text)}</span></li>`).join('')}</ul>
  </section>`;
}

function questionsBlock(id) {
  const n = S.notes[id] || { questions: [] };
  return `<section class="panel stack-sm" aria-labelledby="h-q-${id}"><h2 id="h-q-${id}">Questions for this place</h2>
    ${n.questions.length ? `<div class="qa">${n.questions.map((q) => `<div class="qa-row"><div><b>${esc(q.text)}</b>${q.answer ? `<p class="small"><span class="who">Your note:</span> ${esc(q.answer)}</p>` : ''}</div><button class="btn btn-sm btn-quiet" data-action="q-delete" data-id="${id}" data-q="${q.id}" aria-label="Remove question">Remove</button>
      <div style="grid-column:1/-1"><label class="sr" for="ans-${q.id}">Answer you got</label><input class="input" style="min-height:40px;font-size:.9375rem" id="ans-${q.id}" placeholder="Answer you got (saved as your note)" value="${esc(q.answer)}" data-answer="${id}" data-q="${q.id}"></div></div>`).join('')}</div>` : '<p class="small">Nothing yet. Questions you add stay attached to this place and go into saved briefs.</p>'}
    <form class="btn-row" data-form="q-add" data-id="${id}"><label class="sr" for="newq-${id}">New question</label><input class="input" style="flex:1;min-width:200px" id="newq-${id}" placeholder="e.g. Is the utility package per person?"><button class="btn" type="submit">Add question</button></form>
  </section>`;
}

function viewProperty(id) {
  const c = candidate(id);
  if (!c) return `<div class="empty"><h3>That place isn't in the reviewed collection</h3><p>It may have been removed after review.</p><a class="btn" href="#explore">Back to Explore</a></div>`;
  const r = compare(c, S.prefs, S.commitments);
  return `<!--full-->
  <section class="band"><div class="wrap">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="#explore">Explore</a><span aria-hidden="true">/</span><span>${esc(c.property_name)}</span></nav>
  <div class="prop-head">
    <div><div class="kicker">${esc(typeLabel(c.type))} · ${esc(c.area)}</div><h1 tabindex="-1" id="page-title" style="margin-top:18px">${esc(c.property_name)}</h1><p class="lede">${esc(typeLabel(c.type))} in ${esc(c.area)}${c.address ? ', ' + esc(c.address) : ''}. Map point is the ${esc(c.coordinate_basis.toLowerCase())}.</p><div class="chips">${fitChip(r.fit)}${demoChip()}</div></div>
    <div class="btn-row">${c.type === 'offer' ? shortlistBtn(c.id, false) : ''}<button class="btn" data-action="evidence" data-id="${c.id}">${I.doc} All evidence</button></div>
  </div></div></section>
  <div class="wrap page">
  <div class="two-col">
    <div class="stack">${priceDetail(r)}${pricingEvidence(c)}${housingResearch(c)}${nearbySection(c)}${commuteDetail(r)}</div>
    <div class="stack">${commuteSign(r)}${fitSummary(r)}${questionsBlock(c.id)}</div>
  </div></div>`;
}

function evidenceDrawer(id) {
  const c = candidate(id);
  const disagree = c.evidence.length > 1;
  return `<div class="drawer-scrim" data-action="close-drawer"></div>
  <aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="dr-t" id="drawer">
    <div class="drawer-head"><div><h2 id="dr-t">Evidence for ${esc(c.property_name)}</h2><p class="small">What each source says, when it was checked, and what it supports.</p></div><button class="btn btn-sm" data-action="close-drawer" id="drawer-close">Close</button></div>
    ${disagree ? asyncNotice('unsure', 'Sources disagree', 'The figure shown uses the most recent rendered operator page. The older copy is kept here so you can see the difference.') : ''}
    ${[...c.evidence, ROUTE_EVIDENCE].map((e) => `<div class="ev"><b>${esc(e.source_name)}</b><dl><dt>Type</dt><dd>${esc(e.source_type)}</dd><dt>Checked</dt><dd>${fmtDate(e.observed_at)} (${ago(e.observed_at)})</dd><dt>Supports</dt><dd>${esc(e.supports)}</dd><dt>ID</dt><dd class="num">${esc(e.id)}</dd></dl>${e.url ? `<p><a href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">Open original source ↗</a></p>` : ''}${e.excerpt ? `<blockquote>${esc(e.excerpt)}</blockquote>` : ''}</div>`).join('')}
    <p class="tiny">Sources are loaded from the backend evidence repository. Asking prices are dated evidence; confirm availability and all mandatory charges.</p>
  </aside>`;
}

/* ---------- Compare + AI ---------- */
function aiPanel() {
  const a = S.ai;
  const btn = (label) => `<button class="btn btn-amber" data-action="run-ai" ${a.status === 'pending' || S.shortlist.length === 0 ? 'disabled' : ''}>${label}</button>`;
  let body = '';
  if (a.status === 'idle') body = `<p class="small">Get a plain-language read on your shortlist: why each place might work, its main limitation, and what to ask next. The comparison above is complete without it.</p>${btn('Why these options?')}`;
  else if (a.status === 'pending') body = `<div class="pending-bar" role="progressbar" aria-label="Writing explanation"></div><p class="small" role="status">Writing an explanation for revision ${a.revision}. If you change your inputs before it finishes, this one is discarded.</p>`;
  else if (a.status === 'unavailable') body = asyncNotice('bad', 'AI explanation unavailable', esc(a.reason || 'No verified model response is available. Your comparison, sources and shortlist are unaffected.'), `<div class="btn-row" style="margin-top:10px">${btn('Try again')}</div>`);
  else if (a.status === 'interrupted') body = asyncNotice('unsure', 'The last request was interrupted', 'The page reloaded before an explanation came back. Nothing was saved from it.', `<div class="btn-row" style="margin-top:10px">${btn('Run it again')}</div>`);
  else if (a.status === 'discarded') body = asyncNotice('unsure', 'Explanation discarded', `It was written for revision ${a.revision}, but your inputs changed to revision ${S.revision} while it was running.`, `<div class="btn-row" style="margin-top:10px">${btn(`Explain revision ${S.revision}`)}</div>`);
  else if (a.status === 'done') {
    const stale = a.revision !== S.revision;
    const res = a.result;
    body = `${stale ? asyncNotice('unsure', 'Out of date', `Written for revision ${a.revision}. Your inputs are now revision ${S.revision}, so the reasons below may be wrong.`, `<div class="btn-row" style="margin-top:10px">${btn(`Explain revision ${S.revision}`)}</div>`) : ''}
      <div style="${stale ? 'opacity:.55' : ''}">
        <p>${esc(res.summary)}</p>
        ${res.candidate_explanations.map((x) => `<div class="ai-item"><h3>${esc(x.name)} ${fitChip(x.fit)}</h3><dl><dt>Why</dt><dd>${esc(x.reason)}</dd><dt>Limitation</dt><dd>${esc(x.limitation)}</dd><dt>Ask next</dt><dd>${esc(x.next_question)}</dd><dt>Sources</dt><dd><button class="linkish" data-action="evidence" data-id="${x.candidate_id}">${x.evidence_ids.map(esc).join(', ')}</button></dd></dl></div>`).join('')}
      </div>
      ${!stale ? `<div class="btn-row">${btn('Explain again')}</div>` : ''}`;
  }
  return `<section class="ai" aria-labelledby="h-ai">
    <div class="ai-head"><div><div class="kicker">Explanation</div><h2 id="h-ai">Why these options?</h2></div><div class="ai-run">${a.status === 'done' ? `<span class="chip chip-neutral">Revision ${a.revision}</span><span class="chip chip-demo">Verified model response</span>` : '<span class="chip chip-demo">Optional Gemma provider</span>'}</div></div>
    ${body}
    <p class="tiny">Explanations only restate checks and sources from the comparison. Money and time figures come from the comparison, never from the model.</p>
  </section>`;
}

function viewCompare() {
  const rs = S.shortlist.map(candidate).filter(Boolean).map((c) => compare(c, S.prefs, S.commitments));
  if (!rs.length) return `<div class="page-head"><div class="kicker">Compare</div><h1 tabindex="-1" id="page-title">Compare</h1></div><div class="empty"><h3>Your shortlist is empty</h3><p>Shortlist up to three places on Explore to compare them side by side.</p><a class="btn btn-primary" href="#explore">Go to Explore</a></div>`;
  const row = (label, fn) => `<tr><th scope="row">${label}</th>${rs.map((r) => `<td>${fn(r)}</td>`).join('')}${'<td></td>'.repeat(3 - rs.length)}</tr>`;
  const issues = (r) => [...r.conflicts.map((x) => `<li style="color:var(--conflict)">${esc(x.text)}</li>`), ...r.unknowns.map((x) => `<li>${esc(x.text)}</li>`)].join('') || '<li>None found</li>';
  return `
  <div class="page-head"><div class="kicker">Compare · revision ${S.revision}</div><h1 tabindex="-1" id="page-title">Side by side</h1><p>Your ${plural(rs.length, 'shortlisted place')}, checked against revision ${S.revision}. Columns follow your shortlist order; nothing is ranked.</p></div>
  <div class="cmp-scroll"><table class="cmp">
    <thead><tr><th><span class="sr">Check</span></th>${rs.map((r) => `<th scope="col"><a class="cname" href="#property-${r.cand.id}">${esc(r.cand.property_name)}</a>${fitChip(r.fit)}</th>`).join('')}${'<th></th>'.repeat(3 - rs.length)}</tr></thead>
    <tbody>
      ${row('Price as listed', (r) => r.share ? `<span class="amt num">${money(r.cand.offer.price.amount)}</span><div class="small">${BASIS_LABEL[r.cand.offer.price.basis]} ${FREQ_LABEL[r.cand.offer.price.frequency]}</div>` : '<b style="color:var(--unsure)">Price needs confirmation</b>')}
      ${row('Your share', (r) => r.share ? `<b class="num">${money(r.share.subtotal)}</b> <span class="small">${r.share.complete ? 'recurring, all known costs' : 'partial, costs missing'}${r.share.scenario ? `. Split ${S.prefs.household_size} ways as a scenario` : ''}</span>` : '—')}
      ${row('Source', (r) => `${freshness(r)}<div><button class="linkish small" data-action="evidence" data-id="${r.cand.id}">${esc(r.cand.evidence[0].id)}</button></div>`)}
      ${row('Rooms and lease', (r) => r.cand.offer ? `${esc(r.cand.offer.layout)}<div class="small">${r.cand.offer.lease === 'individual' ? 'Individual lease' : 'Joint lease'}</div>` : '—')}
      ${row('Commute coverage', (r) => `${coverageDots(r)}<b>${r.commute.supported} of ${r.commute.total}</b> routed<div class="small">${r.commute.within} within ${S.prefs.max_commute_minutes} min</div>`)}
      ${row('Longest trip', (r) => r.commute.limiting ? `<b class="num">${r.commute.limiting.best.minutes} min</b> <span class="small">to ${esc(r.commute.limiting.b.short)} by ${MODE_LABEL[r.commute.limiting.best.mode].toLowerCase()}</span>` : '—')}
      ${row('Conflicts and unknowns', (r) => `<ul>${issues(r)}</ul>`)}
    </tbody>
  </table></div>
  <p class="order-note">${I.info}<span>How to read this: conflicts come first because a lower price can't make up for a hard “no”. Places with unknowns aren't ranked below or above each other; they're tied until the missing facts are found.</span></p>
  ${aiPanel()}
  <div class="btn-row" style="margin-top:20px"><a class="btn btn-primary" href="#shortlist">Add questions and save a brief</a></div>`;
}

/* ---------- Shortlist + briefs ---------- */
function viewShortlist() {
  const items = S.shortlist.map(candidate).filter(Boolean);
  const body = items.length ? items.map((c) => {
    const r = compare(c, S.prefs, S.commitments);
    return `<section class="panel sl-item" aria-labelledby="sl-${c.id}">
      <div class="panel-head" style="margin:0"><div><h2 id="sl-${c.id}"><a href="#property-${c.id}" style="text-decoration:none">${esc(c.property_name)}</a></h2><p class="small">${esc(c.offer?.layout || typeLabel(c.type))}</p></div><div class="chips">${fitChip(r.fit)}</div></div>
      ${priceBlock(r)}
      <p class="small">${coverageDots(r)}${coverageText(r)}</p>
      ${questionsBlock(c.id).replace('class="panel stack-sm"', 'class="stack-sm"')}
      <div class="btn-row"><button class="btn btn-sm btn-quiet" data-action="toggle-shortlist" data-id="${c.id}">Remove from shortlist</button></div>
    </section>`;
  }).join('') : `<div class="empty"><h3>Nothing shortlisted yet</h3><p>Shortlist up to three places from Explore. Questions you add stay with each place.</p><a class="btn btn-primary" href="#explore">Go to Explore</a></div>`;
  return `
  <div class="page-head"><div class="kicker">Saved · ${items.length} of 3</div><h1 tabindex="-1" id="page-title">Shortlist</h1><p>${items.length} of 3 places. Add the questions you still need answered, then save a brief to keep a frozen copy of where things stand today.</p></div>
  <div class="two-col">
    <div class="stack">${body}</div>
    <aside class="stack side">
      <div class="panel stack-sm"><h2>Save a decision brief</h2><p class="small">A frozen snapshot of your needs, schedule, these places, their prices with basis and dates, routes, questions and AI status. Later price corrections won't change it.</p>
        <button class="btn btn-primary" data-action="save-brief" ${items.length ? '' : 'disabled'}>Save brief</button>
        <p class="tiny">${I.lock} Saved locally and synced to this backend. It won't appear on other devices.</p></div>
      <div class="panel stack-sm"><h2>Saved briefs</h2>${S.briefs.length ? `<ul class="brief-list">${S.briefs.map((b) => `<li><a href="#brief-${b.id}"><b>${new Date(b.saved_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</b><span class="small">${plural(b.candidates.length, 'place')} · revision ${b.revision}${b.origin === 'guide' ? ' · DormToDoor' : ''}</span></a></li>`).join('')}</ul>` : '<p class="small">None yet.</p>'}</div>
      ${S.shortlist.length >= 2 ? '<a class="btn" href="#compare">Compare side by side</a>' : ''}
    </aside>
  </div>`;
}

function briefText(b) {
  const L = [];
  L.push(`Roomwise decision brief`, `Saved ${new Date(b.saved_at).toLocaleString('en-US')} · revision ${b.revision} · source-backed research snapshot`, '');
  L.push(`Needs: ${money(b.prefs.monthly_budget_per_person)} per person, household of ${b.prefs.household_size}, ${b.prefs.private_bedroom_required ? 'private bedrooms' : 'sharing OK'}, ${b.prefs.travel_modes.map((m) => MODE_LABEL[m]).join('/')} up to ${b.prefs.max_commute_minutes} min`);
  L.push(`Schedule (routed for ${fmtDay(b.routing_date)}): ${b.commitments.map((c) => `${c.building} ${c.weekdays.map(dayLabel).join('/')} ${fmtTime(c.arrival)}${c.sample ? ' [sample]' : ''}`).join('; ')}`, '');
  b.candidates.forEach((c) => {
    L.push(`${c.name} — ${FIT_META[c.fit].label}`);
    L.push(c.price ? `  ${money(c.price.amount)} ${BASIS_LABEL[c.price.basis]} ${FREQ_LABEL[c.price.frequency]}, reviewed ${fmtDate(c.price.last_reviewed_at)}` : '  Price needs confirmation');
    if (c.share) L.push(`  Your share: ${money(c.share.subtotal)}${c.share.complete ? '' : ' (partial)'}`);
    c.commute.forEach((x) => L.push(`  ${x.building}: ${x.minutes != null ? x.minutes + ' min by ' + MODE_LABEL[x.mode].toLowerCase() : 'no supported route'}`));
    [...c.conflicts, ...c.unknowns].forEach((t) => L.push(`  ! ${t}`));
    c.questions.forEach((q) => L.push(`  ? ${q.text}${q.answer ? ' — your note: ' + q.answer : ''}`));
    L.push('');
  });
  L.push(`AI explanation: ${b.ai.status}`);
  if (b.checklist) { L.push('', 'Checklist'); b.checklist.forEach((i) => L.push(`  [${i.status.replace('_', ' ')}] ${i.title}${i.needs_confirmation ? ' (needs confirmation)' : ''}${i.notes ? ' — ' + i.notes : ''}`)); }
  return L.join('\n');
}

function viewBrief(id) {
  const b = S.briefs.find((x) => x.id === id);
  if (!b) return `<div class="empty"><h3>This brief isn't saved in this browser</h3><p>Briefs are stored locally, so they don't appear on other devices or after site data is cleared.</p><a class="btn" href="#shortlist">See saved briefs</a></div>`;
  return `
  <nav class="crumbs" aria-label="Breadcrumb"><a href="#shortlist">Shortlist</a><span aria-hidden="true">/</span><span>Brief</span></nav>
  <div class="page-head"><div class="kicker">Frozen brief</div><h1 tabindex="-1" id="page-title">Decision brief</h1><p>Saved ${new Date(b.saved_at).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })} from ${b.origin === 'guide' ? 'DormToDoor' : 'your shortlist'}.</p></div>
  <div class="frozen">${I.lock}<span>Frozen at revision ${b.revision}. Price corrections and changes to your needs after this point don't alter it.</span>${demoChip()}</div>
  <div class="two-col">
    <div class="stack">
      ${b.candidates.map((c) => `<section class="panel stack-sm"><div class="panel-head" style="margin:0"><h2>${esc(c.name)}</h2>${fitChip(c.fit)}</div>
        <p>${c.price ? `<b class="num">${money(c.price.amount)}</b> ${BASIS_LABEL[c.price.basis]} ${FREQ_LABEL[c.price.frequency]} <span class="tiny">reviewed ${fmtDate(c.price.last_reviewed_at)}</span>` : '<b style="color:var(--unsure)">Price needs confirmation</b>'}${c.share ? ` · your share ${money(c.share.subtotal)}${c.share.complete ? '' : ' (partial)'}` : ''}</p>
        <ul class="check-list">${c.commute.map((x) => `<li><span>${x.mode ? modeIcon(x.mode) : I.q}</span><span>${esc(x.building)}: ${x.minutes != null ? `<b>${x.minutes} min</b> by ${MODE_LABEL[x.mode].toLowerCase()}` : 'no supported route'}</span></li>`).join('')}</ul>
        ${c.conflicts.length || c.unknowns.length ? `<ul class="check-list">${c.conflicts.map((t) => `<li><span style="color:var(--conflict)">${I.x}</span><span>${esc(t)}</span></li>`).join('')}${c.unknowns.map((t) => `<li><span style="color:var(--unsure)">${I.q}</span><span>${esc(t)}</span></li>`).join('')}</ul>` : ''}
        ${c.questions.length ? `<p class="small"><b>Open questions:</b> ${c.questions.map((q) => esc(q.text) + (q.answer ? ` (your note: ${esc(q.answer)})` : '')).join(' · ')}</p>` : ''}
        <p class="tiny">Evidence: ${c.evidence.map((e) => `${esc(e.id)} (${fmtDate(e.observed_at)})`).join(', ')}</p>
      </section>`).join('')}
      ${b.checklist ? `<section class="panel stack-sm"><h2>Checklist at save time</h2><ul class="check-list">${b.checklist.map((i) => `<li><span>${i.status === 'done' ? I.check : I.q}</span><span>${esc(i.title)} <span class="tiny">${i.status.replace('_', ' ')}${i.needs_confirmation ? ', needs confirmation' : ''}</span></span></li>`).join('')}</ul></section>` : ''}
    </div>
    <aside class="stack">
      <div class="panel stack-sm"><h2>Inputs at save time</h2><dl class="kv">
        <dt>Budget</dt><dd>${money(b.prefs.monthly_budget_per_person)} per person</dd><dt>Household</dt><dd>${b.prefs.household_size}, ${b.prefs.private_bedroom_required ? 'private rooms' : 'sharing OK'}</dd>
        <dt>Travel</dt><dd>${b.prefs.travel_modes.map((m) => MODE_LABEL[m]).join(', ')}, ≤ ${b.prefs.max_commute_minutes} min</dd><dt>Routed for</dt><dd>${fmtDay(b.routing_date)}</dd>
        <dt>Classes</dt><dd>${b.commitments.map((c) => `${esc(c.building)}${c.sample ? ' (sample)' : ''}`).join(', ') || 'None'}</dd><dt>AI</dt><dd>${esc(b.ai.status)}</dd></dl></div>
      <div class="panel stack-sm"><h2>Take it with you</h2><p class="small">Copies a plain-text version you can paste into notes or an email. Uploaded documents are never included.</p><button class="btn btn-primary" data-action="copy-brief" data-id="${b.id}">Copy brief as text</button><textarea class="input" id="brief-text" readonly rows="6" aria-label="Brief as text">${esc(briefText(b))}</textarea></div>
    </aside>
  </div>`;
}
