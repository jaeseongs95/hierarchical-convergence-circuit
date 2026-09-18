"""Run EXP30 with the installed existing interpreter; no downloads or git writes."""
from pathlib import Path
import sys
if sys.version_info<(3,12):raise SystemExit('Python 3.12+ is required; no automatic installation.')
root=Path(__file__).resolve().parent
sys.path[:0]=[str(root/'src'),str(root)]
from tools.r049_signal_boundary.pipeline import run
if __name__=='__main__':run(root)
