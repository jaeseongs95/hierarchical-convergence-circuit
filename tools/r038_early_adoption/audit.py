"""생산 TimingTrial/OnlineTrial/run_policy를 호출하지 않는 독립 EXP19 검산."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json
import traceback
from r037_online_selection import io
from . import sources, spec, metrics
from .contracts import demand, digest, finite_nonnegative, USAGE_KEYS

VIEW_FIELDS = ('observation','raw_value','state','completed_paths','graph_complete','original_proof','min_abs_score')


def candidate_view(candidate: dict) -> dict:
    # 생산 native_bridge.project가 아닌 기존 독립 auditor의 투영이다.
    from hcr.evaluation.selection_audit import source_view
    result = source_view(candidate)
    view = {k:deepcopy(result[k]) for k in VIEW_FIELDS}
    view['schema'] = 'hcr-frozen-proof-view-r035-v1'
    return view


def check_wrapper(run: dict, trial: dict, *, view_of=candidate_view, selector_audit=None) -> dict:
    """하위 native state/controller/선택 검산은 audit_trial에서 먼저 수행한다."""
    fields = {'schema','arm','backend','base','posthoc_status','posthoc_selection',
              'posthoc_events','final','usage','wall_seconds'}
    demand(set(run) == fields and run['schema'] == 'hcr-timing-trial-r038-v1', 'EXP19 wrapper schema')
    arm = trial['arm']; base = run['base']
    mapping = {'native':'native_saved','posthoc_support':'native_saved','online_support':'support_first'}
    demand(run['arm'] == arm and arm in mapping and base['policy'] == mapping[arm] and
           base['scope'] == trial['scope'] and base['backend'] == run['backend'], '실험군/base 정책 결합')
    demand(finite_nonnegative(run['wall_seconds']), 'EXP19 wall time')
    expected_events = []
    selection_report = None
    output = run['posthoc_selection']
    status = 'not_applicable'
    if arm == 'posthoc_support':
        p = base['packet']['document']['engine']['pending']
        candidate = None
        if not base['candidates']: status = 'no_readout'
        elif p is None or not p['ready']: status = 'terminal_incomplete'
        elif p['failure_reason'] is not None: status = 'engine_failure'
        elif base['candidates'][-1]['reference']['generation'] != len(base['packet']['document']['transitions'])-1:
            status = 'stale_readout'
        else:
            candidate = base['candidates'][-1]; status = 'selected'
        if candidate is not None:
            demand(output is not None, '사후 선택 누락')
            view = view_of(candidate)
            demand(output['policy'] == 'support_first' and output['limits'] == spec.conditions()['selection_limits'],
                   '사후 선택 정책/예산 변경')
            if selector_audit is None:
                from r035_frozen_selection.audit import audit_result
                selector_audit = audit_result
            selection_report = selector_audit(view, output)
            selection_report = dict(selection_report)
            legacy_count = selection_report.pop('supported_assumptions', None)
            selection_report.update(metrics.assumption_counts(view, output['proof']))
            selection_report['legacy_field_meant_assumptions_checked'] = legacy_count
            expected_events = [
                dict(ordinal=0,event='selection_requested',readout_ordinal=len(base['candidates'])-1,
                     input_sha256=digest(view),candidate_sha256=digest(candidate),policy='support_first',after_base_stop=True),
                dict(ordinal=1,event='selection_committed',result=output)]
        else:
            demand(output is None, '현재 terminal readout 없이 사후 선택을 위조했습니다.')
    else:
        demand(output is None, '등록하지 않은 사후 selector 실행')
    demand(run['posthoc_status'] == status and run['posthoc_events'] == expected_events, '사후 경계/event 결합')
    if arm == 'posthoc_support':
        accepted = output is not None and output['accepted']
        final = dict(source='posthoc',accepted=accepted,value=output['value'] if accepted else None,
            reason='posthoc_'+output['reason'] if output is not None else 'posthoc_'+status,
            policy='support_first',readout_ordinal=len(base['candidates'])-1 if accepted else None,
            candidate_id=base['candidates'][-1]['candidate_id'] if accepted else None,
            proof_sha256=digest(output['proof']) if accepted else None)
    else:
        final = dict(source='base_online',**base['adoption'])
    expected_usage = dict(native_kernel_ticks=base['usage']['initial_kernel_ticks']+base['usage']['extra_kernel_ticks'],
        online_selection_calls=base['usage']['selection_calls'],online_selection=base['usage']['selection'],
        posthoc_selection_calls=int(output is not None),
        posthoc_selection={k:0 if output is None else output['usage'][k] for k in USAGE_KEYS})
    demand(run['final'] == final and run['usage'] == expected_usage, '최종 채택/계수 독립 재계산 불일치')
    return dict(verified=True,posthoc_status=status,posthoc_selection=selection_report,
                first_decision_preserved=True,original_native_run_preserved=True,
                no_retry_or_restart=True,terminal_readout_not_replaced_by_stale_candidate=True)


def audit_trial(run: dict, trial: dict, case: dict, seed: dict, conditions: dict) -> dict:
    from r037_online_selection.audit import audit_native, reachable
    demand(run['backend'] == 'native_hcr', '본 실험 audit에 synthetic backend 혼입')
    policy = {'native':'native_saved','posthoc_support':'native_saved','online_support':'support_first'}[trial['arm']]
    base_trial = dict(id=trial['id'],case=trial['case'],scope=trial['scope'],policy=policy)
    report, rows = audit_native(run['base'],case['observation'],seed,base_trial,conditions,case)
    wrapper = check_wrapper(run,trial)
    for index,(candidate,output) in enumerate(zip(run['base']['candidates'],run['base']['selections'])):
        view = candidate_view(candidate)
        count = metrics.frontier_at(run['base'],candidate)
        demand(view['graph_complete'] is (count == 0), 'readout graph_complete/frontier 불일치')
        row = rows[index]
        row.update(metrics.opportunity(view,candidate['readout']['accepted'],count))
        row.update(arm=trial['arm'],cohort=case['cohort'],
                   native_assumption_counts=metrics.assumption_counts(view,view['original_proof']),
                   selected_assumption_counts=metrics.assumption_counts(view,output['proof']))
        sr = report['selections'][index]
        sr['legacy_field_meant_assumptions_checked'] = sr.pop('supported_assumptions')
        sr.update(row['selected_assumption_counts'])
    final = run['final']; value = final['value']
    worlds = {name:dict(expected=reachable(case['observation'],w),external_correct=None if value is None else
                       value is reachable(case['observation'],w)) for name,w in case['worlds'].items()}
    core = run['base']['packet']['document']['engine']
    native_cost = deepcopy(core['pending']['cost'])
    demand(native_cost['kernel_ticks'] == run['usage']['native_kernel_ticks'], '최종 누적 native 비용')
    final_proof = None
    if final['accepted']:
        final_proof = (run['posthoc_selection']['proof'] if trial['arm'] == 'posthoc_support'
                       else run['base']['selections'][final['readout_ordinal']]['proof'])
    final_counts = (None if not run['base']['candidates'] else
                    metrics.assumption_counts(candidate_view(run['base']['candidates'][-1]),final_proof))
    semantic = metrics.semantic_events(run['base']['packet']['document']['events'])
    return dict(trial=trial,cohort=case['cohort'],audit=report,wrapper=wrapper,readouts=rows,
        final=final,world_results=worlds,classification=metrics.correctness(value,worlds),
        final_assumption_counts=final_counts,native_cost=native_cost,usage=run['usage'],
        native_finish_proof_nodes=sum(len(c['decision']['proof']['nodes']) for c in run['base']['candidates']),
        native_capture_scan_checks=None,unmeasured_cost_is_zero=False,
        native_event_semantic_hashes=[digest(e) for e in semantic],
        final_frontier_count=len(core['pending']['workspace']['frontier']),
        terminal_pending_ready=run['base']['terminal_pending_ready'],
        base_stop_reason=run['base']['adoption']['reason'])


def verify_raw(path) -> tuple:
    from .protocol import validate_plan
    from r036_input_representation.audit import check_seed
    from .reporting import summarize
    root = io.safe(path)
    plan = io.load(root/'plan.json'); validate_plan(plan,check_parent=False)
    manifest = io.load(root/'manifest.json')
    demand(set(manifest) == {'schema','state','independent_audit_pending','files'} and
           manifest['schema'] == 'hcr-exp19-raw-manifest-v1' and manifest['state'] == 'raw_complete' and
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
    cases,seed = sources.validate_parent_documents(documents,hashes)
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
            demand(set(raw) == {'schema','trial','run'} and raw['schema'] == 'hcr-exp19-raw-trial-v1' and
                   raw['trial'] == trial, 'raw trial 바인딩')
            run = raw['run']
            record = audit_trial(run,trial,byname[trial['case']],seed,plan['conditions'])
            take(dict(event='trial_started',trial=trial))
            for event in run['base']['events']:
                take(dict(event='trial_action',trial_id=tid,record=dict(event='native_action',record=event)))
            take(dict(event='trial_action',trial_id=tid,record=dict(event='base_completed',base_sha256=digest(run['base']))))
            for event in run['posthoc_events']:
                take(dict(event='trial_action',trial_id=tid,record=dict(event='posthoc_action',record=event)))
            take(dict(event='trial_action',trial_id=tid,record=dict(event='arm_finished',final=run['final'])))
            take(dict(event='trial_completed',trial_id=tid,raw_sha256=digest(raw)))
            record['raw_sha256'] = digest(raw); records[tid] = record
        demand(stream.read() == '', '미등록 trial/retry/tail stream')
    summary = summarize(list(records.values()))
    audit = dict(schema='hcr-exp19-audit-v1',verified=True,raw_manifest_sha256=io.file_hash(root/'manifest.json'),
        native_trials=len(records),native_readouts=sum(len(r['readouts']) for r in records.values()),
        stream_records=stream_count,seed_training=seed_report,native_state_and_control_replayed=True,
        proof_DAG_and_posthoc_boundary_checked=True,assumption_counts_corrected=True,
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
                 'trials.csv':trial_csv(summary['trials'])}
        if check_only:
            manifest = io.load(target/'manifest.json')
            demand(manifest['schema'] == 'hcr-exp19-analysis-manifest-v1' and
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
            io.put(target/'manifest.json',dict(schema='hcr-exp19-analysis-manifest-v1',
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
