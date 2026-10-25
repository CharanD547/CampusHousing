/* ---------- Home ---------- */
function viewHome() {
  const g = S.guide;
  return `<!--full-->
  <section class="hero" aria-labelledby="page-title">
    <div class="hero-image" role="img" aria-label="Illustrative photograph of brick apartment buildings and trees at sunset"></div>
    <div class="hero-content wrap"><div class="hero-copy">
      <div class="kicker">Student housing, without the guesswork</div>
      <h1 tabindex="-1" id="page-title">Find your place. <span class="soft">Know the trade-offs.</span></h1>
      <p class="lede">A home is more than its listing. Compare housing costs, roommates, nearby essentials and the questions to ask before signing.</p>
      <div class="hero-location"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.8"/></svg>Made for Virginia Tech students · Blacksburg, VA</div>
    </div></div>
  </section>

  <div class="search-wrap wrap">
    <form class="search-shell" role="search" aria-label="Start a housing search" data-form="home-search">
      <div class="search-field"><span class="search-label">Where are you studying?</span><div class="search-value"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.8"/></svg>Virginia Tech</div><div class="sub">Blacksburg, Virginia · the only supported campus today</div></div>
      <div class="search-field"><label class="search-label" for="home-budget">Monthly budget per person</label><input id="home-budget" inputmode="numeric" placeholder="e.g. $1,100" value="${esc(S.prefs.monthly_budget_per_person)}"><div class="sub">Your share of rent plus required fees</div></div>
      <button class="search-cta" type="submit">Explore your options <span class="arrow" aria-hidden="true">↗</span></button>
    </form>
    <p class="search-note">Operator asking prices and housing-guide references · missing costs stay visible</p>
  </div>

  <section class="section wrap" aria-labelledby="h-why">
    <div class="section-top"><div class="kicker">Beyond the listing</div><div class="index">01 — 03 / What we check</div></div>
    <div class="features-intro"><h2 id="h-why">The listing shows a place. We help you see the decision.</h2><p>The cheapest number isn't always the lowest cost, and a short distance doesn't always mean an easy morning.</p></div>
    <div class="feature-row">
      <article class="feature-item"><div class="feature-number">01 / The money</div><h3>See beyond base rent.</h3><p>“$989 per person per installment” stays exactly that. Required fees, deposits and one-time charges are kept apart, and a partial total is never called all-in.</p></article>
      <article class="feature-item"><div class="feature-number">02 / The everyday</div><h3>Explore life nearby.</h3><p>Look for restaurants, groceries and gas stations around a property. Open directions for the way you travel.</p></article>
      <article class="feature-item"><div class="feature-number">03 / The decision</div><h3>Know what you don't know.</h3><p>Too few bedrooms or a joint lease you didn't want shows up first. A cheaper split never hides it, and missing facts stay visible.</p></article>
    </div>
    <div class="demo-board">
      <div><div class="kicker">More places to consider</div><h2 style="font-size:clamp(2.2rem,3.6vw,3.4rem);margin-top:22px">Explore the wider housing market.</h2><p class="lede">Browse ${new Set(CANDIDATES.map(c=>c.property_id)).size} communities and neighborhood references from the housing guide. Checked operator prices and unverified guide figures are labeled separately.</p><div class="btn-row" style="margin-top:28px"><a class="btn btn-primary" href="#explore">Browse every housing option</a><a class="btn btn-quiet" href="#property-${CANDIDATES[0].id}">See costs and nearby places</a></div></div>
      <div class="panel stack"><h3>Compare what matters</h3><p>Whole-unit or per-person pricing. Private rooms or sharing. Your own lease or a joint responsibility. Fees, deposits and questions that still need an answer.</p></div>
    </div>
  </section>

  <section class="paths on-dark" aria-labelledby="h-paths"><div class="wrap paths-grid">
    <div><div class="kicker">Your search, your way</div><h2 id="h-paths">There's more than one way to find home.</h2><p class="sub">Go straight into the details, or start with a guided plan. Both begin with your needs, and both share everything you enter.</p></div>
    <div class="path-list">
      <a class="path" href="#explore"><span class="path-num">01</span><span><span class="path-name">I know what I want.</span><span class="path-desc">Browse housing options checked against your budget, household and lease needs, with source limitations visible.</span></span><span class="path-arrow" aria-hidden="true">↗</span></a>
      <a class="path" href="#guide-${g.started ? g.current_step : 1}"><span class="path-num">02</span><span><span class="path-name">${g.started ? `Pick up at step ${g.current_step}.` : 'Help me figure it out.'}</span><span class="path-desc">DormToDoor: a four-step guide for first-time renters, from your needs to a before-you-sign checklist. No account needed.</span></span><span class="path-arrow" aria-hidden="true">↗</span></a>
      <a class="path" href="#compare"><span class="path-num">03</span><span><span class="path-name">Compare my shortlist.</span><span class="path-desc">${S.shortlist.length} of 3 saved. See cost basis, room constraints, sources and open questions side by side.</span></span><span class="path-arrow" aria-hidden="true">↗</span></a>
    </div>
  </div></section>

  <section class="section wrap faq" aria-labelledby="h-faq"><div class="faq-grid">
    <div class="faq-title"><div class="kicker">Good questions first</div><h2 id="h-faq">Worth asking.</h2><p>Renting is a big decision. Here's what should be clear from the start.</p></div>
    <div class="faq-list">
      <details class="faq-item"><summary>What makes Roomwise different?<span class="plus" aria-hidden="true">+</span></summary><div class="faq-answer">It compares the price basis, household requirements, mandatory charges and what still needs confirmation. Nearby searches help you explore daily essentials around a property.</div></details>
      <details class="faq-item"><summary>What is DormToDoor?<span class="plus" aria-hidden="true">+</span></summary><div class="faq-answer">An optional four-step guide: your needs, exploring housing options, comparing up to three places, and a before-you-sign checklist.</div></details>
      <details class="faq-item"><summary>Which campuses are supported?<span class="plus" aria-hidden="true">+</span></summary><div class="faq-answer">Virginia Tech in Blacksburg. Another campus is added only once its housing data, class buildings and routes have been reviewed, not just by adding a name to a list.</div></details>
      <details class="faq-item"><summary>Are prices and nearby places live?<span class="plus" aria-hidden="true">+</span></summary><div class="faq-answer">Operator prices have review dates. Guide figures are unverified references. Nearby searches use Google Places on demand; current unit availability and complete costs require operator confirmation.</div></details>
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
        <h2 id="h-travel">Getting around</h2>
        <fieldset class="field"><legend class="label">Ways you can travel</legend>
          <div class="toggles">${['walk', 'transit', 'bike', 'drive'].map((m) => `<label class="toggle"><input type="checkbox" id="f-mode-${m}" value="${m}" data-bind="travel_modes" ${d.travel_modes.includes(m) ? 'checked' : ''}><span>${modeIcon(m)}${m === 'drive' ? 'I have a car' : MODE_LABEL[m]}</span></label>`).join('')}</div>
          <p class="hint">Use these preferences when exploring nearby essentials and opening directions.</p>
          ${errLine('f-mode-walk')}
        </fieldset>
      </section>
    </div>

    <aside class="sheet summary-card stack-sm" aria-label="Your inputs">
      <div class="kicker">Your inputs</div>
      <dl class="kv">
        <dt>Budget</dt><dd class="num">${money(Number(d.monthly_budget_per_person) || 0)} per person</dd>
        <dt>Household</dt><dd>${d.household_size}, ${String(d.private_bedroom_required) === 'true' ? 'private rooms' : 'sharing OK'}</dd>
        <dt>Lease</dt><dd>${d.individual_lease_required ? 'My own lease only' : 'Joint or individual'}</dd>
        <dt>Travel</dt><dd>${d.travel_modes.map((m) => MODE_LABEL[m]).join(', ') || 'None chosen'}</dd>
      </dl>
      <p class="tiny">Revision ${S.revision}</p>
      ${dirty ? asyncNotice('unsure', 'Unsaved changes', `Applying creates revision ${S.revision + 1}. Any AI explanation for revision ${S.revision} will be marked out of date. Saved briefs don't change.`) : asyncNotice('ok', 'Results are up to date', `Comparing with revision ${S.revision}.`)}
      <button class="btn btn-primary" data-action="prefs-apply" ${dirty ? '' : 'disabled'}>Apply and update results</button>
      <button class="btn" data-action="prefs-discard" ${dirty ? '' : 'disabled'}>Discard changes</button>
      <p class="tiny">${I.lock} Drafts are cached in this browser and synced to this local backend. Check the save status below.</p>
    </aside>
  </div>`;
}
