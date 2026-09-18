"""독립 unit-test 전용 가상 입력/record. EXP24 본 실험 결과로 사용하지 않는다."""
from copy import deepcopy
from r043_input_order_control import spec
from r043_input_order_control.storage import digest


def parent_fixture():
    edges = [dict(id='e'+str(i),source=a,target=b,score=s) for i,(a,b,s) in enumerate([
        ('start','s',.9),('s','goal',.9),('start','m',None),('m','goal',.9),
        ('start','d1',-.9),('d1','d2',.9),('d2','goal',.9)])]
    branches = {'S':[0,1],'M':[2,3],'D':[4,5,6]}
    parent = dict(schema='hcr-exp22-plan-v1',conditions=dict(budget={'max_advances':12},selection_limits={'max_paths':4}),
                  cases=[],evaluation_worlds={},trials=[])
    for order in ('SMD','SDM','MSD','MDS','DSM','DMS'):
        name = 'order_'+order
        obs = dict(episode_id='fixture-only',revision=0,start='start',goal='goal',
                   edges=[deepcopy(edges[i]) for role in order for i in branches[role]])
        parent['cases'].append(dict(name=name,family='fixture',cohort='fixture',observation=obs,
                                   manipulation=dict(branch_order=order)))
        parent['evaluation_worlds'][name] = {'fixture_world':{'e'+str(i):i != 4 for i in range(7)}}
    seed = dict(memory={'abstract_patterns':[]},config={'minimum':.2})
    parent['memory_sha256'],parent['config_sha256'] = digest(seed['memory']),digest(seed['config'])
    return parent,seed


def plan_fixture():
    parent,seed = parent_fixture()
    cases,worlds = spec.cases(parent)
    plan = dict(conditions=spec.conditions(parent),cases=cases,evaluation_worlds=worlds,trials=spec.trials(),
                memory_sha256=digest(seed['memory']),config_sha256=digest(seed['config']))
    return plan,parent,seed


def report_records():
    plan,parent,seed=plan_fixture(); byname={c['name']:c for c in plan['cases']}
    records=[]
    for t in plan['trials']:
        c=byname[t['case']]; order=c['manipulation']['branch_order']
        ticks=100+10*('SMD','SDM','MSD','MDS','DSM','DMS').index(order)
        signature=dict(value=True,D_DAG=2,assumed_edges=[['e0',True],['e1',True]])
        diag=dict(canonical_readouts=[dict(ordinal=0,ticks=ticks,completed_paths=[['e0','e1']],
            policy_accepted=True,policy_D_DAG=2,state=dict(goal=1))],
            canonical_completion_sha256=digest([['e0','e1']]),
            final_support_signature=signature,completed_path_inventory=[['e0','e1']],
            final_proof_projection=dict(D_DAG=2,assumed_edges=signature['assumed_edges'],paths=[['e0','e1']]),
            first_supported_readout=dict(ordinal=0,ticks=ticks,frontier_count=1),
            first_usable_supported_readout=dict(ordinal=0,ticks=ticks,frontier_count=1),
            support_route_completion_rank=1)
        records.append(dict(trial=deepcopy(t),id_variant=c['id_variant'],branch_order=order,
            final=dict(accepted=True,value=True,reason='fixture'),classification='fixture_correct',
            diagnostics=diag,usage=dict(native_kernel_ticks=ticks,online_selection=dict(edge_checks=2)),
            scheduler_usage=dict(decision_calls=1,edge_id_reads=1,key_comparisons=0,priority_transitions=0),
            native_cost=dict(kernel_ticks=ticks,expansions=1,wall_seconds=0.0),
            readouts=[{}],final_frontier_count=1,reported_wall_seconds=.1,
            parent_regression={} if c['id_variant']=='identity' else None,
            input_order_policy_audit=dict(verified=True,slot_decisions=[])))
    return records


def full_parent_population():
    parent,seed=parent_fixture()
    for c in parent['cases']:
        for scope in ('legacy','scope_b'):
            for arm in ('native','posthoc_support','online_support'):
                for scheduler in ('input_order','edge_id_min','edge_id_max'):
                    parent['trials'].append(dict(id=f"t{len(parent['trials']):04d}",case=c['name'],scope=scope,arm=arm,scheduler=scheduler))
    return parent,seed
