"""Publish exact synthetic datasets, experiment reports and learned LoRA adapters.

Never copy base weights, tokenizers, pickle checkpoints, reviews or workspaces.
"""
from hashlib import sha256
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
BASE='google/gemma-4-E4B-it'
REVISION='ee0ef6023621cff504d758262d4e04895a5af4a2'
RUNS=[('v1','roomwise-gemma-4-e4b-lora','roomwise-synthetic-v1'),
      ('v2','roomwise-gemma-4-e4b-lora-cont','roomwise-synthetic-v1'),
      ('v3','roomwise-gemma-4-e4b-lora-v3','roomwise-synthetic-v2')]


def publish(source, destination):
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    checked={}
    for split in ('train','validation','test'):
        content=(source/(split+'.jsonl')).read_bytes()
        rows=[json.loads(line) for line in content.decode('utf-8').splitlines() if line]
        if sha256(content).hexdigest()!=manifest['files'][split]['sha256'] or len(rows)!=manifest['files'][split]['records']:
            raise ValueError('Historical dataset hash/count mismatch: '+split)
        if any(r.get('source_kind')!='authored_synthetic' or r.get('license')!='MIT' for r in rows):
            raise ValueError('Only the authored MIT synthetic examples may be packaged.')
        checked[split]=content
    if manifest.get('raw_review_records_used')!=0:raise ValueError('Review data is excluded.')
    destination.mkdir(parents=True,exist_ok=True)
    for split,content in checked.items():(destination/(split+'.jsonl')).write_bytes(content)
    shutil.copyfile(source/'manifest.json',destination/'manifest.json')
    return manifest


def publish_adapter(source, destination, label, dataset, report):
    """Copy only safe tensor deltas and a portable PEFT config; record every hash."""
    if report['dataset_manifest']['files']!=dataset['files']:
        raise ValueError('Adapter training report does not match the packaged dataset.')
    weights=source/'adapter_model.safetensors'
    if not 0<weights.stat().st_size<100_000_000:
        raise ValueError('Expected a small LoRA adapter, not full base weights.')
    original=(source/'adapter_config.json').read_bytes()
    config=json.loads(original)
    if config.get('peft_type')!='LORA' or config.get('r')!=16:
        raise ValueError('Unexpected adapter format.')
    config['base_model_name_or_path']=BASE
    # v3 used a local directory: its declared revision was not independently resolved.
    config['revision']=report.get('base_revision')
    destination.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(weights,destination/weights.name)
    (destination/'adapter_config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    digest=sha256(weights.read_bytes()).hexdigest()
    if sha256((destination/weights.name).read_bytes()).hexdigest()!=digest:
        raise ValueError('Adapter copy hash mismatch.')
    manifest={'run':label,'selected_runtime':label=='v2','base_model':BASE,
        'recorded_base_revision':report.get('base_revision'),
        'declared_base_revision':report.get('declared_revision',REVISION),
        'revision_note':'v3 local base revision was declared, not independently verified.' if label=='v3' else 'Revision recorded by historical training report.',
        'dataset':f'../../data/training/{dataset["public_name"]}',
        'training_report':f'../../data/training/reports/{label}-training.json',
        'license':'Apache-2.0','weights_sha256':digest,'weights_bytes':weights.stat().st_size,
        'original_config_sha256':sha256(original).hexdigest(),
        'published_config_sha256':sha256((destination/'adapter_config.json').read_bytes()).hexdigest(),
        'config_changes':'Replaced local base path with Hub identity; recorded resolved revision (null for unverified v3). Tensor bytes unchanged.',
        'excluded':'Base weights, tokenizer copies, optimizer/checkpoints and pickle training_args.bin.'}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (destination/'README.md').write_text(f'''---
base_model: {BASE}
library_name: peft
license: apache-2.0
tags:
- lora
- roomwise
---
# Roomwise Gemma 4 E4B {label} LoRA adapter

{'Selected local runtime.' if label=='v2' else 'Historical experiment; not the selected runtime.'}
{'v3 regressed in generation evaluation; retain for transparency, not deployment.' if label=='v3' else ''}
This folder contains the actual learned tensor deltas, not the base model.
Load using PEFT with the separately obtained base model and its tokenizer.
See [the model card](../../docs/MODEL_CARD.md), [package instructions](../README.md),
[training report]({manifest['training_report']}) and manifest hashes.
Synthetic shared-template evaluation does not establish factual accuracy.
Apache-2.0 applies to this adapter; see [LICENSE](../LICENSE) and [NOTICE](../NOTICE).
''',encoding='utf-8')
    return manifest


def main():
    datasets={}
    for name in ('roomwise-synthetic-v1','roomwise-synthetic-v2'):
        datasets[name]=publish(ROOT/'var/training'/name,ROOT/'data/training'/name)
        datasets[name]['public_name']=name
    reports=ROOT/'data/training/reports';reports.mkdir(parents=True,exist_ok=True)
    for label,folder,name in RUNS:
        source=ROOT/'var/models'/folder
        report=json.loads((source/'training-report.json').read_text(encoding='utf-8'))
        shutil.copyfile(source/'training-report.json',reports/(label+'-training.json'))
        publish_adapter(source/'adapter',ROOT/'models'/('roomwise-gemma-4-e4b-'+label),label,datasets[name],report)
    for name in ('base-gemma4-e4b-evaluation.json','adapter-gemma4-e4b-evaluation.json',
                 'adapter-v2-gemma4-e4b-evaluation.json','adapter-v3-gemma4-e4b-evaluation.json'):
        path=ROOT/'var/training'/name
        if path.exists():shutil.copyfile(path,reports/name)
    for name,manifest in datasets.items():
        provenance={'actual_base_model':BASE,'recorded_or_declared_base_revision':REVISION,
            'manifest_note':'Original Gemma 3 label retained in v1; v1/v2 reports record Gemma 4. Dataset v2 was used by the v3 experiment with an unverified local base revision. Original data and manifests are byte-preserved.',
            'used_by_runs':['v1','v2'] if name.endswith('v1') else ['v3'],
            'runtime_alias':'roomwise-gemma-4-e4b-v2','dataset_total':sum(x['records'] for x in manifest['files'].values()),
            'raw_review_records_used':0,'base_weights_included':False,'lora_adapters_included':True,
            'adapter_package':'../../../models/README.md','base_model_card':'https://huggingface.co/'+BASE,
            'base_license':'Apache-2.0','base_license_url':'https://ai.google.dev/gemma/apache_2',
            'limitation':'Shared templates across splits; answer-kind scores are not factual accuracy. v3 regressed and is not selected.'}
        (ROOT/'data/training'/name/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    print('Packaged both 240-row synthetic dataset versions, three LoRA adapters and historical reports; excluded base weights and private data.')


if __name__=='__main__':main()
