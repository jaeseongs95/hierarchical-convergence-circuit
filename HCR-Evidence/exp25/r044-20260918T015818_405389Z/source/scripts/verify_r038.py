"""R038 추가 배포 파일 및 d25f4bd 기준 의존 소스를 검사한다."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'),str(ROOT/'tools')]


def main(argv=None):
    parser = argparse.ArgumentParser(description='R038 배포/기준선 무결성 검사')
    parser.add_argument('--addon-only',action='store_true')
    args = parser.parse_args(argv)
    manifest = json.loads((ROOT/'R038_MANIFEST.json').read_text(encoding='utf-8'))
    if manifest['schema'] != 'hcr-r038-additive-release-v1' or manifest['basis_commit'] != 'd25f4bd4e3bd8c8aae763e3ee6542dbfd590900f':
        raise ValueError('R038 manifest schema/basis')
    for name,wanted in manifest['files'].items():
        path = ROOT/name
        if '\\' in name or ':' in name or name.startswith('/') or any(p in ('','.','..') for p in name.split('/')):
            raise ValueError('manifest 경로 오류: '+name)
        if any(x.is_symlink() for x in (path,*path.parents)):
            raise ValueError('symlink source 금지: '+name)
        actual = hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        if actual != wanted: raise ValueError('R038 파일 checksum 불일치: '+name)
    if not args.addon_only:
        from r038_early_adoption.sources import dependencies, addon_hashes
        dependency_count = len(dependencies()); addon_hashes()
    else:
        dependency_count = None
    print(json.dumps(dict(verified=True,addon_files=len(manifest['files']),
        dependency_files=dependency_count,addon_only=args.addon_only),ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
