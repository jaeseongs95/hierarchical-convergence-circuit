"""I/O and byte integrity only. No inference, action selection, or outcome scoring."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any

BASE_COMMIT = '7ba5f31fb68a92fa0eca8ed0bf5f302fe2d36b86'
SRC_TREE = '01078420fbcaf73609d741608f289bb76b025ef1'
TEST_TREE = '6cf19995d1bb9aa57fc508f3b8b8bf494c6f16a2'
CONTRACT = 'r050-review-boundary-v1'

class IntegrityError(ValueError):
    pass

def require(ok: bool, message: str) -> None:
    if not ok:
        raise IntegrityError(message)

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')

def fingerprint(value: Any) -> str:
    return sha(canonical(value))

def seal(value: dict) -> dict:
    require('sha256' not in value, 'Do not reseal an existing packet.')
    return dict(value, sha256=fingerprint(value))

def unseal(value: dict, schema: str) -> dict:
    require(isinstance(value, dict) and value.get('schema') == schema, 'Packet schema: ' + schema)
    body = {k: v for k, v in value.items() if k != 'sha256'}
    require(value.get('sha256') == fingerprint(body), 'Packet checksum: ' + schema)
    return body

def _unique(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result

def load(path: Path) -> Any:
    path = safe(path)
    require(path.is_file() and path.stat().st_size <= 128 * 1024 * 1024, 'Missing/oversized JSON: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(IntegrityError('Non-finite JSON: ' + x)))

def safe(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    for p in (path, *path.parents):
        require(not p.is_symlink() and not (hasattr(p, 'is_junction') and p.is_junction()),
                'Symlink/junction not allowed: ' + str(p))
    return path

def relative(root: Path, name: str) -> Path:
    p = PurePosixPath(name)
    require(isinstance(name, str) and bool(name) and not p.is_absolute() and name == p.as_posix()
            and all(s not in ('', '.', '..', '.git') for s in name.split('/'))
            and not any(c in name for c in '\\:\x00\r\n'), 'Unsafe relative path: ' + repr(name))
    return safe(safe(root) / name)

def publish(path: Path, raw: bytes) -> None:
    """Exclusive, atomic publication. Never replace an existing result."""
    path = safe(path)
    require(not path.exists(), 'Refusing to overwrite: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    safe(path.parent)
    fd, temporary = tempfile.mkstemp(prefix='.r050-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)

def dump(path: Path, value: Any) -> None:
    publish(path, canonical(value) + b'\n')

def files(root: Path) -> dict[str, str]:
    root = safe(root)
    found = {}
    for p in sorted(root.rglob('*')):
        safe(p)
        if '__pycache__' in p.parts:
            raise IntegrityError('Unexpected bytecode in a frozen tree: ' + str(p))
        if p.is_file():
            found[p.relative_to(root).as_posix()] = sha(p.read_bytes())
    return found

def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()

def text_blob(raw: bytes) -> str:
    return git_blob(raw.replace(b'\r\n', b'\n'))

def git_tree(root: Path) -> str:
    """Recompute a text-only 100644/040000 Git tree; reject other entry types."""
    root = safe(root)
    entries = []
    for p in root.iterdir():
        safe(p)
        require(p.name != '__pycache__', 'Unexpected bytecode in pinned source.')
        if p.is_dir():
            entries.append((p.name.encode() + b'/', b'40000 ' + p.name.encode() + b'\0' + bytes.fromhex(git_tree(p))))
        else:
            require(p.is_file(), 'Nonregular pinned source entry.')
            raw = p.read_bytes().replace(b'\r\n', b'\n')
            entries.append((p.name.encode(), b'100644 ' + p.name.encode() + b'\0' + bytes.fromhex(git_blob(raw))))
    raw = b''.join(item for _, item in sorted(entries))
    return hashlib.sha1(b'tree ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()

def finite_nonnegative(value: Any) -> bool:
    return type(value) in (float, int) and math.isfinite(value) and value >= 0
