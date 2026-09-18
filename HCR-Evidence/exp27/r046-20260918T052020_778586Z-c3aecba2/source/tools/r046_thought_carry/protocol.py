"""Freeze -> append-only raw -> independent audit -> verify. No network, retries or repairs."""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from copy import deepcopy
import json,os,platform,sys,traceback,subprocess
from . import storage as io, sources,spec
from .contracts import *


def prepare(parent,out):
    root=sources.repo_root();src=io.safe(parent);target=io.safe(out);io.disjoint(src,target)
    inv=sources.baseline(root);basis=sources.read_basis(src);a,c,w=spec.observations()
    plan=dict(schema=SCHEMA,mode='research',created_utc=datetime.now(timezone.utc).isoformat(),parent_path=str(src),
        conditions=spec.conditions(),sources=a,cases=c,worlds=w,trials=spec.trial_order(),kernel_config=basis['config'],
        memory_sha256=io.digest(basis['memory']),parent_hashes=basis['hashes'],source_hashes=inv)
    validate_plan(plan,src);io.put(target,plan)
    return dict(plan=str(target),sha256=io.digest(plan),source_queries=2,followups=24)


def validate_plan(plan,parent=None,installed=True):
    keys={'schema','mode','created_utc','parent_path','conditions','sources','cases','worlds','trials',
          'kernel_config','memory_sha256','parent_hashes','source_hashes'}
    io.require(set(plan)==keys and plan['schema']==SCHEMA and plan['mode']=='research','plan schema/mode')
    a,c,w=spec.observations()
    io.require(plan['conditions']==spec.conditions() and plan['sources']==a and plan['cases']==c and
        plan['worlds']==w and plan['trials']==spec.trial_order(),'frozen condition/input/trial changed')
    if installed:io.require(plan['source_hashes']==sources.baseline(sources.repo_root()),'sources changed after freeze')
    basis=sources.read_basis(parent or plan['parent_path'])
    io.require(plan['parent_hashes']==basis['hashes'] and plan['kernel_config']==basis['config'] and
        plan['memory_sha256']==io.digest(basis['memory']),'seed/basis changed after freeze')
    return basis


def failure_kind(exc):
    if isinstance(exc,KeyboardInterrupt):return 'interrupted'
    if isinstance(exc,ImportError):return 'dependency_failure'
    if isinstance(exc,(json.JSONDecodeError,UnicodeError)):return 'parsing_failure'
    if isinstance(exc,(ValueError,KeyError,TypeError)):return 'schema_contract_or_audit_failure'
    if isinstance(exc,OSError):return 'runtime_io_failure'
    return 'runtime_failure'


def produce(plan,root):
    """Raw query production. Called by research execute only after plan validation.
    Also directly exercised by a separately labelled integration-test harness.
    """
    from .runtime import run_query
    root=io.safe(root);sources_raw={};completed=0;current=None
    try:
        with (root/'attempts.jsonl').open('x',encoding='utf-8',newline='\n') as f:
            def emit(event):
                f.write(io.canonical(event).decode('utf-8')+'\n');f.flush();os.fsync(f.fileno())
            for variant in VARIANTS:
                current=dict(kind='A',id=variant);emit(dict(event='query_started',query=current))
                r=run_query(plan['sources'][variant],plan['kernel_config'],event_sink=lambda e:emit(dict(event='query_event',query=current,record=e)))
                raw=dict(query=current,record=r);io.put(root/'raw'/('A_'+variant+'.json'),raw)
                emit(dict(event='query_completed',query=current,raw_sha256=io.digest(raw)))
                sources_raw[variant]=r;completed+=1
                print('A source preserved: '+variant,flush=True)
            cases={c['id']:c for c in plan['cases']}
            for trial in plan['trials']:
                current=dict(kind='B',trial=trial);source=sources_raw[trial['source']];before=io.digest(source)
                emit(dict(event='query_started',query=current))
                r=run_query(cases[trial['case']]['observation'],plan['kernel_config'],trial['arm'],source,
                    event_sink=lambda e:emit(dict(event='query_event',query=current,record=e)))
                io.require(io.digest(source)==before,'source A was mutated')
                raw=dict(query=current,record=r);io.put(root/'raw'/('B_'+trial['id']+'.json'),raw)
                emit(dict(event='query_completed',query=current,raw_sha256=io.digest(raw)))
                completed+=1;print(f'B raw {completed-2}/24 preserved: {trial["id"]}',flush=True)
        return dict(source_queries=2,followups=24,completed=completed)
    except BaseException as exc:
        io.put(root/'failure.json',dict(stage='query_production',current=current,completed=completed,
            failure_kind=failure_kind(exc),error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),
            automatic_retry=False,partial_events_preserved=True))
        raise


