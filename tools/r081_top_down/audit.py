"""Independent recurrence, event-local rules and proof audit; no producer imports."""
import argparse
from copy import deepcopy
from pathlib import Path
import sys
from hcr import codec
from hcr.prior_policy import read_scope
from hcr.evaluation.review_audit import packet_states
from tools.r050_review_boundary.common import dump, files, fingerprint, load, require, sha
from tools.r050_review_boundary.audit import FORBIDDEN, validate_reservations, candidate_measures, counter_values
from tools.r050_review_boundary.candidate_audit import verify_candidate
from tools.r064_retention.audit import reference
from tools.r076_competition.audit import pools
from tools.r077_equal_binding.audit import collect as parent_collect
from tools.r078_binding_order.audit import public_path
from tools.r079_score_readout.measure import decision_networks, proof_support, measurement_selftest, readout_state
from tools.r080_small_positive.audit import measure as old_measure

SPEC='experiments/exp-62-top-down/frozen_spec.json'

def assert_flags(packet,flag):
    require(type(flag) is bool, 'Frozen flag type')
    doc=packet['document']
    require(doc['engine']['switches']['top_down'] is flag, 'Frozen engine top_down')
    created=[e for e in doc['events'] if e['event']=='r02_engine_created']
    require(len(created)==1 and created[0]['payload']['top_down'] is flag, 'Frozen created top_down')
    require(all(e['payload']['top_down'] is flag for e in doc['events'] if e['event']=='r02_network'), 'Frozen network top_down')

def verify_execution(plan,e,case,memory,gate,mode,identity):
    require(set(e)=={'packet','candidate','advances','ready','stop'},'Execution fields')
    assert_flags(e['packet'],case['top_down'])
    if e['candidate'] is not None: assert_flags(e['candidate']['packet'],case['top_down'])
    states,report=packet_states(e['packet'])
    require(report['verified'],'Native state replay')
    doc=e['packet']['document'];core=doc['engine'];p=core['pending']
    require(doc['session_id']==identity,'Session identity')
    require(core['config']==plan['config'] and core['memory']==memory and states[0]['memory']==memory,'Config/seed memory')
    require(read_scope(core)=='route_only' and core['switches']==dict(use_circuits=gate,top_down=case['top_down'],allow_reexpansion=True),'Policy/switches')
    require(not core['held'] and not core['feedback'] and not core['requests'],'Unlisted learning or observation')
    require(p['observation']==case['observation'] and p['mode']==mode,'Observation/mode')
    operations=[t['operation'] for t in doc['transitions']]
    require(operations==['init','begin']+['advance']*e['advances'],'Generation operations')
    bound=plan['config']['kernel']['max_ticks']*(2 if gate and memory['circuits'] else 1)
    validate_reservations(e,states,plan['limits'],bound)
    require(e['ready'] is p['ready'],'Ready flag')
    if e['ready']:
        require(e['stop']=='readout_ready' and e['candidate'] is not None,'Native candidate missing')
        require(e['candidate']['reference']['segment']==0,'Readout segment')
        verify_candidate(e['candidate'],e['packet'],states)
    else:
        require(e['candidate'] is None and e['stop']=='external_compute_budget','Partial execution status')
        require(e['advances']==plan['limits']['max_advances_per_session'] or p['cost']['kernel_ticks']+bound>plan['limits']['max_kernel_ticks_per_session'],'Premature budget stop')
    return states

def audit_cell(plan, raw, cell, memory, cfg, world, prefix='r081'):
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

def measure(plan, raw, cell, memory, cfg, world, prefix='r081'):
    row = audit_cell(plan,raw,cell,memory,cfg,world,prefix)
    require(not row['pools'] and row['tick_split']['pool']==0, 'OFF has no pool')
    row.pop('wall_seconds')
    row['top_down'] = cell['top_down']
    row['construct_role'] = 'paired_top_down_signal_bundle'
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
                     transmitted=bool(event['top_down'] or l['kind']!='top_down'),
                     last_tick_centered_link_input=l['weight']*(2*previous[l['source']]-1) if event['top_down'] or l['kind']!='top_down' else 0.0,
                     would_be_last_tick_centered_term=l['weight']*(2*previous[l['source']]-1),
                     terminal_centered_link_term=l['weight']*(2*state[l['source']]-1),
                     terminal_uncentered_activation_product=l['weight']*state[l['source']]) for l in links])
        n['top_down']=event['top_down']
        n['active_links_per_tick']=sum(event['top_down'] or l['kind']!='top_down' for l in links)
        n['stored_links']=len(links)
        require(event['drives']['e:1']==4*cell['score'], 'Score mapped to public e3 drive')
    require(sum(n['active_links_per_tick']*n['convergence']['ticks'] for n in row['decision_networks'])==row['cost']['signal_transmissions'], 'Active signal transmission ledger')
    row['first_state_measurement'] = 'measurement_failure' if row['first_decision'] is None else row['first_decision']['category']
    row['session_budget_termination'] = e['stop']=='external_compute_budget'
    return row


