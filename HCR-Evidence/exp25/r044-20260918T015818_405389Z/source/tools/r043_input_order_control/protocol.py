"""prepare → execute: 소스/입력 동결과 단회 native 실행. 검산은 audit 명령에 분리한다."""
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
import platform
import subprocess
import sys
import traceback
from . import storage as io, spec, sources, input_audit, runtime
from .contracts import BASE_COMMIT, PLAN_SCHEMA, RAW_SCHEMA, RAW_MANIFEST_SCHEMA, digest, require

PLAN_KEYS = {'schema','created_at_utc','source_run','conditions','cases','evaluation_worlds','trials',
             'parent_file_hashes','prior_run','prior_file_hashes','memory_sha256','config_sha256','dependency_source_hashes','addon_source_hashes'}


def make_plan(source_run, prior_run) -> dict:
    root, parent, seed, hashes, _ = sources.read_parent(source_run)
    cases, worlds = spec.cases(parent)
    prior_root, prior_hashes, _, _ = sources.read_prior(prior_run,parent,cases,worlds)
    plan = dict(schema=PLAN_SCHEMA, created_at_utc=datetime.now(timezone.utc).isoformat(),
        source_run=str(root), prior_run=str(prior_root), prior_file_hashes=prior_hashes, conditions=spec.conditions(parent), cases=cases,
        evaluation_worlds=worlds, trials=spec.trials(), parent_file_hashes=hashes,
        memory_sha256=digest(seed['memory']), config_sha256=digest(seed['config']),
        dependency_source_hashes=sources.dependencies(), addon_source_hashes=sources.addon_hashes())
    input_audit.check_plan_inputs(plan,parent,seed)
    return plan


def validate_plan(plan: dict, source_run=None, prior_run=None, *, check_parent=True):
    require(type(plan) is dict and set(plan) == PLAN_KEYS and plan['schema'] == PLAN_SCHEMA, 'EXP24 plan schema')
    require(type(plan['created_at_utc']) is str and type(plan['source_run']) is str, 'plan provenance')
    # native 실행과 독립 검산이 동일하게 동결된 소스를 사용하는지 검사한다.
    require(plan['dependency_source_hashes'] == sources.dependencies() and
            plan['addon_source_hashes'] == sources.addon_hashes(), '동결 이후 소스 변경')
    sources.merge_hashes(plan['dependency_source_hashes'],plan['addon_source_hashes'])
    if check_parent:
        root,parent,seed,hashes,documents = sources.read_parent(source_run or plan['source_run'])
        require(plan['parent_file_hashes'] == hashes, '동결 이후 EXP22 원자료 변경')
        input_audit.check_plan_inputs(plan,parent,seed)
        _, prior_hashes, _, _ = sources.read_prior(prior_run or plan['prior_run'],parent,plan['cases'],plan['evaluation_worlds'])
        require(prior_hashes == plan['prior_file_hashes'], 'EXP23 anchors changed after freeze')
        return root,parent,seed,documents
    return None


def prepare(source_run, prior_run, out) -> dict:
    source, target = io.safe(source_run), io.safe(out)
    io.disjoint(source,target)
    require(not target.exists(), '기존 plan 덮어쓰기 금지')
    io.disjoint(prior_run,target)
    plan = make_plan(source,prior_run)
    io.put(target,plan)
    return dict(plan=str(target), plan_sha256=digest(plan), native_trials=12,
                parent_regression_trials=6, automatic_retry=False)


def failure_kind(exc: BaseException) -> str:
    if isinstance(exc, KeyboardInterrupt): return 'interrupted'
    if isinstance(exc, (json.JSONDecodeError, UnicodeError)): return 'parsing_failure'
    if isinstance(exc, ImportError): return 'dependency_failure'
    if isinstance(exc, (ValueError, KeyError, TypeError)): return 'schema_contract_failure'
    if isinstance(exc, OSError): return 'runtime_io_failure'
    return 'runtime_failure'


