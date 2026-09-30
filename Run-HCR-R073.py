"""Run the frozen pool drive decomposition with the existing Python runtime."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
if __name__=='__main__':
    if len(sys.argv)!=1:raise SystemExit('Usage: Run-HCR-R073.cmd')
    from tools.r073_decomposition.pipeline import main
    main()
