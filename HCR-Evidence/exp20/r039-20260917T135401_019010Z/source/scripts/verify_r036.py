#!/usr/bin/env python3
"""추가 파일과 기존 기준선 해시를 검사한다. 네트워크·Git 쓰기는 없다."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from r035_frozen_selection import storage as io
from r035_frozen_selection.contracts import require
from r036_input_representation.sources import check_dependencies
from r036_input_representation.spec import BASE_COMMIT


def verify(root=ROOT):
    deps=check_dependencies(root);m=io.load(root/'R036_MANIFEST.json')
    require(m['schema']=='hcr-r036-additive-release-v1' and m['basis_commit']==BASE_COMMIT,'R036 release manifest')
    for name,h in m['files'].items():require(io.text_hash(io.child(root,name))==h,'R036 배포 파일 변경: '+name)
    actual={p.relative_to(root).as_posix() for p in (root/'tools/r036_input_representation').rglob('*.py')}
    registered={n for n in m['files'] if n.startswith('tools/r036_input_representation/') and n.endswith('.py')}
    require(actual==registered,'R036 미등록 코드')
    return dict(verified=True,release='R0.3.6 / EXP-17',dependencies_checked=len(deps['files']),
                addon_files_checked=len(m['files']),native_source_modified=False)


if __name__=='__main__':
    try:print(json.dumps(verify(),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as exc:print(str(exc),file=sys.stderr);raise SystemExit(2)
