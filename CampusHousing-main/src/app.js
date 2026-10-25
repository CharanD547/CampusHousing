/* ---------- shell + router ---------- */
const NAV = [['explore', 'Explore'],['directory','Housing guide'], ['preferences', 'Preferences'], ['compare', 'Compare'], ['shortlist', 'Shortlist'],['assistant','Assistant'],['data','Data']];

function route() {
  const h = (location.hash || '#home').slice(1);
  if (h.startsWith('property-')) return { name: 'property', id: h.slice(9), nav: 'explore' };
  if (h.startsWith('brief-')) return { name: 'brief', id: h.slice(6), nav: 'shortlist' };
  if (h.startsWith('guide')) return { name: 'guide', step: Number(h.split('-')[1]) || 0, nav: 'guide' };
  if(h==='schedule')return {name:'explore',nav:'explore'};
  const known = ['home', 'explore','directory', 'preferences', 'compare', 'shortlist','assistant','data'];
  return { name: known.includes(h) ? h : 'home', nav: known.includes(h) ? h : 'home' };
}

function renderNav(rt) {
  return NAV.map(([k, l]) => `<a href="#${k}" ${rt.nav === k ? 'aria-current="page"' : ''}>${l}${k === 'shortlist' ? `<span class="count num" aria-label="${S.shortlist.length} of 3">(${S.shortlist.length}/3)</span>` : ''}</a>`).join('');
}

function demoPanel() {
  const t = (k, l) => `<label class="switch" for="sim-${k}"><span>${l}</span><input type="checkbox" id="sim-${k}" data-sim="${k}" ${S.sim[k] ? 'checked' : ''}></label>`;
  return `<div class="demo-panel" role="dialog" aria-label="Demo states"><b>Try failure states</b><p class="tiny">Your inputs and shortlist survive every one of these.</p>${t('mapFails', 'Map fails to load')}${t('aiFails', 'AI service unavailable')}${t('offline', 'Network offline')}${t('emptyInventory', 'Empty collection')}<button class="btn btn-sm btn-quiet" data-action="reset-all">Reset demo to start</button></div>`;
}

function render() {
  if (!API.ready) return;
  const rt = route();
  const focus = document.activeElement && document.activeElement.id ? { id: document.activeElement.id, s: document.activeElement.selectionStart, e: document.activeElement.selectionEnd } : null;
  const views = { home: viewHome, explore: viewExplore, directory:viewHousingDirectory, preferences: viewPreferences, compare: viewCompare, shortlist: viewShortlist, assistant:viewAssistant, data:viewData, property: () => viewProperty(rt.id), brief: () => viewBrief(rt.id), guide: () => viewGuide(rt.step) };
  document.getElementById('nav').innerHTML = renderNav(rt);
  document.getElementById('nav').classList.toggle('open', UI.menu);
  document.getElementById('menu-btn').setAttribute('aria-expanded', UI.menu);
  const te = document.getElementById('top-end'); te.href = `#guide-${S.guide.started ? S.guide.current_step : 1}`; te.textContent = S.guide.started ? `Resume DormToDoor ↗` : 'Start DormToDoor ↗'; te.toggleAttribute('aria-current', rt.nav === 'guide');
  document.getElementById('offline').hidden = !S.sim.offline;
  const html = views[rt.name]();
  document.getElementById('main').innerHTML = html.startsWith('<!--full-->') ? html : `<div class="wrap page">${html}</div>`;
  document.getElementById('overlay').innerHTML = (UI.drawer ? evidenceDrawer(UI.drawer) : '') + (UI.dialog ? dialogView(UI.dialog) : '');
  document.getElementById('demo').innerHTML = UI.demo ? demoPanel() : '';
  document.getElementById('demo-btn').setAttribute('aria-expanded', UI.demo);
  document.getElementById('toast').innerHTML = UI.toast ? `<div class="toast" role="status">${esc(UI.toast)}</div>` : '';
  document.getElementById('store-note').textContent = workspaceMessage();
  renderConnectionStatus();
  hydrateGoogleMaps();
  if (focus) {
    const el = document.getElementById(focus.id);
    if (el) { el.focus({ preventScroll: true }); try { if (focus.s != null && el.setSelectionRange) el.setSelectionRange(focus.s, focus.e); } catch (e) {} }
  }
}

