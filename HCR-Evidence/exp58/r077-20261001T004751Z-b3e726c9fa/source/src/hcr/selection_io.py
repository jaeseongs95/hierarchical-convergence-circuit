"""EXP-15 전용 append-only 파일 입출력. 기존 evidence를 덮어쓰지 않는다."""
from __future__ import annotations
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import stat


def safe(path: Path) -> Path:
    path=Path(os.path.abspath(path))
    for p in (*reversed(path.parents),path):
        try:s=p.lstat()
        except FileNotFoundError:continue
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024):
            raise ValueError('symlink/reparse point is not an evidence path: '+str(p))
    return path


def child(root,relative):
    p=PurePosixPath(relative)
    if not relative or p.is_absolute() or '..' in p.parts or '\\' in relative or ':' in relative:
        raise ValueError('unsafe evidence relative path')
    return safe(Path(root).joinpath(*p.parts))


def loads(raw):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('duplicate JSON key: '+k)
            d[k]=v
        return d
    def bad(x):raise ValueError('non-finite JSON literal: '+x)
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)


def read(path,limit=256*1024*1024):
    p=safe(path)
    with p.open('rb') as f:data=f.read(limit+1)
    if len(data)>limit:raise ValueError('evidence size bound exceeded')
    return data


def load(path):return loads(read(path).decode('utf-8'))
def checksum(path):return hashlib.sha256(read(path)).hexdigest()


def put_bytes(path,data):
    p=safe(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:
        f.write(data);f.flush();os.fsync(f.fileno())


def put(path,obj):
    put_bytes(path,(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8'))


def inventory(root):
    result=set()
    for p in safe(root).rglob('*'):
        safe(p)
        if p.is_file():result.add(p.relative_to(root).as_posix())
    return result
