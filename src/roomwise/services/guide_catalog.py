"""Guide communities stay browsable while separately sourced evidence is added."""
from copy import deepcopy
import json
from roomwise.config import ROOT


def guide_properties(guide,enrichment=None):
    if enrichment is None:
        path=ROOT/'data/housing-guide-evidence.json'
        enrichment=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    result=[]
    for entry in guide['communities']:
        if entry.get('catalog_property_id'):continue
        key=entry['id'];source_id='guide-'+key
        source=dict(id=source_id,type='guide_reference',title='Housing guide reference: '+entry['name'],
            url=entry['source_urls'][0] if entry['source_urls'] else None,checked_at='2026-10-24',
            review_status='research_observation',refresh_policy='manual_only',reviewed_at=None,sha256=guide['document_sha256'],
            excerpt=entry['guide_price_summary'],review_scope='Imported from the supplied housing guide. Reference prices and layouts have not been verified against a current operator quote.')
        update=enrichment.get('properties',{}).get(key,{})
        point=update.get('coordinates') or {}
        reference=deepcopy(entry)
        sources=[source]
        if update.get('status')=='operator_observed':
            reference['evidence_update']=update
            sources.append(dict(id='operator-guide-'+key,type='operator',title='Operator evidence: '+entry['name'],
                url=update['source_url'],checked_at=update['checked_at'],review_status='research_observation',
                refresh_policy='manual_review',reviewed_at=None,sha256=update.get('source_sha256'),
                excerpt='Published floor-plan asking figures and community address; billing basis and fees require confirmation.',
                review_scope=update['billing_note']))
        result.append(dict(id=key,name=entry['name'],address=update.get('address') or entry['address'],lat=point.get('lat'),lon=point.get('lon'),
            coordinate_basis='operator_community_point' if point else 'unverified',
            listing_type='area' if entry['zone']=='Private rentals and neighborhoods' else 'property',
            guide_reference=reference,sources=sources,offers=[dict(id=source_id,name=entry['layouts'],bedrooms=None,
                bathrooms=None,amount=None,basis='unknown',period='unknown',contract='unknown',room='unknown',
                installments=None,start=None,end=None,term_label='Guide reference; exact term unverified',annual_total=None,
                upfront=[],unknowns=(['New operator asking figures found; billing basis, required fees and exact lease still need confirmation.'] if update.get('prices') else ['Guide price reference: '+entry['guide_price_summary'],
                    'Verify the exact floor plan, current rent, billing basis, mandatory fees and availability with the operator.']),
                conflicts=[],property_id=key,source_id=source_id,evidence=[],fees=[],utility_matrix={},
                price_confidence_tier='GUIDE_REFERENCE',source_conflicts=[],operator_questions=[])]))
    return result
