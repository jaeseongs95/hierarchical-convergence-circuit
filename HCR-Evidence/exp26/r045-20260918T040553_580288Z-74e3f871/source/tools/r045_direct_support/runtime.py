"""Unchanged R044 worker and constructor gate. No family, answer, map or proof is supplied."""
from copy import deepcopy
from .storage import require


def worker(observation, config, memory, budget, use_circuits, event_sink):
    require(type(use_circuits) is bool, 'use_circuits must be a bool')
    from r044_reuse_contribution.runtime import worker as inherited_worker
    return inherited_worker(deepcopy(observation), deepcopy(config), deepcopy(memory),
        deepcopy(budget), 'input_order', use_circuits, event_sink)
