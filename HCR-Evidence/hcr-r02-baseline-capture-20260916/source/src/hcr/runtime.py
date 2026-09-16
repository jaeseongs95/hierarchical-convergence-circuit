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


class AdaptiveEngine:
    """R0.2 실행 controller. R0.1 Engine과 동일 kernel/관측/proof/trace 기반을 공유한다.

    단일 src/hcr 안의 명시적인 호환 API다. frozen source 복사본, LLM 호출,
    전체 topology 정답 solver, 실험 label에 의한 경로 분기는 없다.
    """
    def __init__(self, config=None, memory=None, trace=None, *, use_circuits=True,
                 top_down=True, allow_reexpansion=True):
        from .model import AdaptiveConfig
        from .circuits import AdaptiveMemory
        self.config = config or AdaptiveConfig()
        if not isinstance(self.config, AdaptiveConfig):
            raise ContractError('AdaptiveEngine requires AdaptiveConfig')
        if any(type(flag) is not bool for flag in (use_circuits, top_down, allow_reexpansion)):
            raise ContractError('R0.2 engine switches must be bool')
        if memory is not None and not isinstance(memory, AdaptiveMemory):
            raise ContractError('AdaptiveEngine requires AdaptiveMemory')
        self.memory = memory if memory is not None else AdaptiveMemory.empty(self.config)
        AdaptiveMemory.from_document(self.memory.document(), self.config)
        self.trace = trace if trace is not None else Trace()
        self.use_circuits = use_circuits
        self.top_down = top_down
        self.allow_reexpansion = allow_reexpansion
        self._attempts = {}
        self._held = {}
        self._feedback = {}
        self._requests = {}
        self.trace.emit('r02_engine_created', dict(config=plain(self.config), config_signature=self.config.signature,
            memory_hash=self.memory.digest, memory_document=self.memory.document(),
            use_circuits=use_circuits, top_down=top_down, allow_reexpansion=allow_reexpansion))

    def infer(self, obs: Observation, mode: Mode = Mode.FROZEN_EVAL, *, revision_of=None):
        from .model import (AdaptiveCost, AdaptiveDecision, ExpansionBudget, MismatchSignal)
        from .workspace import AdaptiveWorkspace, adaptive_network
        from .expansion import DeterministicExpansionPolicy
        from .dynamics import settle_recorded
        if not isinstance(obs, Observation) or not isinstance(mode, Mode):
            raise ContractError('typed public observation/mode required')
        if len(obs.edges) > self.config.kernel.max_edges:
            raise ContractError('R0.2 observation edge bound')
        forced = revision_of is not None
        if forced:
            if mode != Mode.ADAPT or revision_of not in self._requests:
                raise ContractError('R0.2 unrequested revision')
            request = self._requests[revision_of]
            previous = self._held[revision_of][0]
            if (obs.episode_id != request.episode_id or obs.revision != request.revision
                    or obs.revision <= previous.revision or (obs.start, obs.goal) != (previous.start, previous.goal)
                    or [(e.id, e.source, e.target) for e in obs.edges] != [(e.id, e.source, e.target) for e in previous.edges]):
                raise ContractError('R0.2 revision identity/topology')
            allowed = set(request.edge_ids)
            if any(a.score != b.score and a.id not in allowed for a, b in zip(previous.edges, obs.edges)):
                raise ContractError('R0.2 unrequested measurement changed')
            del self._requests[revision_of]
        elif obs.episode_id in self._attempts:
            raise ContractError('R0.2 episode already used; request a revision explicitly')
        attempt = self._attempts.get(obs.episode_id, 0) + 1
        self._attempts[obs.episode_id] = attempt
        did = 'r02-d-' + str(self.trace.count) + '-' + obs.digest[:16]
        started = perf_counter()
        cost = AdaptiveCost(observation_requests=int(forced))
        memory_hash, memory_version = self.memory.digest, self.memory.version
        self.trace.emit('r02_attempt_started', dict(decision_id=did, observation=plain(obs), mode=mode.value,
            attempt=attempt, memory_hash=memory_hash, memory_version=memory_version, revision_of=revision_of))
        workspace = AdaptiveWorkspace(obs, self.config, cost, self.trace, did)
        policy = DeterministicExpansionPolicy(self.config, self.memory,
                    use_circuits=self.use_circuits and not forced, top_down=self.top_down)
        mismatch = MismatchSignal('feedback_reopen' if forced else 'new_input', float(forced))
        program = None
        state = {}
        conv = Convergence(Status.NO_CANDIDATE, 0, 0.0, 0.0, 0)
        value = None
        network_id = None
        settled_paths = ()
        failure_reason = None
        try:
            while workspace.frontier:
                budget = ExpansionBudget(self.config.max_expansions - cost.expansions,
                    max(0, self.config.max_binding_checks - cost.binding_operations), self.config.max_frontier)
                candidates = policy.propose(workspace, mismatch, budget)
                if candidates:
                    workspace.apply(candidates[0])
                else:
                    workspace.retire()
                paths = tuple(p.path for p in workspace.routes)
                if paths and paths != settled_paths:
                    program, drives, metadata = adaptive_network(workspace)
                    state, conv, network_id = settle_recorded(program, drives, self.config.kernel, cost,
                        self.trace, did, 'decision', metadata, top_down=self.top_down)
                    settled_paths = paths
                candidate_value = ((state['goal'] >= .5) if program is not None
                                   and conv.status == Status.STABLE_DECISION else None)
                has_prior = any(use.prior != 0 for path in workspace.routes for use in path.uses)
                if not has_prior and all(e.score is None or e.score == 0 for e in obs.edges):
                    candidate_value = None
                    if program is not None and conv.status == Status.STABLE_DECISION:
                        conv = replace(conv, status=Status.UNSUPPORTED)
                if candidate_value is True:
                    value = True
                    break
                if candidate_value is False and workspace.complete:
                    value = False
                    break
                if candidate_value is False:
                    mismatch = MismatchSignal('negative_requires_dependency_coverage', 1.0)
                else:
                    mismatch = MismatchSignal('unresolved_or_no_goal_candidate', 1.0)
                self.trace.emit('r02_progress', dict(decision_id=did, mismatch=plain(mismatch),
                    graph_complete=workspace.complete, completed_paths=paths, network_id=network_id))
        except ExpansionLimit as error:
            failure_reason = str(error)
            value = None
            conv = replace(conv, status=Status.BUDGET_EXHAUSTED)
            self.trace.emit('r02_expansion_exhausted', dict(decision_id=did, reason=failure_reason))
        if program is None and failure_reason is None:
            conv = Convergence(Status.NO_CANDIDATE, 0, 0.0, 0.0, 0)
        binding = Binding(obs.digest, obs.revision, tuple(range(len(obs.edges))))
        proof = (Proof((), None, None, (), False) if program is None else
                 reconstruct(obs, program, binding, state, value, cost))
        circuits = tuple(sorted({use.circuit_id for path in workspace.routes for use in path.uses}))
        cost.wall_seconds = perf_counter() - started
        decision = AdaptiveDecision(did, obs.episode_id, obs.digest, obs.revision, attempt, mode, value,
            conv, memory_version, circuits[0] if len(circuits) == 1 else None,
            'adaptive_graph_circuit' if circuits else 'adaptive_graph', proof, cost.snapshot(),
            program.digest if program is not None else None, tuple(sorted(state.items())),
            circuit_ids=circuits, expanded_paths=tuple(path.path for path in workspace.routes),
            graph_complete=workspace.complete, failure_reason=failure_reason,
            adaptive_config_signature=self.config.signature)
        if self.memory.digest != memory_hash:
            raise ContractError('R0.2 inference mutated persistent memory')
        self.trace.emit('r02_decision', plain(decision))
        self._held[did] = (obs, decision, fingerprint(plain(decision)), memory_hash)
        return decision

    def feedback(self, feedback: Feedback) -> dict:
        from .model import AdaptiveCost
        from .learning import update_adaptive
        if not isinstance(feedback, Feedback) or feedback.decision_id not in self._held:
            raise ContractError('R0.2 feedback before decision')
        obs, decision, recorded_hash, memory_hash = self._held[feedback.decision_id]
        if decision.mode == Mode.FROZEN_EVAL:
            raise ContractError('R0.2 frozen evaluation cannot learn')
        if (feedback.observation_digest != obs.digest or fingerprint(plain(decision)) != recorded_hash
                or self.memory.version != decision.memory_version or self.memory.digest != memory_hash):
            raise ContractError('R0.2 feedback/decision/memory binding')
        if decision.id in self._feedback or feedback.id in self.memory.consumed_feedback:
            raise ContractError('R0.2 duplicate feedback')
        cost = AdaptiveCost()
        start = perf_counter()
        patch = update_adaptive(self.memory, obs, decision, feedback, self.config, cost)
        cost.wall_seconds = perf_counter() - start
        self._feedback[decision.id] = feedback
        self.trace.emit('r02_feedback', plain(feedback))
        self.trace.emit('r02_memory_updated', dict(patch=patch, memory_after=self.memory.digest,
                                                   memory_document=self.memory.document(), cost=cost.snapshot()))
        return plain(patch)

    def request_revision(self, decision_id: str) -> ObservationRequest | None:
        if decision_id not in self._feedback or self._feedback[decision_id].correct is not False:
            raise ContractError('R0.2 revision requires external error feedback')
        obs, decision, _, _ = self._held[decision_id]
        if (decision.mode != Mode.ADAPT or not self.allow_reexpansion
                or decision.attempt > self.config.kernel.max_observation_requests):
            return None
        ids = tuple(e.id for e in sorted(obs.edges, key=lambda e: (abs(e.score or 0), e.id))
                    if e.score is None or abs(e.score) < .9)
        if not ids:
            return None
        if decision_id in self._requests:
            raise ContractError('R0.2 revision already pending')
        request = ObservationRequest(decision_id, obs.episode_id, obs.revision + 1, ids,
                                     'uncertain_features_after_error')
        self._requests[decision_id] = request
        self.trace.emit('r02_observation_requested', plain(request))
        return request
