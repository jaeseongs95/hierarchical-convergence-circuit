"""배포 시점의 source/document 파일 SHA-256 점검. 실행 결과 폴더는 대상이 아니다."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import sys


def verify(root:Path) -> dict:
    manifest=json.loads((root/'RELEASE_MANIFEST.json').read_text(encoding='utf-8'))
    failures=[]
    line_ending_variants=[]
    normalized=manifest.get("text_normalized_sha256", {})
    if not isinstance(normalized,dict) or not set(normalized)<=set(manifest["files"]):raise ValueError("normalized release inventory")
    for name,expected in manifest['files'].items():
        rel=PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name:raise ValueError('unsafe source manifest')
        path=root/name
        if not path.is_file() or path.is_symlink():
            failures.append(name)
            continue
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected:
            if name in normalized:
                raw.decode('utf-8')
                if hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()==normalized[name]:
                    line_ending_variants.append(name)
                    continue
            failures.append(name)
    if failures:raise ValueError('release file mismatch: '+', '.join(failures))
    return {'schema':'hcr-release-check-r02','verified':True,'files_checked':len(manifest['files']),
            'release':manifest['release'],'differences':[],
            'line_ending_only_variants':line_ending_variants,
            'scope':'registered release files only; local run/IDE/Git/unregistered development files are not certified'}


if __name__=='__main__':
    try:print(json.dumps(verify(Path(__file__).resolve().parents[1]),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as error:print(str(error),file=sys.stderr);raise SystemExit(2)
