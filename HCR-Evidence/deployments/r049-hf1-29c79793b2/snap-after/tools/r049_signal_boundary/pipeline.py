"""R048 pipeline contracts retained: additive source, sealed snapshots, full parent replay."""
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
import platform
import sys
import zipfile
from tools.r048_precision import io
from . import spec,provenance


def stage(root,name,action):
    io.put(root/'execution'/(name+'.started.json'),dict(stage=name,started_utc=io.now()))
    try:
        result=action();io.put(root/'execution'/(name+'.completed.json'),dict(stage=name,finished_utc=io.now(),result=result))
        print('Completed: '+name,flush=True);return result
    except BaseException as exc:io.failure(root,name,exc);raise


def validate_plan(plan):
    expected=set(spec.body())|{'schema','population','created_utc','source_hashes','parent_bundle_sha256'}
    io.require(set(plan)==expected and plan['schema']=='hcr-exp30-plan-v1','plan schema')
    io.require(plan['population'] in ('research','implementation_validation'),'population label')
    for k,v in spec.body().items():io.require(plan[k]==v,'frozen design changed: '+k)


def check_source(root,plan):
    io.verify_files(root/'source',plan['source_hashes'])
    provenance.package_check(root/'source');provenance.inherited_check(root/'source')
    io.require(io.load(root/'source/docs/R049_FROZEN_DESIGN.json')==spec.body(),'frozen design certificate differs')


def expected_raw(plan):
    return {'plan.json','attempts.jsonl'}|{'raw/'+t['id']+'.json' for t in plan['trials']}


def seal_raw(root):
    plan=io.load(root/'plan.json');validate_plan(plan);names=expected_raw(plan)
    actual={n for n in io.names(root) if n in ('plan.json','attempts.jsonl') or n.startswith('raw/')}
    io.require(actual==names,'raw inventory')
    io.put(root/'raw_manifest.json',dict(schema='hcr-exp30-raw-v1',state='raw_complete',files=io.hashes(root,names)))
    return dict(files=len(names))


def analysis_contents(root):
    from . import evaluate,reporting
    root=io.safe(root);plan=io.load(root/'plan.json');validate_plan(plan);check_source(root,plan)
    parent=root/'parent'
    io.require(io.sha(io.read(parent/'bundle_manifest.json'))==plan['parent_bundle_sha256'],'parent seal changed')
    m=io.load(parent/'bundle_manifest.json');io.verify_files(parent,m['files'],extra=('bundle_manifest.json',))
    raw=io.load(root/'raw_manifest.json')
    io.require(raw['schema']=='hcr-exp30-raw-v1' and raw['state']=='raw_complete' and set(raw['files'])==expected_raw(plan),'raw manifest')
    io.require({n for n in io.names(root) if n in ('plan.json','attempts.jsonl') or n.startswith('raw/')}==expected_raw(plan),'unexpected/missing raw')
    io.verify_files(root,raw['files'],exact=False)
    records,audits,stream=evaluate.read_audit(plan,root)
    prior=io.load(root/'source/docs/R049_PRIOR_EXPLORATION.json')
    summary=evaluate.summarize(plan,records,audits,prior)
    return reporting.contents(summary,audits,stream,io.sha(io.read(root/'raw_manifest.json')))


def analyze(root,verify=False):
    root=io.safe(root);out=analysis_contents(root);m=dict(schema='hcr-exp30-analysis-v1',files={n:io.sha(b) for n,b in out.items()})
    if verify:
        io.require(io.load(root/'analysis/manifest.json')==m,'analysis differs from independent reaggregation')
        io.verify_files(root/'analysis',m['files'],extra=('manifest.json',))
    else:
        (root/'analysis').mkdir(exist_ok=False)
        for n,b in out.items():io.write(io.child(root/'analysis',n),b)
        io.put(root/'analysis/manifest.json',m)
    return dict(verified=True,files=len(out),read_only=verify)


def verify_bundle(root):
    root=io.safe(root);m=io.load(root/'bundle_manifest.json')
    io.require(m['schema']=='hcr-exp30-bundle-v1','bundle schema')
    io.verify_files(root,m['files'],extra=('bundle_manifest.json',))
    provenance.verify_parent(root/'parent')
    analyze(root,verify=True)
    return dict(verified=True,files=len(m['files']),full_parent_replay=True)


def seal_bundle(root):
    io.put(root/'bundle_manifest.json',dict(schema='hcr-exp30-bundle-v1',files=io.hashes(root)))
    return dict(files=len(io.load(root/'bundle_manifest.json')['files']))


