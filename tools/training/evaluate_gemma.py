"""Check held-out target format, or explicitly measure generations from a local model server."""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from roomwise.adapters.model import JSONModel
from roomwise.api.schemas import AssistantAnswer
from roomwise.config import Settings
from train_gemma import read_dataset


def score(result,row):
    answer=AssistantAnswer.model_validate(result)
    citations=set(answer.evidence_ids)<=set(row['allowed_evidence_ids'])
    candidates=set(answer.candidate_ids)<=set(row['allowed_candidate_ids'])
    if answer.answer_kind=='evidence':citations=citations and bool(answer.evidence_ids) and bool(answer.candidate_ids)
    expected=json.loads(row['messages'][-1]['content'])
    return {'schema_valid':True,'citations_valid':citations and candidates,
            'answer_kind_correct':answer.answer_kind==expected['answer_kind']}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,default=ROOT/'var/training/roomwise-synthetic-v1')
    parser.add_argument('--base-url',default='http://127.0.0.1:8002/v1')
    parser.add_argument('--model',default='roomwise-gemma-1b')
    parser.add_argument('--output',type=Path,default=ROOT/'var/training/evaluation-preflight.json')
    parser.add_argument('--generate',action='store_true')
    args=parser.parse_args();manifest,splits=read_dataset(args.data)
    parsed=urlsplit(args.base_url)
    if parsed.hostname not in ('localhost','127.0.0.1','::1') or parsed.scheme!='http':
        parser.error('This evaluation command only contacts a loopback HTTP model server.')
    model=JSONModel(Settings(ROOT/'var',external_operations_enabled=True,ai_provider='openai_compatible',
        ai_model=args.model,ai_base_url=args.base_url))
    results=[]
    for row in splits['test']:
        try:
            output=model.generate(row['messages'][0]['content'],AssistantAnswer.model_json_schema()) if args.generate else json.loads(row['messages'][-1]['content'])
            metrics=score(output,row)
        except Exception:
            metrics={'schema_valid':False,'citations_valid':False,'answer_kind_correct':False}
        results.append({'id':row['id'],'family':row['family'],**metrics})
    report={'mode':'actual_generation' if args.generate else 'target_data_check_only',
            'model_id':args.model if args.generate else None,'inference_performed':args.generate,
            'test_file_sha256':manifest['files']['test']['sha256'],'examples':len(results),
            'metrics':{key:sum(r[key] for r in results)/len(results) for key in ['schema_valid','citations_valid','answer_kind_correct']},
            'results':results,'limitation':'Shared-template synthetic cases. These checks do not measure factual accuracy or prove real-world quality.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))


if __name__=='__main__':main()
