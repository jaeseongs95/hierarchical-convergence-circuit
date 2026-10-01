"""Run the frozen selection input range with the existing Python runtime."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
if __name__=='__main__':
    if len(sys.argv)!=1:
        raise SystemExit('Usage: Run-HCR-R072.cmd')
    from tools.r072_range.pipeline import main
    main()
