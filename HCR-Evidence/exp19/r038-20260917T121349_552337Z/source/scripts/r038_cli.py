"""저장소 루트의 hcr.py보다 src/hcr 패키지를 우선한다."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'),str(ROOT/'tools')]
from r038_early_adoption.cli import main
if __name__ == '__main__':
    raise SystemExit(main())
