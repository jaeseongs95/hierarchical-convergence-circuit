"""R56 / EXP-102: goal-primed shortcuts against the R55 stage 1 kill criteria.

Design, predictions and kill criteria: experiments/exp-102-goal-priming/DESIGN.ko.md
"""
import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT)]
EXP = ROOT / 'experiments/exp-102-goal-priming'

from tools.r55_fabric import fabric as r55  # noqa: E402
from tools.r55_fabric.fabric import Rng  # noqa: E402
from tools.r55_fabric.world import make_tasks, make_world  # noqa: E402
from tools.r56_gated.gated import GoalStore, run  # noqa: E402

T95 = dict(zip(range(2, 31), [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.16, 2.145, 2.131, 2.12, 2.11, 2.101, 2.093, 2.086, 2.08, 2.074, 2.069, 2.064, 2.06, 2.056, 2.052, 2.048, 2.045]))  # two-sided 95% t quantile for n samples (n - 1 degrees of freedom)
SETS = ['seen', 'held', 'held_sub', 'held_comp', 'unrelated', 'false']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def one_seed(seed, spec):
    rng = Rng(seed)
    w = spec['world']
    world = make_world(rng, w['places'], w['degree'], w['open_permille'])
    tasks = make_tasks(rng, world, spec['tasks'])
    truth = tasks['truth']
    sets = dict(seen=sorted({p for t in tasks['train'] for p in t}), held=[(q['start'], q['goal']) for q in tasks['held']],
                held_sub=[(q['start'], q['goal']) for q in tasks['held'] if q['kind'] == 'sub'],
                held_comp=[(q['start'], q['goal']) for q in tasks['held'] if q['kind'] == 'comp'], unrelated=tasks['unrelated'], false=tasks['false'])
    trained_goals = {v for t in tasks['train'] for _, v in t}
    out = dict(seed=seed, set_sizes={k: len(v) for k, v in sets.items()},
               held_with_trained_goal=sum(1 for _, v in sets['held'] if v in trained_goals), systems={})

    def evaluate(store, mode, gate):
        cells = {}
        for name, queries in sets.items():
            events = correct = 0
            parts = {}
            for u, v in queries:
                answer, cost, _, _ = run(world, u, v, store, mode, gate)
                events += cost['total']
                correct += int(answer == truth(u, v))
                for k, c in cost.items():
                    if c:
                        parts[k] = parts.get(k, 0) + c
            cells[name] = dict(queries=len(queries), events=events, correct=correct, parts=parts)
        return cells

    out['systems']['B0_none'] = dict(final=evaluate(None, 'none', 'none'),
                                     training_tail_events=sum(run(world, u, v, None, 'none')[1]['total'] for u, v in tasks['stream'][-spec['tail_episodes']:]))
    known = set(tasks['stream'])
    b0 = out['systems']['B0_none']['final']
    memo = {}
    for name, queries in sets.items():
        events = sum(1 if q in known else run(world, q[0], q[1], None, 'none')[1]['total'] + 1 for q in queries)
        memo[name] = dict(queries=len(queries), events=events, correct=len(queries), parts={})
    out['systems']['B1_memo'] = dict(final=memo)
    r55_equal = True
    for name, cfg in spec['systems'].items():
        params = dict(spec['learning'], **cfg.get('params', {}))
        store = GoalStore(params, cfg.get('capacity', spec['capacity']), cfg.get('tag_capacity', spec['tag_capacity']))
        mode, gate = cfg['mode'], cfg['gate']
        reference = r55.Store(params, cfg.get('capacity', spec['capacity'])) if gate == 'none' else None
        curve, wrong = [], 0
        for u, v in tasks['stream']:
            answer, cost, trace, used = run(world, u, v, store, mode, gate)
            if reference is not None:
                a2, c2, t2, u2 = r55.run(world, u, v, reference, mode)
                r55_equal = r55_equal and a2 == answer and c2['total'] == cost['total'] and t2 == trace
                if a2 and truth(u, v):
                    reference.learn(t2)
            right = answer == truth(u, v)
            wrong += int(not right)
            if answer and right:
                store.learn_for(trace, v)
            elif answer:
                store.weaken(used)
            curve.append(cost['total'])
        items = list(store.items.values())
        out['systems'][name] = dict(final=evaluate(store, mode, gate), training_events=sum(curve), training_tail_events=sum(curve[-spec['tail_episodes']:]), training_wrong=wrong,
            store=dict(shortcuts=len(items), strong=sum(1 for sc in items if sc.s >= 0.5), conducting=sum(1 for sc in items if store.delay(sc) < sc.span),
                       goals_with_tags=sum(1 for g in store.tags if store.primed(g)), tags=sum(len(store.primed(g)) for g in store.tags),
                       nested=sum(1 for sc in items if sc.children)))
    out['ungated_equal_to_r55_run'] = r55_equal
    return out


