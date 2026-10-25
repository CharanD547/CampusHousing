from copy import deepcopy
import json

from roomwise.config import ROOT
from roomwise.repositories.catalog import CatalogRepository
from roomwise.services.guide_catalog import guide_properties
from tools.backend.audit_rent_sources import amount_present
from tools.backend.sync_catalog import sync_catalog


def test_amount_screen_matches_currency_without_matching_a_different_amount():
    assert amount_present('Rent $1,950.00 per month', 1950)
    assert amount_present('Rent $1950 per month', 1950)
    assert not amount_present('Rent $11,950.00 or $1,950.79', 1950)


def test_sources_refresh_even_when_property_body_has_not_changed(tmp_path):
    repo = CatalogRepository(tmp_path)
    prop = deepcopy(repo.catalog()[0])
    for source in prop['sources']:
        source.pop('rent_recheck', None)
    # Keep the property unchanged while its normalized evidence row is stale.
    with repo.connect() as db:
        source = deepcopy(prop['sources'][0])
        source['title'] = 'Stale evidence title'
        db.execute('UPDATE housing_sources SET body=? WHERE id=?', (json.dumps(source), source['id']))
    sync_catalog(repo, {'properties':[prop]}, {}, True)
    assert repo.source(source['id'])['title'] == prop['sources'][0]['title']


def test_guide_ranges_and_multi_building_price_sources_survive_public_catalog():
    guide = json.loads((ROOT/'data/housing-guide.json').read_text(encoding='utf-8'))
    props = guide_properties(guide)
    town = next(p for p in props if p['id']=='knollwood-townhomes')
    group = next(o for o in town['offers'] if '245 /' in o['name'])
    assert float(group['advertised_range']['maximum']) == 2500
    assert group['bedrooms'] is None
    downtown = next(p for p in props if p['id']=='downtown-boutique-historic-rentals')
    for offer in downtown['offers']:
        source = next(s for s in downtown['sources'] if s['id']==offer['source_id'])
        if 'Houston' in offer['name']:
            assert 'houstonst.prospectportal.com' in source['url']
        else:
            assert '703-clay-street' in source['url']
