"""Standalone additive installer; validate every byte before writing any source file."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile


def require(ok,message):
    if not ok:raise ValueError(message)


def safe(path):
    p=Path(os.path.abspath(path))
    for x in (p,*p.parents):
        require(not x.is_symlink() and not (hasattr(x,'is_junction') and x.is_junction()),'symlink/junction path: '+str(x))
    return p


def sha(b):return hashlib.sha256(b).hexdigest()


def loads(data):
    def pairs(xs):
        d={}
        for k,v in xs:
            require(k not in d,'duplicate JSON key');d[k]=v
        return d
    return json.loads(data,object_pairs_hook=pairs)


def put(path,obj):
    path=safe(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(obj,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


def read_archive(archive):
    with zipfile.ZipFile(safe(archive)) as z:
        seen=set();payload={};total=0
        for e in z.infolist():
            n=e.filename;q=PurePosixPath(n)
            require(n and not q.is_absolute() and '\\' not in n and ':' not in n and '\x00' not in n and
                    all(c not in ('','.','..') for c in n.split('/')),'unsafe ZIP entry')
            require(n.casefold() not in seen,'case-insensitive duplicate ZIP entry');seen.add(n.casefold())
            require(not e.is_dir() and (e.external_attr>>16)&0o170000 != 0o120000,'ZIP symlink/directory')
            total+=e.file_size
            require(e.file_size<=5*1024**2 and total<=20*1024**2,'ZIP size limit')
            payload[n]=z.read(e)
    require('R047_MANIFEST.json' in payload,'missing release manifest')
    m=loads(payload['R047_MANIFEST.json'])
    require(set(m)=={'schema','base_commit','native_blobs','files'} and m['schema']=='hcr-r047-release-v1','release contract')
    require(set(payload)==set(m['files'])|{'R047_MANIFEST.json'},'release inventory mismatch')
    for n,h in m['files'].items():require(sha(payload[n].replace(b'\r\n',b'\n'))==h,'release checksum: '+n)
    return payload,m


def validate_target(repo,payload,m):
    repo=safe(repo)
    def git(*args):
        p=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,encoding='utf-8',timeout=15)
        require(p.returncode==0,'git baseline: '+p.stderr.strip());return p.stdout.strip()
    require(Path(git('rev-parse','--show-toplevel')).resolve()==repo.resolve(),'place OneClick in repository root')
    head=git('rev-parse','HEAD');git('merge-base','--is-ancestor',m['base_commit'],head)
    require(sys.version_info>=(3,12),'existing Python 3.12 or newer is required')
    for n,h in m['native_blobs'].items():
        b=safe(repo/n).read_bytes().replace(b'\r\n',b'\n')
        require(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==h,'native source drift: '+n)
    changes=[]
    for n,b in payload.items():
        target=safe(repo/n)
        require(target.is_relative_to(repo),'source escaped repository')
        if target.exists():
            require(target.is_file() and target.read_bytes().replace(b'\r\n',b'\n')==b.replace(b'\r\n',b'\n'),
                    'refusing to overwrite an existing different file: '+n)
        else:changes.append(n)
    return head,changes


def install(repo,archive):
    repo=safe(repo);deploy=repo/'HCR-Evidence'/'deployments'/('r047-install-'+uuid4().hex)
    deploy.mkdir(parents=True,exist_ok=False)
    applied=[]
    try:
        put(deploy/'started.json',dict(archive=str(safe(archive)),sha256=sha(safe(archive).read_bytes()),automatic_retry=False))
        payload,m=read_archive(archive);head,changes=validate_target(repo,payload,m)
        put(deploy/'preflight.json',dict(head=head,files_to_create=changes,files_unchanged=len(payload)-len(changes)))
        with (deploy/'applied.jsonl').open('x',encoding='utf-8',newline='\n') as journal:
            for n in changes:
                target=safe(repo/n);target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as f:f.write(payload[n]);f.flush();os.fsync(f.fileno())
                applied.append(n);journal.write(json.dumps({'created':n,'sha256':sha(payload[n])},ensure_ascii=False)+'\n');journal.flush();os.fsync(journal.fileno())
        put(deploy/'completed.json',dict(created=applied,unchanged=len(payload)-len(applied),native_files_modified=0))
        return deploy
    except BaseException as exc:
        put(deploy/'failure.json',dict(error_type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),
            first_failure_preserved=True,partially_created_files=applied,automatic_retry=False))
        raise


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--launch',action='store_true');a=p.parse_args()
    deploy=install(a.repo,a.archive);print('Additive install journal: '+str(deploy),flush=True)
    if a.launch:
        # One invocation. A failed experiment is not repeated with another interpreter.
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(safe(a.repo)/'Run-HCR-R047.py')],cwd=a.repo)
        put(deploy/'launch_result.json',dict(returncode=result.returncode,automatic_retry=False))
        return result.returncode
    return 0
if __name__=='__main__':sys.exit(main())
