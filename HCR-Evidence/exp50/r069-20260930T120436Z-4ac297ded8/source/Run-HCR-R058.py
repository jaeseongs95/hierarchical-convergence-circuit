"""Standalone EXP-39 entrypoint; common default remains EXP-30."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT/'src'),str(ROOT)]
from tools.r058_horizon.pipeline import main
if __name__ == '__main__':
    raise SystemExit(main())
