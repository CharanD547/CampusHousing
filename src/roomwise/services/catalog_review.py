"""Apply an explicit, human-reviewed price correction without changing saved briefs."""
from copy import deepcopy
from decimal import Decimal
from datetime import datetime
import hashlib
import json
import re

from roomwise.domain.costs import Conflict


def reviewed_property(prop, source, review, snapshot, review_id):
    prop, source = deepcopy(prop), deepcopy(source)
    if source.get('pending_version'):
        raise Conflict('Resolve the pending source review before applying a price correction.')
    if snapshot['url'] != source['url']:
        raise ValueError('The reviewed URL must match the catalog source.')
    if source.get('checked_at') and datetime.fromisoformat(source['checked_at']) > datetime.fromisoformat(snapshot['retrieved_at']):
        raise Conflict('This source has a newer review; do not replace it with older evidence.')
    text = re.sub(r'\s+', ' ', snapshot['text']).strip()
    digest = hashlib.sha256(text.encode()).hexdigest()
    for change in review['offers']:
        offer = next(o for o in prop['offers'] if o['id'] == change['id'])
        if offer['source_id'] != source['id']:
            raise ValueError('Price correction refers to a different source.')
        if offer['amount'] not in (change['before'], change['after']):
            raise Conflict('A price has changed since this review; inspect the current source again.')
        quote = change['quote']
        numbers = re.findall(r'\d[\d,]*(?:\.\d+)?', quote)
        if quote not in text or not any(Decimal(n.replace(',', '')) == Decimal(change['after']) for n in numbers):
            raise ValueError('The reviewed source quote must support the corrected amount.')
        offer['amount'] = change['after']
        offer['evidence'] = [e for e in offer['evidence'] if e.get('review_id') != review_id]
        offer['evidence'].append(dict(field='amount', quote=quote, source_id=source['id'],
                                      source_hash=digest, reviewed_at=snapshot['retrieved_at'], review_id=review_id))
        if review.get('price_note') and review['price_note'] not in offer['unknowns']:
            offer['unknowns'].append(review['price_note'])
    source.update(checked_at=snapshot['retrieved_at'], reviewed_at=snapshot['retrieved_at'],
                  sha256=digest, review_status='reviewed', review_scope=snapshot['review_scope'])
    return prop, source, text


def review_seed(seed, manifest, snapshots):
    seed = deepcopy(seed)
    for review in manifest['sources']:
        prop = next(p for p in seed['properties'] if p['id'] == review['property_id'])
        source = next(s for s in prop['sources'] if s['id'] == review['source_id'])
        updated, source, _ = reviewed_property(prop, source, review, snapshots[source['id']], manifest['id'])
        updated['sources'] = [source if s['id'] == source['id'] else s for s in updated['sources']]
        seed['properties'][seed['properties'].index(prop)] = updated
    seed['price_review'] = manifest['id']
    return seed


def apply_price_review(store, manifest, snapshots):
    """One atomic catalog/source transaction; searches and frozen exports are untouched."""
    changed = []
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        for review in manifest['sources']:
            version_id = hashlib.sha256((manifest['id'] + ':' + review['source_id']).encode()).hexdigest()[:32]
            if db.execute('SELECT 1 FROM housing_source_versions WHERE id=?', (version_id,)).fetchone():
                continue
            raw = db.execute('SELECT body FROM housing_catalog WHERE id=?', (review['property_id'],)).fetchone()
            if not raw:
                raise ValueError('Reviewed property is missing from the catalog.')
            source = store.source(review['source_id'], db, True)
            previous_hash = source.get('sha256')
            prop, source, text = reviewed_property(json.loads(raw[0]), source, review,
                                                   snapshots[source['id']], manifest['id'])
            source.pop('text', None)
            prop['sources'] = [source if s['id'] == source['id'] else s for s in prop['sources']]
            db.execute('UPDATE housing_catalog SET body=? WHERE id=?', (json.dumps(prop), prop['id']))
            db.execute('UPDATE housing_sources SET body=?,text=? WHERE id=?', (json.dumps(source), text, source['id']))
            version = dict(id=version_id, source_id=source['id'], retrieved_at=source['checked_at'],
                           sha256=source['sha256'], previous_hash=previous_hash, changed=True,
                           origin='manual_browser_price_review', decision='reviewed_prices',
                           review_scope=source['review_scope'], review_id=manifest['id'])
            db.execute('INSERT INTO housing_source_versions VALUES (?,?,?,?)',
                       (version_id, source['id'], json.dumps(version), text))
            changed.extend(c['id'] for c in review['offers'])
    return changed
