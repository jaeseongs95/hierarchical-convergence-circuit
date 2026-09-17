#!/usr/bin/env python3
"""기존 회귀 → EXP-15 조건 동결 → raw 생성 → 별도 audit → 재검산. Git/네트워크 변경 없음."""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import json
import subprocess
import sys


def steps(root,out,plan):
    commands=[['scripts/verify_release.py'],['scripts/verify_r034.py'],['hcr.py','check'],
        ['-m','unittest','discover','-s','tools/r02_baseline/tests','-p','test_*.py','-v'],
        ['-m','unittest','discover','-s','tools/r02_concepts/tests','-p','test_*.py','-v'],
        ['tools/r02_concepts/check.py','--repo',str(root)]]
    if out is not None:
        cli=['scripts/r034_cli.py']
        commands.extend([cli+['prepare','--out',str(plan)],
            cli+['execute','--plan',str(plan),'--out',str(out)],
            cli+['audit','--run',str(out)],cli+['verify','--run',str(out)]])
    return commands


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path);p.add_argument('--check-only',action='store_true')
    a=p.parse_args(argv);root=Path(__file__).resolve().parent
    if sys.version_info<(3,12):p.error('Python 3.12 이상이 필요합니다.')
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    out=a.out or Path('HCR-Evidence/exp15')/('r034-'+stamp)
    out=out if out.is_absolute() else root/out
    plan=out.with_name(out.name+'.plan.json')
    if not a.check_only and (out.exists() or plan.exists()):
        print('기존 결과/동결 계획은 덮어쓰지 않습니다. 다른 --out 이름을 사용하세요: '+str(out),file=sys.stderr);return 2
    logs=root/'HCR-Evidence/exp15/execution-logs'/stamp
    logs.mkdir(parents=True,exist_ok=False)
    completed=[];result=2
    try:
        for i,step in enumerate(steps(root,None if a.check_only else out,plan)):
            command=[sys.executable,'-X','utf8','-B','-u',*step]
            print('\n> '+' '.join(command),flush=True)
            with (logs/f'{i:02d}.log').open('x',encoding='utf-8',newline='\n') as log:
                child=subprocess.Popen(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                    text=True,encoding='utf-8',errors='replace')
                try:
                    for line in child.stdout:
                        print(line,end='',flush=True);log.write(line);log.flush()
                    code=child.wait()
                except BaseException:
                    child.terminate();child.wait();raise
            completed.append(dict(command=step,returncode=code))
            if code:raise subprocess.CalledProcessError(code,command)
        if not a.check_only:
            print('\n결과 폴더: '+str(out));print('독립 분석: '+str(out/'analysis/summary.ko.md'))
            print((out/'analysis/summary.ko.md').read_text(encoding='utf-8'))
        result=0;return 0
    except (OSError,subprocess.SubprocessError) as exc:
        print('중단: '+str(exc),file=sys.stderr);return 2
    finally:
        with (logs/'execution.json').open('x',encoding='utf-8',newline='\n') as f:
            json.dump(dict(completed=completed,returncode=result,automatic_retry=False,
                check_only=a.check_only,out=None if a.check_only else str(out)),f,ensure_ascii=False,indent=2)
            f.write('\n')


if __name__=='__main__':raise SystemExit(main())
