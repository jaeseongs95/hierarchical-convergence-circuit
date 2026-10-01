"""Independent raw replay; no producer/runtime/selector execution or summaries as input."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from hcr.evaluation.adaptive_audit_support import scan_patterns, pool_network
from hcr.evaluation.review_audit import packet_states
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require, sha
from tools.r050_review_boundary.audit import FORBIDDEN, candidate_measures, counter_values
from tools.r063_formation.audit import verify_execution, mutation_checks
from tools.r064_retention.audit import reference
from tools.r076_competition.audit import pools
from tools.r077_equal_binding.audit import collect as parent_collect
from tools.r078_binding_order.audit import public_path
from .measure import decision_networks, proof_support, measurement_selftest

SPEC = 'experiments/exp-60-score-readout/frozen_spec.json'


def controls(plan, parent):
    previous = load(parent/'plan.json'); memory = load(parent/'memory/3.json')
    require(plan['config'] == previous['config'] and plan['limits'] == previous['limits'], 'R077 config/budget fixed')
    require(fingerprint(plan['config']) == plan['config_sha256'], 'Config hash')
    require(sha((parent/'memory/3.json').read_bytes()) == plan['memory_sha256'], 'Memory hash')
    require(plan['world_file'] == previous['world_file'] and plan['world_sha256'] == previous['world_sha256'], 'World fixed')
    require(plan['scores'] == dict(s00=0.,s005=.05,s02=.2,s04=.4,s06=.6), 'Frozen score grid')
    require(plan['orders'] == dict(original=['e0','e1','e2','e3'],swapped=['e2','e3','e0','e1']), 'Fixed orders')
    expected = []
    for order, ids in plan['orders'].items():
        for sid, score in plan['scores'].items():
            for gate in (True,False):
                old = deepcopy(next(c for c in previous['cells'] if c['score_id']=='s00' and c['use_circuits']==gate))
                edges = {e['id']:e for e in old['observation']['edges']}; edges['e3']['score'] = score
                old['observation']['edges'] = [edges[i] for i in ids]
                old.update(id=order+'-'+sid+('-on' if gate else '-off'),score_id=sid,score=score,order_id=order,
                    evidence_role='reproduction' if sid in ('s00','s06') else 'new_score_intervention')
                expected.append(old)
    # Canonical plan serialization sorts dict keys; cell order is an explicit list.
    require(sorted(plan['cells'],key=lambda c:c['id']) == sorted(expected,key=lambda c:c['id']), 'Only e3 score varies')
    require(len(plan['cells']) == 20 and len({c['id'] for c in plan['cells']}) == 20, 'Exact matrix')
    cfg = codec.adaptive_config_from(plan['config'])
    require(memory['config_signature'] == cfg.signature and cfg.kernel.prior_gain == 0 and cfg.pattern_lengths == (2,), 'Prior/length/memory signature')
    return memory,cfg


def audit_cell(plan, raw, cell, memory, cfg, world, prefix='r079'):
    require(raw['cell'] == cell, 'Raw input cell identity')
    e = raw['execution']; obs = cell['observation']
    states = verify_execution(plan,e,cell,memory,cell['use_circuits'],'frozen_eval',prefix+'-'+cell['id'])
    events = e['packet']['document']['events']; pool_rows = pools(e,obs,memory,cfg)
    for pool in pool_rows:
        for c in pool['candidates']:
            c['edge_ids'] = public_path(obs,c['edges'])
            require(c['prior'] == 0 and c['mismatch'] == 0, 'Zero prior/mismatch')
        activations = [c['activation'] for c in pool['candidates']]
        pool['candidate_activation_gap'] = max(activations)-min(activations) if len(activations)>=2 else None
        pool['first_minus_second_activation'] = activations[0]-activations[1] if len(activations)==2 else None
        pool['goal_margin'] = abs(2*pool['final_state']['goal']-1)
        pool['candidate_tie'] = pool['candidate_activation_gap'] <= plan['numeric_tolerance'] if len(activations)==2 else None
    decisions = decision_networks(e,states,obs)
    selections = [x['payload']['candidate'] for x in events if x['event']=='r02_expansion']
    selected_paths = [public_path(obs,c['edges']) for c in selections]
    candidate = e['candidate']; support = None
    if candidate is not None:
        support = proof_support(dict(candidate['decision'],_slot_to_edge_id=[x['id'] for x in obs['edges']]))
    split = {kind:sum(x['payload']['convergence']['ticks'] for x in events if x['event']=='r02_settled'
        and x['payload']['network_id'] in {n['payload']['network_id'] for n in events if n['event']=='r02_network' and n['payload']['kind']==kind}) for kind in ('pool','decision')}
    cost = counter_values(e); require(sum(split.values()) == cost['kernel_ticks'], 'Separated tick ledger')
    return dict(id=cell['id'],order_id=cell['order_id'],score_id=cell['score_id'],score=cell['score'],
        use_circuits=cell['use_circuits'],evidence_role=cell.get('evidence_role','parent_observation'),
        construct_role=('pool_selection_control' if cell['use_circuits'] else
                        'score_readout_probe' if cell['order_id']=='swapped' else 'invariance_control'),
        observation_digest=codec.observation_from(obs).digest,slot_to_edge_id=[x['id'] for x in obs['edges']],
        measurement_status='measured' if decisions else 'no_decision_network',first_decision=decisions[0] if decisions else None,
        decision_networks=decisions,progress_events=[x for x in events if x['event']=='r02_progress'],
        binding_scans=[x['payload'] for x in events if x['event']=='r02_binding_scan'],pools=pool_rows,
        selections=selections,selection_edge_ids=selected_paths,first_selection_edge_ids=selected_paths[0] if selected_paths else None,
        final_support=support,raw_value=None if candidate is None else candidate['decision']['value'],
        readout=None if candidate is None else candidate['readout'],
        diagnostic=None if candidate is None else candidate['diagnostic'],
        measures=candidate_measures(e,True),assessment=reference(e,obs,world)['assessment'],
        cost=cost,tick_split=split,advances=e['advances'],stop=e['stop'],
        wall_seconds=e['packet']['document']['engine']['pending']['cost']['wall_seconds'])


def stable_evaluable(row):
    n = row['first_decision']
    return n is not None and n['convergence']['status'] in ('stable_decision','stable_ambiguous')


def stable_true(row):
    n = row['first_decision']
    return n is not None and n['category']=='stable_true' and n['ready'] and n['progress_mismatch_kind'] is None


def universal(rows, predicate, evaluable=stable_evaluable):
    failures = [r['id'] for r in rows if evaluable(r) and not predicate(r)]
    missing = [r['id'] for r in rows if not evaluable(r)]
    return dict(verdict='falsified' if failures else 'not_evaluable' if missing else 'supported',counterexamples=failures,not_evaluable=missing)


def collect(out):
    plan = load(out/'plan.json'); require(plan == load(out/'source'/SPEC), 'Frozen design binding')
    memory,cfg = controls(plan,out/'parent')
    require(sha((out/'source'/plan['world_file']).read_bytes()) == plan['world_sha256'], 'World hash')
    world = load(out/'source'/plan['world_file'])['evaluation']
    require(world == dict(e0=True,e1=True,e2=True,e3=True), 'Fixed authored world')
    rows=[]; repeats=[]
    for cell in plan['cells']:
        raw = load(out/'evaluation'/cell['id']/'inference.json')
        row = audit_cell(plan,raw,cell,memory,cfg,world); rows.append(row)
        location = out/'evaluation'/cell['id']/'progress'; e=raw['execution']
        packets=sorted(location.glob('step-*.json'))
        require(len(packets)==e['advances']+2 and load(packets[-1])==e['packet'], 'Complete progressive snapshots')
        for packet in packets:
            _,report=packet_states(load(packet));require(report['verified'],'Independent progressive replay')
        require((location/'candidate.json').exists() is (e['candidate'] is not None),'Candidate coverage')
        if e['candidate'] is not None: require(load(location/'candidate.json')==e['candidate'],'Candidate bytes')
        if cell['evidence_role']=='reproduction':
            old=load(out/'repeat/evaluation'/cell['id']/'inference.json')
            oldrow=audit_cell(plan,old,old['cell'],memory,cfg,world,'r078')
            require({k:v for k,v in cell.items() if k!='evidence_role'}==old['cell'],'Exact reproduction input')
            require(e['packet']['document']['events']==old['execution']['packet']['document']['events'],'Deterministic native journal reproduction')
            for key in ('final_support','cost','tick_split','first_selection_edge_ids','raw_value'):
                require(row[key]==oldrow[key],'Deterministic reproduction '+key)
            repeats.append(dict(id=cell['id'],input_equal=True,journal_events_equal=True,final_support_equal=True,integer_cost_equal=True))
    require(sorted(p.name for p in (out/'evaluation').iterdir())==sorted(c['id'] for c in plan['cells']),'Exact 20-cell coverage')
    off=[r for r in rows if r['order_id']=='swapped' and not r['use_circuits']]
    positive=[r for r in off if r['score']>0]; new=[r for r in positive if r['evidence_role']=='new_score_intervention']
    witnesses=[r['id'] for r in new if stable_evaluable(r) and not r['first_decision']['ready'] and r['first_decision']['category'] in ('stable_false','stable_ambiguous')]
    missing=[r['id'] for r in new if not stable_evaluable(r)]
    predictions=dict(positive_sign_suffices=universal(positive,stable_true),
        positive_subthreshold_exists=dict(verdict='supported' if witnesses else 'not_evaluable' if missing else 'falsified',witnesses=witnesses,not_evaluable=missing),
        original_off_stable_true=universal([r for r in rows if r['order_id']=='original' and not r['use_circuits']],stable_true),
        on_stable_true=universal([r for r in rows if r['use_circuits']],stable_true))
    def on_evaluable(r):
        if not r['pools'] or not r['pools'][0]['stable'] or len(r['pools'][0]['candidates'])!=2:return False
        c=r['pools'][0]['candidates']
        return all(x['goal_binding'] and len(x['edges'])==2 for x in c) and (r['score']!=.6 or r['pools'][0]['candidate_tie'])
    predictions['on_public_selection']=universal([r for r in rows if r['use_circuits']],
        lambda r:r['first_selection_edge_ids']==(['e0','e1'] if r['score']<.6 else r['pools'][0]['candidates'][0]['edge_ids']),on_evaluable)
    indexed={(r['order_id'],r['score_id'],r['use_circuits']):r for r in rows}
    gate_pairs=[]
    for order in plan['orders']:
        for sid in plan['scores']:
            a,b=indexed[order,sid,True],indexed[order,sid,False]
            gate_pairs.append(dict(order_id=order,score_id=sid,cost_difference_on_minus_off={k:a['cost'][k]-b['cost'][k] for k in a['cost']},
                first_categories=[a['first_decision']['category'] if a['first_decision'] else None,b['first_decision']['category'] if b['first_decision'] else None],
                D_DAG_on=a['measures']['D_DAG'],D_DAG_off=b['measures']['D_DAG']))
    ordered=sorted(off,key=lambda r:r['score'])
    brackets=[dict(lower=a['score'],upper=b['score'],lower_category=a['first_decision']['category'],upper_category=b['first_decision']['category'],
        interpretation='adjacent observed score states only; no precise threshold or continuum monotonicity') for a,b in zip(ordered,ordered[1:])
        if stable_evaluable(a) and stable_evaluable(b) and a['first_decision']['category']!=b['first_decision']['category']]
    return dict(schema='hcc-r079-summary-v1',rows=rows,predictions=predictions,reproduction_checks=repeats,
        observed_adjacent_category_changes=brackets,gate_pairs=gate_pairs,
        native_evaluation_executions=20,reproduction_executions=8,new_score_intervention_executions=12,
        new_primary_score_readout_cells=3,new_invariance_control_cells=3,new_pool_selection_control_cells=6,
        primary_alternative_tests=1,
        native_training_executions=0,feedback_applications=0,new_independent_samples=0,
        reused_memory_sha256=plan['memory_sha256'],config_sha256=plan['config_sha256'],world_sha256=plan['world_sha256'],
        inhibition_causal_effect='not_isolated',readout_gate_necessity='not_isolated',
        actual_energy_joules=None,peak_memory_bytes=None,claim_boundary=plan['claim_boundary'])


def selftest(out):
    plan=load(out/'plan.json'); memory,cfg=controls(plan,out/'parent')
    require(parent_collect(out/'parent')==load(out/'parent/summary.json'),'R077 raw grounding')
    for cell in plan['cells']:
        obs=codec.observation_from(cell['observation'])
        scan=scan_patterns(obs,dict(path=[],visited=[obs.start]),memory,cfg,cfg.max_binding_checks)
        require(scan['complete'] and len(scan['matched'])==2,'Two complete bindings')
        program,_,meta,_=pool_network(obs,scan['matched'],memory,cfg)
        require({tuple(public_path(cell['observation'],m['binding']['edge_order'])) for m in meta}=={('e0','e1'),('e2','e3')},'Public binding paths')
        require(sum(l['source'].startswith('c:') and l['target'].startswith('c:') for l in program['links'])==2,'Two inhibition directions')
    world=load(out/'source'/plan['world_file'])['evaluation']
    for cell in plan['cells']:
        if cell['evidence_role']=='reproduction':
            raw=load(out/'repeat/evaluation'/cell['id']/'inference.json')
            audit_cell(plan,raw,raw['cell'],memory,cfg,world,'r078')
    dump(out/'validation/selftest.json',dict(verified=True,**measurement_selftest(),grammar_checks=20,
        prior_native_journals_reanalyzed=17,past_observations_are_new_evidence=False,new_native_executions=0))


def raw_mutations(out,summary):
    plan=load(out/'plan.json');memory,cfg=controls(plan,out/'parent');world=load(out/'source'/plan['world_file'])['evaluation']
    cell=next(c for c in plan['cells'] if c['id']=='swapped-s06-on');raw=load(out/'evaluation'/cell['id']/'inference.json')
    rejected=mutation_checks(plan,raw['execution'],cell,memory,True,'frozen_eval','r079-'+cell['id'])
    cell=next(c for c in plan['cells'] if c['id']=='swapped-s00-off');raw=load(out/'evaluation'/cell['id']/'inference.json')
    def first_settled(x):return next(e['payload'] for e in x['execution']['packet']['document']['events'] if e['event']=='r02_settled')
    def negative_progress(x):return next(e['payload'] for e in x['execution']['packet']['document']['events'] if e['event']=='r02_progress' and e['payload']['network_id'] is not None)
    mutations={
        'first_status':lambda x:first_settled(x)['convergence'].update(status='stable_ambiguous'),
        'first_goal':lambda x:first_settled(x)['state'].update(goal=.5),
        'first_margin':lambda x:first_settled(x)['convergence'].update(margin=0),
        'progress_reason':lambda x:negative_progress(x)['mismatch'].update(kind='unresolved_or_no_goal_candidate'),
        'progress_network':lambda x:negative_progress(x).update(network_id=None),
        'coverage':lambda x:negative_progress(x).update(graph_complete=True),
        'cell_score':lambda x:next(e for e in x['cell']['observation']['edges'] if e['id']=='e3').update(score=.05),
    }
    for name,mutate in mutations.items():
        bad=deepcopy(raw);mutate(bad);bad['execution']['packet']['sha256']=fingerprint(bad['execution']['packet']['document'])
        try:audit_cell(plan,bad,cell,memory,cfg,world)
        except (ValueError,AssertionError,RuntimeError):rejected.append(name)
        else:raise AssertionError('Undetected raw mutation '+name)
    decision=deepcopy(raw['execution']['candidate']['decision']);decision['_slot_to_edge_id']=[e['id'] for e in cell['observation']['edges']]
    final=decision['proof']['final']
    proof_mutations={
        'final_reference':lambda x:x['proof'].update(final='invented'),
        'final_path_index':lambda x:next(n for n in x['proof']['nodes'] if n['id']==final).update(path_index=0),
        'final_parent':lambda x:next(n for n in x['proof']['nodes'] if n['id']==final).update(parents=['invented']),
        'final_depth':lambda x:x['proof'].update(primitive_depth=99)}
    for name,mutate in proof_mutations.items():
        bad=deepcopy(decision);mutate(bad)
        try:proof_support(bad)
        except ValueError:rejected.append(name)
        else:raise AssertionError('Undetected ancestry mutation '+name)
    return rejected


def main(out,phase):
    for folder,manifest in [('source','source_manifest.json'),('parent','input_manifest.json'),('repeat','repeat_manifest.json')]:
        require(files(out/folder)==load(out/manifest)['files'],'Frozen coverage '+folder)
    if phase=='selftest':selftest(out)
    else:
        require(files(out/'evaluation')==load(out/'raw_manifest.json')['files'],'Raw coverage')
        summary=collect(out);rejected=raw_mutations(out,summary)
        dump(out/'summary.json',summary)
        dump(out/'verification.json',dict(verified=True,independent_native_journals_replayed=20,
            prior_reproduction_journals_replayed=8,independent_feedback_replays=0,rejected_raw_mutations=rejected,
            max_pool_replay_error=max((p['max_replay_error'] for r in summary['rows'] for p in r['pools']),default=None),
            first_network_and_advance_bound=True,final_ancestry_recomputed=True,producer_imports=False,
            independent_researcher=False,new_native_executions=0))
    require(not (FORBIDDEN|{'hcr.activation','hcr.expansion','hcr.learning','tools.r079_score_readout.worker'})&set(sys.modules),'Auditor producer boundary')
    print('Independent audit passed:',phase,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',choices=['selftest','final'],required=True);a=p.parse_args();main(a.out,a.phase)
