"""새 파일에만 기록한다. JSON 중복키/NaN·경로 탈출·symlink는 거부한다."""
from __future__ import annotations
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
from .contracts import require


def _pairs(items):
    result = {}
    for k, v in items:
        require(k not in result, 'JSON 중복키: ' + k)
        result[k] = v
    return result


def loads(text):
    def bad(value):
        raise ValueError('비유한 JSON 상수: ' + value)
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=bad)


def safe(path) -> Path:
    p = Path(path).expanduser().absolute()
    require(not any(x.is_symlink() for x in (p, *p.parents)), 'symlink 경로 금지')
    return p.resolve()


def child(root, name: str) -> Path:
    require(isinstance(name, str) and '\\' not in name and ':' not in name and
            not PurePosixPath(name).is_absolute() and all(x not in ('', '.', '..') for x in name.split('/')),
            '상대 파일 경로 형식')
    root = safe(root); result = safe(root/name)
    require(root in result.parents, '경로 탈출')
    return result


def read(path) -> bytes:
    return safe(path).read_bytes()


def load(path):
    return loads(read(path).decode('utf-8'))


def bytes_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path) -> str:
    return bytes_hash(read(path))


def text_hash(path) -> str:
    return bytes_hash(read(path).replace(b'\r\n', b'\n'))


def write_bytes(path, data: bytes) -> None:
    p = safe(path); p.parent.mkdir(parents=True, exist_ok=True)
    # 'x'로 기존 성공/실패/계획을 덮어쓰지 않는다. 중간 실패 파일도 삭제하지 않는다.
    with p.open('xb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())


def put(path, value) -> None:
    write_bytes(path, (json.dumps(value, ensure_ascii=False, sort_keys=True,
                 separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8'))


def inventory(root) -> set[str]:
    root = safe(root); names = set()
    for p in root.rglob('*'):
        require(not p.is_symlink(), 'symlink inventory')
        if p.is_file():
            names.add(p.relative_to(root).as_posix())
    return names


def disjoint(a, b) -> None:
    a, b = safe(a), safe(b)
    require(a != b and a not in b.parents and b not in a.parents, '입력/출력 경로 중첩 금지')


def write_failure(root, payload: dict) -> None:
    """잘못된 비JSON 중간 상태도 보정하지 않고 repr 원문과 별도 오류로 보존한다."""
    try:
        json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        write_bytes(safe(root)/'failure-partial.repr.txt', repr(payload).encode('utf-8', errors='backslashreplace'))
        reduced = {k:v for k,v in payload.items() if k != 'partial_evidence'}
        reduced['partial_evidence_serialization_error'] = repr(exc)
        reduced['partial_evidence_raw_repr'] = 'failure-partial.repr.txt'
        put(safe(root)/'failure.json', reduced)
    else:
        put(safe(root)/'failure.json', payload)
