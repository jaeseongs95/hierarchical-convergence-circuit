"""Reanalyze existing pool evidence without installation or native research runs."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
if __name__=='__main__':
    if len(sys.argv)!=1:raise SystemExit('Usage: Run-HCR-R070.cmd')
    from tools.r070_pool.pipeline import main
    main()
