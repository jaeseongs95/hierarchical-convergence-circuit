"""Only the native constructor switch differs; the R041 worker loop is unchanged."""
from copy import deepcopy
from .storage import require


def backend_for(use_circuits):
    from r037_online_selection.backend import NativeBackend
    require(type(use_circuits) is bool, 'use_circuits must be a bool, not an integer')
    class ReuseBackend(NativeBackend):
        def begin(self, observation, config, memory, scope, session_id):
            from hcr import codec
            from hcr.circuits import AdaptiveMemory
            from hcr.model import Mode
            from hcr.sessions import AdaptiveSession
            require(scope == 'route_only', 'judgment prior changed')
            cfg=codec.adaptive_config_from(config)
            session=AdaptiveSession(cfg, AdaptiveMemory.from_document(deepcopy(memory),cfg),
                session_id=session_id, judgment_prior=scope, use_circuits=use_circuits)
            session.begin(codec.observation_from(observation),Mode.FROZEN_EVAL)
            require(session.current['switches']==dict(use_circuits=use_circuits,
                top_down=True,allow_reexpansion=True), 'native gate or other switch mismatch')
            require(session.current['memory']==memory and session.current['config']==config,
                'gate changed memory/config')
            return session
    return ReuseBackend()


def worker(observation,config,memory,budget,scheduler,use_circuits,event_sink):
    from r041_scheduler_direction.runtime import ScheduledTimingTrial
    from r041_scheduler_direction.contracts import Budget
    require(scheduler=='input_order', 'unregistered scheduler')
    # No case/variant, evaluation truth, route label or inverse map is passed to native execution.
    return ScheduledTimingTrial(deepcopy(observation),deepcopy(config),deepcopy(memory),
        'route_only','online_support',Budget(**budget),scheduler=scheduler,
        backend=backend_for(use_circuits),event_sink=event_sink)
