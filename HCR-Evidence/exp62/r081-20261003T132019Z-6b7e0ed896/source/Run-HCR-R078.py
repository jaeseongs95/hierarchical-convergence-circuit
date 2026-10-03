"""Evaluate the frozen paired edge-order intervention with the existing runtime."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
if __name__ == '__main__':
    if len(sys.argv) != 1:
        raise SystemExit('Usage: Run-HCR-R078.cmd')
    from tools.r078_binding_order.pipeline import main
    main()
