"""Independent journal and equation replay; no native producer imports."""
import argparse
from pathlib import Path
import sys
from hcr import codec
from hcr.evaluation.adaptive_audit_support import chain_program, scan_patterns, pool_network, circuit_id
from tools.r050_review_boundary.common import dump, files, load, require, sha
from tools.r050_review_boundary.audit import FORBIDDEN, candidate_measures, counter_values
from tools.r063_formation.audit import verify_execution, mutation_checks
from tools.r064_retention.audit import reference, check_learning
from tools.r076_competition.audit import pools

SPEC = 'experiments/exp-58-equal-binding/frozen_spec.json'


def recipe_reference(out, step):
    plan = load(out/'plan.json'); case = plan['training'][step-1]
    e = load(out/'training'/str(step)/'inference.json')
    verify_execution(plan, e, case, load(out/'memory'/f'{step-1}.json'), True,
                     'train', 'r077-train-'+case['id'])
    world = load(out/'source'/plan['world_file'])['training'][case['id']]
    return reference(e, case['observation'], world)


def collect(out):
    plan = load(out/'plan.json'); cfg = codec.adaptive_config_from(plan['config'])
    require(plan == load(out/'source'/SPEC), 'Frozen design binding')
    require(sha((out/'source'/plan['world_file']).read_bytes()) == plan['world_sha256'], 'Frozen world')
    require(cfg.kernel.prior_gain == 0 and cfg.pattern_lengths == (2,), 'Prior-disabled length2 contract')
    world = load(out/'source'/plan['world_file']); formation = []
    require(load(out/'memory/0.json') == dict(schema='hcr-memory-r02', config_signature=cfg.signature,
        version=0, circuits=[], pending=[], consumed_feedback=[], patches=[]), 'Native empty memory')
    for step, case in enumerate(plan['training'], 1):
        base = out/'training'/str(step); e = load(base/'inference.json'); expected = recipe_reference(out, step)
        require(load(base/'reference.json') == expected, 'Reference feedback binding')
        before = load(out/'memory'/f'{step-1}.json'); after = load(out/'memory'/f'{step}.json')
        learn = load(base/'learning.json'); check_learning(e, expected, learn, before, after)
        formation.append(dict(step=step, assessment=expected['assessment'], patch=learn['patch'],
            compiled_lengths=[len(c['pattern']['relations']) for c in after['circuits']],
            pending_lengths=[len(c['pattern']['relations']) for c in after['pending']]))
    memory = load(out/'memory'/f"{len(plan['training'])}.json")
    circuit_states = [dict(id=circuit_id(c), length=len(c['pattern']['relations']), strength=c['strength'],
        version=c['version'], failures=c['failures'], active=c['active'], episodes=c['evidence_episodes'])
        for c in memory['circuits']]
    formed = len(circuit_states) == 1 and circuit_states[0]['length'] == 2 and circuit_states[0]['active']
    rows = []
    for cell in plan['cells']:
        raw = load(out/'evaluation'/cell['id']/'inference.json'); require(raw['cell'] == cell, 'Cell identity')
        e = raw['execution']
        verify_execution(plan, e, cell, memory, cell['use_circuits'], 'frozen_eval', 'r077-'+cell['id'])
        events = e['packet']['document']['events']; networks = pools(e, cell['observation'], memory, cfg)
        selections = [x['payload']['candidate'] for x in events if x['event'] == 'r02_expansion']
        scans = [x['payload'] for x in events if x['event'] == 'r02_binding_scan']
        tick_split = {kind:sum(x['event']=='r02_tick' and x['payload']['network_id']==n['payload']['network_id']
            for n in events if n['event']=='r02_network' and n['payload']['kind']==kind for x in events)
            for kind in ('pool', 'decision')}
        cost = counter_values(e); require(sum(tick_split.values()) == cost['kernel_ticks'], 'Separate tick ledger')
        candidates = [] if not networks else networks[0]['candidates']
        engaged = (formed and len(candidates) == 2 and all(a['goal_binding'] for a in candidates)
            and [a['edges'] for a in candidates] == [[0,1],[2,3]]
            and len({a['circuit_id'] for a in candidates}) == 1)
        # Check every later pool too; never remove an unexpected native candidate.
        for pool in networks:
            require(all(a['goal_binding'] and len(a['edges']) == 2 for a in pool['candidates']), 'Unexpected prefix')
            require(all(a['prior'] == 0 and a['mismatch'] == 0 for a in pool['candidates']), 'Prior/mismatch control')
        candidate = e['candidate']; ref = reference(e, cell['observation'], world['evaluation'])
        rows.append(dict(id=cell['id'], score=cell['score'], use_circuits=cell['use_circuits'], stop=e['stop'],
            binding_scans=scans, pools=networks, selections=selections,
            first_selection=selections[0] if selections else None,
            binding_construct_engaged=engaged if cell['use_circuits'] else None,
            candidate=None if candidate is None else {k:candidate[k] for k in ('decision','diagnostic','readout')},
            measures=candidate_measures(e, True), cost=cost, tick_split=tick_split, assessment=ref['assessment'],
            wall_seconds=e['packet']['document']['engine']['pending']['cost']['wall_seconds']))
    pairs = []
    for score_id in plan['scores']:
        on, off = [next(r for r in rows if r['id'] == score_id+'-'+gate) for gate in ('on','off')]
        complete = on['candidate'] is not None and off['candidate'] is not None
        pairs.append(dict(score_id=score_id, evaluable=complete,
            first_selection_equal=None if not complete else on['first_selection'] == off['first_selection'],
            D_DAG_on=on['measures']['D_DAG'], D_DAG_off=off['measures']['D_DAG'],
            raw_value_equal=None if not complete else on['measures']['raw_decision'] == off['measures']['raw_decision'],
            adopted_value_equal=None if not complete else on['measures']['adopted_value'] == off['measures']['adopted_value'],
            cost_difference_on_minus_off={k:on['cost'][k]-off['cost'][k] for k in on['cost']}))
    on = [r for r in rows if r['use_circuits']]
    evaluable = all(r['binding_construct_engaged'] and r['first_selection'] is not None
        and r['pools'][0]['stable'] for r in on)
    choices = {(r['first_selection']['source'], tuple(r['first_selection']['edges']))
        for r in on if r['first_selection'] is not None}
    endpoints = all(next(r for r in on if r['id'] == identity)['first_selection'] is not None
        and next(r for r in on if r['id'] == identity)['first_selection']['source'] == 'circuit'
        and next(r for r in on if r['id'] == identity)['first_selection']['edges'] == path
        for identity, path in plan['predictions']['endpoint_first_selections'].items())
    return dict(schema='hcc-r077-summary-v1', formation=formation, circuit_states=circuit_states,
        formation_construct_engaged=formed, rows=rows, pairs=pairs,
        score_selection_prediction='not_evaluable' if not evaluable else 'supported' if len(choices)>1 else 'falsified',
        endpoint_preference_prediction='not_evaluable' if not evaluable else 'supported' if endpoints else 'falsified',
        first_selection_switch_observed=None if not evaluable else len(choices)>1,
        intervention='nonnegative_public_e3_score_under_zero_prior_gain_fixed_equal_length_bindings',
        stored_pattern_count=len(circuit_states), expected_initial_binding_count=2,
        native_preparation_executions=len(plan['training']), native_evaluation_executions=len(plan['cells']),
        feedback_applications=sum(x['patch'] is not None for x in formation), new_independent_samples=0,
        inhibition_causal_effect='not_isolated', actual_energy_joules=None, peak_memory_bytes=None,
        claim_boundary='One native pattern, two complete bindings; prior/mismatch zero; fixed scheduler and authored world. No inhibition necessity, general performance or independent discovery sample claim.')


