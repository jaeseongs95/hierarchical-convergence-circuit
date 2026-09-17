#!/usr/bin/env python3
"""저장소 root/cwd와 무관한 EXP-18 명령 진입점."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tools')]
if __name__ == '__main__':
    from r037_online_selection.cli import main
    raise SystemExit(main())
