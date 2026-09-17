"""조건 동결, 단회 native 실행, append-only 증거 보존. audit는 별도 명령이다."""
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
import platform
import subprocess
import sys
import traceback
from r037_online_selection import io
from . import sources, spec, input_audit
from .contracts import Budget, digest, require
from .runtime import ScheduledTimingTrial

PLAN_KEYS = {'schema','created_at_utc','source_run','conditions','cases','evaluation_worlds','trials',
             'parent_file_hashes','canonical_parent_case','memory_sha256','config_sha256','dependency_source_hashes','addon_source_hashes'}


def make_plan(source_run) -> dict:
    root, cases, core, hashes, base = sources.read_parent(source_run)
    return dict(schema='hcr-exp22-plan-v1', created_at_utc=datetime.now(timezone.utc).isoformat(),
        source_run=str(root), conditions=spec.conditions(), cases=spec.public_cases(cases),
        evaluation_worlds={c['name']:c['worlds'] for c in cases}, trials=spec.trials(cases),
        parent_file_hashes=hashes, canonical_parent_case=base, memory_sha256=digest(core['memory']), config_sha256=digest(core['config']),
        dependency_source_hashes=sources.dependencies(), addon_source_hashes=sources.addon_hashes())


def validate_plan(plan: dict, source_run=None, *, check_parent=True):
    require(set(plan) == PLAN_KEYS and plan['schema'] == 'hcr-exp22-plan-v1', 'EXP22 plan schema')
    require(digest(plan['conditions']) == digest(spec.conditions()) and plan['trials'] == spec.trials(plan['cases']) and
            len(plan['cases']) == 6 and len(plan['trials']) == 108, 'EXP22 동결 조건/population 변경')
    require(set(plan['parent_file_hashes']) == set(sources.PARENT_FILES), 'EXP21 출처 inventory 변경')
    input_audit.check_cases(plan['cases'],plan['evaluation_worlds'],plan['canonical_parent_case'])
    input_audit.check_trial_schedule(plan['trials'])
    require(plan['dependency_source_hashes'] == sources.dependencies() and
            plan['addon_source_hashes'] == sources.addon_hashes(), '동결 이후 소스 변경')
    if check_parent:
        root, cases, core, hashes, base = sources.read_parent(source_run or plan['source_run'])
        require(plan['canonical_parent_case'] == base and plan['parent_file_hashes'] == hashes and plan['cases'] == spec.public_cases(cases) and
                plan['evaluation_worlds'] == {c['name']:c['worlds'] for c in cases} and
                plan['memory_sha256'] == digest(core['memory']) and plan['config_sha256'] == digest(core['config']),
                '동결 이후 입력/학습 출처 변경')
        return root
    return None


def prepare(source_run, out) -> dict:
    root, target = io.safe(source_run), io.safe(out)
    io.disjoint(root, target)
    require(not target.exists(), '기존 plan을 덮어쓰지 않습니다.')
    plan = make_plan(root)
    io.put(target, plan)
    return dict(plan=str(target), plan_sha256=digest(plan), base_topologies=1, order_variants=6, native_trials=108, automatic_retry=False)


def failure_kind(exc: BaseException) -> str:
    if isinstance(exc, KeyboardInterrupt): return 'interrupted'
    if isinstance(exc, (json.JSONDecodeError, UnicodeError)): return 'parsing_failure'
    if isinstance(exc, ImportError): return 'dependency_failure'
    if isinstance(exc, (ValueError, KeyError, TypeError)): return 'schema_contract_failure'
    if isinstance(exc, OSError): return 'runtime_io_failure'
    return 'runtime_failure'


def execute(plan: dict, out, source_run=None) -> dict:
    source = validate_plan(plan, source_run)
    root = io.safe(out)
    io.disjoint(source, root)
    root.mkdir(parents=True, exist_ok=False)
    stage = 'copy_sources'; current = None; worker = None; completed = 0
    try:
        io.put(root/'plan.json', plan)
        try:
            head = subprocess.run(['git','-C',str(sources.repo_root()),'rev-parse','HEAD'],
                capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            head = None
        io.put(root/'environment.json', dict(python=sys.version, platform=platform.platform(),
            repository_head=head, basis_commit=spec.BASE_COMMIT, mode='native_experiment',
            external_llm_used=False, synthetic_backend=False, automatic_retry=False, source_run_used=str(source)))
        for name, h in (plan['dependency_source_hashes'] | plan['addon_source_hashes']).items():
            data = io.read(io.child(sources.repo_root(),name))
            require(io.bytes_hash(data.replace(b'\r\n',b'\n')) == h, '복사 중 소스 변경: '+name)
            io.write_bytes(io.child(root,'source/'+name),data)
        for name,h in plan['parent_file_hashes'].items():
            data = io.read(io.child(source,name))
            require(io.bytes_hash(data) == h, '복사 중 EXP21 입력 변경: '+name)
            io.write_bytes(io.child(root,sources.capsule_name(name)),data)
        seed = io.load(root/'upstream/seed/6.json')['document']['engine']
        cases = {c['name']:c for c in plan['cases']}
        stage = 'native_trials'
        with (root/'attempts.jsonl').open('x',encoding='utf-8',newline='\n') as stream:
            def emit(event):
                stream.write(json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
                stream.flush(); os.fsync(stream.fileno())
            for trial in plan['trials']:
                current = trial; worker = None
                emit(dict(event='trial_started',trial=trial))
                # 공개 관측만 넘긴다. evaluation_worlds/case/cohort/manipulation을 runtime에 전달하지 않는다.
                worker = ScheduledTimingTrial(cases[trial['case']]['observation'],seed['config'],seed['memory'],
                    trial['scope'],trial['arm'],Budget(**plan['conditions']['budget']),scheduler=trial['scheduler'],
                    event_sink=lambda e:emit(dict(event='trial_action',trial_id=trial['id'],record=e)))
                run = worker.run()
                require(run['backend'] == run['base']['backend'] == 'native_hcr', '합성 backend가 본 실험에 혼입됐습니다.')
                raw = dict(schema='hcr-exp22-raw-trial-v1',trial=trial,run=run)
                io.put(root/'raw'/f"{trial['id']}.json",raw)
                emit(dict(event='trial_completed',trial_id=trial['id'],raw_sha256=digest(raw)))
                completed += 1
                print(f'EXP-22 native trial {completed}/108 원문 보존',flush=True)
        validate_plan(plan,source)
        io.put(root/'manifest.json',dict(schema='hcr-exp22-raw-manifest-v1',state='raw_complete',
            independent_audit_pending=True,files={n:io.file_hash(root/n) for n in sorted(io.inventory(root))}))
        return dict(raw_complete=True,native_trials=completed,independent_audit_pending=True)
    except BaseException as exc:
        failure = dict(status=failure_kind(exc),stage=stage,trial=current,completed_trials=completed,
            error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),automatic_retry=False)
        if worker is not None:
            try: failure['partial_evidence'] = worker.partial_evidence()
            except BaseException as partial: failure['partial_capture_error'] = repr(partial)
        try: io.write_failure(root,failure)
        except OSError as write_error: print('failure.json 저장 실패: '+str(write_error),file=sys.stderr)
        raise
