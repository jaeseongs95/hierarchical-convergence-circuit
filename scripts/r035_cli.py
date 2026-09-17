"""프로젝트 루트와 무관한 실행 위치에서도 EXP-16 도구를 찾는다."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tools'))
from r035_frozen_selection.cli import main
if __name__=='__main__':raise SystemExit(main())
