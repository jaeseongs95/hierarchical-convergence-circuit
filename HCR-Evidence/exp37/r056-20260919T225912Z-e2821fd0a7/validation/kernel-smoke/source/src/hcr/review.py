"""R0.3.3 근거 부족 뒤 작업 선택. 정답·가능한 세계는 이 모듈에 전달하지 않는다.

최초 readout은 정상 finish branch로 보존한다. 추가 전개는 같은 live session의
남은 frontier에서 수행한다. 관측/정책 전환에 의한 새 추론은 처음부터 실행하며
그 비용을 모두 합산한다. 근거 검사는 R0.3.2 계약이고 정답 보정기가 아니다.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, fields
from math import isfinite
from time import perf_counter
from typing import Callable
from . import codec
from .model import AdaptiveConfig, AdaptiveCost, ContractError, Mode, Observation, fingerprint
from .circuits import AdaptiveMemory
from .sessions import AdaptiveSession, verify_packet
from .grounding import diagnose, apply_readout
from .trace import Trace

POLICIES = ('hold', 'expand_only', 'observe_first', 'expand_then_observe', 'route_review')


@dataclass(frozen=True)
class ReviewLimits:
    max_extra_advances: int = 8
    max_extra_kernel_ticks: int = 2048
    max_measurements: int = 3

    def __post_init__(self):
        for name, upper in (('max_extra_advances', 128), ('max_extra_kernel_ticks', 100000), ('max_measurements', 16)):
            if type(getattr(self, name)) is not int or not 0 <= getattr(self, name) <= upper:
                raise ContractError('bounded review budget: ' + name)


def sealed(body: dict) -> dict:
    return dict(body, sha256=fingerprint(body))


def unseal(packet: dict, schema: str) -> dict:
    if not isinstance(packet, dict) or packet.get('schema') != schema:
        raise ContractError('review packet schema')
    body = {k: v for k, v in packet.items() if k != 'sha256'}
    if packet.get('sha256') != fingerprint(body):
        raise ContractError('review packet checksum')
    return body


def pending_cost(session: AdaptiveSession) -> dict:
    p = session.current['pending']
    if p is None:
        raise ContractError('review session must retain its pending execution')
    return {f.name: p['cost'][f.name] for f in fields(AdaptiveCost)}


def capture_candidate(session: AdaptiveSession, segment: int) -> dict:
    """원본 session은 바꾸지 않고 별도 finish branch의 실제 proof를 만든다."""
    before = session.packet()
    started = perf_counter()
    d, packet = session.fork_readout()
    obs = codec.observation_from(before['document']['engine']['pending']['observation'])
    dg = diagnose(obs, d, packet['document']['events'])
    readout = apply_readout(d, dg, 'dependency_gate')
    if session.packet() != before:
        raise ContractError('candidate readout mutated the continuing branch')
    ref = dict(segment=segment, generation=session.generation, ready_sha256=before['sha256'],
               finished_sha256=packet['sha256'])
    return dict(candidate_id='review-candidate-' + fingerprint(ref), reference=ref,
                decision=codec.plain(d), packet=packet, diagnostic=dg, readout=readout,
                capture_seconds=perf_counter() - started,
                proof_finish_seconds=d.cost['wall_seconds'] - before['document']['engine']['pending']['active_seconds'])


def prepare_baseline(observation: Observation, config: AdaptiveConfig, memory: AdaptiveMemory,
                     *, judgment_prior: str = 'legacy') -> dict:
    started = perf_counter()
    s = AdaptiveSession(config, memory, session_id='review-base-' + observation.digest[:24],
                        judgment_prior=judgment_prior)
    s.begin(observation, Mode.FROZEN_EVAL)
    while s.phase == 'running':
        s.advance()
    first = capture_candidate(s, 0)
    return sealed(dict(schema='hcr-review-baseline-r033-v1', ready=s.packet(), first=first,
                       observation=codec.plain(observation), judgment_prior=judgment_prior,
                       preparation_seconds=perf_counter() - started))


def verify_baseline(baseline: dict) -> None:
    b = unseal(baseline, 'hcr-review-baseline-r033-v1')
    verify_packet(b['ready'])
    verify_packet(b['first']['packet'])
    core = b['ready']['document']['engine']
    p = core['pending']
    if p is None or not p['ready'] or p['mode'] != 'frozen_eval' or p['observation'] != b['observation']:
        raise ContractError('invalid initial review boundary')
    if b['first']['reference']['ready_sha256'] != b['ready']['sha256']:
        raise ContractError('initial candidate not linked to retained state')
    fd = b['first']['packet']['document']
    if (fd['transitions'][:-1] != b['ready']['document']['transitions']
            or fd['events'][:-1] != b['ready']['document']['events']
            or fd['transitions'][-1]['operation'] != 'finish'
            or fd['events'][-1]['payload'] != b['first']['decision']):
        raise ContractError('initial finish branch differs')
    expected_dg = diagnose(codec.observation_from(b['observation']), codec.adaptive_decision_from(b['first']['decision']), fd['events'])
    if b['first']['diagnostic'] != expected_dg or b['first']['readout'] != apply_readout(codec.adaptive_decision_from(b['first']['decision']), expected_dg, 'dependency_gate'):
        raise ContractError('initial diagnostic or gate was changed')
    ref = b['first']['reference']
    if (ref != dict(segment=0, generation=len(b['ready']['document']['transitions'])-1,
                    ready_sha256=b['ready']['sha256'], finished_sha256=b['first']['packet']['sha256'])
            or b['first']['candidate_id'] != 'review-candidate-' + fingerprint(ref)):
        raise ContractError('initial candidate identity')
    from .prior_policy import read_scope
    if read_scope(core) != b['judgment_prior']:
        raise ContractError('initial judgment policy binding')


def measurement_request(obs: Observation, candidate: dict, ordinal: int, edge_id: str) -> dict:
    if edge_id not in {e.id for e in obs.edges} or type(ordinal) is not int or ordinal < 1:
        raise ContractError('measurement target/ordinal')
    return sealed(dict(schema='hcr-review-measurement-request-v1', ordinal=ordinal,
        source_candidate_id=candidate['candidate_id'], observation_digest=obs.digest,
        episode_id=obs.episode_id, from_revision=obs.revision, next_revision=obs.revision + 1,
        edge_ids=[edge_id], reason='selected_proof_or_explored_path_support_gap'))


def consume_measurement(obs: Observation, request: dict, reply: dict) -> tuple[Observation | None, str]:
    """provider 계약 검증. engine에는 요청한 score만 공개된다. topology는 변경 불가."""
    req = unseal(request, 'hcr-review-measurement-request-v1')
    if (req['observation_digest'] != obs.digest or req['episode_id'] != obs.episode_id
            or req['from_revision'] != obs.revision or req['next_revision'] != obs.revision + 1):
        raise ContractError('stale measurement request')
    if (not isinstance(reply, dict) or set(reply) != {'request_sha256', 'status', 'scores', 'source'}
            or reply['request_sha256'] != request['sha256']
            or reply['status'] not in ('measured', 'unavailable')
            or not isinstance(reply['source'], str) or not reply['source']
            or not isinstance(reply['scores'], dict)):
        raise ContractError('invalid measurement response binding')
    if reply['status'] == 'unavailable':
        if reply['scores']:
            raise ContractError('unavailable response includes measurements')
        return None, 'measurement_unavailable'
    if set(reply['scores']) != set(req['edge_ids']):
        raise ContractError('unrequested/missing measurement edge')
    for score in reply['scores'].values():
        if score is not None and (type(score) not in (int, float) or not isfinite(score) or not -1 <= score <= 1):
            raise ContractError('measurement score must be finite, non-boolean, within [-1,1]')
    raw = codec.plain(obs)
    changed = False
    for e in raw['edges']:
        if e['id'] in reply['scores']:
            score = reply['scores'][e['id']]
            changed |= score != e['score']
            e['score'] = score
    if not changed:
        return None, 'measurement_no_new_information'
    raw['revision'] = req['next_revision']
    return codec.observation_from(raw), 'measurement_applied'


def tick_bound(core: dict, config: AdaptiveConfig) -> int:
    p = core['pending']
    pool = core['switches']['use_circuits'] and p['revision_of'] is None and bool(core['memory']['circuits'])
    return config.kernel.max_ticks * (1 + int(pool))


def choose_action(policy: str, core: dict, candidate: dict | None, used: dict,
                  limits: ReviewLimits, config: AdaptiveConfig, switched: bool) -> tuple[str, str | None]:
    """公開状態だけで次の作業を選ぶ。対象が必要十分/最適だとは仮定しない。"""
    p = core['pending']
    if p is None:
        raise ContractError('missing retained computation')
    if p['ready'] and candidate is not None and candidate['readout']['accepted']:
        return 'stop_supported', None
    if policy == 'hold':
        return 'stop_gate', None
    if p['failure_reason'] is not None:
        return 'stop_engine_failure', None
    affordable = (used['extra_advances'] < limits.max_extra_advances
                  and used['extra_kernel_ticks'] + tick_bound(core, config) <= limits.max_extra_kernel_ticks)
    if not p['ready']:
        return ('advance', None) if affordable else ('stop_compute_budget', None)
    if policy == 'route_review':
        if switched or not affordable:
            return ('stop_review_finished', None) if switched else ('stop_compute_budget', None)
        return 'restart_route_only', None
    if policy in ('expand_only', 'expand_then_observe') and p['workspace']['frontier']:
        if not affordable:
            return 'stop_compute_budget', None
        return 'continue_dependency', None
    if policy == 'expand_only':
        return 'stop_frontier_exhausted', None
    if policy in ('observe_first', 'expand_then_observe'):
        if used['measurements'] >= limits.max_measurements:
            return 'stop_measurement_budget', None
        # 관측을 받을 수 있어도 남은 계산 예산이 없으면 비용만 쓰고 재시도하지 않는다.
        if not affordable:
            return 'stop_compute_budget', None
        if candidate is None:
            return 'stop_no_diagnostic', None
        targets = candidate['diagnostic']['suggestion']['edge_ids']
        if not targets:
            return 'stop_no_measurement_target', None
        return 'request_measurement', targets[0]
    raise ContractError('unknown review policy')


class ReviewFlow:
    """한 paired baseline의 추가 작업. 숨은 세계는 observer 외부에만 존재한다."""
    def __init__(self, baseline: dict, policy: str, limits: ReviewLimits | None = None):
        if policy not in POLICIES:
            raise ContractError('unknown review policy')
        init_started = perf_counter()
        verify_baseline(baseline)
        self.baseline = deepcopy(baseline)
        self.policy = policy
        self.limits = limits or ReviewLimits()
        if not isinstance(self.limits, ReviewLimits):
            raise ContractError('typed review limits required')
        self.trace = Trace()
        self.validation_seconds = perf_counter() - init_started
        self._executed = False

    def run(self, observer: Callable[[dict], dict] | None = None) -> dict:
        if self._executed:
            raise ContractError('review flow cannot be executed twice')
        self._executed = True
        started = perf_counter()
        b = self.baseline
        s = AdaptiveSession.from_packet(b['ready'])
        cfg = codec.adaptive_config_from(s.current['config'])
        memory = s.memory_document
        obs = codec.observation_from(b['observation'])
        segments = [s]
        candidates = [deepcopy(b['first'])]
        candidate = candidates[-1]
        used = dict(extra_advances=0, extra_kernel_ticks=0, measurements=0, restarts=0)
        switched = False
        self.trace.emit('review_start', dict(baseline_sha256=b['sha256'], policy=self.policy,
            limits=codec.plain(self.limits), initial_candidate=candidate['candidate_id']))
        stop = None
        for turn in range(512):
            core = s.current
            action, target = choose_action(self.policy, core, candidate, used, self.limits, cfg, switched)
            self.trace.emit('review_action', dict(turn=turn, action=action, target=target,
                segment=len(segments)-1, reference=s.reference,
                source_candidate=None if candidate is None else candidate['candidate_id'], used=dict(used)))
            if action.startswith('stop_'):
                stop = action
                break
            if action == 'continue_dependency':
                s.continue_dependency()
                candidate = None
            elif action == 'advance':
                before = pending_cost(s)
                s.advance()
                after = pending_cost(s)
                delta = after['kernel_ticks'] - before['kernel_ticks']
                if not 0 <= delta <= tick_bound(core, cfg):
                    raise ContractError('review quantum exceeded reservation')
                used['extra_advances'] += 1
                used['extra_kernel_ticks'] += delta
                if s.phase == 'readout_ready':
                    candidate = capture_candidate(s, len(segments)-1)
                    candidates.append(candidate)
                    self.trace.emit('review_candidate', dict(candidate_id=candidate['candidate_id'],
                        reference=candidate['reference'], raw_value=candidate['decision']['value'],
                        accepted=candidate['readout']['accepted']))
            elif action in ('request_measurement', 'restart_route_only'):
                if action == 'request_measurement':
                    used['measurements'] += 1
                    req = measurement_request(obs, candidate, used['measurements'], target)
                    self.trace.emit('review_measurement_request', req)
                    reply = (observer(deepcopy(req)) if observer else
                        dict(request_sha256=req['sha256'], status='unavailable', scores={}, source='no_provider'))
                    # 응답은 검증 실패해도 raw trace에 남긴다. 자동 재요청은 없다.
                    self.trace.emit('review_measurement_response', reply)
                    revised, status = consume_measurement(obs, req, reply)
                    self.trace.emit('review_measurement_consumed', dict(status=status,
                        observation=None if revised is None else codec.plain(revised)))
                    if revised is None:
                        stop = status
                        break
                    obs = revised
                    scope = b['judgment_prior']
                else:
                    scope = 'route_only'
                    switched = True
                used['restarts'] += 1
                s = AdaptiveSession(cfg, AdaptiveMemory.from_document(memory, cfg),
                    session_id='review-segment-' + str(len(segments)) + '-' + obs.digest[:20], judgment_prior=scope)
                s.begin(obs, Mode.FROZEN_EVAL)
                segments.append(s)
                candidate = None
                self.trace.emit('review_restarted', dict(segment=len(segments)-1,
                    reason=action, observation=codec.plain(obs), judgment_prior=scope,
                    initial_reference=s.reference, previous_work_discarded_from_cost=False))
        if stop is None:
            raise ContractError('review controller bound exceeded')
        packets = [segment.packet() for segment in segments]
        if any(packet['document']['engine']['memory'] != memory for packet in packets):
            raise ContractError('review mutated frozen memory')
        # pending costs are cumulative within a segment. Never sum each readout's cumulative cost.
        totals = {f.name: sum(pending_cost(segment)[f.name] for segment in segments) for f in fields(AdaptiveCost)}
        proof_items = sum(len(c['decision']['proof']['nodes']) for c in candidates)
        totals['proof_nodes_reconstructed'] += proof_items
        totals['wall_seconds'] = (sum(segment.current['pending']['active_seconds'] for segment in segments)
                                  + sum(c['proof_finish_seconds'] for c in candidates))
        base_core = b['ready']['document']['engine']['pending']
        accepted = candidate is not None and candidate['readout']['accepted'] and s.phase == 'readout_ready'
        selected = candidate['candidate_id'] if accepted else None
        value = candidate['decision']['value'] if accepted else None
        self.trace.emit('review_finished', dict(reason=stop, value=value, selected_candidate=selected, used=used))
        return dict(schema='hcr-review-result-r033-v1', baseline_sha256=b['sha256'], policy=self.policy,
            limits=codec.plain(self.limits), candidates=candidates, segments=packets, controller=self.trace.records,
            result=dict(value=value, reason=stop, selected_candidate=selected), usage=used,
            cost=dict(engine=totals, initial_advances=sum(t['operation']=='advance' for t in b['ready']['document']['transitions']),
                initial_kernel_ticks=base_core['cost']['kernel_ticks'], extra_kernel_ticks=used['extra_kernel_ticks'],
                proof_readout_items=proof_items, measurement_features=used['measurements'],
                kernel_counters_exclude_controller=True),
            timing=dict(review_wall_seconds=perf_counter()-started, validation_seconds=self.validation_seconds, baseline_seconds=b['preparation_seconds'],
                candidate_capture_seconds=sum(c['capture_seconds'] for c in candidates[1:]),
                measurement_latency_not_simulated=True),
            boundaries=dict(original_decision_preserved=True, selected_value_requires_new_computation=True,
                candidate_id_is_global_local_engine_ids_can_repeat=True, frozen_memory=True,
                explicit_same_state_continuation=True, observation_restart_is_not_frontier_resume=True,
                policy_restart_is_not_free=True, no_hidden_world_input=True,
                no_host_proof_repair=True, no_claim_of_minimal_query=True,
                lifelong_learning=False, controller_checkpoint_resume=False))
