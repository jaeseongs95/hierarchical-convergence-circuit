"""R0.3.2: 이미 생성된 판단의 근거 진단과 명시적인 보류 개입.

관측 score는 참값/보정 확률이 아니다. sign-v1은 선언된 방향성 지지 계약이다.
원시 decision/proof/trace/memory는 수정하지 않는다. 숨은 세계, 정답기, 새 경로 탐색을
호출하지 않는다. readout 개입은 별도 packet으로 남기며 참/거짓을 뒤집지 않는다.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from . import codec
from .model import AdaptiveDecision, ContractError, Observation, fingerprint
from .trace import check_chain

POLICIES = ('diagnostic_only', 'dependency_gate', 'blanket_unknown_gate')


@dataclass(frozen=True)
class SupportContract:
    min_abs_score: float = 0.0

    def __post_init__(self):
        v = self.min_abs_score
        if type(v) not in (int, float) or not isfinite(v) or not 0 <= v < 1:
            raise ContractError('min_abs_score must be finite in [0, 1)')

    def document(self) -> dict:
        return dict(schema='hcr-directional-support-v1', min_abs_score=float(self.min_abs_score),
                    zero_is_neutral=True, missing_is_unknown=True,
                    score_is_probability=False, support_is_truth=False)


def classify(score: float | None, assumed: bool, contract: SupportContract) -> str:
    if type(assumed) is not bool:
        raise ContractError('assumption must be bool, not integer')
    if score is None:
        return 'missing'
    if type(score) not in (int, float) or not isfinite(score) or not -1 <= score <= 1:
        raise ContractError('invalid observation score')
    if score == 0:
        return 'neutral'
    if abs(score) <= contract.min_abs_score:
        return 'below_threshold'
    return 'directional_support' if (score > 0) == assumed else 'sign_conflict'


def _seal(body: dict) -> dict:
    return dict(body, sha256=fingerprint(body))


def _unseal(packet: dict, schema: str) -> dict:
    if not isinstance(packet, dict) or packet.get('schema') != schema:
        raise ContractError('diagnostic schema mismatch')
    body = {k: v for k, v in packet.items() if k != 'sha256'}
    if packet.get('sha256') != fingerprint(body):
        raise ContractError('diagnostic checksum mismatch')
    return body


def diagnose(observation: Observation, decision: AdaptiveDecision, events: list,
             contract: SupportContract | None = None) -> dict:
    """실행 후 진단만 수행한다. source 검사는 formal proof의 독립 재증명이 아니다."""
    contract = contract or SupportContract()
    if not isinstance(contract, SupportContract) or not isinstance(observation, Observation) or not isinstance(decision, AdaptiveDecision):
        raise ContractError('typed observation/decision/contract required')
    if (decision.observation_digest != observation.digest or decision.observation_revision != observation.revision
            or decision.episode_id != observation.episode_id):
        raise ContractError('stale observation/decision binding')
    if decision.value is not None and type(decision.value) is not bool:
        raise ContractError('invalid decision value')
    if not events:
        raise ContractError('source event chain missing')
    check_chain(events, len(events), events[-1]['sha256'])
    d = codec.plain(decision)
    emitted = [e for e in events if e['event'] == 'r02_decision' and e['payload']['id'] == decision.id]
    starts = [e for e in events if e['event'] == 'r02_attempt_started' and e['payload']['decision_id'] == decision.id]
    if len(emitted) != 1 or emitted[0]['payload'] != d or len(starts) != 1 or starts[0]['payload']['observation'] != codec.plain(observation):
        raise ContractError('diagnostic source does not contain this exact decision/observation')
    networks = [e for e in events if e['event'] == 'r02_network' and e['payload']['kind'] == 'decision'
                and e['payload']['decision_id'] == decision.id and e['seq'] < emitted[0]['seq']]
    event = networks[-1] if networks else None
    net = event['payload'] if event else None
    if (net is None) != (decision.program_digest is None):
        raise ContractError('missing/unexpected source network')
    if net and (net['program_digest'] != decision.program_digest or fingerprint(net['program']) != decision.program_digest):
        raise ContractError('diagnostic program binding')
    edge_by_id = {e.id: (i, e) for i, e in enumerate(observation.edges)}
    state = dict(decision.state)
    assumptions = list(decision.proof.assumed_edges)
    if len(dict(assumptions)) != len(assumptions):
        raise ContractError('duplicate assumption')
    rows = []
    for edge_id, assumed in assumptions:
        if edge_id not in edge_by_id or type(assumed) is not bool:
            raise ContractError('assumption outside observation or not bool')
        slot, edge = edge_by_id[edge_id]
        if net is None or f'e:{slot}' not in state:
            raise ContractError('assumption lacks source state')
        terms = []
        for path_index, path in enumerate(net['program']['paths']):
            for position, value in enumerate(path):
                if value == slot:
                    key = f'p:{path_index}:{position}'
                    terms.append(dict(group=key, learned_drive=net['drives'].get(key, 0.0)))
        bound_uses = []
        for route in net['metadata']['routes']:
            for use in route['uses']:
                if slot in use['binding']['edge_order']:
                    bound_uses.append(dict(circuit_id=use['circuit_id'], circuit_version=use['circuit_version'],
                                           routing_prior=use['prior'], edge_order=list(use['binding']['edge_order'])))
        rows.append(dict(edge_id=edge_id, slot=slot, assumed=assumed, score=edge.score,
            observation_kind='missing' if edge.score is None else 'neutral' if edge.score == 0 else 'directional',
            support=classify(edge.score, assumed, contract), evidence_ref=observation.digest + ':' + edge_id,
            observed_drive=net['drives'].get(f'e:{slot}', 0.0), final_activation=state[f'e:{slot}'],
            relation_drives=terms, goal_learned_drive=net['drives'].get('goal', 0.0), routing_uses=bound_uses,
            drive_presence_is_not_causal_attribution=True))
    used = {x['edge_id'] for x in rows}
    gaps = [x['edge_id'] for x in rows if x['support'] != 'directional_support']
    proofs_reported = decision.proof.under_assumptions_valid
    if type(proofs_reported) is not bool:
        raise ContractError('invalid reported proof validity')
    coverage_ok = decision.value is not False or decision.graph_complete
    sufficient = (None if decision.value is None else
                  bool(proofs_reported and rows and not gaps and coverage_ok))
    # 이미 생성한 path만 검사한다. 새 path를 열거하거나 선택 proof를 교체하지 않는다.
    path_checks = []
    for path in decision.expanded_paths:
        if not path or any(type(i) is not int or not 0 <= i < len(observation.edges) for i in path):
            raise ContractError('invalid explored path')
        opened = all(classify(observation.edges[i].score, True, contract) == 'directional_support' for i in path)
        cuts = [observation.edges[i].id for i in path if classify(observation.edges[i].score, False, contract) == 'directional_support']
        path_checks.append(dict(slots=list(path), directionally_open=opened, observed_cut_edges=cuts))
    unknown_edges = [e.id for e in observation.edges if e.score is None or e.score == 0]
    outside = [e for e in unknown_edges if e not in used]
    to_measure = [x['edge_id'] for x in rows if x['support'] in ('missing', 'neutral', 'below_threshold')]
    conflicts = [x['edge_id'] for x in rows if x['support'] == 'sign_conflict']
    if decision.value is None:
        action = 'continue_expansion' if not decision.graph_complete else 'request_observation_or_abstain'
    elif not proofs_reported or not coverage_ok:
        action = 'inspect_invalid_or_incomplete_proof'
    elif to_measure:
        action = 'request_observation'
    elif conflicts:
        action = 'review_prior_or_alternative_method'
    else:
        action = 'retain_under_declared_contract'
    if decision.value is None:
        to_measure = sorted({observation.edges[i].id for p in decision.expanded_paths for i in p
                             if observation.edges[i].score is None or observation.edges[i].score == 0})
    return _seal(dict(schema='hcr-grounding-diagnostic-r032-v1',
        source=dict(observation_digest=observation.digest, observation_revision=observation.revision,
                    memory_digest=starts[0]['payload']['memory_hash'], memory_version=starts[0]['payload']['memory_version'],
                    decision_id=decision.id, decision_sha256=fingerprint(d), program_digest=decision.program_digest,
                    decision_event_seq=emitted[0]['seq'], decision_event_sha256=emitted[0]['sha256'],
                    network_event_sha256=event['sha256'] if event else None,
                    event_head=events[-1]['sha256'], event_count=len(events)),
        contract=contract.document(), original_value=decision.value, assumptions=rows,
        proof_validity_reported=proofs_reported, proof_independently_revalidated=False,
        graph_complete=decision.graph_complete, negative_coverage_required=decision.value is False,
        evidence_support_sufficient=sufficient, support_gap_edges=gaps,
        unknown_edges=unknown_edges, unknown_outside_selected_proof=outside,
        explored_path_checks=path_checks,
        suggestion=dict(action=action, edge_ids=to_measure, sign_conflict_edges=conflicts, executed=False),
        diagnostic_cost=dict(assumptions_checked=len(rows), source_event_count=len(events),
                             explored_path_edge_memberships=sum(len(p) for p in decision.expanded_paths),
                             kernel_ticks=0, new_task_inferences=0, counts_are_inventory_not_full_cpu_operations=True),
        boundaries=dict(decision_modified=False, memory_updated=False, truth_accessed=False,
                        new_paths_generated=False, support_is_external_correctness=False,
                        learned_prior_counted_as_observation=False)))


def apply_readout(decision: AdaptiveDecision, diagnostic: dict, policy: str = 'diagnostic_only') -> dict:
    """별도 readout 개입. 원 판단을 유지하거나 보류만 하며 반대 값을 만들어내지 않는다."""
    body = _unseal(diagnostic, 'hcr-grounding-diagnostic-r032-v1')
    if policy not in POLICIES or body['source']['decision_sha256'] != fingerprint(codec.plain(decision)):
        raise ContractError('readout policy or source mismatch')
    original = decision.value
    if original is None:
        accept, reason = False, 'original_abstention'
    elif policy == 'diagnostic_only':
        accept, reason = True, 'unmodified_diagnostic_control'
    elif policy == 'blanket_unknown_gate':
        accept = not body['unknown_edges']
        reason = 'blanket_no_unknown' if accept else 'blanket_unknown_abstention'
    else:
        accept = body['evidence_support_sufficient'] is True
        reason = 'supported_under_sign_contract' if accept else 'dependency_support_abstention'
    return _seal(dict(schema='hcr-grounded-readout-r032-v1', policy=policy,
        source_decision_id=decision.id, source_decision_sha256=fingerprint(codec.plain(decision)),
        diagnostic_sha256=diagnostic['sha256'], original_value=original,
        value=original if accept else None, accepted=accept, reason=reason,
        intervention=policy != 'diagnostic_only', original_decision_modified=False,
        truth_accessed=False, new_inferences=0, inference_cost_unchanged=True))


def compare_diagnostics(named: dict[str, dict]) -> dict:
    """이미 얻은 서로 다른 판단의 충돌 위치. 합의/중복 관측을 새 증거로 세지 않는다."""
    if len(named) < 2 or any(not isinstance(k, str) or not k for k in named):
        raise ContractError('at least two named diagnostics required')
    bodies = {k: _unseal(v, 'hcr-grounding-diagnostic-r032-v1') for k, v in named.items()}
    if (len({b['source']['observation_digest'] for b in bodies.values()}) != 1
            or len({b['source']['memory_digest'] for b in bodies.values()}) != 1
            or len({fingerprint(b['contract']) for b in bodies.values()}) != 1):
        raise ContractError('comparison requires same observation, memory and support contract')
    values = {k: b['original_value'] for k, b in bodies.items()}
    assignments = {k: {r['edge_id']: r['assumed'] for r in b['assumptions']} for k, b in bodies.items()}
    edges = sorted({edge for rows in assignments.values() for edge in rows})
    conflicts = [dict(edge_id=e, assumptions={k: a[e] for k, a in assignments.items() if e in a})
                 for e in edges if len({a[e] for a in assignments.values() if e in a}) > 1]
    supported = all(b['evidence_support_sufficient'] is True for b in bodies.values())
    resolved = [v for v in values.values() if v is not None]
    if len(set(resolved)) > 1:
        status = 'decision_conflict'
    elif len(resolved) != len(values):
        status = 'incomplete_or_abstained'
    elif supported:
        status = 'agreement_under_contract'
    else:
        status = 'agreement_with_support_gap'
    return _seal(dict(schema='hcr-grounding-conflict-r032-v1',status=status,
        sources={k: v['sha256'] for k,v in named.items()}, values=values,
        assumption_conflicts=conflicts, support_gap_edges=sorted({e for b in bodies.values() for e in b['support_gap_edges']}),
        unique_evidence_refs=sorted({r['evidence_ref'] for b in bodies.values() for r in b['assumptions']}),
        evidence_multiplicity_is_confidence=False, selects_winner=False, new_inferences=0))
