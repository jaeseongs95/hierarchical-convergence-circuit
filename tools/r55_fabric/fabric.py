"""R55 event-driven fabric: places, primitive links, learned shortcuts, veto collaterals.

Pure Python, integers and basic float arithmetic only (no exp/log), own PRNG, no engine imports.
Specification: experiments/exp-100-fabric-direction/DIRECTION.ko.md section 3 and
experiments/exp-101-fabric-stage1/DESIGN.ko.md section 3.

Modes
  none    no shortcuts are used (baseline B0)
  race    shortcut delivery after delay d(s); a veto that arrives no later cancels it (the fabric)
  verify  every use probes all primitive links under the shortcut first, then delivers at +1 (B2)
  habit   delivery at +1, no veto, strength ignored (B3)
"""
from math import ceil

MASK = (1 << 64) - 1


class Rng:
    """splitmix64; identical on every host and Python version."""

    def __init__(self, seed):
        self.state = seed & MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return z ^ (z >> 31)

    def below(self, n):
        return self.next() % n

    def permille(self, p):
        return self.below(1000) < p

    def shuffle(self, items):
        items = list(items)
        for i in range(len(items) - 1, 0, -1):
            j = self.below(i + 1)
            items[i], items[j] = items[j], items[i]
        return items

    def weighted(self, weights):
        r = self.below(sum(weights))
        for i, w in enumerate(weights):
            if r < w:
                return i
            r -= w


class Shortcut:
    __slots__ = ('sid', 'u', 'v', 's', 'span', 'sites', 'children')

    def __init__(self, sid, u, v, s, span, sites, children):
        self.sid, self.u, self.v, self.s, self.span, self.sites, self.children = sid, u, v, s, span, sites, children


class Store:
    """Learned shortcuts of one learner.  capacity None = unlimited; latent None = any pair allowed."""

    def __init__(self, params, capacity, latent=None):
        self.p, self.capacity, self.latent = params, capacity, latent
        self.items, self.by_unit, self.by_pair, self.next_sid = {}, {}, {}, 0
        self.writes = 0

    def delay(self, sc):
        if self.p['delay'] == 'step':
            return 1 if sc.s >= 0.5 else sc.span
        return max(1, ceil(sc.span * (1 - sc.s)))

    def primitive_sites(self, sid, seen=None):
        """All primitive (unit, link index) pairs under a shortcut, through nested shortcuts that still exist."""
        seen = set() if seen is None else seen
        sc = self.items[sid]
        out = set(sc.sites)
        for child in sc.children:
            if child in self.items and child not in seen:
                seen.add(child)
                out |= self.primitive_sites(child, seen)
        return out

    def index(self):
        sites, parents = {}, {}
        for sc in self.items.values():
            for site in sc.sites:
                sites.setdefault(site, []).append(sc.sid)
            for child in sc.children:
                parents.setdefault(child, []).append(sc.sid)
        return sites, parents

    def _remove(self, sid):
        sc = self.items.pop(sid)
        self.by_unit[sc.u].remove(sid)
        del self.by_pair[(sc.u, sc.v)]

    def learn(self, trace):
        """trace: hops [(a, b, kind, ref)] from start to goal; kind 'p' (ref = link index) or 's' (ref = sid)."""
        eta, touched = self.p['eta'], set()
        hop = []
        for a, b, kind, ref in trace:
            if kind == 'p':
                hop.append((1, {(a, ref)}, set()))
            else:
                sc = self.items.get(ref)
                hop.append((sc.span if sc else 1, set(), {ref} if sc else set()))
                if sc and ref not in touched:
                    sc.s += eta * (1 - sc.s)
                    touched.add(ref)
                    self.writes += 1
        units = [trace[0][0]] + [h[1] for h in trace]
        order = range(len(units) - 1, 1, -1) if self.p['tie'] == 'farthest' else range(2, len(units))
        for i in range(len(units) - 2):
            for j in order:
                if j - i < 2:
                    continue
                u, v = units[i], units[j]
                sid = self.by_pair.get((u, v))
                if sid is not None:
                    if sid not in touched:
                        self.items[sid].s += eta * (1 - self.items[sid].s)
                        touched.add(sid)
                        self.writes += 1
                    continue
                if self.latent is not None and v not in self.latent[u]:
                    continue
                span, sites, children = 0, set(), set()
                for h in hop[i:j]:
                    span += h[0]
                    sites |= h[1]
                    children |= h[2]
                sid = self.next_sid
                self.next_sid += 1
                self.items[sid] = Shortcut(sid, u, v, eta, span, sites, children)
                self.by_unit.setdefault(u, []).append(sid)
                self.by_pair[(u, v)] = sid
                touched.add(sid)
                self.writes += 1
        for sid in [s for s in self.items if s not in touched]:
            sc = self.items[sid]
            sc.s *= 1 - self.p['decay']
            if sc.s < self.p['floor']:
                self._remove(sid)
        if self.capacity is not None:
            for u in list(self.by_unit):
                ranked = sorted(self.by_unit[u], key=lambda s: (-self.items[s].s, s))
                for sid in ranked[self.capacity:]:
                    self._remove(sid)

    def weaken(self, sids):
        for sid in sids:
            if sid in self.items:
                self.items[sid].s *= self.p['weaken']
                self.writes += 1


def run(world, start, goal, store, mode):
    """One episode.  world: list per unit of [(target, open)].  Returns answer, event counts, trace, used shortcut ids."""
    cost = dict(inject=1, probe=0, delivery=0, launch=0, short_delivery=0, veto=0, verify=0)
    use = store is not None and mode != 'none'
    sites, parents = store.index() if use and mode == 'race' else ({}, {})
    fired, parent, vetoed = {}, {}, {}
    queue = {0: [(start, 'i', None, None)]}
    late_veto = []

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
