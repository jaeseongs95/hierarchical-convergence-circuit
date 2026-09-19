#!/usr/bin/env python3
"""기존 회귀/EXP-17 검증 → 신규 단위/native 통합 검사 → EXP-18 동결·실행·독립 검산. Git 쓰기/네트워크 없음."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys


def steps(root, source, out, plan):
    commands = [
        ['scripts/verify_release.py'], ['scripts/verify_r034.py'], ['scripts/verify_r035.py'],
        ['scripts/verify_r036.py'], ['scripts/verify_r037.py'], ['hcr.py', 'check'],
        ['-m', 'unittest', 'discover', '-s', 'tools/r02_baseline/tests', '-p', 'test_*.py', '-v'],
        ['-m', 'unittest', 'discover', '-s', 'tools/r02_concepts/tests', '-p', 'test_*.py', '-v'],
        ['tools/r02_concepts/check.py', '--repo', str(root)],
        ['-m', 'unittest', 'discover', '-s', 'tools/r035_frozen_selection/tests', '-p', 'test_*.py', '-v'],
        ['-m', 'unittest', 'discover', '-s', 'tools/r036_input_representation/tests', '-p', 'test_*.py', '-v'],
        ['scripts/r036_cli.py', 'verify', '--run', str(source)],
        ['-m', 'unittest', 'discover', '-s', 'tools/r037_online_selection/tests', '-p', 'test_*.py', '-v'],
        ['-m', 'unittest', 'discover', '-s', 'tools/r037_online_selection/selector_tests', '-p', 'test_*.py', '-v'],
        ['-m', 'unittest', 'discover', '-s', 'tools/r037_online_selection/native_tests', '-p', 'test_*.py', '-v'],
    ]
    if out is not None:
        commands += [
            ['scripts/r037_cli.py', 'prepare', '--source-run', str(source), '--out', str(plan)],
            ['scripts/r037_cli.py', 'execute', '--plan', str(plan), '--out', str(out)],
            ['scripts/r037_cli.py', 'audit', '--run', str(out)],
            ['scripts/r037_cli.py', 'verify', '--run', str(out)],
        ]
    return commands


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run', type=Path, default=Path('HCR-Evidence/exp17/r036-first'))
    parser.add_argument('--out', type=Path)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    if sys.version_info < (3,12):
        parser.error('Python 3.12 이상을 사용하세요.')
    root = Path(__file__).resolve().parent
    sys.path[:0] = [str(root/'src'), str(root/'tools')]
    from r037_online_selection import io
    source = io.safe(args.source_run if args.source_run.is_absolute() else root/args.source_run)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    out = args.out or Path('HCR-Evidence/exp18')/('r037-'+stamp)
    out = io.safe(out if out.is_absolute() else root/out)
    plan = out.with_name(out.name+'.plan.json')
    if not source.is_dir():
        parser.error('EXP-17 결과 폴더를 찾지 못했습니다: '+str(source))
    io.disjoint(source, out)
    if not args.check_only and (out.exists() or plan.exists()):
        parser.error('기존 결과/계획은 덮어쓰지 않습니다. 새로운 --out 경로를 사용하세요.')
    logs = io.safe(root/'HCR-Evidence/exp18/execution-logs'/stamp)
    logs.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join([str(root/'src'), str(root/'tools')] + ([env['PYTHONPATH']] if env.get('PYTHONPATH') else []))
    env['HCR_R037_SOURCE_RUN'] = str(source)
    completed = []; code = 2; failure = None
    try:
        for index, step in enumerate(steps(root, source, None if args.check_only else out, plan)):
            command = [sys.executable, '-X', 'utf8', '-B', '-u', *step]
            print('\n> '+' '.join(command), flush=True)
            with (logs/f'{index:02d}.stdout.txt').open('x',encoding='utf-8',newline='\n') as stream:
                child = subprocess.Popen(command,cwd=root,env=env,stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,text=True,encoding='utf-8')
                try:
                    for line in child.stdout:
                        print(line,end='',flush=True); stream.write(line); stream.flush()
                    rc = child.wait()
                except BaseException:
                    if child.poll() is None:
                        child.terminate(); child.wait()
                    raise
            completed.append(dict(command=step,returncode=rc))
            if rc:
                raise subprocess.CalledProcessError(rc,command)
        code = 0
        if not args.check_only:
            print('\n결과 폴더: '+str(out))
            print((out/'analysis/summary.ko.md').read_text(encoding='utf-8'))
        return 0
    except (OSError,ValueError,ImportError,subprocess.SubprocessError,KeyboardInterrupt) as exc:
        failure = dict(error_type=type(exc).__name__,error=str(exc))
        print('중단: '+str(exc),file=sys.stderr);return 2
    finally:
        io.put(logs/'execution.json',dict(completed=completed,returncode=code,failure=failure,
            automatic_retry=False,check_only=args.check_only,source_run=str(source),
            out=None if args.check_only else str(out)))


if __name__ == '__main__':
    raise SystemExit(main())
