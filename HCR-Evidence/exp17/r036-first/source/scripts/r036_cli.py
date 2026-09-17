#!/usr/bin/env python3
"""저장소의 기존 native와 tools를 같은 기준선에서 로드한다."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from r036_input_representation.cli import main
if __name__=='__main__':raise SystemExit(main())
