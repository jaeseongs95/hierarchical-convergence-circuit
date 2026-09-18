"""One entrypoint: verify basis -> prior replay -> tests -> freeze -> execute -> audit -> bundle."""
from __future__ import annotations
import argparse,os,subprocess,sys,traceback,zipfile
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from r046_thought_carry import storage as io
from r046_thought_carry.contracts import PARENT,BASE_COMMIT


def make_bundle(out,logs,target):
    """Archive only closed files, then byte-check every entry. No existing ZIP overwritten."""
    target=io.safe(target);items={}
    for label,root in [('run',out),('execution',logs)]:
        if root.exists():
            for name in sorted(io.inventory(root)):items[label+'/'+name]=io.child(root,name)
    before={n:io.file_hash(p) for n,p in items.items()}
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,p in items.items():z.write(p,n)
    with zipfile.ZipFile(target) as z:
        io.require(z.testzip() is None and set(z.namelist())==set(items),'bundle CRC/inventory')
        for n,h in before.items():io.require(io.bytes_hash(z.read(n))==h,'bundle content')
    io.require(before=={n:io.file_hash(p) for n,p in items.items()},'evidence changed during bundle')
    return dict(path=str(target),sha256=io.file_hash(target),files=len(items),verified=True)


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,default=ROOT/PARENT)
    p.add_argument('--check-only',action='store_true');p.add_argument('--output-base',type=Path,default=ROOT/'HCR-Evidence/exp27')
    args=p.parse_args(argv)
    if sys.version_info<(3,12):raise RuntimeError('Python 3.12+ required; no automatic installation')
    base=io.safe(args.output_base);parent=io.safe(args.parent);io.disjoint(base,parent)
    tag=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')+'-'+uuid4().hex[:8]
    logs=base/'execution-logs'/tag;logs.mkdir(parents=True,exist_ok=False)
    out=base/('r046-'+tag);plan=base/('r046-'+tag+'.plan.json')
    completed=[];active=None;failure=None;current=None
    commands=[
      ['scripts/verify_r046.py'],
      ['scripts/r045_cli.py','verify','--run',str(parent)],
      ['-m','unittest','discover','-s','tools/r046_thought_carry/tests','-p','test_*.py','-v','-f'],
      ['scripts/r046_cli.py','regression','--source-run',str(parent),'--out',str(logs/'native-core-regression')]]
    if not args.check_only:
        commands += [
          ['scripts/r046_cli.py','prepare','--source-run',str(parent),'--out',str(plan)],
          ['scripts/r046_cli.py','execute','--plan',str(plan),'--out',str(out)],
          ['scripts/r046_cli.py','audit','--run',str(out)],
          ['scripts/r046_cli.py','verify','--run',str(out)]]
    try:
        for i,cmd in enumerate(commands,1):
            current=dict(stage=i,command=cmd);log=logs/f'{i:02d}.log'
            print(f'[{i}] '+' '.join(cmd),flush=True)
            with log.open('xb') as f:
                active=subprocess.Popen([sys.executable,'-X','utf8','-B',*cmd],cwd=ROOT,
                    stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
                try:
                    for b in iter(active.stdout.readline,b''):
                        f.write(b);f.flush();sys.stdout.write(b.decode('utf-8',errors='replace'));sys.stdout.flush()
                    rc=active.wait()
                except BaseException:
                    active.terminate();active.wait();raise
                finally:active.stdout.close()
                os.fsync(f.fileno())
            active=None;completed.append(dict(**current,returncode=rc,log=log.name))
            if rc!=0:raise RuntimeError(f'First failure at stage {i}, exit {rc}; no retry. Log: {log}')
        io.put(logs/'execution.json',dict(state='all_commands_completed',basis_commit=BASE_COMMIT,
            python=sys.version,completed=completed,failure=None,check_only=args.check_only,
            automatic_retry=False,source_run=str(parent),out=str(out)))
        if plan.exists():io.write_bytes(logs/'frozen_plan.json',io.read(plan))
        name=('r046-'+tag+('_check' if args.check_only else '_evidence')+'.zip')
        receipt=make_bundle(out,logs,base/name);io.put(base/(name+'.receipt.json'),receipt)
        print('Verified evidence bundle: '+str(base/name),flush=True);return 0
    except BaseException as exc:
        failure=dict(stage=current,error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),
            completed=completed,automatic_retry=False,partial_raw_preserved=True)
        io.put(logs/'failure-'+uuid4().hex[:8]+'.json',failure)
        if plan.exists() and not (logs/'frozen_plan.json').exists():io.write_bytes(logs/'frozen_plan.json',io.read(plan))
        try:
            receipt=make_bundle(out,logs,base/('r046-'+tag+'_forensic.zip'))
            print('Forensic bundle: '+receipt['path'],flush=True)
        except BaseException as bundle_error:print('Forensic packaging failed; raw/logs retained: '+repr(bundle_error),flush=True)
        print(str(exc),file=sys.stderr,flush=True);return 1

if __name__=='__main__':raise SystemExit(main())
