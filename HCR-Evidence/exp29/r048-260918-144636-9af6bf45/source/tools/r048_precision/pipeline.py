"""One explicit run, immutable snapshots, independent audit, and byte-preserving publication."""
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
import platform
import sys
import zipfile
from . import io,spec,provenance


def stage(root,name,action):
    io.put(root/'execution'/(name+'.started.json'),dict(stage=name,started_utc=io.now()))
    try:
        result=action()
        io.put(root/'execution'/(name+'.completed.json'),dict(stage=name,finished_utc=io.now(),result=result))
        print('Completed: '+name,flush=True);return result
    except BaseException as e:io.failure(root,name,e);raise


def validate_plan(plan):
    expected=set(spec.body())|{'schema','population','created_utc','source_hashes','parent_bundle_sha256'}
    io.require(set(plan)==expected and plan['schema']=='hcr-exp29-plan-v1','plan schema')
    io.require(plan['population'] in ('research','implementation_validation'),'population label')
    for k,v in spec.body().items():io.require(plan[k]==v,'frozen plan changed: '+k)


def check_source(root,plan):
    io.verify_files(root/'source',plan['source_hashes'])
    provenance.package_check(root/'source');provenance.inherited_check(root/'source')


def expected_raw(plan):
    return {'plan.json','attempts.jsonl'}|{'raw/A_'+s+'.json' for s in plan['sources']}|{'raw/B_'+t['id']+'.json' for t in plan['trials']}


def seal_raw(root):
    plan=io.load(root/'plan.json');validate_plan(plan)
    expected=expected_raw(plan)
    io.require({n for n in io.names(root) if n in ('plan.json','attempts.jsonl') or n.startswith('raw/')}==expected,'raw inventory')
    io.put(root/'raw_manifest.json',dict(schema='hcr-exp29-raw-v1',state='raw_complete',files=io.hashes(root,expected)))
    return dict(files=len(expected))


def analysis_contents(root):
    from . import evaluate,reporting
    root=io.safe(root);plan=io.load(root/'plan.json');validate_plan(plan);check_source(root,plan)
    parent=root/'basis/exp28'
    io.require(io.sha(io.read(parent/'bundle_manifest.json'))==plan['parent_bundle_sha256'],'parent manifest changed')
    io.verify_files(parent,io.load(parent/'bundle_manifest.json')['files'],extra=('bundle_manifest.json',))
    raw=io.load(root/'raw_manifest.json')
    io.require(raw['schema']=='hcr-exp29-raw-v1' and raw['state']=='raw_complete' and set(raw['files'])==expected_raw(plan),'raw manifest registry')
    actual={n for n in io.names(root) if n in ('plan.json','attempts.jsonl') or n.startswith('raw/')}
    io.require(actual==expected_raw(plan),'extra or missing raw input')
    io.verify_files(root,raw['files'],exact=False)
    src,records,sa,ba,events=evaluate.read_audit(plan,root)
    s=evaluate.summarize(plan,src,records,sa,ba)
    a=dict(schema='hcr-exp29-audit-v1',verified=True,population=plan['population'],source_queries=len(src),followups=len(records),
        stream_records=events,scalar_ticks=s['unique_native_ticks'],tolerance=2e-12,
        inherited_evaluator_unchanged=True,hypothesis_support_required=False,
        full_AdaptiveSession_replayed=False,raw_manifest_sha256=io.sha(io.read(root/'raw_manifest.json')))
    return reporting.contents(s,a,sa,ba)


def analyze(root,verify=False):
    root=io.safe(root);output=analysis_contents(root)
    m=dict(schema='hcr-exp29-analysis-v1',files={n:io.sha(b) for n,b in output.items()})
    if verify:
        io.require(io.load(root/'analysis/manifest.json')==m,'recomputed analysis manifest differs')
        io.verify_files(root/'analysis',m['files'],extra=('manifest.json',))
    else:
        (root/'analysis').mkdir(exist_ok=False)
        for n,b in output.items():io.write(io.child(root/'analysis',n),b)
        io.put(root/'analysis/manifest.json',m)
    return dict(verified=True,files=len(output),read_only=verify)


def verify_bundle(root,full_parent=True):
    root=io.safe(root);m=io.load(root/'bundle_manifest.json')
    io.require(m['schema']=='hcr-exp29-bundle-v1','bundle schema')
    io.verify_files(root,m['files'],extra=('bundle_manifest.json',))
    if full_parent:
        parent=root/'basis/exp28';snapshot=parent/'source'
        # Read-only parent replay writes no new file into sealed evidence.
        io.command([sys.executable,'-X','utf8','-B',str(snapshot/'scripts/r047_cli.py'),'verify','--run',str(parent)],cwd=snapshot/'src')
    analyze(root,verify=True)
    return dict(verified=True,files=len(m['files']),full_parent_replay=full_parent)


def seal_bundle(root):
    io.put(root/'bundle_manifest.json',dict(schema='hcr-exp29-bundle-v1',files=io.hashes(root)))
    return dict(files=len(io.load(root/'bundle_manifest.json')['files']))


