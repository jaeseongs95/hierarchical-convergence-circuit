"""EXP21 독립 입력/상태/proof/제어 검산. 생산 실행 함수를 호출하지 않는다.
R038 audit_trial은 검증된 native/event 및 R035 proof 검산을 그대로 재사용한다.
"""
from datetime import datetime, timezone
import json
import traceback
from r037_online_selection import io
from .trial_audit import audit_trial
from . import sources, spec, input_audit
from r039_order_isolation import trajectory
from .baseline_audit import compare_parent
from .contracts import demand, digest

def verify_raw(path) -> tuple:
    from .protocol import validate_plan
    from r036_input_representation.audit import check_seed
    from .reporting import summarize
    root = io.safe(path)
    plan = io.load(root/'plan.json'); validate_plan(plan,check_parent=False)
    manifest = io.load(root/'manifest.json')
    demand(set(manifest) == {'schema','state','independent_audit_pending','files'} and
           manifest['schema'] == 'hcr-exp21-raw-manifest-v1' and manifest['state'] == 'raw_complete' and
           manifest['independent_audit_pending'] is True, '완료 raw manifest 계약')
    all_sources = plan['dependency_source_hashes'] | plan['addon_source_hashes']
    expected = {'plan.json','environment.json','attempts.jsonl'}
    expected |= {sources.capsule_name(n) for n in sources.PARENT_FILES}
    expected |= {'source/'+n for n in all_sources}
    expected |= {'raw/'+t['id']+'.json' for t in plan['trials']}
    actual = {n for n in io.inventory(root) if not n.startswith(('analysis/','audit_failures/'))}
    demand(set(manifest['files']) == expected and actual == expected | {'manifest.json'}, 'raw inventory/population')
    for name,h in manifest['files'].items():
        demand(io.file_hash(io.child(root,name)) == h, 'raw checksum: '+name)
    for name,h in all_sources.items():
        demand(io.text_hash(io.child(root,'source/'+name)) == h, '보존된 실행 소스 변경: '+name)
    hashes = {n:io.file_hash(root/sources.capsule_name(n)) for n in sources.PARENT_FILES}
    demand(hashes == plan['parent_file_hashes'], 'parent 복사 계보')
    documents = {n:io.load(root/sources.capsule_name(n)) for n in sources.PARENT_FILES}
    cases,seed,base = sources.validate_parent_documents(documents,hashes)
    input_report=input_audit.check_cases(plan['cases'],plan['evaluation_worlds'],base)
    input_audit.check_trial_schedule(plan['trials'])
    demand(spec.public_cases(cases) == plan['cases'] and
           {c['name']:c['worlds'] for c in cases} == plan['evaluation_worlds'], 'case/world 변조')
    demand(digest(seed['memory']) == plan['memory_sha256'] and digest(seed['config']) == plan['config_sha256'], 'seed hash')
    checked_seed, _, seed_report = check_seed(root,plan)
    demand(checked_seed == seed, '독립 학습 재생과 seed 불일치')
    environment = io.load(root/'environment.json')
    demand(environment['mode'] == 'native_experiment' and environment['synthetic_backend'] is False and
           environment['automatic_retry'] is False and environment['external_llm_used'] is False, 'native 환경 선언')
    byname = {c['name']:c for c in cases}; records = {}; stream_count = 0
    # 긴 원문 stream을 메모리에 한꺼번에 올리지 않는다. 각 기록은 raw와 다시 결합한다.
    with (root/'attempts.jsonl').open(encoding='utf-8') as stream:
        def take(expected_row):
            nonlocal stream_count
            line = stream.readline(); demand(bool(line),'attempt stream 조기 종료')
            demand(digest(io.loads(line)) == digest(expected_row), f'attempt stream 불일치: {stream_count}')
            stream_count += 1
        for trial in plan['trials']:
            tid = trial['id']; raw = io.load(root/'raw'/f'{tid}.json')
            demand(set(raw) == {'schema','trial','run'} and raw['schema'] == 'hcr-exp21-raw-trial-v1' and
                   raw['trial'] == trial, 'raw trial 바인딩')
            run = raw['run']
            record = audit_trial(run,trial,byname[trial['case']],seed,plan['conditions'])
            record['order_diagnostics']=trajectory.describe(run,record,byname[trial['case']])
            take(dict(event='trial_started',trial=trial))
            for event in run['base']['events']:
                take(dict(event='trial_action',trial_id=tid,record=dict(event='native_action',record=event)))
            take(dict(event='trial_action',trial_id=tid,record=dict(event='base_completed',base_sha256=digest(run['base']))))
            for event in run['posthoc_events']:
                take(dict(event='trial_action',trial_id=tid,record=dict(event='posthoc_action',record=event)))
            take(dict(event='trial_action',trial_id=tid,record=dict(event='arm_finished',final=run['final'])))
            take(dict(event='trial_completed',trial_id=tid,raw_sha256=digest(raw)))
            if trial['scheduler']=='input_order':
                parent_plan=documents['plan.json']
                target=next(t for t in parent_plan['trials'] if all(t[k]==trial[k] for k in ('case','scope','arm')))
                record['parent_regression']=compare_parent(run,documents['raw/'+target['id']+'.json'])
            else: record['parent_regression']=None
            record['raw_sha256'] = digest(raw); records[tid] = record
        demand(stream.read() == '', '미등록 trial/retry/tail stream')
    summary = summarize(list(records.values()))
    summary['input_isolation']=input_report
    audit = dict(schema='hcr-exp21-audit-v1',verified=True,raw_manifest_sha256=io.file_hash(root/'manifest.json'),
        native_trials=len(records),native_readouts=sum(len(r['readouts']) for r in records.values()),
        stream_records=stream_count,seed_training=seed_report,native_state_and_control_replayed=True,
        proof_DAG_and_posthoc_boundary_checked=True,assumption_counts_corrected=True,
        fixed_identity_input_isolation_checked=True,order_effect_required=False,
        scheduling_decisions_and_costs_independently_checked=True,priority_only_state_change_checked=True,
        parent_raw_regression_checked=36,scheduler_gap_reduction_required=False,
        opportunity_or_improvement_required=False,correctness_required=False)
    return summary,audit,records


