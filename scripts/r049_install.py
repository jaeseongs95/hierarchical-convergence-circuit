"""Additive R049 installer. No existing source rewrite or automatic dependency install."""
from __future__ import annotations
from pathlib import Path, PurePosixPath
from uuid import uuid4
import argparse
import hashlib
import json
import os
import subprocess
import sys
import traceback
import zipfile

BASE='426ad699235935a97b74b1dcd1acbcd4890313b2'

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(b):return hashlib.sha256(b).hexdigest()

def safe(path):
    p=Path(os.path.abspath(path))
    for x in (p,*p.parents):
        require(not x.is_symlink() and not (hasattr(x,'is_junction') and x.is_junction()),'link/junction path: '+str(x))
    return p

def encode(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')

def put(path,value):
    path=safe(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(encode(value));f.flush();os.fsync(f.fileno())

def read_archive(path):
    entries={};seen=set();total=0
    with zipfile.ZipFile(path) as z:
        for item in z.infolist():
            name=item.filename;parts=name.split('/')
            require(name and not PurePosixPath(name).is_absolute() and not any(c in name for c in ('\\',':','\n','\r','\0'))
                and all(p not in ('','.','..','.git') for p in parts),'unsafe ZIP entry')
            require(name.casefold() not in seen and not item.is_dir(),'duplicate/directory ZIP entry')
            require((item.external_attr>>16)&0o170000 != 0o120000,'ZIP symlink')
            seen.add(name.casefold());total+=item.file_size
            require(item.file_size<=5*1024**2 and total<=32*1024**2,'ZIP expansion budget')
            entries[name]=z.read(item)
    def pairs(xs):
        d={}
        for k,v in xs:require(k not in d,'duplicate manifest key');d[k]=v
        return d
    m=json.loads(entries['R049_MANIFEST.json'],object_pairs_hook=pairs)
    require(set(m)=={'schema','base_commit','files'} and m['base_commit']==BASE and m['schema']=='hcr-r049-release-v1','release schema')
    require(set(entries)==set(m['files'])|{'R049_MANIFEST.json'},'release inventory')
    for name,h in m['files'].items():
        require(sha(entries[name].replace(b'\r\n',b'\n'))==h,'source checksum: '+name)
        require(name.startswith(('tools/r049_signal_boundary/','scripts/r049_','docs/R049_','HCR-Evidence/exp30/'))
                or name in ('Run-HCR-R049.py','Run-HCR-R049.cmd','R049_README.ko.md'), 'out-of-scope package write: '+name)
    return entries,m


def preflight(repo,entries):
    require(sys.version_info>=(3,12),'use the existing Python 3.12 or newer')
    def git(*args):
        p=subprocess.run(['git','-C',str(repo),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        require(p.returncode==0,'git baseline failure: '+p.stderr.decode('utf-8','replace'))
        return p.stdout.decode('utf-8').strip()
    require(Path(git('rev-parse','--show-toplevel')).resolve()==repo.resolve(),'not the repository root')
    head=git('rev-parse','HEAD');git('merge-base','--is-ancestor',BASE,head)
    missing=[]
    for name,data in entries.items():
        target=safe(repo.joinpath(*name.split('/')))
        require(target.is_relative_to(repo),'outside repository')
        if target.exists():
            require(target.is_file() and target.read_bytes().replace(b'\r\n',b'\n')==data.replace(b'\r\n',b'\n'),
                    'refusing to overwrite an existing different file: '+name)
        else:missing.append(name)
    return head,missing


def install(repo,archive,launch=False):
    repo=safe(repo);archive=safe(archive)
    journal=repo/'HCR-Evidence/deployments'/('r049-install-'+uuid4().hex[:12]);journal.mkdir(parents=True,exist_ok=False)
    created=[]
    try:
        put(journal/'started.json',dict(package_sha256=sha(archive.read_bytes()),automatic_retry=False))
        entries,m=read_archive(archive);head,pending=preflight(repo,entries)
        put(journal/'preflight.json',dict(head=head,planned_new_files=pending,unchanged_files=len(entries)-len(pending)))
        with (journal/'writes.jsonl').open('xb') as log:
            for name in pending:
                p=safe(repo.joinpath(*name.split('/')));p.parent.mkdir(parents=True,exist_ok=True)
                with p.open('xb') as f:f.write(entries[name]);f.flush();os.fsync(f.fileno())
                created.append(name);log.write(encode(dict(created=name,sha256=sha(entries[name]))));log.flush();os.fsync(log.fileno())
        # Validate actual installed bytes, not only the ZIP or an in-memory patch.
        for name,data in entries.items():
            require((repo/name).read_bytes().replace(b'\r\n',b'\n')==data.replace(b'\r\n',b'\n'),'post-install mismatch: '+name)
        put(journal/'installed.json',dict(created=created,old_source_files_modified=0,old_evidence_modified=False))
        print('Additive install journal: '+str(journal),flush=True)
        if launch:
            p=subprocess.run([sys.executable,'-X','utf8','-B',str(repo/'Run-HCR-R049.py')],cwd=repo)
            put(journal/'launch_result.json',dict(returncode=p.returncode,automatic_retry=False))
            return p.returncode
        return 0
    except BaseException as exc:
        put(journal/'failure.json',dict(error_type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),
            first_failure_preserved=True,files_created_before_failure=created,automatic_retry=False))
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--launch',action='store_true')
    args=parser.parse_args();raise SystemExit(install(args.repo,args.archive,args.launch))
