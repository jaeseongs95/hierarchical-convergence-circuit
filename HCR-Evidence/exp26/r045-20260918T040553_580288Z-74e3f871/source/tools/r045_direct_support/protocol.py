"""Freeze sources/inputs, preserve raw once, and leave scientific evaluation to audit."""
from datetime import datetime, timezone
import json
import os
import platform
import subprocess
import sys
import traceback
from . import storage as io, sources, spec, input_audit, runtime
from .contracts import BASE_COMMIT, PLAN_SCHEMA, RAW_SCHEMA, RAW_MANIFEST_SCHEMA

PLAN_KEYS = {'schema','created_at_utc','source_run','conditions','cases','evaluation_worlds','trials',
             'parent_file_hashes','memory_sha256','config_sha256','dependency_source_hashes','addon_source_hashes'}


def make_plan(source_run):
    root, parent, seed, hashes, _ = sources.read_parent(source_run)
    cases, worlds = spec.cases()
    plan = dict(schema=PLAN_SCHEMA, created_at_utc=datetime.now(timezone.utc).isoformat(), source_run=str(root),
        conditions=spec.conditions(parent), cases=cases, evaluation_worlds=worlds, trials=spec.trials(),
        parent_file_hashes=hashes, memory_sha256=io.digest(seed['memory']), config_sha256=io.digest(seed['config']),
        dependency_source_hashes=sources.dependencies(), addon_source_hashes=sources.addon_hashes())
    input_audit.check_plan_inputs(plan,parent,seed)
    return plan


def validate_plan(plan, source_run=None, *, check_parent=True):
    io.require(type(plan) is dict and set(plan) == PLAN_KEYS and plan['schema'] == PLAN_SCHEMA, 'EXP26 plan schema')
    io.require(type(plan['created_at_utc']) is str and type(plan['source_run']) is str, 'plan provenance')
    io.require(plan['dependency_source_hashes'] == sources.dependencies() and
        plan['addon_source_hashes'] == sources.addon_hashes(), 'source changed after freeze')
    sources.merge_hashes(plan['dependency_source_hashes'],plan['addon_source_hashes'])
    if check_parent:
        root,parent,seed,hashes,docs = sources.read_parent(source_run or plan['source_run'])
        io.require(plan['parent_file_hashes'] == hashes, 'EXP25 capsule changed after freeze')
        input_audit.check_plan_inputs(plan,parent,seed)
        return root,parent,seed,docs
    return None


def prepare(source_run, out):
    source,target=io.safe(source_run),io.safe(out)
    io.disjoint(source,target);io.require(not target.exists(),'existing plan is not overwritten')
    plan=make_plan(source);io.put(target,plan)
    return dict(plan=str(target),plan_sha256=io.digest(plan),native_trials=12,primary_pairs=2,gate_pairs=6,automatic_retry=False)


def failure_kind(exc):
    if isinstance(exc, KeyboardInterrupt): return 'interrupted'
    if isinstance(exc, (json.JSONDecodeError, UnicodeError)): return 'parsing_failure'
    if isinstance(exc, ImportError): return 'dependency_failure'
    if isinstance(exc, (ValueError, KeyError, TypeError)): return 'schema_contract_failure'
    if isinstance(exc, OSError): return 'runtime_io_failure'
    return 'runtime_failure'


def repository_head():
    try:
        return subprocess.run(['git','-C',str(sources.repo_root()),'rev-parse','HEAD'],
            capture_output=True,text=True,timeout=10,check=True).stdout.strip()
    except (OSError,subprocess.SubprocessError):
        return None


def execute(plan, out, source_run=None):
    source,parent,seed,_=validate_plan(plan,source_run)
    root=io.safe(out);io.disjoint(source,root)
    root.mkdir(parents=True,exist_ok=False)
    stage='copy_frozen_inputs';current=active=None;completed=0
    try:
        io.put(root/'plan.json',plan)
        io.put(root/'environment.json',dict(python=sys.version,platform=platform.platform(),
            repository_head=repository_head(),basis_commit=BASE_COMMIT,mode='native_experiment',
            synthetic_backend=False,external_llm_used=False,automatic_retry=False,source_run_used=str(source),
            inherited_runtime='R044_worker_R041_loop_native_constructor_gate_unchanged'))
        all_sources=sources.merge_hashes(plan['dependency_source_hashes'],plan['addon_source_hashes'])
        for name,h in all_sources.items():
            data=io.read(io.child(sources.repo_root(),name))
            io.require(io.bytes_hash(data.replace(b'\r\n',b'\n'))==h,'source changed during copy: '+name)
            io.write_bytes(io.child(root,'source/'+name),data)
        for name,h in plan['parent_file_hashes'].items():
            data=io.read(io.child(source,name));io.require(io.bytes_hash(data)==h,'EXP25 changed during copy: '+name)
            io.write_bytes(io.child(root,sources.capsule_name(name)),data)
        stage='native_trials';cases={c['name']:c for c in plan['cases']}
        with (root/'attempts.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            def emit(event):
                stream.write(io.canonical(event).decode('utf-8')+'\n');stream.flush();os.fsync(stream.fileno())
            for trial in plan['trials']:
                current=trial;active=None
                emit(dict(event='trial_started',trial=trial))
                active=runtime.worker(cases[trial['case']]['observation'],seed['config'],seed['memory'],
                    plan['conditions']['budget'],trial['use_circuits'],
                    lambda event: emit(dict(event='trial_action',trial_id=trial['id'],record=event)))
                run=active.run()
                io.require(run['backend']==run['base']['backend']=='native_hcr','synthetic backend in research population')
                raw=dict(schema=RAW_SCHEMA,trial=trial,run=run)
                io.put(root/'raw'/f"{trial['id']}.json",raw)
                emit(dict(event='trial_completed',trial_id=trial['id'],raw_sha256=io.digest(raw)))
                completed+=1
                print(f'EXP-26 native trial {completed}/12 raw preserved',flush=True)
        stage='seal_raw'
        validate_plan(plan,source)
        io.put(root/'manifest.json',dict(schema=RAW_MANIFEST_SCHEMA,state='raw_complete',independent_audit_pending=True,
            files={n:io.file_hash(root/n) for n in sorted(io.inventory(root))}))
        return dict(raw_complete=True,native_trials=completed,independent_audit_pending=True)
    except BaseException as exc:
        failure=dict(status=failure_kind(exc),stage=stage,trial=current,completed_trials=completed,
            error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),automatic_retry=False)
        if active is not None:
            try:
                partial=active.partial_evidence();io.canonical(partial);failure['partial_evidence']=partial
            except BaseException as partial: failure['partial_capture_error']=repr(partial)
        try: io.put(root/'failure.json',failure)
        except OSError as write_error: print('failure evidence write failed: '+repr(write_error),file=sys.stderr)
        raise
