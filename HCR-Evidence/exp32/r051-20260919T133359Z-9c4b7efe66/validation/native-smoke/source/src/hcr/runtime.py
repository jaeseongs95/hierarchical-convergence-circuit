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
                 top_down=True, allow_reexpansion=True, judgment_prior="legacy"):
        from .model import AdaptiveConfig
        from .prior_policy import validate_scope, policy_fields
        self._judgment_prior = validate_scope(judgment_prior)
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
        self._pending = None
        self._attempts = {}
        self._held = {}
        self._feedback = {}
        self._requests = {}
        self.trace.emit('r02_engine_created', dict(config=plain(self.config), config_signature=self.config.signature,
            memory_hash=self.memory.digest, memory_document=self.memory.document(),
            use_circuits=use_circuits, top_down=top_down, allow_reexpansion=allow_reexpansion,
            **policy_fields(self.judgment_prior)))

    @property
    def judgment_prior(self):
        """한 engine 수명 동안 불변인 정책. 변경 조건은 새 engine/session으로 실행한다."""
        return self._judgment_prior

    def infer(self, obs: Observation, mode: Mode = Mode.FROZEN_EVAL, *, revision_of=None):
        """기존 API. 동일한 진행 코드를 끝까지 실행하는 편의 호출이다."""
        self.begin(obs, mode, revision_of=revision_of)
        while not self._pending.ready:
            self.advance()
        return self.finish()

    def begin(self, obs: Observation, mode: Mode = Mode.FROZEN_EVAL, *, revision_of=None):
        """R0.2.1: 새 시도 시작. 아직 dependency를 전개하지 않는다."""
        from .state import ExecutionState
        from .prior_policy import validate_scope
        validate_scope(self.judgment_prior)
        from .model import AdaptiveCost, MismatchSignal
        from .workspace import AdaptiveWorkspace
        if self._pending is not None or self.trace._closed:
            raise ContractError('active attempt or closed trace')
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
        self._pending = ExecutionState(obs, mode, revision_of, attempt, did, memory_hash, memory_version,
            self.config.signature, (self.use_circuits, self.top_down, self.allow_reexpansion), cost, workspace,
            MismatchSignal('feedback_reopen' if forced else 'new_input', float(forced)),
            judgment_prior=self.judgment_prior)
        self._pending.active_seconds = perf_counter() - started
        return did

    def _guard_pending(self):
        p = self._pending
        if p is None or self.trace._closed:
            raise ContractError('no active attempt or closed trace')
        if (p.memory_hash != self.memory.digest or p.memory_version != self.memory.version
                or p.config_signature != self.config.signature
                or p.judgment_prior != self.judgment_prior
                or p.switches != (self.use_circuits, self.top_down, self.allow_reexpansion)):
            raise ContractError('active attempt configuration/memory changed')
        return p

    def prioritize_frontier(self, path):
        """R0.3: 이미 생성된 frontier의 순서만 변경한다. 근거/후보를 생성하지 않는다."""
        p = self._guard_pending()
        if p.ready or not isinstance(path, (tuple, list)) or any(type(i) is not int for i in path):
            raise ContractError('frontier priority requires a running attempt and an integer path')
        key = tuple(path)
        matches = [i for i, prefix in enumerate(p.workspace.frontier) if prefix.path == key]
        if len(matches) != 1:
            raise ContractError('priority path is not an existing frontier')
        index = matches[0]
        prefix = p.workspace.frontier[index]
        p.workspace.frontier = [prefix] + p.workspace.frontier[:index] + p.workspace.frontier[index + 1:]
        self.trace.emit('r03_frontier_prioritized', dict(decision_id=p.decision_id,
            path=list(key), previous_index=index, node=plain(prefix.node)))
        return index

    def advance(self):
        """dependency step 한 개. pool/settle 내부 tick에서는 중단하지 않는다."""
        from .model import ExpansionBudget, MismatchSignal
        from .workspace import adaptive_network
        from .expansion import DeterministicExpansionPolicy
        from .dynamics import settle_recorded
        p = self._guard_pending()
        if p.ready:
            raise ContractError('attempt is readout-ready; call finish')
        started = perf_counter()
        ws, cost, obs = p.workspace, p.cost, p.observation
        policy = DeterministicExpansionPolicy(self.config, self.memory,
            use_circuits=self.use_circuits and p.revision_of is None, top_down=self.top_down)
        try:
            if ws.frontier:
                budget = ExpansionBudget(self.config.max_expansions - cost.expansions,
                    max(0, self.config.max_binding_checks - cost.binding_operations), self.config.max_frontier)
                candidates = policy.propose(ws, p.mismatch, budget)
                if candidates:
                    ws.apply(candidates[0])
                else:
                    ws.retire()
                paths = tuple(r.path for r in ws.routes)
                if paths and paths != p.settled_paths:
                    p.program, drives, metadata = adaptive_network(ws, judgment_prior=p.judgment_prior)
                    p.state, p.convergence, p.network_id = settle_recorded(
                        p.program, drives, self.config.kernel, cost, self.trace, p.decision_id,
                        'decision', metadata, top_down=self.top_down)
                    p.settled_paths = paths
                candidate_value = ((p.state['goal'] >= .5) if p.program is not None
                                   and p.convergence.status == Status.STABLE_DECISION else None)
                has_prior = p.judgment_prior == 'legacy' and any(use.prior != 0 for path in ws.routes for use in path.uses)
                if not has_prior and all(e.score is None or e.score == 0 for e in obs.edges):
                    candidate_value = None
                    if p.program is not None and p.convergence.status == Status.STABLE_DECISION:
                        p.convergence = replace(p.convergence, status=Status.UNSUPPORTED)
                if candidate_value is True or (candidate_value is False and ws.complete):
                    p.value, p.ready = candidate_value, True
                else:
                    p.mismatch = MismatchSignal('negative_requires_dependency_coverage' if candidate_value is False
                                               else 'unresolved_or_no_goal_candidate', 1.0)
                    self.trace.emit('r02_progress', dict(decision_id=p.decision_id, mismatch=plain(p.mismatch),
                        graph_complete=ws.complete, completed_paths=paths, network_id=p.network_id))
                p.ready = p.ready or ws.complete
            else:
                p.ready = True
        except ExpansionLimit as error:
            p.failure_reason = str(error)
            p.value, p.ready = None, True
            p.convergence = replace(p.convergence, status=Status.BUDGET_EXHAUSTED)
            self.trace.emit('r02_expansion_exhausted', dict(decision_id=p.decision_id, reason=p.failure_reason))
        if p.program is None and p.failure_reason is None:
            p.convergence = Convergence(Status.NO_CANDIDATE, 0, 0.0, 0.0, 0)
        p.active_seconds += perf_counter() - started
        return p.ready

    def continue_dependency(self):
        """R0.3.3 명시적 개입: 완료하지 않은 frontier를 유지하며 readout 경계를 연다.

        정답/feedback을 받지 않는다. 관측·prior·가정·network·누적 비용을 바꾸지 않는다.
        최초 판단은 호출자가 fork_readout()의 불변 packet으로 먼저 보존한다.
        """
        p = self._guard_pending()
        if (p.mode != Mode.FROZEN_EVAL or not p.ready or p.failure_reason is not None
                or not p.workspace.frontier):
            raise ContractError('review continuation needs a frozen ready boundary with remaining frontier')
        self.trace.emit('r033_dependency_continued', dict(decision_id=p.decision_id,
            frontier_count=len(p.workspace.frontier), reason='explicit_review_without_new_information'))
        p.ready, p.value = False, None

    def finish(self):
        """이미 정해진 readout을 proof와 묶어 완료한다. readout 값 보정은 하지 않는다."""
        from .model import AdaptiveDecision
        p = self._guard_pending()
        if not p.ready:
            raise ContractError('dependency computation is not readout-ready')
        started = perf_counter()
        obs, cost, ws = p.observation, p.cost, p.workspace
        binding = Binding(obs.digest, obs.revision, tuple(range(len(obs.edges))))
        proof = (Proof((), None, None, (), False) if p.program is None else
                 reconstruct(obs, p.program, binding, p.state, p.value, cost))
        circuits = tuple(sorted({use.circuit_id for path in ws.routes for use in path.uses}))
        cost.wall_seconds = p.active_seconds + perf_counter() - started
        decision = AdaptiveDecision(p.decision_id, obs.episode_id, obs.digest, obs.revision, p.attempt, p.mode,
            p.value, p.convergence, p.memory_version, circuits[0] if len(circuits) == 1 else None,
            'adaptive_graph_circuit' if circuits else 'adaptive_graph', proof, cost.snapshot(),
            p.program.digest if p.program is not None else None, tuple(sorted(p.state.items())),
            circuit_ids=circuits, expanded_paths=tuple(path.path for path in ws.routes),
            graph_complete=ws.complete, failure_reason=p.failure_reason, adaptive_config_signature=self.config.signature)
        if self.memory.digest != p.memory_hash:
            raise ContractError('R0.2 inference mutated persistent memory')
        self.trace.emit('r02_decision', plain(decision))
        self._held[p.decision_id] = (obs, decision, fingerprint(plain(decision)), p.memory_hash)
        self._pending = None
        return decision

    def feedback(self, feedback: Feedback) -> dict:
        if self._pending is not None or self.trace._closed:
            raise ContractError('feedback during active attempt or closed trace')
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
        if self._pending is not None or self.trace._closed:
            raise ContractError('revision request during active attempt or closed trace')
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
