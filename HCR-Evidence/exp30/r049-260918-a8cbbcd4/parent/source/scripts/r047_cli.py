"""R047 entrypoint; also runnable from an immutable bundle's source snapshot."""
from pathlib import Path
import argparse
import sys
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'src'),str(root)]
from tools.r047_state_ablation import protocol

def main():
    p=argparse.ArgumentParser(description='HCR R047 / EXP28 state component ablation')
    sub=p.add_subparsers(dest='action',required=True)
    r=sub.add_parser('run');r.add_argument('--repo',type=Path,default=root)
    v=sub.add_parser('verify');v.add_argument('--run',type=Path,required=True)
    sub.add_parser('regression')
    a=p.parse_args()
    if a.action=='run': result=protocol.pipeline(a.repo)
    elif a.action=='verify':
        result=protocol.analyze(a.run,verify=True);protocol.verify_bundle_files(a.run)
    else:
        from tools.r047_state_ablation.regression import run_reference
        result=run_reference()
    import json
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
