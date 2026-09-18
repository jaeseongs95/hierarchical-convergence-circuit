"""Explicit source-root selection before imports; root hcr.py cannot shadow src/hcr."""
from pathlib import Path
import argparse
import sys
root=Path(__file__).resolve().parents[1];sys.path[:0]=[str(root/'src'),str(root)]
from tools.r048_precision import io
from tools.r049_signal_boundary import pipeline,device


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','execute','analyze','verify-analysis','verify'])
    p.add_argument('--run',type=Path);a=p.parse_args()
    if a.action=='run':result=pipeline.run(root)
    else:
        if a.run is None:p.error('--run is required')
        run=io.safe(a.run)
        if a.action=='execute':
            plan=io.load(run/'plan.json');pipeline.validate_plan(plan);pipeline.check_source(run,plan);result=device.produce(plan,run)
        elif a.action=='analyze':result=pipeline.analyze(run)
        elif a.action=='verify-analysis':result=pipeline.analyze(run,True)
        else:result=pipeline.verify_bundle(run)
    print(io.encode(result).decode('utf-8'))
if __name__=='__main__':main()
