"""Freeze -> self-test -> ONE final regression -> actual run -> independent audit.

No install, model download, git commit/push, repair, or automatic retry occurs.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from pathlib import Path
import os
import shutil
import subprocess
import sys
import traceback
from uuid import uuid4
import zipfile
from .common import (BASE_COMMIT, CONTRACT, SRC_TREE, TEST_TREE, dump, files, git_tree,
                     load, publish, require, safe, seal, sha, text_blob)


def now():
    return datetime.now(timezone.utc).isoformat()

def git(root: Path,*args: str) -> str:
    p=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,encoding='utf-8',errors='strict')
    require(p.returncode==0,'Git read failed: '+' '.join(args)+'\n'+p.stderr)
    return p.stdout.strip()

def protected_files(root: Path) -> dict[str,str]:
    require(git(root,'rev-parse','HEAD:src')==SRC_TREE and git(root,'rev-parse','HEAD:tests')==TEST_TREE,
            'Source/test trees differ from the implementation baseline. No automatic rebase/repair.')
    records=git(root,'ls-tree','-r',BASE_COMMIT,'--','src','tests').splitlines()
    result={}
    for record in records:
        meta,name=record.split('\t',1)
        mode,kind,blob=meta.split()
        require(mode=='100644' and kind=='blob','Unsupported source file mode: '+name)
        path=safe(root/name)
        require(path.is_file() and text_blob(path.read_bytes())==blob,'Modified/missing protected file: '+name)
        result[name]=sha(path.read_bytes())
    for directory in ('src','tests'):
        actual={p.relative_to(root).as_posix() for p in (root/directory).rglob('*.py') if '__pycache__' not in p.parts}
        require(actual <= set(result),'Untracked Python source would change the execution contract.')
    return result


def verify_current_releases(root: Path) -> dict:
    report={}
    manifest_blobs = {'R048':'b7a2acd87277d0218ae4a08ae510e1f842d93b74', 'R049':'62b2cf8180cd0e4d329fa9af46cd1cab842c148b'}
    for release in ('R048','R049'):
        require(text_blob((root/(release+'_MANIFEST.json')).read_bytes()) == manifest_blobs[release],
                'Historical/current release manifest identity changed: '+release)
        manifest=load(root/(release+'_MANIFEST.json'))
        for name,expected in manifest['files'].items():
            path=safe(root/name)
            require(path.is_file() and sha(path.read_bytes().replace(b'\r\n',b'\n'))==expected,
                    release+' package hash mismatch: '+name)
        report[release]=dict(files=len(manifest['files']),verified=True,
                            manifest_sha256=sha((root/(release+'_MANIFEST.json')).read_bytes()))
    return report


def verify_addon(root: Path) -> dict:
    manifest=load(root/'R050_MANIFEST.json')
    require(manifest['contract']==CONTRACT,'Add-on contract version')
    for name,expected in manifest['files'].items():
        from .common import relative
        p=relative(root,name)
        require(p.is_file() and sha(p.read_bytes().replace(b'\r\n',b'\n'))==expected,
                'Add-on file changed: '+name)
    return manifest


def freeze(root: Path, out: Path, install_receipt: str | None) -> dict:
    source_files=protected_files(root)
    addon=verify_addon(root)
    releases=verify_current_releases(root)
    require(out.is_dir() and not any(out.iterdir()), 'A newly allocated empty evidence directory is required')
    source_files.update({name:sha((root/name).read_bytes()) for name in addon['files']})
    source_files['R050_MANIFEST.json']=sha((root/'R050_MANIFEST.json').read_bytes())
    source_files['experiments/INDEX.json']=sha((root/'experiments/INDEX.json').read_bytes())
    for name,expected in source_files.items():
        p=safe(root/name)
        raw=p.read_bytes()
        require(sha(raw)==expected,'Concurrent source change during freeze: '+name)
        publish(out/'source'/name,raw)
    require(git_tree(out/'source'/'src')==SRC_TREE and git_tree(out/'source'/'tests')==TEST_TREE,
            'Frozen source tree identity failed')
    dump(out/'source_manifest.json',dict(schema='hcc-r050-source-manifest-v1',files=files(out/'source'),
         baseline_commit=BASE_COMMIT,actual_checkout_commit=git(root,'rev-parse','HEAD'),
         normalization_for_native_source='CRLF to LF only; raw byte hashes retained',current_releases=releases))
    # Construction of config/memory is not an inference and precedes self-test.
    from hcr import codec
    from hcr.model import AdaptiveConfig
    from hcr.circuits import AdaptiveMemory
    spec=load(out/'source'/'experiments'/'exp-31-review-boundary'/'frozen_spec.json')
    require(codec.plain(AdaptiveConfig())==spec['config'],'Pinned default config does not match the frozen design')
    plan=seal(dict(schema='hcc-r050-plan-v1',contract=CONTRACT,created_at_utc=now(),
         baseline_commit=BASE_COMMIT,actual_checkout_commit=git(root,'rev-parse','HEAD'),
         git_status=git(root,'status','--porcelain=v1','--untracked-files=no'),
         source_manifest_sha256=sha((out/'source_manifest.json').read_bytes()),
         addon_manifest_sha256=sha((out/'source'/'R050_MANIFEST.json').read_bytes()),
         config=spec['config'],empty_memory=AdaptiveMemory.empty(AdaptiveConfig()).document(),
         cases=spec['cases'],arms=spec['arms'],limits=spec['limits'],
         frozen_predictions=spec['predictions'],numeric_comparison=spec['numeric_comparison'],
         boundaries=spec['boundaries'],installation_receipt=install_receipt,
         python=sys.version,platform=sys.platform,study_executed_at_freeze=False))
    dump(out/'plan.json',plan)
    dump(out/'validation'/'preflight.json',dict(verified=True,core_source_files=len([n for n in source_files if n.startswith('src/')]),
         baseline_commit=BASE_COMMIT,current_releases=releases,no_model_installation=True))
    return plan


def stage(root: Path,out: Path,name: str,module: str,args: list[str],*,source: Path | None=None) -> None:
    source=source or out/'source'
    launcher=out/'source'/'tools'/'r050_review_boundary'/'bootstrap.py'
    command=[sys.executable,'-X','utf8','-B',str(launcher),'--source',str(source),'--module',module,'--',*args]
    print('STAGE:',name,flush=True)
    log=out/'validation'/(name+'.log')
    log.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join([str(source/'src'),str(source)]))
    started=now()
    with log.open('xb') as stream:
        completed=subprocess.run(command,cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT)
    dump(out/'validation'/(name+'.receipt.json'),dict(command=command,returncode=completed.returncode,
         started_at_utc=started,finished_at_utc=now(),automatic_retry=False))
    require(completed.returncode==0,f'{name} failed; first failure and partial evidence retained: {log}')


def raw_manifest(out: Path) -> dict:
    mapping={}
    for directory in ('baselines','raw','progress','measurements','interventions'):
        p=out/directory
        if p.exists():
            mapping.update({directory+'/'+name:value for name,value in files(p).items()})
    result=dict(schema='hcc-r050-raw-manifest-v1',files=mapping)
    dump(out/'raw_manifest.json',result)
    return result


def run(root: Path, install_receipt: str | None=None) -> Path:
    if sys.version_info<(3,12):
        raise RuntimeError('Existing Python 3.12+ is required. No auto-install.')
    out=safe(root/'HCR-Evidence'/'exp31'/('r050-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:10]))
    out.mkdir(parents=True, exist_ok=False)
    phase='freeze'
    try:
        freeze(root,out,install_receipt)
        phase='selftest'
        stage(root,out,'01-unit-selftest','tools.r050_review_boundary.selftest',
              ['--tests',str(out/'source'/'tools'/'r050_review_boundary'/'tests'),
               '--output',str(out/'validation'/'unit_selftest.json')])
        stage(root,out,'02-native-contract-smoke','tools.r050_review_boundary.native_smoke',['--run',str(out)])
        stage(root,out,'03-native-contract-audit','tools.r050_review_boundary.smoke_audit',['--run',str(out)])
        phase='final_core_regression'
        stage(root,out,'04-final-core-regression','tools.r050_review_boundary.regression',
              ['--repo',str(root),'--output',str(out/'validation'/'core_regression.json')],source=root)
        # Detect edits during test execution. Tests never authorize a new baseline.
        protected_files(root)
        verify_current_releases(root)
        verify_addon(root)
        phase='actual_research_execution'
        stage(root,out,'05-research-worker','tools.r050_review_boundary.worker',['--run',str(out)])
        raw_manifest(out)
        phase='independent_audit'
        stage(root,out,'06-independent-audit','tools.r050_review_boundary.audit',
              ['--run',str(out),'--output',str(out/'analysis'/'audit.json')])
        phase='reporting'
        stage(root,out,'07-audited-reporting','tools.r050_review_boundary.reporting',['--run',str(out)])
        phase='derived_artifact_verification'
        stage(root,out,'08-analysis-consistency','tools.r050_review_boundary.verify_analysis',
              ['--run',str(out),'--audit',str(out/'analysis'/'audit.json'),
               '--output',str(out/'validation'/'analysis_consistency.json')])
        dump(out/'result.json',dict(status='EXECUTED_AND_INDEPENDENTLY_VERIFIED',contract=CONTRACT,
             research_experiment_executed=True,git_commit_push_performed=False,
             native_core_regressions=1,selftest_is_research_evidence=False,
             implementation_revision='r050-source-implementation-3-proof-audit',derived_artifacts_verified=True,
             hypothesis_success_not_required=True,completed_at_utc=now()))
        phase='bundle_packaging'
        dump(out/'bundle_manifest.json',dict(schema='hcc-r050-bundle-manifest-v1',files=files(out)))
        zip_path=out.with_suffix('.zip')
        with zipfile.ZipFile(zip_path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as bundle:
            for p in sorted(out.rglob('*')):
                if p.is_file():
                    bundle.write(p,arcname=out.name+'/'+p.relative_to(out).as_posix())
        print('EVIDENCE:',out,flush=True)
        print('BUNDLE:',zip_path,flush=True)
        return out
    except BaseException as exc:
        out.mkdir(parents=True,exist_ok=True)
        failure=(out.parent/(out.name+'-packaging-failure.json')) if (out/'bundle_manifest.json').exists() else out/'failure.json'
        if not failure.exists():
            dump(failure,dict(status='FAILED',stage=phase,exception=type(exc).__name__,message=str(exc),
                 traceback=traceback.format_exc(),automatic_retry=False,partial_evidence_retained=True,
                 source_was_not_repaired=True,failed_at_utc=now()))
        print('FAILED EVIDENCE:',out,file=sys.stderr,flush=True)
        raise


def verify_existing(root: Path, out: Path) -> Path:
    out=safe(out)
    trusted=verify_addon(root)
    for name,expected in trusted['files'].items():
        p=out/'source'/name
        require(p.is_file() and sha(p.read_bytes().replace(b'\r\n',b'\n'))==expected,'Frozen add-on differs from this verified package: '+name)
    inventory=load(out/'bundle_manifest.json')['files']
    actual=files(out)
    actual.pop('bundle_manifest.json',None)
    require(actual==inventory,'Bundle inventory/hash mismatch')
    receipt=out.parent/(out.name+'-verify-'+uuid4().hex[:10]+'.json')
    command=[sys.executable,'-X','utf8','-B',str(out/'source'/'tools'/'r050_review_boundary'/'bootstrap.py'),
             '--source',str(out/'source'),'--module','tools.r050_review_boundary.audit','--',
             '--run',str(out),'--output',str(receipt)]
    status=subprocess.run(command,cwd=root).returncode
    require(status==0,'Independent verification failed; existing evidence was not changed')
    # Existing summary/CSV/Markdown are checked against the FRESH raw re-audit,
    # not merely against a saved verified=true flag.
    analysis_receipt = receipt.with_name(receipt.stem + '-analysis.json')
    command=[sys.executable,'-X','utf8','-B',str(out/'source'/'tools'/'r050_review_boundary'/'bootstrap.py'),
             '--source',str(out/'source'),'--module','tools.r050_review_boundary.verify_analysis','--',
             '--run',str(out),'--audit',str(receipt),'--output',str(analysis_receipt)]
    status=subprocess.run(command,cwd=root).returncode
    require(status==0,'Saved analysis differs from raw replay; evidence was not changed')
    return analysis_receipt


def main(argv=None) -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--verify',type=Path)
    p.add_argument('--installation-receipt')
    a=p.parse_args(argv)
    root=safe(a.repo)
    if a.verify:
        print('VERIFY RECEIPT:',verify_existing(root,a.verify))
    else:
        run(root,a.installation_receipt)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
