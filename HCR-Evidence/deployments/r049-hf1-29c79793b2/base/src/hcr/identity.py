"""Node / Semantic / Role identity를 분리한다. 의미가 같아도 실행 node는 다를 수 있다."""
from __future__ import annotations
from dataclasses import dataclass
from typing import NewType
from .model import ContractError, Observation, identifier, fingerprint

NodeIdentity = NewType('NodeIdentity', str)
SemanticIdentity = NewType('SemanticIdentity', str)
RoleIdentity = NewType('RoleIdentity', str)


@dataclass(frozen=True)
class NodeRef:
    node_id: NodeIdentity
    semantic_id: SemanticIdentity
    revision: int

    def __post_init__(self) -> None:
        if not identifier(self.node_id) or not identifier(self.semantic_id):
            raise ContractError('invalid node/semantic identity')
        if type(self.revision) is not int or self.revision < 0:
            raise ContractError('invalid node revision')


@dataclass(frozen=True)
class RoleBinding:
    observation_digest: str
    revision: int
    pattern_id: str
    roles: tuple[tuple[RoleIdentity, NodeRef], ...]
    edge_order: tuple[int, ...]

    def check(self, obs: Observation, length: int) -> None:
        if self.observation_digest != obs.digest or self.revision != obs.revision:
            raise ContractError('stale role binding')
        if len(self.edge_order) != length or len(set(self.edge_order)) != length:
            raise ContractError('non-injective edge binding')
        if any(type(i) is not int or not 0 <= i < len(obs.edges) for i in self.edge_order):
            raise ContractError('edge binding index')
        if tuple(r for r, _ in self.roles) != tuple('R' + str(i) for i in range(length + 1)):
            raise ContractError('role identity/order')
        refs = [ref for _, ref in self.roles]
        if (len({r.node_id for r in refs}) != len(refs)
                or len({r.semantic_id for r in refs}) != len(refs)
                or any(r.revision != obs.revision for r in refs)):
            raise ContractError('role/node/revision consistency')
        for i, slot in enumerate(self.edge_order):
            edge = obs.edges[slot]
            if (edge.source, edge.target) != (refs[i].semantic_id, refs[i + 1].semantic_id):
                raise ContractError('role relation does not bind to the current observation')


def bind_path(obs: Observation, pattern_id: str, slots: tuple[int, ...]) -> RoleBinding:
    if not slots:
        raise ContractError('empty role path')
    if any(type(i) is not int or not 0 <= i < len(obs.edges) for i in slots):
        raise ContractError('role path index')
    vertices = [obs.edges[slots[0]].source] + [obs.edges[i].target for i in slots]
    context = fingerprint((obs.digest, pattern_id, slots))[:24]
    roles = tuple((RoleIdentity('R' + str(i)),
                   NodeRef(NodeIdentity('binding:' + context + ':' + str(i)),
                           SemanticIdentity(vertex), obs.revision))
                  for i, vertex in enumerate(vertices))
    binding = RoleBinding(obs.digest, obs.revision, pattern_id, roles, slots)
    binding.check(obs, len(slots))
    return binding


def binding_from(raw: dict) -> RoleBinding:
    try:
        if set(raw) != {'observation_digest', 'revision', 'pattern_id', 'roles', 'edge_order'}:
            raise ContractError('role binding fields')
        return RoleBinding(raw['observation_digest'], raw['revision'], raw['pattern_id'],
                           tuple((RoleIdentity(role), NodeRef(**ref)) for role, ref in raw['roles']),
                           tuple(raw['edge_order']))
    except (KeyError, TypeError, ValueError) as error:
        raise ContractError('invalid role binding packet') from error