def repository_head():
    try:
        r=subprocess.run(['git','-C',str(sources.repo_root()),'rev-parse','HEAD'],capture_output=True,text=True,timeout=5,check=True)
        return r.stdout.strip()
    except (OSError,subprocess.SubprocessError):return None


def execute(plan_path,out,parent=None):
    plan=io.load(plan_path);basis=validate_plan(plan,parent);root=io.safe(out)
    io.disjoint(root,parent or plan['parent_path']);root.mkdir(parents=True,exist_ok=False)
    try:
        io.put(root/'plan.json',plan)
        io.put(root/'environment.json',dict(python=sys.version,platform=platform.platform(),
            basis_commit=BASE_COMMIT,repository_head=repository_head(),mode='native_kernel_research_with_explicit_adapter',
            previous_AdaptiveSession_not_replaced=True,automatic_retry=False,external_llm=False))
        for name,h in plan['source_hashes'].items():
            data=io.read(io.child(sources.repo_root(),name))
            io.require(io.bytes_hash(data.replace(b'\r\n',b'\n'))==h,'source copy mismatch')
            io.write_bytes(io.child(root,'source/'+name),data)
        for name,data in basis['data'].items():io.write_bytes(io.child(root,'basis/exp26/'+name),data)
        result=produce(plan,root)
        validate_plan(plan,parent)
        io.put(root/'manifest.json',dict(schema='hcr-exp27-raw-manifest-v1',state='raw_complete',
            files={n:io.file_hash(io.child(root,n)) for n in sorted(io.inventory(root))}))
        return result
    except BaseException as exc:
        if not (root/'failure.json').exists():
            io.put(root/'failure.json',dict(stage='copy_or_seal',failure_kind=failure_kind(exc),
                error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),automatic_retry=False))
        raise


def record_audit(plan,root):
    from .evaluator import audit_record
    src={};rows={};audits={};seq=[];source_reports={}
    for variant in VARIANTS:
        q=dict(kind='A',id=variant);raw=io.load(root/'raw'/('A_'+variant+'.json'))
        io.require(raw['query']==q,'source query binding');r=raw['record']
        io.require(r['observation']==plan['sources'][variant] and r['config']==plan['kernel_config'] and r['arm']=='cold','source computation inputs')
        report=audit_record(r);source_reports[variant]=report;src[variant]=r;seq.append(raw)
    cases={c['id']:c for c in plan['cases']}
    for t in plan['trials']:
        q=dict(kind='B',trial=t);raw=io.load(root/'raw'/('B_'+t['id']+'.json'));r=raw['record']
        io.require(raw['query']==q and r['arm']==t['arm'] and r['observation']==cases[t['case']]['observation'] and r['config']==plan['kernel_config'],'followup input binding')
        report=audit_record(r,src[t['source']],plan['worlds'][t['case']]);rows[t['id']]=r;audits[t['id']]=report;seq.append(raw)
    count=0
    with (root/'attempts.jsonl').open(encoding='utf-8') as f:
        def take(value):
            nonlocal count
            line=f.readline();io.require(line and io.loads(line)==value,'stream record mismatch at '+str(count));count+=1
        for raw in seq:
            q=raw['query'];take(dict(event='query_started',query=q))
            for ev in raw['record']['events']:take(dict(event='query_event',query=q,record=ev))
            take(dict(event='query_completed',query=q,raw_sha256=io.digest(raw)))
        io.require(f.read()=='','unexpected trials/retry/tail records')
    return src,rows,audits,source_reports,count


