"""R0.3.4 추가 파일만 검증한다. 기존 RELEASE_MANIFEST와 과거 evidence는 바꾸지 않는다."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import sys


def verify(root):
    root=Path(root)
    m=json.loads((root/'R034_MANIFEST.json').read_text(encoding='utf-8'))
    if m.get('schema')!='hcr-r034-additive-release-v1':raise ValueError('R034 manifest schema')
    failures=[]
    for name,h in m['files'].items():
        rel=PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name:raise ValueError('unsafe release path')
        p=root.joinpath(*rel.parts)
        if not p.is_file() or p.is_symlink() or any(x.is_symlink() for x in p.parents):
            failures.append(name);continue
        data=p.read_bytes();data.decode('utf-8')
        if hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()!=h:failures.append(name)
    if failures:raise ValueError('R034 source mismatch: '+', '.join(failures))
    return dict(verified=True,release='R0.3.4 additive EXP-15',files_checked=len(m['files']),
                scope='registered additive files only; legacy files are checked separately',basis_commit=m['basis_commit'])


if __name__=='__main__':
    try:print(json.dumps(verify(Path(__file__).resolve().parents[1]),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as exc:print(str(exc),file=sys.stderr);raise SystemExit(2)