def stats(values):
    n = len(values)
    mean = sum(values) / n
    sd = (sum((v - mean) ** 2 for v in values) / (n - 1)) ** 0.5
    half = T95[n] * sd / n ** 0.5
    return dict(n=n, mean=mean, sd=sd, ci95=[mean - half, mean + half])


def summarize(rows, spec):
    names = list(rows[0]['systems'])

    def per_query(row, system, s):
        cell = row['systems'][system]['final'][s]
        return cell['events'] / cell['queries'] if cell['queries'] else None

    def relative(system, s, against='B0_none'):
        usable = [r for r in rows if r['set_sizes'][s] > 0]
        return stats([(per_query(r, system, s) - per_query(r, against, s)) / per_query(r, against, s) for r in usable])
    table = {system: {s: dict(mean_events_per_query=sum(per_query(r, system, s) for r in rows if r['set_sizes'][s] > 0) / sum(1 for r in rows if r['set_sizes'][s] > 0),
                              relative_to_B0=relative(system, s)) for s in SETS} for system in names}
    accuracy = {system: {s: [sum(r['systems'][system]['final'][s]['correct'] for r in rows), sum(r['set_sizes'][s] for r in rows)] for s in SETS} for system in names}
    k = spec['kill']

    def kill(system):
        held, memo, unrelated = relative(system, 'held'), relative(system, 'held', 'B1_memo'), relative(system, 'unrelated')
        exact = all(a == b for a, b in accuracy[system].values()) and all(r['systems'][system]['training_wrong'] == 0 for r in rows)
        verdict = dict(K1=held['mean'] <= -k['k1_min_reduction'] and held['ci95'][1] < 0, K2=memo['mean'] <= -k['k1_min_reduction'] and memo['ci95'][1] < 0,
                       K3=not unrelated['ci95'][0] > k['k3_max_increase'], K4=exact)
        return dict(verdict=verdict, stage1='PASS' if all(verdict.values()) else 'FAIL', held=held, held_vs_memo=memo, unrelated=unrelated, false=relative(system, 'false'))
    kills = {system: kill(system) for system in spec['systems']}
    tail = {system: stats([(r['systems'][system]['training_tail_events'] - r['systems']['B0_none']['training_tail_events']) / r['systems']['B0_none']['training_tail_events'] for r in rows]) for system in spec['systems']}
    stores = {system: {key: sum(r['systems'][system]['store'][key] for r in rows) / len(rows) for key in rows[0]['systems'][system]['store']} for system in spec['systems']}
    paired = {}
    for s in SETS:
        usable = [r for r in rows if r['set_sizes'][s] > 0]
        paired[s] = stats([(per_query(r, spec['primary'], s) - per_query(r, 'fabric_ungated', s)) / per_query(r, 'fabric_ungated', s) for r in usable])
    return dict(seeds=len(rows), ungated_equal_to_r55_run=all(r['ungated_equal_to_r55_run'] for r in rows), table=table, accuracy=accuracy, kill=kills,
                stage1=kills[spec['primary']]['stage1'], training_tail_relative_to_B0=tail, stores=stores, primary_relative_to_ungated=paired,
                held_with_trained_goal=[sum(r['held_with_trained_goal'] for r in rows), sum(r['set_sizes']['held'] for r in rows)])


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--out', help='new output folder (must not exist)')
    a.add_argument('--group', choices=['calibration', 'evaluation', 'r55_evaluation'], required=True)
    a.add_argument('--spec', default=str(EXP / 'frozen_spec.json'))
    args = a.parse_args()
    require(sys.version_info >= (3, 12), 'Python 3.12 required')
    started = time.monotonic()
    spec = read(args.spec)
    if args.group != 'calibration':
        require(all(sha(ROOT / n) == h for n, h in read(EXP / 'input_manifest.json').items()), 'input SHA pins')
    rows = [one_seed(seed, spec) for seed in spec['seeds'][args.group]]
    summary = summarize(rows, spec)
    result = dict(schema='hcr-r56-goal-priming-analysis-v1', group=args.group, spec_sha256=sha(args.spec), rows=rows, summary=summary)
    result['rows_sha256'] = hashlib.sha256(canonical(rows).encode()).hexdigest()
    result['environment'] = dict(python=sys.version, platform=platform.platform(), machine=platform.machine())
    result['cost'] = dict(wall_seconds=time.monotonic() - started)
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        with (out / ('analysis-%s.json' % args.group)).open('x', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
    print(canonical(dict(group=args.group, stage1=summary['stage1'], kill=summary['kill'][spec['primary']]['verdict'], r55_equal=summary['ungated_equal_to_r55_run'],
                         rows_sha256=result['rows_sha256'], seconds=result['cost']['wall_seconds'])))


if __name__ == '__main__':
    main()
