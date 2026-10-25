"""Guide communities are browsable candidates, with no fabricated quotes or map points."""


def guide_properties(guide):
    result=[]
    for entry in guide['communities']:
        if entry.get('catalog_property_id'):continue
        key=entry['id'];source_id='guide-'+key
        source=dict(id=source_id,type='guide_reference',title='Housing guide reference: '+entry['name'],
            url=entry['source_urls'][0] if entry['source_urls'] else None,checked_at='2026-10-24',
            review_status='research_observation',refresh_policy='manual_only',reviewed_at=None,sha256=guide['document_sha256'],
            excerpt=entry['guide_price_summary'],review_scope='Imported from the supplied housing guide. Reference prices and layouts have not been verified against a current operator quote.')
        result.append(dict(id=key,name=entry['name'],address=entry['address'],lat=None,lon=None,
            listing_type='area' if entry['zone']=='Private rentals and neighborhoods' else 'property',
            guide_reference=entry,sources=[source],offers=[dict(id=source_id,name=entry['layouts'],bedrooms=None,
                bathrooms=None,amount=None,basis='unknown',period='unknown',contract='unknown',room='unknown',
                installments=None,start=None,end=None,term_label='Guide reference; exact term unverified',annual_total=None,
                upfront=[],unknowns=['Guide price reference: '+entry['guide_price_summary'],
                    'Verify the exact floor plan, current rent, billing basis, mandatory fees and availability with the operator.'],
                conflicts=[],property_id=key,source_id=source_id,evidence=[],fees=[],utility_matrix={},
                price_confidence_tier='GUIDE_REFERENCE',source_conflicts=[],operator_questions=[])]))
    return result
