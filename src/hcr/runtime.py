"""단일 실행계: recall/graph → 같은 kernel → 판단 → 허용 feedback → 느린 학습.
평가·world·정답 solver를 import하지 않는다. 추가 관측은 요청 record로만 표현한다.
"""
from __future__ import annotations
from dataclasses import replace
from time import perf_counter
from .model import (Config,Cost,Mode,Status,Observation,Decision,Convergence,Proof,Feedback,
                    ObservationRequest,ContractError,ExpansionLimit,fingerprint)
from .binding import Topology,Binding
from .circuits import Memory
from .workspace import expand
from .dynamics import settle
from .proof import reconstruct
from .learning import update
from .trace import Trace
from .codec import plain


class Engine:
    def __init__(self,config:Config|None=None,memory:Memory|None=None,trace:Trace|None=None,*,
                 use_circuits:bool=True,top_down:bool=True,allow_reexpansion:bool=True):
        self.config=config or Config();self.memory=memory if memory is not None else Memory()
        self.trace=trace if trace is not None else Trace()
        self.use_circuits=use_circuits;self.top_down=top_down;self.allow_reexpansion=allow_reexpansion
        self._attempts={};self._held={};self._feedback={};self._requests={}
        self.trace.emit('engine_created',{'config':plain(self.config),'memory_hash':self.memory.digest,
             'memory_document':self.memory.document(),'use_circuits':use_circuits,'top_down':top_down,'allow_reexpansion':allow_reexpansion})

    def infer(self,obs:Observation,mode:Mode=Mode.FROZEN_EVAL,*,revision_of:str|None=None) -> Decision:
        if not isinstance(obs,Observation) or not isinstance(mode,Mode):raise ContractError('typed observation/mode required')
        if len(obs.edges)>self.config.max_edges:raise ContractError('edge limit')
        forced=False
        if revision_of is not None:
            if mode!=Mode.ADAPT or revision_of not in self._requests:raise ContractError('unrequested revision')
            request=self._requests[revision_of];prior=self._held[revision_of][0]
            if obs.episode_id!=request.episode_id or obs.revision!=request.revision or obs.revision<=prior.revision:
                raise ContractError('revision identity')
            before=[(e.id,e.source,e.target) for e in prior.edges];after=[(e.id,e.source,e.target) for e in obs.edges]
            if before!=after or (obs.start,obs.goal)!=(prior.start,prior.goal):raise ContractError('observation revision changed topology')
            allowed=set(request.edge_ids)
            if any(a.score!=b.score and a.id not in allowed for a,b in zip(prior.edges,obs.edges)):
                raise ContractError('unrequested measurement changed')
            forced=True
            self.trace.emit('circuit_reopened',{'previous_decision':revision_of,'new_observation':obs.digest,
                            'new_revision':obs.revision,'reason':'external_mismatch_and_new_observation'})
            del self._requests[revision_of]
        elif obs.episode_id in self._attempts:raise ContractError('episode already used; explicit revision required')
        attempt=self._attempts.get(obs.episode_id,0)+1;self._attempts[obs.episode_id]=attempt
        did='d-'+str(self.trace.count)+'-'+obs.digest[:16]
        cost=Cost();cost.observation_requests=int(forced);start=perf_counter();topology=Topology.from_observation(obs)
        topology.validate(self.config)
        before_hash=self.memory.digest;version=self.memory.version
        self.trace.emit('attempt_started',{'decision_id':did,'observation':plain(obs),'mode':mode.value,
                        'attempt':attempt,'memory_hash':before_hash,'memory_version':version,'revision_of':revision_of})
        recalled=None if forced or not self.use_circuits else self.memory.recall(obs,self.config,cost)
        program=None;circuit_id=None;prior=0.0;method='graph_expansion';expansion_failed=False
        if recalled:
            circuit,binding=recalled;program=circuit.program;circuit_id=circuit.id;method='circuit_reuse'
            cost.circuit_groups_instantiated+=len(program.groups)
            # 현재 관측이 명확하면 prior를 약화한다. 과거 답을 반환하는 경로는 없다.
            uncertainty=max(1-abs(e.score or 0.0) for e in obs.edges)
            prior=self.config.prior_gain*circuit.strength*circuit.balance*uncertainty
            self.trace.emit('circuit_recalled',{'decision_id':did,'circuit_id':circuit.id,'version':circuit.version,
                'binding':plain(binding),'learned_strength':circuit.strength,'learned_balance':circuit.balance,
                'prior_drive':prior,'program_digest':program.digest})
        else:
            binding=Binding(obs.digest,obs.revision,tuple(range(len(obs.edges))))
            self.trace.emit('expansion_started',{'decision_id':did,'reason':'feedback_reopen' if forced else 'no_applicable_circuit'})
            try:program=expand(topology,self.config,cost,lambda event,payload:self.trace.emit(event,dict(payload,decision_id=did)))
            except ExpansionLimit as error:
                expansion_failed=True
                self.trace.emit('expansion_exhausted',{'decision_id':did,'error':str(error)})
        if program is None:
            state={};conv=Convergence(Status.BUDGET_EXHAUSTED if expansion_failed else Status.NO_CANDIDATE,0,0.0,0.0,0);value=None
        else:
            binding.check(obs)
            drives={g.id:(prior if g.level==1 else self.config.evidence_gain*(obs.edges[binding.edge_order[int(g.id.split(':')[1])]].score or 0.0)) for g in program.groups}
            self.trace.emit('network_instantiated',{'decision_id':did,'program':plain(program),'program_digest':program.digest,
                       'drives':drives,'binding':plain(binding),'top_down':self.top_down,'fresh_state':True})
            state,conv=settle(program,drives,self.config,cost,top_down=self.top_down,
                  observe=lambda tick,state,residual,stable:self.trace.emit('tick',{'decision_id':did,'tick':tick,
                    'state':state,'residual':residual,'stable_steps':stable}))
            value=(state['goal']>=0.5) if conv.status==Status.STABLE_DECISION else None
            if prior==0 and all(e.score is None or e.score==0 for e in obs.edges):
                value=None
                if conv.status==Status.STABLE_DECISION:conv=replace(conv,status=Status.UNSUPPORTED)
            if value is None:
                self.trace.emit('expansion_unavailable',{'decision_id':did,'reason':'all_public_paths_already_instantiated; no_unrequested_information',
                                'candidates':len(program.groups)*2})
        self.trace.emit('decision_readout',{'decision_id':did,'value':value,'status':conv.status.value,'memory_version':version})
        proof=Proof((),None,None,(),False) if program is None else reconstruct(obs,program,binding,state,value,cost)
        self.trace.emit('explanation_reconstructed',{'decision_id':did,'proof':plain(proof),'is_execution_trace':False})
        cost.wall_seconds=perf_counter()-start
        decision=Decision(did,obs.episode_id,obs.digest,obs.revision,attempt,mode,value,conv,version,circuit_id,
                          method,proof,cost.snapshot(),None if program is None else program.digest,tuple(sorted(state.items())))
        if self.memory.digest!=before_hash:raise ContractError('inference mutated persistent memory')
        self.trace.emit('decision',plain(decision))
        self._held[did]=(obs,decision,topology,program,fingerprint(plain(decision)),before_hash)
        return decision

    def feedback(self,feedback:Feedback) -> dict:
        if feedback.decision_id not in self._held:raise ContractError('feedback before decision')
        obs,decision,topology,program,recorded_hash,recorded_memory=self._held[feedback.decision_id]
        if decision.mode==Mode.FROZEN_EVAL:raise ContractError('frozen evaluation cannot learn')
        if feedback.observation_digest!=obs.digest or fingerprint(plain(decision))!=recorded_hash:
            raise ContractError('feedback/decision identity')
        if decision.id in self._feedback:raise ContractError('decision feedback already consumed')
        if self.memory.version!=decision.memory_version or self.memory.digest!=recorded_memory:raise ContractError('memory version changed after decision')
        self.trace.emit('feedback',plain(feedback));cost=Cost();learning_started=perf_counter()
        patch=update(self.memory,obs,decision,feedback,topology,program,self.config,cost)
        cost.wall_seconds=perf_counter()-learning_started
        self._feedback[decision.id]=feedback
        self.trace.emit('memory_updated',{'patch':patch,'memory_after':self.memory.digest,'memory_document':self.memory.document(),'cost':cost.snapshot()})
        return plain(patch)

    def request_revision(self,decision_id:str) -> ObservationRequest | None:
        if decision_id not in self._feedback or self._feedback[decision_id].correct is not False:
            raise ContractError('revision requires an observed external error')
        obs,decision,_,_,_,_=self._held[decision_id]
        if decision.mode!=Mode.ADAPT or not self.allow_reexpansion:return None
        if decision.attempt>self.config.max_observation_requests:return None
        ids=tuple(e.id for e in sorted(obs.edges,key=lambda e:(abs(e.score or 0),e.id)) if e.score is None or abs(e.score)<0.9)
        if not ids:
            self.trace.emit('revision_unavailable',{'decision_id':decision_id,'reason':'no_less_certain_observation'})
            return None
        request=ObservationRequest(decision_id,obs.episode_id,obs.revision+1,ids,'uncertain_features_after_error')
        if decision_id in self._requests:raise ContractError('revision request already pending')
        self._requests[decision_id]=request
        self.trace.emit('observation_requested',plain(request));return request
