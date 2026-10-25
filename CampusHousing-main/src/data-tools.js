let DATA_RECORDS=null,DATA_ERROR=null;
function viewData() {
  if (!DATA_RECORDS && !DATA_ERROR) loadDataRecords();
  return `<div class="page-head"><div class="kicker">Local records</div><h1>Data and recovery</h1><p>Export your records or move a workspace or brief into recoverable trash. Trash remains on this server until an operator performs a permanent purge; it is not permanent erasure.</p></div><div class="panel stack-sm"><button class="btn" data-action="data-refresh">Refresh records</button>${DATA_ERROR?`<p role="alert">${esc(DATA_ERROR)}</p>`:''}${!DATA_RECORDS?'<p>Loading records…</p>':`<p>${DATA_RECORDS.length} records. Exports contain schedules and notes; keep downloaded files private.</p><ul>${DATA_RECORDS.map(r=>`<li style="margin:16px 0"><b>${esc(r.collection==='briefs'?'Decision brief':'Workspace')}</b> · ${esc(r.id)} · ${esc(r.deleted_at?'In trash':r.updated_at)} <div class="btn-row">${r.deleted_at?`<button class="btn btn-sm" data-action="record-restore" data-id="${esc(r.id)}" data-collection="${r.collection}">Restore</button>`:`<button class="btn btn-sm" data-action="record-export" data-id="${esc(r.id)}" data-collection="${r.collection}">Export JSON</button><button class="btn btn-sm" data-action="record-trash" data-id="${esc(r.id)}" data-collection="${r.collection}">Move to trash</button>`}</div></li>`).join('')}</ul>`}<p class="small">Current workspace: ${esc(workspaceID)}. After restoring this workspace, reload to resume editing. Operator database backups are separate from these individual exports.</p><p class="small">Provider disclosure: Street maps load OpenStreetMap tiles; nearby searches send the catalog property point and category to the configured provider (OpenStreetMap Overpass by default, or Google Places when enabled). Google Maps links and optional embedded maps send browser requests to Google. Results stay live, outside saved briefs and model training. Roomwise does not send your class schedule to Places. Routes, if enabled, send housing/building points, travel mode and transit arrival time. Maps usage follows <a href="https://maps.google.com/help/terms_maps/" target="_blank" rel="noopener noreferrer">Google Maps terms</a> and <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Google privacy policy</a>.</p></div>`;
}
async function loadDataRecords() {
  try{DATA_RECORDS=(await api('/records')).records;DATA_ERROR=null;}catch(error){DATA_ERROR=error.message;}
  if (route().name==='data') render();
}
document.addEventListener('click',async event=>{
  const b=event.target.closest('[data-action]');if(!b)return;
  const action=b.dataset.action;
  if(action==='data-refresh'){DATA_RECORDS=null;DATA_ERROR=null;loadDataRecords();return;}
  if(!['record-export','record-trash','record-restore'].includes(action))return;
  b.disabled=true;
  const base='/records/'+b.dataset.collection+'/'+encodeURIComponent(b.dataset.id);
  try{
    if(action==='record-export') {
      const data=await api(base+'/export');const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
      const a=document.createElement('a');a.href=url;a.download='roomwise-'+b.dataset.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    }else{
      await api(base+(action==='record-restore'?'/restore':''),{method:action==='record-restore'?'POST':'DELETE'});
      if(b.dataset.collection==='briefs') {
        if(action==='record-trash')S.briefs=S.briefs.filter(x=>x.id!==b.dataset.id);
        else {const brief=briefForDisplay(await api('/briefs/'+encodeURIComponent(b.dataset.id)));if(!S.briefs.some(x=>x.id===brief.id))S.briefs.push(brief);}
        save();
      }
      if(action==='record-trash' && b.dataset.collection==='workspaces' && b.dataset.id===workspaceID){clearTimeout(workspaceTimer);API.workspaceTrashed=true;API.conflict=true;API.sync='workspace in trash; restore and reload to resume';}
      await loadDataRecords();
    }
  }catch(error){toast(error.message);}finally{b.disabled=false;}
});
