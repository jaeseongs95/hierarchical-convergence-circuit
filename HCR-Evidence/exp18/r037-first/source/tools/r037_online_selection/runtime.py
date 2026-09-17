"""온라인 채택 제어기. case 이름, world, 평가용 진단은 인자로 받지 않는다.

AdaptiveSession.finish의 원 판단을 보존하고, 별도 adoption이 실행의 종료를 제어한다.
이를 native kernel 자체의 변경이나 학습된 자율 repair 정책으로 부르지 않는다.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from time import perf_counter
from .backend import NativeBackend
from .contracts import (Budget, POLICIES, SCOPES, SELECTION_LIMITS,
                        SELECTION_BUDGET_REASONS, USAGE_KEYS, digest, require,
                        validate_public_observation)


class OnlineTrial:
    def __init__(self, observation: dict, config: dict, memory: dict, scope: str,
                 policy: str, budget: Budget | None = None, *, backend=None, event_sink=None):
        validate_public_observation(observation)
        require(scope in SCOPES and policy in POLICIES, '미등록 prior/선택 정책')
        self.observation = deepcopy(observation)
        self.config = deepcopy(config); self.memory = deepcopy(memory)
        self.scope = scope; self.policy = policy; self.budget = budget or Budget()
        require(isinstance(self.budget, Budget), 'typed Budget 필요')
        self.backend = backend if backend is not None else NativeBackend()
        self.event_sink = event_sink
        self.session = None; self.candidates = []; self.selections = []; self.events = []
        self.executed = False
        self.usage = dict(initial_advances=0, extra_advances=0, initial_kernel_ticks=0,
                          extra_kernel_ticks=0, selection_calls=0,
                          selection={key: 0 for key in USAGE_KEYS})

    def emit(self, event: str, **payload) -> None:
        record = dict(ordinal=len(self.events), event=event, **deepcopy(payload))
        self.events.append(record)
        if self.event_sink is not None:
            self.event_sink(deepcopy(record))

    def _ticks(self) -> int:
        return self.session.current['pending']['cost']['kernel_ticks']

    def _stage(self) -> str:
        return 'extra' if self.candidates else 'initial'

    def _affordable(self) -> tuple[bool, int]:
        stage = self._stage(); reserve = self.backend.reservation(self.session)
        require(type(reserve) is int and reserve >= 0, 'native 예약량 형식')
        limit_adv = getattr(self.budget, f'max_{stage}_advances')
        limit_ticks = getattr(self.budget, f'max_{stage}_kernel_ticks')
        return (self.usage[f'{stage}_advances'] < limit_adv and
                self.usage[f'{stage}_kernel_ticks'] + reserve <= limit_ticks), reserve

    def _work(self, operation: str, reserve: int) -> None:
        s = self.session; before = self._ticks(); stage = self._stage()
        self.emit('work_requested', operation=operation, reference=s.reference,
                  stage=stage, kernel_ticks=before, reserved_kernel_ticks=reserve)
        if operation == 'advance':
            s.advance()
        else:
            s.continue_dependency()
        delta = self._ticks() - before
        require(0 <= delta <= reserve if operation == 'advance' else delta == 0,
                'native 계산이 예약량/continue 계약을 위반했습니다.')
        if operation == 'advance':
            self.usage[f'{stage}_advances'] += 1
            self.usage[f'{stage}_kernel_ticks'] += delta
        self.emit('work_committed', operation=operation, reference=s.reference,
                  phase=s.phase, kernel_ticks=self._ticks())

    def _readout(self) -> dict:
        s = self.session; ordinal = len(self.candidates)
        self.emit('readout_requested', reference=s.reference, readout_ordinal=ordinal)
        before = s.packet()
        candidate = self.backend.capture(s)
        require(s.packet() == before, 'readout이 live session을 수정했습니다.')
        self.candidates.append(deepcopy(candidate))
        # selector 실패 또는 강제 종료 전에도 원 판단을 원문으로 보존한다.
        self.emit('readout_committed', readout_ordinal=ordinal, candidate=candidate)
        candidate_hash = digest(candidate)
        view = self.backend.project(candidate); view_hash = digest(view)
        self.emit('selection_requested', readout_ordinal=ordinal, policy=self.policy,
                  input_sha256=view_hash, candidate_sha256=candidate_hash)
        output = self.backend.select(view, self.policy, dict(SELECTION_LIMITS))
        require(digest(view) == view_hash and digest(candidate) == candidate_hash and s.packet() == before,
                'selector가 입력/native 상태를 수정했습니다.')
        require(type(output['accepted']) is bool and type(output['value']) in (bool, type(None)),
                '선택 출력 형식')
        require(output['policy'] == self.policy and output['input_sha256'] == view_hash,
                '선택 정책/입력 출처')
        require(output['value'] is (view['raw_value'] if output['accepted'] else None),
                'proof 선택이 raw 값을 뒤집었습니다.')
        require(output['limits'] == SELECTION_LIMITS and set(output['usage']) == set(USAGE_KEYS),
                'selector 비용 계약')
        for key, value in output['usage'].items():
            require(type(value) is int and value >= 0, '계측되지 않은 비용을 0으로 치환할 수 없습니다.')
            self.usage['selection'][key] += value
        self.usage['selection_calls'] += 1
        self.selections.append(deepcopy(output))
        self.emit('selection_committed', readout_ordinal=ordinal, result=output)
        return output

    def run(self) -> dict:
        require(not self.executed, '한 trial은 한 번만 실행합니다. 자동 retry 없음')
        self.executed = True; started = perf_counter()
        # 두 policy에 같은 identity를 부여해 policy 외 identity 교란을 제거한다.
        session_id = 'online-r037-' + self.scope + '-' + digest(self.observation)[:20]
        self.emit('begin_requested', session_id=session_id, scope=self.scope, policy=self.policy,
                  observation_sha256=digest(self.observation), config_sha256=digest(self.config),
                  memory_sha256=digest(self.memory))
        self.session = s = self.backend.begin(self.observation, self.config, self.memory,
                                             self.scope, session_id)
        require(s.current['pending'] is not None, 'native pending 누락')
        self.usage['initial_kernel_ticks'] = self._ticks()
        require(self._ticks() <= self.budget.max_initial_kernel_ticks, 'begin 계산 예산 초과')
        self.emit('begin_committed', reference=s.reference, phase=s.phase)
        current_selection = None; processed_generation = None; reason = None
        # 최대 128 initial + 128 extra advances 및 각 readout/continue에 대한 유한 상한.
        for _ in range(1024):
            p = s.current['pending']
            require(s.phase in ('running', 'readout_ready'), '미등록 native 경계')
            if s.phase == 'readout_ready':
                if processed_generation != s.generation:
                    current_selection = self._readout(); processed_generation = s.generation
                if current_selection['accepted']:
                    reason = 'stop_supported_policy'; break
                if current_selection['reason'] in SELECTION_BUDGET_REASONS:
                    reason = 'stop_selection_budget'; break
                if p['failure_reason'] is not None:
                    reason = 'stop_engine_failure'; break
                if not p['workspace']['frontier']:
                    reason = 'stop_frontier_exhausted'; break
                affordable, reserve = self._affordable()
                if not affordable:
                    reason = 'stop_compute_budget'; break
                self._work('continue_dependency', 0)
                current_selection = None
            else:
                if p['failure_reason'] is not None:
                    reason = 'stop_engine_failure'; break
                affordable, reserve = self._affordable()
                if not affordable:
                    reason = 'stop_initial_budget' if not self.candidates else 'stop_compute_budget'
                    break
                self._work('advance', reserve)
        require(reason is not None, 'controller event bound 소진')
        accepted = reason == 'stop_supported_policy'
        adoption = dict(accepted=accepted, value=current_selection['value'] if accepted else None,
                        reason=reason, policy=self.policy,
                        readout_ordinal=len(self.candidates)-1 if accepted else None,
                        candidate_id=self.candidates[-1]['candidate_id'] if accepted else None,
                        proof_sha256=digest(current_selection['proof']) if accepted else None)
        self.emit('stop', reference=s.reference, adoption=adoption)
        packet = s.packet()
        require(packet['document']['engine']['memory'] == self.memory, '동결 memory 변경')
        require(self._ticks() == self.usage['initial_kernel_ticks'] + self.usage['extra_kernel_ticks'],
                '누적 native kernel cost 불일치')
        return dict(schema='hcr-online-trial-r037-v1', backend=self.backend.kind,
                    scope=self.scope, policy=self.policy, budget=asdict(self.budget),
                    observation_sha256=digest(self.observation), memory_sha256=digest(self.memory),
                    config_sha256=digest(self.config), packet=packet,
                    candidates=deepcopy(self.candidates), selections=deepcopy(self.selections),
                    events=deepcopy(self.events), adoption=adoption, usage=deepcopy(self.usage),
                    terminal_pending_ready=packet['document']['engine']['pending']['ready'],
                    wall_seconds=perf_counter()-started)

    def partial_evidence(self) -> dict:
        return dict(schema='hcr-online-partial-r037-v1', events=deepcopy(self.events),
                    candidates=deepcopy(self.candidates), selections=deepcopy(self.selections),
                    usage=deepcopy(self.usage),
                    packet=None if self.session is None else self.session.packet())
