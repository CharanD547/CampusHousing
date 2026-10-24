"""Bounded JSON inference transport for hosted Google models or an owner-configured server."""
import json
import re
import time
from urllib.parse import urlsplit

import httpx


class JSONModel:
    def __init__(self, settings, transport=None):
        self.settings=settings
        self.provider=settings.ai_provider
        self.model_id=settings.ai_model or None
        self.transport=transport

    @property
    def configured(self):
        return bool(self.model_id and self.provider in ('google','openai_compatible') and
                    (self.provider!='google' or self.settings.ai_api_key))

    def generate(self, prompt, schema):
        if not self.configured or not self.settings.external_operations_enabled:
            raise ValueError('Model is disabled or unconfigured.')
        prompt=prompt+'\nReturn exactly one JSON object matching this schema:\n'+json.dumps(schema)
        if len(prompt)>100000: raise ValueError('Context exceeds inference limit.')
        headers={'Content-Type':'application/json'}
        if self.provider=='google':
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}',self.model_id): raise ValueError('Invalid Google model ID.')
            url='https://generativelanguage.googleapis.com/v1beta/models/'+self.model_id+':generateContent'
            headers['x-goog-api-key']=self.settings.ai_api_key
            payload={'contents':[{'role':'user','parts':[{'text':prompt}]}],
                     'generationConfig':{'temperature':0,'maxOutputTokens':1800}}
            if self.model_id.startswith('gemini-'):
                payload['generationConfig'].update(responseMimeType='application/json',responseJsonSchema=schema)
        else:
            base=self.settings.ai_base_url.rstrip('/')
            parsed=urlsplit(base)
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError('Use a clean owner-configured inference URL.')
            if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('localhost','127.0.0.1','::1')):
                raise ValueError('Inference requires HTTPS or a loopback HTTP server.')
            url=base+'/chat/completions'
            if self.settings.ai_api_key:headers['Authorization']='Bearer '+self.settings.ai_api_key
            payload={'model':self.model_id,'messages':[{'role':'user','content':prompt}],
                     'temperature':0,'max_tokens':1800,'response_format':{'type':'json_object'}}
        started=time.monotonic()
        with httpx.Client(timeout=httpx.Timeout(25,connect=5),follow_redirects=False,transport=self.transport) as client:
            with client.stream('POST',url,headers=headers,json=payload) as response:
                response.raise_for_status()
                content=bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content)>128000 or time.monotonic()-started>30:raise ValueError('Inference response exceeded limits.')
        data=json.loads(content)
        if self.provider=='google':
            returned=data.get('modelVersion','')
            if returned and not returned.startswith(self.model_id):raise ValueError('Unexpected Google model identity.')
            raw=''.join(p.get('text','') for p in data['candidates'][0]['content']['parts'] if not p.get('thought'))
        else:
            if data.get('model')!=self.model_id:raise ValueError('Unexpected model identity.')
            raw=data['choices'][0]['message']['content']
        # A complete JSON fence is tolerated, arbitrary embedded/trailing prose is not.
        raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip())
        return json.loads(raw)
