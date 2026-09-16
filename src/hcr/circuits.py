"""역할화한 실행 구조의 versioned memory. 입력→답 캐시가 아니다."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from .model import Config, Program, Group, Link, Cost, ContractError, Observation, fingerprint
from .binding import Topology, Binding, bind
from . import codec


@dataclass
class Circuit:
    id: str
    topology: Topology
    program: Program
    config_signature: str
    strength: float
    positive: int
    negative: int
    evidence_episodes: list[str]
    feedback_ids: list[str]
    proof_digests: list[str]
    failures: int = 0
    version: int = 1
    active: bool = True

    @property
    def balance(self) -> float:
        return (self.positive-self.negative)/(self.positive+self.negative+1)


@dataclass
class Pending:
    topology: Topology
    program: Program
    episodes: list[str]
    feedback_ids: list[str]
    proof_digests: list[str]
    positive: int
    negative: int


@dataclass
class Memory:
    version: int = 0
    circuits: list[Circuit] = field(default_factory=list)
    pending: list[Pending] = field(default_factory=list)
    consumed_feedback: list[str] = field(default_factory=list)
    patches: list[dict] = field(default_factory=list)

    def document(self) -> dict:
        return {'schema':'hcr-memory-r01','version':self.version,
                'circuits':codec.plain(self.circuits),'pending':codec.plain(self.pending),
                'consumed_feedback':list(self.consumed_feedback),'patches':codec.plain(self.patches)}

    @property
    def digest(self) -> str:
        return fingerprint(self.document())

    def recall(self, obs: Observation, config: Config, cost: Cost) -> tuple[Circuit,Binding] | None:
        for circuit in sorted(self.circuits,key=lambda c:(-c.strength,c.id)):
            cost.recall_checks+=1
            if not circuit.active or circuit.config_signature!=config.signature: continue
            binding=bind(circuit.topology,obs,config,cost)
            if binding is not None: return circuit,binding
        return None

    def save(self,path: Path, *, replace: bool=False) -> None:
        document=self.document()
        codec.save(path,{'document':document,'sha256':fingerprint(document)},replace=replace)

    @classmethod
    def load(cls,path: Path,config: Config) -> 'Memory':
        return cls.from_packet(codec.loads(Path(path).read_bytes()),config)

    @classmethod
    def from_document(cls, document:dict, config:Config) -> 'Memory':
        return cls.from_packet({'document':document,'sha256':fingerprint(document)},config)

    @classmethod
    def from_packet(cls, packet:dict, config:Config) -> 'Memory':
        if not isinstance(packet,dict):raise ContractError('memory packet must be an object')
        if set(packet)!={'document','sha256'} or fingerprint(packet['document'])!=packet['sha256']:
            raise ContractError('memory integrity mismatch')
        d=packet['document']
        if not isinstance(d,dict):raise ContractError('memory document must be an object')
        if set(d)!={'schema','version','circuits','pending','consumed_feedback','patches'} or d['schema']!='hcr-memory-r01':
            raise ContractError('memory schema')
        if type(d['version']) is not int or d['version']<0 or len(d['circuits'])>config.max_circuits or len(d['pending'])>config.max_circuits:
            raise ContractError('memory bounds')
        if not isinstance(d['consumed_feedback'],list) or not isinstance(d['patches'],list) or d['version']!=len(d['consumed_feedback']) or d['version']!=len(d['patches']):
            raise ContractError('memory history/version consistency')
        for i,patch in enumerate(d['patches']):
            if not isinstance(patch,dict):raise ContractError('invalid memory patch')
            if patch.get('version')!=i+1 or patch.get('previous_version')!=i or patch.get('feedback_id')!=d['consumed_feedback'][i]:
                raise ContractError('memory patch chain')
        from .workspace import make_program,discover_paths
        def components(raw):
            top=raw['topology'];topology=Topology(top['vertices'],top['start'],top['goal'],tuple(tuple(v) for v in top['edges']))
            top_cost=Cost();paths=discover_paths(topology,config,top_cost)
            obj=raw['program'];program=Program(tuple(Group(**g) for g in obj['groups']),tuple(Link(**e) for e in obj['links']),tuple(tuple(p) for p in obj['paths']),obj['edge_count'])
            if program!=make_program(len(topology.edges),paths,config):raise ContractError('invalid compiled structure certificate')
            return topology,program
        circuits=[];pending=[]
        try:
            for r in d['circuits']:
                top,program=components(r);x=dict(r,topology=top,program=program)
                c=Circuit(**x)
                if c.config_signature!=config.signature or type(c.strength) not in (int,float) or not 0<=c.strength<=1 or any(type(v) is not int or v<0 for v in (c.positive,c.negative,c.failures,c.version)) or c.version<1 or type(c.active) is not bool or len(set(c.evidence_episodes))<config.min_valid_episodes:
                    raise ContractError('circuit contract/provenance')
                if len(set(c.evidence_episodes))!=len(c.evidence_episodes) or c.positive+c.negative!=len(c.evidence_episodes) or len(c.proof_digests)<len(c.evidence_episodes) or not set(c.feedback_ids)<=set(d['consumed_feedback']):
                    raise ContractError('circuit evidence provenance')
                circuits.append(c)
            for r in d['pending']:
                top,program=components(r);item=Pending(**dict(r,topology=top,program=program))
                if len(set(item.episodes))!=len(item.episodes) or any(type(v) is not int or v<0 for v in (item.positive,item.negative)) or item.positive+item.negative!=len(item.episodes) or not set(item.feedback_ids)<=set(d['consumed_feedback']):raise ContractError('pending evidence provenance')
                pending.append(item)
        except (KeyError,TypeError,ValueError) as exc:
            raise ContractError('invalid memory data') from exc
        if len({c.id for c in circuits})!=len(circuits) or len(set(d['consumed_feedback']))!=len(d['consumed_feedback']):
            raise ContractError('duplicate memory records')
        return cls(d['version'],circuits,pending,d['consumed_feedback'],d['patches'])


# R0.2는 부분 회로용 명시적 schema를 사용한다. R0.1 memory를 자동 변환하지 않는다.
from .patterns import CircuitPattern, pattern_from
from .model import AdaptiveConfig, identifier


@dataclass
class PatternCircuit:
    pattern: CircuitPattern
    strength: float
    evidence_episodes: list[str]
    feedback_ids: list[str]
    proof_digests: list[str]
    version: int = 1
    failures: int = 0
    active: bool = True

    @property
    def id(self) -> str:
        return self.pattern.id

    @property
    def balance(self) -> float:
        # R0.2에서는 externally verified positive path motif만 등록한다.
        return len(self.evidence_episodes) / (len(self.evidence_episodes) + 1)


@dataclass
class PatternPending:
    pattern: CircuitPattern
    evidence_episodes: list[str] = field(default_factory=list)
    feedback_ids: list[str] = field(default_factory=list)
    proof_digests: list[str] = field(default_factory=list)


@dataclass
class AdaptiveMemory:
    config_signature: str
    version: int = 0
    circuits: list[PatternCircuit] = field(default_factory=list)
    pending: list[PatternPending] = field(default_factory=list)
    consumed_feedback: list[str] = field(default_factory=list)
    patches: list[dict] = field(default_factory=list)

    @classmethod
    def empty(cls, config: AdaptiveConfig) -> 'AdaptiveMemory':
        return cls(config.signature)

    def document(self) -> dict:
        return dict(schema='hcr-memory-r02', config_signature=self.config_signature, version=self.version,
                    circuits=codec.plain(self.circuits), pending=codec.plain(self.pending),
                    consumed_feedback=list(self.consumed_feedback), patches=codec.plain(self.patches))

    @property
    def digest(self) -> str:
        return fingerprint(self.document())

    def save(self, path: Path, *, replace: bool = False) -> None:
        document = self.document()
        codec.save(path, dict(document=document, sha256=fingerprint(document)), replace=replace)

    @classmethod
    def load(cls, path: Path, config: AdaptiveConfig) -> 'AdaptiveMemory':
        return cls.from_packet(codec.loads(Path(path).read_bytes()), config)

    @classmethod
    def from_packet(cls, packet: dict, config: AdaptiveConfig) -> 'AdaptiveMemory':
        if (not isinstance(packet, dict) or set(packet) != {'document', 'sha256'}
                or fingerprint(packet['document']) != packet['sha256']):
            raise ContractError('R0.2 memory integrity')
        return cls.from_document(packet['document'], config)

    @classmethod
    def from_document(cls, document: dict, config: AdaptiveConfig) -> 'AdaptiveMemory':
        required = {'schema', 'config_signature', 'version', 'circuits', 'pending', 'consumed_feedback', 'patches'}
        if not isinstance(document, dict) or set(document) != required or document['schema'] != 'hcr-memory-r02':
            raise ContractError('R0.2 memory schema; R0.1 memory must stay on the R0.1 path')
        d = codec.loads(codec.dumps(document))
        if d['config_signature'] != config.signature:
            raise ContractError('R0.2 memory/config mismatch')
        if any(not isinstance(d[k], list) for k in ('circuits', 'pending', 'consumed_feedback', 'patches')):
            raise ContractError('R0.2 memory arrays')
        if (type(d['version']) is not int or d['version'] < 0
                or d['version'] != len(d['consumed_feedback']) or d['version'] != len(d['patches'])
                or len(set(d['consumed_feedback'])) != d['version']
                or any(not identifier(x) for x in d['consumed_feedback'])
                or len(d['circuits']) > config.kernel.max_circuits
                or len(d['pending']) > config.kernel.max_circuits):
            raise ContractError('R0.2 memory history/bounds')
        for i, patch in enumerate(d['patches']):
            if (not isinstance(patch, dict) or patch.get('version') != i + 1
                    or patch.get('previous_version') != i or patch.get('feedback_id') != d['consumed_feedback'][i]):
                raise ContractError('R0.2 memory patch chain')
        circuits = []
        pending = []
        try:
            for raw, compiled in [(r, True) for r in d['circuits']] + [(r, False) for r in d['pending']]:
                pattern = pattern_from(raw['pattern'], config.kernel)
                if pattern.length not in config.pattern_lengths:
                    raise ContractError('unregistered pattern length')
                if any(not isinstance(raw[k], list) for k in ('evidence_episodes', 'feedback_ids', 'proof_digests')):
                    raise ContractError('pattern evidence arrays')
                episodes, feedbacks, proofs = (raw[k] for k in ('evidence_episodes', 'feedback_ids', 'proof_digests'))
                if (not episodes or len(set(episodes)) != len(episodes)
                        or any(not identifier(e) for e in episodes)
                        or len(proofs) != len(episodes) or len(feedbacks) < len(episodes)
                        or len(set(feedbacks)) != len(feedbacks)
                        or not set(feedbacks) <= set(d['consumed_feedback'])
                        or any(not isinstance(h, str) or len(h) != 64 or any(c not in '0123456789abcdef' for c in h) for h in proofs)):
                    raise ContractError('pattern evidence provenance')
                kwargs = dict(raw, pattern=pattern)
                if compiled:
                    item = PatternCircuit(**kwargs)
                    if (type(item.strength) not in (int, float) or not 0 <= item.strength <= 1
                            or type(item.version) is not int or item.version < 1
                            or type(item.failures) is not int or item.failures < 0
                            or type(item.active) is not bool
                            or len(episodes) < config.kernel.min_valid_episodes):
                        raise ContractError('compiled pattern state')
                    circuits.append(item)
                else:
                    if len(episodes) >= config.kernel.min_valid_episodes:
                        raise ContractError('pending threshold was not compiled')
                    pending.append(PatternPending(**kwargs))
        except (KeyError, TypeError, ValueError) as error:
            raise ContractError('invalid R0.2 memory records') from error
        ids = [c.id for c in circuits] + [p.pattern.id for p in pending]
        if len(ids) != len(set(ids)):
            raise ContractError('duplicate R0.2 pattern')
        return cls(d['config_signature'], d['version'], circuits, pending, d['consumed_feedback'], d['patches'])