def controls(plan,parent):
    previous=load(parent/'plan.json');memory=load(parent/'memory/3.json')
    require(plan['config']==previous['config'] and plan['limits']==previous['limits'],'R077 fixed config/budget')
    require(fingerprint(plan['config'])==plan['config_sha256'],'Config fingerprint')
    require(sha((parent/'memory/3.json').read_bytes())==plan['memory_sha256'],'Frozen memory')
    require(plan['world_file']==previous['world_file'] and plan['world_sha256']==previous['world_sha256'],'Frozen world')
    require(plan['scores']==dict(s003=.03,s004=.04) and plan['orders']==dict(swapped=['e2','e3','e0','e1']),'Exact grid/order')
    expected=[]
    base=next(c for c in previous['cells'] if c['score_id']=='s00' and not c['use_circuits'])
    for sid,score in [('s003',.03),('s004',.04)]:
        for flag in (True,False):
            c=deepcopy(base);edges={e['id']:e for e in c['observation']['edges']};edges['e3']['score']=score
            c['observation']['edges']=[edges[i] for i in ['e2','e3','e0','e1']]
            c.update(id='swapped-'+sid+'-td'+str(int(flag))+'-off',score_id=sid,score=score,order_id='swapped',top_down=flag,
                evidence_role='reproduction' if flag else 'new_signal_intervention',reproduction_id='swapped-'+sid+'-off' if flag else None)
            expected.append(c)
    require(plan['cells']==expected,'Exactly four paired cells; only top_down switch differs within pairs')
    cfg=codec.adaptive_config_from(plan['config'])
    require(cfg.signature==memory['config_signature'] and cfg.kernel.prior_gain==0,'Memory/config signature')
    return memory,cfg


def stable(n):return n is not None and n['category'] in ('stable_true','stable_false','stable_ambiguous')


def classify(rows,tolerance):
    indexed={(r['score_id'],r['top_down']):r for r in rows};pred={};pairs=[]
    for sid in ('s003','s004'):
        a,b=[indexed[sid,flag]['first_decision'] for flag in (True,False)]
        literal=b is not None and b['category']=='stable_true' and b['candidate_value'] is True and b['ready'] is True and b['progress_mismatch_kind'] is None
        pred['remove_bundle_'+sid+'_true']=dict(verdict='not_evaluable' if not stable(b) else 'supported' if literal else 'falsified',literal=literal,stable_evaluable=stable(b))
        measured=a is not None and b is not None;both=stable(a) and stable(b)
        numeric=None if not measured else b['goal_activation']-a['goal_activation']
        pairs.append(dict(score_id=sid,category_evaluable=both,numeric_evaluable=measured,
            category_changed=None if not both else a['category']!=b['category'],
            first_goal_difference_false_minus_true=numeric,numeric_difference=None if not measured else abs(numeric)>tolerance,
            first_categories=[None if n is None else n['category'] for n in (a,b)],
            first_statuses=[None if n is None else n['convergence']['status'] for n in (a,b)]))
    pred['category_change_exists']=dict(verdict='supported' if any(p['category_changed'] is True for p in pairs) else 'not_evaluable' if not all(p['category_evaluable'] for p in pairs) else 'falsified')
    pred['numeric_difference_both']=dict(verdict='falsified' if any(p['numeric_difference'] is False for p in pairs) else 'not_evaluable' if not all(p['numeric_evaluable'] for p in pairs) else 'supported')
    return pred,pairs


