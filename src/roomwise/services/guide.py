"""Deterministic DormToDoor questions with stable IDs and user-owned progress."""
from hashlib import sha256
from roomwise.api.errors import APIError


def checklist(comparison, request):
    candidate=next((c for c in comparison['candidate_results'] if c['candidate_id']==request.candidate_id),None)
    if not candidate: raise APIError('unknown_candidate','Candidate is not part of this comparison.')
    previous={item.id:item for item in request.previous_items}
    prompts=[('money','Confirm the complete mandatory fee and utility schedule.'),
             ('lease','Confirm exact lease dates, payment count and deposit return conditions.'),
             ('roommates','Confirm bedroom arrangement and each roommate’s contractual responsibility.'),
             ('commute','Check walking access, nearby essentials and travel timetables.'),
             ('move_in','Confirm availability, move-in arrangements and required documents.')]
    prompts += [('money', 'Resolve: '+x) for x in candidate['unknown_costs']]
    prompts += [('lease', 'Resolve documented conflict: '+x) for x in candidate['hard_conflicts']]
    items=[]
    for category,title in prompts:
        key=sha256((request.candidate_id+':'+category+':'+title).encode()).hexdigest()[:20]
        old=previous.get(key)
        if old is None and category=='commute':
            legacy=sha256((request.candidate_id+':commute:Verify each class journey, including walks, transfers and timetable dates.').encode()).hexdigest()[:20]
            old=previous.get(legacy)
        items.append(dict(id=key,candidate_id=request.candidate_id,category=category,title=title,status=old.status if old else 'not_started',
                          notes=old.notes if old else '',evidence_ids=candidate['evidence_ids'],needs_confirmation=True,origin='deterministic'))
    # Preserve user-created items, but never accept submitted evidence as backend-reviewed facts.
    for item in request.previous_items:
        if item.origin=='user' and item.id not in {x['id'] for x in items}:
            items.append({**item.model_dump(), 'evidence_ids':[], 'needs_confirmation':True})
    return dict(input_revision=comparison['input_revision'],candidate_id=request.candidate_id,checklist=items,
                ai_status='not_used',wish_i_knew={'status':'insufficient_evidence','insights':[],
                'reason':'No authorized resident review dataset is configured.'})
