"""EXP20 단계별 CLI. 기존 파일/실패 실행을 덮어쓰지 않는다."""
from __future__ import annotations
import argparse
import json
import zipfile
from r037_online_selection import io
from .contracts import require


def main(argv=None):
    p = argparse.ArgumentParser(description='R039 / EXP20 proof 채택 시점 실험')
    sub = p.add_subparsers(dest='command',required=True)
    q = sub.add_parser('prepare'); q.add_argument('--source-run',required=True); q.add_argument('--out',required=True)
    q = sub.add_parser('execute'); q.add_argument('--plan',required=True); q.add_argument('--out',required=True); q.add_argument('--source-run')
    for command in ('audit','verify'):
        q = sub.add_parser(command); q.add_argument('--run',required=True)
    q = sub.add_parser('bundle'); q.add_argument('--run',required=True); q.add_argument('--out',required=True)
    args = p.parse_args(argv)
    if args.command == 'prepare':
        from .protocol import prepare
        result = prepare(args.source_run,args.out)
    elif args.command == 'execute':
        from .protocol import execute
        result = execute(io.load(args.plan),args.out,args.source_run)
    elif args.command in ('audit','verify'):
        from .audit import write_analysis
        result = write_analysis(args.run,check_only=args.command == 'verify')
    else:
        root,target = io.safe(args.run),io.safe(args.out)
        io.disjoint(root,target)
        require(root.is_dir() and not target.exists(), '원본 폴더 필요/기존 ZIP 덮어쓰기 금지')
        names = io.inventory(root)
        require('manifest.json' in names or 'failure.json' in names,'실험 원자료 또는 실패 원문이 필요합니다.')
        target.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for name in sorted(names): z.write(io.child(root,name),name)
        result = dict(bundle=str(target),sha256=io.file_hash(target),files=len(names),
                      contains_failed_run='failure.json' in names)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True,allow_nan=False))
    return 0
