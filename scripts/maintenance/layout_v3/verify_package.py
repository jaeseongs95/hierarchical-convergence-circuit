"""Check delivered file integrity; this is not a signature/authenticity certificate."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import sys

def verify(root: Path):
    manifest = json.loads((root / 'PACKAGE_MANIFEST.json').read_bytes())
    for name, expected in manifest['files'].items():
        p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
            raise ValueError('Unsafe package path')
        full = root / name
        if full.is_symlink() or not full.is_file() or hashlib.sha256(full.read_bytes()).hexdigest() != expected:
            raise ValueError('Package file changed/missing: ' + name)
    print('Package integrity: OK')

if __name__ == '__main__':
    try:
        verify(Path(__file__).resolve().parent)
    except Exception as exc:
        print('STOPPED: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
