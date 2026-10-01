"""검증된 연속 부분 경로의 역할 문법. 인스턴스 이름/이전 답 문자열을 저장하지 않는다."""
from __future__ import annotations
from dataclasses import dataclass
from .model import Config, Program, Group, Link, ContractError, fingerprint
from .codec import plain

CONDITIONS = ('injective_roles', 'contiguous_directed_path', 'current_revision', 'current_measurements')


@dataclass(frozen=True)
class RoleSpec:
    id: str
    kind: str = 'vertex'


@dataclass(frozen=True)
class RelationSpec:
    source_role: str
    target_role: str
    kind: str = 'open_edge'


@dataclass(frozen=True)
class CircuitPattern:
    roles: tuple[RoleSpec, ...]
    relations: tuple[RelationSpec, ...]
    entry_conditions: tuple[str, ...]
    output_role: str
    program: Program
    kernel_signature: str

    @property
    def id(self) -> str:
        return 'pattern-' + fingerprint(plain(self))[:24]

    @property
    def length(self) -> int:
        return len(self.relations)

    def validate(self, config: Config) -> None:
        if not 2 <= self.length <= config.max_path_length:
            raise ContractError('unsupported subgraph size')
        expected_roles = tuple(RoleSpec('R' + str(i)) for i in range(self.length + 1))
        expected_relations = tuple(RelationSpec('R' + str(i), 'R' + str(i + 1)) for i in range(self.length))
        if (self.roles != expected_roles or self.relations != expected_relations
                or self.entry_conditions != CONDITIONS or self.output_role != 'R' + str(self.length)
                or self.kernel_signature != config.signature):
            raise ContractError('subgraph role/entry/output/kernel contract')
        # 구조 certificate를 확인한다. 현재/과거 정답을 계산하는 것이 아니다.
        from .workspace import make_program
        if self.program != make_program(self.length, (tuple(range(self.length)),), config):
            raise ContractError('compiled primitive program certificate')


def make_pattern(length: int, config: Config) -> CircuitPattern:
    from .workspace import make_program
    pattern = CircuitPattern(tuple(RoleSpec('R' + str(i)) for i in range(length + 1)),
                             tuple(RelationSpec('R' + str(i), 'R' + str(i + 1)) for i in range(length)),
                             CONDITIONS, 'R' + str(length),
                             make_program(length, (tuple(range(length)),), config), config.signature)
    pattern.validate(config)
    return pattern


def pattern_from(raw: dict, config: Config) -> CircuitPattern:
    try:
        if set(raw) != {'roles', 'relations', 'entry_conditions', 'output_role', 'program', 'kernel_signature'}:
            raise ContractError('pattern fields')
        p = raw['program']
        program = Program(tuple(Group(**g) for g in p['groups']), tuple(Link(**e) for e in p['links']),
                          tuple(tuple(x) for x in p['paths']), p['edge_count'])
        result = CircuitPattern(tuple(RoleSpec(**r) for r in raw['roles']),
                                tuple(RelationSpec(**r) for r in raw['relations']),
                                tuple(raw['entry_conditions']), raw['output_role'], program, raw['kernel_signature'])
        result.validate(config)
        return result
    except (KeyError, TypeError, ValueError) as error:
        raise ContractError('invalid pattern packet') from error
