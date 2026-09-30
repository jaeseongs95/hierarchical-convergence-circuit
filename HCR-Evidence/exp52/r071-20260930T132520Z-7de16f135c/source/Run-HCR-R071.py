"""Run the frozen native selection boundary experiment with existing Python."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
if __name__=='__main__':
    if len(sys.argv)!=1:raise SystemExit('Usage: Run-HCR-R071.cmd')
    from tools.r071_boundary.pipeline import main
    main()
