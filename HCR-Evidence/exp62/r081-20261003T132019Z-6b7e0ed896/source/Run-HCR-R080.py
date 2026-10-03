"""Evaluate the frozen paired edge-order intervention with the existing runtime."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
if __name__ == '__main__':
    if len(sys.argv) != 1:
        raise SystemExit('Usage: Run-HCR-R080.cmd')
    from tools.r080_small_positive.pipeline import main
    main()
