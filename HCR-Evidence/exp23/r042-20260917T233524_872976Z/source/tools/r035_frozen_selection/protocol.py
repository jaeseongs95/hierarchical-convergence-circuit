"""EXP-16 조건 동결/생성. 생성기는 정답률이나 독립 audit 결과를 작성하지 않는다."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys
import subprocess
import traceback
from . import storage as io
from .contracts import Limits, digest, require
from . import spec, upstream
from .selection import run_policy
from .transforms import transform


def code_hashes():
    root = upstream.repo_root()
    names = {p.relative_to(root).as_posix() for p in Path(__file__).parent.rglob('*.py')}
    names |= {'Run-HCR-R035.py', 'scripts/r035_cli.py', 'scripts/verify_r035.py',
              'tools/r035_frozen_selection/native_baseline.json', 'R035_MANIFEST.json'}
    return {name: io.text_hash(io.child(root, name)) for name in sorted(names)}


def metadata(snapshot):
    return {k:deepcopy(v) for k,v in snapshot.items() if k not in ('input', 'native_readout')} | {'input_sha256':digest(snapshot['input'])}


def make_plan(source_run):
    registry = upstream.check_native()
    root, m, source_plan = upstream.source_identity(source_run)
    require(source_plan['source_hashes'] == registry['files'], 'EXP-15 원 실행 소스와 기준선 불일치')
    population = upstream.select_population(root); saved = upstream.snapshots(population)
    require(saved, '사용 가능한 native snapshot이 없습니다.')
    return dict(schema='hcr-exp16-plan-v1', conditions=spec.conditions(),
        created_at_utc=datetime.now(timezone.utc).isoformat(), source_run=str(root),
        upstream_manifest_sha256=io.file_hash(root/'manifest.json'),
        upstream_plan_sha256=io.file_hash(root/'plan.json'), native_source_hashes=source_plan['source_hashes'],
        addon_source_hashes=code_hashes(), snapshots=[metadata(s) for s in saved])


def validate_plan(plan, source_run=None):
    fields = {'schema', 'conditions', 'created_at_utc', 'source_run', 'upstream_manifest_sha256',
        'upstream_plan_sha256', 'native_source_hashes', 'addon_source_hashes', 'snapshots'}
    require(set(plan) == fields and plan['schema'] == 'hcr-exp16-plan-v1', 'EXP-16 plan schema')
    require(plan['conditions'] == spec.conditions(), '조건 동결 이후 실험 정의 변경')
    require(plan['addon_source_hashes'] == code_hashes(), '조건 동결 이후 EXP-16 소스 변경')
    reg = upstream.check_native()
    require(plan['native_source_hashes'] == reg['files'], 'EXP-15/현재 native 소스 불일치')
    root = io.safe(source_run or plan['source_run'])
    require(io.file_hash(root/'manifest.json') == plan['upstream_manifest_sha256']
        and io.file_hash(root/'plan.json') == plan['upstream_plan_sha256'], 'EXP-15 원자료 기준 변경')
    return root


def prepare(source_run, out):
    out = io.safe(out)
    require(not out.exists(), '기존 계획은 덮어쓰지 않습니다.')
    source = io.safe(source_run)
    require(out != source and source not in out.parents, '계획 파일을 EXP-15 source 안에 쓰지 않습니다.')
    plan = make_plan(source_run); io.put(out, plan)
    return dict(plan=str(out), snapshots=len(plan['snapshots']),
                planned_conditions=len(spec.cells([s['id'] for s in plan['snapshots']])), source_verified_by_native_auditor=False)


def generate(plan, out, source_run=None):
    source = validate_plan(plan, source_run); root = io.safe(out)
    require(root != source and source not in root.parents and root not in source.parents, 'source와 output은 분리된 폴더여야 합니다.')
    root.mkdir(parents=True, exist_ok=False)
    completed = 0; stage = 'source'; current = None
    try:
        io.put(root/'plan.json', plan)
        try:
            cp = subprocess.run(['git','-C',str(upstream.repo_root()),'rev-parse','HEAD'],capture_output=True,text=True,timeout=10,check=True)
            head = cp.stdout.strip()
        except (OSError,subprocess.SubprocessError):
            head = None
        io.put(root/'environment.json', dict(python=sys.version, platform=platform.platform(),repository_head=head,
            source_run_used=str(source), external_llm_used=False, native_kernel_executed=False,
            reuses_previous_exp15_states=True, automatic_retry=False))
        for name,h in plan['addon_source_hashes'].items():
            data = io.read(io.child(upstream.repo_root(), name))
            require(io.sha_bytes(data.replace(b'\r\n',b'\n')) == h, '소스 snapshot 변화: '+name)
            io.put_bytes(io.child(root,'source/'+name), data)
        io.put_bytes(root/'upstream/manifest.json', io.read(source/'manifest.json'))
        io.put_bytes(root/'upstream/plan.json', io.read(source/'plan.json'))
        population = upstream.select_population(source); saved = upstream.snapshots(population)
        require([metadata(s) for s in saved] == plan['snapshots'], '조건 동결 이후 snapshot 변화')
        for item in population:
            io.put_bytes(io.child(root,'upstream/'+item['path']), item['raw_bytes'])
            io.put_bytes(io.child(root,'upstream/'+item['baseline_path']), item['baseline_bytes'])
        for s in saved: io.put(root/'snapshots'/f"{s['id']}.json",s)
        byid = {s['id']:s for s in saved}; stage = 'selection'
        with (root/'attempts.jsonl').open('x',encoding='utf-8',newline='\n') as log:
            def emit(record):
                log.write(json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
                log.flush(); os.fsync(log.fileno())
            for cell in spec.cells(list(byid)):
                current = cell
                s = byid[cell['snapshot_id']]; source_hash = digest(s)
                emit(dict(event='attempt_started',cell_id=cell['id'],snapshot_id=s['id'],snapshot_sha256=source_hash))
                transformed = transform(s['input'],cell['variant'])
                result = run_policy(transformed['input'],cell['policy'],Limits(**cell['limits']))
                require(source_hash == digest(s), '원 snapshot 수정')
                raw = dict(cell=cell,snapshot_sha256=source_hash,transformed=transformed,result=result)
                io.put(root/'raw'/f"{cell['id']}.json",raw)
                emit(dict(event='attempt_completed',cell_id=cell['id'],raw_sha256=digest(raw)))
                completed += 1
                if completed % 100 == 0: print(f'선택 조건 {completed}개 raw 보존',flush=True)
        names = io.inventory(root)
        io.put(root/'manifest.json',dict(schema='hcr-exp16-raw-manifest-v1',state='raw_complete',
            independent_audit_pending=True,files={n:io.file_hash(root/n) for n in sorted(names)}))
        return dict(raw_complete=True, snapshots=len(saved), conditions=completed, independent_audit_pending=True,
                    new_native_kernel_ticks=0, source=str(source))
    except BaseException as exc:
        kind = ('parsing_failure' if isinstance(exc,(json.JSONDecodeError,UnicodeError)) else
                'schema_contract_failure' if isinstance(exc,(ValueError,KeyError,TypeError)) else
                'runtime_io_failure' if isinstance(exc,OSError) else 'runtime_failure')
        io.put(root/'failure.json',dict(stage=stage,cell=current,completed_conditions=completed,
            status=kind,error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),automatic_retry=False))
        raise
