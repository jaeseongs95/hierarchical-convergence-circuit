"""native 상태/원 proof/온라인 adoption을 독립 검산한다. 생산 OnlineTrial/run_policy 호출 없음."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import traceback
import json
from . import io, sources, spec
from .contracts import demand, digest
from .control_audit import audit_control

VIEW_FIELDS = ('observation', 'raw_value', 'state', 'completed_paths',
               'graph_complete', 'original_proof', 'min_abs_score')


def reachable(obs, truth) -> bool:
    """독립 평가용 reachability. 이 함수나 truth는 온라인 실행기에 전달되지 않는다."""
    seen = {obs['start']}
    changed = True
    while changed:
        changed = False
        for e in obs['edges']:
            if truth[e['id']] and e['source'] in seen and e['target'] not in seen:
                seen.add(e['target']); changed = True
    return obs['goal'] in seen


def information(view) -> dict:
    obs = view['observation']; threshold = view['min_abs_score']
    positive = {e['id']:e['score'] is not None and e['score'] > threshold for e in obs['edges']}
    possible = {e['id']:not(e['score'] is not None and e['score'] < -threshold) for e in obs['edges']}
    yes, maybe = reachable(obs, positive), reachable(obs, possible)
    return dict(identifiable=yes or not maybe, value=True if yes else False if not maybe else None,
                positive_support_path_exists=yes, possible_positive_path_exists=maybe)


def audit_native(run: dict, observation: dict, seed: dict, trial: dict, conditions: dict, case: dict) -> tuple:
    from hcr.prior_policy import read_scope
    from hcr.evaluation.review_audit import packet_states, verify_candidate
    from hcr.evaluation.selection_audit import source_view
    from r035_frozen_selection.audit import audit_result, view_check
    demand(run['backend'] == 'native_hcr' and run['scope'] == trial['scope'] and run['policy'] == trial['policy'],
           'native 실행 조건/종류')
    demand(run['budget'] == conditions['budget'], '사전 동결 계산 예산')
    packet = run['packet']; states, native_report = packet_states(packet)
    for c in states.values():
        demand(c['memory'] == seed['memory'] and c['config'] == seed['config'], '동결 memory/config 변경')
        demand(read_scope(c) == trial['scope'] and
               c['switches'] == dict(use_circuits=True, top_down=True, allow_reexpansion=True), 'prior/switches 변경')
        demand(not c['held'] and not c['feedback'] and not c['requests'], '학습/관측/native finish 덮어쓰기')
        if c['pending'] is not None:
            demand(c['pending']['observation'] == observation and c['pending']['mode'] == 'frozen_eval', '입력 provenance')
    demand(run['memory_sha256'] == digest(seed['memory']) and run['config_sha256'] == digest(seed['config']) and
           run['observation_sha256'] == digest(observation), 'trial 입력 hash')
    rows = []; selection_reports = []; candidate_reports = []
    demand(len(run['candidates']) == len(run['selections']), '선택 누락')
    for ordinal, (candidate, output) in enumerate(zip(run['candidates'], run['selections'])):
        demand(candidate['reference']['segment'] == 0, '다중 session 숨김')
        candidate_reports.append(verify_candidate(candidate, packet, states))
        raw = source_view(candidate)
        view = {k:deepcopy(raw[k]) for k in VIEW_FIELDS}; view['schema'] = 'hcr-frozen-proof-view-r035-v1'
        view_check(view)
        demand(output['limits'] == conditions['selection_limits'] and output['policy'] == trial['policy'], '선택 정책/예산')
        report = audit_result(view, output); selection_reports.append(report)
        if trial['policy'] == 'native_saved':
            demand(output['proof'] == view['original_proof'] and
                   output['accepted'] is candidate['readout']['accepted'] and
                   output['value'] is candidate['readout']['value'], 'native 저장 proof/gate 기준선 불일치')
        info = information(view)
        supported = [i for i,p in enumerate(view['completed_paths']) if
                     all(view['observation']['edges'][s]['score'] is not None and
                         view['observation']['edges'][s]['score'] > view['min_abs_score'] for s in p)]
        active = [i for i in supported if all(view['state'][f'e:{s}'] >= .5 for s in view['completed_paths'][i])]
        world_results = {name:dict(expected=reachable(observation, world),
                                  external_correct=None if output['value'] is None else
                                  output['value'] is reachable(observation, world))
                         for name, world in case['worlds'].items()}
        native_correct = {name:None if candidate['readout']['value'] is None else
                          candidate['readout']['value'] is result['expected'] for name,result in world_results.items()}
        rows.append(dict(trial_id=trial['id'], case=trial['case'], scope=trial['scope'], policy=trial['policy'],
            ordinal=ordinal, first_readout=ordinal == 0, last_available_readout=ordinal == len(run['candidates'])-1,
            native_view_sha256=digest(view), raw_value=view['raw_value'],
            native_accepted=candidate['readout']['accepted'], native_value=candidate['readout']['value'],
            policy_accepted=output['accepted'], policy_value=output['value'], policy_reason=output['reason'],
            D_DAG=report['D_DAG'], native_D_DAG=candidate['decision']['proof']['primitive_depth'],
            selected_assumptions=None if output['proof'] is None else output['proof']['assumed_edges'],
            native_assumptions=candidate['decision']['proof']['assumed_edges'],
            selected_path_index=output['selected_path_index'],
            completed_paths=view['completed_paths'], graph_complete=view['graph_complete'],
            supported_completed=supported, activation_eligible_supported=active, information=info,
            raw_conflicts_with_identified_value=info['identifiable'] and view['raw_value'] is not None and
                                               view['raw_value'] is not info['value'],
            recovered_same_value_output=not candidate['readout']['accepted'] and output['accepted'],
            kernel_ticks_at_readout=candidate['decision']['cost']['kernel_ticks'],
            native_proof_nodes=len(candidate['decision']['proof']['nodes']),
            convergence=candidate['decision'].get('convergence'), selection_usage=output['usage'],
            world_results=world_results, native_external_correct=native_correct))
    control_report = audit_control(run, states)
    # terminal packet 검산 비용/시간은 온라인 task 비용에 합산하지 않는다.
    final_truth = {name:dict(expected=reachable(observation, world),
                            external_correct=None if not run['adoption']['accepted'] else
                            run['adoption']['value'] is reachable(observation, world))
                   for name,world in case['worlds'].items()}
    return dict(native=native_report, controller=control_report, candidates=candidate_reports,
                selections=selection_reports, final_world_results=final_truth), rows


def verify_raw(run_path) -> tuple:
    # 여기서도 조건 검증만 재사용한다. 생산 실행/선택 함수는 부르지 않는다.
    from .protocol import validate_plan
    from r036_input_representation.audit import check_seed
    root = io.safe(run_path); plan = io.load(root/'plan.json'); validate_plan(plan, check_parent=False)
    manifest = io.load(root/'manifest.json')
    demand(set(manifest) == {'schema', 'state', 'independent_audit_pending', 'files'} and
           manifest['schema'] == 'hcr-exp18-raw-manifest-v1' and manifest['state'] == 'raw_complete' and
           manifest['independent_audit_pending'] is True, '미완료 raw manifest')
    all_sources = plan['dependency_source_hashes'] | plan['addon_source_hashes']
    expected = {'plan.json', 'environment.json', 'attempts.jsonl', 'basis/exp17/manifest.json', 'basis/exp17/plan.json'}
    expected |= {'upstream/'+n for n in sources.UPSTREAM_FILES}
    expected |= {'source/'+n for n in all_sources}
    expected |= {'raw/'+t['id']+'.json' for t in plan['trials']}
    demand(set(manifest['files']) == expected, 'raw inventory/population')
    actual = {n for n in io.inventory(root) if not n.startswith(('analysis/', 'audit_failures/'))}
    demand(actual == expected | {'manifest.json'}, '미등록/누락 raw 파일')
    for n,h in manifest['files'].items():
        demand(io.file_hash(io.child(root,n)) == h, 'raw checksum: '+n)
    for n,h in all_sources.items():
        demand(io.text_hash(io.child(root,'source/'+n)) == h, '동결 소스 snapshot: '+n)
    parent_manifest = io.load(root/'basis/exp17/manifest.json')
    parent_plan = io.load(root/'basis/exp17/plan.json')
    demand(parent_manifest['schema'] == 'hcr-exp17-raw-manifest-v1' and parent_manifest['state'] == 'raw_complete' and
           parent_plan['schema'] == 'hcr-exp17-plan-v1', 'EXP-17 parent schema')
    for n,h in plan['parent_file_hashes'].items():
        name = n if n.startswith('upstream/') else 'basis/exp17/'+n
        demand(io.file_hash(io.child(root,name)) == h, 'EXP-17 parent copy: '+n)
        if n != 'manifest.json':
            demand(parent_manifest['files'][n] == h, 'EXP-17 manifest binding: '+n)
    old_manifest = io.load(root/'upstream/manifest.json')
    demand(old_manifest['schema'] == 'hcr-exp15-raw-manifest-v1' and old_manifest['state'] == 'raw_complete', 'EXP-15 manifest')
    for n in sources.UPSTREAM_FILES[1:]:
        demand(old_manifest['files'][n] == plan['upstream_file_hashes'][n], 'EXP-15 출처 hash')
    seed, old, seed_report = check_seed(root, plan)
    cases = {c['name']:c for c in old['conditions']['cases']}
    public = [dict(name=c['name'],family=c['family'],observation=c['observation']) for c in old['conditions']['cases']]
    demand(public == plan['cases'] == parent_plan['cases'], '입력 population 변조')
    demand(parent_plan['memory_sha256'] == plan['memory_sha256'] and
           parent_plan['config_sha256'] == plan['config_sha256'], 'EXP-17 seed 결합')
    stream = [io.loads(line) for line in io.read(root/'attempts.jsonl').decode('utf-8').splitlines()]
    pos = 0; records = {}; rows = []; final_rows = []
    def take(expected_row):
        nonlocal pos
        demand(pos < len(stream) and digest(stream[pos]) == digest(expected_row), f'attempt stream 불일치: {pos}')
        pos += 1
    for trial in plan['trials']:
        tid = trial['id']; raw = io.load(root/'raw'/f'{tid}.json')
        demand(set(raw) == {'schema','trial','run'} and raw['schema'] == 'hcr-exp18-raw-trial-v1' and raw['trial'] == trial,
               'raw trial 결합')
        case = cases[trial['case']]
        report, rr = audit_native(raw['run'], case['observation'], seed, trial, plan['conditions'], case)
        take(dict(event='trial_started',trial_id=tid))
        for event in raw['run']['events']:
            take(dict(event='online_action',trial_id=tid,record=event))
        take(dict(event='trial_completed',trial_id=tid,raw_sha256=digest(raw)))
        records[tid] = dict(raw_sha256=digest(raw), audit=report, rows=rr)
        rows.extend(rr)
        final_rows.append(dict(trial=trial, adoption=raw['run']['adoption'],
            native_readouts=len(rr), costs=report['controller'],
            native_proof_nodes=sum(r['native_proof_nodes'] for r in rr),
            world_results=report['final_world_results']))
    demand(pos == len(stream), '미등록 trial/retry/tail event')
    from .reporting import summarize
    summary = summarize(rows, final_rows)
    audit = dict(schema='hcr-exp18-audit-v1', verified=True,
                 raw_manifest_sha256=io.file_hash(root/'manifest.json'), native_trials=len(records),
                 native_readouts=len(rows), stream_records=len(stream), seed_training=seed_report,
                 native_sessions_independently_replayed=True, online_control_independently_recomputed=True,
                 proof_DAGs_independently_checked=True, first_decisions_preserved=True,
                 correctness_or_improvement_required=False)
    return summary, audit, records


def write_analysis(run_path, *, check_only=False) -> dict:
    root = io.safe(run_path)
    try:
        from .reporting import render, csv_text
        summary, audit, records = verify_raw(root)
        target = root/'analysis'
        objects = {'summary.json':summary, 'audit.json':audit} | {'records/'+k+'.json':v for k,v in records.items()}
        texts = {'summary.ko.md':render(summary), 'conditions.csv':csv_text(summary['readout_rows'])}
        if check_only:
            manifest = io.load(target/'manifest.json')
            demand(manifest['schema'] == 'hcr-exp18-analysis-manifest-v1' and
                   manifest['raw_manifest_sha256'] == audit['raw_manifest_sha256'], 'analysis provenance')
            demand(io.inventory(target) == set(objects) | set(texts) | {'manifest.json'} and
                   set(manifest['files']) == set(objects) | set(texts), 'analysis inventory')
            for n,v in objects.items():
                demand(io.load(target/n) == v, '독립 재계산: '+n)
            for n,v in texts.items():
                demand(io.read(target/n).decode('utf-8') == v, '보고서 재계산: '+n)
            for n,h in manifest['files'].items():
                demand(io.file_hash(target/n) == h, 'analysis checksum: '+n)
        else:
            target.mkdir(parents=True, exist_ok=False)
            for n,v in objects.items():
                io.put(target/n,v)
            for n,v in texts.items():
                io.write_bytes(target/n,v.encode('utf-8'))
            io.put(target/'manifest.json', dict(schema='hcr-exp18-analysis-manifest-v1',
                raw_manifest_sha256=audit['raw_manifest_sha256'],
                files={n:io.file_hash(target/n) for n in sorted(set(objects)|set(texts))}))
        return audit
    except BaseException as exc:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        try:
            kind = ('interrupted' if isinstance(exc, KeyboardInterrupt) else
                    'parsing_failure' if isinstance(exc, (json.JSONDecodeError, UnicodeError)) else
                    'runtime_io_failure' if isinstance(exc, OSError) else
                    'dependency_failure' if isinstance(exc, ImportError) else
                    'schema_contract_failure' if isinstance(exc, (KeyError, TypeError)) else 'evaluator_disagreement')
            io.put(root/'audit_failures'/f'{stamp}.json', dict(status=kind,
                error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc(), automatic_retry=False))
        except OSError:
            pass
        raise