def collect(out):
    plan=load(out/'plan.json');require(plan==load(out/'source'/SPEC),'Frozen spec binding')
    memory,cfg=controls(plan,out/'parent');world=load(out/'source'/plan['world_file'])['evaluation']
    require(sha((out/'source'/plan['world_file']).read_bytes())==plan['world_sha256'] and world==dict(e0=True,e1=True,e2=True,e3=True),'Authored world')
    rows=[];repeats=[]
    for c in plan['cells']:
        raw=load(out/'evaluation'/c['id']/'inference.json');e=raw['execution'];row=measure(plan,raw,c,memory,cfg,world);rows.append(row)
        require(row['first_decision'] is not None,'Measurement failure: missing first decision')
        packets=sorted((out/'evaluation'/c['id']/'progress').glob('step-*.json'))
        require(len(packets)==e['advances']+2 and load(packets[-1])==e['packet'],'Progress packet coverage')
        for path in packets:
            packet=load(path);assert_flags(packet,c['top_down']);require(packet_states(packet)[1]['verified'],'Progress independent replay')
        path=out/'evaluation'/c['id']/'progress/candidate.json'
        require(path.exists() is (e['candidate'] is not None),'Candidate file coverage')
        if path.exists():require(load(path)==e['candidate'],'Candidate file equality')
        if c['evidence_role']=='reproduction':
            old=load(out/'repeat/evaluation'/c['reproduction_id']/'inference.json')
            oldrow=old_measure(plan,old,old['cell'],memory,cfg,world,'r080')
            require(c['observation']==old['cell']['observation'],'Exact reproduction observation')
            require(e['packet']['document']['events']==old['execution']['packet']['document']['events'],'R080 exact journal reproduction')
            for key in ('final_support','cost','tick_split','raw_value'):require(row[key]==oldrow[key],'R080 reproduction '+key)
            repeats.append(dict(id=c['id'],historical_id=c['reproduction_id'],journal_events_equal=True,integer_cost_equal=True,final_support_equal=True,new_independent_evidence=False))
    require(sorted(p.name for p in (out/'evaluation').iterdir())==sorted(c['id'] for c in plan['cells']),'Exactly four executed cells')
    predictions,pairs=classify(rows,plan['numeric_tolerance']);indexed={(r['score_id'],r['top_down']):r for r in rows}
    for pair in pairs:
        a,b=[indexed[pair['score_id'],flag] for flag in (True,False)];an,bn=a['first_decision'],b['first_decision']
        raws=[load(out/'evaluation'/r['id']/'inference.json')['execution']['packet']['document']['events'] for r in (a,b)]
        first=[events[n['event_index']]['payload'] for events,n in zip(raws,(an,bn))]
        require(first[0]['program']==first[1]['program'] and first[0]['drives']==first[1]['drives'] and first[0]['metadata']==first[1]['metadata'],'Paired first network program/drives/route metadata')
        # Compare only naturally shared route inventories; do not equalize later expansion.
        shared=[]
        for left in a['decision_networks']:
            for right in b['decision_networks']:
                if left['route_slot_paths']==right['route_slot_paths']:
                    require(left['program_digest']==right['program_digest'] and left['drives']==right['drives'],'Shared route program/drives fixed')
                    shared.append(left['program_digest'])
        pair.update(first_program_digest=an['program_digest'],paired_program_equal=True,shared_route_program_digests=shared,
            first_numeric_difference_false_minus_true={key:bn['convergence'][key]-an['convergence'][key] for key in ('margin','residual','ticks','stable_steps')},
            first_readout=[{k:n[k] for k in ('candidate_value','ready','pending_value','progress_mismatch_kind','progress_event_seq','generation','graph_complete')} for n in (an,bn)],
            first_active_links_per_tick=[n['active_links_per_tick'] for n in (an,bn)],
            cost_difference_false_minus_true={k:b['cost'][k]-a['cost'][k] for k in a['cost']},
            final_paths=[r['final_support']['selected_edge_id_path'] if r['final_support'] else None for r in (a,b)],
            D_DAG=[r['final_support']['recomputed_D_DAG'] if r['final_support'] else None for r in (a,b)])
    return dict(schema='hcc-r081-summary-v1',rows=rows,pairs=pairs,predictions=predictions,reproduction_checks=repeats,
        native_evaluation_executions=4,reproduction_executions=2,new_signal_intervention_executions=2,
        native_training_executions=0,feedback_applications=0,new_independent_samples=0,
        claim_boundary=plan['claim_boundary'],actual_energy_joules=None,peak_memory_bytes=None,
        prediction_supports_are_not_independent_samples=True)


