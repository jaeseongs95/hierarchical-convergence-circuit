"""EXP-13 사전 조건. 정답과 가능한 세계는 평가기에서만 사용한다."""
from __future__ import annotations
from .. import codec
from ..model import AdaptiveConfig, EdgeObservation, Observation
from ..tasks.toy_world import chain
from .prior_spec import ARMS, TRAINING_COUNTS, arm_options, training_world

PROTOCOL = 'exp13-r032-grounding-v1'
READOUT_POLICIES = ('diagnostic_only', 'dependency_gate', 'blanket_unknown_gate')
SUPPORT = dict(schema='hcr-directional-support-v1', min_abs_score=0.0,
               zero_is_neutral=True, missing_is_unknown=True, score_is_probability=False, support_is_truth=False)


def fixtures():
    cases = []
    def add(name, family, edges, worlds):
        obs = Observation('grounding-'+name, 0, 's', 'g',
                          tuple(EdgeObservation('e'+str(i), a, b, score) for i,(a,b,score) in enumerate(edges)))
        cases.append(dict(name=name, family=family, observation=codec.plain(obs),
                          worlds={k:{e.id:bool(v[i]) for i,e in enumerate(obs.edges)} for k,v in worlds.items()}))
    def chain_case(name, family, scores, worlds):
        add(name, family, [('s','a',scores[0]),('a','b',scores[1]),('b','g',scores[2])], worlds)
    chain_case('strong_positive','preservation',(.92,.92,.92),{'declared':(1,1,1)})
    chain_case('strong_negative','preservation',(-.98,.92,.92),{'declared':(0,1,1)})
    chain_case('weak_negative','prior_conflict',(-.06,.92,.92),{'declared':(0,1,1)})
    chain_case('weak_positive','preservation',(.06,.92,.92),{'declared':(1,1,1)})
    pair={'first_open':(1,1,1),'first_closed':(0,1,1)}
    chain_case('critical_missing','critical_unknown',(None,.92,.92),pair)
    chain_case('critical_zero','critical_unknown',(0.0,.92,.92),pair)
    chain_case('all_missing','global_unknown',(None,)*3,pair)
    chain_case('all_zero','global_unknown',(0.0,)*3,pair)
    for label,score in (('missing',None),('zero',0.0)):
        add('irrelevant_'+label,'supported_alternative',
            [('s','a',.92),('a','g',.92),('s','b',score),('b','g',.92)],
            {'other_open':(1,1,1,1),'other_closed':(1,1,0,1)})
        chain_case('known_cut_'+label,'supported_negative',(-.98,score,score),
                   {'rest_open':(0,1,1),'rest_closed':(0,0,0)})
    add('two_branch_cut','supported_negative',
        [('s','a',-.98),('a','g',None),('s','b',-.98),('b','g',None)],
        {'rest_open':(0,1,0,1),'rest_closed':(0,0,0,0)})
    chain_case('misleading_direction','noisy_evidence',(.92,.92,.92),{'declared':(0,1,1)})
    return cases


def condition_plan():
    return dict(protocol=PROTOCOL, engine_arms=list(ARMS), readout_policies=list(READOUT_POLICIES),
        training_counts=list(TRAINING_COUNTS), adaptive_config=codec.plain(AdaptiveConfig()),
        fixtures=fixtures(), support_contract=SUPPORT, frozen_memory=True,
        diagnostic_runs_per_task=1, readout_views_share_one_task=True,
        original_decision_preserved=True, hidden_truth_passed_to_diagnostic=False,
        retries=0, feedback_during_evaluation=False, measurement_requests_executed=0,
        score_sign_is_not_truth=True, evaluator_enumerations_not_fed_back=True,
        policy_view_count_is_not_inference_count=True)


def cells():
    for n in TRAINING_COUNTS:
        for i,c in enumerate(fixtures()):
            offset=(TRAINING_COUNTS.index(n)+i)%len(ARMS)
            for a in ARMS[offset:]+ARMS[:offset]:
                yield n,c,a
