"""별도 prepare/execute/audit/verify/bundle CLI. 불완전 run도 forensic bundle로 보존한다."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import zipfile
from . import storage as io
from .storage import require


def bundle(run, out):
    root,target = io.safe(run),io.safe(out)
    require(root.is_dir(), 'run 폴더가 없습니다.')
    io.disjoint(root,target)
    require(not target.exists(), '기존 ZIP 덮어쓰기 금지')
    names = sorted(io.inventory(root))
    require(names, '빈 run은 bundle할 수 없습니다.')
    target.parent.mkdir(parents=True,exist_ok=True)
    before = {n:io.file_hash(root/n) for n in names}
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in names: archive.write(root/name,root.name+'/'+name)
    require(before == {n:io.file_hash(root/n) for n in sorted(io.inventory(root))}, 'bundle 도중 evidence 변경')
    with zipfile.ZipFile(target) as archive:
        require(archive.testzip() is None, 'ZIP CRC 오류')
        require(set(archive.namelist()) == {root.name+'/'+n for n in names}, 'ZIP inventory')
        for name,h in before.items():
            require(io.bytes_hash(archive.read(root.name+'/'+name)) == h, 'ZIP content checksum')
    return dict(bundle=str(target),files=len(names),sha256=io.file_hash(target),
                complete_raw=(root/'manifest.json').is_file(),analysis_present=(root/'analysis/manifest.json').is_file())


def main(argv=None):
    parser = argparse.ArgumentParser(description='EXP25 / R044 frozen-memory circuit-reuse contribution')
    commands = parser.add_subparsers(dest='command',required=True)
    prep = commands.add_parser('prepare');prep.add_argument('--source-run',required=True,type=Path);prep.add_argument('--out',required=True,type=Path);prep.add_argument('--prior-run',required=True,type=Path)
    exe = commands.add_parser('execute');exe.add_argument('--plan',required=True,type=Path);exe.add_argument('--source-run',type=Path);exe.add_argument('--out',required=True,type=Path);exe.add_argument('--prior-run',type=Path)
    for name in ('audit','verify'):
        sub = commands.add_parser(name);sub.add_argument('--run',required=True,type=Path)
    pack = commands.add_parser('bundle');pack.add_argument('--run',required=True,type=Path);pack.add_argument('--out',required=True,type=Path)
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        from .protocol import prepare
        result = prepare(args.source_run,args.prior_run,args.out)
    elif args.command == 'execute':
        from .protocol import execute
        result = execute(io.load(args.plan),args.out,args.source_run,args.prior_run)
    elif args.command in ('audit','verify'):
        from .audit import write_analysis
        result = write_analysis(args.run,check_only=args.command == 'verify')
    else:
        result = bundle(args.run,args.out)
    print(io.canonical(result).decode('utf-8'),flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
