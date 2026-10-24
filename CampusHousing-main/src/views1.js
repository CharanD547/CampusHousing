/* ---------- Home ---------- */
function viewHome() {
  const r = compare(CANDIDATES[0], S.prefs, S.commitments);
  const sample = S.commitments.some((c) => c.sample);
  const g = S.guide;
  return `<!--full-->
  <section class="hero" aria-labelledby="page-title">
    <div class="hero-image" role="img" aria-label="Illustrative photograph of brick apartment buildings and trees at sunset"></div>
    <div class="hero-content wrap"><div class="hero-copy">
      <div class="kicker">Student housing, without the guesswork</div>
      <h1 tabindex="-1" id="page-title">Find your place. <span class="soft">Know the trade-offs.</span></h1>
      <p class="lede">A home is more than its listing. Put the cost, the commute to every class, and the questions you haven't thought to ask in one place.</p>
      <div class="hero-location"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.8"/></svg>Made for Virginia Tech students · Blacksburg, VA</div>
    </div></div>
  </section>

  <div class="search-wrap wrap">
    <form class="search-shell" role="search" aria-label="Start a housing search" data-form="home-search">
      <div class="search-field"><span class="search-label">Where are you studying?</span><div class="search-value"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.8"/></svg>Virginia Tech</div><div class="sub">Blacksburg, Virginia · the only supported campus today</div></div>
      <div class="search-field"><label class="search-label" for="home-budget">Monthly budget per person</label><input id="home-budget" inputmode="numeric" placeholder="e.g. $1,100" value="${esc(S.prefs.monthly_budget_per_person)}"><div class="sub">Your share of rent plus required fees</div></div>
      <button class="search-cta" type="submit">Explore your options <span class="arrow" aria-hidden="true">↗</span></button>
    </form>
    <p class="search-note">Source-backed asking prices · missing costs and route coverage stay visible</p>
  </div>

  <section class="section wrap" aria-labelledby="h-why">
    <div class="section-top"><div class="kicker">Beyond the listing</div><div class="index">01 — 03 / What we check</div></div>
    <div class="features-intro"><h2 id="h-why">The listing shows a place. We help you see the decision.</h2><p>The cheapest number isn't always the lowest cost, and a short distance doesn't always mean an easy morning.</p></div>
    <div class="feature-row">
      <article class="feature-item"><div class="feature-number">01 / The money</div><h3>See beyond base rent.</h3><p>“$989 per person per installment” stays exactly that. Required fees, deposits and one-time charges are kept apart, and a partial total is never called all-in.</p></article>
      <article class="feature-item"><div class="feature-number">02 / The everyday</div><h3>Make the commute count.</h3><p>Every class building gets its own route. If only one of two classes has a supported route, you see 1 of 2, not a pass.</p></article>
      <article class="feature-item"><div class="feature-number">03 / The decision</div><h3>Know what you don't know.</h3><p>Too few bedrooms or a joint lease you didn't want shows up first. A cheaper split never hides it, and missing facts stay visible.</p></article>
    </div>
    <div class="demo-board">
      <div><div class="kicker">From one place to your week</div><h2 style="font-size:clamp(2.2rem,3.6vw,3.4rem);margin-top:22px">Every class, routed on its own.</h2><p class="lede">${sample ? 'This uses the sample schedule.' : 'This uses your schedule.'} Building locations and prices come from the backend. Route times appear only when a real provider supports them.</p><div class="btn-row" style="margin-top:28px"><a class="btn btn-primary" href="#schedule">Add my classes</a><a class="btn btn-quiet" href="#property-${CANDIDATES[0].id}">See the full breakdown</a></div></div>
      ${commuteSign(r, { title: 'From ' + CANDIDATES[0].property_name })}
    </div>
  </section>

  <section class="paths on-dark" aria-labelledby="h-paths"><div class="wrap paths-grid">
    <div><div class="kicker">Your search, your way</div><h2 id="h-paths">There's more than one way to find home.</h2><p class="sub">Go straight into the details, or start with a guided plan. Both begin with your needs, and both share everything you enter.</p></div>
    <div class="path-list">
      <a class="path" href="#explore"><span class="path-num">01</span><span><span class="path-name">I know what I want.</span><span class="path-desc">Browse ${CANDIDATES.length} reviewed places on a list and map, checked against your budget, roommates and classes.</span></span><span class="path-arrow" aria-hidden="true">↗</span></a>
      <a class="path" href="#guide-${g.started ? g.current_step : 1}"><span class="path-num">02</span><span><span class="path-name">${g.started ? `Pick up at step ${g.current_step}.` : 'Help me figure it out.'}</span><span class="path-desc">DormToDoor: a four-step guide for first-time renters, from your needs to a before-you-sign checklist. No account needed.</span></span><span class="path-arrow" aria-hidden="true">↗</span></a>
      <a class="path" href="#compare"><span class="path-num">03</span><span><span class="path-name">Compare my shortlist.</span><span class="path-desc">${S.shortlist.length} of 3 saved. See cost basis, room constraints, commute coverage and open questions side by side.</span></span><span class="path-arrow" aria-hidden="true">↗</span></a>
    </div>
  </div></section>

  <section class="section wrap faq" aria-labelledby="h-faq"><div class="faq-grid">
    <div class="faq-title"><div class="kicker">Good questions first</div><h2 id="h-faq">Worth asking.</h2><p>Renting is a big decision. Here's what should be clear from the start.</p></div>
    <div class="faq-list">
      <details class="faq-item"><summary>What makes Roomwise different?<span class="plus" aria-hidden="true">+</span></summary><div class="faq-answer">It compares more than the advertised rent: the price basis, roommate requirements, a commute to each class, and what still needs confirmation. Missing information stays visible instead of being guessed.</div></details>
      <details class="faq-item"><summary>What is DormToDoor?<span class="plus" aria-hidden="true">+</span></summary><div class="faq-answer">An optional four-step guide for first-time renters: your needs, your campus routine, comparing up to three places, and a before-you-sign checklist you can save.</div></details>
      <details class="faq-item"><summary>Which campuses are supported?<span class="plus" aria-hidden="true">+</span></summary><div class="faq-answer">Virginia Tech in Blacksburg. Another campus is added only once its housing data, class buildings and routes have been reviewed, not just by adding a name to a list.</div></details>
      <details class="faq-item"><summary>Are prices and commutes live?<span class="plus" aria-hidden="true">+</span></summary><div class="faq-answer">Prices are source-reviewed asking figures with their original billing basis. Routes and Gemma explanations require configured providers; unavailable services never produce invented results.</div></details>
      <details class="faq-item"><summary>Where is my information kept?<span class="plus" aria-hidden="true">+</span></summary><div class="faq-answer">Drafts are cached in this browser and synced to the local Roomwise backend. Decision briefs are immutable server records. This instance is intended for one local operator.</div></details>
    </div>
  </div></section>`;
}

