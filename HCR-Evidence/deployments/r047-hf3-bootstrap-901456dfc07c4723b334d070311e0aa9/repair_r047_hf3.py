"""R047-HF3: authorized source/manifest migration, not hash-check bypass.

No network, installation, git writes, experiment retry, or parent evidence changes.
Python >=3.12; Windows launcher extracts and executes this stdlib-only program.
"""
from __future__ import annotations
import argparse
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import traceback
from uuid import uuid4

BASE = 'bdd24df2d783a1cea82a6050f4f793c9eb06ca0a'
PROTOCOL = 'tools/r047_state_ablation/protocol.py'
MANIFEST = 'R047_MANIFEST.json'
CERTIFICATE = 'docs/R047_HF3_RELEASE.json'
NATIVE = {
 'src/hcr/__init__.py':'ea6ccdd983eb195aaefb8898057f4fb2493a95f1',
 'src/hcr/model.py':'89e90e7f32e8cf388bbb0f7c7213b4261dc606b4',
 'src/hcr/binding.py':'44aa43f2fd4be7aa3af0b9183f03e1fe5b748d37',
 'src/hcr/codec.py':'44eac9a84681b7ba919fa3cf737ab0dbff8477e1',
 'src/hcr/identity.py':'0214cfe5bf7a5c2d41ca5e353e3f0d880fee374b',
 'src/hcr/workspace.py':'52bc9338f43078bc11835491d5baf80d16195809',
 'src/hcr/dynamics.py':'53de614846489a531f4a8d463fc17eabe1e5a6ca',
 'src/hcr/proof.py':'119c35031a97d57bc8e2c874332e8b9e1ecf6b7a',
}
OLD_CMD = "            cmd=[sys.executable,'-X','utf8','-B','-m','unittest','discover','-s','tools/r047_state_ablation/tests','-p','test_*.py','-v','-f']"
OLD_RUN = '                p=subprocess.run(cmd,cwd=repo,env=childenv,stdout=out,stderr=subprocess.STDOUT)'
NEW_RUN = "                p=subprocess.run(cmd,cwd=repo/'src',env=childenv,stdout=out,stderr=subprocess.STDOUT)"
TEST_DIR = "            tests_dir=repo/'tools'/'r047_state_ablation'/'tests'"
NEW_CMD = "            cmd=[sys.executable,'-X','utf8','-B','-m','unittest','discover','-s',str(tests_dir),'-p','test_*.py','-v','-f']"
MARKERS = {v: '            # '+v+': run tests from repo/src so root-level hcr.py cannot shadow src/hcr package.'
           for v in ('HF1','HF2','HF3')}

class RepairError(ValueError):
    pass

def require(ok, message):
    if not ok: raise RepairError(message)

def sha(data): return hashlib.sha256(data).hexdigest()
def lf(data):
    data.decode('utf-8', errors='strict')
    require(not data.startswith(b'\xef\xbb\xbf'), 'Unexpected UTF-8 BOM; refusing to normalize an unrecognized edit')
    return data.replace(b'\r\n', b'\n')
def text_sha(data): return sha(lf(data))
def canonical(obj): return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
def jd(obj): return canonical(obj)+b'\n'
def decode(data):
    def pairs(xs):
        out={}
        for k,v in xs:
            require(k not in out, 'Duplicate JSON key: '+k);out[k]=v
        return out
    def bad(s): raise RepairError('Nonfinite JSON: '+s)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=bad)
def safe(path):
    p=Path(os.path.abspath(path))
    for part in (p,*p.parents):
        require(not part.is_symlink() and not (hasattr(part,'is_junction') and part.is_junction()),
                'Symlink/junction is not permitted: '+str(part))
    return p

def relative(name):
    require(type(name) is str and name and '\\' not in name and ':' not in name and '\x00' not in name,
            'Unsafe inventory name')
    q=PurePosixPath(name)
    require(not q.is_absolute() and all(x not in ('','.','..') and x==x.rstrip(' .') for x in name.split('/')),
            'Unsafe inventory components: '+name)
    return q

def child(root,name):
    q=relative(name);base=safe(root);p=safe(base.joinpath(*q.parts))
    require(p.is_relative_to(base), 'Path outside repository')
    return p

def write_new(path,data):
    p=safe(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())

def put(path,obj): write_new(path,jd(obj))
def now(): return datetime.now(timezone.utc).isoformat()

