"""Second-path check of the R56 / EXP-102 analysis.

Does not import the R56 probe.  On the host that runs it, for the evaluation seeds:

* regenerates worlds and tasks and recomputes B0 / B1 event sums with a closed-form layer count;
* re-runs five systems (ungated, primed, goal-match control, primed habit, primed verify) with a
  separately written training and evaluation loop and compares every final cell with the recording;
* checks that with an empty goal tag set the gated executor costs exactly the no-learning count;
* recomputes statistics, kill criteria and prediction verdicts with separate code (both seed groups).

Recorded row values are integers and must be identical on every host (blocking).
"""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT)]
EXP = ROOT / 'experiments/exp-102-goal-priming'

from tools.r55_fabric.fabric import Rng  # noqa: E402
from tools.r55_fabric.world import bfs, make_tasks, make_world  # noqa: E402
from tools.r56_gated.gated import GoalStore, run  # noqa: E402

T95 = dict(zip(range(2, 31), [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.16, 2.145, 2.131, 2.12, 2.11, 2.101, 2.093, 2.086, 2.08, 2.074, 2.069, 2.064, 2.06, 2.056, 2.052, 2.048, 2.045]))
SETS = ['seen', 'held', 'held_sub', 'held_comp', 'unrelated', 'false']
RERUN = ['fabric_ungated', 'fabric_primed', 'control_goal_match', 'B3_habit_primed', 'B2_verify_primed']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def closed_form(world, start, goal):
    dist, _ = bfs(world, start)
    limit = dist.get(goal)
    before = [u for u, d in dist.items() if limit is None or d < limit]
    return 1 + sum(len(world[u]) for u in before) + sum(1 for u in before for _, is_open in world[u] if is_open)


def interval(values):
    n = len(values)
    mean = sum(values) / n
    sd = (sum((v - mean) ** 2 for v in values) / (n - 1)) ** 0.5
    half = T95[n] * sd / n ** 0.5
    return [mean, mean - half, mean + half]


def judge(rows, spec):
    def per_query(row, system, s):
        cell = row['systems'][system]['final'][s]
        return cell['events'] / cell['queries']

    def relative(system, s, against='B0_none'):
        return interval([(per_query(r, system, s) - per_query(r, against, s)) / per_query(r, against, s) for r in rows if r['set_sizes'][s] > 0])
    k = spec['kill']

    def kill(system):
        held, memo, unrelated = relative(system, 'held'), relative(system, 'held', 'B1_memo'), relative(system, 'unrelated')
        exact = all(r['systems'][system]['final'][s]['correct'] == r['set_sizes'][s] for r in rows for s in SETS) and all(r['systems'][system]['training_wrong'] == 0 for r in rows)
        return dict(K1=held[0] <= -k['k1_min_reduction'] and held[2] < 0, K2=memo[0] <= -k['k1_min_reduction'] and memo[2] < 0, K3=not unrelated[1] > k['k3_max_increase'], K4=exact)
    primary = spec['primary']
    kills = {system: kill(system) for system in spec['systems']}
    held = {system: relative(system, 'held') for system in spec['systems']}
    paired = relative(primary, 'held', 'fabric_ungated')
    trained = [sum(r['held_with_trained_goal'] for r in rows), sum(r['set_sizes']['held'] for r in rows)]
    predictions = dict(
        P1=all(r['ungated_equal_to_r55_run'] for r in rows),
        P2=all(kills[primary].values()),
        P3=relative(primary, 'false')[2] < 0.01,
        P4=paired[2] < 0,
        P5=all(kills['control_goal_match'].values()) and abs(held['control_goal_match'][0] - held[primary][0]) < 0.10,
        P6=held['B3_habit_primed'][0] < held[primary][0] and held['B2_verify_primed'][0] < held[primary][0],
        P7=all(all(kills[s].values()) for s in spec['systems'] if s.startswith('sens_')),
        P8=trained[0] / trained[1] >= 0.8)
    return dict(kill=kills, predictions={n: 'supported' if v else 'falsified' for n, v in predictions.items()}, held=held,
                unrelated={system: relative(system, 'unrelated') for system in spec['systems']}, primary_false=relative(primary, 'false'),
                primary_vs_ungated=dict(held=paired, held_sub=relative(primary, 'held_sub', 'fabric_ungated'), held_comp=relative(primary, 'held_comp', 'fabric_ungated'),
                                        unrelated=relative(primary, 'unrelated', 'fabric_ungated')),
                held_comp={system: relative(system, 'held_comp') for system in spec['systems']}, held_with_trained_goal=trained,
                verify_minus_habit_primed_held=interval([(per_query(r, 'B2_verify_primed', 'held') - per_query(r, 'B3_habit_primed', 'held')) / per_query(r, 'B0_none', 'held') for r in rows]))