def selftest(out):
    plan = load(out/'plan.json'); cfg = codec.adaptive_config_from(plan['config'])
    require(cfg.kernel.prior_gain == 0 and cfg.pattern_lengths == (2,), 'Config control')
    obs = codec.observation_from(plan['cells'][0]['observation'])
    # Synthetic grammar only; this memory never reaches the producer.
    memory = dict(circuits=[dict(pattern=dict(relations=[{}]*2,
        program=chain_program(2, [[0,1]], cfg.kernel)),
        evidence_episodes=['synthetic-1','synthetic-2','synthetic-3'], strength=.55, version=1, active=True)])
    scanned = scan_patterns(obs, dict(path=[], visited=[obs.start]), memory, cfg, cfg.max_binding_checks)
    require(scanned['complete'] and [m['binding']['edge_order'] for m in scanned['matched']] == [[0,1],[2,3]], 'Two complete bindings')
    program, drives, meta, _ = pool_network(obs, scanned['matched'], memory, cfg)
    require(len(meta)==2 and len({m['circuit_id'] for m in meta})==1, 'One pattern, two bindings')
    require(sum(l['source'].startswith('c:') and l['target'].startswith('c:') for l in program['links'])==2, 'Inhibition grammar')
    base = plan['cells'][0]['observation']
    require(len(base['edges'])==4 and len(plan['cells'])==2*len(plan['scores']), 'Cell coverage')
    for cell in plan['cells']:
        obs2 = cell['observation']
        require({k:v for k,v in obs2.items() if k!='edges'}=={k:v for k,v in base.items() if k!='edges'}, 'Fixed identity/revision')
        require(len(obs2['edges'])==len(base['edges']), 'Fixed edge count')
        for i, (a,b) in enumerate(zip(base['edges'], obs2['edges'])):
            require({k:v for k,v in a.items() if k!='score'}=={k:v for k,v in b.items() if k!='score'}, 'Fixed topology/order/IDs')
            require(b['score']==(cell['score'] if i==3 else .6 if i==1 else 1.0), 'Only e3 score varies')
        _, _, metadata, _ = pool_network(codec.observation_from(obs2), scanned['matched'] if obs2==base else
            scan_patterns(codec.observation_from(obs2),dict(path=[],visited=[obs.start]),memory,cfg,cfg.max_binding_checks)['matched'], memory, cfg)
        require(all(m['prior']==0 and m['mismatch']==0 for m in metadata), 'Zero prior and mismatch')
    for a,b in zip(plan['cells'][::2],plan['cells'][1::2]):
        require(a['observation']==b['observation'] and a['use_circuits'] and not b['use_circuits'], 'ON/OFF pairs')
    world = load(out/'source'/plan['world_file'])
    require(world['evaluation']=={e['id']:True for e in base['edges']}, 'Fixed all-passable world')
    dump(out/'validation/selftest.json', dict(verified=True, synthetic_candidate_count=2,
        synthetic_stored_pattern_count=1, synthetic_inhibition_links=2, synthetic_native_executions=0,
        research_sample=False, paired_intervention_checked=True, prior_mismatch_zero=True))