def repository_head():
    try:
        return subprocess.run(['git','-C',str(sources.repo_root()),'rev-parse','HEAD'],
            capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def execute(plan: dict, out, source_run=None, prior_run=None) -> dict:
    source,parent,seed,_ = validate_plan(plan,source_run,prior_run)
    prior = io.safe(prior_run or plan['prior_run'])
    root = io.safe(out); io.disjoint(source,root); io.disjoint(prior,root)
    root.mkdir(parents=True, exist_ok=False)
    current = active_worker = None
    stage, completed = 'copy_sources', 0
    try:
        io.put(root/'plan.json',plan)
        io.put(root/'environment.json',dict(python=sys.version, platform=platform.platform(),
            repository_head=repository_head(), basis_commit=BASE_COMMIT, mode='native_experiment',
            external_llm_used=False, synthetic_backend=False, automatic_retry=False,
            source_run_used=str(source), prior_run_used=str(prior), inherited_runtime='R041_unchanged'))
        all_sources = sources.merge_hashes(plan['dependency_source_hashes'], plan['addon_source_hashes'])
        for name,h in all_sources.items():
            data = io.read(io.child(sources.repo_root(),name))
            require(io.bytes_hash(data.replace(b'\r\n',b'\n')) == h, '복사 중 소스 변경: '+name)
            io.write_bytes(io.child(root,'source/'+name),data)
        for name,h in plan['parent_file_hashes'].items():
            data = io.read(io.child(source,name))
            require(io.bytes_hash(data) == h, '복사 중 parent 변경: '+name)
            io.write_bytes(io.child(root,sources.capsule_name(name)),data)
        cases = {case['name']:case for case in plan['cases']}
        for name,h in plan['prior_file_hashes'].items():
            data = io.read(io.child(prior,name))
            require(io.bytes_hash(data) == h, 'EXP23 anchor changed while copying: '+name)
            io.write_bytes(io.child(root,sources.prior_capsule_name(name)),data)
        stage = 'native_trials'
        with (root/'attempts.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            def emit(event):
                stream.write(io.canonical(event).decode('utf-8')+'\n')
                stream.flush(); os.fsync(stream.fileno())
            for trial in plan['trials']:
                current = trial; active_worker = None
                emit(dict(event='trial_started',trial=trial))
                active_worker = runtime.worker(cases[trial['case']]['observation'],seed['config'],seed['memory'],
                    plan['conditions']['budget'], trial['scheduler'],
                    lambda event: emit(dict(event='trial_action',trial_id=trial['id'],record=event)))
                run = active_worker.run()
                require(run['backend'] == run['base']['backend'] == 'native_hcr', 'synthetic backend 본 실험 혼입')
                raw = dict(schema=RAW_SCHEMA,trial=trial,run=run)
                io.put(root/'raw'/f"{trial['id']}.json",raw)
                emit(dict(event='trial_completed',trial_id=trial['id'],raw_sha256=digest(raw)))
                completed += 1
                print(f'EXP-24 native trial {completed}/12 원문 보존',flush=True)
        # 다른 프로세스가 파일을 바꾼 경우 완료로 봉인하지 않는다.
        validate_plan(plan,source,prior)
        io.put(root/'manifest.json',dict(schema=RAW_MANIFEST_SCHEMA,state='raw_complete',
            independent_audit_pending=True,
            files={name:io.file_hash(root/name) for name in sorted(io.inventory(root))}))
        return dict(raw_complete=True,native_trials=completed,independent_audit_pending=True)
    except BaseException as exc:
        failure = dict(status=failure_kind(exc),stage=stage,trial=current,completed_trials=completed,
            error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),automatic_retry=False)
        if active_worker is not None:
            try: failure['partial_evidence'] = active_worker.partial_evidence()
            except BaseException as partial: failure['partial_capture_error'] = repr(partial)
        try: io.put(root/'failure.json',failure)
        except OSError as write_error: print('failure.json 저장 실패: '+str(write_error),file=sys.stderr)
        raise
