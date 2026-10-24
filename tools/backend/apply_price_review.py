"""Apply the bundled manual price review to an existing catalog. No provider calls."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from roomwise.services.catalog_review import apply_price_review
from roomwise.repositories.catalog import CatalogRepository


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'var')
    args = parser.parse_args()
    snapshots = json.loads((ROOT / 'data/housing-source-snapshots.json').read_text(encoding='utf-8'))
    changed=[]
    store=CatalogRepository(args.data_dir)
    for filename in ('housing-price-review.json','housing-price-recheck-mill.json'):
        manifest=json.loads((ROOT/'data'/filename).read_text(encoding='utf-8'))
        changed.extend(apply_price_review(store,manifest,snapshots))
    print('Reviewed catalog offers:', ', '.join(changed) if changed else 'already applied')
    print('Saved searches and immutable decision briefs were preserved.')
