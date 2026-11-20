"""R53 event-driven executor on plain (JSON) kernel programs.  No engine imports, no file access.

The update formula is re-stated here from src/hcr/dynamics.py so that the executor is a second
implementation.  One parameter, theta, turns the synchronous dense update into a send-on-delta one:

* a group transmits on all of its outgoing links only when its state differs from the value it
  last transmitted by more than theta (the first tick transmits everything);
* a group is recomputed only when it received a transmission in this tick or its own previous
  recomputation moved it by more than theta; otherwise it keeps its state;
* targets read the last transmitted value of a source, not its current value;
* stopping is the unchanged native rule (residual tolerance, patience, oscillation, max_ticks).

With theta = 0 this skips only exact no-ops, so the trajectory is the native one bit for bit.
"""
from math import exp


def event_settle(program, drives, kernel, top_down, theta):
    groups = [g['id'] for g in program['groups']]
    bias = {g['id']: g['bias'] for g in program['groups']}
    links = [l for l in program['links'] if top_down or l['kind'] != 'top_down']
    incoming = {g: [] for g in groups}
    out_degree = {g: 0 for g in groups}
    for l in links:
        incoming[l['target']].append(l)
        out_degree[l['source']] += 1
    state = {g: 0.5 for g in groups}
    seen = {g: None for g in groups}
    self_active = {g: True for g in groups}
    link_events = group_updates = 0
    history, stable, residual = [], 0, 1.0
    states = []
    status, ticks = 'budget_exhausted', kernel['max_ticks']
    for i in range(1, kernel['max_ticks'] + 1):
        senders = [g for g in groups if seen[g] is None or abs(state[g] - seen[g]) > theta]
        for g in senders:
            seen[g] = state[g]
            link_events += out_degree[g]
        touched = {l['target'] for l in links if l['source'] in senders}
        nxt = {}
        for g in groups:
            p = state[g]
            if g not in touched and not self_active[g]:
                nxt[g] = p
                continue
            total = bias[g] + drives.get(g, 0.0)
            for l in incoming[g]:
                total += l['weight'] * (2 * seen[l['source']] - 1)
            positive = total + kernel['self_excitation'] * p - kernel['inhibition'] * (1 - p)
            negative = -total + kernel['self_excitation'] * (1 - p) - kernel['inhibition'] * p
            z = (positive - negative) / kernel['temperature']
            target = 1 / (1 + exp(-z)) if z >= 0 else exp(z) / (1 + exp(z))
            nxt[g] = (1 - kernel['damping']) * p + kernel['damping'] * target
            self_active[g] = abs(nxt[g] - p) > theta
            group_updates += 1
        residual = max(abs(nxt[g] - state[g]) for g in groups)
        stable = stable + 1 if residual <= kernel['residual_tolerance'] else 0
        states.append(nxt)
        margin = abs(2 * nxt['goal'] - 1)
        if stable >= kernel['patience']:
            status, ticks, state = ('stable_decision' if margin >= kernel['margin_threshold'] else 'stable_ambiguous'), i, nxt
            break
        if history and residual > kernel['residual_tolerance'] * 10 and max(abs(nxt[g] - history[-1][g]) for g in groups) < kernel['residual_tolerance']:
            status, ticks, state = 'oscillating', i, nxt
            break
        history.append(state)
        history = history[-3:]
        state = nxt
    return dict(state=state, status=status, ticks=ticks, link_events=link_events, group_updates=group_updates,
                dense_link_events=len(links) * ticks, dense_group_updates=len(groups) * ticks, links=len(links), groups=len(groups), states=states)


def decision_outcome(result):
    """What the engine reads from a decision network: status and the side of the goal."""
    return [result['status'], result['state']['goal'] >= 0.5]


def pool_outcome(result, candidates, activation_threshold, mismatch_threshold):
    """What the engine reads from a pool network: the ordered eligible candidates (activation.py / expansion.py)."""
    stable = result['status'] in ('stable_decision', 'stable_ambiguous')
    eligible = []
    for i, c in enumerate(candidates):
        a = result['state']['c:%d' % i]
        if stable and a >= activation_threshold and c['mismatch'] <= mismatch_threshold:
            edges = list(c['binding']['edge_order'])
            eligible.append((-a, -len(edges), edges, c['circuit_id']))
    return [[e[2], e[3]] for e in sorted(eligible)]
