/* ---------- DormToDoor guide ---------- */
const GUIDE_STEPS = [
  { n: 1, t: 'Your needs', s: 'Budget, roommates, travel' },
  { n: 2, t: 'Explore places', s: 'Housing and nearby essentials' },
  { n: 3, t: 'Compare', s: 'Up to three places' },
  { n: 4, t: 'Before you sign', s: 'Your checklist' },
];

function stepper(cur) {
  const done = S.guide.completed_steps;
  return `<ol class="stepper" aria-label="DormToDoor progress">${GUIDE_STEPS.map((st) => {
    const state = st.n === cur ? 'current' : done.includes(st.n) ? 'done' : 'todo';
    return `<li class="${state}"><span class="node" aria-hidden="true">0${st.n}${state === 'done' ? ' ' + I.check : ''}</span><a href="#guide-${st.n}" ${st.n === cur ? 'aria-current="step"' : ''}>${st.t}<span class="sr">${state === 'done' ? ', complete' : state === 'current' ? ', current step' : ''}</span></a><span class="s">${st.s}</span></li>`;
  }).join('')}</ol>`;
}

function guideAnswers() {
  const p = S.prefs;
  return `<aside class="panel summary-card stack-sm" aria-label="Your answers so far">
    <div class="kicker">Your answers</div><h2>So far</h2>
    <dl class="kv">
      <dt>Campus</dt><dd>Virginia Tech</dd>
      <dt>Budget</dt><dd class="num">${money(p.monthly_budget_per_person)} each</dd>
      <dt>Dates</dt><dd>${p.move_in_date ? `${fmtDate(p.move_in_date)} to ${fmtDate(p.move_out_date) || '?'}` : 'Not set'}</dd>
      <dt>Living</dt><dd>${p.household_size} ${p.household_size === 1 ? 'person' : 'people'}, ${p.private_bedroom_required ? 'own rooms' : 'sharing OK'}</dd>
      <dt>Travel</dt><dd>${p.travel_modes.map((m) => MODE_LABEL[m]).join(', ') || 'None'}</dd>
      <dt>Top three</dt><dd>${p.priorities.length ? p.priorities.map((x, i) => `${i + 1}. ${esc(x)}`).join('<br>') : 'Not chosen'}</dd>
    </dl>
    <p class="tiny">Shared with Explore and Preferences. Revision ${S.revision}. ${I.lock} Saved locally and synced to this backend.</p>
  </aside>`;
}

