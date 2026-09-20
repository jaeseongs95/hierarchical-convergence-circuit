"""R0.2.1 dependency 경계의 실행 상태. 이 문서는 session 검산 뒤에만 복원한다.

observation revision, memory version, generation은 서로 대체하지 않는다.
새 network는 R0.2와 같이 fresh state로 시작하며, 종료된 network 상태만 보존한다.
"""
from __future__ import annotations
from dataclasses import dataclass, field, fields
from . import codec
from .model import (Observation, Mode, AdaptiveCost, MismatchSignal, Program, Convergence,
                    Status, Feedback, ObservationRequest, fingerprint)


@dataclass
class ExecutionState:
    observation: Observation
    mode: Mode
    revision_of: str | None
    attempt: int
    decision_id: str
    memory_hash: str
    memory_version: int
    config_signature: str
    switches: tuple[bool, bool, bool]
    cost: AdaptiveCost
    workspace: object
    mismatch: MismatchSignal
    program: Program | None = None
    state: dict = field(default_factory=dict)
    convergence: Convergence = field(default_factory=lambda: Convergence(Status.NO_CANDIDATE, 0, 0.0, 0.0, 0))
    value: bool | None = None
    network_id: str | None = None
    settled_paths: tuple = ()
    failure_reason: str | None = None
    ready: bool = False
    active_seconds: float = 0.0
    judgment_prior: str = "legacy"

    def document(self):
        data = {f.name: codec.plain(getattr(self, f.name)) for f in fields(self)
                if f.name not in ('workspace', 'cost', 'judgment_prior')}
        from .prior_policy import policy_fields
        data.update(policy_fields(self.judgment_prior))
        ws = self.workspace
        data['cost'] = self.cost.snapshot()
        data['workspace'] = dict(frontier=codec.plain(ws.frontier), routes=codec.plain(ws.routes),
                                 known=[list(p) for p in sorted(ws.known)], next_node=ws._next_node)
        return data


def engine_document(engine):
    """Trace는 별도 보존한다. 반환 객체를 수정해도 실행 객체는 바뀌지 않는다."""
    from .prior_policy import policy_fields
    return dict(config=codec.plain(engine.config), memory=engine.memory.document(),
        **policy_fields(engine.judgment_prior),
        switches=dict(use_circuits=engine.use_circuits, top_down=engine.top_down,
                      allow_reexpansion=engine.allow_reexpansion), attempts=dict(engine._attempts),
        held={k: dict(observation=codec.plain(v[0]), decision=codec.plain(v[1]),
                      recorded_hash=v[2], memory_hash=v[3]) for k, v in engine._held.items()},
        feedback=codec.plain(engine._feedback), requests=codec.plain(engine._requests),
        pending=engine._pending.document() if engine._pending is not None else None)


def _prefix(raw):
    from .workspace import RoutePrefix, AppliedCircuit
    from .identity import NodeRef, binding_from
    return RoutePrefix(NodeRef(**raw['node']), tuple(raw['path']), tuple(raw['visited']),
        tuple(AppliedCircuit(**dict(use, binding=binding_from(use['binding']))) for use in raw['uses']))


def restore_engine(document, records):
    """검산된 표준 JSON만 재구성. pickle, 외부 코드 로딩, 재추론을 하지 않는다."""
    from .runtime import AdaptiveEngine
    from .circuits import AdaptiveMemory
    from .workspace import AdaptiveWorkspace
    from .model import Group, Link
    from .trace import Trace
    from .prior_policy import read_scope
    engine = AdaptiveEngine.__new__(AdaptiveEngine)
    engine._judgment_prior = read_scope(document)
    engine.config = codec.adaptive_config_from(document['config'])
    engine.memory = AdaptiveMemory.from_document(document['memory'], engine.config)
    engine.trace = Trace()
    # 검증한 원래 event 문자열의 의미/해시를 그대로 보존. engine_created를 다시 emit하지 않는다.
    engine.trace._records = [codec.dumps(r) for r in records]
    engine.trace._head = records[-1]['sha256'] if records else '0' * 64
    for k, v in document['switches'].items():
        setattr(engine, k, v)
    engine._attempts = dict(document['attempts'])
    engine._held = {k: (codec.observation_from(v['observation']), codec.adaptive_decision_from(v['decision']),
                         v['recorded_hash'], v['memory_hash']) for k, v in document['held'].items()}
    engine._feedback = {k: Feedback(**v) for k, v in document['feedback'].items()}
    engine._requests = {k: ObservationRequest(**dict(v, edge_ids=tuple(v['edge_ids'])))
                        for k, v in document['requests'].items()}
    engine._pending = None
    if document['pending'] is not None:
        raw = dict(document['pending'])
        pending_scope = read_scope(raw)
        raw.pop('prior_policy', None)
        raw['judgment_prior'] = pending_scope
        obs = codec.observation_from(raw['observation'])
        cost = AdaptiveCost(**{f.name: raw['cost'][f.name] for f in fields(AdaptiveCost)})
        ws = AdaptiveWorkspace.__new__(AdaptiveWorkspace)
        ws.observation, ws.config, ws.cost = obs, engine.config, cost
        ws.trace, ws.decision_id = engine.trace, raw['decision_id']
        wd = raw['workspace']
        ws.frontier, ws.routes = [_prefix(p) for p in wd['frontier']], [_prefix(p) for p in wd['routes']]
        ws.known, ws._next_node = {tuple(p) for p in wd['known']}, wd['next_node']
        pr = raw['program']
        program = None if pr is None else Program(tuple(Group(**g) for g in pr['groups']),
            tuple(Link(**l) for l in pr['links']), tuple(tuple(p) for p in pr['paths']), pr['edge_count'])
        engine._pending = ExecutionState(**dict(raw, observation=obs, mode=Mode(raw['mode']),
            switches=tuple(raw['switches']), cost=cost, workspace=ws, program=program,
            mismatch=MismatchSignal(**raw['mismatch']),
            convergence=Convergence(**dict(raw['convergence'], status=Status(raw['convergence']['status']))),
            settled_paths=tuple(tuple(p) for p in raw['settled_paths'])))
    return engine
