"""Run the explicit fact-retrieval baseline without installing anything."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'src'),str(ROOT)]
if __name__ == '__main__':
    if len(sys.argv) != 1: raise SystemExit('Usage: Run-HCR-R066.cmd')
    from tools.r066_facts.pipeline import main
    main()