function guideStep1() {
  const p = S.prefs;
  const seg = (name, val, opts) => `<div class="seg" role="radiogroup">${opts.map(([v, l]) => `<label><input type="radio" name="g-${name}" id="g-${name}-${v}" value="${v}" ${String(val) === String(v) ? 'checked' : ''} data-gbind="${name}"><span>${l}</span></label>`).join('')}</div>`;
  const dateErr = (!!p.move_in_date !== !!p.move_out_date) || (p.move_in_date && p.move_out_date && p.move_out_date <= p.move_in_date);
  return `<div class="stack">
    <div class="kicker">01 / Your needs</div><h2 tabindex="-1" id="page-title">Start with what you can afford and who you'll live with</h2>
    <p class="lede">A few short answers. You can change any of them later, here or on Preferences.</p>
    <div class="grid-2">
      <div class="field"><label for="g-budget">Monthly budget, your share</label><div class="input-prefix"><span>$</span><input class="input num" id="g-budget" inputmode="numeric" value="${esc(p.monthly_budget_per_person)}" data-gbind="monthly_budget_per_person" data-num ${UI.guideErrors && !(p.monthly_budget_per_person >= 200 && p.monthly_budget_per_person <= 5000) ? 'aria-invalid="true"' : ''}></div>${UI.guideErrors && !(p.monthly_budget_per_person >= 200 && p.monthly_budget_per_person <= 5000) ? `<p class="err">${I.x} Enter an amount between $200 and $5,000</p>` : '<p class="hint">Rent plus required fees you can pay each month.</p>'}</div>
      <div class="field"><label for="g-campus">Campus</label><select class="input" id="g-campus" disabled><option>Virginia Tech, Blacksburg</option></select><p class="hint">The only supported campus today.</p></div>
    </div>
    <div class="vocab" aria-label="Money words, explained">
      <details><summary>Per person or whole unit?</summary><p>Per person means the price is just your bill. Whole unit means the price is for the apartment, and roommates split it. On a joint lease, each signer can owe the full amount.</p></details>
      <details><summary>Installment or monthly rent?</summary><p>Some leases charge 12 “installments” over 11.5 months. It's still 12 payments, but not one per calendar month, so the total is what matters.</p></details>
      <details><summary>Required fees and deposits</summary><p>Required fees (utility packages, trash) are part of what you'll pay every month. Deposits are usually refundable. One-time fees (application, admin) aren't.</p></details>
    </div>
    <div class="grid-2">
      <fieldset class="field"><legend class="label">People living together</legend>${seg('household_size', p.household_size, [[1, '1'], [2, '2'], [3, '3'], [4, '4']])}</fieldset>
      <fieldset class="field"><legend class="label">Bedroom</legend>${seg('private_bedroom_required', p.private_bedroom_required, [[true, 'My own'], [false, 'Sharing is OK']])}</fieldset>
    </div>
    <div class="grid-2">
      <div class="field"><label for="g-movein">Move-in <span class="opt">if you know it</span></label><input class="input" type="date" id="g-movein" value="${esc(p.move_in_date)}" data-gbind="move_in_date"></div>
      <div class="field"><label for="g-moveout">Move-out <span class="opt">if you know it</span></label><input class="input" type="date" id="g-moveout" value="${esc(p.move_out_date)}" data-gbind="move_out_date" ${dateErr ? 'aria-invalid="true"' : ''}>${dateErr ? `<p class="err">${I.x} Choose both dates, with move-out after move-in.</p>` : ''}</div>
    </div>
    <fieldset class="field"><legend class="label">How you'll get around</legend><div class="toggles">${['walk', 'transit', 'bike', 'drive'].map((m) => `<label class="toggle"><input type="checkbox" id="g-mode-${m}" value="${m}" data-gbind="travel_modes" ${p.travel_modes.includes(m) ? 'checked' : ''}><span>${modeIcon(m)}${m === 'drive' ? 'I have a car' : MODE_LABEL[m]}</span></label>`).join('')}</div>${UI.guideErrors && !p.travel_modes.length ? `<p class="err">${I.x} Choose at least one</p>` : ''}</fieldset>
    <fieldset class="field"><legend class="label">What matters most? Pick three, in order</legend>
      <div class="prio">${PRIORITY_OPTIONS.map((o) => { const i = p.priorities.indexOf(o); return `<button type="button" data-action="prio" data-v="${esc(o)}" aria-pressed="${i >= 0}" id="prio-${PRIORITY_OPTIONS.indexOf(o)}">${i >= 0 ? `<span class="rank">${i + 1}</span>` : ''}${esc(o)}</button>`; }).join('')}</div>
      <p class="hint">${p.priorities.length < 3 ? `Choose ${3 - p.priorities.length} more.` : 'Tap one to remove it.'} Priorities shape explanations; they never hide a conflict.</p>
    </fieldset>
  </div>`;
}

function guideStep2() {
  return `<div class="stack">
    <div class="kicker">02 / Explore places</div><h2 tabindex="-1" id="page-title">What should be near your home?</h2>
    <p class="lede">Explore all housing-guide options, save up to three different places and check groceries, restaurants and gas stations from property details.</p>
    <p>Operator-checked plans and guide references have different evidence levels. Confirm the exact unit, lease, fees and address before deciding.</p>
    <div class="btn-row"><a class="btn btn-primary" href="#explore">Explore housing options</a><a class="btn" href="#shortlist">Review my shortlist</a></div>
  </div>`;
}

function guideCandidates() {
  let ids = S.guide.selected_candidate_ids.filter((id) => candidate(id));
  if (!ids.length) ids = S.shortlist.length ? S.shortlist.slice(0, 3) : propertyGroups(compareAll()).map(g=>g.lead).slice(0, 3).map((r) => r.cand.id);
  return ids.slice(0, 3).map((id) => compare(candidate(id), S.prefs, S.commitments));
}

