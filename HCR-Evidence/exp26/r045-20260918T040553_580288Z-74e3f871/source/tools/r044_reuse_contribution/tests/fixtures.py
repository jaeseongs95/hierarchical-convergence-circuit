"""Synthetic unit-test fixtures only, deliberately independent of native outcomes."""
from copy import deepcopy
from r043_input_order_control.tests.fixtures import parent_fixture as old_fixture
from r044_reuse_contribution import spec
from r044_reuse_contribution.storage import digest


def parent_fixture():
    p,s=old_fixture()
    s['memory']={'circuits':[{'fixture_pattern':'length_two'}]}
    p['memory_sha256']=digest(s['memory'])
    return p,s


def plan_fixture():
    parent,seed=parent_fixture();cases,worlds=spec.cases(parent)
    return dict(conditions=spec.conditions(parent),cases=cases,evaluation_worlds=worlds,trials=spec.trials(),
        memory_sha256=parent['memory_sha256'],config_sha256=parent['config_sha256']),parent,seed


def full_parent_population():
    parent,seed=parent_fixture()
    for c in parent['cases']:
        for scope in ('legacy','route_only'):
            for arm in ('native','posthoc_support','online_support'):
                for scheduler in ('input_order','edge_id_min','edge_id_max'):
                    parent['trials'].append(dict(id=f"t{len(parent['trials']):04d}",case=c['name'],scope=scope,arm=arm,scheduler=scheduler))
    return parent,seed


def report_records():
    plan,_,_=plan_fixture();cases={c['name']:c for c in plan['cases']};records=[]
    for t in plan['trials']:
        gate=t['use_circuits'];c=cases[t['case']];ticks=80 if gate else 100;exp=2 if gate else 4
        signature=dict(value=True,D_DAG=2,assumed_edges=[['e0',True],['e1',True]])
        readout=dict(ordinal=0,ticks=ticks,completed_paths=[['e0','e1']],policy_accepted=True,policy_D_DAG=2,state={'goal':1.0})
        diagnostics=dict(canonical_readouts=[readout],canonical_completion_sha256=digest([['e0','e1']]),
            final_support_signature=signature,completed_path_inventory=[['e0','e1']],
            final_proof_projection=dict(D_DAG=2,assumed_edges=signature['assumed_edges'],paths=[['e0','e1']]),
            first_supported_readout=dict(ordinal=0,ticks=ticks,frontier_count=1),
            first_usable_supported_readout=dict(ordinal=0,ticks=ticks,frontier_count=1),support_route_completion_rank=1)
        measurements=dict(macro_actions=int(gate),primitive_actions=1 if gate else 4,
            pool_kernel_ticks=30 if gate else 0,decision_kernel_ticks=50 if gate else 100,
            binding_scan_calls=1 if gate else 0,binding_edge_scans=7 if gate else 0,circuit_inspections=int(gate),
            macro_span_edge_items=2 if gate else 0,exposure='macro_applied' if gate else 'none',
            adopted_route=None,networks=[],actions=[])
        records.append(dict(trial=deepcopy(t),use_circuits=gate,id_variant=c['id_variant'],branch_order=c['manipulation']['branch_order'],
            final=dict(accepted=True,value=True,reason='stop_supported_policy'),classification='correct_in_all_declared_worlds',
            diagnostics=diagnostics,reuse_measurements=measurements,
            usage=dict(native_kernel_ticks=ticks,online_selection={'edge_checks':2}),
            scheduler_usage=dict(decision_calls=exp,edge_id_reads=exp,key_comparisons=0,priority_transitions=0),
            native_cost=dict(kernel_ticks=ticks,expansions=exp,wall_seconds=0.0),readouts=[{}],final_frontier_count=1,
            reported_wall_seconds=.01,parent_regression={} if gate and c['id_variant']=='identity' else None,
            input_order_policy_audit={'verified':True,'slot_decisions':[]}))
    return records


def state_fixture(gate=True):
    plan,parent,seed=plan_fixture();case=plan['cases'][0];obs=case['observation']
    pol=dict(schema='hcr-judgment-prior-policy-v1',judgment_scope='route_only')
    core=dict(memory=deepcopy(seed['memory']),config=deepcopy(seed['config']),
        switches=dict(use_circuits=gate,top_down=True,allow_reexpansion=True),
        prior_policy=dict(pol,sha256=digest(pol)),held={},feedback={},requests={},
        pending=dict(observation=deepcopy(obs),mode='frozen_eval',cost=dict(learning_updates=0,memory_write_items=0)))
    return {0:deepcopy(core),1:deepcopy(core)},obs,seed,dict(scope='route_only',use_circuits=gate)


def event_fixture(gate=True):
    p,_,_=plan_fixture();case=p['cases'][0];trial=dict(use_circuits=gate);events=[]
    def emit(event,**payload):events.append(dict(seq=len(events),event=event,payload=payload))
    if gate:
        emit('r02_binding_scan',scans=[['fixture',[],0]],inspected=['fixture'])
    for kind in (('pool','decision') if gate else ('decision',)):
        emit('r02_network',network_id=kind,kind=kind,top_down=True,
            program=dict(groups=[{'id':'e:0','level':0},{'id':'goal','level':1}],
                         links=[{'kind':'support'}]),drives={'e:0':1.0,'goal':0.0})
        for i in (1,2):emit('r02_tick',network_id=kind,tick=i)
        emit('r02_settled',network_id=kind,convergence={'ticks':2,'status':'stable_decision'})
        if kind=='pool':emit('r02_pool_result',network_id=kind)
    source='circuit' if gate else 'primitive';candidate=dict(source=source,edges=[0,1] if gate else [0],circuit_id='fixture' if gate else None)
    emit('r02_proposals',circuits_enabled=gate,candidates=[candidate])
    emit('r02_expansion',candidate=candidate,prefix={'path':[]},complete=False)
    ticks=4 if gate else 2
    cost=dict(kernel_ticks=ticks,group_updates=ticks*2,signal_transmissions=ticks,
        binding_checks=int(gate),binding_operations=int(gate),recall_checks=int(gate),pool_calls=int(gate),
        expansions=1,circuit_reuses=int(gate),frontier_retirements=0)
    run=dict(base=dict(packet=dict(document=dict(engine=dict(pending=dict(observation=case['observation'],cost=cost,
        workspace={'routes':[]})),events=events)),events=[],selections=[]),usage={'native_kernel_ticks':ticks},final={'accepted':False})
    return run,trial,case
