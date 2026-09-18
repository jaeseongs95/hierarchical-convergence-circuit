"""Explicit prepare/execute/audit/verify/bundle boundaries; bundle can preserve partial runs."""
import argparse
from pathlib import Path
import zipfile
from . import storage as io


def bundle(run,out,execution_logs=None):
    root,target=io.safe(run),io.safe(out)
    io.require(root.is_dir(),'run directory missing');io.disjoint(root,target)
    io.require(not target.exists(),'existing ZIP is not overwritten')
    names=sorted(io.inventory(root));io.require(names,'empty run')
    items={root.name+'/'+n:root/n for n in names}
    if execution_logs is not None:
        logs=io.safe(execution_logs);io.require(logs.is_dir(),'sealed execution snapshot missing')
        io.disjoint(root,logs);io.disjoint(logs,target)
        items.update({'execution/'+n:logs/n for n in sorted(io.inventory(logs))})
    before={n:io.file_hash(p) for n,p in items.items()}
    seal=dict(schema='hcr-exp26-bundle-v1',files=before,
        raw_complete=(root/'manifest.json').is_file(),analysis_present=(root/'analysis/manifest.json').is_file(),
        execution_snapshot_included=execution_logs is not None,automatic_retry=False)
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,path in items.items():z.write(path,name)
        z.writestr('BUNDLE-MANIFEST.json',io.canonical(seal)+b'\n')
    io.require(before=={n:io.file_hash(p) for n,p in items.items()},'evidence changed during bundle')
    io.require(names==sorted(io.inventory(root)),'run inventory changed during bundle')
    if execution_logs is not None:
        io.require({'execution/'+n for n in io.inventory(logs)}=={n for n in items if n.startswith('execution/')},'execution inventory changed')
    with zipfile.ZipFile(target) as z:
        io.require(z.testzip() is None and set(z.namelist())==set(items)|{'BUNDLE-MANIFEST.json'},'ZIP CRC/inventory')
        for name,h in before.items():io.require(io.bytes_hash(z.read(name))==h,'ZIP checksum')
    return dict(bundle=str(target),files=len(items),sha256=io.file_hash(target),
        raw_complete=seal['raw_complete'],analysis_present=seal['analysis_present'],execution_snapshot_included=execution_logs is not None)


def main(argv=None):
    parser=argparse.ArgumentParser(description='EXP26 / R045 direct goal-support reuse diagnostics')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--source-run',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p=sub.add_parser('execute');p.add_argument('--plan',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--source-run',type=Path)
    for command in ('audit','verify'):
        p=sub.add_parser(command);p.add_argument('--run',required=True,type=Path)
    p=sub.add_parser('bundle');p.add_argument('--run',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--execution-logs',type=Path)
    args=parser.parse_args(argv)
    if args.command=='prepare':
        from .protocol import prepare
        result=prepare(args.source_run,args.out)
    elif args.command=='execute':
        from .protocol import execute
        result=execute(io.load(args.plan),args.out,args.source_run)
    elif args.command in ('audit','verify'):
        from .audit import write_analysis
        result=write_analysis(args.run,check_only=args.command=='verify')
    else: result=bundle(args.run,args.out,args.execution_logs)
    print(io.canonical(result).decode('utf-8'),flush=True)
    return 0

if __name__=='__main__': raise SystemExit(main())
