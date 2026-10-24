import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools/training'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_training_prep_keeps_context_groups_disjoint_and_excludes_reviews(tmp_path):
    manifest=load('prepare_dataset').prepare(tmp_path)
    checked,splits=load('train_gemma').read_dataset(tmp_path)
    assert checked==manifest and manifest['raw_review_records_used']==0
    assert {k:len(v) for k,v in splits.items()}=={'train':192,'validation':24,'test':24}
    assert all(r['source_kind']=='authored_synthetic' for rows in splits.values() for r in rows)
    assert any(json.loads(row['messages'][-1]['content'])['evidence_ids'] for row in splits['train'])
