from __future__ import annotations
import argparse
from pathlib import Path
from . import storage as io


def main(argv=None):
    p=argparse.ArgumentParser(description='EXP27: explicit sequential thought carry on pinned native HCR core')
    sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('prepare');x.add_argument('--source-run',type=Path,required=True);x.add_argument('--out',type=Path,required=True)
    x=sub.add_parser('execute');x.add_argument('--plan',type=Path,required=True);x.add_argument('--out',type=Path,required=True)
    for command in ('audit','verify'):
        x=sub.add_parser(command);x.add_argument('--run',type=Path,required=True)
    x=sub.add_parser('regression');x.add_argument('--source-run',type=Path,required=True);x.add_argument('--out',type=Path,required=True)
    args=p.parse_args(argv)
    if args.command=='prepare':
        from .protocol import prepare
        result=prepare(args.source_run,args.out)
    elif args.command=='execute':
        from .protocol import execute
        result=execute(args.plan,args.out)
    elif args.command in ('audit','verify'):
        from .protocol import analyze
        result=analyze(args.run,verify=args.command=='verify')
    else:
        from .regression import native_regression
        result=native_regression(args.source_run,args.out)
    print(io.canonical(result).decode('utf-8'),flush=True);return 0

if __name__=='__main__':raise SystemExit(main())
