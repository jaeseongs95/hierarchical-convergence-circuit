"""Independent native journal, feedback and multi-candidate equation replay."""
import argparse
from pathlib import Path
import sys
from hcr import codec
from hcr.evaluation.audit import independent_step
from hcr.evaluation.adaptive_audit_support import chain_program, pool_network, scan_patterns, circuit_id
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require, sha
from tools.r050_review_boundary.audit import FORBIDDEN, candidate_measures, counter_values
from tools.r063_formation.audit import verify_execution, mutation_checks
from tools.r064_retention.audit import reference, check_learning

SPEC = 'experiments/exp-57-native-competition/frozen_spec.json'


def recipe_reference(out, step):
    plan = load(out/'plan.json'); case = plan['training'][step-1]
    e = load(out/'training'/str(step)/'inference.json')
    verify_execution(plan, e, case, load(out/'memory'/f'{step-1}.json'), True,
                     'train', 'r076-train-'+case['id'])
    world = load(out/'source'/plan['world_file'])['training'][case['id']]
    return reference(e, case['observation'], world)


def pools(execution, observation, memory, cfg):
    events = execution['packet']['document']['events']; obs = codec.observation_from(observation)
    result = []
    for event in events:
        if event['event'] != 'r02_network' or event['payload']['kind'] != 'pool':
            continue
        n = event['payload']; nid = n['network_id']; meta = n['metadata']['candidates']
        records = [dict(circuit_id=c['circuit_id'], binding=c['binding']) for c in meta]
        program, drives, expected_meta, _ = pool_network(obs, records, memory, cfg)
        require((n['program'], n['drives'], meta) == (program, drives, expected_meta), 'Pool grammar/drives/bindings')
        state = {g['id']: .5 for g in program['groups']}; error = 0.0
        ticks = [x['payload'] for x in events if x['event']=='r02_tick' and x['payload']['network_id']==nid]
        for tick in ticks:
            state = independent_step(program, state, drives, cfg.kernel, n['top_down'])
            error = max(error, max(abs(state[k]-tick['state'][k]) for k in state))
            require(error <= 2e-12, 'Multi-candidate recurrence')
        settled = next(x['payload'] for x in events if x['event']=='r02_settled' and x['payload']['network_id']==nid)
        require(max(abs(state[k]-settled['state'][k]) for k in state) <= 2e-12, 'Pool final state')
        actual = next(x['payload']['activations'] for x in events if x['event']=='r02_pool_result' and x['payload']['network_id']==nid)
        stable = settled['convergence']['status'] in ('stable_decision', 'stable_ambiguous')
        require(len(actual)==len(meta), 'All candidate readouts')
        candidates = []
        for i, (a, m) in enumerate(zip(actual, meta)):
            activation = state['c:'+str(i)]
            eligible = stable and activation >= cfg.activation_threshold and m['mismatch'] <= cfg.mismatch_threshold
            require({k:a[k] for k in m}==m and abs(a['activation']-activation)<=2e-12 and a['eligible'] is eligible,
                    'Candidate activation/eligibility')
            slots = m['binding']['edge_order']
            incoming = [x for x in program['links'] if x['target']=='c:'+str(i) and x['source'].startswith('c:')]
            require(len(incoming)==len(meta)-1 and all(x['weight']==-cfg.circuit_inhibition for x in incoming), 'Pairwise inhibition')
            candidates.append(dict(index=i, **a, edges=slots, goal_binding=obs.edges[slots[-1]].target==obs.goal,
                inhibition_inputs=[dict(source=x['source'],weight=x['weight'],final_signed_input=x['weight']*state[x['source']]) for x in incoming]))
        result.append(dict(network_id=nid, prefix=n['metadata']['prefix'], candidates=candidates,
            program_sha256=fingerprint(program), drives=drives, final_state=state,
            convergence=settled['convergence'], ticks=len(ticks), max_replay_error=error,
            inhibition_edge_count=len(meta)*(len(meta)-1), stable=stable))
    return result


