"""R0.3.2 / EXP-13 CLI. plan은 실행하지 않고 demo만 새 계산을 수행한다."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from . import codec
from .model import ContractError


def main(argv=None):
    parser=argparse.ArgumentParser(prog='hcr grounding', description='EXP-13: proof support / explicit abstention / conflict diagnostics')
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('plan',help='고정 조건 출력; 새 추론 없음')
    demo=commands.add_parser('demo',help='근거 진단 / dependency gate / blanket gate 비교')
    demo.add_argument('--out',type=Path,required=True)
    verify=commands.add_parser('verify',help='원시 기록 재집계·수치 검산; 새 추론 없음')
    verify.add_argument('--run',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='plan':
            from .evaluation.grounding_spec import condition_plan
            result=dict(state='planned',conditions=condition_plan(),inference_executed=False)
        elif args.command=='demo':
            from .evaluation.grounding_protocol import run_demo
            result=run_demo(args.out)
        else:
            from .evaluation.grounding_protocol import verify_run
            result=verify_run(args.run)
        print(codec.dumps(result));return 0
    except (ContractError,OSError,ValueError,KeyError,TypeError) as exc:
        print(codec.dumps(dict(state='failed',error=type(exc).__name__+': '+str(exc))),file=sys.stderr);return 2
