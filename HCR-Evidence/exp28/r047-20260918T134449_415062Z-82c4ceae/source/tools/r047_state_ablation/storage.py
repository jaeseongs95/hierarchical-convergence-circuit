"""Strict JSON and append-only storage. No network or corrective writes."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
from typing import Any

class EvidenceError(ValueError):
    pass

def require(ok: bool, message: str) -> None:
    if not ok:
        raise EvidenceError(message)

def _pairs(items):
    out = {}
    for k, v in items:
        require(k not in out, 'duplicate JSON key: ' + k)
        out[k] = v
    return out

def finite(value: Any) -> None:
    if isinstance(value, dict):
        require(all(type(k) is str for k in value), 'non-string JSON key')
        for v in value.values(): finite(v)
    elif isinstance(value, (list, tuple)):
        for v in value: finite(v)
    elif type(value) is float:
        require(math.isfinite(value), 'nonfinite number')

def loads(data: str | bytes):
    def reject(x): raise EvidenceError('nonfinite JSON: ' + x)
    obj = json.loads(data, object_pairs_hook=_pairs, parse_constant=reject)
    finite(obj)
    return obj

def canonical(obj: Any) -> bytes:
    finite(obj)
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def digest(obj: Any) -> str:
    return sha(canonical(obj))

def safe(path: str | Path) -> Path:
    p = Path(os.path.abspath(Path(path).expanduser()))
    for x in (p, *p.parents):
        require(not x.is_symlink() and not (hasattr(x, 'is_junction') and x.is_junction()),
                'symlink/junction is not permitted: ' + str(x))
    return p

def child(root: Path, name: str) -> Path:
    require(type(name) is str and name and '\\' not in name and ':' not in name,
            'invalid inventory path')
    q = PurePosixPath(name)
    require(not q.is_absolute() and all(x not in ('', '.', '..') for x in name.split('/')),
            'path traversal/empty component')
    base = safe(root); p = safe(base.joinpath(*q.parts))
    require(p.is_relative_to(base), 'outside inventory root')
    return p

def load(path: str | Path):
    return loads(safe(path).read_bytes())

def write(path: str | Path, data: bytes) -> None:
    p = safe(path); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())

def put(path: str | Path, obj: Any) -> None:
    write(path, canonical(obj) + b'\n')

def file_hash(path: str | Path) -> str:
    h = hashlib.sha256()
    with safe(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()

def text_hash(path: str | Path) -> str:
    return sha(safe(path).read_bytes().replace(b'\r\n', b'\n'))

def inventory(root: str | Path) -> list[str]:
    root = safe(root); out = []
    for p in root.rglob('*'):
        safe(p)
        if p.is_file(): out.append(p.relative_to(root).as_posix())
    return sorted(out)

def append_event(stream, obj: dict) -> None:
    stream.write(canonical(obj).decode('utf-8') + '\n')
    stream.flush(); os.fsync(stream.fileno())