function guideStep3() {
  const rs = guideCandidates();
  const view = S.guide.view;
  return `<div class="stack">
    <div class="kicker">03 / Compare</div><h2 tabindex="-1" id="page-title">Three places to start with</h2>
    <p class="lede">${S.shortlist.length ? 'From your shortlist.' : 'The first three reviewed offers, documented fits first.'} Nobody is crowned the winner. Each card shows what's confirmed and what isn't.</p>
    <div class="btn-row"><div class="seg view-switch" role="radiogroup" aria-label="View"><label><input type="radio" name="gview" value="list" data-action="gview" ${view === 'list' ? 'checked' : ''}><span>List</span></label><label><input type="radio" name="gview" value="map" data-action="gview" ${view === 'map' ? 'checked' : ''}><span>Map</span></label></div><a class="btn btn-quiet" href="#explore">Browse all ${new Set(CANDIDATES.map(c=>c.property_id)).size} places on Explore</a></div>
    ${view === 'map' ? schematicMap(rs) : ''}
    <ul class="cand-list">${rs.map((r) => {
      const c = r.cand;
      return `<li class="cand" style="cursor:default">
        <div class="cand-top"><div><div class="cand-name">${esc(c.property_name)}</div><div class="cand-area">${esc(c.area)}${c.offer ? ' · ' + esc(c.offer.layout) : ''}</div></div>${fitChip(r.fit)}</div>
        ${priceBlock(r)}
        <div class="cand-meta">${freshness(r)}${c.guide_reference?'':demoChip()}</div>
        <details class="vocab"><summary>Why this option?</summary><div style="padding-bottom:12px" class="stack-sm">
          <ul class="check-list">${r.conflicts.map((x) => `<li><span style="color:var(--conflict)">${I.x}</span><span>${esc(x.text)}</span></li>`).join('')}${r.unknowns.map((x) => `<li><span style="color:var(--unsure)">${I.q}</span><span>${esc(x.text)}</span></li>`).join('')}${!r.conflicts.length && !r.unknowns.length ? `<li><span style="color:var(--fit)">${I.check}</span><span>Budget, bedrooms and lease check out with current sources.</span></li>` : ''}</ul>
          <p class="tiny">From the deterministic comparison, not AI. Sources: ${c.evidence.map((e) => esc(e.id)).join(', ')}. <button class="linkish" data-action="evidence" data-id="${c.id}">Open evidence</button></p>
        </div></details>
        <div class="cand-actions">${shortlistBtn(c.id)}<a class="btn btn-sm btn-quiet" href="#property-${c.id}">Full details</a></div>
      </li>`;
    }).join('')}</ul>
  </div>`;
}

