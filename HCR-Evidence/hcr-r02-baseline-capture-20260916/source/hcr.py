#!/usr/bin/env python3
"""압축 해제 후 설치 없이 실행하는 진입점. 네트워크·pip·git 명령을 실행하지 않는다."""
from pathlib import Path
import sys

if sys.version_info < (3, 12):
    raise SystemExit('Python 3.12 이상이 필요합니다. 기존 설치 경로를 명시해 실행하세요.')
sys.path.insert(0, str(Path(__file__).resolve().parent/'src'))
from hcr.cli import main
if __name__ == '__main__':
    raise SystemExit(main())
