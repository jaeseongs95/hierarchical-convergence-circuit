"""기존 native API의 얇은 연결 계층. src/hcr의 소스/상태/proof를 수정하지 않는다."""
from __future__ import annotations
from copy import deepcopy
from .contracts import require


class NativeBackend:
    kind = 'native_hcr'

    def begin(self, observation: dict, config: dict, memory: dict, scope: str, session_id: str):
        from hcr import codec
        from hcr.circuits import AdaptiveMemory
        from hcr.model import Mode
        from hcr.sessions import AdaptiveSession
        cfg = codec.adaptive_config_from(config)
        session = AdaptiveSession(cfg, AdaptiveMemory.from_document(deepcopy(memory), cfg),
                                  session_id=session_id, judgment_prior=scope)
        session.begin(codec.observation_from(observation), Mode.FROZEN_EVAL)
        return session

    def capture(self, session) -> dict:
        from hcr.review import capture_candidate
        return capture_candidate(session, 0)

    def project(self, candidate: dict) -> dict:
        from r035_frozen_selection.native_bridge import project
        return project(candidate)

    def select(self, view: dict, policy: str, limits: dict) -> dict:
        from r035_frozen_selection.selection import run_policy
        from r035_frozen_selection.contracts import Limits
        return run_policy(view, policy, Limits(**limits))

    def reservation(self, session) -> int:
        from hcr import codec
        from hcr.review import tick_bound
        value = tick_bound(session.current, codec.adaptive_config_from(session.current['config']))
        require(type(value) is int and value >= 0, 'native tick 예약량')
        return value