def analysis_contents(root):
    from . import reporting
    root=io.safe(root);plan=io.load(root/'plan.json');m=io.load(root/'manifest.json')
    io.require(m['schema']=='hcr-exp27-raw-manifest-v1' and m['state']=='raw_complete','incomplete raw')
    validate_plan(plan,root/'basis/exp26')
    expected={'plan.json','environment.json','attempts.jsonl'}
    expected|={'source/'+n for n in plan['source_hashes']}
    expected|={'basis/exp26/'+n for n in plan['parent_hashes']}
    expected|={'raw/A_'+v+'.json' for v in VARIANTS}
    expected|={'raw/B_'+t['id']+'.json' for t in plan['trials']}
    actual={n for n in io.inventory(root) if not n.startswith(('analysis/','audit_failures/'))}
    io.require(set(m['files'])==expected and actual==expected|{'manifest.json'},'raw inventory')
    for n,h in m['files'].items():io.require(io.file_hash(io.child(root,n))==h,'raw byte hash: '+n)
    for n,h in plan['source_hashes'].items():io.require(io.text_hash(io.child(root,'source/'+n))==h,'snapshot source mismatch')
    src,rows,checks,sa,stream=record_audit(plan,root)
    s=reporting.summarize(plan,src,rows,checks)
    audit=dict(schema='hcr-exp27-audit-v1',verified=True,source_queries=2,followups=24,stream_records=stream,
        native_scalar_ticks=sum(r['native_cost']['kernel_ticks'] for r in src.values())+sum(r['native_cost']['kernel_ticks'] for r in rows.values()),
        state_and_proof_replayed=True,old_EXP26_replayed_here=False,old_EXP26_verify_is_launcher_precondition=True,
        hypotheses_not_validity=True,full_AdaptiveSession_replay_claimed=False,raw_manifest_sha256=io.file_hash(root/'manifest.json'))
    objects={'summary.json':s,'audit.json':audit,'source_audits.json':sa,'record_audits.json':checks,'claims.json':s['claims']}
    output={n:io.canonical(v)+b'\n' for n,v in objects.items()};output['summary.ko.md']=reporting.render(s)
    for name in ('trials','pairs','cost_differences','ID_controls','memo_controls','transfer_maps','proof_refs','signatures'):
        output[name+'.csv']=reporting.csv_bytes(s[name])
    return output


def analyze(root,verify=False):
    root=io.safe(root)
    try:
        contents=analysis_contents(root);target=root/'analysis'
        manifest=dict(schema='hcr-exp27-analysis-manifest-v1',files={n:io.bytes_hash(b) for n,b in contents.items()})
        if verify:
            io.require(io.load(target/'manifest.json')==manifest,'analysis manifest mismatch')
            io.require(io.inventory(target)==set(contents)|{'manifest.json'},'analysis inventory')
            for n,b in contents.items():io.require(io.read(target/n)==b,'analysis recomputation mismatch: '+n)
        else:
            target.mkdir(parents=True,exist_ok=False)
            for n,b in contents.items():io.write_bytes(target/n,b)
            io.put(target/'manifest.json',manifest)
        return dict(verified=True,read_only=verify,files=len(contents))
    except BaseException as exc:
        from uuid import uuid4
        io.put(root/'audit_failures'/('failure-'+uuid4().hex+'.json'),dict(error_type=type(exc).__name__,
            error=str(exc),traceback=traceback.format_exc(),automatic_retry=False,verify_mode=verify))
        raise