def collect(out):
    plan = load(out/'plan.json'); cfg = codec.adaptive_config_from(plan['config'])
    require(plan==load(out/'source'/SPEC), 'Frozen design binding')
    require(sha((out/'source'/plan['world_file']).read_bytes())==plan['world_sha256'], 'Frozen independent world')
    world = load(out/'source'/plan['world_file']); formation=[]
    empty=load(out/'memory/0.json')
    require(empty==dict(schema='hcr-memory-r02',config_signature=cfg.signature,version=0,
        circuits=[],pending=[],consumed_feedback=[],patches=[]), 'Native empty memory')
    for step, case in enumerate(plan['training'], 1):
        base=out/'training'/str(step); e=load(base/'inference.json'); expected=recipe_reference(out,step)
        require(load(base/'reference.json')==expected, 'Reference feedback exact binding')
        before=load(out/'memory'/f'{step-1}.json'); after=load(out/'memory'/f'{step}.json')
        learn=load(base/'learning.json'); check_learning(e,expected,learn,before,after)
        formation.append(dict(step=step, assessment=expected['assessment'], patch=learn['patch'],
            compiled_lengths=[len(c['pattern']['relations']) for c in after['circuits']],
            pending_lengths=[len(c['pattern']['relations']) for c in after['pending']]))
    memory=load(out/'memory'/f"{len(plan['training'])}.json")
    circuit_states=[dict(id=circuit_id(c),length=len(c['pattern']['relations']),strength=c['strength'],
        version=c['version'],failures=c['failures'],active=c['active'],episodes=c['evidence_episodes']) for c in memory['circuits']]
    formed=sorted(c['length'] for c in circuit_states)==[2,3] and all(c['active'] for c in circuit_states)
    rows=[]
    for cell in plan['cells']:
        raw=load(out/'evaluation'/cell['id']/'inference.json'); require(raw['cell']==cell,'Cell identity')
        e=raw['execution']; verify_execution(plan,e,cell,memory,cell['use_circuits'],'frozen_eval','r076-'+cell['id'])
        events=e['packet']['document']['events']; networks=pools(e,cell['observation'],memory,cfg)
        selections=[x['payload']['candidate'] for x in events if x['event']=='r02_expansion']
        scans=[x['payload'] for x in events if x['event']=='r02_binding_scan']
        tick_split={kind:sum(x['event']=='r02_tick' and x['payload']['network_id']==n['payload']['network_id']
            for n in events if n['event']=='r02_network' and n['payload']['kind']==kind for x in events) for kind in ('pool','decision')}
        cost=counter_values(e); require(sum(tick_split.values())==cost['kernel_ticks'],'Separate tick ledger')
        c=e['candidate']; ref=reference(e,cell['observation'],world['evaluation'])
        goal_candidates=[] if not networks else [a for a in networks[0]['candidates'] if a['goal_binding']]
        engaged=formed and len(goal_candidates)==2 and len({a['circuit_id'] for a in goal_candidates})==2
        rows.append(dict(id=cell['id'],score=cell['score'],use_circuits=cell['use_circuits'],
            stop=e['stop'],binding_scans=scans,pools=networks,selections=selections,
            first_selection=selections[0] if selections else None,
            competition_construct_engaged=engaged if cell['use_circuits'] else None,
            candidate=None if c is None else {k:c[k] for k in ('decision','diagnostic','readout')},
            measures=candidate_measures(e,True),cost=cost,tick_split=tick_split,assessment=ref['assessment'],
            wall_seconds=e['packet']['document']['engine']['pending']['cost']['wall_seconds']))
    pairs=[]
    for score_id in plan['scores']:
        on,off=[next(r for r in rows if r['id']==score_id+'-'+gate) for gate in ('on','off')]
        complete=on['candidate'] is not None and off['candidate'] is not None
        pairs.append(dict(score_id=score_id,evaluable=complete,
            first_selection_equal=None if not complete else on['first_selection']==off['first_selection'],
            D_DAG_on=on['measures']['D_DAG'],D_DAG_off=off['measures']['D_DAG'],
            raw_value_equal=None if not complete else on['measures']['raw_decision']==off['measures']['raw_decision'],
            adopted_value_equal=None if not complete else on['measures']['adopted_value']==off['measures']['adopted_value'],
            cost_difference_on_minus_off={k:on['cost'][k]-off['cost'][k] for k in on['cost']}))
    on=[r for r in rows if r['use_circuits']]
    evaluable=all(r['competition_construct_engaged'] and r['first_selection'] is not None and r['pools'][0]['stable'] for r in on)
    choices={(r['first_selection']['source'],tuple(r['first_selection']['edges']),r['first_selection']['circuit_id']) for r in on if r['first_selection'] is not None}
    return dict(schema='hcc-r076-summary-v1',formation=formation,circuit_states=circuit_states,
        formation_construct_engaged=formed,rows=rows,pairs=pairs,
        score_selection_prediction='not_evaluable' if not evaluable else 'supported' if len(choices)>1 else 'falsified',
        first_selection_switch_observed=None if not evaluable else len(choices)>1,
        intervention='joint_public_score_evidence_uncertainty_prior_and_negative_mismatch',
        native_preparation_executions=3,native_evaluation_executions=8,
        feedback_applications=sum(x['patch'] is not None for x in formation),new_independent_samples=0,
        inhibition_causal_effect='not_isolated',actual_energy_joules=None,peak_memory_bytes=None,
        claim_boundary='Authored deterministic multi-pattern native mechanism probe; prefix candidates retained; no pure evidence effect, inhibition necessity, general performance or learning advantage claim.')


