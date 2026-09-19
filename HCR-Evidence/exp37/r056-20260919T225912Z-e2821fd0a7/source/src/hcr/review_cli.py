"""R0.3.3 근거 기반 재검토 실험 CLI."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from . import codec,session_io
from .model import ContractError


def main(argv=None):
    p=argparse.ArgumentParser(prog='hcr review',description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    demo=sub.add_parser('demo',help='EXP-14: 계획 저장 뒤 개발 실험 실행')
    demo.add_argument('--out',type=Path,required=True)
    demo.add_argument('--training-counts',type=int,nargs='+',default=[6])
    plan=sub.add_parser('plan',help='추론 없이 source/조건을 동결')
    plan.add_argument('--out',type=Path,required=True)
    plan.add_argument('--training-counts',type=int,nargs='+',default=[6])
    exe=sub.add_parser('execute',help='동결 계획과 같은 source에서 실행')
    exe.add_argument('--plan',type=Path,required=True);exe.add_argument('--out',type=Path,required=True)
    check=sub.add_parser('verify',help='재추론 없이 원시 상태·행동·관측·집계 재검산')
    check.add_argument('--run',type=Path,required=True)
    a=p.parse_args(argv)
    from .evaluation.review_protocol import run_demo,verify_run,make_plan,validate_plan
    try:
        if a.command=='plan':
            out=session_io.new_output(a.out);doc=make_plan(a.training_counts);codec.save(out,doc)
            result=dict(state='prepared',plan=str(out),new_inferences=0)
        elif a.command=='verify':result=verify_run(a.run)
        elif a.command=='execute':
            doc=codec.loads(session_io.read_bytes(a.plan));validate_plan(doc)
            session_io.new_output(a.out,inputs=(a.plan,))
            result=run_demo(a.out,plan=doc)
        else:result=run_demo(a.out,a.training_counts)
        print(codec.dumps(result));return 0
    except (ContractError,ValueError,OSError) as e:
        print(type(e).__name__+': '+str(e),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
