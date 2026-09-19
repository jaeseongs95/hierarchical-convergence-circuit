#!/usr/bin/env python3
"""R0.3.3 검증/EXP-14 실행기. PowerShell 정책 변경 없이 기존 Python으로 실행한다."""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import sys


def commands(out: Path | None) -> list[list[str]]:
    steps = [
        ['scripts/verify_release.py'],
        ['hcr.py', 'check'],
        ['-m', 'unittest', 'discover', '-s', 'tools/r02_baseline/tests', '-p', 'test_*.py', '-v'],
        ['-m', 'unittest', 'discover', '-s', 'tools/r02_concepts/tests', '-p', 'test_*.py', '-v'],
        ['tools/r02_concepts/check.py', '--repo', str(Path(__file__).resolve().parents[2])],
    ]
    if out is not None:
        steps += [['hcr.py', 'review', 'demo', '--out', str(out)],
                  ['hcr.py', 'review', 'verify', '--run', str(out)]]
    return steps


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='프로젝트 기준 상대경로 또는 절대경로; 기존 결과는 보존')
    parser.add_argument('--check-only', action='store_true')
    args=parser.parse_args(argv)
    root=Path(__file__).resolve().parents[2]
    if sys.version_info<(3,12):
        parser.error('Python 3.12 이상이 필요합니다.')
    out=args.out or Path('HCR-Evidence')/'exp14'/('r033-'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    out=out if out.is_absolute() else root/out
    if not args.check_only and out.exists():
        print('기존 결과 폴더는 덮어쓰지 않습니다: '+str(out),file=sys.stderr);return 2
    try:
        for step in commands(None if args.check_only else out):
            print('\n> '+ ' '.join(step),flush=True)
            # 출력은 터미널로 전달한다. stdout=None을 문자열로 처리하는 테스트/실행기는 사용하지 않는다.
            subprocess.run([sys.executable,'-X','utf8','-B',*step],cwd=root,check=True)
        if not args.check_only:
            print('\n결과 폴더: '+str(out))
            print((out/'summary.ko.md').read_text(encoding='utf-8'))
        return 0
    except (subprocess.CalledProcessError,OSError) as exc:
        print('중단: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':
    raise SystemExit(main())
