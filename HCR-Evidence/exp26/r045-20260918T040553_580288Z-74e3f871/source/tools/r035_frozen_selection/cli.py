"""EXP-16 prepare → execute → audit → verify.각 명령은 별도 프로세스로 실행한다."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from . import storage as io


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('prepare');x.add_argument('--source-run',type=Path,required=True);x.add_argument('--out',type=Path,required=True)
    x=sub.add_parser('execute');x.add_argument('--plan',type=Path,required=True);x.add_argument('--out',type=Path,required=True);x.add_argument('--source-run',type=Path)
    for name in ('audit','verify'):
        x=sub.add_parser(name);x.add_argument('--run',type=Path,required=True);x.add_argument('--source-run',type=Path)
    a=p.parse_args(argv)
    try:
        if a.command=='prepare':
            from .protocol import prepare
            result=prepare(a.source_run,a.out)
        elif a.command=='execute':
            from .protocol import generate
            result=generate(io.load(a.plan),a.out,a.source_run)
        else:
            from .verification import write_analysis
            result=write_analysis(a.run,a.source_run,check_only=a.command=='verify')
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError,ImportError) as exc:
        print(f'{type(exc).__name__}: {exc}',file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
