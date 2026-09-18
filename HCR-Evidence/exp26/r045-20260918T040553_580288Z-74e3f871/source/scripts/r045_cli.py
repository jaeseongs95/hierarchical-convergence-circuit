from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from r045_direct_support.cli import main
if __name__=='__main__': raise SystemExit(main())
