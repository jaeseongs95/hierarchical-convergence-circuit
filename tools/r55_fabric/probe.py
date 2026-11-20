"""R55 / EXP-101: fabric stage 0 (instrument) and stage 1 (compression and transfer in a fixed world).

Design, predictions and kill criteria: experiments/exp-101-fabric-stage1/DESIGN.ko.md
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
EXP = ROOT / 'experiments/exp-101-fabric-stage1'

from tools.r55_fabric.fabric import Rng, Store, run  # noqa: E402
from tools.r55_fabric.world import bfs, make_tasks, make_world  # noqa: E402

T95 = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262, 20: 2.093, 30: 2.045}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def systems(spec, rng_latent, n):
    base = spec['learning']
    latent = [set(rng_latent.shuffle([v for v in range(n) if v != u])[:spec['latent_targets']]) for u in range(n)]
    table = dict(
        fabric=dict(mode='race', capacity=spec['capacity'], params=base),
        fabric_latent=dict(mode='race', capacity=spec['capacity'], params=base, latent=latent),
        B2_verify=dict(mode='verify', capacity=spec['capacity'], params=base),
        B2_verify_unlimited=dict(mode='verify', capacity=None, params=base),
        B3_habit=dict(mode='habit', capacity=spec['capacity'], params=base))
    for name, change in spec['sensitivity'].items():
        table['sens_' + name] = dict(mode='race', capacity=change.get('capacity', spec['capacity']), params=dict(base, **{k: v for k, v in change.items() if k != 'capacity'}))
    return table


def evaluate(world, queries, truth, store, mode, memo=None):
    total, correct, parts = 0, 0, {}
    for u, v in queries:
        if memo is not None and (u, v) in memo:
            answer, cost = memo[(u, v)], dict(total=1, memo=1)
        else:
            answer, cost, _, _ = run(world, u, v, store, mode)
            if memo is not None:
                cost = dict(cost, memo=1, total=cost['total'] + 1)
        total += cost['total']
        correct += int(answer == truth(u, v))
        for k, c in cost.items():
            parts[k] = parts.get(k, 0) + c
    return dict(queries=len(queries), events=total, correct=correct, parts=parts)


def one_seed(seed, spec):
    rng = Rng(seed)
    w = spec['world']
    world = make_world(rng, w['places'], w['degree'], w['open_permille'])
    tasks = make_tasks(rng, world, spec['tasks'])
    truth = tasks['truth']
    sets = dict(seen=sorted({p for t in tasks['train'] for p in t}), held=[(q['start'], q['goal']) for q in tasks['held']],
                held_sub=[(q['start'], q['goal']) for q in tasks['held'] if q['kind'] == 'sub'],
                held_comp=[(q['start'], q['goal']) for q in tasks['held'] if q['kind'] == 'comp'],
                unrelated=tasks['unrelated'], false=tasks['false'])
    # stage 0: the no-learning fabric answers every query of every set and of the stream like the reachability oracle
    stage0 = all(run(world, u, v, None, 'none')[0] == truth(u, v) for u, v in set(tasks['stream']) | {q for s in sets.values() for q in s})
    shortest = {name: sum(tasks['reach'][u][v] for u, v in qs if truth(u, v)) for name, qs in sets.items()}
    out = dict(seed=seed, stage0_answers_equal_oracle=stage0, routes=[len(r) - 1 for r in tasks['routes']], set_sizes={k: len(v) for k, v in sets.items()},
               shortest_path_sum=shortest, systems={})
    checkpoints = spec['checkpoints']
    base = {c: {name: evaluate(world, qs, truth, None, 'none') for name, qs in sets.items()} for c in checkpoints}
    tail = spec['tail_episodes']
    out['systems']['B0_none'] = dict(checkpoints=base, training_tail_events=sum(run(world, u, v, None, 'none')[1]['total'] for u, v in tasks['stream'][-tail:]))
    memo, memo_cp, t = {}, {}, 0
    for c in checkpoints:
        while t < c:
            u, v = tasks['stream'][t]
            memo[(u, v)] = truth(u, v)
            t += 1
        memo_cp[c] = {name: evaluate(world, qs, truth, None, 'none', memo=memo) for name, qs in sets.items()}
    out['systems']['B1_memo'] = dict(checkpoints=memo_cp)
    for name, cfg in systems(spec, Rng(seed ^ 0x5F5F5F5F), w['places']).items():
        store = Store(cfg['params'], cfg['capacity'], cfg.get('latent'))
        cps, curve, t, wrong_train = {}, [], 0, 0
        for c in checkpoints:
            while t < c:
                u, v = tasks['stream'][t]
                answer, cost, trace, used = run(world, u, v, store, cfg['mode'])
                right = answer == truth(u, v)
                wrong_train += int(not right)
                if answer and right:
                    store.learn(trace)
                elif answer and not right:
                    store.weaken(used)
                curve.append(cost['total'])
                t += 1
            cps[c] = {s: evaluate(world, qs, truth, store, cfg['mode']) for s, qs in sets.items()}
        items = list(store.items.values())
        out['systems'][name] = dict(checkpoints=cps, training_events=sum(curve), training_tail_events=sum(curve[-tail:]), training_wrong=wrong_train, writes=store.writes,
            store=dict(shortcuts=len(items), nested=sum(1 for sc in items if sc.children), strong=sum(1 for sc in items if sc.s >= 0.5),
                       delay_one=sum(1 for sc in items if store.delay(sc) == 1), span_sum=sum(sc.span for sc in items),
                       max_span=max((sc.span for sc in items), default=0), units_with_shortcuts=sum(1 for v in store.by_unit.values() if v)))
    return out


def stats(values):
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return dict(n=n, mean=mean, sd=None, ci95=None)
    sd = (sum((v - mean) ** 2 for v in values) / (n - 1)) ** 0.5
    half = T95[n] * sd / n ** 0.5
    return dict(n=n, mean=mean, sd=sd, ci95=[mean - half, mean + half])


def summarize(rows, spec):
    final = str(spec['checkpoints'][-1]) if isinstance(next(iter(rows[0]['systems']['B0_none']['checkpoints'])), str) else spec['checkpoints'][-1]
    names = list(rows[0]['systems'])
    sets = list(rows[0]['set_sizes'])

    def per_query(row, system, s, c=final):
        cell = row['systems'][system]['checkpoints'][c][s]
        return cell['events'] / cell['queries'] if cell['queries'] else None

    table, accuracy = {}, {}
    for system in names:
        table[system], accuracy[system] = {}, {}
        for s in sets:
            usable = [r for r in rows if r['set_sizes'][s] > 0]
            rel = [(per_query(r, system, s) - per_query(r, 'B0_none', s)) / per_query(r, 'B0_none', s) for r in usable]
            table[system][s] = dict(mean_events_per_query=sum(per_query(r, system, s) for r in usable) / len(usable) if usable else None,
                                    relative_to_B0=stats(rel) if len(usable) in T95 or len(usable) < 2 else dict(n=len(usable), mean=sum(rel) / len(rel), sd=None, ci95=None))
            accuracy[system][s] = [sum(r['systems'][system]['checkpoints'][final][s]['correct'] for r in rows), sum(r['set_sizes'][s] for r in rows)]
    usable = [r for r in rows if r['set_sizes']['held'] > 0]
    vs_memo = [(per_query(r, 'fabric', 'held') - per_query(r, 'B1_memo', 'held')) / per_query(r, 'B1_memo', 'held') for r in usable]
    curve = {system: {str(c): sum(per_query(r, system, 'held', c if not isinstance(final, str) else str(c)) for r in usable) / len(usable) for c in spec['checkpoints']} for system in ('fabric', 'B0_none', 'B2_verify', 'B3_habit')}
    k = spec['kill']
    f = table['fabric']
    K = dict(
        K1=dict(passed=f['held']['relative_to_B0']['ci95'] is not None and f['held']['relative_to_B0']['ci95'][1] < 0 and f['held']['relative_to_B0']['mean'] <= -k['k1_min_reduction'], held_relative_to_B0=f['held']['relative_to_B0']),
        K2=dict(passed=len(vs_memo) in T95 and stats(vs_memo)['ci95'][1] < 0 and stats(vs_memo)['mean'] <= -k['k1_min_reduction'], held_relative_to_B1=stats(vs_memo) if len(vs_memo) in T95 else None),
        K3=dict(passed=not (f['unrelated']['relative_to_B0']['ci95'] is not None and f['unrelated']['relative_to_B0']['ci95'][0] > k['k3_max_increase']), unrelated_relative_to_B0=f['unrelated']['relative_to_B0']),
        K4=dict(passed=all(a == b for a, b in accuracy['fabric'].values()) and all(r['systems']['fabric']['training_wrong'] == 0 for r in rows), accuracy=accuracy['fabric']))
    tail_rel = {system: stats([(r['systems'][system]['training_tail_events'] - r['systems']['B0_none']['training_tail_events']) / r['systems']['B0_none']['training_tail_events'] for r in rows]) for system in names if 'training_tail_events' in rows[0]['systems'][system] and len(rows) in T95}
    stores = {system: {key: sum(r['systems'][system]['store'][key] for r in rows) / len(rows) for key in rows[0]['systems'][system]['store']} for system in names if 'store' in rows[0]['systems'][system]}
    return dict(seeds=len(rows), stage0_all=all(r['stage0_answers_equal_oracle'] for r in rows), final_checkpoint=spec['checkpoints'][-1], table=table, accuracy=accuracy,
                held_curve=curve, training_tail_relative_to_B0=tail_rel, kill=K, stage1='PASS' if all(v['passed'] for v in K.values()) else 'FAIL', stores=stores,
                set_sizes_mean={s: sum(r['set_sizes'][s] for r in rows) / len(rows) for s in sets},
                shortest_path_per_true_query={s: (sum(r['shortest_path_sum'][s] for r in rows) / max(1, sum(r['set_sizes'][s] for r in rows))) for s in sets if s != 'false'})


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--out', help='new output folder (must not exist)')
    a.add_argument('--group', choices=['calibration', 'evaluation'], required=True)
    a.add_argument('--spec', default=str(EXP / 'frozen_spec.json'))
    args = a.parse_args()
    require(sys.version_info >= (3, 12), 'Python 3.12 required')
    started = time.monotonic()
    spec = read(args.spec)
    if args.group == 'evaluation':
        require(all(sha(ROOT / n) == h for n, h in read(EXP / 'input_manifest.json').items()), 'input SHA pins')
    rows = [one_seed(seed, spec) for seed in spec['seeds'][args.group]]
    summary = summarize(rows, spec)
    result = dict(schema='hcr-r55-fabric-stage1-analysis-v1', group=args.group, spec_sha256=sha(args.spec), rows=rows, summary=summary)
    result['rows_sha256'] = hashlib.sha256(canonical(rows).encode()).hexdigest()
    result['environment'] = dict(python=sys.version, platform=platform.platform(), machine=platform.machine())
    result['cost'] = dict(wall_seconds=time.monotonic() - started)
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=False)
        with (out / 'analysis.json').open('x', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
    print(canonical(dict(group=args.group, stage0=summary['stage0_all'], stage1=summary['stage1'], kill={k: v['passed'] for k, v in summary['kill'].items()},
                         rows_sha256=result['rows_sha256'], seconds=result['cost']['wall_seconds'])))


if __name__ == '__main__':
    main()
