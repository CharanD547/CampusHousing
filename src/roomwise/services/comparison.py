"""Validate inputs, calculate independently of AI, and retain route coverage gaps."""
from hashlib import sha256
import json
import uuid
from copy import deepcopy
from datetime import timedelta

from roomwise.api.errors import APIError
from roomwise.config import now
from roomwise.domain.costs import evaluate


def catalog_fingerprint(catalog):
    return sha256(json.dumps(catalog, sort_keys=True).encode()).hexdigest()


def candidates(catalog):
    result = []
    for prop in catalog:
        for offer in prop['offers']:
            result.append(dict(id=offer['id'], type='offer', property_id=prop['id'], property_name=prop['name'],
                               address=prop['address'], coordinates={'lat':prop['lat'], 'lon':prop['lon']},
                               coordinate_basis='representative_address', data_status='source_review_required' if offer['amount'] is None else 'reviewed_asking_price',
                               sources=prop['sources'], offer=dict(id=offer['id'], layout=offer['name'], bedrooms=offer['bedrooms'], contract=offer['contract'],room=offer['room'],
                               price={'amount':offer['amount'], 'currency':'USD', 'basis':{'person':'per_person','unit':'whole_unit'}.get(offer['basis'], 'unknown'),
                                      'frequency':{'monthly':'calendar_month','installment':'installment'}.get(offer['period'], 'other'),
                                      'payment_count':offer.get('installments'), 'term':{'start':offer.get('start'), 'end':offer.get('end'), 'label':offer['term_label']},
                                      'source_id':offer['source_id'], 'last_reviewed_at':next(s for s in prop['sources'] if s['id']==offer['source_id'])['checked_at']},
                               fees=offer['upfront'], unknown_costs=offer['unknowns'])))
    return result


