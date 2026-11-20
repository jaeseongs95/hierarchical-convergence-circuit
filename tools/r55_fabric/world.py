"""R55 world and query generation, reachability oracle.  Deterministic given a seed."""
from tools.r55_fabric.fabric import Rng


def make_world(rng, n, degree, open_permille):
    world = []
    for u in range(n):
        targets = rng.shuffle([v for v in range(n) if v != u])[:degree]
        world.append([(v, rng.permille(open_permille)) for v in targets])
    return world


def bfs(world, start):
    """Distances and first-arrival parents under the fabric's own tie order (unit firing order, then link index)."""
    dist, parent, layer = {start: 0}, {}, [start]
    while layer:
        nxt = []
        for u in layer:
            for v, is_open in world[u]:
                if is_open and v not in dist:
                    dist[v] = dist[u] + 1
                    parent[v] = u
                    nxt.append(v)
        layer = nxt
    return dist, parent


def make_tasks(rng, world, spec):
    n = len(world)
    routes = []
    attempts = 0
    while len(routes) < spec['routes'] and attempts < 1000:
        attempts += 1
        start = rng.below(n)
        dist, parent = bfs(world, start)
        far = [v for v, d in dist.items() if d >= spec['route_min']]
        if not far:
            continue
        deepest = min(max(dist[v] for v in far), spec['route_max'])
        end = rng.shuffle(sorted(v for v in far if dist[v] == deepest))[0]
        path = [end]
        while path[-1] != start:
            path.append(parent[path[-1]])
        path.reverse()
        if path not in routes:
            routes.append(path)
    on_route = {v for r in routes for v in r}
    train, held = [], []
    seen = set()
    for r, path in enumerate(routes):
        pairs = [(i, j) for i in range(len(path)) for j in range(i + 2, len(path)) if (path[i], path[j]) not in seen]
        seen |= {(path[i], path[j]) for i, j in pairs}
        pairs = rng.shuffle(pairs)
        cut = (len(pairs) + 1) // 2
        tr = pairs[:cut]
        train.append([(path[i], path[j]) for i, j in tr])
        for i, j in pairs[cut:]:
            kind = 'sub' if any(a <= i and j <= b for a, b in tr) else 'comp'
            held.append(dict(start=path[i], goal=path[j], kind=kind, route=r))
    reserved = {(q['start'], q['goal']) for q in held} | {p for t in train for p in t}
    off = [v for v in range(n) if v not in on_route]
    reach = {u: bfs(world, u)[0] for u in range(n)}
    far_true = rng.shuffle([(u, v) for u in off for v in off if v in reach[u] and reach[u][v] >= 2])
    false_all = rng.shuffle([(u, v) for u in range(n) for v in range(n) if u != v and v not in reach[u] and (u, v) not in reserved])
    unrelated = far_true[:spec['eval_unrelated']]
    false_set = false_all[:spec['eval_false']]
    reserved |= set(unrelated) | set(false_set)
    stream = []
    weights = [1000 // (r + 1) if train[r] else 0 for r in range(len(routes))]
    for _ in range(spec['episodes']):
        if rng.permille(spec['background_permille']) or not any(weights):
            while True:
                u, v = rng.below(n), rng.below(n)
                if u != v and (u, v) not in reserved:
                    break
            stream.append((u, v))
        else:
            r = rng.weighted(weights)
            stream.append(train[r][rng.below(len(train[r]))])
    truth = lambda u, v: v in reach[u]
    return dict(routes=routes, train=train, held=held, unrelated=unrelated, false=false_set, stream=stream, truth=truth, reach=reach)
