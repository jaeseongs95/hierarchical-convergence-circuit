"""EXP29 command entry; explicit source root avoids root hcr.py import shadowing."""
from pathlib import Path
import argparse
import json
import sys
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'src'),str(root)]
from tools.r048_precision import pipeline,io

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','execute','analyze','verify-analysis','verify'])
    p.add_argument('--run',type=Path);p.add_argument('--repo',type=Path,default=root);a=p.parse_args()
    if a.action=='run':result=pipeline.run(a.repo)
    else:
        if a.run is None:p.error('--run is required')
        run=io.safe(a.run)
        if a.action=='execute':
            from tools.r048_precision.device import execute
            plan=io.load(run/'plan.json');pipeline.validate_plan(plan);pipeline.check_source(run,plan)
            result=execute(plan,run)
        elif a.action=='analyze':result=pipeline.analyze(run)
        elif a.action=='verify-analysis':result=pipeline.analyze(run,verify=True)
        else:result=pipeline.verify_bundle(run)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
