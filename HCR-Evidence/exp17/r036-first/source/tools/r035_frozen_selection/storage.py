"""추가 전용 evidence I/O. 중복 JSON 키, NaN, 경로 탈출, 덮어쓰기를 거부한다."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat


def safe(path):
    p = Path(os.path.abspath(path))
    for x in (*reversed(p.parents), p):
        try: s = x.lstat()
        except FileNotFoundError: continue
        if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024):
            raise ValueError('symlink/reparse point 금지: '+str(x))
    return p


def child(root, name):
    if not isinstance(name, str): raise ValueError('상대 경로 형식')
    rel = PurePosixPath(name)
    if not name or rel.is_absolute() or str(rel) != name or '..' in rel.parts or '\\' in name or ':' in name:
        raise ValueError('안전하지 않은 상대 경로: '+name)
    return safe(Path(root).joinpath(*rel.parts))


def loads(text):
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d: raise ValueError('중복 JSON 키: '+k)
            d[k] = v
        return d
    def bad(x): raise ValueError('유한하지 않은 JSON 상수: '+x)
    return json.loads(text, object_pairs_hook=pairs, parse_constant=bad)


def read(path, max_bytes=256*1024*1024):
    with safe(path).open('rb') as f: data = f.read(max_bytes+1)
    if len(data) > max_bytes: raise ValueError('evidence 파일 크기 한도')
    return data


def load(path): return loads(read(path).decode('utf-8'))
def sha_bytes(data): return hashlib.sha256(data).hexdigest()
def file_hash(path): return sha_bytes(read(path))
def text_hash(path): return sha_bytes(read(path).replace(b'\r\n', b'\n'))


def put_bytes(path, data):
    p = safe(path); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f: f.write(data); f.flush(); os.fsync(f.fileno())


def put(path, obj):
    put_bytes(path, (json.dumps(obj, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8'))


def inventory(root):
    root = safe(root)
    return {p.relative_to(root).as_posix() for p in root.rglob('*') if safe(p).is_file()}