def selftest(out):
    plan=load(out/'plan.json');memory,cfg=controls(plan,out/'parent')
    require(parent_collect(out/'parent')==load(out/'parent/summary.json'),'R077 raw grounding')
    world=load(out/'source'/plan['world_file'])['evaluation']
    for c in plan['cells']:
        require(codec.observation_from(c['observation']).digest is not None,'Grammar')
        if c['top_down']:
            raw=load(out/'repeat/evaluation'/c['reproduction_id']/'inference.json');old_measure(plan,raw,raw['cell'],memory,cfg,world,'r080')
    # Algebraic identity only, not a new test-condition trajectory or native pilot.
    algebra=0
    for p in (0.,.25,.5,.75,1.):
        for drive in (-2.,0.,2.):
            s=cfg.kernel.self_excitation;i=cfg.kernel.inhibition
            lhs=(drive+s*p-i*(1-p))-(-drive+s*(1-p)-i*p)
            rhs=2*drive+(s+i)*(2*p-1)
            require(abs(lhs-rhs)<1e-14,'Own-state algebra');algebra+=1
    rows=[dict(score_id=sid,top_down=flag,first_decision=dict(category='stable_true',candidate_value=True,ready=True,progress_mismatch_kind=None,goal_activation=.9,convergence=dict(status='stable_decision'))) for sid in ('s003','s004') for flag in (True,False)]
    pred,_=classify(rows,plan['numeric_tolerance']);require(pred['category_change_exists']['verdict']=='falsified' and pred['numeric_difference_both']['verdict']=='falsified','Literal equal category and number')
    for category in ('budget_exhausted','oscillating'):
        bad=deepcopy(rows);bad[1]['first_decision']['category']=category;bad[1]['first_decision']['convergence']['status']=category
        pred,_=classify(bad,plan['numeric_tolerance']);require(pred['remove_bundle_s003_true']['verdict']=='not_evaluable' and pred['category_change_exists']['verdict']=='not_evaluable','Nonstable not false')
    missing=deepcopy(rows);missing[1]['first_decision']=None
    pred,_=classify(missing,plan['numeric_tolerance']);require(pred['remove_bundle_s003_true']['verdict']=='not_evaluable' and pred['category_change_exists']['verdict']=='not_evaluable','Missing is not false')
    require(pred['numeric_difference_both']['verdict']=='falsified','Measured equal counterexample survives other missing pair')
    ambiguous=deepcopy(rows);ambiguous[1]['first_decision'].update(category='stable_ambiguous',candidate_value=None,ready=False,progress_mismatch_kind='unresolved_or_no_goal_candidate')
    pred,_=classify(ambiguous,plan['numeric_tolerance']);require(pred['remove_bundle_s003_true']['verdict']=='falsified' and pred['category_change_exists']['verdict']=='supported','Ambiguous is stable category, not False')
    numeric=deepcopy(rows)
    for r in numeric[1::2]:r['first_decision']['goal_activation']=.8
    pred,_=classify(numeric,plan['numeric_tolerance']);require(pred['numeric_difference_both']['verdict']=='supported' and pred['category_change_exists']['verdict']=='falsified','Numeric difference does not imply category change')
    numeric[1]['first_decision']=None
    pred,_=classify(numeric,plan['numeric_tolerance']);require(pred['numeric_difference_both']['verdict']=='not_evaluable','No numeric counterexample with missing pair')
    dump(out/'validation/selftest.json',dict(verified=True,**measurement_selftest(),algebra_checks=algebra,prediction_cases=7,
        grammar_checks=4,prior_native_journals_reanalyzed=11,new_native_executions=0,numeric_pilot_executions=0))


def rehash(raw):
    packet=raw['execution']['packet'];doc=packet['document'];previous='0'*64
    for e in doc['events']:
        e['previous']=previous;e['sha256']=fingerprint({k:v for k,v in e.items() if k!='sha256'});previous=e['sha256']
    packet['sha256']=fingerprint(doc)