def write_analysis(path, *, check_only=False) -> dict:
    root = io.safe(path)
    try:
        from .reporting import render, csv_text, trial_csv
        summary,audit,records = verify_raw(root)
        target = root/'analysis'
        objects = {'summary.json':summary,'audit.json':audit} | {'records/'+k+'.json':v for k,v in records.items()}
        texts = {'summary.ko.md':render(summary),'paired.csv':csv_text(summary['paired']),
                 'trials.csv':trial_csv(summary['trials']),
                 'scheduler_contrasts.csv':csv_text(summary['scheduler_contrasts']),
                 'mediation.csv':csv_text(summary['mediation']),
                 'scheduler_decisions.csv':csv_text(summary['scheduler_decisions']),
                 'order_effects.csv':csv_text(summary['order_effects']),
                 'readouts.csv':csv_text(summary['readout_rows'])}
        if check_only:
            manifest = io.load(target/'manifest.json')
            demand(manifest['schema'] == 'hcr-exp21-analysis-manifest-v1' and
                   manifest['raw_manifest_sha256'] == audit['raw_manifest_sha256'], 'analysis 계보')
            demand(set(manifest['files']) == set(objects)|set(texts) and
                   io.inventory(target) == set(objects)|set(texts)|{'manifest.json'}, 'analysis inventory')
            for n,v in objects.items(): demand(io.load(target/n) == v,'독립 재계산: '+n)
            for n,v in texts.items(): demand(io.read(target/n).decode('utf-8') == v,'보고서 재계산: '+n)
            for n,h in manifest['files'].items(): demand(io.file_hash(target/n) == h,'analysis checksum: '+n)
        else:
            target.mkdir(parents=True,exist_ok=False)
            for n,v in objects.items(): io.put(target/n,v)
            for n,v in texts.items(): io.write_bytes(target/n,v.encode('utf-8'))
            io.put(target/'manifest.json',dict(schema='hcr-exp21-analysis-manifest-v1',
                raw_manifest_sha256=audit['raw_manifest_sha256'],
                files={n:io.file_hash(target/n) for n in sorted(set(objects)|set(texts))}))
        return audit
    except BaseException as exc:
        kind = ('interrupted' if isinstance(exc,KeyboardInterrupt) else
                'parsing_failure' if isinstance(exc,(json.JSONDecodeError,UnicodeError)) else
                'dependency_failure' if isinstance(exc,ImportError) else
                'runtime_io_failure' if isinstance(exc,OSError) else 'evaluator_disagreement')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        try:
            io.put(root/'audit_failures'/f'{stamp}.json',dict(status=kind,error=str(exc),
                error_type=type(exc).__name__,traceback=traceback.format_exc(),automatic_retry=False))
        except OSError: pass
        raise
