"""Strict append-only files, sealed inventories, and portable subprocess helpers."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import hashlib
import json
import math
import os
import subprocess
import sys
import traceback

class ContractError(ValueError): pass

def require(condition, message):
    if not condition: raise ContractError(message)

def _pairs(items):
    out={}
    for k,v in items:
        require(k not in out,'duplicate JSON key: '+k);out[k]=v
    return out

def finite(x):
    if isinstance(x,dict):
        require(all(type(k) is str for k in x),'JSON key type')
        for v in x.values():finite(v)
    elif isinstance(x,(list,tuple)):
        for v in x:finite(v)
    elif type(x) is float:require(math.isfinite(x),'nonfinite number')

def loads(raw):
    def reject(x):raise ContractError('nonfinite JSON '+x)
    value=json.loads(raw,object_pairs_hook=_pairs,parse_constant=reject);finite(value);return value

def encode(obj):
    finite(obj)
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def sha(data):return hashlib.sha256(data).hexdigest()
def digest(obj):return sha(encode(obj))
def blob(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def lf(data):return data.replace(b'\r\n',b'\n')
def now():return datetime.now(timezone.utc).isoformat()

def safe(path):
    p=Path(os.path.abspath(Path(path).expanduser()))
    for x in (p,*p.parents):
        require(not x.is_symlink() and not (hasattr(x,'is_junction') and x.is_junction()),'link/junction: '+str(x))
    return p

def child(root,name):
    require(type(name) is str and name and not any(x in name for x in ('\\',':','\0','\n','\r')),'unsafe relative path')
    q=PurePosixPath(name)
    require(not q.is_absolute() and all(x not in ('','.','..') for x in name.split('/')),'path traversal')
    r=safe(root);p=safe(r.joinpath(*q.parts));require(p.is_relative_to(r),'path outside root');return p

def read(path):return safe(path).read_bytes()
def load(path):return loads(read(path))

def write(path,data):
    p=safe(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())

def put(path,obj):write(path,encode(obj)+b'\n')

def append(f,obj):
    f.write(encode(obj)+b'\n');f.flush();os.fsync(f.fileno())

def names(root):
    r=safe(root);out=[]
    for p in r.rglob('*'):
        safe(p)
        if p.is_file():out.append(p.relative_to(r).as_posix())
    return sorted(out)

def hashes(root,selected=None):
    return {n:sha(read(child(root,n))) for n in sorted(names(root) if selected is None else selected)}

def verify_files(root,expected,exact=True,extra=()):
    actual=set(names(root));missing=sorted(set(expected)-actual)
    changed=[n for n in sorted(set(expected)&actual) if sha(read(child(root,n)))!=expected[n]]
    unexpected=sorted(actual-set(expected)-set(extra)) if exact else []
    require(not missing and not changed and not unexpected,
            'file integrity: '+json.dumps(dict(missing=missing,changed=changed,unexpected=unexpected),ensure_ascii=False))
    return dict(verified=True,files=len(expected))

def failure(root,stage,exc):
    target=safe(root)/'failure.json'
    if target.exists():return
    classification=('interrupted' if isinstance(exc,KeyboardInterrupt) else
        'contract_or_audit_failure' if isinstance(exc,ValueError) else
        'parsing_failure' if isinstance(exc,UnicodeError) else 'runtime_failure')
    put(target,dict(stage=stage,classification=classification,error_type=type(exc).__name__,message=str(exc),
                   traceback=traceback.format_exc(),created_utc=now(),automatic_retry=False))

def command(args,cwd,log=None,env=None,timeout=None):
    if log is None:
        p=subprocess.run(args,cwd=cwd,env=env,input=None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
        require(p.returncode==0,'command failed: '+repr(args)+'\n'+p.stderr.decode('utf-8','replace'))
        return p.stdout
    with safe(log).open('xb') as f:
        p=subprocess.run(args,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    if p.returncode:
        # Expose the underlying failure instead of only "self-test failed".
        tail=read(log).decode('utf-8','replace').splitlines()[-45:]
        print('\n'.join(tail),file=sys.stderr,flush=True)
        raise ContractError(f'command returned {p.returncode}; full log: {log}')
    return dict(returncode=0,log=Path(log).name,sha256=sha(read(log)))
