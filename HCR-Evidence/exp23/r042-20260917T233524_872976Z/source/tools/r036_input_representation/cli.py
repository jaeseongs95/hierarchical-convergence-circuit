"""EXP-17 prepare/execute/audit/verify CLI."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from r035_frozen_selection import storage as io


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('prepare');a.add_argument('--source-run',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    a=s.add_parser('execute');a.add_argument('--plan',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    a.add_argument('--source-run',type=Path)
    for cmd in ('audit','verify'):
        a=s.add_parser(cmd);a.add_argument('--run',type=Path,required=True)
    args=p.parse_args(argv)
    if sys.version_info<(3,12):p.error('Python 3.12 이상 필요')
    try:
        if args.command=='prepare':
            from .protocol import prepare
            result=prepare(args.source_run,args.out)
        elif args.command=='execute':
            from .protocol import generate
            result=generate(io.load(args.plan),args.out,args.source_run)
        else:
            from .verification import write_analysis
            result=write_analysis(args.run,check_only=args.command=='verify')
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,KeyError,TypeError,OSError,RuntimeError) as exc:
        print(type(exc).__name__+': '+str(exc),file=sys.stderr);return 2