/* ---------- Preferences ---------- */
function prefErrors(d) {
  const e = [];
  const b = Number(d.monthly_budget_per_person);
  if (!d.monthly_budget_per_person && d.monthly_budget_per_person !== 0) e.push({ field: 'f-budget', msg: 'Enter a monthly budget per person' });
  else if (!(b >= 200 && b <= 5000)) e.push({ field: 'f-budget', msg: 'Budget must be between $200 and $5,000 per person' });
  if (!d.travel_modes.length) e.push({ field: 'f-mode-walk', msg: 'Choose at least one way to travel' });
  if (!!d.move_in_date !== !!d.move_out_date) e.push({field:'f-moveout',msg:'Choose both housing dates, or leave both empty.'});
  if (d.move_in_date && d.move_out_date && d.move_out_date <= d.move_in_date) e.push({ field: 'f-moveout', msg: `Move-out must be after move-in (${fmtDate(d.move_in_date)})` });
  return e;
}

function viewPreferences() {
  if (!S.draft) S.draft = clone(S.prefs);
  const d = S.draft;
  const errs = prefErrors(d);
  const show = UI.errorsShown && errs.length;
  const fe = (id) => (UI.errorsShown ? errs.find((x) => x.field === id) : null);
  const dirty = JSON.stringify(d) !== JSON.stringify(S.prefs);
  const share = 2050 / Math.max(1, Number(d.household_size));
  const seg = (name, val, opts) => `<div class="seg" role="radiogroup">${opts.map(([v, l]) => `<label><input type="radio" name="${name}" id="f-${name}-${v}" value="${v}" ${String(val) === String(v) ? 'checked' : ''} data-bind="${name}"><span>${l}</span></label>`).join('')}</div>`;
  const errLine = (id) => fe(id) ? `<p class="err" id="${id}-err">${I.x} ${esc(fe(id).msg)}</p>` : '';

  return `
  <div class="page-head"><div class="kicker">Preferences</div><h1 tabindex="-1" id="page-title">What you need from a home</h1><p>Every place is checked against these. Change anything and press Apply when you're ready.</p></div>
  ${show ? `<div class="error-summary" role="alert" tabindex="-1" id="err-summary"><h2>${plural(errs.length, 'thing')} to fix before results can update</h2><ul>${errs.map((x) => `<li><a href="#${x.field}" data-action="focus-field" data-field="${x.field}">${esc(x.msg)}</a></li>`).join('')}</ul></div>` : ''}
  <div class="two-col">
    <div class="stack">
      <section class="panel stack" aria-labelledby="h-budget">
        <h2 id="h-budget">Budget</h2>
        <div class="grid-2">
          <div class="field">
            <label for="f-budget">Monthly budget per person</label>
            <div class="input-prefix"><span>$</span><input class="input num" id="f-budget" inputmode="numeric" value="${esc(d.monthly_budget_per_person)}" data-bind="monthly_budget_per_person" data-num aria-describedby="f-budget-hint" ${fe('f-budget') ? 'aria-invalid="true"' : ''}></div>
            <p class="hint" id="f-budget-hint">Your share of rent plus required fees, each month or installment.</p>
            ${errLine('f-budget')}
          </div>
          <div class="field">
            <label for="f-campus">Campus</label>
            <select class="input" id="f-campus" data-bind="campus_id"><option value="vt">Virginia Tech, Blacksburg</option></select>
            <p class="hint">Only verified campuses are listed. Virginia Tech is the only one today.</p>
          </div>
        </div>
        <div class="grid-2">
          <div class="well"><b>Per person</b><p class="small">“$989 per person” is your own bill, usually on an individual lease. Nobody else's missed payment is on you.</p></div>
          <div class="well"><b>Whole unit</b><p class="small">“$2,050 for the unit” split ${esc(d.household_size)} ways is about ${money(share)} each. On a joint lease every signer can owe the full ${money(2050)}.</p></div>
        </div>
      </section>

      <section class="panel stack" aria-labelledby="h-house">
        <h2 id="h-house">Household</h2>
        <div class="grid-2">
          <fieldset class="field"><legend class="label">People living together</legend>${seg('household_size', d.household_size, [[1, '1'], [2, '2'], [3, '3'], [4, '4']])}</fieldset>
          <fieldset class="field"><legend class="label">Bedroom</legend>${seg('private_bedroom_required', d.private_bedroom_required, [[true, 'Private for each'], [false, 'Sharing is OK']])}</fieldset>
        </div>
        <label class="switch" for="f-indiv"><span><b>Require my own lease</b><span class="small" style="display:block">Only show places where each person signs for their own room.</span></span><input type="checkbox" id="f-indiv" data-bind="individual_lease_required" ${d.individual_lease_required ? 'checked' : ''}></label>
        <div class="grid-2">
          <div class="field"><label for="f-movein">Move-in <span class="opt">if you know it</span></label><input class="input" type="date" id="f-movein" value="${esc(d.move_in_date)}" data-bind="move_in_date"></div>
          <div class="field"><label for="f-moveout">Move-out <span class="opt">if you know it</span></label><input class="input" type="date" id="f-moveout" value="${esc(d.move_out_date)}" data-bind="move_out_date" ${fe('f-moveout') ? 'aria-invalid="true" aria-describedby="f-moveout-err"' : ''}>${errLine('f-moveout')}</div>
        </div>
      </section>

      <section class="panel stack" aria-labelledby="h-travel">
        <h2 id="h-travel">Getting to class</h2>
        <fieldset class="field"><legend class="label">Ways you can travel</legend>
          <div class="toggles">${['walk', 'transit', 'bike', 'drive'].map((m) => `<label class="toggle"><input type="checkbox" id="f-mode-${m}" value="${m}" data-bind="travel_modes" ${d.travel_modes.includes(m) ? 'checked' : ''}><span>${modeIcon(m)}${m === 'drive' ? 'I have a car' : MODE_LABEL[m]}</span></label>`).join('')}</div>
          <p class="hint">Select each mode you want checked. A mode only has an estimate when the configured provider supports it for your selected date.</p>
          ${errLine('f-mode-walk')}
        </fieldset>
        <div class="grid-2">
          <div class="field"><label for="f-max">Longest commute you'll accept</label><div class="range-row"><input type="range" id="f-max" min="5" max="60" step="5" value="${esc(d.max_commute_minutes)}" data-bind="max_commute_minutes" data-num aria-valuetext="${d.max_commute_minutes} minutes"><span class="range-val num" id="f-max-out">${esc(d.max_commute_minutes)} min</span></div></div>
          <div class="field"><label for="f-buffer">Arrive early by</label><select class="input" id="f-buffer" data-bind="arrival_buffer_minutes" data-num>${[0, 5, 10, 15, 20].map((v) => `<option value="${v}" ${Number(d.arrival_buffer_minutes) === v ? 'selected' : ''}>${v ? v + ' minutes' : 'No buffer'}</option>`).join('')}</select><p class="hint">You can change this per class on the Schedule page.</p></div>
        </div>
      </section>
    </div>

    <aside class="sheet summary-card stack-sm" aria-label="Your inputs">
      <div class="kicker">Your inputs</div>
      <dl class="kv">
        <dt>Budget</dt><dd class="num">${money(Number(d.monthly_budget_per_person) || 0)} per person</dd>
        <dt>Household</dt><dd>${d.household_size}, ${String(d.private_bedroom_required) === 'true' ? 'private rooms' : 'sharing OK'}</dd>
        <dt>Lease</dt><dd>${d.individual_lease_required ? 'My own lease only' : 'Joint or individual'}</dd>
        <dt>Travel</dt><dd>${d.travel_modes.map((m) => MODE_LABEL[m]).join(', ') || 'None chosen'}, up to ${d.max_commute_minutes} min</dd>
        <dt>Classes</dt><dd>${S.commitments.length} · <a href="#schedule">edit</a></dd>
      </dl>
      <p class="tiny">Revision ${S.revision}</p>
      ${dirty ? asyncNotice('unsure', 'Unsaved changes', `Applying creates revision ${S.revision + 1}. Any AI explanation for revision ${S.revision} will be marked out of date. Saved briefs don't change.`) : asyncNotice('ok', 'Results are up to date', `Comparing with revision ${S.revision}.`)}
      <button class="btn btn-primary" data-action="prefs-apply" ${dirty ? '' : 'disabled'}>Apply and update results</button>
      <button class="btn" data-action="prefs-discard" ${dirty ? '' : 'disabled'}>Discard changes</button>
      <p class="tiny">${I.lock} Drafts are cached in this browser and synced to this local backend. Check the save status below.</p>
    </aside>
  </div>`;
}

/* ---------- Schedule ---------- */
function commitmentEditor(e) {
  const isNew = e.id === 'new';
  return `<div class="stop-edit" role="group" aria-label="${isNew ? 'New class' : 'Edit class'}">
    <div class="grid-2">
      <div class="field"><label for="e-bld">Building</label>
        <select class="input" id="e-bld" data-edit="building_id"><option value="">Choose a verified building</option>${BUILDINGS.map((b) => `<option value="${b.id}" ${e.building_id === b.id ? 'selected' : ''}>${esc(b.label)}</option>`).join('')}</select>
        <p class="hint">Not listed? Unverified buildings can't be routed. Pick the closest listed one only if it's truly where you'll be.</p>
        ${UI.editErr?.building ? `<p class="err">${I.x} Choose a building</p>` : ''}
      </div>
      <div class="field"><label for="e-time">Arrive by <span class="opt">local time</span></label><input class="input" type="time" id="e-time" value="${esc(e.arrival_time_local)}" data-edit="arrival_time_local">${UI.editErr?.time ? `<p class="err">${I.x} Enter an arrival time</p>` : ''}</div>
    </div>
    <fieldset class="field"><legend class="label">Days</legend><div class="toggles">${DAYS.map(([v, l]) => `<label class="toggle day"><input type="checkbox" id="e-day-${v}" value="${v}" data-edit="weekdays" ${e.weekdays.includes(v) ? 'checked' : ''}><span>${l}</span></label>`).join('')}</div>${UI.editErr?.days ? `<p class="err">${I.x} Choose at least one day</p>` : ''}</fieldset>
    <div class="field" style="max-width:280px"><label for="e-buf">Arrive early by</label><select class="input" id="e-buf" data-edit="arrival_buffer_minutes"><option value="">Use my default (${S.prefs.arrival_buffer_minutes} min)</option>${[0, 5, 10, 15, 20].map((v) => `<option value="${v}" ${e.arrival_buffer_minutes === v ? 'selected' : ''}>${v} minutes</option>`).join('')}</select></div>
    <div class="btn-row"><button class="btn btn-primary" data-action="commit-save">${isNew ? 'Add class' : 'Save class'}</button><button class="btn btn-quiet" data-action="commit-cancel">Cancel</button></div>
  </div>`;
}

function scheduleBuilder() {
  const cs = S.commitments;
  const hasSample = cs.some((c) => c.sample);
  const e = UI.editing;
  const items = cs.map((c) => {
    if (e && e.id === c.id) return `<li class="stop"><span class="stop-dot" aria-hidden="true"></span><div class="stop-body">${commitmentEditor(e)}</div></li>`;
    const b = building(c.building_id);
    const buf = c.arrival_buffer_minutes ?? S.prefs.arrival_buffer_minutes;
    return `<li class="stop"><span class="stop-dot" aria-hidden="true"></span><div class="stop-body"><div class="stop-card">
      <div><h3>${esc(b.label)}${c.sample ? '<span class="chip chip-demo sample-tag">Sample</span>' : ''}</h3>
      <p class="when"><b>${c.weekdays.map(dayLabel).join(', ')}</b> · arrive by <b class="num">${fmtTime(c.arrival_time_local)}</b> · ${buf} min early${c.arrival_buffer_minutes == null ? ' (default)' : ''}</p>
      <p class="tiny">Official GIS location · <a href="${esc(b.source)}" target="_blank" rel="noopener noreferrer">VT source</a></p></div>
      <div class="btn-row"><button class="btn btn-sm" data-action="commit-edit" data-id="${c.id}" aria-label="Edit ${esc(b.label)}">Edit</button><button class="btn btn-sm btn-quiet" data-action="commit-delete" data-id="${c.id}" aria-label="Remove ${esc(b.label)}">Remove</button></div>
    </div></div></li>`;
  }).join('');
  const adding = e && e.id === 'new' ? `<li class="stop"><span class="stop-dot" aria-hidden="true"></span><div class="stop-body">${commitmentEditor(e)}</div></li>` : '';
  return `
    ${hasSample ? asyncNotice('unsure', 'This is a sample schedule', 'Two example classes so you can see how routing works. Replace them with your own.', '<div class="btn-row" style="margin-top:10px"><button class="btn btn-sm" data-action="sample-clear">Clear sample</button></div>') : ''}
    <ol class="route-line" aria-label="Your weekly classes">
      <li class="stop"><span class="stop-dot home" aria-hidden="true"></span><div class="stop-body"><p style="padding-top:8px"><b>Your home</b> <span class="small">· each place on Explore is routed from here</span></p></div></li>
      ${items}${adding}
    </ol>
    ${!cs.length && !adding ? `<div class="empty"><h3>No classes yet</h3><p>Add the buildings you go to each week. Commutes stay unchecked until you do.</p><div class="btn-row"><button class="btn btn-primary" data-action="commit-new">Add a class</button><button class="btn" data-action="sample-load">Use the sample schedule</button></div></div>` : ''}
    ${cs.length && !e ? `<div class="btn-row">${cs.length < 10 ? '<button class="btn btn-primary" data-action="commit-new">Add a class</button>' : '<p class="small">That\'s the limit of 10 classes. Combine repeating meetings into one entry.</p>'}${!hasSample ? '<button class="btn btn-quiet" data-action="sample-load">Replace with sample</button>' : ''}</div>` : ''}`;
}

function routingDisclosure() {
  return `<div class="panel stack-sm"><h2>Which date routes use</h2>
  <label for="routing-date">Representative route date</label><input class="input" type="date" id="routing-date" value="${esc(S.route_date)}">
  <label for="routing-scope">Analysis scope</label><select class="input" id="routing-scope"><option value="single_date" ${S.routing_scope!=='representative_week'?'selected':''}>Selected date only</option><option value="representative_week" ${S.routing_scope==='representative_week'?'selected':''}>Every class meeting in this week</option></select>
  <p class="small">Weekly analysis uses Monday–Sunday of the selected date and counts each scheduled meeting separately. Missing journeys remain unavailable. Google Routes requires a separate enabled credential; Maps and Places keys do not establish commute coverage. The imported BT feed covers only October 1–31, 2026.</p>
  <p class="tiny">Building points come from official VT GIS. Entrances, classroom access and indoor walking are unverified.</p></div>`;
}

function viewSchedule() {
  return `
  <div class="page-head"><div class="kicker">Campus routine</div><h1 tabindex="-1" id="page-title">Your week on campus</h1><p>Add the buildings you need to reach and when. Each one gets its own route from every place you look at.</p></div>
  <div class="two-col">
    <div class="stack">${scheduleBuilder()}</div>
    <div class="stack side">${routingDisclosure()}
      <div class="panel stack-sm"><h2>Revision ${S.revision}</h2><p class="small">Adding, editing or removing a class creates a new revision and refreshes every comparison. Saved briefs keep the schedule they were saved with.</p><a class="btn" href="#explore">See commutes on Explore</a></div>
    </div>
  </div>`;
}
