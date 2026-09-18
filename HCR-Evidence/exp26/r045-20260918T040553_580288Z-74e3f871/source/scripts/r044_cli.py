"""루트 hcr.py의 패키지 shadowing을 피하는 CLI entrypoint."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'),str(ROOT/'tools')]
from r044_reuse_contribution.cli import main
if __name__ == '__main__':
    raise SystemExit(main())
