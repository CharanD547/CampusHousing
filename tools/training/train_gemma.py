"""Optional isolated Gemma 3 text LoRA trainer. Default is a download-free preflight."""
import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def read_dataset(folder):
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    splits={}
    for split in ['train','validation','test']:
        content=(folder/(split+'.jsonl')).read_bytes()
        if sha256(content).hexdigest()!=manifest['files'][split]['sha256']:raise ValueError('Dataset hash mismatch.')
        splits[split]=[json.loads(line) for line in content.decode('utf-8').splitlines() if line.strip()]
    groups=[{r['group_id'] for r in splits[s]} for s in ['train','validation','test']]
    if any(groups[i]&groups[j] for i,j in [(0,1),(0,2),(1,2)]):raise ValueError('Context leakage across splits.')
    if any(r.get('source_kind')!='authored_synthetic' for rows in splits.values() for r in rows):
        raise ValueError('This starter recipe only permits its authored synthetic dataset. Curate licensed real data separately.')
    return manifest,splits


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,default=ROOT/'var/training/roomwise-synthetic-v1')
    parser.add_argument('--output',type=Path,default=ROOT/'var/models/roomwise-gemma-1b-lora')
    parser.add_argument('--model',default='google/gemma-3-1b-it')
    parser.add_argument('--revision',default='dcc83ea841ab6100d6b47a070329e1ba4cf78752')
    parser.add_argument('--train',action='store_true')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    manifest,splits=read_dataset(args.data)
    available={name:importlib.util.find_spec(name) is not None for name in ['torch','transformers','peft','datasets','accelerate']}
    report={'mode':'training' if args.train else 'preflight_only','base_model':args.model,
            'dependencies':available,'hf_token_present':bool(os.getenv('HF_TOKEN')),
            'examples':{k:len(v) for k,v in splits.items()},'weights_downloaded':False,'model_trained':False}
    if not args.train:
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2));return
    if not all(available.values()):raise RuntimeError('Install the optional training requirements in a separate environment.')
    if not args.model.startswith('google/gemma-3-1b-'):raise ValueError('Starter training recipe is tested structurally for the Gemma 3 1B text architecture only.')
    if args.output.exists():raise ValueError('Choose a new output directory; do not overwrite a previous adapter.')
    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, DataCollatorForSeq2Seq, Trainer, TrainingArguments
    if not torch.cuda.is_available():raise RuntimeError('A compatible CUDA-enabled PyTorch installation is required.')
    if not torch.cuda.is_bf16_supported():raise RuntimeError('This recipe requires BF16 support; select a compatible runtime.')
    tokenizer=AutoTokenizer.from_pretrained(args.model,revision=args.revision)
    if tokenizer.pad_token_id is None:tokenizer.pad_token=tokenizer.eos_token
    model=AutoModelForCausalLM.from_pretrained(args.model,revision=args.revision,torch_dtype=torch.bfloat16,attn_implementation='eager')
    resolved_revision=getattr(model.config,'_commit_hash',None)
    model=get_peft_model(model,LoraConfig(r=16,lora_alpha=32,lora_dropout=.05,bias='none',
        target_modules=['q_proj','k_proj','v_proj','o_proj'],task_type='CAUSAL_LM'))
    model.config.use_cache=False
    model.enable_input_require_grads()

    def encode(row):
        prompt=tokenizer.apply_chat_template(row['messages'][:-1],tokenize=False,add_generation_prompt=True)
        full=tokenizer.apply_chat_template(row['messages'],tokenize=False,add_generation_prompt=False)
        prompt_ids=tokenizer(prompt,add_special_tokens=False)['input_ids']
        ids=tokenizer(full,add_special_tokens=False)['input_ids']
        if len(ids)>1536 or len(prompt_ids)>=len(ids):raise ValueError('Example too long or incompatible chat template; inspect before training.')
        if ids[:len(prompt_ids)]!=prompt_ids:raise ValueError('Chat template prefix mismatch; do not train with incorrect label masking.')
        return {'input_ids':ids,'attention_mask':[1]*len(ids),'labels':[-100]*len(prompt_ids)+ids[len(prompt_ids):]}
    train=Dataset.from_list([encode(row) for row in splits['train']])
    validation=Dataset.from_list([encode(row) for row in splits['validation']])
    trainer=Trainer(model=model,processing_class=tokenizer,train_dataset=train,eval_dataset=validation,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer,label_pad_token_id=-100),
        args=TrainingArguments(output_dir=str(args.output),num_train_epochs=2,per_device_train_batch_size=1,
             per_device_eval_batch_size=1,gradient_accumulation_steps=8,gradient_checkpointing=True,
             learning_rate=2e-4,bf16=True,eval_strategy='epoch',save_strategy='epoch',save_total_limit=2,
             logging_steps=5,report_to=[],seed=42))
    before=trainer.evaluate();trainer.train();after=trainer.evaluate()
    trainer.save_model(str(args.output/'adapter'));tokenizer.save_pretrained(args.output/'adapter')
    report.update(weights_downloaded=True,model_trained=True,base_revision=resolved_revision,
        validation_before=before,validation_after=after,dataset_manifest=manifest,
        task_quality_status='not_established; held-out generation and baseline comparison still required',
        adapter_type='LoRA; base model weights remain separately licensed',
        packages={name:__import__(name).__version__ for name in ['torch','transformers','peft','datasets','accelerate']})
    (args.output/'training-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
