"""Append-only plan/raw/audit/bundle pipeline. No outcome-based repair or retry."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import platform
import subprocess
import sys
import traceback
import zipfile
from . import storage as io, spec, provenance

RAW_FIXED = ('plan.json','environment.json','attempts.jsonl')


def now(): return datetime.now(timezone.utc).isoformat()


def kind(exc):
    if isinstance(exc, KeyboardInterrupt):return 'interrupted'
    if isinstance(exc, (UnicodeError,)):return 'parsing_failure'
    if isinstance(exc, (ImportError,)):return 'dependency_failure'
    if isinstance(exc, (ValueError, KeyError, TypeError)):return 'schema_contract_or_measurement_failure'
    if isinstance(exc, OSError):return 'runtime_io_failure'
    return 'runtime_failure'


def failure(root, stage, exc):
    root=io.safe(root)
    target=root/'failure.json'
    if target.exists(): return  # The first error is never replaced by a secondary error.
    io.put(target,dict(stage=stage,classification=kind(exc),error_type=type(exc).__name__,message=str(exc),
        traceback=traceback.format_exc(),automatic_retry=False,created_utc=now(),partial_evidence_preserved=True))


def stage(root, name, callback):
    logs=io.safe(root)/'execution';logs.mkdir(parents=True,exist_ok=True)
    io.put(logs/(name+'.started.json'),dict(stage=name,started_utc=now()))
    try:
        result=callback()
        io.put(logs/(name+'.completed.json'),dict(stage=name,finished_utc=now(),result=result))
        print('Completed: '+name,flush=True)
        return result
    except BaseException as exc:
        failure(root,name,exc)
        raise


def make_plan(repo, parent, parent_report, population='research'):
    io.require(population in ('research','implementation_validation'), 'unknown population')
    return dict(schema='hcr-exp28-plan-v1',population=population,created_utc=now(),
        base_commit=spec.BASE_COMMIT,**spec.expected_plan_body(),
        source_files=provenance.source_inventory(repo),
        parent_files={n:io.file_hash(io.child(parent,n)) for n in io.inventory(parent)},
        parent_verification=parent_report)


def validate_plan(plan):
    keys={'schema','population','created_utc','base_commit','design','sources','cases','worlds','trials',
          'kernel_config','source_files','parent_files','parent_verification'}
    io.require(set(plan)==keys and plan['schema']=='hcr-exp28-plan-v1', 'plan fields/schema')
    io.require(plan['population'] in ('research','implementation_validation') and plan['base_commit']==spec.BASE_COMMIT,'plan origin')
    spec.validate_body(plan)


def copy_frozen_inputs(repo,parent,root,plan):
    validate_plan(plan)
    for name,h in plan['source_files'].items():
        src=io.child(repo,name);data=src.read_bytes()
        io.require(io.sha(data)==h,'source changed while freezing: '+name)
        io.write(io.child(root,'source/'+name),data)
    for name,h in plan['parent_files'].items():
        data=io.child(parent,name).read_bytes()
        io.require(io.sha(data)==h,'parent changed while freezing: '+name)
        io.write(io.child(root,'basis/exp27/'+name),data)


def produce(plan,root):
    """Only public observation/config/arm/A record reach the runtime."""
    from .runtime import run_query
    root=io.safe(root);root.mkdir(parents=True,exist_ok=True)
    cases={x['id']:x for x in plan['cases']};sources={};completed=0;query=None
    try:
        with (root/'attempts.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            def emit(obj): io.append_event(stream,obj)
            for variant in spec.VARIANTS:
                query=dict(kind='A',id=variant);emit(dict(event='query_started',query=query))
                r=run_query(plan['sources'][variant],plan['kernel_config'],
                    event_sink=lambda ev:emit(dict(event='query_event',query=query,record=ev)))
                raw=dict(query=query,record=r);io.put(root/'raw'/('A_'+variant+'.json'),raw)
                sources[variant]=r;completed+=1
                emit(dict(event='query_completed',query=query,raw_sha256=io.digest(raw)))
                print('A preserved: '+variant,flush=True)
            for trial in plan['trials']:
                query=dict(kind='B',trial=trial);source=sources[trial['source']];before=io.digest(source)
                emit(dict(event='query_started',query=query))
                r=run_query(cases[trial['case']]['observation'],plan['kernel_config'],trial['arm'],source,
                    event_sink=lambda ev:emit(dict(event='query_event',query=query,record=ev)))
                io.require(before==io.digest(source),'source A mutated during B')
                raw=dict(query=query,record=r);io.put(root/'raw'/('B_'+trial['id']+'.json'),raw)
                completed+=1;emit(dict(event='query_completed',query=query,raw_sha256=io.digest(raw)))
                print(f"B preserved: {completed-2}/42 {trial['id']}",flush=True)
        return dict(source_queries=2,followups=42,completed=completed,population=plan['population'])
    except BaseException as exc:
        failure(root,'produce',exc)
        io.put(root/'partial_progress.json',dict(completed=completed,current=query,automatic_retry=False))
        raise


def raw_names(plan):
    return (set(RAW_FIXED)|{'source/'+n for n in plan['source_files']}|
            {'basis/exp27/'+n for n in plan['parent_files']}|
            {'raw/A_'+v+'.json' for v in spec.VARIANTS}|
            {'raw/B_'+t['id']+'.json' for t in plan['trials']})


def seal_raw(root,plan):
    names=raw_names(plan)
    actual={n for n in io.inventory(root) if n in RAW_FIXED or n.startswith(('raw/','source/','basis/'))}
    io.require(actual==names,'raw inventory before sealing')
    m=dict(schema='hcr-exp28-raw-manifest-v1',state='raw_complete',
           files={n:io.file_hash(io.child(root,n)) for n in sorted(names)})
    io.put(root/'raw_manifest.json',m)
    return dict(raw_files=len(names),manifest_sha256=io.file_hash(root/'raw_manifest.json'))


def read_and_audit(plan,root):
    """Independent native replay and exact stream/record consistency. Never reruns model."""
    from .audit import audit_record
    sources={};rows={};checks={};source_checks={};sequence=[]
    for variant in spec.VARIANTS:
        raw=io.load(root/'raw'/('A_'+variant+'.json'));r=raw['record']
        io.require(set(raw)=={'query','record'} and raw['query']==dict(kind='A',id=variant),'A query identity')
        io.require(r['observation']==plan['sources'][variant] and r['config']==plan['kernel_config'] and r['arm']=='cold','A input')
        a=audit_record(r);source_checks[variant]=a;sources[variant]=r;sequence.append(raw)
    cases={x['id']:x for x in plan['cases']}
    for trial in plan['trials']:
        raw=io.load(root/'raw'/('B_'+trial['id']+'.json'));r=raw['record']
        io.require(set(raw)=={'query','record'} and raw['query']==dict(kind='B',trial=trial),'B query identity')
        io.require(r['observation']==cases[trial['case']]['observation'] and r['config']==plan['kernel_config'] and r['arm']==trial['arm'],'B input changed')
        checks[trial['id']]=audit_record(r,sources[trial['source']],plan['worlds'][trial['case']])
        rows[trial['id']]=r;sequence.append(raw)
    count=0
    with (root/'attempts.jsonl').open(encoding='utf-8') as stream:
        def take(expected):
            nonlocal count
            line=stream.readline();io.require(bool(line) and io.loads(line)==expected,'stream mismatch at '+str(count))
            count+=1
        for raw in sequence:
            q=raw['query'];take(dict(event='query_started',query=q))
            for ev in raw['record']['events']:take(dict(event='query_event',query=q,record=ev))
            take(dict(event='query_completed',query=q,raw_sha256=io.digest(raw)))
        io.require(stream.read()=='','unregistered extra trial, retry, or trailing event')
    return sources,rows,checks,source_checks,count


def analysis_contents(root):
    from . import reporting
    root=io.safe(root);plan=io.load(root/'plan.json');validate_plan(plan)
    m=io.load(root/'raw_manifest.json')
    io.require(m['schema']=='hcr-exp28-raw-manifest-v1' and m['state']=='raw_complete','raw not sealed')
    io.require(set(m['files'])==raw_names(plan),'raw manifest completeness')
    actual={n for n in io.inventory(root) if n in RAW_FIXED or n.startswith(('raw/','source/','basis/'))}
    io.require(actual==raw_names(plan),'raw inventory changed')
    provenance.check_inventory(root,m['files'])
    provenance.native_check(root/'source');provenance.package_check(root/'source')
    for n,h in plan['source_files'].items():io.require(io.file_hash(io.child(root,'source/'+n))==h,'frozen source')
    io.require(set(io.inventory(root/'basis/exp27'))==set(plan['parent_files']),'frozen parent inventory')
    provenance.check_inventory(root/'basis/exp27',plan['parent_files'])
    parent=provenance.parent_check(root/'basis/exp27')
    io.require(parent==plan['parent_verification'],'parent re-verification differs')
    src,rows,checks,sc,stream=read_and_audit(plan,root)
    s=reporting.summarize(plan,src,rows,checks)
    audit=dict(schema='hcr-exp28-audit-v1',verified=True,population=plan['population'],
        source_queries=len(src),followups=len(rows),stream_records=stream,
        scalar_ticks=sum(a['scalar_ticks'] for a in list(checks.values())+list(sc.values())),
        scalar_tolerance=2e-12,all_scalar_errors_within_tolerance=True,
        raw_manifest_sha256=io.file_hash(root/'raw_manifest.json'),
        separate_equations_and_proof_semantics=True,full_AdaptiveSession_replayed=False,
        hypothesis_support_required_for_validity=False)
    stable_checks = lambda group: {k:dict({a:b for a,b in v.items() if a!='max_scalar_error'},scalar_error_within_tolerance=True) for k,v in group.items()}
    objects={'summary.json':s,'audit.json':audit,'record_audits.json':stable_checks(checks),
             'source_audits.json':stable_checks(sc),'claims.json':s['claims']}
    out={n:io.canonical(v)+b'\n' for n,v in objects.items()}
    out['summary.ko.md']=reporting.render(s);out['parent_review.ko.md']=provenance.parent_addendum(parent)
    for name in ('trials','pairs','hypotheses','cost_differences','interactions','ID_controls','transfer_maps','dependency_scans','signatures'):
        out[name+'.csv']=reporting.csv_bytes(s[name])
    return out


def analyze(root,verify=False):
    root=io.safe(root);out=analysis_contents(root);dest=root/'analysis'
    m=dict(schema='hcr-exp28-analysis-manifest-v1',files={n:io.sha(b) for n,b in out.items()})
    if verify:
        io.require(io.load(dest/'manifest.json')==m,'analysis manifest differs from recomputation')
        io.require(set(io.inventory(dest))==set(out)|{'manifest.json'},'analysis inventory changed')
        for name,data in out.items():io.require(io.child(dest,name).read_bytes()==data,'analysis differs: '+name)
    else:
        dest.mkdir(parents=True,exist_ok=False)
        for name,data in out.items():io.write(io.child(dest,name),data)
        io.put(dest/'manifest.json',m)
    return dict(verified=True,read_only=verify,analysis_files=len(out))


def seal_bundle(root):
    names=io.inventory(root)
    io.require('bundle_manifest.json' not in names,'bundle already sealed')
    io.put(root/'bundle_manifest.json',dict(schema='hcr-exp28-bundle-v1',
        files={n:io.file_hash(io.child(root,n)) for n in names}))
    return verify_bundle_files(root)


def verify_bundle_files(root):
    root=io.safe(root);m=io.load(root/'bundle_manifest.json')
    io.require(m['schema']=='hcr-exp28-bundle-v1','bundle schema')
    io.require(set(io.inventory(root))==set(m['files'])|{'bundle_manifest.json'},'bundle inventory differs')
    provenance.check_inventory(root,m['files'])
    return dict(verified=True,files=len(m['files']))


def archive(root):
    root=io.safe(root);verify_bundle_files(root)
    dest=root.with_name(root.name+'_evidence.zip')
    with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name in io.inventory(root):z.write(io.child(root,name),name)
    with zipfile.ZipFile(dest) as z:
        io.require(z.testzip() is None and set(z.namelist())==set(io.inventory(root)),'archive inventory/CRC')
        for name in z.namelist():io.require(io.sha(z.read(name))==io.file_hash(io.child(root,name)),'archive bytes')
    receipt=dict(archive=dest.name,sha256=io.file_hash(dest),bytes=dest.stat().st_size,
                 independently_audited_source=io.file_hash(root/'bundle_manifest.json'))
    io.put(dest.with_name(dest.name+'.receipt.json'),receipt)
    return receipt


def pipeline(repo):
    repo=io.safe(repo);tag=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')+'-'+uuid4().hex[:8]
    root=repo/'HCR-Evidence'/'exp28'/('r047-'+tag);root.mkdir(parents=True,exist_ok=False)
    try:
        env=stage(root,'01-baseline',lambda:provenance.repository_check(repo))
        stage(root,'02-release',lambda:dict(files=len(provenance.package_check(repo)['files'])))
        parent=repo/spec.PARENT_RUN
        pr=stage(root,'03-parent',lambda:provenance.parent_check(parent))
        def tests():
            tests_dir=repo/'tools'/'r047_state_ablation'/'tests'
            # HF2: run tests from repo/src so root-level hcr.py cannot shadow src/hcr package.
            cmd=[sys.executable,'-X','utf8','-B','-m','unittest','discover','-s',str(tests_dir),'-p','test_*.py','-v','-f']
            # Source path selects the native package rather than root-level hcr.py.
            import os
            childenv=dict(os.environ,PYTHONPATH=str(repo/'src')+os.pathsep+str(repo),PYTHONDONTWRITEBYTECODE='1')
            with (root/'execution'/'04-tests.txt').open('xb') as out:
                p=subprocess.run(cmd,cwd=repo/'src',env=childenv,stdout=out,stderr=subprocess.STDOUT)
            io.require(p.returncode==0,'self-test failed; see execution/04-tests.txt')
            return dict(returncode=p.returncode,population='implementation_validation_not_research')
        stage(root,'04-tests',tests)
        from .regression import run_reference
        stage(root,'05-regression',run_reference)
        plan=make_plan(repo,parent,pr)
        io.put(root/'plan.json',plan)
        io.put(root/'environment.json',dict(python=sys.version,platform=platform.platform(),**env,
            automatic_retry=False,external_llm=False,source_snapshot_before_queries=True))
        stage(root,'06-freeze',lambda:(copy_frozen_inputs(repo,parent,root,plan) or dict(plan_sha256=io.digest(plan))))
        stage(root,'07-execute',lambda:produce(plan,root))
        stage(root,'08-seal-raw',lambda:seal_raw(root,plan))
        stage(root,'09-audit',lambda:analyze(root))
        stage(root,'10-verify',lambda:analyze(root,verify=True))
        io.write(root/'VERIFY_BUNDLE.cmd',(repo/'scripts/r047_verify_bundle.cmd').read_bytes())
        io.put(root/'execution/completed.json',dict(state='all_commands_completed',automatic_retry=False,finished_utc=now()))
        seal_bundle(root)  # No more writes inside root after this seal.
        receipt=archive(root)
        print('Evidence: '+str(root),flush=True)
        print('Summary: '+str(root/'analysis/summary.ko.md'),flush=True)
        print('Archive: '+str(root.parent/receipt['archive']),flush=True)
        return dict(run=str(root),archive=receipt)
    except BaseException as exc:
        # Archive errors are recorded outside a sealed run so its seal stays valid.
        target=root.parent/(root.name+'_failure') if (root/'bundle_manifest.json').exists() else root
        target.mkdir(parents=True,exist_ok=True);failure(target,'pipeline',exc)
        print('Failed; preserved evidence: '+str(target),file=sys.stderr,flush=True)
        raise
