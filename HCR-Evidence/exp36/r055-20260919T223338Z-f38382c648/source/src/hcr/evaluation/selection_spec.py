"""EXP-15 동결 조건. world는 평가/provider에만 공개한다.

EXP-14의 8개 입력은 원 조건을 보존한다. chain3/4의 running 경계 대조는
새 조건이며 최초 판단이 존재하는 182개 main rollout과 별도로 집계한다.
"""
from __future__ import annotations
from copy import deepcopy

BASE_COMMIT = '54330d01c979cb942b39558186c206b4373b758e'
PROTOCOL = 'exp15-r034-proof-selection-v1'
ARMS = ('hold','expand_only','restart_same','restart_route_only','select_only','expand_then_select','observe_first')
WORK_LIMITS = dict(max_extra_advances=8,max_extra_kernel_ticks=2048,max_measurements=3)
SELECTION_LIMITS = dict(max_ranked_paths=64,max_path_checks=64,max_edge_checks=256,max_proof_nodes=128)


def observation(name, pairs, scores, prefix='grounding-'):
    return dict(episode_id=prefix+name,start='s',goal='g',revision=0,
        edges=[dict(id=f'e{i}',source=a,target=b,score=scores[i]) for i,(a,b) in enumerate(pairs)])


def cases():
    chain=[('s','a'),('a','b'),('b','g')];diamond=[('s','a'),('a','g'),('s','b'),('b','g')]
    return [
        dict(name='strong_positive',family='preservation',observation=observation('strong_positive',chain,[.92]*3),worlds={'declared':dict(e0=True,e1=True,e2=True)}),
        dict(name='weak_negative',family='prior_conflict',observation=observation('weak_negative',chain,[-.06,.92,.92]),worlds={'declared':dict(e0=False,e1=True,e2=True)}),
        dict(name='critical_missing',family='critical_unknown',observation=observation('critical_missing',chain,[None,.92,.92]),worlds={'first_closed':dict(e0=False,e1=True,e2=True),'first_open':dict(e0=True,e1=True,e2=True)}),
        dict(name='critical_zero',family='critical_unknown',observation=observation('critical_zero',chain,[0.0,.92,.92]),worlds={'first_closed':dict(e0=False,e1=True,e2=True),'first_open':dict(e0=True,e1=True,e2=True)}),
        dict(name='irrelevant_missing',family='supported_alternative',observation=observation('irrelevant_missing',diamond,[.92,.92,None,.92]),worlds={'other_closed':dict(e0=True,e1=True,e2=False,e3=True),'other_open':dict(e0=True,e1=True,e2=True,e3=True)}),
        dict(name='known_cut_missing',family='supported_negative',observation=observation('known_cut_missing',chain,[-.98,None,None]),worlds={'rest_closed':dict(e0=False,e1=False,e2=False),'rest_open':dict(e0=False,e1=True,e2=True)}),
        dict(name='two_branch_cut',family='supported_negative',observation=observation('two_branch_cut',diamond,[-.98,None,-.98,None]),worlds={'rest_closed':dict(e0=False,e1=False,e2=False,e3=False),'rest_open':dict(e0=False,e1=True,e2=False,e3=True)}),
        dict(name='misleading_direction',family='noisy_evidence',observation=observation('misleading_direction',chain,[.92]*3),worlds={'declared':dict(e0=False,e1=True,e2=True)}),
    ]


def computation_cases():
    result=[]
    for n in (3,4):
        vertices=['s']+[f'c{i}' for i in range(n-1)]+['g']
        obs=observation(f'chain{n}',list(zip(vertices,vertices[1:])),[.92]*n,prefix='computation-')
        result.append(dict(name=f'computation_chain{n}',family='unfinished_computation',observation=obs,
            worlds={'declared':{f'e{i}':True for i in range(n)}},initial_advances=1,use_circuits=False))
    return result


def conditions():
    return dict(protocol=PROTOCOL,exp14_basis_commit=BASE_COMMIT,training_count=6,scopes=['legacy','route_only'],
        arms=list(ARMS),cases=cases(),computation_cases=computation_cases(),
        work_limits=deepcopy(WORK_LIMITS),selection_limits=deepcopy(SELECTION_LIMITS),
        simulation_only=True,frozen_memory=True,selection_changes_value=False,
        selection_only_uses_existing_routes=True,main_first_decision_preserved=True,
        computation_control_has_no_first_decision=True,task_success_required_for_audit=False,
        learning_strength_axis_tested=False,selected_proof_gap_is_not_global_information_gap=True)


def baseline_specs(cp):
    for case in cp['cases']:
        for scope in cp['scopes']:
            yield dict(key=case['name']+'/'+scope,case=case['name'],scope=scope,phase='readout_ready')
    for case in cp['computation_cases']:
        yield dict(key=case['name']+'/route_only',case=case['name'],scope='route_only',phase='running')


def cells(cp):
    rows=[]
    def add(case,scope,world,arm,group='main',work=None,selection=None):
        rows.append(dict(case=case,scope=scope,world=world,arm=arm,group=group,
            baseline_key=case+'/'+scope,limits=deepcopy(work or cp['work_limits']),
            selection_limits=deepcopy(selection or cp['selection_limits']),provider='perfect' if arm=='observe_first' else None))
    for case in cp['cases']:
        for scope in cp['scopes']:
            for world in sorted(case['worlds']):
                for arm in cp['arms']:add(case['name'],scope,world,arm)
    for case in cp['computation_cases']:
        add(case['name'],'route_only','declared','hold','running_hold')
        for budget in (0,1,8):
            add(case['name'],'route_only','declared','continue',f'running_budget_{budget}',
                work=dict(cp['work_limits'],max_extra_advances=budget))
    for group,arm,work,sel in [
        ('selection_no_scan','select_only',None,dict(cp['selection_limits'],max_path_checks=0)),
        ('selection_no_extra_compute','expand_then_select',dict(cp['work_limits'],max_extra_advances=0),None),
        ('selection_no_edges','expand_then_select',None,dict(cp['selection_limits'],max_edge_checks=0)),
        ('selection_no_proof','expand_then_select',None,dict(cp['selection_limits'],max_proof_nodes=0)),
    ]:
        add('irrelevant_missing','legacy','other_closed',arm,group,work,sel)
    for i,row in enumerate(rows):row['id']=f's{i:04d}'
    return rows


def all_cases(cp):
    return {c['name']:c for c in cp['cases']+cp['computation_cases']}
