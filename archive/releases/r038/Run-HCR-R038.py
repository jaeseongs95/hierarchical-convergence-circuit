"""Windows/Linux 단회 실행기. 설치/네트워크/모델 다운로드/Git 변경/자동 retry 없음."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parent


def main(argv=None):
    parser = argparse.ArgumentParser(description='R038 검증 및 EXP19 단회 실행')
    parser.add_argument('--source-run',type=Path,default=ROOT/'HCR-Evidence/exp18/r037-first')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--check-only',action='store_true')
    args = parser.parse_args(argv)
    if sys.version_info < (3,12): raise RuntimeError('Python 3.12 이상이 필요합니다.')
    sys.path[:0] = [str(ROOT/'src'),str(ROOT/'tools')]
    from r037_online_selection import io
    from r038_early_adoption.contracts import require
    source = io.safe(args.source_run)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    out = io.safe(args.out or ROOT/'HCR-Evidence/exp19'/('r038-'+stamp))
    plan = out.with_name(out.name+'.plan.json')
    log_dir = ROOT/'HCR-Evidence/exp19/execution-logs'/stamp
    log_dir.mkdir(parents=True,exist_ok=False)
    env = dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=os.pathsep.join((str(ROOT/'src'),str(ROOT/'tools'))),HCR_R038_SOURCE_RUN=str(source))
    completed = []; failure = None; returncode = 1
    commands = [ ['scripts/verify_r038.py'],
        ['-m','unittest','discover','-s','tools/r038_early_adoption/tests','-p','test_*.py','-v'],
        ['-m','unittest','discover','-s','tools/r038_early_adoption/selector_tests','-p','test_*.py','-v'],
        ['scripts/r037_cli.py','verify','--run',str(source)],
        ['-m','unittest','discover','-s','tools/r038_early_adoption/native_tests','-p','test_*.py','-v'] ]
    if not args.check_only:
        commands += [ ['scripts/r038_cli.py','prepare','--source-run',str(source),'--out',str(plan)],
            ['scripts/r038_cli.py','execute','--plan',str(plan),'--source-run',str(source),'--out',str(out)],
            ['scripts/r038_cli.py','audit','--run',str(out)],
            ['scripts/r038_cli.py','verify','--run',str(out)],
            ['scripts/r038_cli.py','bundle','--run',str(out),'--out',str(out.with_name(out.name+'_evidence.zip'))] ]
    try:
        io.disjoint(source,out)
        require(source.is_dir(),'EXP18 원자료 폴더가 없습니다: '+str(source))
        require(not out.exists() and not plan.exists(),'기존 실행/계획 재사용 금지. --out에 새 이름을 지정하십시오.')
        for i,command in enumerate(commands,1):
            print(f'[{i}/{len(commands)}] '+subprocess.list2cmdline(command),flush=True)
            log = log_dir/f'{i:02d}.log'
            with log.open('x',encoding='utf-8',newline='\n') as f:
                proc = subprocess.Popen([sys.executable,'-X','utf8','-B',*command],cwd=ROOT,env=env,
                    stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='strict')
                try:
                    for line in proc.stdout:
                        print(line,end='',flush=True); f.write(line); f.flush()
                    code = proc.wait()
                except BaseException:
                    proc.terminate()
                    try: proc.wait(timeout=10)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait()
                    raise
            completed.append(dict(command=command,returncode=code,log=str(log)))
            if code != 0:
                returncode = code
                raise RuntimeError(f'첫 실패에서 중단했습니다. 단계 {i}, 종료 코드 {code}, 로그: {log}')
        returncode = 0
    except BaseException as exc:
        failure = dict(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
        print(str(exc),file=sys.stderr)
    finally:
        payload = dict(automatic_retry=False,check_only=args.check_only,source_run=str(source),out=str(out),
                       completed=completed,failure=failure,returncode=returncode)
        io.put(log_dir/'execution.json',payload)
        print('실행 기록: '+str(log_dir),flush=True)
    if returncode == 0 and not args.check_only:
        print('분석 보고서: '+str(out/'analysis/summary.ko.md'),flush=True)
        print('원자료 ZIP: '+str(out.with_name(out.name+'_evidence.zip')),flush=True)
    return returncode

if __name__ == '__main__':
    raise SystemExit(main())
