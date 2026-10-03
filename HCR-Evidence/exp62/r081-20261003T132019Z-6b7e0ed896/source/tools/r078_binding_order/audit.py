"""Independent journal/equation replay and slot-to-public-ID correspondence."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from hcr.evaluation.adaptive_audit_support import scan_patterns, pool_network, circuit_id
from hcr.evaluation.review_audit import packet_states
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require, sha
from tools.r050_review_boundary.audit import FORBIDDEN, candidate_measures, counter_values
from tools.r063_formation.audit import verify_execution, mutation_checks
from tools.r064_retention.audit import reference
from tools.r076_competition.audit import pools
from tools.r077_equal_binding.audit import collect as parent_collect

SPEC = 'experiments/exp-59-binding-order/frozen_spec.json'


def controls(plan, parent):
    previous = load(parent/'plan.json')
    require(plan['config'] == previous['config'] and plan['limits'] == previous['limits'], 'R077 config/budget reuse')
    require(fingerprint(plan['config']) == plan['config_sha256'], 'Config hash')
    require(sha((parent/'memory/3.json').read_bytes()) == plan['memory_sha256'], 'R077 seed memory hash')
    require(plan['world_file'] == previous['world_file'] and plan['world_sha256'] == previous['world_sha256'], 'R077 world reuse')
    memory = load(parent/'memory/3.json'); cfg = codec.adaptive_config_from(plan['config'])
    require(memory['config_signature'] == cfg.signature and cfg.kernel.prior_gain == 0 and cfg.pattern_lengths == (2,), 'Memory config/prior/length control')
    require(len(plan['cells']) == 12 and set(plan['orders']) == {'original','swapped'}, 'Frozen order matrix')
    require(plan['orders'] == dict(original=['e0','e1','e2','e3'], swapped=['e2','e3','e0','e1']), 'Block-only swap')
    require(plan['scores'] == previous['scores'], 'R077 score levels')
    expected = []
    for order, ids in plan['orders'].items():
        for old in previous['cells']:
            cell = deepcopy(old); cell.update(id=order+'-'+old['id'], order_id=order)
            edges = {e['id']:e for e in old['observation']['edges']}
            cell['observation']['edges'] = [edges[i] for i in ids]; expected.append(cell)
    require(plan['cells'] == expected, 'Only input edge order changes within each pair')
    return memory, cfg


def public_path(observation, slots):
    edges = observation['edges']
    require(all(type(i) is int and 0 <= i < len(edges) for i in slots), 'Valid edge slot')
    path = [edges[i] for i in slots]
    require(all(a['target'] == b['source'] for a,b in zip(path,path[1:])), 'Bound path adjacency')
    return [edge['id'] for edge in path]


def audit_cell(plan, raw, cell, memory, cfg, world):
    require(raw['cell'] == cell, 'Raw cell identity/order/score')
    e = raw['execution']; obs = cell['observation']
    verify_execution(plan, e, cell, memory, cell['use_circuits'], 'frozen_eval', 'r078-'+cell['id'])
    events = e['packet']['document']['events']; networks = pools(e, obs, memory, cfg)
    selections = [x['payload']['candidate'] for x in events if x['event'] == 'r02_expansion']
    for pool in networks:
        for candidate in pool['candidates']:
            candidate['edge_ids'] = public_path(obs, candidate['edges'])
            require(candidate['prior'] == 0 and candidate['mismatch'] == 0, 'Zero prior/mismatch')
    first = selections[0] if selections else None
    selection_ids = [public_path(obs, selection['edges']) for selection in selections]
    candidates = networks[0]['candidates'] if networks else []
    engaged = (len(candidates) == 2 and len({c['circuit_id'] for c in candidates}) == 1
        and all(c['goal_binding'] and len(c['edges']) == 2 for c in candidates)
        and {tuple(c['edge_ids']) for c in candidates} == {('e0','e1'),('e2','e3')})
    tick_split = {kind:sum(x['event'] == 'r02_tick' and x['payload']['network_id'] == n['payload']['network_id']
        for n in events if n['event'] == 'r02_network' and n['payload']['kind'] == kind for x in events)
        for kind in ('pool','decision')}
    cost = counter_values(e); require(sum(tick_split.values()) == cost['kernel_ticks'], 'Tick ledger')
    candidate = e['candidate']; assessment = reference(e, obs, world)['assessment']
    proof = None if candidate is None else candidate['decision']['proof']['paths']
    if proof is not None:
        slots = {edge['id']:i for i,edge in enumerate(obs['edges'])}
        for path in proof:
            require(public_path(obs, [slots[i] for i in path]) == path, 'Proof public ID mapping')
    return dict(id=cell['id'], order_id=cell['order_id'], score_id=cell['score_id'], score=cell['score'],
        use_circuits=cell['use_circuits'], slot_to_edge_id=[edge['id'] for edge in obs['edges']],
        observation_digest=codec.observation_from(obs).digest, stop=e['stop'],
        binding_scans=[x['payload'] for x in events if x['event'] == 'r02_binding_scan'],
        pools=networks, selections=selections, selection_edge_ids=selection_ids,
        first_selection=first, first_selection_edge_ids=selection_ids[0] if selection_ids else None,
        proof_edge_id_paths=proof, binding_construct_engaged=engaged if cell['use_circuits'] else None,
        candidate=None if candidate is None else {k:candidate[k] for k in ('decision','diagnostic','readout')},
        measures=candidate_measures(e, True), assessment=assessment, cost=cost, tick_split=tick_split,
        wall_seconds=e['packet']['document']['engine']['pending']['cost']['wall_seconds'])


def collect(out):
    plan = load(out/'plan.json'); require(plan == load(out/'source'/SPEC), 'Frozen design binding')
    parent = out/'parent'; memory, cfg = controls(plan, parent)
    require(sha((out/'source'/plan['world_file']).read_bytes()) == plan['world_sha256'], 'World hash')
    world = load(out/'source'/plan['world_file'])['evaluation']
    require(world == dict(e0=True,e1=True,e2=True,e3=True), 'R077 all-open world, including neutral score0')
    rows = [audit_cell(plan, load(out/'evaluation'/cell['id']/'inference.json'), cell, memory, cfg, world)
        for cell in plan['cells']]
    require(sorted(p.name for p in (out/'evaluation').iterdir()) == sorted(c['id'] for c in plan['cells']), 'Exact 12 evaluation coverage')
    for row in rows:
        location = out/'evaluation'/row['id']/'progress'
        raw = load(out/'evaluation'/row['id']/'inference.json')['execution']
        packets = sorted(location.glob('step-*.json'))
        require(len(packets) == raw['advances']+2 and load(packets[-1]) == raw['packet'], 'Complete progress and final packet')
        for packet in packets:
            _, report = packet_states(load(packet)); require(report['verified'], 'Progress packet replay')
        require((location/'candidate.json').exists() is (raw['candidate'] is not None), 'Progress candidate coverage')
        if raw['candidate'] is not None: require(load(location/'candidate.json') == raw['candidate'], 'Progress candidate binding')
    def ready(r):
        return r['candidate'] is not None and r['stop'] == 'readout_ready' and r['measures']['convergence_status'] != 'budget_exhausted'
    def on_ready(r):
        return (ready(r) and r['binding_construct_engaged'] and r['pools'][0]['stable']
            and r['first_selection'] is not None)
    def verdict(evaluable, condition):
        return 'not_evaluable' if not evaluable else 'supported' if condition else 'falsified'
    indexed = {(r['order_id'],r['score_id'],r['use_circuits']):r for r in rows}
    order_pairs = []
    for score_id in plan['scores']:
        for gate in (True,False):
            a,b = [indexed[o,score_id,gate] for o in plan['orders']]
            complete = all((on_ready if gate else ready)(r) for r in (a,b))
            order_pairs.append(dict(score_id=score_id, use_circuits=gate, evaluable=complete,
                first_selection_id_equal=None if not complete else a['first_selection_edge_ids'] == b['first_selection_edge_ids'],
                proof_id_equal=None if not complete else a['proof_edge_id_paths'] == b['proof_edge_id_paths'],
                candidate_order_by_ids=[[] if not r['pools'] else [c['edge_ids'] for c in r['pools'][0]['candidates']] for r in (a,b)],
                cost_difference_swapped_minus_original={k:b['cost'][k]-a['cost'][k] for k in a['cost']}))
    endpoints = [indexed[order,score,True] for order in plan['orders'] for score in ('s00','s10')]
    evaluable = all(on_ready(r) for r in endpoints)
    expected = plan['predictions']['endpoint_edge_id_paths']
    predictions = dict(
        non_tie_first_selection=verdict(evaluable, all(r['first_selection']['source'] == 'circuit' and r['first_selection_edge_ids'] == expected[r['score_id']] for r in endpoints)),
        non_tie_proof=verdict(evaluable, all(r['proof_edge_id_paths'] == [expected[r['score_id']]] for r in endpoints)))
    ties = [indexed[order,'s06',True] for order in plan['orders']]
    tie_ready = all(on_ready(r) for r in ties)
    equal_activation = tie_ready and all(abs(r['pools'][0]['candidates'][0]['activation']-r['pools'][0]['candidates'][1]['activation']) <= plan['numeric_tolerance'] for r in ties)
    order_flip = tie_ready and ties[0]['pools'][0]['candidates'][0]['edge_ids'] != ties[1]['pools'][0]['candidates'][0]['edge_ids']
    predictions['tie_first_selection'] = verdict(equal_activation, order_flip and all(r['first_selection']['source'] == 'circuit' and r['first_selection_edge_ids'] == r['pools'][0]['candidates'][0]['edge_ids'] for r in ties))
    predictions['tie_proof'] = verdict(equal_activation, order_flip and all(r['proof_edge_id_paths'] == [r['pools'][0]['candidates'][0]['edge_ids']] for r in ties))
    off = [r for r in rows if not r['use_circuits']]; off_ready = all(ready(r) for r in off)
    first_route = {o:ids[:2] for o,ids in plan['orders'].items()}
    predictions['off_first_selection'] = verdict(off_ready, all(r['first_selection'] is not None and r['first_selection']['source'] == 'primitive' and r['first_selection_edge_ids'] == first_route[r['order_id']][:1] for r in off))
    predictions['off_proof'] = verdict(off_ready, all(r['proof_edge_id_paths'] == [first_route[r['order_id']]] for r in off))
    gate_pairs = []
    for order in plan['orders']:
        for score in plan['scores']:
            on,offrow = indexed[order,score,True],indexed[order,score,False]
            gate_pairs.append(dict(order_id=order, score_id=score,
                cost_difference_on_minus_off={k:on['cost'][k]-offrow['cost'][k] for k in on['cost']},
                D_DAG_on=on['measures']['D_DAG'], D_DAG_off=offrow['measures']['D_DAG'],
                adopted_value_equal=on['measures']['adopted_value'] == offrow['measures']['adopted_value']))
    return dict(schema='hcc-r078-summary-v1', rows=rows, order_pairs=order_pairs, gate_pairs=gate_pairs,
        predictions=predictions, tie_activation_equal=equal_activation, native_preparation_executions=0,
        native_evaluation_executions=len(rows), feedback_applications=0, new_independent_samples=0,
        stored_pattern_count=len(memory['circuits']), reused_memory_sha256=plan['memory_sha256'],
        config_sha256=plan['config_sha256'], world_sha256=plan['world_sha256'],
        circuit_id=circuit_id(memory['circuits'][0]), intervention='paired_edge_block_order_only_within_score_gate',
        inhibition_causal_effect='not_isolated', actual_energy_joules=None, peak_memory_bytes=None,
        claim_boundary='One sealed memory, fixed public graph identity, three authored score levels, two array orders. Native executions are not independent discovery samples; no inhibition necessity or general HCC advantage claim.')


def selftest(out):
    plan = load(out/'plan.json'); parent = out/'parent'; memory,cfg = controls(plan,parent)
    # Reanalysis of sealed R077 observations, not a new execution or discovery sample.
    require(parent_collect(parent) == load(parent/'summary.json'), 'Raw-grounded R077 summary')
    for cell in plan['cells']:
        obs = codec.observation_from(cell['observation'])
        scan = scan_patterns(obs, dict(path=[],visited=[obs.start]), memory, cfg, cfg.max_binding_checks)
        require(scan['complete'] and len(scan['matched']) == 2, 'Two complete grammar bindings')
        program,_,meta,_ = pool_network(obs,scan['matched'],memory,cfg)
        require({tuple(public_path(cell['observation'],m['binding']['edge_order'])) for m in meta} == {('e0','e1'),('e2','e3')}, 'Independent slot/ID correspondence')
        require(sum(l['source'].startswith('c:') and l['target'].startswith('c:') for l in program['links']) == 2, 'Two inhibition directions')
    dump(out/'validation/selftest.json', dict(verified=True, native_executions=0, research_sample=False,
        synthetic_native_executions=0, grammar_checks=12, past_native_journals_reanalyzed=9,
        past_observations_are_new_evidence=False, r077_raw_grounding=True, only_edge_order_changes=True))


def main(out, phase):
    for folder, manifest in [('source','source_manifest.json'),('parent','input_manifest.json')]:
        require(files(out/folder) == load(out/manifest)['files'], 'Frozen coverage '+folder)
    if phase == 'selftest': selftest(out)
    else:
        require(files(out/'evaluation') == load(out/'raw_manifest.json')['files'], 'Raw coverage')
        summary = collect(out); plan = load(out/'plan.json'); memory,cfg = controls(plan,out/'parent')
        cell = next(c for c in plan['cells'] if c['id'] == 'swapped-s10-on')
        raw = load(out/'evaluation'/cell['id']/'inference.json')
        rejected = mutation_checks(plan,raw['execution'],cell,memory,True,'frozen_eval','r078-'+cell['id']) if raw['execution']['candidate'] is not None else []
        mutations = {
            'cell_order':lambda x:x['cell']['observation']['edges'].reverse(),
            'pool_activation':lambda x:next(e for e in x['execution']['packet']['document']['events'] if e['event']=='r02_pool_result')['payload']['activations'][0].update(activation=.1),
            'binding_slot':lambda x:next(e for e in x['execution']['packet']['document']['events'] if e['event']=='r02_network' and e['payload']['kind']=='pool')['payload']['metadata']['candidates'][0]['binding'].update(edge_order=[2,1]),
            'candidate_order':lambda x:next(e for e in x['execution']['packet']['document']['events'] if e['event']=='r02_network' and e['payload']['kind']=='pool')['payload']['metadata']['candidates'].reverse(),
        }
        world = load(out/'source'/plan['world_file'])['evaluation']
        for name,mutate in mutations.items():
            bad = deepcopy(raw); mutate(bad)
            bad['execution']['packet']['sha256'] = fingerprint(bad['execution']['packet']['document'])
            try: audit_cell(plan,bad,cell,memory,cfg,world)
            except (ValueError,AssertionError,RuntimeError): rejected.append(name)
            else: raise AssertionError('Undetected raw mutation '+name)
        dump(out/'summary.json',summary)
        dump(out/'verification.json',dict(verified=True, independent_native_replays=12,
            independent_feedback_replays=0, rejected_raw_mutations=rejected,
            max_pool_replay_error=max((p['max_replay_error'] for r in summary['rows'] for p in r['pools']),default=None),
            all_candidate_states_preserved=True, slot_to_edge_id_recomputed=True,
            negative_result_allowed=True, producer_imports=False, independent_researcher=False))
    require(not (FORBIDDEN|{'hcr.activation','hcr.expansion','hcr.learning','tools.r078_binding_order.worker'}) & set(sys.modules), 'Auditor producer boundary')
    print('Independent audit passed:',phase,flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',choices=['selftest','final'],required=True)
    args = p.parse_args(); main(args.out,args.phase)
