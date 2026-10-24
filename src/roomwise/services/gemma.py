"""Bounded evidence tool boundary; no model response can change calculated fit or prices."""
from roomwise.api.errors import APIError
from roomwise.api.schemas import AIExplanation


class EvidenceTools:
    def __init__(self, comparison, evidence, max_calls=8):
        self.comparison,self.evidence,self.remaining=comparison,evidence,max_calls
        self.allowed_evidence={e for c in comparison['candidate_results'] for e in c['evidence_ids']}

    def call(self, name, **args):
        if self.remaining<=0: raise APIError('tool_limit','Evidence tool limit reached.',429)
        self.remaining-=1
        if name=='get_comparison': return self.comparison
        candidate=next((x for x in self.comparison['candidate_results'] if x['candidate_id']==args.get('candidate_id')),None)
        if not candidate: raise APIError('unknown_candidate','Tools can only access compared candidates.')
        if name=='get_area_data': return candidate
        if name=='get_commute':
            return [r for r in candidate['commute_estimates'] if r['commitment_id']==args.get('commitment_id') and r['mode']==args.get('mode')]
        if name=='get_offer_evidence': return [self.evidence.get(key) for key in candidate['evidence_ids']]
        if name=='nearby_places': return {'status':'unavailable','places':[],'reason':'Live nearby discovery is available in property details when enabled; Google Places content is excluded from saved model context.'}
        raise APIError('unknown_tool','This tool is not permitted.')


def explain(runtime, comparison, evidence):
    tools=EvidenceTools(comparison,evidence)
    try:
        result=runtime.explain(comparison,tools)
        result=AIExplanation.model_validate(result).model_dump()
        if result['status']=='ai_unavailable': return result
        if result['status']!='complete' or not result.get('model_id'):
            raise ValueError('No real model identity or completion status.')
        for item in result['candidate_explanations']:
            if item['candidate_id'] not in {x['candidate_id'] for x in comparison['candidate_results']}:
                raise ValueError('Unknown candidate in model output.')
            if not item.get('evidence_ids') or not set(item['evidence_ids'])<=tools.allowed_evidence:
                raise ValueError('Unrecognized citation.')
            if any(field in item for field in ('amount','fit_state','price','commute_minutes')):
                raise ValueError('Model output cannot define calculated facts.')
        return {**result,'input_revision':comparison['input_revision']}
    except Exception:
        return dict(status='ai_unavailable',model_id=None,input_revision=comparison['input_revision'],candidate_explanations=[],
                    error={'code':'invalid_or_failed_inference','message':'Inference failed or its evidence could not be validated.','retryable':True})