def archive(root):
    root=io.safe(root);m=io.load(root/'bundle_manifest.json');io.verify_files(root,m['files'],extra=('bundle_manifest.json',))
    dest=root.with_name(root.name+'_evidence.zip')
    with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n in io.names(root):z.write(io.child(root,n),n)
    with zipfile.ZipFile(dest) as z:
        io.require(z.testzip() is None and set(z.namelist())==set(io.names(root)),'ZIP inventory/CRC')
        for n in z.namelist():io.require(io.sha(z.read(n))==io.sha(io.read(io.child(root,n))),'ZIP bytes differ: '+n)
    receipt=dict(archive=dest.name,sha256=io.sha(io.read(dest)),bytes=dest.stat().st_size,
        bundle_manifest_sha256=io.sha(io.read(root/'bundle_manifest.json')))
    io.put(dest.with_name(dest.name+'.receipt.json'),receipt);return receipt


def run(repo, *, population="research"):
    io.require(population in ("research","implementation_validation"),"population label")
    repo=io.safe(repo)
    # Compact names keep nested parent evidence shorter than the previous long run IDs.
    tag=datetime.now(timezone.utc).strftime('%y%m%d-%H%M%S')+'-'+uuid4().hex[:8]
    root=repo/'HCR-Evidence/exp29'/('r048-'+tag);root.mkdir(parents=True,exist_ok=False)
    io.write(root/'.gitattributes',provenance.ATTRIBUTES)
    io.write(root/'.gitignore',b'# Preserve all generated evidence, including original logs.\n!*\n')
    try:
        env=stage(root,'01-baseline',lambda:provenance.repository_check(repo))
        stage(root,'02-release',lambda:dict(files=len(provenance.package_check(repo)['files'])))
        restored=stage(root,'03-parent-copy',lambda:provenance.parent_copy_from_repo(repo,root/'basis/exp28'))
        io.put(root/'parent_byte_recovery.json',restored)
        stage(root,'04-parent-replay',lambda:provenance.verify_parent(root/'basis/exp28',root/'execution/04-parent-replay.txt'))
        files=stage(root,'05-source-freeze',lambda:provenance.copy_source(repo,root/'basis/exp28/source',root/'source'))
        snapshot=root/'source'
        io.put(root/'environment.json',dict(python=sys.version,platform=platform.platform(),**env,
            automatic_retry=False,models_downloaded=False,old_evidence_modified=False))
        def tests(which):
            return io.command([sys.executable,'-X','utf8','-B',str(snapshot/'scripts/r048_tests.py'),
                '--root',str(snapshot),'--suite',which],cwd=snapshot/'src',log=root/'execution'/('tests-'+which+'.txt'))
        stage(root,'06-inherited-tests',lambda:tests('inherited'))
        stage(root,'07-new-tests',lambda:tests('new'))
        stage(root,'08-publication-preflight',lambda:provenance.publication_check(repo,root))
        plan=dict(schema='hcr-exp29-plan-v1',population=population,created_utc=io.now(),**spec.body(),
            source_hashes=files,parent_bundle_sha256=io.sha(io.read(root/'basis/exp28/bundle_manifest.json')))
        validate_plan(plan);check_source(root,plan);io.put(root/'plan.json',plan)
        cli=snapshot/'scripts/r048_cli.py'
        stage(root,'09-execute',lambda:io.command([sys.executable,'-X','utf8','-B',str(cli),'execute','--run',str(root)],
            cwd=snapshot/'src',log=root/'execution/09-execute.txt'))
        stage(root,'10-seal-raw',lambda:seal_raw(root))
        stage(root,'11-audit',lambda:io.command([sys.executable,'-X','utf8','-B',str(cli),'analyze','--run',str(root)],
            cwd=snapshot/'src',log=root/'execution/11-audit.txt'))
        stage(root,'12-analysis-replay',lambda:io.command([sys.executable,'-X','utf8','-B',str(cli),'verify-analysis','--run',str(root)],
            cwd=snapshot/'src',log=root/'execution/12-analysis-replay.txt'))
        io.write(root/'VERIFY_BUNDLE.cmd',io.read(snapshot/'scripts/r048_verify_bundle.cmd'))
        stage(root,'13-publication',lambda:provenance.publication_check(repo,root))
        io.put(root/'execution/completed.json',dict(state='execution_and_analysis_completed',automatic_retry=False,finished_utc=io.now()))
        seal_bundle(root)
        # Keep all post-seal receipts outside the sealed directory.
        receipt_dir=root.parent/(root.name+'_receipts');receipt_dir.mkdir(exist_ok=False)
        result=io.command([sys.executable,'-X','utf8','-B',str(cli),'verify','--run',str(root)],
            cwd=snapshot/'src',log=receipt_dir/'final-verify.txt')
        io.put(receipt_dir/'final-verify.json',result)
        io.put(receipt_dir/'git-clean.json',provenance.publication_check(repo,root))
        bundle=archive(root)
        print('Summary: '+str(root/'analysis/summary.ko.md'),flush=True)
        print('Evidence: '+str(root.parent/bundle['archive']),flush=True)
        return dict(run=str(root),archive=bundle)
    except BaseException as e:
        target=root.parent/(root.name+'_receipts') if (root/'bundle_manifest.json').exists() else root
        target.mkdir(parents=True,exist_ok=True);io.failure(target,'pipeline',e)
        print('Failed; original and partial evidence preserved: '+str(target),file=sys.stderr,flush=True)
        raise
