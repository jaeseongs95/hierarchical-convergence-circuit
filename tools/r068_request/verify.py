"""Separate evaluator: native formula replay and explicit API contract checks."""
import argparse
from copy import deepcopy
from itertools import product
from pathlib import Path
import sys
from hcr.evaluation.review_audit import packet_states
from tools.r050_review_boundary.audit import candidate_measures, counter_values, FORBIDDEN
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require
from tools.r063_formation.audit import verify_execution, mutation_checks


def check_request(record, execution):
    expected = execution['candidate']['packet']
    require(record == dict(status='contract_rejected', request=None,
        error=dict(type='ContractError', message='R0.2 revision requires external error feedback'),
        before=expected, after=expected), 'No-feedback rejection and atomic state')
    _, report = packet_states(record['after']); require(report['verified'], 'Finished branch replay')
    core = record['after']['document']['engine']
    require(not core['feedback'] and not core['requests'], 'No injected feedback/request')


def check_synthetic(row, plan, memory):
    name = row['name']; obs = deepcopy(plan['observation']); obs['episode_id'] = 'synthetic-'+name
    cfg = deepcopy(plan['config'])
    if name in ('single_candidate_revision', 'duplicate_pending', 'unrequested_edge'): obs['edges'][0]['score'] = 1.0
    if name == 'strong_edges':
        for edge in obs['edges']: edge['score'] = 1.0
    if name == 'zero_budget': cfg['kernel']['max_observation_requests'] = 0
    if name == 'zero_budget':
        require(row == dict(name=name, config=cfg, status='configuration_rejected',
            error='양의 정수 설정 필요: max_observation_requests', packets=[]), 'Invalid zero-budget configuration')
        return
    mode = {'frozen_feedback':'frozen_eval', 'train_mode':'train'}.get(name, 'adapt')
    require(row['observation'] == obs and row['config'] == cfg and row['mode'] == mode, 'Synthetic inputs')
    for packet in row['packets']:
        states, report = packet_states(packet); require(report['verified'], 'Synthetic independent replay')
        require(states[0]['memory'] == memory and packet['document']['engine']['config'] == cfg, 'Synthetic seed/config')
        require(packet['document']['session_id'] == 'r068-synthetic-'+name, 'Synthetic identity')
    first = row['packets'][0]['document']; last = row['packets'][-1]['document']
    require(first['events'][-1]['payload'] == row['decision'], 'Initial synthetic decision')
    require(row['decision']['mode'] == mode and row['decision']['value'] is True, 'Synthetic positive initial judgment')
    feedback = dict(id='synthetic-feedback-'+name, decision_id=row['decision']['id'],
        observation_digest=row['decision']['observation_digest'], correct=name == 'correct_feedback', proof_valid=False,
        source='external_reference')
    require(row['feedback'] == feedback, 'Synthetic feedback intervention')
    recorded = [e['payload'] for e in last['events'] if e['event'] == 'r02_feedback']
    require(recorded == ([] if name == 'frozen_feedback' else [feedback]), 'Exact feedback consumption')
    expected_ids = ['e0','e1'] if name == 'weak_edges' else ['e1'] if name in (
        'single_candidate_revision','duplicate_pending','unrequested_edge') else None
    expected_request = None if expected_ids is None else dict(decision_id=row['decision']['id'],
        episode_id=obs['episode_id'], revision=1, edge_ids=expected_ids, reason='uncertain_features_after_error')
    require(row['request'] == expected_request, 'Synthetic native request selection')
    request_events = [e['payload'] for e in last['events'] if e['event'] == 'r02_observation_requested']
    require(request_events == ([] if expected_request is None else [expected_request]), 'Request event count')
    error_contracts = {
        'frozen_feedback':('feedback','R0.2 frozen evaluation cannot learn'),
        'correct_feedback':('request_revision','R0.2 revision requires external error feedback'),
        'duplicate_pending':('request_revision','R0.2 revision already pending'),
        'unrequested_edge':('begin','R0.2 unrequested measurement changed')}
    require(len(row['errors']) == int(name in error_contracts), 'Expected rejection coverage')
    for error in row['errors']:
        operation, message = error_contracts[name]
        require(error == dict(operation=operation,message=message,before=row['packets'][-1],after=row['packets'][-1]), 'Synthetic rejection atomicity')
    if name == 'single_candidate_revision':
        d = row['later']; require(d is not None and d['value'] is False and d['observation_revision'] == 1
            and d['cost']['observation_requests'] == 1, 'Synthetic revision readout')
        require(last['transitions'][:len(first['transitions'])] == first['transitions'], 'Same-session prefix')
        require(last['events'][-1]['payload'] == d, 'Revision decision binding')
        attempts = [e['payload'] for e in last['events'] if e['event'] == 'r02_attempt_started']
        require(len(attempts) == 2 and attempts[1]['revision_of'] == row['decision']['id'], 'Revision lineage')
    else: require(row['later'] is None, 'No synthetic extra inference')