def schema(m):
    require(type(m) is dict and set(m)=={'schema','base_commit','native_blobs','files'}, 'Unexpected release manifest fields')
    require(m['schema']=='hcr-r047-release-v1' and m['base_commit']==BASE, 'Wrong base release')
    require(m['native_blobs']==NATIVE, 'Native baseline registry changed')
    require(type(m['files']) is dict and PROTOCOL in m['files'] and len(m['files'])<=1000, 'Invalid release inventory')
    seen=set()
    for n,h in m['files'].items():
        relative(n)
        require(n.casefold() not in seen, 'Case-aliased manifest path');seen.add(n.casefold())
        require(type(h) is str and len(h)==64 and set(h)<=set('0123456789abcdef'), 'Invalid SHA-256 entry')
        require(n not in (MANIFEST,*NATIVE) and not n.startswith(('HCR-Evidence/exp','HCR-Evidence/deployments/')),
                'Release cannot overwrite native files or evidence')
    for n in ('Run-HCR-R047.py','tools/r047_state_ablation/provenance.py','tools/r047_state_ablation/storage.py',
              'tools/r047_state_ablation/spec.py','scripts/install_r047.py'):
        require(n in m['files'], 'Required release file absent: '+n)

def candidate_original(data):
    """Reverse only the exact published HF1/HF2/HF3 edit, never arbitrary changes."""
    text=lf(data).decode('utf-8')
    if text.count(OLD_CMD)==1 and text.count(OLD_RUN)==1:
        require(not any(m in text for m in MARKERS.values()), 'Mixed original/hotfix content')
        return text,'original'
    for version,marker in MARKERS.items():
        replacement='\n'.join((TEST_DIR,marker,NEW_CMD))
        if text.count(replacement)==1 and text.count(NEW_RUN)==1:
            original=text.replace(replacement,OLD_CMD).replace(NEW_RUN,OLD_RUN)
            require(original.count(OLD_CMD)==1 and original.count(OLD_RUN)==1,
                    'Ambiguous inverse hotfix')
            return original,version
    raise RepairError('protocol.py is not the original release or exact HF1/HF2/HF3 edit; no file will be re-signed')

def make_protocol(original):
    require(original.count(OLD_CMD)==1 and original.count(OLD_RUN)==1, 'Original harness signature not found')
    replacement='\n'.join((TEST_DIR,MARKERS['HF3'],NEW_CMD))
    new=original.replace(OLD_CMD,replacement).replace(OLD_RUN,NEW_RUN)
    # Code outside pipeline.tests must be byte-identical after the known inverse edit.
    restored,version=candidate_original(new.encode('utf-8'))
    require(restored==original and version=='HF3','Patch inverse mismatch')
    ast.parse(new)
    # Additional independent AST restriction: changes may occur only inside nested tests().
    def masked(text):
        tree=ast.parse(text);count=0
        for fn in tree.body:
            if isinstance(fn,ast.FunctionDef) and fn.name=='pipeline':
                # tests() is under pipeline's try block in this release.
                for node in ast.walk(fn):
                    if isinstance(node,ast.FunctionDef) and node.name=='tests':
                        node.body=[ast.Pass()];count+=1
        require(count==1,'Expected one pipeline.tests definition')
        return ast.dump(tree,include_attributes=False)
    require(masked(original)==masked(new), 'AST changed outside test harness')
    return new.encode('utf-8')

def certificate(base, original, patched):
    return dict(schema='hcr-r047-hf3-change-certificate-v1',hotfix='R047-HF3',base_commit=BASE,
        original_manifest=base,original_manifest_semantic_sha256=sha(canonical(base)),
        original_protocol_lf_sha256=text_sha(original.encode('utf-8')),
        patched_protocol_lf_sha256=text_sha(patched),
        authorized_changes=['absolute unittest discovery path','unittest cwd=repo/src',
            'release manifest protocol hash migration','this immutable change certificate'],
        research_design_changed=False,native_source_changed=False,raw_evidence_modified=False,
        validation_disabled=False,all_other_original_file_hashes_preserved=True,
        applies_to=['original R047','HF1','HF2','interrupted HF3','complete HF3'])

