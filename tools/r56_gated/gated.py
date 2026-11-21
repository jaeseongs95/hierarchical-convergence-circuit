"""R56 goal-primed fabric: a shortcut conducts only if the goal of the current query primed it.

Extends tools/r55_fabric/fabric.py without changing it.

* GoalStore keeps, per goal place, a bounded set of tags: the shortcuts that were created or
  strengthened in a correct episode that had this goal.
* run() is the R55 episode loop with two gate options:
    'none'   R55 behaviour (bit-identical event counts; checked in stage 0)
    'primed' at time 0 the goal sends one priming event to each tagged shortcut that still exists;
             only primed shortcuts may conduct
    'match'  control without learning of tags: a shortcut may conduct only if its target is the goal
             (the goal identity is assumed to be known everywhere for free)
"""
from tools.r55_fabric.fabric import Store


class GoalStore(Store):
    def __init__(self, params, capacity, tag_capacity, latent=None):
        super().__init__(params, capacity, latent)
        self.tag_capacity, self.tags = tag_capacity, {}

    def learn_for(self, trace, goal):
        before = {sid: sc.s for sid, sc in self.items.items()}
        self.learn(trace)
        touched = {sid for sid, sc in self.items.items() if sid not in before or sc.s > before[sid]}
        tags = {sid for sid in self.tags.get(goal, set()) | touched if sid in self.items}
        ranked = sorted(tags, key=lambda sid: (-self.items[sid].s, sid))
        self.tags[goal] = set(ranked[:self.tag_capacity])

    def primed(self, goal):
        return {sid for sid in self.tags.get(goal, ()) if sid in self.items}


def run(world, start, goal, store, mode, gate='none'):
    cost = dict(inject=1, probe=0, delivery=0, launch=0, short_delivery=0, veto=0, verify=0, prime=0)
    use = store is not None and mode != 'none'
    sites, parents = store.index() if use and mode == 'race' else ({}, {})
    primed = store.primed(goal) if use and gate == 'primed' else None
    if primed is not None:
        cost['prime'] = len(primed)
    fired, parent, vetoed = {}, {}, {}
    queue = {0: [(start, 'i', None, None)]}

    def veto(sid, at):
        cost['veto'] += 1
        if sid not in vetoed or at < vetoed[sid]:
            vetoed[sid] = at
        for up in parents.get(sid, ()):
            veto(up, at)

    while queue:
        t = min(queue)
        events = queue.pop(t)
        new = []
        for target, kind, src, ref in [e for e in events if e[1] != 's'] + [e for e in events if e[1] == 's']:
            if kind == 's':
                if ref in vetoed and vetoed[ref] <= t:
                    continue
                cost['short_delivery'] += 1
            elif kind == 'p':
                cost['delivery'] += 1
            if target not in fired:
                fired[target] = t
                parent[target] = (src, kind, ref)
                new.append(target)
        if goal in fired:
            break
        for u in new:
            for idx, (v, is_open) in enumerate(world[u]):
                cost['probe'] += 1
                if is_open:
                    queue.setdefault(t + 1, []).append((v, 'p', u, idx))
                else:
                    for sid in sites.get((u, idx), ()):
                        veto(sid, t + 1)
            if use:
                for sid in store.by_unit.get(u, ()):
                    sc = store.items[sid]
                    if store.p['conduct'] != 'always' and store.delay(sc) >= sc.span:
                        continue
                    if (primed is not None and sid not in primed) or (gate == 'match' and sc.v != goal):
                        continue
                    if mode == 'verify':
                        under = store.primitive_sites(sid)
                        cost['verify'] += len(under)
                        if all(world[a][idx][1] for a, idx in under):
                            queue.setdefault(t + 1, []).append((sc.v, 's', u, sid))
                    else:
                        cost['launch'] += 1
                        queue.setdefault(t + (1 if mode == 'habit' else store.delay(sc)), []).append((sc.v, 's', u, sid))
    answer = goal in fired
    trace, used = [], []
    if answer:
        node = goal
        while node != start:
            src, kind, ref = parent[node]
            trace.append((src, node, kind, ref))
            if kind == 's':
                used.append(ref)
            node = src
        trace.reverse()
    cost['total'] = sum(cost.values())
    return answer, cost, trace, used