function dialogView(d) {
  if (d === 'restart') return `<div class="dialog-scrim"><div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="dlg-t" aria-describedby="dlg-d"><h2 id="dlg-t">Restart DormToDoor?</h2><p id="dlg-d">This clears your guide progress and checklist. Your needs, shortlist and ${plural(S.briefs.length, 'saved brief')} stay as they are.</p><div class="btn-row"><button class="btn btn-danger" data-action="guide-restart-confirm" id="dlg-ok">Restart guide</button><button class="btn" data-action="dialog-close">Keep my progress</button></div></div></div>`;
  return '';
}

let toastTimer;
function toast(msg) { UI.toast = msg; render(); clearTimeout(toastTimer); toastTimer = setTimeout(() => { UI.toast = null; render(); }, 3200); }

function go(hash) { if (location.hash === hash) render(); else location.hash = hash; }

function bump() { S.revision++; save(); queueComparison(); }

/* ---------- events ---------- */
document.addEventListener('click', async (ev) => {
  const t = ev.target.closest('[data-action]');
  if (!t) { if (UI.demo && !ev.target.closest('#demo, #demo-btn')) { UI.demo = false; render(); } return; }
  if (t.tagName === 'LI' && ev.target.closest('a[href], button, input, select, summary')) return;
  const a = t.dataset.action, id = t.dataset.id;
  switch (a) {
    case 'select': {
      const key = candidate(id)?.property_id || id;
      UI.selected = UI.selected === key ? null : key; render();
      const c = document.getElementById('card-' + key); if (c && t.closest('svg')) c.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      break;
    }
    case 'toggle-shortlist': {
      if (S.shortlist.includes(id)) { S.shortlist = S.shortlist.filter((x) => x !== id); save(); toast(`Removed ${candidate(id).property_name} from your shortlist`); }
      else if (S.shortlist.some(x=>candidate(x)?.property_id===candidate(id)?.property_id)) {
        S.shortlist=S.shortlist.map(x=>candidate(x)?.property_id===candidate(id)?.property_id?id:x);save();toast('Updated the selected plan for '+candidate(id).property_name);
      }
      else if (S.shortlist.length >= 3) toast('Your shortlist holds 3 places. Remove one first.');
      else { S.shortlist.push(id); save(); toast(`Shortlisted ${candidate(id).property_name}`); }
      break;
    }
    case 'evidence': UI.drawer = id; render(); document.getElementById('drawer-close')?.focus(); break;
    case 'close-drawer': { const back = UI.drawer; UI.drawer = null; render(); document.querySelector(`[data-action="evidence"][data-id="${back}"]`)?.focus(); break; }
    case 'toggle-map': UI.mapOpen = !UI.mapOpen; render(); break;
    case 'map-retry': S.sim.mapFails = false; save(); render(); break;
    case 'clear-search': UI.query = ''; UI.filters = { fit: true, conflict: true, insufficient: true }; render(); break;
    case 'sim-off': S.sim[t.dataset.key] = false; save(); render(); break;
    case 'focus-field': ev.preventDefault(); document.getElementById(t.dataset.field)?.focus(); break;
    case 'prefs-apply': {
      const errs = prefErrors(S.draft);
      if (errs.length) { UI.errorsShown = true; render(); document.getElementById('err-summary')?.focus(); return; }
      S.prefs = { ...clone(S.draft), monthly_budget_per_person: Number(S.draft.monthly_budget_per_person) };
      S.draft = null; UI.errorsShown = false; bump(); toast(`Applied. Results now use revision ${S.revision}.`); break;
    }
    case 'prefs-discard': S.draft = null; UI.errorsShown = false; render(); toast('Changes discarded'); break;
    case 'run-ai': runAI(); break;
    case 'retry-api': initRoomwise(); break;
    case 'q-delete': { const n = S.notes[id]; n.questions = n.questions.filter((q) => q.id !== t.dataset.q); save(); render(); break; }
    case 'save-brief': {
      if (!S.shortlist.length && t.dataset.origin === 'guide') S.shortlist = guideCandidates().map((r) => r.cand.id);
      await saveServerBrief(t.dataset.origin || 'shortlist'); break;
    }
    case 'copy-brief': {
      const b = S.briefs.find((x) => x.id === id); const txt = briefText(b); const ta = document.getElementById('brief-text');
      const fallback = () => { ta.focus(); ta.select(); toast('Text selected. Press Ctrl+C or ⌘C to copy.'); };
      try { navigator.clipboard.writeText(txt).then(() => toast('Brief copied'), fallback); } catch (e) { fallback(); }
      break;
    }
    case 'prio': {
      const v = t.dataset.v, p = S.prefs.priorities;
      if (p.includes(v)) S.prefs.priorities = p.filter((x) => x !== v);
      else if (p.length < 3) S.prefs.priorities = [...p, v];
      else { toast('You have three. Tap one to remove it first.'); return; }
      bump(); render(); break;
    }
    case 'gview': S.guide.view = t.value; save(); render(); break;
    case 'guide-back': break;
    case 'guide-next': {
      const n = Number(t.dataset.step);
      if (n === 1) { const p = S.prefs; if (prefErrors(p).length) { UI.guideErrors = true; render(); return; } UI.guideErrors = false; }
      if (!S.guide.completed_steps.includes(n)) S.guide.completed_steps.push(n);
      if (n === 3) { S.guide.selected_candidate_ids = guideCandidates().map((r) => r.cand.id); API.checklistKey = null; }
      save(); go('#guide-' + (n + 1)); break;
    }
    case 'guide-finish': if (!S.guide.completed_steps.includes(4)) S.guide.completed_steps.push(4); save(); toast('All four steps done. Your progress is saved.'); break;
    case 'guide-exit': S.guide.updated_at = new Date().toISOString(); save(); go('#home'); toast(`Saved. Resume at step ${S.guide.current_step} from the home page.`); break;
    case 'guide-restart': UI.dialog = 'restart'; render(); document.getElementById('dlg-ok')?.focus(); break;
    case 'guide-restart-confirm': S.guide = { ...defaultState().guide }; UI.dialog = null; save(); go('#guide-1'); toast('Guide restarted. Saved briefs were kept.'); break;
    case 'dialog-close': UI.dialog = null; render(); break;
    case 'reset-all': { const briefs = S.briefs, workspaceRevision = S.workspaceRevision, revision = S.revision + 1; S = defaultState(); S.briefs = briefs; S.workspaceRevision = workspaceRevision; S.revision = revision; queueComparison(); UI.demo = false; save(); go('#home'); toast('Demo reset. Saved briefs were kept.'); break; }
  }
});