def selftest(out):
    plan=load(out/'plan.json');cfg=codec.adaptive_config_from(plan['config'])
    obs=codec.observation_from(plan['cells'][0]['observation'])
    # Separate synthetic grammar check; never inserted into a native memory.
    memory=dict(circuits=[dict(pattern=dict(relations=[{}]*n,program=chain_program(n,[list(range(n))],cfg.kernel)),
        evidence_episodes=['synthetic-1','synthetic-2','synthetic-3'],strength=.55,version=1,active=True) for n in (2,3)])
    prefix=dict(path=[],visited=[obs.start]);scanned=scan_patterns(obs,prefix,memory,cfg,cfg.max_binding_checks)
    require(scanned['complete'] and [m['binding']['edge_order'] for m in scanned['matched']]==[[0,1],[2,3],[2,3,4]], 'Three candidates including prefix')
    program,drives,meta,_=pool_network(obs,scanned['matched'],memory,cfg)
    require(len(meta)==3 and sum(l['source'].startswith('c:') and l['target'].startswith('c:') for l in program['links'])==6, 'Synthetic inhibition grammar')
    base=plan['cells'][0]['observation']
    for cell in plan['cells']:
        obs2=cell['observation']; require(set(obs2)==set(base),'Paired observation fields')
        require({k:v for k,v in obs2.items() if k!='edges'}=={k:v for k,v in base.items() if k!='edges'},'Fixed identity/order/revision')
        for i,(a,b) in enumerate(zip(base['edges'],obs2['edges'])):
            require({k:v for k,v in a.items() if k!='score'}=={k:v for k,v in b.items() if k!='score'},'Fixed edge identity/topology')
            require(b['score']==(cell['score'] if i==4 else 1.0),'Only e4 score varies')
    dump(out/'validation/selftest.json',dict(verified=True,synthetic_candidate_count=3,
        synthetic_inhibition_links=6,synthetic_native_executions=0,research_sample=False,paired_intervention_checked=True))


def main(out, phase, step=None):
    if phase=='reference': dump(out/'training'/str(step)/'reference.json',recipe_reference(out,step))
    elif phase=='selftest': selftest(out)
    else:
        for folder,manifest in [('source','source_manifest.json'),('memory','memory_manifest.json'),
                                ('training','training_manifest.json'),('evaluation','raw_manifest.json')]:
            require(files(out/folder)==load(out/manifest)['files'],'Exact raw coverage '+folder)
        summary=collect(out);plan=load(out/'plan.json');cell=plan['cells'][-2]
        raw=load(out/'evaluation'/cell['id']/'inference.json');memory=load(out/'memory/3.json')
        rejected=mutation_checks(plan,raw['execution'],cell,memory,cell['use_circuits'],'frozen_eval','r076-'+cell['id']) if raw['execution']['candidate'] is not None else []
        dump(out/'summary.json',summary)
        dump(out/'verification.json',dict(verified=True,independent_native_replays=11,
            independent_feedback_replays=summary['feedback_applications'],rejected_raw_mutations=rejected,
            max_pool_replay_error=max((p['max_replay_error'] for r in summary['rows'] for p in r['pools']),default=None),
            all_candidate_states_preserved=True,negative_result_allowed=True,producer_imports=False))
    require(not (FORBIDDEN|{'hcr.activation','hcr.expansion','hcr.learning','tools.r076_competition.worker'}) & set(sys.modules), 'Auditor producer import boundary')
    print('Independent audit passed:',phase,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',choices=['selftest','reference','final'],required=True);p.add_argument('--step',type=int)
    a=p.parse_args();main(a.out,a.phase,a.step)
