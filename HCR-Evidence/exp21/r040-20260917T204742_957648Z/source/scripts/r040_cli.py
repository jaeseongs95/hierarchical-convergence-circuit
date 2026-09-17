"""저장소 루트 hcr.py shadowing을 피하는 CLI bootstrap."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from r040_frontier_schedule.cli import main
if __name__=='__main__': raise SystemExit(main())