def archive(root):
    root=io.safe(root);m=io.load(root/'bundle_manifest.json');io.verify_files(root,m['files'],extra=('bundle_manifest.json',))
    dest=root.with_name(root.name+'_evidence.zip')
    with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n in io.names(root):z.write(io.child(root,n),n)
    with zipfile.ZipFile(dest) as z:
        io.require(z.testzip() is None and set(z.namelist())==set(io.names(root)),'ZIP CRC/inventory')
        for n in z.namelist():io.require(io.sha(z.read(n))==io.sha(io.read(io.child(root,n))),'ZIP byte mismatch: '+n)
    receipt=dict(archive=dest.name,bytes=dest.stat().st_size,sha256=io.sha(io.read(dest)),bundle_manifest_sha256=io.sha(io.read(root/'bundle_manifest.json')))
    io.put(dest.with_name(dest.name+'.receipt.json'),receipt);return receipt


def run_tests(snapshot,root,which):
    return io.command([sys.executable,'-X','utf8','-B',str(snapshot/'scripts/r049_tests.py'),'--root',str(snapshot),'--suite',which],
        cwd=snapshot/'src',log=root/'execution'/('tests-'+which+'.txt'))


def run(repo,*,population='research'):
    io.require(population in ('research','implementation_validation'),'population label')
    repo=io.safe(repo)
    # Shorter than R048: adding the parent/ nesting does not lengthen old deepest paths.
    tag=datetime.now(timezone.utc).strftime('%y%m%d')+'-'+uuid4().hex[:8]
    root=repo/'HCR-Evidence/exp30'/('r049-'+tag);root.mkdir(parents=True,exist_ok=False)
    io.write(root/'.gitattributes',provenance.ATTRIBUTES);io.write(root/'.gitignore',b'# Preserve all evidence.\n!*\n')
    try:
        env=stage(root,'01-baseline',lambda:provenance.repository_check(repo))
        stage(root,'02-release',lambda:dict(files=len(provenance.package_check(repo)['files'])))
        restored=stage(root,'03-parent-copy',lambda:provenance.parent_copy_from_repo(repo,root/'parent'))
        io.put(root/'parent_byte_recovery.json',restored)
        stage(root,'04-parent-replay',lambda:provenance.verify_parent(root/'parent',root/'execution/04-parent-replay.txt'))
        files=stage(root,'05-source-freeze',lambda:provenance.copy_source(repo,root/'parent/source',root/'source'))
        snapshot=root/'source'
        io.put(root/'environment.json',dict(python=sys.version,platform=platform.platform(),**env,
            automatic_retry=False,old_evidence_modified=False,learning=False))
        stage(root,'06-inherited-tests',lambda:run_tests(snapshot,root,'inherited'))
        stage(root,'07-new-tests',lambda:run_tests(snapshot,root,'new'))
        stage(root,'08-publication-preflight',lambda:provenance.publication_check(repo,root))
        plan=dict(schema='hcr-exp30-plan-v1',population=population,created_utc=io.now(),**spec.body(),
            source_hashes=files,parent_bundle_sha256=io.sha(io.read(root/'parent/bundle_manifest.json')))
        validate_plan(plan);check_source(root,plan);io.put(root/'plan.json',plan)
        cli=snapshot/'scripts/r049_cli.py'
        for name,action in [('09-execute','execute'),('11-audit','analyze'),('12-analysis-replay','verify-analysis')]:
            stage(root,name,lambda action=action,name=name:io.command([sys.executable,'-X','utf8','-B',str(cli),action,'--run',str(root)],
                cwd=snapshot/'src',log=root/'execution'/(name+'.txt')))
            if action=='execute':stage(root,'10-seal-raw',lambda:seal_raw(root))
        io.write(root/'VERIFY_BUNDLE.cmd',io.read(snapshot/'scripts/r049_verify_bundle.cmd'))
        stage(root,'13-publication',lambda:provenance.publication_check(repo,root))
        io.put(root/'execution/completed.json',dict(state='execution_and_analysis_completed',automatic_retry=False,finished_utc=io.now()))
        seal_bundle(root)
        receipts=root.parent/(root.name+'_receipts');receipts.mkdir(exist_ok=False)
        verified=io.command([sys.executable,'-X','utf8','-B',str(cli),'verify','--run',str(root)],
            cwd=snapshot/'src',log=receipts/'final-verify.txt')
        io.put(receipts/'final-verify.json',verified)
        io.put(receipts/'git-clean.json',provenance.publication_check(repo,root))
        z=archive(root)
        print('Summary: '+str(root/'analysis/summary.ko.md'),flush=True)
        print('Evidence: '+str(root.parent/z['archive']),flush=True)
        return dict(run=str(root),archive=z)
    except BaseException as e:
        target=root.parent/(root.name+'_receipts') if (root/'bundle_manifest.json').exists() else root
        target.mkdir(parents=True,exist_ok=True);io.failure(target,'pipeline',e)
        print('Failed; first failure and partial evidence preserved: '+str(target),file=sys.stderr,flush=True)
        raise
