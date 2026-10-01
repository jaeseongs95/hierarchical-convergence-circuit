"""R0.3 입출력 연결. 기존 hcr.py / session CLI를 대체하지 않는다."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from . import codec, session_io
from .model import ContractError


def main(argv=None):
    parser=argparse.ArgumentParser(prog='hcr methods')
    sub=parser.add_subparsers(dest='command',required=True)
    demo=sub.add_parser('demo',help='EXP-11 동결 조건 실행 및 검산')
    demo.add_argument('--out',required=True,type=Path)
    demo.add_argument('--first-method',choices=('sequential','associative'),default='associative')
    verify=sub.add_parser('verify',help='완료 EXP-11의 원시 상태·메시지·예산 재검산')
    verify.add_argument('--run',required=True,type=Path)
    infer=sub.add_parser('infer',help='공개 관측만 사용; 외부 정답 평가 없음')
    infer.add_argument('--input',required=True,type=Path)
    infer.add_argument('--memory',type=Path)
    infer.add_argument('--out',required=True,type=Path)
    infer.add_argument('--arm',choices=('sequential','associative','fixed','adaptive','fixed_no_messages','adaptive_no_messages'),default='adaptive')
    infer.add_argument('--max-advances',type=int,default=12)
    infer.add_argument('--max-kernel-ticks',type=int,default=2048)
    args=parser.parse_args(argv)
    try:
        if args.command=='demo':
            from .evaluation.method_protocol import run_demo
            result=run_demo(args.out,first_method=args.first_method)
        elif args.command=='verify':
            from .evaluation.method_protocol import verify_run
            result=verify_run(args.run)
        else:
            from .methods import MethodEngine,MethodConfig
            from .model import AdaptiveConfig
            from .circuits import AdaptiveMemory
            config=AdaptiveConfig()
            out=session_io.new_output(args.out,inputs=[args.input]+([args.memory] if args.memory else []))
            obs=codec.observation_from(codec.loads(session_io.read_bytes(args.input)))
            memory=AdaptiveMemory.load(args.memory,config) if args.memory else None
            record=MethodEngine(config,memory,MethodConfig(max_advances=args.max_advances,max_kernel_ticks=args.max_kernel_ticks)).infer(obs,arm=args.arm)
            codec.save(out,record)
            result=dict(state='complete',output=str(out),result=record['result'],budget=record['budget'])
        print(codec.dumps(result));return 0
    except (ContractError, OSError, ValueError) as exc:
        print(codec.dumps(dict(state='failed',error=type(exc).__name__+': '+str(exc))),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
