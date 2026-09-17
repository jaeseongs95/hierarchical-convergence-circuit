"""기존 R041 native worker에 공개 입력만 전달하는 어댑터. 새 scheduler 구현은 없다."""
from copy import deepcopy
from .storage import require


def worker(observation: dict, config: dict, memory: dict, budget: dict,
           scheduler: str, event_sink):
    from r041_scheduler_direction.runtime import ScheduledTimingTrial
    from r041_scheduler_direction.contracts import Budget
    require(scheduler in ('edge_id_min','edge_id_max'), '등록되지 않은 scheduler')
    # case/variant/edge_map/평가 world는 ScheduledTimingTrial에 전달되지 않는다.
    return ScheduledTimingTrial(deepcopy(observation), deepcopy(config), deepcopy(memory),
        'legacy', 'online_support', Budget(**budget), scheduler=scheduler, event_sink=event_sink)