def inspect_release(repo):
    repo=safe(repo);mdata=child(repo,MANIFEST).read_bytes();current=decode(mdata);schema(current)
    if CERTIFICATE in current['files']:
        certbytes=child(repo,CERTIFICATE).read_bytes()
        require(text_sha(certbytes)==current['files'][CERTIFICATE], 'HF3 certificate checksum mismatch')
        supplied=decode(certbytes)
        require(supplied.get('schema')=='hcr-r047-hf3-change-certificate-v1', 'Unknown certificate')
        base=supplied['original_manifest'];schema(base)
        require(CERTIFICATE not in base['files'],'Recursive migration certificate')
    else:
        base=deepcopy(current);supplied=None
    pbytes=child(repo,PROTOCOL).read_bytes()
    original,state=candidate_original(pbytes)
    require(text_sha(original.encode('utf-8'))==base['files'][PROTOCOL],
            'Unrecognized change beyond the approved import-path edit; original protocol hash does not match')
    patched=make_protocol(original)
    cert=certificate(base,original,patched);certbytes=jd(cert)
    target=deepcopy(base);target['files'][PROTOCOL]=text_sha(patched);target['files'][CERTIFICATE]=text_sha(certbytes)
    require(current in (base,target),'Manifest differs outside authorized HF3 migration')
    if supplied is not None: require(supplied==cert,'HF3 certificate content changed')
    elif child(repo,CERTIFICATE).exists():
        require(child(repo,CERTIFICATE).read_bytes()==certbytes, 'Unregistered different file at HF3 certificate path')
    verified={};problems=[]
    for name,wanted in base['files'].items():
        if name==PROTOCOL: continue
        p=child(repo,name)
        if not p.is_file(): problems.append('missing: '+name);continue
        if text_sha(p.read_bytes())!=wanted:problems.append('changed: '+name)
        verified[name]=sha(p.read_bytes())
    for name,wanted in NATIVE.items():
        p=child(repo,name)
        if not p.is_file():problems.append('missing native: '+name);continue
        b=lf(p.read_bytes());h=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        if h!=wanted:problems.append('changed native: '+name)
        verified[name]=sha(p.read_bytes())
    require(not problems,'Files other than the approved protocol edit must match:\n'+'\n'.join(problems))
    for name in (PROTOCOL,MANIFEST):verified[name]=sha(child(repo,name).read_bytes())
    cp=child(repo,CERTIFICATE)
    verified[CERTIFICATE]=sha(cp.read_bytes()) if cp.exists() else None
    desired={PROTOCOL:patched,CERTIFICATE:certbytes,MANIFEST:jd(target)}
    return dict(base=base,current=current,target=target,state=state,original=original,
                certificate=cert,desired=desired,preimages=verified,
                already_complete=current==target and text_sha(pbytes)==text_sha(patched))

# A fresh process uses the installed provenance.py, not a substitute hash-only checker.
# Source-inventory copying is the same boundary that EXP28 freeze/audit uses.
WORKER = r'''
import hashlib, json, os, sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
sys.path[:0]=[str(root/'src'),str(root)]
import hcr
assert Path(hcr.__file__).resolve()==root/'src/hcr/__init__.py', 'hcr module shadowing'
from tools.r047_state_ablation import provenance, storage, spec
assert Path(provenance.__file__).resolve()==root/'tools/r047_state_ablation/provenance.py'
m=provenance.package_check(root)
n=provenance.native_check(root)
source=provenance.source_inventory(root)
report=dict(package_verified=True,native_verified=True,files=len(m['files']),source_files=len(source),
            hcr_origin=str(Path(hcr.__file__).resolve()),design_sha256=storage.digest(spec.design()))
if len(sys.argv)>3:
    dest=Path(sys.argv[3]);dest.mkdir(parents=True,exist_ok=False)
    for name,h in source.items():
        data=(root/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==h
        p=dest/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(data)
    report['copied_source_snapshot']=str(dest)
with Path(sys.argv[2]).open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,sort_keys=True)
print(json.dumps(report,ensure_ascii=False,sort_keys=True))
'''

