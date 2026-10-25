/* Session-only chat: no raw review ingestion or automatic training export. */
const CHAT={messages:[],pending:false,error:null,contextCandidateID:null};
function chatCandidateIDs() { return CHAT.contextCandidateID && candidate(CHAT.contextCandidateID) ? [CHAT.contextCandidateID] : S.shortlist.slice(0,3); }
function viewAssistant() {
  const configured=API.health?.assistant;
  const enabled=configured?.status==='configured_requires_verification';
  return `<div class="page-head"><div class="kicker">Roomwise assistant</div><h1 id="page-title" tabindex="-1">Ask about your housing decision</h1>
    <p>Understand the shortlist, missing costs, billing basis and questions to ask next. Prices and fit checks remain owned by your comparison.</p></div>
    <div class="two-col"><section class="panel stack-sm"><h2>Your conversation</h2>
      <div class="small" role="status">${enabled ? `Configured model: ${esc(configured.model_id)}. A successful answer will identify its model and sources.` : 'Local research helper · no AI model runs. Ask about your comparison, missing costs, installment billing or next steps. Gemma or Gemini can be connected later.'}</div>
      <div role="log" aria-label="Assistant conversation" aria-live="polite">${CHAT.messages.map(m=>`<article class="panel stack-sm" style="margin:14px 0"><b>${m.role==='user' ? 'You':'Roomwise'}</b><p style="white-space:pre-wrap">${esc(m.content)}</p>
        ${m.role==='assistant' ? `<p class="tiny">${m.model ? 'Model: '+esc(m.model):m.fallback?'Local rules · Gemma attempt did not pass validation':'Local rules · no model run'} · input revision ${m.revision}${m.revision!==S.revision || m.selection!==JSON.stringify(chatCandidateIDs()) ? ' · context changed; answer is out of date':''}</p>`:''}
        ${m.fallback?`<p class="small">${esc(m.fallback.message)}</p>`:''}
        ${(m.evidence_ids || []).map(id=>{const e=CANDIDATES.flatMap(c=>c.evidence).find(e=>e.id===id);return e?.url ? `<a class="btn btn-sm" href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">${esc(e.source_name)}</a>`:'';}).join('')}
        ${(m.limitations || []).length ? `<p class="small">Limits: ${m.limitations.map(esc).join(' ')}</p>`:''}</article>`).join('')}
        ${CHAT.pending ? '<p role="status">Checking your saved comparison and available evidence…</p>':''}
      </div>
      ${CHAT.error ? `<p role="alert">${esc(CHAT.error)}</p>`:''}
      <form data-form="assistant-chat" class="stack-sm"><label for="assistant-question">Your question</label><textarea class="input" id="assistant-question" rows="3" maxlength="2000" placeholder="What costs are still missing from my shortlist?" required ${CHAT.pending ? 'disabled':''}></textarea>
        <button class="btn btn-primary" type="submit" ${CHAT.pending ? 'disabled':''}>Ask Roomwise</button></form>
      <p class="tiny">Chat stays in this tab and is not added to training data. With a provider enabled, your question, recent conversation and the selected comparison evidence are sent to that configured model.</p>
    </section><aside class="panel stack-sm"><h2>Try asking</h2>${['What does per installment mean?','Which facts are still missing for these offers?','What should I ask before signing?'].map(q=>`<button class="btn" data-assistant-prompt="${esc(q)}">${esc(q)}</button>`).join('')}
      <p class="small">Context: revision ${S.revision}, ${CHAT.contextCandidateID?esc(candidate(CHAT.contextCandidateID)?.property_name || 'Selected plan')+' · '+esc(candidate(CHAT.contextCandidateID)?.offer.layout || ''):S.shortlist.length ? S.shortlist.length+' shortlisted offers':'first three compared offers'}. No raw resident reviews are sent to the assistant.</p>
      ${CHAT.contextCandidateID?'<button class="btn btn-sm" data-action="clear-assistant-property">Use shortlist instead</button>':''}
      <a href="#compare">Review the deterministic comparison →</a></aside></div>`;
}
document.addEventListener('click',event=>{
  const button=event.target.closest('[data-assistant-prompt]');
  if(button) {const input=document.getElementById('assistant-question');input.value=button.dataset.assistantPrompt;UI.formDrafts[input.id]=input.value;input.focus();}
});
document.addEventListener('submit',async event=>{
  if(event.target.dataset.form!=='assistant-chat')return;
  event.preventDefault();
  if(CHAT.pending)return;
  const question=document.getElementById('assistant-question').value.trim();
  if(!question)return;
  const revision=S.revision, ids=chatCandidateIDs(),selection=JSON.stringify(ids), history=CHAT.messages.slice(-8).map(m=>({role:m.role,content:m.content.slice(0,3000)}));
  CHAT.messages.push({role:'user',content:question});UI.formDrafts['assistant-question']='';CHAT.pending=true;CHAT.error=null;render();
  try {
    const comparison=await ensureComparison();
    if(S.revision!==revision)throw new Error('Inputs changed. Ask again using the updated comparison.');
    const response=await api('/assistant/messages',{method:'POST',body:JSON.stringify({comparison_id:comparison.id,revision,
      request_id:requestID(),question,candidate_ids:ids,history})});
    if(response.status!=='complete') {CHAT.error=response.error?.message || 'The configured model is unavailable.';UI.formDrafts['assistant-question']=question;return;}
    CHAT.messages.push({role:'assistant',content:response.result.answer,model:response.model_id,provider:response.provider,revision,selection,
      stale:S.revision!==revision,evidence_ids:response.result.evidence_ids,limitations:response.result.limitations,fallback:response.fallback});
  } catch(error) {CHAT.error=error.message;UI.formDrafts['assistant-question']=question;}
  finally {CHAT.pending=false;render();}
});
