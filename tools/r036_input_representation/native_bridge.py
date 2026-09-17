"""공개 입력에서 실제 native session을 실행한다. world/case 정답은 받지 않는다."""
from __future__ import annotations
from copy import deepcopy
from time import perf_counter
from r035_frozen_selection.contracts import digest, require


class NativeTrial:
    """단회 실행 adapter. 실패 중의 마지막 commit된 native 상태도 꺼낼 수 있다."""
    def __init__(self, observation: dict, config: dict, memory: dict, scope: str,
                 max_initial_advances: int, continuation_limits: dict, event_sink=None):
        require(type(max_initial_advances) is int and 0<=max_initial_advances<=64,'초기 advance 예산')
        self.observation=deepcopy(observation);self.config=deepcopy(config);self.memory=deepcopy(memory)
        self.scope=scope;self.maximum=max_initial_advances;self.limits=deepcopy(continuation_limits)
        self.sink=event_sink;self.actions=[];self.session=None;self.first=None;self.flow=None;self.executed=False

    def emit(self, row):
        self.actions.append(deepcopy(row))
        if self.sink:self.sink(deepcopy(row))

    def run(self) -> dict:
        from hcr import codec
        from hcr.circuits import AdaptiveMemory
        from hcr.model import Mode
        from hcr.sessions import AdaptiveSession
        from hcr.review import capture_candidate, ReviewLimits, sealed
        from hcr.selection_runtime import SelectionFlow
        require(not self.executed,'native trial은 재실행하지 않습니다.');self.executed=True
        started=perf_counter();cfg=codec.adaptive_config_from(self.config)
        obs=codec.observation_from(self.observation)
        self.session=s=AdaptiveSession(cfg,AdaptiveMemory.from_document(deepcopy(self.memory),cfg),
            session_id='input-r036-'+self.scope+'-'+obs.digest[:20],judgment_prior=self.scope)
        s.begin(obs,Mode.FROZEN_EVAL)
        self.emit(dict(operation='begin_committed',reference=s.reference,phase=s.phase))
        count=0
        while s.phase=='running' and count<self.maximum:
            self.emit(dict(operation='advance_requested',reference=s.reference,
                           kernel_ticks=s.current['pending']['cost']['kernel_ticks']))
            s.advance();count+=1
            self.emit(dict(operation='advance_committed',reference=s.reference,phase=s.phase,
                           kernel_ticks=s.current['pending']['cost']['kernel_ticks']))
        initial=s.packet()
        require(initial['document']['engine']['memory']==self.memory,'초기 실행이 동결 memory를 변경함')
        if s.phase=='running':
            return dict(schema='hcr-input-native-r036-v1',status='initial_budget_exhausted',
                initial_advances=count,initial_packet=initial,initial_actions=deepcopy(self.actions),
                baseline=None,flow=None,wall_seconds=perf_counter()-started)
        require(s.phase=='readout_ready','등록되지 않은 native 초기 종료 경계: '+s.phase)
        self.first=capture_candidate(s,0)
        self.emit(dict(operation='first_readout',candidate_id=self.first['candidate_id'],generation=s.generation))
        baseline=sealed(dict(schema='hcr-review-baseline-r033-v1',ready=initial,first=self.first,
            observation=deepcopy(self.observation),judgment_prior=self.scope,preparation_seconds=perf_counter()-started))
        initial_actions=deepcopy(self.actions)
        # 셀렉터 결과는 continuation의 종료 판단에 전달하지 않는다.
        self.flow=SelectionFlow(baseline,'expand_only',limits=ReviewLimits(**self.limits),
            event_sink=lambda row:self.emit(dict(operation='continuation_action',record=row)))
        result=self.flow.run()
        require(result['candidates'][0]==self.first,'최초 candidate 보존 실패')
        require(all(p['document']['engine']['memory']==self.memory for p in result['segments']),'continuation memory 변경')
        return dict(schema='hcr-input-native-r036-v1',status='readout_ready',initial_advances=count,
            initial_packet=initial,initial_actions=initial_actions,baseline=baseline,flow=result,
            wall_seconds=perf_counter()-started)

    def partial_evidence(self) -> dict:
        return dict(actions=deepcopy(self.actions),first=deepcopy(self.first),
            initial_session=None if self.session is None else self.session.packet(),
            continuation=None if self.flow is None else self.flow.partial_evidence())
