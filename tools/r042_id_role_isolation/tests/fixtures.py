"""독립 unit-test 전용 가상 입력/record. EXP23 본 실험 결과로 사용하지 않는다."""
from copy import deepcopy
from r042_id_role_isolation import spec
from r042_id_role_isolation.storage import digest


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


def report_records(*, reverse=True, equal=False):
    plan,_,_ = plan_fixture(); cases = {c['name']:c for c in plan['cases']}
    records = []
    for trial in plan['trials']:
        case=cases[trial['case']]; variant=case['id_variant']; scheduler=trial['scheduler']
        fast = scheduler == 'edge_id_min'
        if reverse and variant == 'swap_SD': fast = not fast
        ticks = 100 if equal or fast else 160
        tag = 'fast' if equal or fast else 'slow'
        diag = dict(pre_competitive_probe={'fixture':'same'},canonical_completion_sha256=tag,
            canonical_trajectory_sha256=tag,final_proof_projection={'D_DAG':2},
            first_supported_readout={'ticks':ticks,'ordinal':0},support_route_completion_rank=2 if fast else 3,
            canonical_readouts=[],scheduler_rows=[])
        records.append(dict(trial=deepcopy(trial),id_variant=variant,branch_order=case['manipulation']['branch_order'],
            final={'accepted':True,'value':True,'reason':'fixture'},classification='correct_in_all_declared_worlds',
            usage={'native_kernel_ticks':ticks,'online_selection':{}},scheduler_usage={},readouts=[{}],
            diagnostics=diag,final_frontier_count=int(fast),reported_wall_seconds=.1,
            parent_regression={} if variant == 'identity' else None))
    return records
