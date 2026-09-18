"""독립 native replay/selector/scheduler 검산 + 역변환·회귀. 생산 worker를 호출하지 않는다."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json
import traceback
from . import storage as io, sources, input_audit, trajectory, baseline_audit, reporting, policy_audit
from .contracts import RAW_SCHEMA, RAW_MANIFEST_SCHEMA, ANALYSIS_MANIFEST_SCHEMA, digest, require


def verify_raw(path):
    from .protocol import validate_plan
    from r036_input_representation.audit import check_seed
    from r041_scheduler_direction.trial_audit import audit_trial as audit_native_trial
    root = io.safe(path); plan = io.load(root/'plan.json')
    validate_plan(plan,check_parent=False)
    manifest = io.load(root/'manifest.json')
    require(set(manifest) == {'schema','state','independent_audit_pending','files'} and
            manifest['schema'] == RAW_MANIFEST_SCHEMA and manifest['state'] == 'raw_complete' and
            manifest['independent_audit_pending'] is True, 'EXP24 raw 완료 manifest 계약')
    all_sources = sources.merge_hashes(plan['dependency_source_hashes'],plan['addon_source_hashes'])
    expected = {'plan.json','environment.json','attempts.jsonl'}
    expected |= {'source/'+n for n in all_sources}
    expected |= {sources.capsule_name(n) for n in plan['parent_file_hashes']}
    expected |= {sources.prior_capsule_name(n) for n in plan['prior_file_hashes']}
    expected |= {'raw/'+t['id']+'.json' for t in plan['trials']}
    actual = {n for n in io.inventory(root) if not n.startswith(('analysis/','audit_failures/'))}
    require(set(manifest['files']) == expected and actual == expected | {'manifest.json'}, 'EXP24 raw inventory')
    for name,h in manifest['files'].items():
        require(io.file_hash(io.child(root,name)) == h, 'raw checksum: '+name)
    for name,h in all_sources.items():
        require(io.text_hash(io.child(root,'source/'+name)) == h, '보존 source 불일치: '+name)
    documents, hashes = {}, {}
    for name in plan['parent_file_hashes']:
        data = io.read(io.child(root,sources.capsule_name(name)))
        documents[name], hashes[name] = io.loads(data),io.bytes_hash(data)
    require(hashes == plan['parent_file_hashes'], 'EXP22 capsule 계보')
    parent,seed = sources.validate_parent_documents(documents,hashes)
    input_report = input_audit.check_plan_inputs(plan,parent,seed)
    prior_docs, prior_hashes = {}, {}
    for name in plan['prior_file_hashes']:
        data = io.read(io.child(root,sources.prior_capsule_name(name)))
        prior_docs[name], prior_hashes[name] = io.loads(data),io.bytes_hash(data)
    require(prior_hashes == plan['prior_file_hashes'], 'EXP23 anchor capsule mismatch')
    prior_report = sources.validate_prior_documents(prior_docs,prior_hashes,parent,plan['cases'],plan['evaluation_worlds'])
    checked_seed,_,seed_report = check_seed(root,plan)
    require(checked_seed == seed, '독립 seed replay 불일치')
    env = io.load(root/'environment.json')
    require(env['mode'] == 'native_experiment' and env['synthetic_backend'] is False and
            env['automatic_retry'] is False and env['external_llm_used'] is False and
            env['inherited_runtime'] == 'R041_unchanged', 'native 환경 선언')
    cases = {c['name']:dict(deepcopy(c),worlds=deepcopy(plan['evaluation_worlds'][c['name']])) for c in plan['cases']}
    parent_cases = {c['name']:dict(deepcopy(c),worlds=deepcopy(parent['evaluation_worlds'][c['name']])) for c in parent['cases']}
    parent_trials = {(t['case'],t['scheduler']):t for t in sources.parent_regression_trials(parent)}
    records = {}; old_reports = {}; stream_count = 0
    with (root/'attempts.jsonl').open(encoding='utf-8') as stream:
        def take(expected_row):
            nonlocal stream_count
            line = stream.readline()
            require(bool(line), 'attempt stream 조기 종료')
            require(digest(io.loads(line)) == digest(expected_row), f'attempt stream 불일치: {stream_count}')
            stream_count += 1
        for trial in plan['trials']:
            tid = trial['id']; case = cases[trial['case']]
            raw = io.load(root/'raw'/f'{tid}.json')
            require(set(raw) == {'schema','trial','run'} and raw['schema'] == RAW_SCHEMA and raw['trial'] == trial,
                    'EXP24 raw trial binding')
            run = raw['run']
            record = audit_native_trial(run,trial,case,seed,plan['conditions'])
            record.update(id_variant=case['id_variant'],branch_order=case['manipulation']['branch_order'],
                          reported_wall_seconds=run['wall_seconds'])
            record['diagnostics'] = trajectory.describe(run,record,case)
            record['input_order_policy_audit'] = policy_audit.check(run['base'])
            take(dict(event='trial_started',trial=trial))
            for event in run['base']['events']:
                take(dict(event='trial_action',trial_id=tid,record=dict(event='native_action',record=event)))
            take(dict(event='trial_action',trial_id=tid,record=dict(event='base_completed',base_sha256=digest(run['base']))))
            for event in run['posthoc_events']:
                take(dict(event='trial_action',trial_id=tid,record=dict(event='posthoc_action',record=event)))
            take(dict(event='trial_action',trial_id=tid,record=dict(event='arm_finished',final=run['final'])))
            take(dict(event='trial_completed',trial_id=tid,raw_sha256=digest(raw)))
            record['parent_regression'] = None
            if case['id_variant'] == 'identity':
                oldtrial = parent_trials[(case['parent_case'],trial['scheduler'])]
                oldraw = documents['raw/'+oldtrial['id']+'.json']
                # 저장 summary가 아니라 parent raw 자체도 같은 독립 native auditor로 다시 검산한다.
                old_reports[oldtrial['id']] = audit_native_trial(oldraw['run'],oldtrial,
                    parent_cases[oldtrial['case']],seed,parent['conditions'])
                record['parent_regression'] = baseline_audit.compare(run,oldraw)
            record['raw_sha256'] = digest(raw)
            records[tid] = record
        require(stream.read() == '', '미등록 trial/retry/tail stream')
    require(len(old_reports) == 6, 'EXP22 회귀 재검산 누락')
    summary = reporting.summarize(list(records.values()))
    audit = dict(schema='hcr-exp24-audit-v1',verified=True,raw_manifest_sha256=io.file_hash(root/'manifest.json'),
        native_trials=12,native_readouts=sum(len(r['readouts']) for r in records.values()),stream_records=stream_count,
        seed_training=seed_report,input_isolation=input_report,prior_lineage=prior_report,
        native_state_proof_control_and_scheduler_independently_replayed=True,
        parent_raw_independently_audited=6,parent_identity_regression_checked=6,
        all_108_parent_trials_replayed_in_this_audit=False,
        inverse_mapping_evaluator_only=True,native_sources_modified=False,
        correctness_required=False,invariance_required=False,
        hypotheses_are_results_not_acceptance_criteria=True)
    return summary,audit,records


def _contents(summary,audit,records):
    objects = {'summary.json':summary,'audit.json':audit}
    objects.update({'records/'+tid+'.json':record for tid,record in records.items()})
    texts = {'summary.ko.md':reporting.render(summary),
             'groups.csv':reporting.csv_text(summary['groups']),
             'paired_ID_control.csv':reporting.csv_text(summary['comparisons']),
             'cost_differences.csv':reporting.csv_text(summary['cost_differences']),
             'comparisons.csv':reporting.csv_text(summary['comparisons']),
             'trials.csv':reporting.csv_text(summary['trials']),
             'readouts.csv':reporting.csv_text(summary['readouts']),
             'scheduler_decisions.csv':reporting.csv_text(summary['scheduler_decisions'])}
    return objects,texts


def write_analysis(path, *, check_only=False):
    root = io.safe(path)
    try:
        summary,audit,records = verify_raw(root)
        objects,texts = _contents(summary,audit,records)
        target = root/'analysis'
        if check_only:
            manifest = io.load(target/'manifest.json')
            require(set(manifest) == {'schema','raw_manifest_sha256','files'} and
                    manifest['schema'] == ANALYSIS_MANIFEST_SCHEMA and
                    manifest['raw_manifest_sha256'] == audit['raw_manifest_sha256'], 'analysis 계보')
            require(set(manifest['files']) == set(objects)|set(texts) and
                    io.inventory(target) == set(objects)|set(texts)|{'manifest.json'}, 'analysis inventory')
            for name,value in objects.items():
                require(digest(io.load(target/name)) == digest(value), 'analysis 독립 재계산: '+name)
            for name,value in texts.items():
                require(io.read(target/name).decode('utf-8') == value, '보고서 재계산: '+name)
            for name,h in manifest['files'].items():
                require(io.file_hash(target/name) == h, 'analysis checksum: '+name)
        else:
            target.mkdir(parents=True,exist_ok=False)
            for name,value in objects.items(): io.put(target/name,value)
            for name,value in texts.items(): io.write_bytes(target/name,value.encode('utf-8'))
            io.put(target/'manifest.json',dict(schema=ANALYSIS_MANIFEST_SCHEMA,
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
