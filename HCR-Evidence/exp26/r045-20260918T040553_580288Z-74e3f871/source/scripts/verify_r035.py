"""R035 추가 파일과 native 기준선 검사. 과거 manifest/evidence는 갱신하지 않는다."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from r035_frozen_selection import storage as io
from r035_frozen_selection.upstream import check_native


def verify(root=ROOT):
    root=io.safe(root);m=io.load(root/'R035_MANIFEST.json')
    if m['schema']!='hcr-r035-additive-release-v1':raise ValueError('R035 manifest schema')
    for name,h in m['files'].items():
        if io.text_hash(io.child(root,name))!=h:raise ValueError('R035 checksum: '+name)
    reg=check_native(root)
    return dict(verified=True,addon_files=len(m['files']),unchanged_native_files=len(reg['files']),basis_commit=reg['basis_commit'])


if __name__=='__main__':
    try:print(json.dumps(verify(),ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError) as e:print(str(e),file=sys.stderr);raise SystemExit(2)