function guideStep4() {
  const currentChecklistKey=JSON.stringify([S.revision,guideCandidates().map(r=>r.cand.id).slice(0,3)]);
  if (API.checklistKey!==currentChecklistKey) queueChecklist();
  if (!S.guide.checklist) { queueChecklist(); return `<div class="panel stack-sm"><h2>Before you sign</h2><p role="status">${API.checklistError ? esc(API.checklistError) : 'Loading your checklist from the backend…'}</p><button class="btn" data-action="retry-checklist">Try again</button></div>`; }
  const cl = S.guide.checklist;
  const doneN = cl.filter((i) => i.status === 'done' || i.status === 'not_applicable').length;
  return `<div class="stack">
    <div class="kicker">04 / Before you sign</div><h2 tabindex="-1" id="page-title">Before you sign anything</h2>
    <p class="lede">Questions and tasks for your places. Items marked “needs confirmation” come from facts we couldn't verify. ${doneN} of ${cl.length} handled.</p>
    ${CHECKLIST_CATEGORIES.map((cat) => {
      const its = cl.filter((i) => i.category === cat.id);
      if (!its.length) return '';
      return `<section class="cl-group" aria-labelledby="cl-${cat.id}"><h3 id="cl-${cat.id}">${cat.label}</h3>${its.map((i) => `<div class="cl-item ${i.status === 'done' ? 'done-item' : ''}">
        <div><div class="cl-title">${esc(i.title)}</div>${i.details ? `<p class="small">${esc(i.details)}</p>` : ''}
          <div class="chips" style="margin-top:6px">${i.origin === 'generic' ? '<span class="chip chip-neutral">General advice</span>' : i.origin === 'user' ? '<span class="chip chip-neutral">Added by you</span>' : '<span class="chip chip-neutral">From your comparison</span>'}${i.needs_confirmation ? flagChip('Needs confirmation') : ''}${i.evidence_ids.length ? `<button class="linkish tiny" data-action="evidence" data-id="${i.candidate_id}">${i.evidence_ids.map(esc).join(', ')}</button>` : ''}</div></div>
        <div><label class="sr" for="st-${i.id}">Status for ${esc(i.title)}</label><select class="input" id="st-${i.id}" data-cl="${i.id}" data-clf="status">${[['not_started', 'Not started'], ['in_progress', 'In progress'], ['done', 'Done'], ['not_applicable', 'Not needed']].map(([v, l]) => `<option value="${v}" ${i.status === v ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
        <div class="full"><label class="sr" for="nt-${i.id}">Notes</label><input class="input" style="min-height:40px;font-size:.9375rem" id="nt-${i.id}" placeholder="Notes" value="${esc(i.notes)}" data-cl="${i.id}" data-clf="notes"></div>
      </div>`).join('')}</section>`;
    }).join('')}
    <form class="btn-row" data-form="cl-add"><label class="sr" for="cl-new">Add your own item</label><input class="input" style="flex:1;min-width:200px" id="cl-new" placeholder="Add your own item"><select class="input" style="width:auto" id="cl-new-cat" aria-label="Category">${CHECKLIST_CATEGORIES.map((c) => `<option value="${c.id}">${c.label}</option>`).join('')}</select><button class="btn" type="submit">Add</button></form>
    <section class="empty" aria-labelledby="h-wish"><h3 id="h-wish">What students wish they knew</h3><p>No authorized resident feedback exists for these places yet, so this stays empty. Nothing here is written from marketing copy or guessed.</p></section>
    <div class="panel stack-sm"><h3>Save your first-renter brief</h3><p class="small">Your answers, these places, this checklist and every open question, frozen as of now.</p><div class="btn-row"><button class="btn btn-primary" data-action="save-brief" data-origin="guide">Save brief</button></div></div>
  </div>`;
}

function viewGuide(step) {
  const n = Math.min(4, Math.max(1, step || S.guide.current_step));
  if (S.guide.current_step !== n || !S.guide.started) { S.guide.current_step = n; S.guide.started = true; S.guide.updated_at = new Date().toISOString(); save(); }
  const body = [null, guideStep1, guideStep2, guideStep3, guideStep4][n]();
  return `<!--full-->
  <section class="band"><div class="wrap" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:20px 60px;align-items:end">
    <div><div class="kicker">DormToDoor · step ${n} of 4</div><p style="font-family:var(--display);font-size:clamp(2.6rem,5vw,4.8rem);font-weight:680;letter-spacing:-.06em;line-height:1.05;color:var(--on-dark);margin-top:18px">From dorm to door.</p></div>
    <p style="font-size:1rem;line-height:1.7;max-width:390px">A guide for first-time renters. Everything you enter here is shared with Explore, and nothing needs an account.</p>
  </div></section>
  <div class="wrap">${stepper(n)}</div>
  <div class="wrap page">
  <div class="guide-grid">
    <div class="guide-main">${body}
      <div class="guide-nav">
        <div class="btn-row">${n > 1 ? `<a class="btn" href="#guide-${n - 1}" data-action="guide-back">Back</a>` : ''}<button class="btn btn-quiet" data-action="guide-exit">Save and exit</button><button class="btn btn-quiet" data-action="guide-restart">Restart</button></div>
        ${n < 4 ? `<button class="btn btn-primary" data-action="guide-next" data-step="${n}">Next: ${GUIDE_STEPS[n].t}</button>` : '<button class="btn btn-primary" data-action="guide-finish">Finish</button>'}
      </div>
    </div>
    ${guideAnswers()}
  </div></div>`;
}
