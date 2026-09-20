"""R0.3.1: 회로 선택용 prior와 판단용 learned drive의 적용 범위를 분리한다.

memory의 학습 규칙·kernel configuration signature는 바꾸지 않는다.
legacy의 문서/이벤트는 이전 바이트 의미를 유지하고 비기본 정책만 명시적으로 기록한다.
"""
from __future__ import annotations
from dataclasses import dataclass
from .model import ContractError, fingerprint

SCHEMA = 'hcr-judgment-prior-policy-v1'
SCOPES = ('legacy', 'route_only')


def validate_scope(scope: str) -> str:
    if type(scope) is not str or scope not in SCOPES:
        raise ContractError('judgment prior scope must be legacy or route_only')
    return scope


@dataclass(frozen=True)
class PriorPolicy:
    judgment_scope: str = 'legacy'

    def __post_init__(self):
        validate_scope(self.judgment_scope)

    def document(self) -> dict:
        body = dict(schema=SCHEMA, judgment_scope=self.judgment_scope)
        return dict(body, sha256=fingerprint(body))


def policy_fields(scope: str) -> dict:
    validate_scope(scope)
    return {} if scope == 'legacy' else {'prior_policy': PriorPolicy(scope).document()}


def read_scope(container: dict) -> str:
    """필드 없는 과거 형식은 legacy다. 비기본 정책의 누락은 상위 schema/계보가 거부한다."""
    if 'prior_policy' not in container:
        return 'legacy'
    raw = container['prior_policy']
    if not isinstance(raw, dict) or set(raw) != {'schema', 'judgment_scope', 'sha256'}:
        raise ContractError('malformed judgment prior policy')
    scope = validate_scope(raw['judgment_scope'])
    if scope == 'legacy' or raw != PriorPolicy(scope).document():
        raise ContractError('noncanonical policy or policy checksum mismatch')
    return scope
