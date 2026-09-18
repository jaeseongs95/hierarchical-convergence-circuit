"""Self-contained additive installer. Complete preflight before writes; no overwrite/rollback/retry."""
from __future__ import annotations
import argparse,hashlib,json,os,sys,zipfile
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from uuid import uuid4

R045_BLOB='7698b7b3675a8ff3599858f3fe8689277304a14a'
BASE='3f07c81e27984e712f8cf3dc4b52ab2194dfbc53'

def fail(ok,msg):
    if not ok:raise ValueError(msg)

def safe(p):
    p=Path(os.path.abspath(p))
    for q in (p,*p.parents):fail(not q.is_symlink() and not (hasattr(q,'is_junction') and q.is_junction()),'link/junction path: '+str(q))
    return p

def sha(b):return hashlib.sha256(b).hexdigest()

def strict(raw):
    def pairs(items):
        out={}
        for k,v in items:fail(k not in out,'duplicate JSON key');out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs)

def check_name(n):
    fail(isinstance(n,str) and n and '\\' not in n and ':' not in n and '\0' not in n,'archive path')
    fail(not PurePosixPath(n).is_absolute() and all(x not in ('','.','..') for x in n.split('/')),'archive escape')
    permitted=(n in ('R046_MANIFEST.json','R046_README.ko.md','Run-HCR-R046.py','Run-HCR-R046.cmd') or
        n.startswith(('tools/r046_thought_carry/','validation/r046/','docs/R046_','experiments/exp-27-thought-carry/')) or
        (n.startswith('scripts/') and '/' not in n[8:] and 'r046' in n))
    fail(permitted,'not an additive R046 path: '+n)

def payload(path):
    result={}
    with zipfile.ZipFile(path) as z:
        infos=z.infolist();fail(len(infos)<300,'archive item budget')
        fail(sum(i.file_size for i in infos)<20*1024**2,'archive size budget')
        for info in infos:
            n=info.filename;check_name(n)
            fail(n not in result and not info.is_dir(),'duplicate/directory ZIP entry')
            fail((info.external_attr>>16)&0o170000!=0o120000,'archive symlink')
            result[n]=z.read(info)
        fail(z.testzip() is None,'ZIP CRC')
    fail('R046_MANIFEST.json' in result,'missing release manifest')
    m=strict(result['R046_MANIFEST.json'])
    fail(set(m)=={'schema','basis_commit','files'} and m['schema']=='hcr-r046-additive-v1' and m['basis_commit']==BASE,'release schema')
    fail(set(result)==set(m['files'])|{'R046_MANIFEST.json'},'archive inventory')
    for n,h in m['files'].items():fail(sha(result[n].replace(b'\r\n',b'\n'))==h,'payload checksum: '+n)
    return result

def install(root,archive):
    root=safe(root);data=payload(archive)
    b=safe(root/'R045_MANIFEST.json').read_bytes().replace(b'\r\n',b'\n')
    fail(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==R045_BLOB,'R045 baseline with HF1 schema fix required')
    # Complete conflict scan first. Neither old research files nor modified R046 files are overwritten.
    for n,b in data.items():
        p=safe(root/Path(*PurePosixPath(n).parts))
        if p.exists():fail(p.is_file() and p.read_bytes().replace(b'\r\n',b'\n')==b.replace(b'\r\n',b'\n'),'existing file conflict: '+n)
    tag=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')+'-'+uuid4().hex[:8]
    log=root/'HCR-Evidence/deployments'/('r046-'+tag);log.mkdir(parents=True,exist_ok=False)
    with (log/'install.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        def event(v):f.write(json.dumps(v,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
        event(dict(event='preflight_passed',payload_sha256=sha(Path(archive).read_bytes()),files=len(data)))
        try:
            for n,b in data.items():
                p=safe(root/Path(*PurePosixPath(n).parts))
                if p.exists():event(dict(event='existing_identical',path=n));continue
                p.parent.mkdir(parents=True,exist_ok=True)
                with p.open('xb') as out:out.write(b);out.flush();os.fsync(out.fileno())
                event(dict(event='installed',path=n,sha256=sha(b)))
            event(dict(event='complete',automatic_retry=False))
        except BaseException as exc:
            event(dict(event='first_failure',error_type=type(exc).__name__,error=str(exc),automatic_retry=False));raise
    return dict(installed=True,files=len(data),log=str(log))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=Path);p.add_argument('--archive',required=True,type=Path)
    a=p.parse_args();fail(sys.version_info>=(3,12),'Python >=3.12 required');print(json.dumps(install(a.repo,a.archive),ensure_ascii=False))
