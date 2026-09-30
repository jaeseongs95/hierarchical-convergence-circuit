"""Run the frozen native selection boundary experiment with existing Python."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
if __name__=='__main__':
    if len(sys.argv) not in (1,3) or (len(sys.argv)==3 and sys.argv[1]!='--recover'):
        raise SystemExit('Usage: Run-HCR-R071.cmd [--recover <failed EXP52 run>]')
    from tools.r071_boundary.pipeline import main
    main(Path(sys.argv[2]) if len(sys.argv)==3 else None)