class ComparisonService:
    def __init__(self, catalog, campuses, routing, store):
        self.catalog, self.campuses, self.routing, self.store = catalog, campuses, routing, store

    def compare(self, request):
        self.campuses.get(request.campus_id)
        buildings = {c.id:self.campuses.building(request.campus_id, c.building_id) for c in request.commitments}
        catalog = self.catalog.catalog()
        public = {c['id']:c for c in candidates(catalog)}
        ids = request.candidate_ids or list(public)
        if not set(ids) <= public.keys():
            raise APIError('unknown_candidate', 'Choose candidates in the audited catalog.')
        p = request.preferences
        # Date placeholders are used only for the legacy calculator; their results remain unknown below.
        prefs = dict(budget=p.monthly_budget_per_person, household_size=p.household_size,
                     room='private' if p.private_bedroom_required else 'shared', individual_contract=p.individual_lease_required,
                     start=p.move_in_date.isoformat() if p.move_in_date else '0001-01-01',
                     end=p.move_out_date.isoformat() if p.move_out_date else '9999-12-31')
        occurrences=[]
        for commitment in request.commitments:
            dates=[request.route_date]
            if request.routing_scope=='representative_week':
                monday=request.route_date-timedelta(days=request.route_date.weekday())
                dates=[monday+timedelta(days=i) for i,day in enumerate(('mon','tue','wed','thu','fri','sat','sun')) if day in commitment.weekdays]
            occurrences.extend((commitment,day) for day in dates)
        results=[]
        routing=self.routing.for_request() if hasattr(self.routing,'for_request') else self.routing
        for key in ids:
            candidate=public[key]
            prop=next(x for x in catalog if x['id']==candidate['property_id'])
            offer=next(x for x in prop['offers'] if x['id']==key)
            source=next(x for x in prop['sources'] if x['id']==offer['source_id'])
            costs=evaluate(offer,prefs,source)
            conflicts=list(costs['conflicts']); unknowns=list(costs['unknowns'])
            if not p.move_in_date:
                # No fabricated housing dates or date conflicts when the user hasn't chosen a stay.
                conflicts=[x for x in conflicts if x!='Published lease dates do not cover your intended stay.']
                costs['checks']['dates']='unknown'; unknowns.append('Intended housing dates were not supplied.')
            if p.requested_bedrooms and (offer['bedrooms'] is None or offer['bedrooms']<p.requested_bedrooms):
                if offer['bedrooms'] is None: unknowns.append('Requested bedroom count is not documented.')
                else: conflicts.append('This layout has fewer bedrooms than requested.')
            if offer['period']!='monthly':
                # Contractual installments cannot be compared with a monthly budget as though identical.
                costs['checks']['budget']='unknown'
                conflicts=[x for x in conflicts if x!='The known recurring amount alone exceeds your payment budget.']
                unknowns.append('Installment/payment amount is not a documented calendar-month total; monthly affordability is unresolved.')
            routes=[]
            if not request.commitments:
                unknowns.append('Add class commitments before judging commute coverage.')
            for commitment,route_day in occurrences:
                for mode in p.travel_modes:
                    if route_day.strftime('%a').lower() not in commitment.weekdays:
                        route=dict(candidate_id=key,commitment_id=commitment.id,mode=mode,minutes=None,status='unsupported',
                                   route_date=route_day.isoformat(),provider='schedule_validation',context={},coverage_notes=['Representative route date does not match this commitment weekday.'],evidence_ids=[])
                    else:
                        try:
                            route=routing.estimate(candidate,buildings[commitment.id],commitment,mode,route_day,p)
                        except Exception:
                            route=dict(candidate_id=key,commitment_id=commitment.id,mode=mode,minutes=None,status='unavailable',
                                       route_date=route_day.isoformat(),provider=getattr(self.routing,'provider','routing_adapter'),context={},
                                       coverage_notes=['Routing request failed; other comparisons remain available.'],evidence_ids=[])
                    # Provider boundaries cannot turn absent durations into a positive route.
                    if route.get('status')=='supported' and (not isinstance(route.get('minutes'),(int,float)) or not 0<=route['minutes']<=1440):
                        route={**route,'status':'unavailable','minutes':None,'coverage_notes':['Provider returned an invalid duration.']}
                    routes.append(route)
            best=[]
            for commitment,route_day in occurrences:
                options=[r for r in routes if r['commitment_id']==commitment.id and r['route_date']==route_day.isoformat() and r['status']=='supported']
                if options: best.append(min(options,key=lambda x:x['minutes']))
            supported=len(best)
            if supported<len(occurrences): unknowns.append('Not all class commitments have supported route evidence.')
            if any(r['minutes']>p.max_commute_minutes for r in best): conflicts.append('A supported class journey exceeds the maximum commute preference.')
            state='conflict' if conflicts else 'insufficient_evidence' if unknowns else 'documented_fit'
            costs.update(status=state, conflicts=list(dict.fromkeys(conflicts)), unknowns=list(dict.fromkeys(unknowns)))
            results.append(dict(candidate_id=key,property_id=prop['id'],fit_state=state,
                                cost_breakdown=costs,known_recurring_subtotal=costs['per_person'],
                                price_label='Base installment / unknown extras' if offer['period']=='installment' else 'Known subtotal; confirm missing charges',
                                unknown_costs=list(dict.fromkeys(unknowns)),hard_conflicts=list(dict.fromkeys(conflicts)),
                                reason_codes=(['hard_conflict'] if conflicts else [])+(['missing_evidence'] if unknowns else []),
                                supported_commitments=supported,total_commitments=len(occurrences),
                                limiting_commitment=max(best,key=lambda x:x['minutes'])['commitment_id'] if best else None,
                                commute_estimates=routes,evidence_ids=[source['id']],source_date=source['checked_at']))
        result=dict(id=uuid.uuid4().hex,input_revision=request.revision,revision=request.revision,
                    status='partial' if any(x['unknown_costs'] for x in results) else 'complete',
                    created_at=now(),inputs=request.model_dump(mode='json'),catalog_fingerprint=catalog_fingerprint(catalog),
                    catalog_snapshot=[public[key] for key in ids],
                    building_snapshot=list({b['id']:b for b in buildings.values()}.values()),
                    candidate_results=results,ai_status='not_requested',missing_data=sorted({x for r in results for x in r['unknown_costs']}))
        saved=deepcopy(result)
        # Google route results are live-only. No provider durations, derived fit verdicts or route bodies
        # are retained in comparisons/briefs. Inputs remain available for a new provider request.
        for row in saved['candidate_results']:
            if any(r.get('provider')=='google_routes' for r in row['commute_estimates']):
                row['commute_estimates']=[];row['supported_commitments']=0;row['limiting_commitment']=None
                row['hard_conflicts']=[x for x in row['hard_conflicts'] if x!='A supported class journey exceeds the maximum commute preference.']
                row['unknown_costs'].append('Live Google Maps journey data is excluded from saved records; request fresh estimates.')
                row['fit_state']='conflict' if row['hard_conflicts'] else 'insufficient_evidence'
                row['cost_breakdown'].update(status=row['fit_state'],conflicts=row['hard_conflicts'],unknowns=row['unknown_costs'])
                row['reason_codes']=(['hard_conflict'] if row['hard_conflicts'] else [])+['missing_evidence']
        saved['missing_data']=sorted({x for row in saved['candidate_results'] for x in row['unknown_costs']})
        saved['status']='partial' if saved['missing_data'] else 'complete'
        self.store.save_comparison(saved)
        return result
