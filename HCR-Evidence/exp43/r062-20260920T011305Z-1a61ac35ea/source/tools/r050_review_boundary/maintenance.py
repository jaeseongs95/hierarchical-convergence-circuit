"""Transactional install / known-predecessor upgrade. Preserve every preimage."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback
from uuid import uuid4
from .common import (BASE_COMMIT, CONTRACT, dump, files, load, publish, relative,
                     require, safe, sha, text_blob)
from .pipeline import git, protected_files, verify_current_releases, verify_addon

INDEX_BLOB = '52bd8cd1c25dde2ebbd622318cbdcaebba0c3c35'
DISPATCHER_BLOB = 'f36ad5a1a145bb61cbb26531703348fa9cfa305b'


def discover_repo(explicit: Path | None, package: Path) -> Path:
    if explicit is not None:
        candidates=[safe(explicit)]
    else:
        candidates=[]
        for anchor in (package,Path.cwd()):
            candidates.extend([safe(anchor),*safe(anchor).parents])
    for root in candidates:
        if (root/'.git').exists() and (root/'src'/'hcr').is_dir() and (root/'experiments'/'INDEX.json').is_file():
            actual=Path(git(root,'rev-parse','--show-toplevel'))
            require(safe(actual)==root,'Unexpected Git root')
            return root
    raise ValueError('Extract HCC_EXP31_R050 inside the repository, or use Run.cmd --repo "D:\\path\\to\\repository".')


def index_change(root: Path, entry: dict) -> tuple[bytes,bytes]:
    current=(root/'experiments'/'INDEX.json').read_bytes()
    old=subprocess.run(['git','-C',str(root),'show',BASE_COMMIT+':experiments/INDEX.json'],capture_output=True)
    require(old.returncode==0 and text_blob(old.stdout)==INDEX_BLOB,'Pinned catalog blob unavailable')
    baseline=json.loads(old.stdout)
    parsed=json.loads(current)
    expected=deepcopy(baseline)
    require(not any(r['experiment_id']=='EXP-31' for r in expected['experiments']),'EXP-31 already existed at baseline')
    expected['experiments'].append(entry)
    if parsed==expected:
        return current,current
    require(parsed==baseline and text_blob(current)==INDEX_BLOB,'Catalog contains external changes; not overwritten')
    proposed=(json.dumps(expected,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    require(expected['default_experiment']==baseline['default_experiment']=='EXP-30','Default release was changed')
    return current,proposed


def replace_guarded(path: Path, expected: bytes, proposed: bytes) -> None:
    path=safe(path)
    require(path.is_file() and path.read_bytes()==expected,'Concurrent external edit: '+str(path))
    fd,tmp=tempfile.mkstemp(prefix='.r050-install-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(proposed);stream.flush();os.fsync(stream.fileno())
        require(path.is_file() and path.read_bytes()==expected,'Concurrent edit before replace: '+str(path))
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def plan_payload_operations(root: Path, payload: Path, receipt: Path,
                            predecessor: dict[str, str]) -> list[dict]:
    """Never overwrite an unknown file. Every recognised replacement has a preimage."""
    operations = []
    for name, digest in files(payload).items():
        path = relative(root, name)
        if not path.exists():
            operations.append(dict(kind='add', path=name, before_sha256=None, after_sha256=digest))
            continue
        require(path.is_file(), 'Installed path is not a regular file: ' + name)
        before = path.read_bytes()
        normalized = sha(before.replace(b'\r\n', b'\n'))
        if normalized == digest:
            continue
        require(name in predecessor and normalized == predecessor[name],
                'Existing file is neither this release nor its known predecessor: ' + name)
        publish(receipt / 'preimages' / name, before)
        operations.append(dict(kind='replace', path=name, source='payload',
                               before_sha256=sha(before), after_sha256=digest))
    return operations


def apply_operations(root: Path, payload: Path, receipt: Path, operations: list[dict], index_after: bytes,
                     *, applied: list[dict] | None = None) -> list[dict]:
    applied = [] if applied is None else applied
    for number,op in enumerate(operations):
        path=relative(root,op['path'])
        if op['kind']=='add':
            raw=relative(payload,op['path']).read_bytes()
            require(sha(raw)==op['after_sha256'],'Payload changed after plan freeze')
            publish(path,raw)
        else:
            before=(receipt/'preimages'/op['path']).read_bytes()
            proposed = (relative(payload,op['path']).read_bytes() if op.get('source') == 'payload' else index_after)
            require(sha(before)==op['before_sha256'] and sha(proposed)==op['after_sha256'],'Frozen replacement plan hash')
            replace_guarded(path,before,proposed)
        applied.append(op)
        dump(receipt/'applied'/f'{number:04d}.json',op)
    return applied


def rollback(root: Path, receipt: Path, operations: list[dict]) -> dict:
    restored=[];unresolved=[]
    for op in reversed(operations):
        path=relative(root,op['path'])
        if not path.exists():
            if op['kind']=='add':
                restored.append(dict(path=op['path'],status='already_absent'))
                continue
            unresolved.append(dict(path=op['path'],reason='replaced_file_missing'));continue
        observed = path.read_bytes() if path.is_file() else None
        if observed is None or sha(observed)!=op['after_sha256']:
            unresolved.append(dict(path=op['path'],reason='external_change_preserved'));continue
        if op['kind']=='add':
            path.unlink()
            restored.append(dict(path=op['path'],status='owned_addition_removed'))
        else:
            old=(receipt/'preimages'/op['path']).read_bytes()
            if sha(old)!=op['before_sha256']:
                unresolved.append(dict(path=op['path'],reason='preimage_hash_mismatch'));continue
            replace_guarded(path,observed,old)
            restored.append(dict(path=op['path'],status='original_bytes_restored'))
    return dict(complete=not unresolved,restored=restored,unresolved=unresolved,
                raw_evidence_deleted=False,external_changes_overwritten=False)


def install(package: Path, explicit: Path | None) -> int:
    payload=package/'payload'
    root=discover_repo(explicit,package)
    identity=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]
    receipt=safe(root/'HCR-Evidence'/'repository-maintenance'/('r050-install-'+identity))
    receipt.mkdir(parents=True,exist_ok=False)
    publish(receipt/'.gitattributes', b'* -text\n')
    publish(receipt/'.gitignore', b'!*.log\n')
    lock=receipt.parent/'.r050-install.lock'
    lock_bytes=(identity+'\n').encode()
    applied=[];acquired=False
    try:
        publish(lock,lock_bytes);acquired=True
        require(sys.version_info>=(3,12),'Existing Python 3.12+ required')
        protected=protected_files(root)
        releases=verify_current_releases(root)
        require(text_blob((root/'scripts'/'run_indexed_experiment.py').read_bytes())==DISPATCHER_BLOB,
                'Dispatcher changed; candidate catalog cannot be safely appended')
        entry=load(payload/'experiments'/'exp-31-review-boundary'/'catalog_entry.json')
        before,after=index_change(root,entry)
        operations=[]
        payload_files=files(payload)
        manifest=load(payload/'R050_MANIFEST.json')
        require(manifest['contract']==CONTRACT,'Wrong add-on contract')
        require(set(payload_files)==set(manifest['files'])|{'R050_MANIFEST.json'},'Unexpected payload inventory')
        for name,expected in manifest['files'].items():
            require(sha((payload/name).read_bytes())==expected,'Payload hash mismatch: '+name)
        known = load(package / 'PREDECESSOR_FILES.json')
        require(known['schema'] == 'hcc-r050-known-predecessor-v1', 'Predecessor catalog schema')
        operations = plan_payload_operations(root, payload, receipt, known['files'])
        if before!=after:
            publish(receipt/'preimages'/'experiments'/'INDEX.json',before)
            operations.append(dict(kind='replace',path='experiments/INDEX.json',before_sha256=sha(before),after_sha256=sha(after)))
        publish(receipt/'index-after.json',after)
        dump(receipt/'plan.json',dict(schema='hcc-r050-install-plan-v1',baseline_commit=BASE_COMMIT,
             actual_checkout_commit=git(root,'rev-parse','HEAD'),created_at_utc=datetime.now(timezone.utc).isoformat(),
             operations=operations,protected_source_hashes=protected,current_releases=releases,
             addon_manifest_sha256=sha((payload/'R050_MANIFEST.json').read_bytes()),
             full_regression_before_or_during_patch=False,default_experiment_unchanged=True))
        # Ownership is appended before journaling: even a failed receipt write
        # cannot erase which bytes this installation has already published.
        apply_operations(root, payload, receipt, operations, after, applied=applied)
        # Independent byte/hash checks before any full regression.
        verify_addon(root);protected_files(root);verify_current_releases(root)
        require((root/'experiments'/'INDEX.json').read_bytes()==after,'Final catalog mismatch')
        # Load the original dispatcher solely for read_index; do not run an experiment.
        import importlib.util
        spec=importlib.util.spec_from_file_location('r050_existing_dispatcher',root/'scripts'/'run_indexed_experiment.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.read_index(root)
        dump(receipt/'direct_audit.json',dict(verified=True,changed_files=len(applied),
             existing_core_unchanged=True,R048_R049_unchanged=True,default_experiment='EXP-30'))
        command=[sys.executable,'-X','utf8','-B',str(root/'Run-HCR-R050.py'),
                 '--installation-receipt',str(receipt)]
        print('Repository:',root,flush=True)
        print('Installation receipt:',receipt,flush=True)
        # The pipeline freezes conditions before tests, executes the complete core
        # regression once, then runs/audits the new experiment. No retry on failure.
        completed=subprocess.run(command,cwd=root,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
        require(completed.returncode==0,'R050 pipeline failed; review the preserved evidence and logs')
        protected_files(root);verify_current_releases(root);verify_addon(root)
        require((root/'experiments'/'INDEX.json').read_bytes()==after, 'Catalog changed during execution')
        dump(receipt/'result.json',dict(status='APPLIED_AND_EXECUTED',changed_files=len(applied),
             rollback_performed=False,git_commit_push_performed=False,full_core_runs=1))
        return 0
    except BaseException as exc:
        dump(receipt/'failure.json',dict(exception=type(exc).__name__,message=str(exc),
             traceback=traceback.format_exc(),automatic_retry=False,first_failure_preserved=True))
        try:
            restored=rollback(root,receipt,applied)
        except BaseException as rollback_exc:
            restored=dict(complete=False,error=str(rollback_exc),traceback=traceback.format_exc(),raw_evidence_deleted=False)
        dump(receipt/'rollback.json',restored)
        print('FAILED. Evidence retained:',receipt,file=sys.stderr,flush=True)
        raise
    finally:
        if acquired and lock.is_file() and lock.read_bytes()==lock_bytes:
            lock.unlink()


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--package',required=True,type=Path)
    p.add_argument('--repo',type=Path)
    a=p.parse_args(argv)
    return install(safe(a.package),a.repo)

if __name__=='__main__':
    raise SystemExit(main())