def main(out):
    plan = load(out/'plan.json'); memory = load(out/'parent/memory/after_correction.json')
    require(plan == load(out/'source/experiments/exp-49-request-boundary/frozen_spec.json'), 'Frozen spec')
    for folder, manifest in [('source','source_manifest.json'),('parent','input_manifest.json'),
                             ('evaluation','raw_manifest.json'),('synthetic','synthetic_manifest.json')]:
        require(files(out/folder) == load(out/manifest)['files'], 'Coverage '+folder)
    previous = load(out/'source/experiments/exp-48-observation-refresh/frozen_spec.json')
    for key in ('observation','config','limits','parent_run','parent_files'):
        require(plan[key] == previous[key], 'Preserved R067 '+key)
    require(files(out/'parent') == plan['parent_files'], 'Pinned parent')
    require(plan['modes'] == ['frozen_eval','adapt'], 'Mode coverage')
    rows = []; sample = None
    for mode, gate in product(plan['modes'], (False, True)):
        identity = f"{mode}-{'on' if gate else 'off'}"; where = out/'evaluation'/identity
        execution = load(where/'inference.json')
        verify_execution(plan, execution, dict(observation=plan['observation']), memory, gate, mode, 'r068-'+identity)
        require(execution['candidate'] is not None, 'Completed boundary probe')
        record = load(where/'request_attempt.json'); check_request(record, execution)
        before = execution['candidate']['packet']['document']
        require(not any(e['event']=='r02_observation_requested' for e in before['events']), 'Automatic request count')
        rows.append(dict(identity=identity,mode=mode,gate=gate,value=execution['candidate']['decision']['value'],
            accepted=execution['candidate']['readout']['accepted'],cost=counter_values(execution),
            api_status=record['status'],request=None,measurement_calls=0,feedback_calls=0,
            reference_A=candidate_measures(execution,False),reference_B=candidate_measures(execution,True)))
        sample = (execution,record,mode,gate,identity)
    require({p.name for p in (out/'evaluation').iterdir()} == {r['identity'] for r in rows}, 'Research cell coverage')
    require({p.stem for p in (out/'synthetic').glob('*.json')} == set(plan['synthetic_cases']), 'Synthetic coverage')
    for name in plan['synthetic_cases']: check_synthetic(load(out/'synthetic'/f'{name}.json'),plan,memory)
    require(load(out/'validation/selftest.json') == dict(passed=plan['synthetic_cases'],synthetic_only=True), 'Synthetic report')
    execution,record,mode,gate,identity = sample
    rejected = mutation_checks(plan,execution,dict(observation=plan['observation']),memory,gate,mode,'r068-'+identity)
    for name, change in [('request_injected',lambda x:x.update(request={'edge_ids':['e1']})),
                         ('success_forged',lambda x:x.update(status='returned')),
                         ('state_changed',lambda x:x['after']['document']['engine']['memory'].update(version=999))]:
        bad = deepcopy(record); change(bad)
        try: check_request(bad,execution)
        except (ValueError,AssertionError,RuntimeError): rejected.append(name)
        else: raise AssertionError('Undetected request mutation '+name)
    syn = load(out/'synthetic/weak_edges.json'); bad = deepcopy(syn); bad['request']['edge_ids']=['e1']
    try: check_synthetic(bad,plan,memory)
    except (ValueError,AssertionError,RuntimeError): rejected.append('synthetic_edge_selection')
    else: raise AssertionError('Undetected synthetic mutation')
    require(not (FORBIDDEN | {'tools.r068_request.worker','tools.r068_request.selftest'}) & set(sys.modules), 'Independent evaluator import boundary')
    dump(out/'summary.json',dict(rows=rows,research_sessions=4,reference_worlds_per_session=2,
        independent_samples=False,autonomous_request_comparison='not_measurable_missing_native_fact_freshness_input',
        automatic_requests=0,api_attempts_without_feedback=4,measurement_calls=0,research_feedback_calls=0,
        synthetic_cases=len(plan['synthetic_cases']),claim='Existing request API requires external error feedback; no autonomous conflict trigger demonstrated.'))
    dump(out/'verification.json',dict(verified=True,research_formula_replays=4,synthetic_cases=len(plan['synthetic_cases']),
        rejected_mutations=rejected,independent_process=True,independent_researcher=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out',type=Path,required=True)
    main(parser.parse_args().out)
