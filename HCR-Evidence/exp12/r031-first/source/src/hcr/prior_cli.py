"""R0.3.1 / EXP-12 CLI. plan은 실행하지 않고 demo만 새 계산을 수행한다."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from . import codec
from .model import ContractError


def main(argv=None):
    parser=argparse.ArgumentParser(prog='hcr priors', description='EXP-12: routing prior / judgment prior scope')
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('plan',help='고정 조건 출력; 새 추론 없음')
    demo=commands.add_parser('demo',help='score sweep / 고정 network / 보존 과제 실행')
    demo.add_argument('--out',type=Path,required=True)
    verify=commands.add_parser('verify',help='원시 기록 재집계·수치 검산; 새 추론 없음')
    verify.add_argument('--run',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='plan':
            from .evaluation.prior_spec import condition_plan
            result=dict(state='planned',conditions=condition_plan(),inference_executed=False)
        elif args.command=='demo':
            from .evaluation.prior_protocol import run_demo
            result=run_demo(args.out)
        else:
            from .evaluation.prior_protocol import verify_run
            result=verify_run(args.run)
        print(codec.dumps(result));return 0
    except (ContractError,OSError,ValueError,KeyError,TypeError) as exc:
        print(codec.dumps(dict(state='failed',error=type(exc).__name__+': '+str(exc))),file=sys.stderr);return 2
