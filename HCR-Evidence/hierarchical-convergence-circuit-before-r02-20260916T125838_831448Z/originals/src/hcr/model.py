"""공개 관측·상태·신호·판단 계약. 숨은 세계 상태나 정답은 이 모듈에 없다."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from math import isfinite
import hashlib
import json


class ContractError(ValueError):
    """입력/단계/저장 계약 위반. 논리적 오답과 구분한다."""


class ExpansionLimit(ContractError):
    """명시적 그래프 확장 자원 한도. 소프트웨어 계약 오류와 구분한다."""


class Mode(str, Enum):
    TRAIN = 'train'
    FROZEN_EVAL = 'frozen_eval'
    ADAPT = 'adapt'


class Status(str, Enum):
    STABLE_DECISION = 'stable_decision'
    STABLE_AMBIGUOUS = 'stable_ambiguous'
    OSCILLATING = 'oscillating'
    BUDGET_EXHAUSTED = 'budget_exhausted'
    NO_CANDIDATE = 'no_candidate'
    UNSUPPORTED = 'unsupported'


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def identifier(value: str) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 128 and all(ord(c) >= 32 for c in value)


@dataclass(frozen=True)
class Config:
    evidence_gain: float = 4.0
    relation_gain: float = 2.0
    top_down_gain: float = 0.35
    prior_gain: float = 2.0
    self_excitation: float = 0.25
    inhibition: float = 0.20
    damping: float = 0.45
    temperature: float = 1.0
    residual_tolerance: float = 1e-6
    margin_threshold: float = 0.30
    patience: int = 4
    max_ticks: int = 160
    max_edges: int = 8
    max_paths: int = 4
    max_path_length: int = 4
    max_groups: int = 32  # 2 candidates/group => 64 candidates
    max_search: int = 2048
    min_valid_episodes: int = 3
    max_circuits: int = 16
    weakening: float = 0.20
    learning_rate: float = 0.25
    max_observation_requests: int = 2

    def __post_init__(self) -> None:
        integer_fields = ('patience', 'max_ticks', 'max_edges', 'max_paths', 'max_path_length',
                          'max_groups', 'max_search', 'min_valid_episodes', 'max_circuits',
                          'max_observation_requests')
        for k, v in asdict(self).items():
            if k in integer_fields:
                if type(v) is not int or v < 1: raise ContractError('양의 정수 설정 필요: '+k)
            elif type(v) not in (int, float) or not isfinite(v) or v < 0:
                raise ContractError('유한 비음수 설정 필요: '+k)
        if not 0 < self.damping <= 1 or self.temperature <= 0 or self.residual_tolerance <= 0:
            raise ContractError('damping/temperature/tolerance 범위')
        if not 0 < self.margin_threshold < 1 or not 0 < self.weakening < 1 or not 0 < self.learning_rate <= 1:
            raise ContractError('margin/weakening/learning 범위')
        if self.max_ticks < self.patience or self.max_edges > 8 or self.max_paths > 4 or self.max_groups > 32 or self.max_path_length > 4:
            raise ContractError('R0.1의 작고 유한한 범위 초과')

    @property
    def signature(self) -> str:
        return fingerprint(asdict(self))


@dataclass(frozen=True)
class EdgeObservation:
    id: str
    source: str
    target: str
    score: float | None  # [-1,1] 공개 측정. 내부 truth가 아니다.

    def __post_init__(self) -> None:
        if not all(identifier(x) for x in (self.id, self.source, self.target)) or self.source == self.target:
            raise ContractError('edge identity/self-loop')
        if self.score is not None and (type(self.score) not in (int, float) or not isfinite(self.score) or not -1 <= self.score <= 1):
            raise ContractError('score는 None 또는 [-1,1]의 유한 수')


@dataclass(frozen=True)
class Observation:
    episode_id: str
    revision: int
    start: str
    goal: str
    edges: tuple[EdgeObservation, ...]

    def __post_init__(self) -> None:
        if not all(identifier(x) for x in (self.episode_id, self.start, self.goal)) or self.start == self.goal:
            raise ContractError('episode/start/goal identity')
        if type(self.revision) is not int or self.revision < 0 or not isinstance(self.edges, tuple):
            raise ContractError('revision/immutable edges')
        if not all(isinstance(e, EdgeObservation) for e in self.edges):
            raise ContractError('edges must be EdgeObservation records')
        if not self.edges or len({e.id for e in self.edges}) != len(self.edges) or len({(e.source,e.target) for e in self.edges}) != len(self.edges):
            raise ContractError('empty/duplicate edges')
        vertices = {n for e in self.edges for n in (e.source, e.target)}
        if self.start not in vertices or self.goal not in vertices: raise ContractError('unknown endpoints')

    @property
    def digest(self) -> str:
        return fingerprint(asdict(self))


@dataclass(frozen=True)
class Group:
    id: str
    level: int  # A0 feature, A1 relation. proof D와 다르다.
    bias: float = 0.0


@dataclass(frozen=True)
class Link:
    source: str
    target: str
    weight: float
    kind: str  # support / top_down


@dataclass(frozen=True)
class Program:
    groups: tuple[Group, ...]
    links: tuple[Link, ...]
    paths: tuple[tuple[int, ...], ...]  # template edge role indices
    edge_count: int

    def validate(self, config: Config) -> None:
        names = [g.id for g in self.groups]
        if not names or len(names) != len(set(names)) or 'goal' not in names :
            raise ContractError('signal group identity/budget')
        if len(names)>config.max_groups:raise ExpansionLimit('signal group budget')
        for g in self.groups:
            if g.level not in (0,1) or not isfinite(g.bias): raise ContractError('A level/bias')
        for e in self.links:
            if e.source not in names or e.target not in names or not isfinite(e.weight) or e.kind not in ('support','top_down'):
                raise ContractError('signal link')
        if not 1 <= self.edge_count <= config.max_edges or not 1 <= len(self.paths) <= config.max_paths:
            raise ContractError('program size')
        for path in self.paths:
            if not 1 <= len(path) <= config.max_path_length or len(set(path)) != len(path) or any(type(i) is not int or not 0 <= i < self.edge_count for i in path):
                raise ContractError('path role index')

    @property
    def digest(self) -> str:
        return fingerprint(asdict(self))


@dataclass
class Cost:
    search_edge_checks: int = 0
    dynamic_groups_created: int = 0
    dynamic_links_created: int = 0
    binding_checks: int = 0
    recall_checks: int = 0
    circuit_groups_instantiated: int = 0
    kernel_ticks: int = 0
    group_updates: int = 0
    signal_transmissions: int = 0
    normalization_ops: int = 0
    proof_nodes_reconstructed: int = 0
    compilation_items: int = 0
    memory_write_items: int = 0
    observation_requests: int = 0
    verification_checks: int = 0
    wall_seconds: float = 0.0

    def snapshot(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Convergence:
    status: Status
    ticks: int
    residual: float
    margin: float
    stable_steps: int


@dataclass(frozen=True)
class ProofNode:
    id: str
    rule: str
    edge_id: str | None
    parents: tuple[str, ...]
    path_index: int | None = None


@dataclass(frozen=True)
class Proof:
    nodes: tuple[ProofNode, ...]
    final: str | None
    primitive_depth: int | None
    assumed_edges: tuple[tuple[str, bool], ...]
    under_assumptions_valid: bool
    paths: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class Decision:
    id: str
    episode_id: str
    observation_digest: str
    observation_revision: int
    attempt: int
    mode: Mode
    value: bool | None
    convergence: Convergence
    memory_version: int
    circuit_id: str | None
    method: str
    proof: Proof
    cost: dict
    program_digest: str | None
    state: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class Feedback:
    id: str
    decision_id: str
    observation_digest: str
    correct: bool | None
    proof_valid: bool
    source: str = 'external_reference'

    def __post_init__(self) -> None:
        if not all(identifier(x) for x in (self.id,self.decision_id,self.source)) or (self.correct is not None and type(self.correct) is not bool) or type(self.proof_valid) is not bool:
            raise ContractError('feedback contract')
        if len(self.observation_digest) != 64 or any(c not in '0123456789abcdef' for c in self.observation_digest):
            raise ContractError('feedback observation digest')


@dataclass(frozen=True)
class ObservationRequest:
    decision_id: str
    episode_id: str
    revision: int
    edge_ids: tuple[str, ...]
    reason: str
