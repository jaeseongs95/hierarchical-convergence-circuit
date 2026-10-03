"""Evaluate the frozen paired top-down signal intervention with the existing runtime."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--resume',type=Path)
    p.add_argument('--review-dir',type=Path)
    p.add_argument('--writer-id',required=True)
    p.add_argument('--reviewer-id',required=True)
    args=p.parse_args()
    from tools.r081_top_down.pipeline import main
    main(args.resume,args.review_dir,args.writer_id,args.reviewer_id)
