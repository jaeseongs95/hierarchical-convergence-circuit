"""Existing repository: run the full frozen EXP28 workflow without auto-install or retry."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parent
sys.path[:0]=[str(root/'src'),str(root)]
from tools.r047_state_ablation.protocol import pipeline
if __name__=='__main__':pipeline(root)
