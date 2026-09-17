"""프로젝트 루트에서 호출하는 EXP-15 전용 진입점."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from hcr.selection_cli import main
if __name__=='__main__':raise SystemExit(main())
