from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from r046_thought_carry.cli import main
if __name__=='__main__':raise SystemExit(main())
