"""검증 → 조건 동결 → 단회 실행 → 독립 audit → 재검산 → ZIP. 설치/Git 쓰기/재시도 없음."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parent


def find_parent(explicit=None):
    from r042_id_role_isolation import storage as io
    from r042_id_role_isolation.contracts import PARENT_RUN, PARENT_RAW_SHA256
    if explicit is not None:
        source = io.safe(explicit)
        io.require(io.file_hash(source/'manifest.json') == PARENT_RAW_SHA256, '--source-run의 EXP22 checksum이 다릅니다.')
        return source
    preferred = ROOT/PARENT_RUN
    if preferred.is_dir():
        io.require(io.file_hash(preferred/'manifest.json') == PARENT_RAW_SHA256, '기준 EXP22 manifest 변경')
        return preferred
    matches = [p.parent for p in (ROOT/'HCR-Evidence/exp22').glob('r041-*/manifest.json')
               if io.file_hash(p) == PARENT_RAW_SHA256]
    io.require(len(matches) == 1, '지정 EXP22 raw를 찾지 못했습니다. --source-run 경로를 지정하십시오.')
    return matches[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description='R042 / EXP23 ID-role isolation')
    parser.add_argument('--source-run',type=Path)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--check-only',action='store_true',help='기존 raw 재검산 및 통합 self-test까지만 실행')
    args = parser.parse_args(argv)
    if sys.version_info < (3,12): raise RuntimeError('Python 3.12 이상이 필요합니다.')
    sys.path[:0] = [str(ROOT/'src'),str(ROOT/'tools')]
    from r042_id_role_isolation import storage as io
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    log_dir = ROOT/'HCR-Evidence/exp23/execution-logs'/stamp
    log_dir.mkdir(parents=True,exist_ok=False)
    out = io.safe(args.out or ROOT/'HCR-Evidence/exp23'/('r042-'+stamp))
    plan = out.with_name(out.name+'.plan.json')
    completed = []; failure = None; source = None; code = 1
    try:
        source = find_parent(args.source_run)
        io.disjoint(source,out)
        if not args.check_only:
            io.require(not out.exists() and not plan.exists(), '기존 실행/plan을 덮어쓰지 않습니다.')
        env = dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',
            PYTHONPATH=os.pathsep.join((str(ROOT/'src'),str(ROOT/'tools'))),
            HCR_R042_SOURCE_RUN=str(source),HCR_R042_NATIVE_TEST_OUT=str(log_dir/'native-selftest'))
        commands = [
            ['scripts/verify_r042.py'],
            ['-m','unittest','discover','-s','tools/r042_id_role_isolation/tests','-p','test_*.py','-v'],
            ['scripts/r041_cli.py','verify','--run',str(source)],
            ['-m','unittest','discover','-s','tools/r042_id_role_isolation/native_tests','-p','test_*.py','-v']]
        if not args.check_only:
            commands.extend([
                ['scripts/r042_cli.py','prepare','--source-run',str(source),'--out',str(plan)],
                ['scripts/r042_cli.py','execute','--plan',str(plan),'--source-run',str(source),'--out',str(out)],
                ['scripts/r042_cli.py','audit','--run',str(out)],
                ['scripts/r042_cli.py','verify','--run',str(out)],
                ['scripts/r042_cli.py','bundle','--run',str(out),'--out',str(out.with_name(out.name+'_evidence.zip'))]])
        for index,command in enumerate(commands,1):
            print(f'[{index}/{len(commands)}] '+subprocess.list2cmdline(command),flush=True)
            log = log_dir/f'{index:02d}.log'
            with log.open('x',encoding='utf-8',newline='\n') as stream:
                proc = subprocess.Popen([sys.executable,'-X','utf8','-B',*command],cwd=ROOT,env=env,
                    stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='strict')
                try:
                    for line in proc.stdout:
                        print(line,end='',flush=True);stream.write(line);stream.flush()
                    stage_code = proc.wait()
                except BaseException:
                    proc.terminate()
                    try: proc.wait(timeout=10)
                    except subprocess.TimeoutExpired: proc.kill();proc.wait()
                    raise
                finally:
                    if proc.stdout is not None: proc.stdout.close()
            completed.append(dict(command=command,returncode=stage_code,log=str(log)))
            if stage_code:
                code = stage_code
                raise RuntimeError(f'첫 실패에서 중단했습니다. 단계 {index}, 로그: {log}')
        code = 0
    except BaseException as exc:
        failure = dict(error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
        print(str(exc),file=sys.stderr)
    finally:
        io.put(log_dir/'execution.json',dict(automatic_retry=False,check_only=args.check_only,
            source_run=None if source is None else str(source),out=str(out),completed=completed,
            failure=failure,returncode=code))
        print('실행 기록: '+str(log_dir),flush=True)
    if code == 0 and not args.check_only:
        print('보고서: '+str(out/'analysis/summary.ko.md'),flush=True)
        print('원자료 ZIP: '+str(out.with_name(out.name+'_evidence.zip')),flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
