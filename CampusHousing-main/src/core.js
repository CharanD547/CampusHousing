/* ---------- state ---------- */
let STORE_KEY = 'roomwise.v2';
const clone = (o) => JSON.parse(JSON.stringify(o));

// randomUUID requires a secure context; LAN HTTP still supports getRandomValues.
function requestID() {
  if (typeof crypto.randomUUID==='function') return crypto.randomUUID();
  const bytes=crypto.getRandomValues(new Uint8Array(16));
  bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
  const hex=Array.from(bytes,x=>x.toString(16).padStart(2,'0')).join('');
  return [hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-');
}

function defaultState() {
  const prefs = {
    campus_id: 'vt', monthly_budget_per_person: 1100, household_size: 2,
    private_bedroom_required: true, individual_lease_required: false,
    travel_modes: ['walk', 'transit'], max_commute_minutes: 30, arrival_buffer_minutes: 10,
    move_in_date: '', move_out_date: '', priorities: ['Lowest monthly cost', 'Nearby essentials', 'Private bedroom'],
  };
  return {
    revision: 0,
    workspaceRevision: 0, route_date: TODAY,
    prefs,
    draft: null,
    commitments: [],
    shortlist: [],
    notes: {},
    setAside: {},
    briefs: [],
    guide: { current_step: 1, completed_steps: [], selected_candidate_ids: [], checklist: null, view: 'list', started: false, updated_at: null },
    ai: { status: 'idle', revision: null, result: null, requested_at: null },
    sim: { mapFails: false, aiFails: false, offline: false, emptyInventory: false },
  };
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw);
    const d = defaultState();
    return { ...d, ...s, commitments: [], guide: { ...d.guide, ...s.guide }, sim: { ...d.sim, ...s.sim }, ai: s.ai && s.ai.status === 'pending' ? { ...s.ai, status: 'interrupted' } : (s.ai?.flow === 'assistant-v2' ? s.ai : d.ai) };
  } catch (e) { return null; }
}

let S = loadState() || defaultState();
let storageOk = true;
function save() {
  if (API.ready) S.pendingSync=true;
  try { localStorage.setItem(STORE_KEY, JSON.stringify(S)); storageOk = true; } catch (e) { storageOk = false; }
  if (typeof queueWorkspaceSave === 'function') queueWorkspaceSave();
}

// transient UI state (not persisted)
const UI = {
  selected: null, query: '', filters: { fit: true, conflict: true, insufficient: true }, mapOpen: true,
  drawer: null, dialog: null, toast: null, editing: null, menu: false, demo: false, errorsShown: false,
  guideErrors: false,
};

