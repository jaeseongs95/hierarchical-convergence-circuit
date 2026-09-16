"""배포 시점의 source/document 파일 SHA-256 점검. 실행 결과 폴더는 대상이 아니다."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import sys


def verify(root:Path) -> dict:
    manifest=json.loads((root/'RELEASE_MANIFEST.json').read_text(encoding='utf-8'))
    failures=[]
    for name,expected in manifest['files'].items():
        rel=PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name:raise ValueError('unsafe source manifest')
        path=root/name
        if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            failures.append(name)
    if failures:raise ValueError('release file mismatch: '+', '.join(failures))
    return {'schema':'hcr-release-check-r01','verified':True,'files_checked':len(manifest['files']),
            'release':manifest['release'],'differences':[],
            'scope':'registered release files only; local run/IDE/Git/unregistered development files are not certified'}


if __name__=='__main__':
    try:print(json.dumps(verify(Path(__file__).resolve().parents[1]),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as error:print(str(error),file=sys.stderr);raise SystemExit(2)
