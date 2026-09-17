"""표준 라이브러리만 사용하는 strict JSON, 경로 경계, append-only 파일 IO."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
from typing import Any


class ContractError(ValueError):
    """입력/계획/계보/출력 계약 위반. 실패를 자동 보정하지 않는다."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, '중복 JSON key: ' + key)
        result[key] = value
    return result


def _reject_constant(value):
    raise ContractError('비유한 JSON 숫자: ' + value)


def _finite_tree(value):
    if isinstance(value, dict):
        require(all(type(k) is str for k in value), 'JSON key는 문자열이어야 합니다.')
        for item in value.values():
            _finite_tree(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _finite_tree(item)
    elif type(value) is float:
        require(math.isfinite(value), '비유한 숫자는 evidence에 허용하지 않습니다.')


def loads(value: str | bytes) -> Any:
    result = json.loads(value, object_pairs_hook=_pairs, parse_constant=_reject_constant)
    _finite_tree(result)
    return result


def canonical(value: Any) -> bytes:
    _finite_tree(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def bytes_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe(path: str | Path) -> Path:
    original = Path(path).expanduser()
    require(not any(p.is_symlink() for p in (original, *original.parents)), 'symlink 경로 금지: ' + str(path))
    result = Path(os.path.abspath(original))
    require(not any(p.is_symlink() for p in (result, *result.parents)), 'symlink 경로 금지: ' + str(path))
    return result


def child(root: str | Path, name: str) -> Path:
    require(type(name) is str and name and '\\' not in name and ':' not in name and '\x00' not in name,
            '잘못된 상대 경로')
    require(all(p not in ('', '.', '..') for p in name.split('/')), '경로 탈출/빈 component 금지')
    relative = PurePosixPath(name)
    require(not relative.is_absolute(), '절대 inventory 경로 금지')
    base = safe(root)
    target = safe(base.joinpath(*relative.parts))
    require(target.is_relative_to(base), '경로 경계 위반')
    return target


def disjoint(a: str | Path, b: str | Path) -> None:
    a, b = safe(a), safe(b)
    require(not a.is_relative_to(b) and not b.is_relative_to(a), '원자료와 출력 경로가 겹칩니다.')


def read(path: str | Path) -> bytes:
    return safe(path).read_bytes()


def load(path: str | Path) -> Any:
    return loads(read(path))


def file_hash(path: str | Path) -> str:
    h = hashlib.sha256()
    with safe(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def text_hash(path: str | Path) -> str:
    # Git checkout의 CRLF/LF만 정규화한다. Evidence bytes에는 적용하지 않는다.
    return bytes_hash(read(path).replace(b'\r\n', b'\n'))


def write_bytes(path: str | Path, data: bytes) -> None:
    target = safe(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def put(path: str | Path, value: Any) -> None:
    write_bytes(path, canonical(value) + b'\n')


def inventory(root: str | Path) -> set[str]:
    root = safe(root)
    result = set()
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'inventory symlink 금지: ' + str(path))
        if path.is_file():
            result.add(path.relative_to(root).as_posix())
    return result
