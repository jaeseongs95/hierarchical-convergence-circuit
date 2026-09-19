"""Baseline → tests → old raw verify → native selftest → frozen run → independent audit → sealed bundle.

No installation, network, Git writes, automatic retry or automatic repair occurs here.
The standalone OneClick CMD performs additive installation before calling this entrypoint.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import traceback
import uuid

ROOT=Path(__file__).resolve().parent


def find_parent(explicit=None):
    from r045_direct_support import storage as io
    from r045_direct_support.contracts import PARENT_RUN,PARENT_RAW_SHA256
    preferred=io.safe(explicit or ROOT/PARENT_RUN)
    if explicit is not None or preferred.is_dir():
        io.require(io.file_hash(preferred/'manifest.json')==PARENT_RAW_SHA256,'pinned EXP25 manifest differs')
        return preferred
    matches=[p.parent for p in (ROOT/'HCR-Evidence/exp25').glob('r044-*/manifest.json') if io.file_hash(p)==PARENT_RAW_SHA256]
    io.require(len(matches)==1,'pinned EXP25 raw not found; no alternate experiment is substituted')
    return matches[0]


def forensic_bundle(log_dir,out,plan):
    import zipfile
    from r045_direct_support import storage as io
    target=log_dir.with_name(log_dir.name+'_forensic.zip')
    items={'execution/'+n:log_dir/n for n in sorted(io.inventory(log_dir))}
    if out is not None and out.is_dir():items.update({'partial_run/'+n:out/n for n in sorted(io.inventory(out))})
    if plan is not None and plan.is_file():items['frozen_plan.json']=plan
    hashes={n:io.file_hash(p) for n,p in items.items()}
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,p in items.items():z.write(p,n)
        z.writestr('FORENSIC-MANIFEST.json',io.canonical(dict(complete=False,automatic_retry=False,files=hashes)))
    with zipfile.ZipFile(target) as z:
        io.require(z.testzip() is None,'forensic CRC')
        for n,h in hashes.items():io.require(io.bytes_hash(z.read(n))==h,'forensic checksum')
    return target


def snapshot_execution(log_dir,completed):
    from r045_direct_support import storage as io
    names=sorted(io.inventory(log_dir));target=log_dir/'sealed-execution'
    target.mkdir(exist_ok=False)
    for name in names:io.write_bytes(io.child(target,name),io.read(io.child(log_dir,name)))
    io.put(target/'prebundle.json',dict(schema='hcr-r045-prebundle-v1',completed=completed,
        all_prebundle_steps_passed=True,automatic_retry=False,native_selftest_not_research=True))
    return target


def commands(source,plan,out,check_only=False):
    result=[['scripts/verify_r045.py'],
        ['-m','unittest','discover','-s','tools/r044_reuse_contribution/tests','-p','test_*.py','-v'],
        ['-m','unittest','discover','-s','tools/r045_direct_support/tests','-p','test_*.py','-v'],
        ['scripts/r044_cli.py','verify','--run',str(source)],
        ['-m','unittest','discover','-s','tools/r045_direct_support/native_tests','-p','test_*.py','-v','-f']]
    if not check_only:
        result += [['scripts/r045_cli.py','prepare','--source-run',str(source),'--out',str(plan)],
                   ['scripts/r045_cli.py','execute','--plan',str(plan),'--source-run',str(source),'--out',str(out)],
                   ['scripts/r045_cli.py','audit','--run',str(out)],
                   ['scripts/r045_cli.py','verify','--run',str(out)]]
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description='R045 / EXP26 direct-support circuit contribution')
    parser.add_argument('--source-run',type=Path);parser.add_argument('--out',type=Path)
    parser.add_argument('--check-only',action='store_true',help='Run all mandatory checks, but no new research trials')
    args=parser.parse_args(argv)
    if sys.version_info<(3,12):raise RuntimeError('Python 3.12 or newer required')
    sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
    from r045_direct_support import storage as io
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')+'-'+uuid.uuid4().hex[:8]
    log_dir=io.safe(ROOT/'HCR-Evidence/exp26/execution-logs'/stamp);log_dir.mkdir(parents=True,exist_ok=False)
    out=io.safe(args.out or ROOT/'HCR-Evidence/exp26'/('r045-'+stamp))
    plan=out.with_name(out.name+'.plan.json')
    completed=[];failure=None;source=None;code=1;current=None;proc=None
    out_owned=not out.exists();plan_owned=not plan.exists()
    try:
        source=find_parent(args.source_run)
        for path in (out,plan):io.disjoint(source,path);io.disjoint(log_dir,path)
        if not args.check_only:io.require(out_owned and plan_owned,'existing run/plan is not overwritten or resumed')
        env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',
            PYTHONPATH=os.pathsep.join((str(ROOT/'src'),str(ROOT/'tools'))),
            HCR_R045_SOURCE_RUN=str(source),HCR_R045_NATIVE_TEST_OUT=str(log_dir/'native-selftest'))
        with (log_dir/'stages.jsonl').open('x',encoding='utf-8',newline='\n') as stages:
            def stage_event(value):
                stages.write(io.canonical(value).decode('utf-8')+'\n');stages.flush();os.fsync(stages.fileno())
            def run_step(command):
                nonlocal current,proc,code
                index=len(completed)+1;current=command;log=log_dir/f'{index:02d}.log'
                stage_event(dict(event='started',ordinal=index,command=command))
                print(f'[{index}] '+subprocess.list2cmdline(command),flush=True)
                with log.open('x',encoding='utf-8',newline='\n') as output:
                    proc=subprocess.Popen([sys.executable,'-X','utf8','-B',*command],cwd=ROOT,env=env,
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='strict')
                    try:
                        for line in proc.stdout:
                            print(line,end='',flush=True);output.write(line);output.flush()
                        rc=proc.wait()
                    except BaseException:
                        proc.terminate()
                        try:proc.wait(timeout=10)
                        except subprocess.TimeoutExpired:proc.kill();proc.wait()
                        raise
                    finally:
                        if proc.stdout is not None:proc.stdout.close()
                entry=dict(command=command,returncode=rc,log=str(log));completed.append(entry)
                stage_event(dict(event='completed',ordinal=index,**entry))
                if rc:
                    code=rc
                    raise RuntimeError(f'First failure; no retry. Stage {index}, log: {log}')
            for command in commands(source,plan,out,args.check_only):run_step(command)
            if not args.check_only:
                snapshot=snapshot_execution(log_dir,completed)
                run_step(['scripts/r045_cli.py','bundle','--run',str(out),'--execution-logs',str(snapshot),
                          '--out',str(out.with_name(out.name+'_evidence.zip'))])
        code=0
    except BaseException as exc:
        failure=dict(command=current,error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
        print(str(exc),file=sys.stderr)
    finally:
        io.put(log_dir/'execution.json',dict(automatic_retry=False,check_only=args.check_only,source_run=None if source is None else str(source),
            out=str(out),completed=completed,failure=failure,returncode=code))
        print('Execution logs: '+str(log_dir),flush=True)
        if code:
            try:print('Incomplete forensic ZIP: '+str(forensic_bundle(log_dir,out if out_owned else None,plan if plan_owned else None)),flush=True)
            except BaseException as exc:print('Forensic ZIP failed; original evidence remains: '+repr(exc),file=sys.stderr)
    if code==0 and not args.check_only:
        print('Report: '+str(out/'analysis/summary.ko.md'),flush=True)
        print('Evidence ZIP: '+str(out.with_name(out.name+'_evidence.zip')),flush=True)
    return code

if __name__=='__main__':raise SystemExit(main())