/* ---------- formatting ---------- */
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const money = (n) => (n == null ? '—' : '$' + Math.round(n).toLocaleString('en-US'));
const money2 = (n) => n == null ? 'Unknown' : '$' + (Math.round(n * 100) / 100).toLocaleString('en-US', { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 });
const parseDate = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(Date.UTC(y, m - 1, d)); };
const daysBetween = (a, b) => Math.round((parseDate(b) - parseDate(a)) / 86400000);
const fmtDate = (s, opts = { month: 'short', day: 'numeric', year: 'numeric' }) => s ? parseDate(s).toLocaleDateString('en-US', { ...opts, timeZone: 'UTC' }) : '';
const campusDate = (s) => s && s.length>10 ? new Date(s).toLocaleDateString('en-CA',{timeZone:'America/New_York'}) : s;
const fmtDay = (s) => fmtDate(s, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
const ago = (s) => { const n = daysBetween(s, TODAY); return n <= 0 ? 'today' : n === 1 ? '1 day ago' : `${n} days ago`; };
const DAYS = [['mon', 'Mon'], ['tue', 'Tue'], ['wed', 'Wed'], ['thu', 'Thu'], ['fri', 'Fri'], ['sat', 'Sat'], ['sun', 'Sun']];
const dayLabel = (d) => (DAYS.find((x) => x[0] === d) || [, d])[1];
const fmtTime = (t) => { if (!t) return ''; const [h, m] = t.split(':').map(Number); const ap = h >= 12 ? 'pm' : 'am'; return `${((h + 11) % 12) + 1}:${String(m).padStart(2, '0')} ${ap}`; };
const plural = (n, w, p) => `${n} ${n === 1 ? w : (p || w + 's')}`;
const MODE_LABEL = { walk: 'Walk', transit: 'Bus', bike: 'Bike', drive: 'Drive' };
const BASIS_LABEL = { per_person: 'per person', whole_unit: 'for the whole unit', per_space: 'per space', per_pet: 'per pet', per_applicant: 'per applicant', per_leaseholder: 'per leaseholder', unknown:'billing basis unconfirmed' };
const FREQ_LABEL = { calendar_month: 'per month', installment: 'per installment', other: 'billing frequency unconfirmed' };
const building = (id) => BUILDINGS.find((b) => b.id === id);
const candidate = (id) => CANDIDATES.find((c) => c.id === id);
const uid = (p) => p + Math.random().toString(36).slice(2, 8);

/* ---------- icons ---------- */
const I = {
  walk: '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="13" cy="4" r="2"/><path d="M10.6 8.2 8 9.6V13h2v-2.2l1.2-.6-1.4 6.6L7 19.4 8.4 21l3.4-3 .9-3.2 2 2V21h2v-5.2l-2.3-2.4.7-3.2c.9 1.3 2.4 2.3 4.3 2.3v-2c-1.4 0-2.5-.8-3.1-1.9l-1-1.6c-.5-.8-1.5-1.1-2.4-.8z"/></svg>',
  bus: '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6 3h12a2 2 0 0 1 2 2v11a2 2 0 0 1-1 1.7V20a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1v-1H8v1a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-2.3A2 2 0 0 1 4 16V5a2 2 0 0 1 2-2zm0 3v5h12V6H6zm1.5 7.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm9 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z"/></svg>',
  bike: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="5.5" cy="16.5" r="3.5"/><circle cx="18.5" cy="16.5" r="3.5"/><path d="M5.5 16.5 9 9h6l3.5 7.5M9 9l3 7.5L15 9M13 5h3"/></svg>',
  car: '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M5 11 6.6 6.4A2 2 0 0 1 8.5 5h7a2 2 0 0 1 1.9 1.4L19 11a2 2 0 0 1 2 2v4a1 1 0 0 1-1 1h-1v1.5a1.5 1.5 0 0 1-3 0V18H8v1.5a1.5 1.5 0 0 1-3 0V18H4a1 1 0 0 1-1-1v-4a2 2 0 0 1 2-2zm2.2 0h9.6l-1.2-3.6a.6.6 0 0 0-.5-.4H8.9a.6.6 0 0 0-.5.4L7.2 11zM6.5 13a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm11 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z"/></svg>',
  check: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 8.5 3.2 3L13 4.5"/></svg>',
  x: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="m4 4 8 8M12 4l-8 8"/></svg>',
  q: '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M5.8 5.8a2.3 2.3 0 1 1 3.4 2c-.7.4-1.2.9-1.2 1.7v.4"/><circle cx="8" cy="12.6" r=".6" fill="currentColor"/></svg>',
  info: '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="10" cy="10" r="8"/><path d="M10 9v5M10 6.2v.1" stroke-linecap="round"/></svg>',
  alert: '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 2.5 18.5 17h-17L10 2.5z" stroke-linejoin="round"/><path d="M10 8v4M10 14.5v.1" stroke-linecap="round"/></svg>',
  search: '<svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5"/><path d="m13 13 4.5 4.5" stroke-linecap="round"/></svg>',
  doc: '<svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M5 2.5h6.5L15.5 6.5V17a.5.5 0 0 1-.5.5H5a.5.5 0 0 1-.5-.5V3a.5.5 0 0 1 .5-.5z"/><path d="M11 2.5V7h4.5M7.5 11h5M7.5 14h5"/></svg>',
  star: '<svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="m10 2.5 2.3 4.8 5.2.7-3.8 3.6.9 5.2L10 14.3l-4.6 2.5.9-5.2L2.5 8l5.2-.7L10 2.5z"/></svg>',
  starOn: '<svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="m10 2.5 2.3 4.8 5.2.7-3.8 3.6.9 5.2L10 14.3l-4.6 2.5.9-5.2L2.5 8l5.2-.7L10 2.5z"/></svg>',
  arrowUp: '<svg width="26" height="26" viewBox="0 0 26 26" fill="currentColor" aria-hidden="true"><path d="M13 2 4 12h6v12h6V12h6L13 2z"/></svg>',
  arrowR: '<svg width="26" height="26" viewBox="0 0 26 26" fill="currentColor" aria-hidden="true"><path d="M24 13 14 4v6H2v6h12v6l10-9z"/></svg>',
  home: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linejoin="round" aria-hidden="true"><path d="M4 11 12 4l8 7v9h-5v-6H9v6H4v-9z"/></svg>',
  lock: '<svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="4" y="9" width="12" height="8.5" rx="1.5"/><path d="M6.5 9V6.5a3.5 3.5 0 0 1 7 0V9"/></svg>',
};
const modeIcon = (m) => I[{transit:'bus',drive:'car'}[m] || m] || '';

/* Comparisons and price shares are supplied by api.js from the backend. */
const compareAll = () => CANDIDATES.map((c) => compare(c, S.prefs, S.commitments));
const FIT_ORDER = { fit: 0, insufficient: 1, conflict: 2 };

/* ---------- small renderers ---------- */
const FIT_META = {
  fit: { label: 'Criteria match', cls: 'chip-fit', icon: I.check },
  conflict: { label: 'Conflict', cls: 'chip-conflict', icon: I.x },
  insufficient: { label: 'Insufficient evidence', cls: 'chip-insufficient', icon: I.q },
};
const fitChip = (fit) => `<span class="chip ${FIT_META[fit].cls}">${FIT_META[fit].icon}${FIT_META[fit].label}</span>`;
const flagChip = (t) => `<span class="chip chip-flag">${I.q}${esc(t)}</span>`;
const demoChip = () => '<span class="chip chip-neutral">Source-backed catalog</span>';
const typeLabel = (t) => ({ offer: 'Specific offer', property: 'Property', area: 'Representative area' }[t]);

function priceBlock(r, size = 'card') {
  const c = r.cand;
  if(c.guide_reference)return planPrices({cand:c});
  if (c.type === 'area') {
    const a = c.area_range;
    return `<div class="cand-price"><span class="amt range num">${money(a.min)}–${money(a.max)}</span><span class="basis">area range ${BASIS_LABEL[a.basis]} ${FREQ_LABEL[a.frequency]}, not an offer</span></div>`;
  }
  if (!r.share) return `<div class="cand-price"><span class="tbd">Price needs confirmation</span></div>`;
  const p = c.offer.price;
  const label = r.share.complete ? (r.share.mandatory ? 'with required fees' : 'base rent, no required fees') : 'base only, required costs missing';
  return `<div class="cand-price"><span class="amt num">${money(p.amount)}</span><span class="basis">${BASIS_LABEL[p.basis]} ${FREQ_LABEL[p.frequency]}</span>${p.basis === 'whole_unit' ? `<span class="basis">≈ ${money(r.share.subtotal)} each split ${S.prefs.household_size} ways, ${label}</span>` : r.share.mandatory || !r.share.complete ? `<span class="basis">${money(r.share.subtotal)} ${label}</span>` : ''}</div>`;
}

function freshness(r) {
  const c = r.cand;
  if(c.guide_reference)return '<span class="chip chip-neutral">Guide reference · unverified</span>';
  const d = c.offer?.price?.last_reviewed_at || c.area_range?.observed_at || c.evidence[0]?.observed_at || TODAY;
  const stale = daysBetween(d, TODAY) > STALE_AFTER_DAYS;
  return stale ? flagChip(`Stale source, reviewed ${ago(d)}`) : `<span class="tiny">Reviewed ${ago(d)}</span>`;
}

function shortlistBtn(id, small = true) {
  const on = S.shortlist.includes(id);
  const full = !on && S.shortlist.length >= 3;
  return `<button type="button" class="btn ${small ? 'btn-sm' : ''}" data-action="toggle-shortlist" data-id="${id}" aria-pressed="${on}" ${full ? 'aria-disabled="true" title="Shortlist holds 3. Remove one first."' : ''}>${on ? I.starOn + ' Shortlisted' : I.star + ' Shortlist'}</button>`;
}

function asyncNotice(kind, title, body, action = '') {
  const icon = kind === 'ok' ? I.check : kind === 'bad' ? I.alert : I.info;
  return `<div class="notice ${kind}" role="status">${icon}<div><strong>${title}</strong>${body ? `<p>${body}</p>` : ''}${action}</div></div>`;
}