def main(out, phase, step=None):
    if phase == 'reference':
        dump(out/'training'/str(step)/'reference.json', recipe_reference(out, step))
    elif phase == 'selftest':
        selftest(out)
    else:
        for folder, manifest in [('source','source_manifest.json'),('memory','memory_manifest.json'),
                                  ('training','training_manifest.json'),('evaluation','raw_manifest.json')]:
            require(files(out/folder)==load(out/manifest)['files'], 'Exact raw coverage '+folder)
        summary = collect(out); plan = load(out/'plan.json'); cell = plan['cells'][-2]
        raw = load(out/'evaluation'/cell['id']/'inference.json')
        memory = load(out/'memory'/f"{len(plan['training'])}.json")
        rejected = mutation_checks(plan,raw['execution'],cell,memory,cell['use_circuits'],'frozen_eval','r077-'+cell['id']) if raw['execution']['candidate'] is not None else []
        dump(out/'summary.json', summary)
        dump(out/'verification.json', dict(verified=True,
            independent_native_replays=len(plan['training'])+len(plan['cells']),
            independent_feedback_replays=summary['feedback_applications'], rejected_raw_mutations=rejected,
            max_pool_replay_error=max((p['max_replay_error'] for r in summary['rows'] for p in r['pools']),default=None),
            all_candidate_states_preserved=True, negative_result_allowed=True, producer_imports=False))
    require(not (FORBIDDEN|{'hcr.activation','hcr.expansion','hcr.learning','tools.r077_equal_binding.worker'}) & set(sys.modules), 'Auditor producer boundary')
    print('Independent audit passed:', phase, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',choices=['selftest','reference','final'],required=True); p.add_argument('--step',type=int)
    a = p.parse_args(); main(a.out,a.phase,a.step)
