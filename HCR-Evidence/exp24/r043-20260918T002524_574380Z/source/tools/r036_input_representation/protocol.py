"""EXP-17 조건 동결/실행. generator는 외부 정답이나 진단 분류를 계산하지 않는다."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback
from r035_frozen_selection import storage as io
from r035_frozen_selection.contracts import Limits, digest, require
from r035_frozen_selection.native_bridge import project
from r035_frozen_selection.selection import run_policy
from . import spec, sources
from .transforms import transform_input, validate_observation
from .native_bridge import NativeTrial


def make_plan(source_run) -> dict:
    registry=sources.check_dependencies()
    source,manifest,previous,seed=sources.read_source(source_run)
    native={n:h for n,h in registry['files'].items() if n.startswith('src/hcr/')}
    require(previous['source_hashes']==native,'seed와 native 실행 소스 불일치')
    core=seed['document']['engine'];cases=spec.public_cases(previous)
    require(len(cases)==8 and len({c['name'] for c in cases})==8,'EXP-15의 8개 기본 입력을 모두 사용해야 합니다.')
    for c in cases:validate_observation(c['observation'])
    return dict(schema='hcr-exp17-plan-v1',created_at_utc=datetime.now(timezone.utc).isoformat(),
        conditions=spec.conditions(),cases=cases,trials=spec.trials(cases),source_run=str(source),
        upstream_file_hashes=sources.source_hashes(source),memory_sha256=digest(core['memory']),config_sha256=digest(core['config']),
        dependency_source_hashes=registry['files'],addon_source_hashes=sources.code_hashes(),
        prior_result_basis='EXP-16 fixed-state proof selection; next intervention moves representation to input boundary')


def validate_plan(plan: dict, source_run=None, *, check_upstream=True):
    keys={'schema','created_at_utc','conditions','cases','trials','source_run','upstream_file_hashes',
          'memory_sha256','config_sha256','dependency_source_hashes','addon_source_hashes','prior_result_basis'}
    require(set(plan)==keys and plan['schema']=='hcr-exp17-plan-v1','EXP-17 plan schema')
    require(digest(plan['conditions'])==digest(spec.conditions()) and digest(plan['trials'])==digest(spec.trials(plan['cases'])),'조건 동결 이후 설계 변경')
    require(plan['dependency_source_hashes']==sources.check_dependencies()['files'] and
            plan['addon_source_hashes']==sources.code_hashes(),'조건 동결 이후 소스 변경')
    require(len(plan['cases'])==8 and len({c['name'] for c in plan['cases']})==8,'입력 population')
    for c in plan['cases']:validate_observation(c['observation'])
    require(set(plan['upstream_file_hashes'])==set(sources.UPSTREAM_FILES),'EXP-15 출처 inventory')
    if check_upstream:
        source,_,old,seed=sources.read_source(source_run or plan['source_run'])
        require(sources.source_hashes(source)==plan['upstream_file_hashes'],'조건 동결 이후 EXP-15 원자료 변경')
        require(spec.public_cases(old)==plan['cases'] and digest(seed['document']['engine']['memory'])==plan['memory_sha256']
            and digest(seed['document']['engine']['config'])==plan['config_sha256'],'입력/memory/config 동결 불일치')
        return source
    return None


def prepare(source_run,out):
    source=io.safe(source_run);target=io.safe(out)
    require(not target.exists(),'기존 계획은 덮어쓰지 않습니다.')
    require(target!=source and source not in target.parents,'원자료 안에 계획을 쓰지 않습니다.')
    plan=make_plan(source);io.put(target,plan)
    return dict(plan=str(target),native_trials=len(plan['trials']),
        readouts='data dependent: first native decision and every actual continuation readout',
        proof_policies_per_readout=3,source_native_audited_in_this_step=False)


def generate(plan,out,source_run=None):
    source=validate_plan(plan,source_run);root=io.safe(out)
    require(root!=source and source not in root.parents and root not in source.parents,'입력/output 폴더 중첩 금지')
    root.mkdir(parents=True,exist_ok=False)
    stage='source';current=None;worker=None;completed=0;readouts=0
    try:
        io.put(root/'plan.json',plan)
        try:
            cp=subprocess.run(['git','-C',str(sources.repo_root()),'rev-parse','HEAD'],capture_output=True,text=True,timeout=10,check=True)
            head=cp.stdout.strip()
        except (OSError,subprocess.SubprocessError):head=None
        io.put(root/'environment.json',dict(python=sys.version,platform=platform.platform(),repository_head=head,
            basis_commit=spec.BASE_COMMIT,automatic_retry=False,external_llm_used=False,
            native_graph_execution_requested=True,reuses_previous_graph_states=False,
            historical_memory_reused=True,source_run_used=str(source)))
        all_sources=plan['dependency_source_hashes']|plan['addon_source_hashes']
        for name,h in all_sources.items():
            data=io.read(io.child(sources.repo_root(),name))
            require(io.sha_bytes(data.replace(b'\r\n',b'\n'))==h,'copy 중 소스 변경: '+name)
            io.put_bytes(io.child(root,'source/'+name),data)
        for name,h in plan['upstream_file_hashes'].items():
            data=io.read(io.child(source,name));require(io.sha_bytes(data)==h,'copy 중 upstream 변경: '+name)
            io.put_bytes(io.child(root,'upstream/'+name),data)
        seed=io.load(root/'upstream/seed/6.json')['document']['engine'];cases={c['name']:c for c in plan['cases']}
        stage='native_trials'
        with (root/'attempts.jsonl').open('x',encoding='utf-8',newline='\n') as log:
            def emit(row):
                log.write(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
                log.flush();os.fsync(log.fileno())
            for trial in plan['trials']:
                current=trial;worker=None
                emit(dict(event='trial_started',trial_id=trial['id']))
                transformed=transform_input(cases[trial['case']]['observation'],trial['variant'])
                emit(dict(event='input_prepared',trial_id=trial['id'],input_sha256=digest(transformed['observation'])))
                worker=NativeTrial(transformed['observation'],seed['config'],seed['memory'],trial['scope'],
                    plan['conditions']['max_initial_advances'],plan['conditions']['continuation_limits'],
                    event_sink=lambda row:emit(dict(event='native_action',trial_id=trial['id'],record=row)))
                native=worker.run();emit(dict(event='native_completed',trial_id=trial['id'],native_sha256=digest(native)))
                candidates=[] if native['flow'] is None else native['flow']['candidates'];compared=[]
                stage='readout_comparison'
                for ordinal,candidate in enumerate(candidates):
                    view=project(candidate);vh=digest(view);results={}
                    for policy in spec.POLICIES:
                        emit(dict(event='selection_started',trial_id=trial['id'],ordinal=ordinal,policy=policy,input_sha256=vh))
                        output=run_policy(view,policy,Limits(**plan['conditions']['selection_limits']))
                        require(digest(view)==vh,'selector가 native 입력을 수정했습니다.')
                        results[policy]=output
                        emit(dict(event='selection_completed',trial_id=trial['id'],ordinal=ordinal,policy=policy,result_sha256=digest(output)))
                    compared.append(dict(ordinal=ordinal,candidate_id=candidate['candidate_id'],candidate_sha256=digest(candidate),
                        input_sha256=vh,results=results));readouts+=1
                raw=dict(schema='hcr-exp17-trial-v1',trial=trial,transformed=transformed,memory_sha256=plan['memory_sha256'],
                         native=native,readouts=compared)
                io.put(root/'raw'/f"{trial['id']}.json",raw)
                emit(dict(event='trial_completed',trial_id=trial['id'],raw_sha256=digest(raw)))
                completed+=1;stage='native_trials'
                if completed%16==0:print(f'native trial {completed}/{len(plan["trials"])} raw 보존',flush=True)
        validate_plan(plan,source)
        names=io.inventory(root)
        io.put(root/'manifest.json',dict(schema='hcr-exp17-raw-manifest-v1',state='raw_complete',
            independent_audit_pending=True,files={n:io.file_hash(root/n) for n in sorted(names)}))
        return dict(raw_complete=True,native_trials=completed,native_readouts=readouts,
            proof_policy_evaluations=3*readouts,independent_audit_pending=True)
    except BaseException as exc:
        kind=('parsing_failure' if isinstance(exc,(json.JSONDecodeError,UnicodeError)) else
              'schema_contract_failure' if isinstance(exc,(ValueError,KeyError,TypeError)) else
              'runtime_io_failure' if isinstance(exc,OSError) else 'runtime_failure')
        failure=dict(stage=stage,trial=current,completed_trials=completed,status=kind,
            error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),automatic_retry=False)
        if worker is not None:
            try:failure['partial_evidence']=worker.partial_evidence()
            except BaseException as pe:failure['partial_capture_error']=str(pe)
        io.put(root/'failure.json',failure);raise
