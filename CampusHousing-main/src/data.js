/* Roomwise data is loaded from the same-origin backend, never generated as market facts. */
const TODAY = new Date().toLocaleDateString('en-CA', {timeZone:'America/New_York'});
let ROUTING_DATE = TODAY;
const STALE_AFTER_DAYS = 7;
const CAMPUS = {id:'vt', name:'Virginia Tech', city:'Blacksburg, VA', timezone:'America/New_York'};
const BUILDINGS = [];
const CANDIDATES = [];
const PHOTO_POS = { foxridge: '67% 80%', windsor: '17% 53%', terrace: '83% 50%', alight: '92% 30%', union: '60% 45%', mill: '47% 50%' };
let LIVE_PRICES_AT = null;
const ROUTE_EVIDENCE = {id:'routing-status',source_type:'Provider availability',source_name:'Roomwise routing status',observed_at:TODAY,supports:'Routing is unavailable until a real provider is configured. No estimated times are invented.'};
const PRIORITY_OPTIONS = [
  'Lowest monthly cost', 'Nearby essentials', 'Private bedroom', 'My own lease',
  'Quiet street', 'Groceries nearby', 'Pets allowed', 'Short lease term',
];

const CHECKLIST_CATEGORIES = [
  { id: 'money', label: 'Money' },
  { id: 'lease', label: 'Lease' },
  { id: 'roommates', label: 'Roommates' },
  { id: 'commute', label: 'Commute' },
  { id: 'move_in', label: 'Move-in' },
];
