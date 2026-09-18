from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from r046_thought_carry.sources import baseline
if __name__=='__main__':
    if sys.version_info<(3,12):raise RuntimeError('Python 3.12 or newer is required; nothing is installed automatically.')
    result=baseline(ROOT)
    print('Pinned native core and R046 release integrity: '+str(len(result))+' files verified')
