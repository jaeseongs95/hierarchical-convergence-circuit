"""EXP-14 사전 동결 조건. 가능한 세계/참값/관측 provider는 평가 층 전용이다."""
from __future__ import annotations
from copy import deepcopy
from .grounding_spec import fixtures
from .audit import require

PROTOCOL='exp14-r033-grounded-review-v1'
POLICIES=('hold','expand_only','observe_first','expand_then_observe','route_review')
SCOPES=('legacy','route_only')
CASE_NAMES=('strong_positive','weak_negative','critical_missing','critical_zero',
            'irrelevant_missing','known_cut_missing','two_branch_cut','misleading_direction')
DEFAULT_LIMITS=dict(max_extra_advances=8,max_extra_kernel_ticks=2048,max_measurements=3)


def condition_plan(training_counts=(6,)):
    counts=list(training_counts)
    require(counts==sorted(set(counts)) and counts and all(type(n)is int and n in (3,6,9) for n in counts),'training snapshots: sorted unique subset of 3,6,9')
    cases=[c for name in CASE_NAMES for c in fixtures() if c['name']==name]
    return dict(protocol=PROTOCOL,training_counts=counts,cases=cases,scopes=list(SCOPES),policies=list(POLICIES),
        limits=DEFAULT_LIMITS,baseline_shared_across_policy_and_world=True,adaptive_learning=False,
        prior_switch_only_in_explicit_arm=True,default_training_is_not_rigidity_study=True,
        measurement_environment='simulated_perfect_sensor_not_empirical_measurement',
        query_target_rule='first_gap_in_selected_proof_or_existing_paths_not_global_oracle',
        controls=['unchanged_sensor','unavailable_sensor','zero_extra_work','one_extra_step'],
        whole_controller_checkpoint_resume=False,task_success_not_an_acceptance_requirement=True)


def baselines(plan):
    for n in plan['training_counts']:
        for c in plan['cases']:
            for scope in plan['scopes']:
                yield n,c,scope


def cells(plan):
    result=[]
    for n,c,scope in baselines(plan):
        for w in sorted(c['worlds']):
            for policy in plan['policies']:
                result.append(dict(training=n,case=c['name'],scope=scope,world=w,policy=policy,
                    provider='perfect',group='main',limits=dict(plan['limits'])))
        if c['name'] in ('critical_missing','irrelevant_missing'):
            w=min(c['worlds'])
            for name,steps in [('zero_extra_work',0),('one_extra_step',1)]:
                result.append(dict(training=n,case=c['name'],scope=scope,world=w,policy='expand_then_observe',
                    provider='perfect',group=name,limits=dict(plan['limits'],max_extra_advances=steps)))
        if c['name']=='critical_missing':
            w=min(c['worlds'])
            for provider in ('unchanged','unavailable'):
                result.append(dict(training=n,case=c['name'],scope=scope,world=w,policy='expand_then_observe',
                    provider=provider,group=provider+'_sensor',limits=dict(plan['limits'])))
    for i,r in enumerate(result):r['id']=f'r{i:04d}'
    return result


def provider_for(observation,world,mode):
    """테스트 환경 adapter. 실제 센서/LLM 결과로 부르지 않는다. 요청 edge만 공개한다."""
    scores={e['id']:e['score'] for e in observation['edges']}
    def provider(request):
        ids=request['edge_ids']
        if mode=='perfect':
            return dict(request_sha256=request['sha256'],status='measured',
                scores={e:.98 if world[e] else -.98 for e in ids},source='simulated_perfect_sensor')
        if mode=='unchanged':
            return dict(request_sha256=request['sha256'],status='measured',
                scores={e:scores[e] for e in ids},source='simulated_unchanged_sensor')
        return dict(request_sha256=request['sha256'],status='unavailable',scores={},source='simulated_unavailable_sensor')
    return provider
