"""R037 계약을 유지하며 실험군과 terminal readout의 의미를 명시한다."""
from __future__ import annotations
from r037_online_selection.contracts import (
    Budget, SCOPES, SELECTION_LIMITS, USAGE_KEYS, digest, require, demand,
    finite_nonnegative, validate_public_observation,
)

ARMS = ('native', 'posthoc_support', 'online_support')
BASE_POLICY = {'native': 'native_saved', 'posthoc_support': 'native_saved',
               'online_support': 'support_first'}


def terminal_readout(run: dict) -> tuple[dict | None, str]:
    """마지막 관찰이 아니라 실제 종료 경계와 일치하는 readout만 사용한다."""
    p = run['packet']['document']['engine']['pending']
    if not run['candidates']:
        return None, 'no_readout'
    if p is None or not p['ready']:
        return None, 'terminal_incomplete'
    if p['failure_reason'] is not None:
        return None, 'engine_failure'
    last = run['candidates'][-1]
    if last['reference']['generation'] != len(run['packet']['document']['transitions']) - 1:
        return None, 'stale_readout'
    return last, 'terminal_readout'