document.getElementById('menu-btn').addEventListener('click', () => { UI.menu = !UI.menu; render(); });
document.getElementById('demo-btn').addEventListener('click', () => { UI.demo = !UI.demo; render(); });

document.addEventListener('keydown', (ev) => {
  if (ev.key === 'Escape') {
    if (UI.dialog) { UI.dialog = null; render(); }
    else if (UI.drawer) { const back = UI.drawer; UI.drawer = null; render(); document.querySelector(`[data-action="evidence"][data-id="${back}"]`)?.focus(); }
    else if (UI.demo) { UI.demo = false; render(); document.getElementById('demo-btn').focus(); }
  }
  if ((ev.key === 'Enter' || ev.key === ' ') && ev.target.classList?.contains('mk')) { ev.preventDefault(); ev.target.dispatchEvent(new MouseEvent('click', { bubbles: true })); }
  if (ev.key === 'Tab' && (UI.drawer || UI.dialog)) {
    const box = document.querySelector(UI.dialog ? '.dialog' : '#drawer');
    const f = box.querySelectorAll('button, a[href], input, select, textarea');
    if (!f.length) return;
    if (ev.shiftKey && document.activeElement === f[0]) { ev.preventDefault(); f[f.length - 1].focus(); }
    else if (!ev.shiftKey && document.activeElement === f[f.length - 1]) { ev.preventDefault(); f[0].focus(); }
  }
});

function readBind(el, target) {
  const k = el.dataset.bind || el.dataset.gbind;
  if (k === 'travel_modes') { const set = new Set(target.travel_modes); el.checked ? set.add(el.value) : set.delete(el.value); target.travel_modes = ['walk', 'transit', 'bike', 'drive'].filter((m) => set.has(m)); }
  else if (el.type === 'checkbox') target[k] = el.checked;
  else if (k === 'private_bedroom_required') target[k] = el.value === 'true';
  else if (k === 'household_size') target[k] = Number(el.value);
  else if ('num' in el.dataset) target[k] = el.value === '' ? '' : Number(String(el.value).replace(/[^0-9.]/g, ''));
  else target[k] = el.value;
}

let guideTimer;
document.addEventListener('input', (ev) => {
  const el = ev.target;
  if (el.dataset.ui === 'query') { UI.query = el.value; render(); return; }
  if (el.dataset.bind && el.type === 'range') { readBind(el, S.draft); document.getElementById('f-max-out').textContent = el.value + ' min'; return; }
  if (el.dataset.bind) { readBind(el, S.draft); render(); return; }
  if (el.dataset.gbind && el.type !== 'radio' && el.type !== 'checkbox' && el.type !== 'date') {
    readBind(el, S.prefs); save(); clearTimeout(guideTimer); guideTimer = setTimeout(() => { bump(); render(); }, 600); render(); return;
  }
  if (el.dataset.answer) { const n = S.notes[el.dataset.answer]; const q = n.questions.find((x) => x.id === el.dataset.q); q.answer = el.value; save(); return; }
  if (el.dataset.cl && el.dataset.clf === 'notes') { const i = S.guide.checklist.find((x) => x.id === el.dataset.cl); i.notes = el.value; save(); }
});

