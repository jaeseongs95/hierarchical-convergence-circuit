"""R037 native 흐름을 재사용한다. 외부 world/조건 라벨/기회 진단은 받지 않는다."""
from __future__ import annotations
from copy import deepcopy
from time import perf_counter
from r037_online_selection.backend import NativeBackend
from r037_online_selection.runtime import OnlineTrial
from .contracts import (ARMS, BASE_POLICY, Budget, SELECTION_LIMITS, USAGE_KEYS,
                        digest, require, finite_nonnegative, terminal_readout)


class TimingTrial:
    def __init__(self, observation: dict, config: dict, memory: dict, scope: str, arm: str,
                 budget: Budget | None = None, *, backend=None, event_sink=None):
        require(arm in ARMS, '미등록 EXP-19 실험군')
        self.arm = arm
        self.backend = backend if backend is not None else NativeBackend()
        self.event_sink = event_sink
        self.executed = False
        self.base = None
        self.posthoc_events = []
        self.worker = OnlineTrial(observation, config, memory, scope, BASE_POLICY[arm],
            budget, backend=self.backend,
            event_sink=lambda e:self._send(dict(event='native_action', record=e)))

    def _send(self, event: dict) -> None:
        if self.event_sink is not None:
            self.event_sink(deepcopy(event))

    def _post_event(self, name: str, **payload) -> None:
        e = dict(ordinal=len(self.posthoc_events), event=name, **deepcopy(payload))
        self.posthoc_events.append(e)
        self._send(dict(event='posthoc_action', record=e))

    def run(self) -> dict:
        require(not self.executed, '단일 trial 재실행/retry 금지')
        self.executed = True
        started = perf_counter()
        self.base = base = self.worker.run()
        self._send(dict(event='base_completed', base_sha256=digest(base)))
        result = None
        status = 'not_applicable'
        if self.arm == 'posthoc_support':
            candidate, status = terminal_readout(base)
            if candidate is not None:
                live_before = self.worker.session.packet()
                base_hash = digest(base)
                view = self.backend.project(candidate)
                view_hash = digest(view)
                ordinal = len(base['candidates']) - 1
                self._post_event('selection_requested', readout_ordinal=ordinal,
                    input_sha256=view_hash, candidate_sha256=digest(candidate),
                    policy='support_first', after_base_stop=True)
                result = self.backend.select(view, 'support_first', dict(SELECTION_LIMITS))
                require(digest(base) == base_hash and digest(view) == view_hash and
                        self.worker.session.packet() == live_before,
                        '사후 선택이 원 native/session/view를 변경했습니다.')
                require(type(result['accepted']) is bool and
                        result['value'] is (view['raw_value'] if result['accepted'] else None),
                        '사후 proof 선택이 raw 값을 뒤집었습니다.')
                require(result['policy'] == 'support_first' and result['input_sha256'] == view_hash and
                        result['limits'] == SELECTION_LIMITS, '사후 selector 출처/예산 불일치')
                require(set(result['usage']) == set(USAGE_KEYS) and
                        all(type(v) is int and v >= 0 for v in result['usage'].values()), '사후 비용 계약')
                require('wall_seconds' in result and finite_nonnegative(result['wall_seconds']), '사후 시간 계약')
                self._post_event('selection_committed', result=result)
                status = 'selected'
        if self.arm != 'posthoc_support':
            final = dict(source='base_online', **deepcopy(base['adoption']))
        else:
            accepted = result is not None and result['accepted']
            final = dict(source='posthoc', accepted=accepted,
                value=result['value'] if accepted else None,
                reason=('posthoc_' + result['reason']) if result is not None else 'posthoc_' + status,
                policy='support_first', readout_ordinal=len(base['candidates'])-1 if accepted else None,
                candidate_id=base['candidates'][-1]['candidate_id'] if accepted else None,
                proof_sha256=digest(result['proof']) if accepted else None)
        usage = dict(native_kernel_ticks=base['usage']['initial_kernel_ticks']+base['usage']['extra_kernel_ticks'],
            online_selection_calls=base['usage']['selection_calls'],
            online_selection=deepcopy(base['usage']['selection']),
            posthoc_selection_calls=int(result is not None),
            posthoc_selection={k:0 if result is None else result['usage'][k] for k in USAGE_KEYS})
        self._send(dict(event='arm_finished', final=final))
        return dict(schema='hcr-timing-trial-r038-v1', arm=self.arm, backend=self.backend.kind,
            base=base, posthoc_status=status, posthoc_selection=result,
            posthoc_events=deepcopy(self.posthoc_events), final=final, usage=usage,
            wall_seconds=perf_counter()-started)

    def partial_evidence(self) -> dict:
        return dict(schema='hcr-timing-partial-r038-v1', arm=self.arm,
            base=deepcopy(self.base), native_partial=self.worker.partial_evidence(),
            posthoc_events=deepcopy(self.posthoc_events))
