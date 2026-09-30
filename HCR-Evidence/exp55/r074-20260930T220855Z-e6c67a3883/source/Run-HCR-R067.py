"""Run the e1 observation-refresh experiment without installing anything."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'src'),str(ROOT)]
if __name__ == '__main__':
    if len(sys.argv) != 1: raise SystemExit('Usage: Run-HCR-R067.cmd')
    from tools.r067_refresh.pipeline import main
    main()