document.addEventListener('change', (ev) => {
  const el = ev.target;
  if (el.dataset.filter) { UI.filters[el.dataset.filter] = el.checked; render(); return; }
  if (el.dataset.sim) { S.sim[el.dataset.sim] = el.checked; save(); render(); return; }
  if (el.dataset.gbind && (el.type === 'radio' || el.type === 'checkbox' || el.type === 'date')) { readBind(el, S.prefs); bump(); render(); return; }
  if (el.dataset.bind && (el.tagName === 'SELECT' || el.type === 'range')) { readBind(el, S.draft); render(); return; }
  if (el.dataset.cl && el.dataset.clf === 'notes') { const i = S.guide.checklist.find((x) => x.id === el.dataset.cl); i.notes = el.value; save(); }
});

document.addEventListener('change', (ev) => {
  const el = ev.target;
  if (el.dataset.filter) { UI.filters[el.dataset.filter] = el.checked; render(); return; }
  if (el.dataset.sim) { S.sim[el.dataset.sim] = el.checked; save(); render(); return; }
  if (el.dataset.gbind && (el.type === 'radio' || el.type === 'checkbox' || el.type === 'date')) { readBind(el, S.prefs); bump(); render(); return; }
  if (el.dataset.bind && (el.tagName === 'SELECT' || el.type === 'range')) { readBind(el, S.draft); render(); return; }
  if (el.dataset.edit) {
    const e = UI.editing, k = el.dataset.edit;
    if (k === 'weekdays') { const s = new Set(e.weekdays); el.checked ? s.add(el.value) : s.delete(el.value); e.weekdays = [...s]; }
    else if (k === 'arrival_buffer_minutes') e[k] = el.value === '' ? null : Number(el.value);
    else e[k] = el.value;
    return;
  }
  if (el.dataset.cl && el.dataset.clf === 'status') { const i = S.guide.checklist.find((x) => x.id === el.dataset.cl); i.status = el.value; save(); render(); }
});

document.addEventListener('submit', (ev) => {
  ev.preventDefault();
  const f = ev.target;
  if (f.dataset.form === 'home-search') {
    const v = Number(String(document.getElementById('home-budget').value).replace(/[^0-9.]/g, ''));
    if (v && v !== S.prefs.monthly_budget_per_person) {
      if (v < 200 || v > 5000) { toast('Enter a budget between $200 and $5,000 per person'); return; }
      S.prefs.monthly_budget_per_person = v; S.draft = null; bump();
    }
    go('#explore'); return;
  }
  if (f.dataset.form === 'q-add') {
    const id = f.dataset.id, inp = f.querySelector('input'), v = inp.value.trim();
    if (!v) { inp.focus(); return; }
    S.notes[id] = S.notes[id] || { questions: [] };
    S.notes[id].questions.push({ id: uid('q'), text: v, answer: '' }); save(); render();
    document.getElementById('newq-' + id)?.focus(); toast('Question added');
  }
  if (f.dataset.form === 'cl-add') {
    const v = document.getElementById('cl-new').value.trim(); if (!v) return;
    S.guide.checklist.push({ id: uid('u'), category: document.getElementById('cl-new-cat').value, title: v, details: '', status: 'not_started', notes: '', evidence_ids: [], needs_confirmation: false, origin: 'user' });
    save(); render(); document.getElementById('cl-new')?.focus();
  }
});

let lastRoute = null;
window.addEventListener('hashchange', () => {
  UI.menu = false; UI.drawer = null; UI.editing = null;
  const r = route();
  if (r.name !== 'preferences' && S.draft && JSON.stringify(S.draft) === JSON.stringify(S.prefs)) S.draft = null;
  render();
  if (lastRoute !== location.hash) { window.scrollTo(0, 0); document.getElementById('page-title')?.focus({ preventScroll: true }); }
  lastRoute = location.hash;
});
window.addEventListener('online', () => { S.sim.offline = false; render(); });
window.addEventListener('offline', () => { S.sim.offline = true; render(); });

initRoomwise();
lastRoute = location.hash;
