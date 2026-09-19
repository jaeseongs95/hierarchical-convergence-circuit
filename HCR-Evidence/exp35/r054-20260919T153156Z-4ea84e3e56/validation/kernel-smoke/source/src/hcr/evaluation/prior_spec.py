"""EXP-12의 사전 선언 조건. hidden truth는 이 평가 계층 밖으로 전달하지 않는다."""
from __future__ import annotations
from dataclasses import replace
from .. import codec
from ..model import AdaptiveConfig
from ..tasks.toy_world import chain, diamond

PROTOCOL = 'exp12-r031-prior-scope-v1'
ARMS = ('legacy', 'route_only', 'graph_only')
TRAINING_COUNTS = (3, 6, 9)
SCORES = (('strong_negative', -.98), ('weak_negative', -.06), ('zero', 0.0),
          ('weak_positive', .06), ('strong_positive', .98), ('missing', None))


def arm_options(arm):
    if arm not in ARMS:
        raise ValueError('unknown EXP-12 arm')
    return dict(use_circuits=arm != 'graph_only', judgment_prior='route_only' if arm == 'route_only' else 'legacy')


def training_world(i):
    return chain('prior-train-' + str(i), (True, True, True), prefix='train-' + str(i))


def fixtures():
    """조건명은 evaluator용이다. 추론기는 observation만 받는다.

    0/결측의 두 world는 같은 추론에 대한 대조 평가이며 추론 표본을 두 배로 세지 않는다.
    """
    result = []
    def append(name, family, world, first_score=None, paired=False):
        obs = world.observation
        truths = {'declared': dict(world.hidden)}
        if paired:
            truths = {'first_open': {e.id: True for e in obs.edges},
                      'first_closed': {e.id: i != 0 for i, e in enumerate(obs.edges)}}
        result.append(dict(name=name, family=family, observation=codec.plain(obs),
                           worlds=truths, first_score=first_score, paired_hidden_worlds=paired))
    for name, score in SCORES:
        truth = score is None or score >= 0
        w = chain('prior-sweep', (truth, True, True), (score, .92, .92), prefix='sweep')
        append('sweep_' + name, 'score_sweep', w, score, score is None or score == 0)
    append('familiar', 'preservation', chain('prior-familiar', (True,)*3))
    append('counterfactual', 'preservation', chain('prior-counterfactual', (False, True, True)))
    append('longer', 'preservation', chain('prior-longer', (True,)*4))
    append('diamond', 'preservation', diamond('prior-diamond', (False, True, True, True)))
    w = chain('prior-renamed', (True,)*3, prefix='renamed-identity')
    append('renamed_reordered', 'preservation', replace(w, observation=replace(w.observation, edges=tuple(reversed(w.observation.edges)))))
    append('all_missing', 'identifiability', chain('prior-missing', (True,)*3, (None,)*3), paired=True)
    append('all_zero', 'identifiability', chain('prior-zero', (True,)*3, (0.0,)*3), paired=True)
    return result


def condition_plan():
    return dict(protocol=PROTOCOL, arms=list(ARMS), training_counts=list(TRAINING_COUNTS),
                adaptive_config=codec.plain(AdaptiveConfig()), fixtures=fixtures(),
                frozen_evaluation=True, retries=0, hidden_truth_passed_to_engine=False,
                case_arm_repeats=1, fixed_network_source='last_legacy_decision_network',
                fixed_network_scopes=['legacy', 'route_only'], first_arm_rotation=True,
                no_candidate_or_answer_host_correction=True)


def cells():
    for n in TRAINING_COUNTS:
        for index, case in enumerate(fixtures()):
            offset = (TRAINING_COUNTS.index(n) + index) % len(ARMS)
            for arm in ARMS[offset:] + ARMS[:offset]:
                yield n, case, arm