def raw_mutations(out):
    plan=load(out/'plan.json');memory,cfg=controls(plan,out/'parent');world=load(out/'source'/plan['world_file'])['evaluation'];rejected=[]
    def event(x,kind):return next(e['payload'] for e in x['execution']['packet']['document']['events'] if e['event']==kind)
    def change_state(x,kind):
        state=event(x,kind)['state'];state['goal']=.75 if state['goal']!=.75 else .25
    def change_status(x):
        conv=event(x,'r02_settled')['convergence']
        conv['status']='oscillating' if conv['status']!='oscillating' else 'budget_exhausted'
    for c in [plan['cells'][0],plan['cells'][1]]:
        raw=load(out/'evaluation'/c['id']/'inference.json');control=deepcopy(raw);rehash(control);measure(plan,control,c,memory,cfg,world)
        mutations={
            'network_flag':lambda x:event(x,'r02_network').update(top_down=not c['top_down']),
            'engine_flag':lambda x:x['execution']['packet']['document']['engine']['switches'].update(top_down=not c['top_down']),
            'created_flag':lambda x:event(x,'r02_engine_created').update(top_down=not c['top_down']),
            'tick_state':lambda x:change_state(x,'r02_tick'),
            'first_status':change_status,
            'first_goal':lambda x:change_state(x,'r02_settled'),
            'signal_count':lambda x:x['execution']['packet']['document']['engine']['pending']['cost'].update(signal_transmissions=0),
        }
        if c['top_down']:
            def progress(x):return next(e['payload'] for e in x['execution']['packet']['document']['events'] if e['event']=='r02_progress' and e['payload']['network_id'] is not None)
            mutations.update(progress_reason=lambda x:progress(x)['mismatch'].update(kind='unresolved_or_no_goal_candidate'),
                progress_network=lambda x:progress(x).update(network_id=None),progress_coverage=lambda x:progress(x).update(graph_complete=True))
        for name,mutate in mutations.items():
            bad=deepcopy(raw);mutate(bad);rehash(bad)
            try:measure(plan,bad,c,memory,cfg,world)
            except (ValueError,AssertionError,RuntimeError) as error:
                reason=str(error);require(not any(t in reason for t in ('event chain mismatch','session packet seal')),'Stale hash is not semantic rejection')
                rejected.append(dict(cell=c['id'],name=name,reason=reason,event_chain_rehashed=True))
            else:raise AssertionError('Undetected semantic mutation '+name)
    raw=load(out/'evaluation'/plan['cells'][0]['id']/'inference.json')
    d=deepcopy(raw['execution']['candidate']['decision']);d['_slot_to_edge_id']=[e['id'] for e in plan['cells'][0]['observation']['edges']]
    for name,mutate in dict(final_depth=lambda x:x['proof'].update(primitive_depth=99),final_reference=lambda x:x['proof'].update(final='invented')).items():
        bad=deepcopy(d);mutate(bad)
        try:proof_support(bad)
        except ValueError as error:rejected.append(dict(name=name,reason=str(error),layer='independent proof ancestry'))
        else:raise AssertionError('Undetected proof mutation '+name)
    return rejected


def main(out,phase):
    for folder,manifest in [('source','source_manifest.json'),('parent','input_manifest.json'),('repeat','repeat_manifest.json')]:require(files(out/folder)==load(out/manifest)['files'],'Frozen coverage '+folder)
    if phase=='selftest':selftest(out)
    else:
        require(files(out/'evaluation')==load(out/'raw_manifest.json')['files'],'Raw coverage')
        summary=collect(out);rejected=raw_mutations(out);dump(out/'summary.json',summary)
        dump(out/'verification.json',dict(verified=True,independent_native_journals_replayed=4,prior_reproduction_journals_replayed=2,
            semantic_rejections=rejected,rehash_only_controls_passed=2,first_network_and_advance_bound=True,
            final_ancestry_recomputed=True,frozen_flag_binding=True,active_transmissions_recomputed=True,
            producer_imports=False,independent_researcher=False,new_native_executions=0))
    require(not (FORBIDDEN|{'hcr.activation','hcr.expansion','hcr.learning','tools.r081_top_down.worker'})&set(sys.modules),'Auditor producer boundary')
    print('Independent audit passed:',phase,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--phase',choices=['selftest','final'],required=True);a=p.parse_args();main(a.out,a.phase)

