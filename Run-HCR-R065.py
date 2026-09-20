"""One-click R064 information-boundary reanalysis; no installation or native research."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--core-regression':
        from tools.r050_review_boundary.regression import main
        raise SystemExit(main(['--repo',str(ROOT),'--output',sys.argv[2]]))
    if len(sys.argv) != 1: raise SystemExit('Usage: Run-HCR-R065.cmd')
    from tools.r065_information.pipeline import main
    main()
