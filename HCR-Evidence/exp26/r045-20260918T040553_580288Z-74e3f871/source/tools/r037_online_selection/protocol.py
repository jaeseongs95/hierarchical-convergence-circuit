"""조건 동결 → 단회 실행 → 원문 보존. evaluator는 별도 프로세스의 audit 명령에서만 실행한다."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import platform
import subprocess
import sys
import traceback
from . import io, sources, spec
from .contracts import Budget, digest, require
from .runtime import OnlineTrial


def make_plan(source_run) -> dict:
    source, cases, core, parent_hashes = sources.read_parent(source_run)
    return dict(schema='hcr-exp18-plan-v1', created_at_utc=datetime.now(timezone.utc).isoformat(),
                source_run=str(source), conditions=spec.conditions(), cases=cases, trials=spec.trials(cases),
                parent_file_hashes=parent_hashes,
                upstream_file_hashes={n:parent_hashes['upstream/'+n] for n in sources.UPSTREAM_FILES},
                memory_sha256=digest(core['memory']), config_sha256=digest(core['config']),
                dependency_source_hashes=sources.dependencies(), addon_source_hashes=sources.code_hashes())


def validate_plan(plan: dict, source_run=None, *, check_parent=True):
    fields = {'schema', 'created_at_utc', 'source_run', 'conditions', 'cases', 'trials',
              'parent_file_hashes', 'upstream_file_hashes', 'memory_sha256', 'config_sha256',
              'dependency_source_hashes', 'addon_source_hashes'}
    require(set(plan) == fields and plan['schema'] == 'hcr-exp18-plan-v1', 'EXP-18 plan schema')
    require(plan['conditions'] == spec.conditions() and plan['trials'] == spec.trials(plan['cases']),
            '조건 동결 이후 실험 설계 변경')
    require(tuple(c['name'] for c in plan['cases']) == spec.CASE_NAMES and len(plan['trials']) == 32,
            '32개 paired trial population')
    require(plan['dependency_source_hashes'] == sources.dependencies() and
            plan['addon_source_hashes'] == sources.code_hashes(), '동결 이후 소스 변경')
    require(set(plan['parent_file_hashes']) == set(sources.PARENT_FILES) and
            plan['upstream_file_hashes'] == {n:plan['parent_file_hashes']['upstream/'+n] for n in sources.UPSTREAM_FILES},
            '출처 inventory')
    if check_parent:
        root, cases, core, hashes = sources.read_parent(source_run or plan['source_run'])
        require(hashes == plan['parent_file_hashes'] and cases == plan['cases'] and
                digest(core['memory']) == plan['memory_sha256'] and digest(core['config']) == plan['config_sha256'],
                '동결 이후 입력/학습 출처 변경')
        return root
    return None


def prepare(source_run, out) -> dict:
    source, target = io.safe(source_run), io.safe(out)
    require(not target.exists(), '기존 계획은 덮어쓰지 않습니다.')
    require(source not in target.parents, 'EXP-17 원자료 내부에 계획을 쓰지 않습니다.')
    plan = make_plan(source)
    io.put(target, plan)
    return dict(plan=str(target), plan_sha256=digest(plan), native_trials=32,
                base_cases=8, new_training=False, automatic_retry=False)


def execute(plan: dict, out, source_run=None) -> dict:
    source = validate_plan(plan, source_run); root = io.safe(out)
    io.disjoint(source, root); root.mkdir(parents=True, exist_ok=False)
    stage = 'copy_sources'; current = None; worker = None; completed = 0
    try:
        io.put(root/'plan.json', plan)
        try:
            head = subprocess.run(['git', '-C', str(sources.repo_root()), 'rev-parse', 'HEAD'],
                capture_output=True, text=True, timeout=10, check=True).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            head = None
        io.put(root/'environment.json', dict(python=sys.version, platform=platform.platform(), repository_head=head,
            code_basis=spec.BASE_COMMIT, mode='native_experiment', external_llm_used=False,
            automatic_retry=False, synthetic_backend=False, source_run_used=str(source)))
        for name, h in (plan['dependency_source_hashes'] | plan['addon_source_hashes']).items():
            data = io.read(io.child(sources.repo_root(), name))
            require(io.bytes_hash(data.replace(b'\r\n', b'\n')) == h, '복사 도중 소스 변경: '+name)
            io.write_bytes(io.child(root, 'source/'+name), data)
        for name, h in plan['parent_file_hashes'].items():
            data = io.read(io.child(source, name)); require(io.bytes_hash(data) == h, 'EXP-17 source 변경')
            destination = name if name.startswith('upstream/') else 'basis/exp17/'+name
            io.write_bytes(io.child(root, destination), data)
        seed = io.load(root/'upstream/seed/6.json')['document']['engine']
        cases = {c['name']:c for c in plan['cases']}
        stage = 'native_trials'
        with (root/'attempts.jsonl').open('x', encoding='utf-8', newline='\n') as stream:
            def emit(row):
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                        separators=(',', ':'), allow_nan=False)+'\n')
                stream.flush(); os.fsync(stream.fileno())
            for trial in plan['trials']:
                current = trial; worker = None
                emit(dict(event='trial_started', trial_id=trial['id']))
                # case/world/정답을 넘기지 않는다. 각 policy는 fresh native session을 실행한다.
                worker = OnlineTrial(cases[trial['case']]['observation'], seed['config'], seed['memory'],
                    trial['scope'], trial['policy'], Budget(**plan['conditions']['budget']),
                    event_sink=lambda e:emit(dict(event='online_action', trial_id=trial['id'], record=e)))
                flow = worker.run()
                require(flow['backend'] == 'native_hcr', '실험 경로에 synthetic backend 혼입')
                raw = dict(schema='hcr-exp18-raw-trial-v1', trial=trial, run=flow)
                io.put(root/'raw'/f"{trial['id']}.json", raw)
                emit(dict(event='trial_completed', trial_id=trial['id'], raw_sha256=digest(raw)))
                completed += 1
                print(f'EXP-18 native trial {completed}/32 원문 보존', flush=True)
        validate_plan(plan, source)
        names = io.inventory(root)
        io.put(root/'manifest.json', dict(schema='hcr-exp18-raw-manifest-v1', state='raw_complete',
            independent_audit_pending=True, files={n:io.file_hash(root/n) for n in sorted(names)}))
        return dict(raw_complete=True, native_trials=completed, independent_audit_pending=True)
    except BaseException as exc:
        kind = ('interrupted' if isinstance(exc, KeyboardInterrupt) else
                'parsing_failure' if isinstance(exc, (json.JSONDecodeError, UnicodeError)) else
                'schema_contract_failure' if isinstance(exc, (ValueError, KeyError, TypeError)) else
                'runtime_io_failure' if isinstance(exc, OSError) else 'runtime_failure')
        failure = dict(stage=stage, trial=current, completed_trials=completed, status=kind,
                       error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc(),
                       automatic_retry=False)
        if worker is not None:
            try:
                failure['partial_evidence'] = worker.partial_evidence()
            except BaseException as partial_exc:
                failure['partial_capture_error'] = repr(partial_exc)
        try:
            io.write_failure(root, failure)
        except OSError as failure_write:
            print('failure.json 기록 실패: '+str(failure_write), file=sys.stderr)
        raise
