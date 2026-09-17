#!/usr/bin/env python3
"""R037 배포 파일 해시·기존 기준선 검사. Git 쓰기 없음."""
from pathlib import Path
import argparse
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tools')]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--addon-only', action='store_true', help='native 기준선 없이 신규 배포 파일만 확인')
    args = parser.parse_args(argv)
    from r037_online_selection import io, spec
    from r037_online_selection.contracts import require
    manifest = io.load(ROOT/'R037_MANIFEST.json')
    require(manifest['schema'] == 'hcr-r037-additive-release-v1' and manifest['basis_commit'] == spec.BASE_COMMIT,
            'R037 release schema/basis')
    for name,h in manifest['files'].items():
        require(io.text_hash(io.child(ROOT,name)) == h, 'R037 배포 파일 변경: '+name)
    actual = {p.relative_to(ROOT).as_posix() for p in (ROOT/'tools/r037_online_selection').rglob('*.py')}
    listed = {n for n in manifest['files'] if n.startswith('tools/r037_online_selection/') and n.endswith('.py')}
    require(actual == listed, 'R037 Python source inventory')
    if not args.addon_only:
        from r037_online_selection.sources import dependencies
        dependencies()
    print('R037 배포 해시 확인 완료' + (' (신규 파일만)' if args.addon_only else ' / b6b57589 native·R035·R036 기준선 일치'))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, ImportError) as exc:
        print('검증 중단: '+str(exc), file=sys.stderr); raise SystemExit(2)
