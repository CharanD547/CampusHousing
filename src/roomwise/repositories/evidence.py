"""Public evidence metadata; complete scraped pages are not returned by default."""
from roomwise.api.errors import APIError


class EvidenceRepository:
    def __init__(self, catalog):
        self.catalog = catalog

    def get(self, key):
        try:
            source = self.catalog.source(key)
        except KeyError:
            raise APIError('evidence_not_found', 'Evidence was not found.', 404) from None
        return dict(id=key, source_type='operator', source_name=source['title'], url=source['url'],
                    observed_at=source['checked_at'], supports=source.get('review_scope', source.get('applicable_term')),
                    excerpt=source.get('excerpt'), review_status=source['review_status'],
                    license_or_reuse_scope='Short source locator only. Operator terms apply; no review republication permission inferred.')
