"""Producer-side protocol. The auditor reimplements target and intervention rules."""
from __future__ import annotations
from copy import deepcopy
from .common import require

ARMS = ('hold', 'same_input_restart', 'echo_revision_restart', 'strength_revision_restart')

def select_probe(observation: dict, candidate: dict | None) -> dict:
    """Only public observations/diagnostics and already expanded paths are read.

    Prefer a weak sign-conflict edge. Otherwise inspect weak known edges in the
    existing expanded paths. Tie-break by observation slot, never by lexical ID.
    This is a NEW experiment policy, not the native R033 measurement selector.
    """
    if candidate is None:
        return dict(edge_id=None, slot=None, reason='no_candidate', slots_inspected=0)
    edges = observation['edges']
    conflict = set(candidate['diagnostic']['suggestion']['sign_conflict_edges'])
    explored = {i for path in candidate['decision']['expanded_paths'] for i in path}
    possible = []
    for i, edge in enumerate(edges):
        score = edge['score']
        if type(score) in (int, float) and 0 < abs(score) < 1 and (edge['id'] in conflict or i in explored):
            possible.append((0 if edge['id'] in conflict else 1, abs(score), i, edge['id']))
    if not possible:
        return dict(edge_id=None, slot=None, reason='no_weak_known_dependency', slots_inspected=len(edges))
    priority, _, slot, edge = min(possible)
    return dict(edge_id=edge, slot=slot,
                reason='weak_sign_conflict' if priority == 0 else 'weak_explored_dependency',
                slots_inspected=len(edges))

def revised_input(original: dict, arm: str, target: dict) -> dict:
    require(arm in ARMS, 'Unknown arm')
    out = deepcopy(original)
    if arm in ('echo_revision_restart', 'strength_revision_restart'):
        slot = target['slot']
        require(type(slot) is int and 0 <= slot < len(out['edges']), 'Missing probe target')
        edge = out['edges'][slot]
        require(edge['id'] == target['edge_id'] and 0 < abs(edge['score']) < 1, 'Invalid probe target')
        out['revision'] += 1
        if arm == 'strength_revision_restart':
            edge['score'] = 1.0 if edge['score'] > 0 else -1.0
    return out

def terminal(candidate: dict | None) -> dict:
    accepted = candidate is not None and candidate['readout']['accepted'] is True
    return dict(accepted=accepted,
                value=candidate['readout']['value'] if accepted else None,
                selected_candidate_id=candidate['candidate_id'] if accepted else None)
