"""Optional isolated Gemma 4 E4B text LoRA trainer. Default is a download-free preflight."""
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
    parser.add_argument('--output',type=Path,default=ROOT/'var/models/roomwise-gemma-4-e4b-lora-new')
    parser.add_argument('--model',default='google/gemma-4-E4B-it')
    parser.add_argument('--revision',default='ee0ef6023621cff504d758262d4e04895a5af4a2')
    parser.add_argument('--train',action='store_true')
    parser.add_argument('--report',type=Path)
    parser.add_argument('--init-adapter',type=Path,help='Continue training an existing LoRA adapter instead of starting from the base weights.')
    parser.add_argument('--epochs',type=float,default=2)
    parser.add_argument('--learning-rate',type=float,default=2e-4)
    args=parser.parse_args()
    if args.epochs<=0 or not 0<args.learning_rate<1:parser.error('Use positive epochs and a learning rate between zero and one.')
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
    local_model=Path(args.model).is_dir()
    if not local_model and args.model!='google/gemma-4-E4B-it':raise ValueError('Training recipe is tested for google/gemma-4-E4B-it (or a local copy of it) only.')
    if args.output.exists():raise ValueError('Choose a new output directory; do not overwrite a previous adapter.')
    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, DataCollatorForSeq2Seq, Trainer, TrainingArguments
    if not torch.cuda.is_available():raise RuntimeError('A compatible CUDA-enabled PyTorch installation is required.')
    if not torch.cuda.is_bf16_supported():raise RuntimeError('This recipe requires BF16 support; select a compatible runtime.')
    revision=None if local_model else args.revision
    tokenizer=AutoTokenizer.from_pretrained(args.model,revision=revision)
    if tokenizer.pad_token_id is None:tokenizer.pad_token=tokenizer.eos_token
    model=AutoModelForCausalLM.from_pretrained(args.model,revision=revision,dtype=torch.bfloat16,attn_implementation='eager')
    if getattr(model.config,'model_type',None)!='gemma4':raise ValueError('Local weights must use the Gemma 4 architecture.')
    resolved_revision=getattr(model.config,'_commit_hash',None)
    # Text-decoder projections only: Gemma 4 also has vision/audio towers with similarly named linears.
    if args.init_adapter:
        from peft import PeftModel
        model=PeftModel.from_pretrained(model,str(args.init_adapter),is_trainable=True)
    else:
        model=get_peft_model(model,LoraConfig(r=16,lora_alpha=32,lora_dropout=.05,bias='none',
            target_modules=r'.*language_model.*\.(q_proj|k_proj|v_proj|o_proj)',task_type='CAUSAL_LM'))
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
        args=TrainingArguments(output_dir=str(args.output),num_train_epochs=args.epochs,per_device_train_batch_size=1,
             per_device_eval_batch_size=1,gradient_accumulation_steps=8,gradient_checkpointing=True,
             learning_rate=args.learning_rate,bf16=True,eval_strategy='epoch',save_strategy='epoch',save_total_limit=2,
             logging_steps=5,report_to=[],seed=42))
    before=trainer.evaluate();trainer.train();after=trainer.evaluate()
    trainer.save_model(str(args.output/'adapter'));tokenizer.save_pretrained(args.output/'adapter')
    report.update(weights_downloaded=not local_model,local_weights_used=local_model,model_trained=True,base_revision=resolved_revision,
        declared_revision=args.revision,revision_verification='Hub-resolved' if resolved_revision else 'Local directory; supplied revision is not independently verified',
        init_adapter=str(args.init_adapter) if args.init_adapter else None,epochs=args.epochs,learning_rate=args.learning_rate,
        validation_before=before,validation_after=after,dataset_manifest=manifest,
        task_quality_status='not_established; held-out generation and baseline comparison still required',
        adapter_type='LoRA; base model weights remain separately licensed',
        packages={name:__import__(name).__version__ for name in ['torch','transformers','peft','datasets','accelerate']})
    (args.output/'training-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