def main(evidence):
    failures = []

    def check(ok, message):
        if not ok and message not in failures:
            failures.append(message)

    spec = read(EXP / 'frozen_spec.json')
    analysis = read(evidence / 'analysis-evaluation.json')
    other = read(evidence / 'analysis-r55_evaluation.json')
    out = dict(schema='hcr-r56-goal-priming-verification-v1', analysis_sha256={n: sha(evidence / n) for n in ('analysis-evaluation.json', 'analysis-r55_evaluation.json')},
               independent_auditor=False, host=dict(python=sys.version, platform=platform.platform(), machine=platform.machine()), recorded_host=analysis['environment'])
    check(analysis['spec_sha256'] == other['spec_sha256'] == sha(EXP / 'frozen_spec.json') and analysis['group'] == 'evaluation' and other['group'] == 'r55_evaluation', 'analyses bound to the frozen spec')
    check(all(sha(ROOT / n) == h for n, h in read(EXP / 'input_manifest.json').items()), 'input pins')
    check([r['seed'] for r in analysis['rows']] == spec['seeds']['evaluation'] and not set(spec['seeds']['evaluation']) & set(spec['seeds']['r55_evaluation']) and not set(spec['seeds']['evaluation']) & set(spec['seeds']['calibration']), 'evaluation seeds are new')

    closed = dict(checked=0, equal=0)
    cells = dict(checked=0, equal=0)
    empty = dict(checked=0, equal=0)
    w = spec['world']
    for row in analysis['rows']:
        rng = Rng(row['seed'])
        world = make_world(rng, w['places'], w['degree'], w['open_permille'])
        tasks = make_tasks(rng, world, spec['tasks'])
        truth = tasks['truth']
        sets = dict(seen=sorted({p for t in tasks['train'] for p in t}), held=[(q['start'], q['goal']) for q in tasks['held']],
                    held_sub=[(q['start'], q['goal']) for q in tasks['held'] if q['kind'] == 'sub'],
                    held_comp=[(q['start'], q['goal']) for q in tasks['held'] if q['kind'] == 'comp'], unrelated=tasks['unrelated'], false=tasks['false'])
        known = set(tasks['stream'])
        for s in SETS:
            closed['checked'] += 2
            closed['equal'] += int(sum(closed_form(world, u, v) for u, v in sets[s]) == row['systems']['B0_none']['final'][s]['events'])
            closed['equal'] += int(sum(1 if q in known else closed_form(world, *q) + 1 for q in sets[s]) == row['systems']['B1_memo']['final'][s]['events'])
        for name in RERUN:
            cfg = spec['systems'][name]
            store = GoalStore(dict(spec['learning'], **cfg.get('params', {})), cfg.get('capacity', spec['capacity']), cfg.get('tag_capacity', spec['tag_capacity']))
            for u, v in tasks['stream']:
                answer, _, trace, used = run(world, u, v, store, cfg['mode'], cfg['gate'])
                if answer and truth(u, v):
                    store.learn_for(trace, v)
                elif answer:
                    store.weaken(used)
            for s in SETS:
                events = correct = 0
                for u, v in sets[s]:
                    answer, cost, _, _ = run(world, u, v, store, cfg['mode'], cfg['gate'])
                    events += cost['total']
                    correct += int(answer == truth(u, v))
                recorded = row['systems'][name]['final'][s]
                cells['checked'] += 1
                cells['equal'] += int(events == recorded['events'] and correct == recorded['correct'])
            if name == 'fabric_primed':
                for u, v in sets['unrelated'] + sets['false']:
                    if not store.primed(v):
                        empty['checked'] += 1
                        empty['equal'] += int(run(world, u, v, store, 'race', 'primed')[1]['total'] == closed_form(world, u, v))
    out['closed_form_B0_B1_against_recording'] = closed
    out['rerun_cells_against_recording'] = cells
    out['unprimed_goal_costs_exactly_no_learning'] = empty
    check(closed['checked'] == closed['equal'], 'B0 and B1 event sums equal the closed-form count')
    check(cells['checked'] == cells['equal'] == 30 * len(RERUN) * 6, 'five re-run systems equal the recording in every final cell')
    check(empty['checked'] == empty['equal'] and empty['checked'] > 0, 'a query whose goal primes nothing costs exactly the no-learning count')

    local = judge(analysis['rows'], spec)
    secondary = judge(other['rows'], spec)
    recorded = {system: v['verdict'] for system, v in analysis['summary']['kill'].items()}
    check(local['kill'] == recorded, 'kill verdicts equal to the recording (evaluation seeds)')
    check(secondary['kill'] == {system: v['verdict'] for system, v in other['summary']['kill'].items()}, 'kill verdicts equal to the recording (R55 seeds)')
    rk = analysis['summary']['kill'][spec['primary']]
    check(abs(local['held'][spec['primary']][0] - rk['held']['mean']) <= 1e-9 and abs(local['unrelated'][spec['primary']][1] - rk['unrelated']['ci95'][0]) <= 1e-9, 'primary statistics equal to the recording within 1e-9')
    check(('PASS' if all(local['kill'][spec['primary']].values()) else 'FAIL') == analysis['summary']['stage1'], 'stage 1 status equal to the recording')
    out['evaluation'] = local
    out['r55_seeds'] = dict(kill=secondary['kill'], predictions=secondary['predictions'], held=secondary['held'], primary_vs_ungated=secondary['primary_vs_ungated'])
    out['failures'] = failures
    out['status'] = 'PASS' if not failures else 'FAIL'
    return out


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('--evidence', default=str(ROOT / 'evidence/goal-priming-20261120-r56'))
    a.add_argument('--write', metavar='NAME', help='write the report to NAME inside the evidence folder (must not exist)')
    args = a.parse_args()
    result = main(Path(args.evidence))
    text = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n'
    if args.write:
        with (Path(args.evidence) / args.write).open('x', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print(text)
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
