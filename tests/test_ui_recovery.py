from hashlib import sha256
from types import SimpleNamespace
from roomwise.services.guide import checklist


def test_renamed_travel_checklist_preserves_existing_progress():
    key=sha256(b'offer:commute:Verify each class journey, including walks, transfers and timetable dates.').hexdigest()[:20]
    previous=SimpleNamespace(id=key,status='done',notes='Already checked',origin='deterministic')
    request=SimpleNamespace(candidate_id='offer',previous_items=[previous])
    comparison={'input_revision':1,'candidate_results':[{'candidate_id':'offer','unknown_costs':[],'hard_conflicts':[],'evidence_ids':[]}]}
    result=checklist(comparison,request)
    travel=next(i for i in result['checklist'] if i['category']=='commute')
    assert travel['status']=='done' and travel['notes']=='Already checked'
    assert 'class' not in travel['title']
