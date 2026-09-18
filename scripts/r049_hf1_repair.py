"""Transactional R049 HF1 installer. Never changes native, prior evidence or experiment design.

The original release and every permitted patch file are verified before diagnosis.
Real local native diagnosis and the complete new test suite precede source changes.
Per-file replacement uses os.replace; multi-file atomicity is NOT claimed.
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
from uuid import uuid4
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import traceback
import zipfile

BASE='426ad699235935a97b74b1dcd1acbcd4890313b2'
ORIGINAL_MANIFEST_SEMANTIC_SHA='d790f3b1838ec76bfdfa6c1be567af1df696c166d2939a6d69cb9aa8a754b61e'
CHANGE_FILE='docs/R049_HF1_CHANGE.json'
MANIFEST='R049_MANIFEST.json'
CHANGED={'tools/r049_signal_boundary/evaluate.py','tools/r049_signal_boundary/reporting.py',
         'tools/r049_signal_boundary/tests/test_r049_device.py'}
ADDED={'tools/r049_signal_boundary/regression.py','tools/r049_signal_boundary/tests/test_r049_hf1.py',
       'docs/R049_HF1_EXPLORATION.json','docs/R049_HF1_CHANGE.json','docs/R049_HF1_README.ko.md',
       'scripts/r049_hf1_probe.py','scripts/r049_hf1_repair.py','scripts/r049_hf1_launch.ps1'}
NATIVE={'src/hcr/__init__.py':'ea6ccdd983eb195aaefb8898057f4fb2493a95f1',
 'src/hcr/model.py':'89e90e7f32e8cf388bbb0f7c7213b4261dc606b4',
 'src/hcr/binding.py':'44aa43f2fd4be7aa3af0b9183f03e1fe5b748d37',
 'src/hcr/codec.py':'44eac9a84681b7ba919fa3cf737ab0dbff8477e1',
 'src/hcr/identity.py':'0214cfe5bf7a5c2d41ca5e353e3f0d880fee374b',
 'src/hcr/workspace.py':'52bc9338f43078bc11835491d5baf80d16195809',
 'src/hcr/dynamics.py':'53de614846489a531f4a8d463fc17eabe1e5a6ca',
 'src/hcr/proof.py':'119c35031a97d57bc8e2c874332e8b9e1ecf6b7a'}


def require(ok,message):
    if not ok:raise ValueError(message)

def sha(b):return hashlib.sha256(b).hexdigest()
def lf(b):return b.replace(b'\r\n',b'\n')
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def encode(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def semantic(x):return sha(encode(x))

def loads(raw):
    def pairs(xs):
        d={}
        for k,v in xs:require(k not in d,'duplicate JSON key');d[k]=v
        return d
    def reject(x):raise ValueError('nonfinite JSON '+x)
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)

def safe(path):
    p=Path(os.path.abspath(path))
    for x in (p,*p.parents):
        require(not x.is_symlink() and not (hasattr(x,'is_junction') and x.is_junction()),'link/junction: '+str(x))
    return p

def child(root,name):
    require(type(name) is str and name and not PurePosixPath(name).is_absolute() and
        not any(c in name for c in ('\\',':','\n','\r','\0')) and
        all(p not in ('','.','..','.git') for p in name.split('/')),'unsafe relative path: '+str(name))
    root=safe(root);p=safe(root.joinpath(*name.split('/')));require(p.is_relative_to(root),'path outside root');return p

def write(path,data):
    path=safe(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())

def put(path,x):write(path,encode(x)+b'\n')

def read_package(archive):
    files={};seen=set();total=0
    with zipfile.ZipFile(archive) as z:
        for e in z.infolist():
            n=e.filename;child(Path.cwd(),n)
            require(n.casefold() not in seen and not e.is_dir(),'duplicate/directory entry');seen.add(n.casefold())
            require((e.external_attr>>16)&0o170000!=0o120000,'zip symlink')
            total+=e.file_size;require(e.file_size<=5*1024**2 and total<=32*1024**2,'archive budget')
            files[n]=z.read(e)
    require(MANIFEST in files and CHANGE_FILE in files,'missing HF1 release files')
    m=loads(files[MANIFEST]);cert=loads(files[CHANGE_FILE]);old=cert['original_manifest']
    require(semantic(old)==ORIGINAL_MANIFEST_SEMANTIC_SHA,'original release identity changed')
    require(set(m)=={'schema','base_commit','files'} and m['schema']=='hcr-r049-release-v1' and m['base_commit']==BASE,'patched release schema')
    require(set(m['files'])==set(old['files'])|ADDED and set(files)==set(m['files'])|{MANIFEST},'patch inventory')
    require(set(cert['changed_existing_files'])==CHANGED and set(cert['added_files'])==ADDED,'unauthorized change scope')
    for n,h in m['files'].items():
        require(sha(lf(files[n]))==h,'patch source checksum: '+n)
        if n in old['files'] and n not in CHANGED:require(h==old['files'][n],'protected source changed: '+n)
    require(sha(files['docs/R049_HF1_EXPLORATION.json'])==
        loads(files['docs/R049_PRIOR_EXPLORATION.json'])['source_sha256'],'exploration provenance')
    return files,m,old

def baseline(repo):
    require(sys.version_info>=(3,12),'Existing Python 3.12+ is required')
    def git(*args):
        p=subprocess.run(['git','-C',str(repo),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        require(p.returncode==0,'Git baseline: '+p.stderr.decode('utf-8','replace'))
        return p.stdout.decode('utf-8').strip()
    require(Path(git('rev-parse','--show-toplevel')).resolve()==repo.resolve(),'not repository root')
    head=git('rev-parse','HEAD');git('merge-base','--is-ancestor',BASE,head)
    raw=lf((repo/'R048_MANIFEST.json').read_bytes())
    require(blob(raw)=='b7a2acd87277d0218ae4a08ae510e1f842d93b74','R048 manifest changed')
    inherited=loads(raw)
    for n,h in inherited['files'].items():require(sha(lf(child(repo,n).read_bytes()))==h,'R048 source changed: '+n)
    for n,h in NATIVE.items():require(blob(lf(child(repo,n).read_bytes()))==h,'native source changed: '+n)
    return head,inherited

def inspect_current(repo,files,m,old):
    current=loads((repo/MANIFEST).read_bytes())
    require(current==old or current==m,'unknown current R049 manifest; refusing to rebaseline edits')
    before={};pending=[]
    for n,data in files.items():
        p=child(repo,n);b=p.read_bytes() if p.exists() else None;before[n]=b
        if n==MANIFEST:pass
        elif n in old['files']:
            allowed={old['files'][n]}
            if n in CHANGED:allowed.add(m['files'][n])
            require(b is not None and sha(lf(b)) in allowed,'unexpected R049 edit/missing original: '+n)
        elif b is not None:require(sha(lf(b))==m['files'][n],'unexpected existing HF1 addition: '+n)
        if b is None or (loads(b)!=m if n==MANIFEST else lf(b)!=lf(data)):pending.append(n)
    # The manifest is always installed last, after every declared file exists.
    pending=sorted(n for n in pending if n!=MANIFEST)+([MANIFEST] if MANIFEST in pending else [])
    return before,pending

def invoke(args,cwd,log):
    with safe(log).open('xb') as f:
        p=subprocess.run(args,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1'))
    if p.returncode:
        print('\n'.join(log.read_text(encoding='utf-8',errors='replace').splitlines()[-45:]),flush=True)
    require(p.returncode==0,'subprocess failed; preserved log: '+str(log))
    return dict(returncode=p.returncode,log=log.name,sha256=sha(log.read_bytes()))

def replace_file(path,data):
    path=safe(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name('.'+path.name+'.hf1-'+uuid4().hex[:8]+'.tmp')
    try:
        write(temp,data);require(temp.read_bytes()==data,'temporary write mismatch')
        os.replace(temp,path);require(path.read_bytes()==data,'installed bytes mismatch')
    finally:
        if temp.exists():temp.unlink()

def apply(repo,files,before,pending,journal,verify):
    put(journal/'transaction.json',dict(pending=pending,original_bytes={n:None if before[n] is None else sha(before[n]) for n in pending},multi_file_atomic=False))
    for n in pending:
        if before[n] is not None:write(child(journal/'backup',n),before[n])
    touched=[]
    try:
        with (journal/'writes.jsonl').open('xb') as stream:
            for n in pending:
                p=child(repo,n);b=p.read_bytes() if p.exists() else None
                require(b==before[n],'concurrent edit before replacement: '+n)
                touched.append(n);replace_file(p,files[n])
                stream.write(encode(dict(path=n,sha256=sha(files[n])))+b'\n');stream.flush();os.fsync(stream.fileno())
        verify()
    except BaseException:
        rollback=[]
        for n in reversed(touched):
            try:
                p=child(repo,n);current=p.read_bytes() if p.exists() else None
                require(current in (files[n],before[n]),'concurrent edit; rollback refuses overwrite')
                if before[n] is None:
                    if p.exists():p.unlink()
                elif current!=before[n]:replace_file(p,before[n])
                rollback.append(dict(path=n,restored=True))
            except BaseException as error:rollback.append(dict(path=n,restored=False,message=str(error)))
        put(journal/'rollback.json',dict(files=rollback,complete=all(x['restored'] for x in rollback)))
        raise

def repair(repo,archive,launch=True):
    repo=safe(repo);archive=safe(archive)
    journal=repo/'HCR-Evidence/deployments'/('r049-hf1-'+uuid4().hex[:10]);journal.mkdir(parents=True,exist_ok=False)
    installed=False
    try:
        put(journal/'started.json',dict(package_sha256=sha(archive.read_bytes()),automatic_retry=False,
            python=sys.version,old_runs_modified=False))
        files,m,old=read_package(archive);head,inherited=baseline(repo)
        before,pending=inspect_current(repo,files,m,old)
        put(journal/'preflight.json',dict(head=head,pending=pending,already_patched=not pending))
        stage=journal/'st';parent_source=journal/'base'
        for n in sorted(set(inherited['files'])|{ 'R048_MANIFEST.json' }|set(NATIVE)):
            b=child(repo,n).read_bytes();write(child(stage,n),b);write(child(parent_source,n),b)
        for n,b in files.items():write(child(stage,n),b)
        probe=stage/'scripts/r049_hf1_probe.py'
        prefix=[sys.executable,'-X','utf8','-B',str(probe)]
        invoke(prefix+['--root',str(stage),'--mode','diagnose','--out',str(journal/'diagnosis.json')],stage/'src',journal/'diagnosis.txt')
        diagnosis=loads((journal/'diagnosis.json').read_bytes())
        print('Local reference diagnosis: '+diagnosis['diagnosis'],flush=True)
        print('Saved details: '+str(journal/'diagnosis.json'),flush=True)
        invoke([sys.executable,'-X','utf8','-B',str(stage/'scripts/r049_tests.py'),'--root',str(stage),'--suite','new'],stage/'src',journal/'tests-staged.txt')
        invoke(prefix+['--root',str(stage),'--mode','snapshot','--parent-source',str(parent_source),'--snapshot',str(journal/'snap-before'),
            '--out',str(journal/'snapshot-before.json')],stage/'src',journal/'snapshot-before.txt')
        # Recheck every original or staged addition before changing the first source file.
        for n,b in before.items():require((child(repo,n).read_bytes() if child(repo,n).exists() else None)==b,'source changed during validation: '+n)
        def verify_installed():
            cmd=[sys.executable,'-X','utf8','-B',str(repo/'scripts/r049_hf1_probe.py')]
            invoke(cmd+['--root',str(repo),'--mode','snapshot','--parent-source',str(parent_source),'--snapshot',str(journal/'snap-after'),
                '--out',str(journal/'snapshot-after.json')],repo/'src',journal/'snapshot-after.txt')
        apply(repo,files,before,pending,journal,verify_installed);installed=True
        put(journal/'installed.json',dict(changed_files=pending,source_and_manifest_verified=True,
            native_changed=False,experiment_conditions_changed=False,old_runs_modified=False))
        print('HF1 installed and snapshot verified: '+str(journal),flush=True)
        if launch:
            p=subprocess.run([sys.executable,'-X','utf8','-B',str(repo/'Run-HCR-R049.py')],cwd=repo,
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1'))
            put(journal/'launch_result.json',dict(returncode=p.returncode,automatic_retry=False))
            return p.returncode
        return 0
    except BaseException as error:
        put(journal/'failure.json',dict(error_type=type(error).__name__,message=str(error),traceback=traceback.format_exc(),
            installed=installed,automatic_retry=False,first_failure_preserved=True))
        print('HF1 stopped; diagnostic and backup preserved: '+str(journal),file=sys.stderr,flush=True)
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--launch',action='store_true');a=p.parse_args();raise SystemExit(repair(a.repo,a.archive,a.launch))
