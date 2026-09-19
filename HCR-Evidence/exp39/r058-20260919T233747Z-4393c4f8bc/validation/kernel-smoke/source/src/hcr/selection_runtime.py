"""R0.3.4 실험 adapter. 기존 AdaptiveSession/finish를 그대로 사용한다.

정답이나 possible worlds를 인자로 받지 않는다. support-first는 명시적인
sidecar proof 후보이며 기존 finish decision을 새 증명으로 덮어쓰지 않는다.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from time import perf_counter
from typing import Callable

from .selection_control import choose_action
from .selection import (SelectionLimits, digest, empty_usage, project_candidate,
                        require, select_supported)

ARMS = ('hold', 'expand_only', 'restart_same', 'restart_route_only',
        'select_only', 'expand_then_select', 'observe_first')


def prepare_running(observation, config, memory, *, initial_advances: int = 1) -> dict:
    """순수 계산 대조: 아직 running인 경계. 가짜 최초 decision을 만들지 않는다."""
    from .sessions import AdaptiveSession
    from .model import Mode
    from . import codec
    started = perf_counter()
    s = AdaptiveSession(config, memory, session_id='selection-running-' + observation.digest[:20],
                        use_circuits=False, judgment_prior='route_only')
    s.begin(observation, Mode.FROZEN_EVAL)
    for _ in range(initial_advances):
        require(s.phase == 'running', 'computation control reached a decision before prescribed boundary')
        s.advance()
    require(s.phase == 'running', 'computation control must retain an unfinished dependency')
    body = dict(schema='hcr-selection-running-baseline-r034-v1', ready=s.packet(), first=None,
        observation=codec.plain(observation), judgment_prior='route_only',
        preparation_seconds=perf_counter() - started, initial_advances=initial_advances)
    return dict(body, sha256=digest(body))


class SelectionFlow:
    """한 baseline에서 한 번만 실행. 오류 전 action도 sink에 즉시 보존한다."""
    def __init__(self, baseline: dict, arm: str, *, limits=None, selection_limits=None,
                 event_sink: Callable[[dict], None] | None = None):
        from .review import ReviewLimits
        require(arm in ARMS + ('continue',), 'unknown EXP-15 arm')
        self.baseline = deepcopy(baseline)
        self.arm = arm
        self.limits = limits or ReviewLimits()
        self.selection_limits = selection_limits or SelectionLimits()
        self.event_sink = event_sink
        self.actions = []
        self._executed = False
        self._sessions = []
        self._candidates = []
        self._selections = []
        self._reference_flow = None

    def run(self, observer=None) -> dict:
        from . import codec
        from .circuits import AdaptiveMemory
        from .model import Mode
        from .sessions import AdaptiveSession
        from .review import ReviewFlow, capture_candidate, pending_cost, tick_bound
        from .prior_policy import read_scope
        require(not self._executed, 'selection flow is single use')
        self._executed = True
        b = self.baseline
        require(b.get('sha256') == digest({k:v for k,v in b.items() if k != 'sha256'}), 'baseline checksum')
        if self.arm == 'observe_first':
            require(b['first'] is not None, 'observation reference requires ready baseline')
            # EXP-14 동작 자체를 참조 조건으로 재사용한다. 세부 로그는 old raw controller에도 있다.
            flow = ReviewFlow(b, 'observe_first', self.limits)
            self._reference_flow = flow
            try:
                result = flow.run(observer)
            except BaseException:
                if self.event_sink:
                    for e in flow.trace.records:
                        self.event_sink(dict(kind='exp14-reference-partial', event=e))
                raise
            return dict(schema='hcr-selection-observation-reference-r034-v1',
                        baseline_sha256=b['sha256'], arm=self.arm, reference=result)
        require(observer is None, 'non-observation arm must not receive a provider')
        started = perf_counter()
        s = AdaptiveSession.from_packet(b['ready'])
        cfg = codec.adaptive_config_from(s.current['config'])
        memory = s.memory_document
        observation = codec.observation_from(b['observation'])
        segments = [s]
        candidates = [deepcopy(b['first'])] if b['first'] is not None else []
        candidate = candidates[-1] if candidates else None
        selections = []; checked = set(); selected = None
        self._sessions = segments; self._candidates = candidates; self._selections = selections
        usage = dict(extra_advances=0, extra_kernel_ticks=0, restarts=0, selection_calls=0, **empty_usage())
        stop = None
        for turn in range(1024):
            core = s.current; p = core['pending']; seg = len(segments)-1
            require(p is not None, 'retained session lost pending computation')
            action = choose_action(arm=self.arm,ready=p['ready'],failed=p['failure_reason'] is not None,
                frontier=bool(p['workspace']['frontier']),candidate_id=None if candidate is None else candidate['candidate_id'],
                native_accepted=candidate is not None and candidate['readout']['accepted'],
                selection_accepted=selected is not None and selected['accepted'],
                checked=candidate is not None and candidate['candidate_id'] in checked,restarts=usage['restarts'],
                extra_advances=usage['extra_advances'],extra_ticks=usage['extra_kernel_ticks'],
                max_advances=self.limits.max_extra_advances,max_ticks=self.limits.max_extra_kernel_ticks,
                tick_reservation=tick_bound(core,cfg))
            record = dict(ordinal=turn, action=action, segment=seg, generation=s.generation,
                reference=s.reference, source_candidate_id=None if candidate is None else candidate['candidate_id'],
                usage_before=deepcopy(usage))
            self.actions.append(record)
            if self.event_sink:
                self.event_sink(deepcopy(record))
            if action.startswith('stop_'):
                stop = action; break
            if action == 'select_existing_proof':
                view = project_candidate(candidate)
                packet = select_supported(view, self.selection_limits, {k:usage[k] for k in empty_usage()})
                selections.append(packet); selected = packet; checked.add(candidate['candidate_id'])
                usage['selection_calls'] += 1
                usage.update(packet['usage_after'])
            elif action == 'continue_dependency':
                s.continue_dependency(); candidate = None; selected = None
            elif action == 'advance':
                before = pending_cost(s)
                s.advance()
                delta = pending_cost(s)['kernel_ticks'] - before['kernel_ticks']
                require(0 <= delta <= tick_bound(core, cfg), 'advance exceeded reserved kernel budget')
                usage['extra_advances'] += 1; usage['extra_kernel_ticks'] += delta
                if s.phase == 'readout_ready':
                    candidate = capture_candidate(s, seg); candidates.append(candidate); selected = None
            else:
                flags = core['switches']
                scope = b['judgment_prior'] if self.arm == 'restart_same' else 'route_only'
                s = AdaptiveSession(cfg, AdaptiveMemory.from_document(memory, cfg),
                    session_id='selection-restart-' + observation.digest[:20], judgment_prior=scope, **flags)
                s.begin(observation, Mode.FROZEN_EVAL)
                require(s.phase == 'running', 'unexpected immediate restart readout')
                segments.append(s); candidate = None; selected = None; usage['restarts'] += 1
        require(stop is not None, 'controller event bound exhausted')
        packets = [x.packet() for x in segments]
        require(all(x['document']['engine']['memory'] == memory for x in packets), 'frozen memory changed')
        origin = 'none'; value = None; selected_id = None
        if stop == 'stop_supported_native':
            origin = 'native'; value = candidate['decision']['value']; selected_id = candidate['candidate_id']
        elif stop == 'stop_supported_selection':
            origin = 'selection'; value = selected['value']; selected_id = selected['candidate_id']
        initial = b['ready']['document']['engine']['pending']['cost']['kernel_ticks']
        initial_proof_nodes = 0 if b['first'] is None else len(b['first']['decision']['proof']['nodes'])
        native_nodes = sum(len(c['decision']['proof']['nodes']) for c in candidates)
        total_kernel = sum(x['document']['engine']['pending']['cost']['kernel_ticks'] for x in packets)
        require(total_kernel == initial + usage['extra_kernel_ticks'], 'segment cumulative cost mismatch')
        return dict(schema='hcr-selection-flow-r034-v1', baseline_sha256=b['sha256'], arm=self.arm,
            limits=asdict(self.limits), selection_limits=asdict(self.selection_limits),
            segments=packets, candidates=candidates, selections=selections, actions=self.actions,
            result=dict(value=value, origin=origin, candidate_id=selected_id, reason=stop), usage=usage,
            cost=dict(initial_kernel_ticks=initial, pathway_kernel_ticks=total_kernel,
                initial_native_proof_nodes=initial_proof_nodes, native_proof_nodes=native_nodes,
                extra_native_proof_nodes=native_nodes-initial_proof_nodes,
                sidecar_proof_nodes=usage['proof_nodes'], measurements=0),
            timing=dict(wall_seconds=perf_counter()-started,
                selection_wall_seconds=sum(x['wall_seconds'] for x in selections)),
            boundaries=dict(original_candidate_preserved=True, frozen_memory=True, observation_unchanged=True,
                support_selection_is_sidecar=True, no_value_flips_by_selection=True,
                selection_cost_is_not_kernel_cost=True, not_autonomous_policy_learning=True))

    def partial_evidence(self) -> dict:
        """실패 시점의 마지막으로 commit된 session 및 최초 응답을 보존한다."""
        return dict(actions=deepcopy(self.actions),
            segments=[s.packet() for s in self._sessions],
            candidates=deepcopy(self._candidates),selections=deepcopy(self._selections),
            exp14_reference_trace=[] if self._reference_flow is None else self._reference_flow.trace.records)
