"""Independent journal/formula replay; no producer or runtime imports."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from hcr.evaluation.review_audit import packet_states
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require, sha
from tools.r050_review_boundary.audit import FORBIDDEN
from tools.r063_formation.audit import mutation_checks
from tools.r077_equal_binding.audit import collect as parent_collect
from tools.r079_score_readout.audit import audit_cell, stable_true
from tools.r079_score_readout.measure import measurement_selftest, readout_state, proof_support

SPEC = 'experiments/exp-61-small-positive/frozen_spec.json'
SCORES = dict(s00=0., s0005=.005, s001=.01, s002=.02, s003=.03, s004=.04, s005=.05)


def controls(plan, parent):
    previous = load(parent/'plan.json'); memory = load(parent/'memory/3.json')
    require(plan['config'] == previous['config'] and plan['limits'] == previous['limits'], 'R077 config/budget fixed')
    require(fingerprint(plan['config']) == plan['config_sha256'], 'Config hash')
    require(sha((parent/'memory/3.json').read_bytes()) == plan['memory_sha256'], 'Memory hash')
    require(plan['world_file'] == previous['world_file'] and plan['world_sha256'] == previous['world_sha256'], 'World fixed')
    require(plan['scores'] == SCORES and plan['orders'] == dict(swapped=['e2','e3','e0','e1']), 'Frozen grid/order')
    expected = []
    base = next(c for c in previous['cells'] if c['score_id']=='s00' and not c['use_circuits'])
    for sid, score in SCORES.items():
        old = deepcopy(base); edges = {e['id']:e for e in old['observation']['edges']}; edges['e3']['score'] = score
        old['observation']['edges'] = [edges[i] for i in plan['orders']['swapped']]
        old.update(id='swapped-'+sid+'-off',score_id=sid,score=score,order_id='swapped',
                   evidence_role='reproduction' if sid in ('s00','s005') else 'new_score_intervention')
        expected.append(old)
    require(plan['cells'] == expected, 'Only e3 score varies; exact ordered seven cells')
    cfg = codec.adaptive_config_from(plan['config'])
    require(memory['config_signature']==cfg.signature and cfg.kernel.prior_gain==0 and cfg.pattern_lengths==(2,), 'Seed memory signature')
    return memory, cfg


def measure(plan, raw, cell, memory, cfg, world, prefix='r080'):
    row = audit_cell(plan,raw,cell,memory,cfg,world,prefix)
    require(not row['pools'] and row['tick_split']['pool']==0, 'OFF has no pool')
    row.pop('wall_seconds')
    row['pool_metrics'] = None
    row['pool_metrics_applicability'] = 'not_applicable_OFF'
    e = raw['execution']; p = e['packet']['document']['engine']['pending']; c = e['candidate']
    active = p['active_seconds']; finish = None if c is None else c['proof_finish_seconds']
    duration = None if c is None else c['decision']['cost']['wall_seconds']
    require(active>=0 and (finish is None or finish>=0), 'Nonnegative native durations')
    if c is not None: require(abs(duration-active-finish)<1e-12, 'Native/finish duration accounting')
    row['durations'] = dict(native_active_seconds=active,proof_finish_seconds=finish,
        finished_decision_wall_seconds=duration,candidate_capture_seconds=None if c is None else c['capture_seconds'],
        capture_overlaps_finish=True,pending_cost_wall_seconds=p['cost']['wall_seconds'],pending_cost_is_duration=False)
    events = e['packet']['document']['events']
    for n in row['decision_networks']:
        event = events[n['event_index']]['payload']; program = event['program']
        links = program['links']; ancestors = {'goal'}
        while True:
            prior = set(ancestors)
            ancestors.update(l['source'] for l in links if l['target'] in prior and (event['top_down'] or l['kind']!='top_down'))
            if ancestors == prior: break
        ticks = [x['payload'] for x in events if x['event']=='r02_tick' and x['payload']['network_id']==n['network_id']]
        previous = ticks[-2]['state'] if len(ticks)>1 else {g['id']:.5 for g in program['groups']}
        state = n['final_state']
        n.update(program_digest=event['program_digest'],drives=event['drives'],goal_dependency_group_ids=sorted(ancestors),
                 e3_slot='e:1',e3_goal_connected='e:1' in ancestors,
                 link_terms=[dict(source=l['source'],target=l['target'],kind=l['kind'],weight=l['weight'],
                     last_tick_centered_link_input=l['weight']*(2*previous[l['source']]-1),
                     terminal_centered_link_term=l['weight']*(2*state[l['source']]-1),
                     terminal_uncentered_activation_product=l['weight']*state[l['source']]) for l in links])
        require(event['drives']['e:1']==4*cell['score'] and n['e3_goal_connected'], 'Score mapped to goal-connected public e3')
    row['first_state_measurement'] = 'measurement_failure' if row['first_decision'] is None else row['first_decision']['category']
    row['session_budget_termination'] = e['stop']=='external_compute_budget'
    return row


def stable_evaluable(row):
    n = row['first_decision']
    return n is not None and n['category'] in ('stable_true','stable_false','stable_ambiguous')


def stable_witness(row):
    n = row['first_decision']
    return stable_evaluable(row) and n['category'] in ('stable_false','stable_ambiguous') and not n['ready'] and n['progress_mismatch_kind'] in ('negative_requires_dependency_coverage','unresolved_or_no_goal_candidate')


def classify(rows):
    positive = [r for r in rows if r['score']>0]; new = [r for r in positive if r['evidence_role']=='new_score_intervention']
    counter = [r['id'] for r in positive if stable_witness(r)]
    missing = [r['id'] for r in positive if not stable_evaluable(r)]
    witnesses = [r['id'] for r in new if stable_witness(r)]
    new_missing = [r['id'] for r in new if not stable_evaluable(r)]
    # Observed nonstable states are evidence for the separate stability prediction,
    # never False/ambiguous witnesses for the stable-state alternative test.
    boundary = [r['id'] for r in new if r['first_decision'] is not None and r['first_decision']['category'] in ('budget_exhausted','oscillating')]
    absent = [r['id'] for r in new if r['first_decision'] is None]
    return dict(positive_grid_stable_true=dict(verdict='falsified' if counter else 'not_evaluable' if missing else 'supported',
        counterexamples=counter,not_evaluable=missing),
        small_positive_nontrue_exists=dict(verdict='supported' if witnesses else 'not_evaluable' if new_missing else 'falsified',witnesses=witnesses,not_evaluable=new_missing),
        small_positive_stability_boundary_exists=dict(verdict='supported' if boundary else 'not_evaluable' if absent else 'falsified',witnesses=boundary,not_evaluable=absent))


def collect(out):
    plan = load(out/'plan.json'); require(plan==load(out/'source'/SPEC), 'Frozen design binding')
    memory,cfg = controls(plan,out/'parent'); world = load(out/'source'/plan['world_file'])['evaluation']
    require(sha((out/'source'/plan['world_file']).read_bytes())==plan['world_sha256'] and world==dict(e0=True,e1=True,e2=True,e3=True), 'Authored world')
    rows=[];repeats=[]
    for cell in plan['cells']:
        raw=load(out/'evaluation'/cell['id']/'inference.json');e=raw['execution']
        row=measure(plan,raw,cell,memory,cfg,world);rows.append(row)
        packets=sorted((out/'evaluation'/cell['id']/'progress').glob('step-*.json'))
        require(len(packets)==e['advances']+2 and load(packets[-1])==e['packet'], 'Complete progressive packets')
        for packet in packets: require(packet_states(load(packet))[1]['verified'], 'Progressive independent replay')
        candidate=out/'evaluation'/cell['id']/'progress/candidate.json'
        require(candidate.exists() is (e['candidate'] is not None), 'Candidate coverage')
        if e['candidate'] is not None: require(load(candidate)==e['candidate'], 'Candidate bytes')
        if cell['evidence_role']=='reproduction':
            old=load(out/'repeat/evaluation'/cell['id']/'inference.json')
            oldrow=measure(plan,old,old['cell'],memory,cfg,world,'r079')
            require({k:v for k,v in cell.items() if k!='evidence_role'}=={k:v for k,v in old['cell'].items() if k!='evidence_role'}, 'Exact endpoint input')
            require(e['packet']['document']['events']==old['execution']['packet']['document']['events'], 'Endpoint journal equality')
            for key in ('final_support','cost','tick_split','raw_value'): require(row[key]==oldrow[key], 'Endpoint reproduction '+key)
            repeats.append(dict(id=cell['id'],input_equal=True,journal_events_equal=True,final_support_equal=True,integer_cost_equal=True))
    require(sorted(p.name for p in (out/'evaluation').iterdir())==sorted(c['id'] for c in plan['cells']), 'Exact seven-cell coverage')
    brackets=[dict(lower=a['score'],upper=b['score'],lower_category=a['first_state_measurement'],upper_category=b['first_state_measurement'],
        interpretation='adjacent observed categories only; no precise threshold or continuum monotonicity') for a,b in zip(rows,rows[1:]) if a['first_state_measurement']!=b['first_state_measurement']]
    return dict(schema='hcc-r080-summary-v1',rows=rows,predictions=classify(rows),reproduction_checks=repeats,
        observed_adjacent_category_changes=brackets,native_evaluation_executions=7,reproduction_executions=2,new_score_intervention_executions=5,
        primary_stable_alternative_tests=1,stability_boundary_test_separate=True,native_training_executions=0,feedback_applications=0,new_independent_samples=0,
        actual_energy_joules=None,peak_memory_bytes=None,claim_boundary=plan['claim_boundary'])


def selftest(out):
    plan=load(out/'plan.json');memory,cfg=controls(plan,out/'parent')
    require(parent_collect(out/'parent')==load(out/'parent/summary.json'), 'R077 raw grounding')
    world=load(out/'source'/plan['world_file'])['evaluation']
    for cell in plan['cells']:
        require(codec.observation_from(cell['observation']).digest is not None, 'Input grammar')
        if cell['evidence_role']=='reproduction':
            raw=load(out/'repeat/evaluation'/cell['id']/'inference.json');measure(plan,raw,raw['cell'],memory,cfg,world,'r079')
    for status in ('budget_exhausted','oscillating'):
        r=readout_state(status,.8,False);require(r['candidate_value'] is None and not r['ready'] and r['category']==status, 'Nonstable is not False')
    fake=dict(id='synthetic',score=.005,evidence_role='new_score_intervention',first_decision=dict(category='budget_exhausted'))
    verdict=classify([fake]);require(verdict['positive_grid_stable_true']['verdict']=='not_evaluable' and verdict['small_positive_nontrue_exists']['verdict']=='not_evaluable' and verdict['small_positive_stability_boundary_exists']['verdict']=='supported', 'Budget prediction separation')
    dump(out/'validation/selftest.json',dict(verified=True,**measurement_selftest(),nonstable_cases=2,prediction_budget_case=1,
        grammar_checks=7,prior_native_journals_reanalyzed=11,new_native_executions=0,research_sample=False))


def raw_mutations(out):
    plan=load(out/'plan.json');memory,cfg=controls(plan,out/'parent');world=load(out/'source'/plan['world_file'])['evaluation']
    cell=plan['cells'][0];raw=load(out/'evaluation'/cell['id']/'inference.json')
    rejected=mutation_checks(plan,raw['execution'],cell,memory,False,'frozen_eval','r080-'+cell['id'])
    def settled(x): return next(e['payload'] for e in x['execution']['packet']['document']['events'] if e['event']=='r02_settled')
    def progress(x): return next(e['payload'] for e in x['execution']['packet']['document']['events'] if e['event']=='r02_progress' and e['payload']['network_id'] is not None)
    mutations=dict(first_status=lambda x:settled(x)['convergence'].update(status='stable_ambiguous'),
        first_goal=lambda x:settled(x)['state'].update(goal=.5),progress_reason=lambda x:progress(x)['mismatch'].update(kind='unresolved_or_no_goal_candidate'),
        progress_network=lambda x:progress(x).update(network_id=None),coverage=lambda x:progress(x).update(graph_complete=True),
        cell_score=lambda x:next(e for e in x['cell']['observation']['edges'] if e['id']=='e3').update(score=.05))
    for name,mutate in mutations.items():
        bad=deepcopy(raw);mutate(bad);bad['execution']['packet']['sha256']=fingerprint(bad['execution']['packet']['document'])
        try: measure(plan,bad,cell,memory,cfg,world)
        except (ValueError,AssertionError,RuntimeError): rejected.append(name)
        else: raise AssertionError('Undetected raw mutation '+name)
    decision=deepcopy(raw['execution']['candidate']['decision']);decision['_slot_to_edge_id']=[e['id'] for e in cell['observation']['edges']]
    for name,mutate in dict(final_reference=lambda x:x['proof'].update(final='invented'),final_depth=lambda x:x['proof'].update(primitive_depth=99)).items():
        bad=deepcopy(decision);mutate(bad)
        try: proof_support(bad)
        except ValueError: rejected.append(name)
        else: raise AssertionError('Undetected proof mutation '+name)
    return rejected


def main(out,phase):
    for folder,manifest in [('source','source_manifest.json'),('parent','input_manifest.json'),('repeat','repeat_manifest.json')]:
        require(files(out/folder)==load(out/manifest)['files'], 'Frozen coverage '+folder)
    if phase=='selftest': selftest(out)
    else:
        require(files(out/'evaluation')==load(out/'raw_manifest.json')['files'], 'Raw coverage')
        summary=collect(out);rejected=raw_mutations(out);dump(out/'summary.json',summary)
        dump(out/'verification.json',dict(verified=True,independent_native_journals_replayed=7,prior_reproduction_journals_replayed=2,
            rejected_raw_mutations=rejected,first_network_and_advance_bound=True,final_ancestry_recomputed=True,
            producer_imports=False,independent_researcher=False,new_native_executions=0))
    require(not (FORBIDDEN|{'hcr.activation','hcr.expansion','hcr.learning','tools.r080_small_positive.worker'})&set(sys.modules), 'Auditor producer boundary')
    print('Independent audit passed:',phase,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--phase',choices=['selftest','final'],required=True)
    a=p.parse_args();main(a.out,a.phase)
