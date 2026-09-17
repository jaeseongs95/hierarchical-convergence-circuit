#!/usr/bin/env python3
"""기존 회귀/실제 native 통합 검사 → EXP-17 입력 재표현 → 별도 audit/verify. Git 쓰기·네트워크 작업 없음."""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import json
import os
import subprocess
import sys


def steps(root,source,out,plan):
    commands=[['scripts/verify_release.py'],['scripts/verify_r034.py'],['scripts/verify_r035.py'],
        ['scripts/verify_r036.py'],['hcr.py','check'],
        ['-m','unittest','discover','-s','tools/r02_baseline/tests','-p','test_*.py','-v'],
        ['-m','unittest','discover','-s','tools/r02_concepts/tests','-p','test_*.py','-v'],
        ['tools/r02_concepts/check.py','--repo',str(root)],
        ['-m','unittest','discover','-s','tools/r035_frozen_selection/tests','-p','test_*.py','-v'],
        ['-m','unittest','discover','-s','tools/r036_input_representation/tests','-p','test_*.py','-v'],
        ['-m','unittest','discover','-s','tools/r036_input_representation/native_tests','-p','test_*.py','-v'],
        ['scripts/r034_cli.py','verify','--run',str(source)]]
    if out is not None:
        commands += [['scripts/r036_cli.py','prepare','--source-run',str(source),'--out',str(plan)],
            ['scripts/r036_cli.py','execute','--plan',str(plan),'--out',str(out)],
            ['scripts/r036_cli.py','audit','--run',str(out)],['scripts/r036_cli.py','verify','--run',str(out)]]
    return commands


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-run',type=Path,default=Path('HCR-Evidence/exp15/r034-first'))
    p.add_argument('--out',type=Path);p.add_argument('--check-only',action='store_true');a=p.parse_args(argv)
    if sys.version_info<(3,12):p.error('Python 3.12 이상을 사용하세요.')
    root=Path(__file__).resolve().parent;sys.path.insert(0,str(root/'tools'))
    from r035_frozen_selection.storage import safe
    source=safe(a.source_run if a.source_run.is_absolute() else root/a.source_run)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    out=a.out or Path('HCR-Evidence/exp17')/('r036-'+stamp);out=safe(out if out.is_absolute() else root/out)
    plan=out.with_name(out.name+'.plan.json')
    if not source.is_dir():p.error('EXP-15 원자료 폴더를 찾지 못했습니다: '+str(source))
    if not a.check_only and (out.exists() or plan.exists()):p.error('기존 결과/계획을 덮어쓰지 않습니다. 새로운 --out 이름을 사용하세요.')
    if out==source or source in out.parents or out in source.parents:p.error('EXP-15 source와 EXP-17 output 폴더를 분리하세요.')
    logs=safe(root/'HCR-Evidence/exp17/execution-logs'/stamp);logs.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy();env['PYTHONPATH']=str(root/'src')+os.pathsep+str(root/'tools')+(os.pathsep+env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    env['HCR_R036_SOURCE_RUN']=str(source)
    completed=[];code=2
    try:
        for i,step in enumerate(steps(root,source,None if a.check_only else out,plan)):
            cmd=[sys.executable,'-X','utf8','-B','-u',*step];print('\n> '+' '.join(cmd),flush=True)
            with (logs/f'{i:02d}.stdout.txt').open('x',encoding='utf-8',newline='\n') as log:
                child=subprocess.Popen(cmd,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8')
                try:
                    for line in child.stdout:print(line,end='',flush=True);log.write(line);log.flush()
                    rc=child.wait()
                except BaseException:
                    child.terminate();child.wait();raise
            completed.append(dict(command=step,returncode=rc))
            if rc:raise subprocess.CalledProcessError(rc,cmd)
        code=0
        if not a.check_only:
            print('\n결과 폴더: '+str(out));print((out/'analysis/summary.ko.md').read_text(encoding='utf-8'))
        return 0
    except (OSError,subprocess.SubprocessError,UnicodeError) as exc:
        print('중단: '+str(exc),file=sys.stderr);return 2
    finally:
        with (logs/'execution.json').open('x',encoding='utf-8',newline='\n') as f:
            json.dump(dict(completed=completed,returncode=code,automatic_retry=False,check_only=a.check_only,
                source_run=str(source),out=None if a.check_only else str(out)),f,ensure_ascii=False,indent=2);f.write('\n')


if __name__=='__main__':raise SystemExit(main())