def env_for(root):
    return dict(os.environ,PYTHONPATH=str(root/'src')+os.pathsep+str(root),
                PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')

def command(cmd,cwd,log,env=None):
    with safe(log).open('xb') as out:
        p=subprocess.run(cmd,cwd=cwd,env=env,stdout=out,stderr=subprocess.STDOUT)
        out.flush();os.fsync(out.fileno())
    if p.returncode != 0:
        print('--- Failure log (tail; full log is preserved) ---',file=sys.stderr,flush=True)
        print('\n'.join(safe(log).read_text(encoding='utf-8',errors='replace').splitlines()[-50:]),file=sys.stderr,flush=True)
    require(p.returncode==0, 'Command failed (exit '+str(p.returncode)+'); complete log: '+str(log))
    return p.returncode

def tree_probe(root,journal,label,copy_snapshot=False):
    worker=journal/'tree_probe.py'
    if not worker.exists(): write_new(worker,WORKER.encode('utf-8'))
    report=journal/(label+'.json');cmd=[sys.executable,'-X','utf8','-B',str(worker),str(root),str(report)]
    if copy_snapshot:cmd.append(str(journal/(label+'-source-snapshot')))
    command(cmd,root/'src',journal/(label+'.txt'),env_for(root))
    return decode(report.read_bytes())

def build_staged(repo,journal,info):
    stage=journal/'staged_release';stage.mkdir(exist_ok=False)
    for name in sorted(set(info['target']['files'])|set(NATIVE)|{MANIFEST}):
        data=info['desired'].get(name)
        if data is None: data=child(repo,name).read_bytes()
        write_new(child(stage,name),data)
    # Reproduce the real filename collision, instead of testing a directory without hcr.py.
    shadow=child(repo,'hcr.py')
    if shadow.is_file():write_new(stage/'hcr.py',shadow.read_bytes())
    return stage

def ensure_unchanged(repo,expected):
    for name,h in expected.items():
        p=child(repo,name)
        actual=sha(p.read_bytes()) if p.exists() else None
        require(actual==h,'File changed since preflight: '+name)

def replace_staged(src,dst):
    # Same filesystem (both are inside the repository); no PowerShell/.NET overload.
    os.replace(src,dst)

def rollback(repo,journal,attempted,before,desired):
    outcomes=[]
    for name in reversed(attempted):
        dst=child(repo,name);current=dst.read_bytes() if dst.exists() else None
        old=before[name]
        try:
            if current==old:
                outcomes.append(dict(path=name,status='unchanged'));continue
            require(current==desired[name], 'Concurrent edit: will not overwrite during rollback')
            if old is None: dst.unlink()
            else:
                stage=child(journal,'rollback/'+name);write_new(stage,old);os.replace(stage,dst)
            require((dst.read_bytes() if dst.exists() else None)==old, 'Rollback verification failed')
            outcomes.append(dict(path=name,status='restored_exact_preimage'))
        except BaseException as exc:
            outcomes.append(dict(path=name,status='rollback_failed',error=repr(exc)))
    put(journal/'rollback.json',dict(outcomes=outcomes,all_restored=all(x['status']!='rollback_failed' for x in outcomes)))
    return outcomes

def apply_transaction(repo,journal,info,post_check=None):
    """Three-file migration. Manifest last, explicit preimages, no claim of multi-file atomicity."""
    before={n:child(repo,n).read_bytes() if child(repo,n).exists() else None for n in info['desired']}
    for n,data in before.items():
        if data is not None:write_new(child(journal,'backup/'+n),data)
    for n,data in info['desired'].items():write_new(child(journal,'pending/'+n),data)
    put(journal/'transaction_prepared.json',dict(order=list(info['desired']),
        before={n:None if b is None else sha(b) for n,b in before.items()},
        after={n:sha(b) for n,b in info['desired'].items()},multi_file_atomic=False,
        recovery='recognized partial states or exact-byte rollback; no automatic experiment retry'))
    ensure_unchanged(repo,info['preimages']);attempted=[]
    try:
        with (journal/'transaction.jsonl').open('x',encoding='utf-8',newline='\n') as events:
            def event(obj):events.write(canonical(obj).decode()+'\n');events.flush();os.fsync(events.fileno())
            for name,data in info['desired'].items():
                dst=child(repo,name)
                current=dst.read_bytes() if dst.exists() else None
                require(current==before[name], 'Target changed during transaction: '+name)
                if current==data:
                    event(dict(path=name,action='unchanged'));continue
                dst.parent.mkdir(parents=True,exist_ok=True)
                attempted.append(name);event(dict(path=name,action='replace_started'))
                replace_staged(child(journal,'pending/'+name),dst)
                require(dst.read_bytes()==data, 'Destination verification failed: '+name)
                event(dict(path=name,action='replace_verified',sha256=sha(data)))
        check=inspect_release(repo)
        require(check['already_complete'],'Post-install manifest/source mismatch')
        if post_check is not None:post_check()
        put(journal/'transaction_committed.json',dict(hotfix='R047-HF3',changed=attempted,
            protocol_lf_sha256=text_sha(child(repo,PROTOCOL).read_bytes()),
            manifest_sha256=sha(child(repo,MANIFEST).read_bytes()),certificate_sha256=sha(child(repo,CERTIFICATE).read_bytes())))
        return attempted
    except BaseException:
        rollback(repo,journal,attempted,before,info['desired'])
        raise

def git_preflight(repo):
    def git(*args):
        p=subprocess.run(['git','-C',str(repo),*args],capture_output=True,encoding='utf-8',errors='strict')
        require(p.returncode==0, 'Git baseline check failed: '+p.stderr.strip());return p.stdout.strip()
    require(Path(git('rev-parse','--show-toplevel')).resolve()==repo.resolve(),'Not repository root')
    head=git('rev-parse','HEAD');git('merge-base','--is-ancestor',BASE,head)
    return head

def run(repo,launch=True):
    repo=safe(repo);require(sys.version_info>=(3,12),'Existing Python 3.12+ required')
    require(child(repo,PROTOCOL).is_file() and child(repo,MANIFEST).is_file(),'Place CMD in the installed R047 repository root')
    journal=repo/'HCR-Evidence/deployments'/('r047-hf3-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')+'-'+uuid4().hex[:8])
    journal.mkdir(parents=True,exist_ok=False)
    try:
        put(journal/'started.json',dict(hotfix='R047-HF3',python=sys.version,executable=sys.executable,
            started_utc=now(),repository=str(repo),automatic_retry=False))
        head=git_preflight(repo);info=inspect_release(repo)
        put(journal/'preflight.json',dict(head=head,detected_state=info['state'],already_complete=info['already_complete'],
            unchanged_files=len(info['preimages'])-3,original_protocol_lf_sha256=info['base']['files'][PROTOCOL]))
        print('HF3: authorized state = '+info['state'],flush=True)
        stage=build_staged(repo,journal,info)
        first=tree_probe(stage,journal,'01-staged-package',True)
        snap=Path(first['copied_source_snapshot'])
        second=tree_probe(snap,journal,'02-frozen-source-package')
        require(first['design_sha256']==second['design_sha256'],'Design changed during source copy')
        print('HF3: staged release and frozen source snapshot verified',flush=True)
        # Execute the ORIGINAL test suite in the same corrected environment as pipeline.tests.
        tests=stage/'tools/r047_state_ablation/tests'
        require(tests.is_dir(),'Original R047 tests are missing')
        command([sys.executable,'-X','utf8','-B','-m','unittest','discover','-s',str(tests),
                 '-p','test_*.py','-v','-f'],stage/'src',journal/'03-original-selftests.txt',env_for(stage))
        print('HF3: original staged self-tests passed',flush=True)
        def post():
            r=tree_probe(repo,journal,'04-installed-package',True)
            require(r['design_sha256']==first['design_sha256'],'Installed design changed')
            s=tree_probe(Path(r['copied_source_snapshot']),journal,'05-installed-snapshot')
            require(s['design_sha256']==first['design_sha256'],'Installed snapshot design changed')
        changed=apply_transaction(repo,journal,info,post)
        put(journal/'repair_verified.json',dict(hotfix='R047-HF3',changed_files=changed,
            original_suite_passed=True,source_snapshot_package_check_passed=True,design_sha256=first['design_sha256'],
            previous_runs_modified=False,validation_bypassed=False,completed_utc=now()))
        print('HF3: source + manifest migration verified',flush=True)
        print('Journal: '+str(journal),flush=True)
        if not launch:return 0
        put(journal/'launch_started.json',dict(command=[sys.executable,'-X','utf8','-B',str(repo/'Run-HCR-R047.py')],automatic_retry=False))
        print('HF3: launching ONE new R047 run; previous failed runs remain untouched',flush=True)
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(repo/'Run-HCR-R047.py')],cwd=repo,env=env_for(repo))
        put(journal/'launch_result.json',dict(returncode=result.returncode,automatic_retry=False,
            experiment_success_claimed=result.returncode==0,completed_utc=now()))
        if result.returncode:print('R047 run failed; see its preserved run evidence. No retry was attempted.',flush=True)
        return result.returncode
    except BaseException as exc:
        failure=dict(stage='HF3 migration or prelaunch verification',error_type=type(exc).__name__,
                     message=str(exc),traceback=traceback.format_exc(),automatic_retry=False,created_utc=now())
        try:put(journal/'failure.json',failure)
        except Exception:traceback.print_exc()
        print('HF3 ERROR: '+str(exc),file=sys.stderr,flush=True)
        print('Preserved journal: '+str(journal),file=sys.stderr,flush=True)
        return 1

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--repair-only',action='store_true',help='Repair and verify but do not run the experiment')
    a=p.parse_args();return run(a.repo,not a.repair_only)
if __name__=='__main__':sys.exit(main())
