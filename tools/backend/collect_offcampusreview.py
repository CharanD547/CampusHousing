"""Collect all discoverable public OCR review pages into a local SQLite research DB."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from roomwise.adapters.offcampusreview import PublicReviewCollector
from roomwise.repositories.reviews import ReviewRepository

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,default=ROOT/'var/offcampusreview.sqlite3')
    parser.add_argument('--max-pages',type=int,default=1500)
    args=parser.parse_args()
    repo=ReviewRepository(args.database)
    result=asyncio.run(PublicReviewCollector(repo,max_pages=args.max_pages).run())
    report=args.database.with_suffix('.collection.json')
    report.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)
