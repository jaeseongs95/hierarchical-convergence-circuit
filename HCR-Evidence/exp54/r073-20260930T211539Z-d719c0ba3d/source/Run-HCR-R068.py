"""Run the native request-boundary experiment without installing anything."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'src'),str(ROOT)]
if __name__ == '__main__':
    if len(sys.argv) != 1: raise SystemExit('Usage: Run-HCR-R068.cmd')
    from tools.r068_request.pipeline import main
    main()
