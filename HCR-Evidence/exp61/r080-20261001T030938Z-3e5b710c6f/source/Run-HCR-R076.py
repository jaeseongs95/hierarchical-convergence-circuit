"""Run the frozen native competition experiment with the existing runtime."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
if __name__ == '__main__':
    if len(sys.argv) != 1:
        raise SystemExit('Usage: Run-HCR-R076.cmd')
    from tools.r076_competition.pipeline import main
    main()
