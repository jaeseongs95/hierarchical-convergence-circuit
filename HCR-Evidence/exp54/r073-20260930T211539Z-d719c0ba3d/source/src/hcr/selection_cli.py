"""R0.3.4 EXP-15 실행 명령. 기존 hcr.py CLI를 변경하지 않는다."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import traceback


def main(argv=None):
    from . import selection_io as sio
    from .evaluation.selection_protocol import make_plan,generate,write_analysis
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    prepare=sub.add_parser('prepare',help='조건과 실행 소스 해시를 동결한다')
    prepare.add_argument('--out',type=Path,required=True)
    execute=sub.add_parser('execute',help='raw만 생성한다. 독립 검산은 별도 명령이다')
    execute.add_argument('--plan',type=Path,required=True);execute.add_argument('--out',type=Path,required=True)
    for name in ('audit','verify'):
        q=sub.add_parser(name);q.add_argument('--run',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        if a.command=='prepare':
            plan=make_plan();sio.put(a.out,plan)
            result=dict(prepared=True,path=str(a.out),protocol=plan['conditions']['protocol'])
        elif a.command=='execute':result=generate(a.out,sio.load(a.plan))
        else:result=write_analysis(a.run,check_only=a.command=='verify')
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except Exception as exc:
        if a.command in ('audit','verify') and a.run.is_dir():
            try:
                stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
                sio.put(a.run/'audit_failures'/(stamp+'.json'),dict(command=a.command,error_type=type(exc).__name__,
                    error=str(exc),traceback=traceback.format_exc(),raw_modified=False,automatic_retry=False))
            except Exception as report_error:print('검산 실패 기록 오류: '+str(report_error),file=sys.stderr)
        print(type(exc).__name__+': '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
