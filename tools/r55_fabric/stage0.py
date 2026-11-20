"""R55 stage 0: instrument checks that do not depend on the evaluation seeds.

1. hand-made line world: learning, delay, and the shortcut-versus-veto race in all four modes;
2. no-learning event counts against a closed-form layer count on random worlds;
3. no-learning answers against the unchanged AdaptiveEngine (circuits off) on tiny worlds inside its bounds
   (reported, not blocking: the engine leaves some inputs undecided).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]

from tools.r55_fabric.fabric import Rng, Store, run  # noqa: E402
from tools.r55_fabric.world import bfs, make_world  # noqa: E402

PARAMS = dict(eta=0.25, decay=0.01, floor=0.01, weaken=0.2, delay='linear', tie='farthest', conduct='faster')


def line_checks():
    world = [[(1, True)], [(2, True)], [(3, True)], []]
    closed = [[(1, True)], [(2, True)], [(3, False)], []]
    first_closed = [[(1, False)], [(2, True)], [(3, True)], []]
    strong = Store(PARAMS, 4)
    for _ in range(8):
        strong.learn(run(world, 0, 3, strong, 'race')[2])
    weak = Store(PARAMS, 4)
    weak.learn(run(world, 0, 3, weak, 'race')[2])
    full = strong.by_pair[(0, 3)]
    return dict(
        strong_shortcut_has_delay_one=strong.delay(strong.items[full]) == 1 and strong.items[full].span == 3,
        strong_shortcut_sites=sorted(strong.primitive_sites(full)) == [(0, 0), (1, 0), (2, 0)],
        open_world_all_modes_true=all(run(world, 0, 3, strong, m)[0] for m in ('none', 'race', 'verify', 'habit')),
        deep_break_none_false=run(closed, 0, 3, strong, 'none')[0] is False,
        deep_break_verify_false=run(closed, 0, 3, strong, 'verify')[0] is False,
        deep_break_habit_true=run(closed, 0, 3, strong, 'habit')[0] is True,
        deep_break_strong_race_true=run(closed, 0, 3, strong, 'race')[0] is True,
        deep_break_weak_race_false=run(closed, 0, 3, weak, 'race')[0] is False,
        first_link_break_strong_race_false=run(first_closed, 0, 3, strong, 'race')[0] is False,
        weak_shortcut_does_not_conduct=run(world, 0, 3, weak, 'race')[1]['launch'] == 0 and len(weak.items) == 3,
        strong_store_launches_only_the_conducting_one=run(world, 0, 3, strong, 'race')[1]['launch'] == 1)


def closed_form(world, start, goal):
    dist, _ = bfs(world, start)
    limit = dist.get(goal)
    fired_before = [u for u, d in dist.items() if limit is None or d < limit]
    return 1 + sum(len(world[u]) for u in fired_before) + sum(1 for u in fired_before for v, is_open in world[u] if is_open)


def count_checks():
    checked = equal = 0
    for seed in range(5000, 5020):
        rng = Rng(seed)
        world = make_world(rng, 24, 3, 700)
        for _ in range(50):
            u, v = rng.below(24), rng.below(24)
            if u == v:
                continue
            answer, cost, _, _ = run(world, u, v, None, 'none')
            checked += 1
            equal += int(cost['total'] == closed_form(world, u, v) and answer == (v in bfs(world, u)[0]))
    return dict(checked=checked, equal=equal)


def engine_checks():
    from hcr.model import AdaptiveConfig, EdgeObservation, Mode, Observation
    from hcr.runtime import AdaptiveEngine
    cfg = AdaptiveConfig()
    checked = equal = undecided = undecided_false = 0
    for seed in range(6000, 6060):
        rng = Rng(seed)
        world = make_world(rng, 5, 1, 700)
        extra = rng.below(5)
        world[extra] = world[extra] + [((extra + 1 + rng.below(4)) % 5, rng.permille(700))]
        seen, edges = set(), []
        for u, links in enumerate(world):
            for v, is_open in links:
                if (u, v) not in seen:
                    seen.add((u, v))
                    edges.append((u, v, is_open))
        clean = [[] for _ in range(5)]
        for u, v, is_open in edges:
            clean[u].append((v, is_open))
        start, goal = 0, 1 + rng.below(4)
        obs = Observation('r55-s0-%d' % seed, 0, 'v%d' % start, 'v%d' % goal, tuple(EdgeObservation('e%d' % i, 'v%d' % u, 'v%d' % v, 1.0 if o else -1.0) for i, (u, v, o) in enumerate(edges)))
        decision = AdaptiveEngine(cfg, use_circuits=False, judgment_prior='route_only').infer(obs, Mode.FROZEN_EVAL)
        answer = run(clean, start, goal, None, 'none')[0]
        checked += 1
        undecided += int(decision.value is None)
        undecided_false += int(decision.value is None and answer is False)
        equal += int(decision.value is answer)
    return dict(checked=checked, equal=equal, engine_undecided=undecided, engine_undecided_where_fabric_false=undecided_false)


if __name__ == '__main__':
    out = dict(line=line_checks(), counts=count_checks(), engine=engine_checks())
    out['status'] = 'PASS' if all(out['line'].values()) and out['counts']['checked'] == out['counts']['equal'] else 'FAIL'
    print(json.dumps(out, indent=1, sort_keys=True))
    raise SystemExit(0 if out['status'] == 'PASS' else 1)
