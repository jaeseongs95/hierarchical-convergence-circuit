"""Independent native replay + additional accounting, sealed analysis, and read-only verify."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import traceback
from . import storage as io, sources, input_audit, reporting
from .contracts import PLAN_SCHEMA, RAW_SCHEMA, RAW_MANIFEST_SCHEMA, ANALYSIS_MANIFEST_SCHEMA
from .protocol import validate_plan


def check_attempt_stream(root, plan):
    """Exact cardinality/order: no hidden trials, dropped first attempts, retries or tail records."""
    count=0
    with (root/'attempts.jsonl').open(encoding='utf-8') as stream:
        def take(expected):
            nonlocal count
            line=stream.readline()
            io.require(bool(line),'attempt stream ended early')
            io.require(io.digest(io.loads(line))==io.digest(expected),'attempt stream mismatch at '+str(count))
            count+=1
        for trial in plan['trials']:
            raw=io.load(root/'raw'/f"{trial['id']}.json");run=raw['run'];tid=trial['id']
            take(dict(event='trial_started',trial=trial))
            for event in run['base']['events']:
                take(dict(event='trial_action',trial_id=tid,record=dict(event='native_action',record=event)))
            take(dict(event='trial_action',trial_id=tid,record=dict(event='base_completed',base_sha256=io.digest(run['base']))))
            for event in run['posthoc_events']:
                take(dict(event='trial_action',trial_id=tid,record=dict(event='posthoc_action',record=event)))
            take(dict(event='trial_action',trial_id=tid,record=dict(event='arm_finished',final=run['final'])))
            take(dict(event='trial_completed',trial_id=tid,raw_sha256=io.digest(raw)))
        io.require(stream.read()=='','unexpected retry/trial/tail stream')
    return count


def verify_raw(path):
    from r036_input_representation.audit import check_seed
    from r044_reuse_contribution.trial_audit import audit_trial as audit_parent_trial
    from .trial_audit import audit_trial
    root=io.safe(path);plan=io.load(root/'plan.json');manifest=io.load(root/'manifest.json')
    validate_plan(plan,check_parent=False)
    io.require(set(manifest)=={'schema','state','independent_audit_pending','files'} and
        manifest['schema']==RAW_MANIFEST_SCHEMA and manifest['state']=='raw_complete' and manifest['independent_audit_pending'] is True,
        'EXP26 raw complete manifest contract')
    all_sources=sources.merge_hashes(plan['dependency_source_hashes'],plan['addon_source_hashes'])
    expected={'plan.json','environment.json','attempts.jsonl'} | {'source/'+n for n in all_sources}
    expected|={sources.capsule_name(n) for n in plan['parent_file_hashes']}
    expected|={'raw/'+t['id']+'.json' for t in plan['trials']}
    actual={n for n in io.inventory(root) if not n.startswith(('analysis/','audit_failures/'))}
    io.require(set(manifest['files'])==expected and actual==expected|{'manifest.json'},'EXP26 raw inventory')
    for name,h in manifest['files'].items():
        io.require(io.file_hash(io.child(root,name))==h,'raw checksum: '+name)
    for name,h in all_sources.items():
        io.require(io.text_hash(io.child(root,'source/'+name))==h,'preserved source mismatch: '+name)
    documents,hashes={},{}
    for name in plan['parent_file_hashes']:
        data=io.read(io.child(root,sources.capsule_name(name)))
        documents[name],hashes[name]=io.loads(data),io.bytes_hash(data)
    io.require(hashes==plan['parent_file_hashes'],'EXP25 capsule lineage')
    parent,seed=sources.validate_parent_documents(documents,hashes)
    input_report=input_audit.check_plan_inputs(plan,parent,seed)
    checked_seed,_,seed_report=check_seed(root,plan)
    io.require(checked_seed==seed,'independent training seed replay disagrees')
    env=io.load(root/'environment.json')
    io.require(env['mode']=='native_experiment' and env['synthetic_backend'] is False and
        env['automatic_retry'] is False and env['external_llm_used'] is False and
        env['inherited_runtime']=='R044_worker_R041_loop_native_constructor_gate_unchanged','native environment declaration')
    stream_records=check_attempt_stream(root,plan)
    cases={c['name']:dict(deepcopy(c),worlds=deepcopy(plan['evaluation_worlds'][c['name']])) for c in plan['cases']}
    records={}
    for trial in plan['trials']:
        tid=trial['id'];raw=io.load(root/'raw'/f'{tid}.json')
        io.require(set(raw)=={'schema','trial','run'} and raw['schema']==RAW_SCHEMA and raw['trial']==trial,'raw trial binding')
        record=audit_trial(raw['run'],trial,cases[trial['case']],seed,plan['conditions'])
        record['raw_sha256']=io.digest(raw);records[tid]=record
    parent_cases={c['name']:dict(deepcopy(c),worlds=deepcopy(parent['evaluation_worlds'][c['name']])) for c in parent['cases']}
    parent_reports={}
    for tid in sources.REGRESSION_IDS:
        raw=documents['raw/'+tid+'.json'];trial=raw['trial']
        parent_reports[tid]=audit_parent_trial(raw['run'],trial,parent_cases[trial['case']],seed,parent['conditions'])
    summary=reporting.summarize(list(records.values()))
    audit=dict(schema='hcr-exp26-audit-v1',verified=True,raw_manifest_sha256=io.file_hash(root/'manifest.json'),
        native_trials=12,native_readouts=sum(len(r['readouts']) for r in records.values()),stream_records=stream_records,
        input_isolation=input_report,seed_training=seed_report,independent_native_state_proof_control_replay=True,
        parent_raw_independently_replayed=4,parent_full_24_raw_replayed_in_this_audit=False,
        parent_native_rerun_in_this_audit=False,parent_regression_live_runs_in_launcher_selftest_not_research=True,
        inverse_mapping_evaluator_only=True,native_sources_modified=False,
        correctness_required=False,direct_exposure_required_for_audit=False,predictions_are_results_not_validity=True)
    return summary,audit,records,parent_reports


def contents(summary,audit,records,parent_reports):
    objects={'summary.json':summary,'audit.json':audit,'claims.json':summary['claims'],
             'parent_raw_rechecks.json':parent_reports}
    objects.update({'records/'+tid+'.json':r for tid,r in records.items()})
    texts={'summary.ko.md':reporting.render(summary)}
    for key in ('comparisons','cost_differences','ID_controls','conflict_controls','trials','groups','decision_networks',
                'candidate_exposure','expansion_actions','readouts','binding_scans'):
        texts[key+'.csv']=reporting.csv_text(summary[key])
    # Full pool + decision event costs, not only decision signatures.
    networks=[]
    for tid,r in records.items():
        tags=dict(trial_id=tid,family=r['family'],id_variant=r['id_variant'],use_circuits=r['trial']['use_circuits'])
        networks.extend(dict(**tags,**n) for n in r['reuse_measurements']['networks'])
    texts['network_costs.csv']=reporting.csv_text(networks)
    return objects,texts


def write_analysis(path, *, check_only=False):
    root=io.safe(path)
    try:
        summary,audit,records,parent_reports=verify_raw(root)
        objects,texts=contents(summary,audit,records,parent_reports);target=root/'analysis'
        names=set(objects)|set(texts)
        if check_only:
            manifest=io.load(target/'manifest.json')
            io.require(set(manifest)=={'schema','raw_manifest_sha256','files'} and manifest['schema']==ANALYSIS_MANIFEST_SCHEMA and
                manifest['raw_manifest_sha256']==audit['raw_manifest_sha256'],'analysis lineage')
            io.require(set(manifest['files'])==names and io.inventory(target)==names|{'manifest.json'},'analysis inventory')
            for name,value in objects.items(): io.require(io.digest(io.load(target/name))==io.digest(value),'analysis recomputation: '+name)
            for name,value in texts.items(): io.require(io.read(target/name).decode('utf-8')==value,'report recomputation: '+name)
            for name,h in manifest['files'].items(): io.require(io.file_hash(target/name)==h,'analysis checksum: '+name)
        else:
            target.mkdir(parents=True,exist_ok=False)
            for name,value in objects.items(): io.put(target/name,value)
            for name,value in texts.items(): io.write_bytes(target/name,value.encode('utf-8'))
            io.put(target/'manifest.json',dict(schema=ANALYSIS_MANIFEST_SCHEMA,raw_manifest_sha256=audit['raw_manifest_sha256'],
                files={n:io.file_hash(target/n) for n in sorted(names)}))
        return audit
    except BaseException as exc:
        kind=('interrupted' if isinstance(exc,KeyboardInterrupt) else
              'parsing_failure' if isinstance(exc,(json.JSONDecodeError,UnicodeError)) else
              'dependency_failure' if isinstance(exc,ImportError) else
              'runtime_io_failure' if isinstance(exc,OSError) else 'evaluator_disagreement')
        # Typed inherited failures remain distinguishable without importing runtime dependencies on failure.
        if type(exc).__name__=='MeasurementError': kind='measurement_failure'
        if type(exc).__name__=='GateContractError': kind='intervention_contract_failure'
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        try: io.put(root/'audit_failures'/f'{stamp}.json',dict(status=kind,error_type=type(exc).__name__,error=str(exc),
            traceback=traceback.format_exc(),automatic_retry=False))
        except OSError: pass
        raise
