"""Loopback-only serving of already-downloaded Gemma weights and an optional local LoRA adapter."""
import argparse
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal


class Message(BaseModel):
    role: Literal['user']
    content: str = Field(min_length=1,max_length=100000)


class ChatRequest(BaseModel):
    model: str
    messages: list[Message] = Field(min_length=1,max_length=1)
    max_tokens: int = Field(default=1200,ge=1,le=1800)
    temperature: float = 0
    response_format: dict | None = None


def create_server(model_path,adapter_path=None,alias='roomwise-gemma-1b'):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    if not torch.cuda.is_available():raise RuntimeError('A compatible CUDA-enabled PyTorch installation is required.')
    tokenizer=AutoTokenizer.from_pretrained(str(model_path),local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(str(model_path),local_files_only=True,
        torch_dtype=torch.bfloat16,attn_implementation='eager').to('cuda')
    if adapter_path:
        from peft import PeftModel
        model=PeftModel.from_pretrained(model,str(adapter_path),local_files_only=True)
    model.eval();gate=BoundedSemaphore(1)
    app=FastAPI(title='Roomwise Local Gemma',docs_url=None,redoc_url=None)

    @app.get('/health')
    def health():return {'model':alias,'adapter_loaded':bool(adapter_path),'inference_verified':False,
                         'scope':'Loaded local weights; generation quality is not established by health.'}

    @app.post('/v1/chat/completions')
    def complete(body:ChatRequest):
        if body.model!=alias:raise HTTPException(400,'Choose the configured local model alias.')
        if not gate.acquire(blocking=False):raise HTTPException(429,'A local inference request is already running.')
        try:
            inputs=tokenizer.apply_chat_template([m.model_dump() for m in body.messages],add_generation_prompt=True,
                tokenize=True,return_tensors='pt',return_dict=True).to('cuda')
            length=inputs['input_ids'].shape[-1]
            if length>8192:raise HTTPException(413,'Context exceeds the local token limit.')
            with torch.inference_mode():
                generated=model.generate(**inputs,max_new_tokens=body.max_tokens,max_time=20,do_sample=False,
                    pad_token_id=tokenizer.eos_token_id)
            answer=tokenizer.decode(generated[0][length:],skip_special_tokens=True)
            return {'model':alias,'choices':[{'message':{'role':'assistant','content':answer}}],
                    'usage':{'prompt_tokens':length,'completion_tokens':generated.shape[-1]-length}}
        finally:gate.release()

    return app


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',type=Path,required=True,help='Local downloaded base-model directory; no Hub download occurs.')
    parser.add_argument('--adapter',type=Path)
    parser.add_argument('--alias',default='roomwise-gemma-1b')
    parser.add_argument('--port',type=int,default=8002)
    args=parser.parse_args()
    if not args.model.is_dir() or (args.adapter and not args.adapter.is_dir()):parser.error('Supply existing local model/adapter directories.')
    import uvicorn
    uvicorn.run(create_server(args.model,args.adapter,args.alias),host='127.0.0.1',port=args.port,workers=1)
