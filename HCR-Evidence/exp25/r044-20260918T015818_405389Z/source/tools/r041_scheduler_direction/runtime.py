"""R037 loop와 R038 사후 경계를 재사용하고, advance 직전 명시적 priority만 추가한다."""
from copy import deepcopy
from r037_online_selection.runtime import OnlineTrial
from r038_early_adoption.runtime import TimingTrial
from .contracts import SCHEDULERS, SCHEDULE_USAGE, BASE_POLICY, digest, require
from . import scheduler as scheduling


class ScheduledOnlineTrial(OnlineTrial):
    def __init__(self,*args,scheduler='input_order',**kwargs):
        require(scheduler in SCHEDULERS,'미등록 scheduler')
        super().__init__(*args,**kwargs)
        self.scheduler=scheduler
        self.scheduler_usage={k:0 for k in SCHEDULE_USAGE}

    def _work(self,operation,reserve):
        # 기존 loop의 예산/실패 검사를 통과한 advance에서만 호출된다.
        if operation=='advance':
            session=self.session;before=session.packet()
            view=scheduling.project(session.current);view_hash=digest(view)
            self.emit('schedule_requested',reference=session.reference,scheduler=self.scheduler,
                      input_sha256=view_hash,view=view)
            decision=scheduling.choose(view,self.scheduler)
            require(digest(view)==view_hash and session.packet()==before,'scheduler 입력/native 상태 변경')
            self.emit('schedule_decided',decision=decision)
            # 실제 API 호출 여부가 확정된 후 비용을 기록한다. 실패 시 부분 기록으로 남는다.
            if decision['priority_required']:
                path=decision['selected_path']
                self.emit('priority_requested',reference=session.reference,path=path)
                previous_index=session.prioritize_frontier(path)
                require(type(previous_index) is int and previous_index==decision['selected_index'],
                        'prioritize_frontier 반환/선택 불일치')
                self.emit('priority_committed',reference=session.reference,previous_index=previous_index)
            for k,v in decision['usage'].items(): self.scheduler_usage[k]+=v
        super()._work(operation,reserve)

    def run(self):
        result=super().run()
        result.update(schema='hcr-scheduled-online-r041-v1',scheduler=self.scheduler,
                      scheduler_usage=deepcopy(self.scheduler_usage))
        return result

    def partial_evidence(self):
        result=super().partial_evidence()
        result.update(schema='hcr-scheduled-partial-r041-v1',scheduler=self.scheduler,
                      scheduler_usage=deepcopy(self.scheduler_usage))
        return result


class ScheduledTimingTrial(TimingTrial):
    def __init__(self,observation,config,memory,scope,arm,budget=None,*,scheduler='input_order',
                 backend=None,event_sink=None):
        # 부모 생성자는 실행하지 않고 객체만 만든다. 실제 worker를 이 클래스의 worker로 교체한다.
        super().__init__(observation,config,memory,scope,arm,budget,backend=backend,event_sink=event_sink)
        self.worker=ScheduledOnlineTrial(observation,config,memory,scope,BASE_POLICY[arm],budget,
            scheduler=scheduler,backend=self.backend,
            event_sink=lambda e:self._send(dict(event='native_action',record=e)))
        # R038 TimingTrial.run의 보존·사후 채택·비용 계약은 변경하지 않는다.
