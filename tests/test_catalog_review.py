import json
from pathlib import Path
import pytest
from roomwise.domain.costs import Conflict
from roomwise.repositories.catalog import CatalogRepository
from roomwise.repositories.workspace import WorkspaceStore
from roomwise.services.catalog_review import apply_price_review

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    return (json.loads((ROOT/'data/housing-price-review.json').read_text(encoding='utf-8')),
            json.loads((ROOT/'data/housing-source-snapshots.json').read_text(encoding='utf-8')))


def amounts(store): return {o['id']:o['amount'] for p in store.catalog() for o in p['offers']}


def old_catalog(store):
    manifest,snapshots=inputs()
    with store.connect() as db:
        for review in manifest['sources']:
            prop=json.loads(db.execute('SELECT body FROM housing_catalog WHERE id=?',(review['property_id'],)).fetchone()[0])
            for change in review['offers']:next(o for o in prop['offers'] if o['id']==change['id'])['amount']=change['before']
            db.execute('UPDATE housing_catalog SET body=? WHERE id=?',(json.dumps(prop),prop['id']))
            # Roll the source back to before the manifest's snapshot so the review applies to older evidence.
            source=json.loads(db.execute('SELECT body FROM housing_sources WHERE id=?',(review['source_id'],)).fetchone()[0])
            source.update(checked_at='2026-10-15T16:00:00+00:00',review_status='reviewed',
                          url=snapshots[review['source_id']]['url'])
            db.execute('UPDATE housing_sources SET body=? WHERE id=?',(json.dumps(source),review['source_id']))


def test_review_preserves_frozen_brief_and_is_idempotent(tmp_path):
    catalog=CatalogRepository(tmp_path);old_catalog(catalog);workspaces=WorkspaceStore(tmp_path)
    brief=workspaces.save_brief({'comparison_id':'old','request_id':'same'},{'catalog':catalog.catalog()})
    manifest,snapshots=inputs()
    assert len(apply_price_review(catalog,manifest,snapshots))==6
    assert amounts(catalog)['alight-east']=='835' and amounts(catalog)['union-c1']=='1340'
    assert workspaces.get('briefs',brief['id'])==brief
    assert apply_price_review(catalog,manifest,snapshots)==[]


@pytest.mark.parametrize('failure',['quote','price','newer_review'])
def test_invalid_review_rolls_back_all_changes(tmp_path,failure):
    catalog=CatalogRepository(tmp_path);old_catalog(catalog);manifest,snapshots=inputs()
    if failure=='quote':manifest['sources'][1]['offers'][-1]['quote']='Invented $1340 quote'
    elif failure=='price':
        with catalog.connect() as db:
            prop=json.loads(db.execute("SELECT body FROM housing_catalog WHERE id='union'").fetchone()[0])
            next(o for o in prop['offers'] if o['id']=='union-c1')['amount']='1500'
            db.execute("UPDATE housing_catalog SET body=? WHERE id='union'",(json.dumps(prop),))
    else:
        with catalog.connect() as db:
            source=catalog.source('union-plans',db);source['checked_at']='2026-10-25T12:00:00+00:00'
            db.execute("UPDATE housing_sources SET body=? WHERE id='union-plans'",(json.dumps(source),))
    before=amounts(catalog)
    with pytest.raises((ValueError,Conflict)):apply_price_review(catalog,manifest,snapshots)
    assert amounts(catalog)==before
