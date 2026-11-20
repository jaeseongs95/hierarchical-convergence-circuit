"""Second-path check of the R55 / EXP-101 analysis.

Does not import the R55 probe.  On the host that runs it:

* regenerates every world and task set from the seeds and recomputes the no-learning (B0) and memo
  (B1) event sums of every evaluation set with a closed-form layer count, without the event simulator;
* re-runs the fabric (primary configuration) and the B2 / B3 baselines with a separately written
  training and evaluation loop and compares every checkpoint cell with the recording;
* recomputes the paired statistics, the kill criteria and the prediction verdicts with separate code.

All recorded row values are integers produced by integer arithmetic and basic float operations, so
they must be identical on every host (blocking).  Statistics are compared with tolerance 1e-9.
"""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT)]
EXP = ROOT / 'experiments/exp-101-fabric-stage1'

from tools.r55_fabric.fabric import Rng, Store, run  # noqa: E402
from tools.r55_fabric.world import bfs, make_tasks, make_world  # noqa: E402

T95 = {29: 2.048, 30: 2.045}
SETS = ['seen', 'held', 'held_sub', 'held_comp', 'unrelated', 'false']


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
    return mean, mean - half, mean + half


def main(evidence):
    failures = []

    def check(ok, message):
        if not ok and message not in failures:
            failures.append(message)

    analysis = read(evidence / 'analysis.json')
    spec = read(EXP / 'frozen_spec.json')
    out = dict(schema='hcr-r55-fabric-stage1-verification-v1', analysis_sha256=sha(evidence / 'analysis.json'), independent_auditor=False,
               host=dict(python=sys.version, platform=platform.platform(), machine=platform.machine()), recorded_host=analysis['environment'])
    check(analysis['spec_sha256'] == sha(EXP / 'frozen_spec.json') and analysis['group'] == 'evaluation', 'analysis bound to the frozen spec and the evaluation group')
    check(all(sha(ROOT / n) == h for n, h in read(EXP / 'input_manifest.json').items()), 'input pins')
    stage0 = read(evidence / 'stage0.json')
    check(stage0['status'] == 'PASS', 'recorded stage 0 status')
    check(stage0['engine']['equal'] + stage0['engine']['engine_undecided'] == stage0['engine']['checked'], 'stage 0 engine comparison: every decided input agrees')

    final = str(spec['checkpoints'][-1])
    cells = dict(checked=0, equal=0)
    closed = dict(checked=0, equal=0)
    w, base = spec['world'], spec['learning']
    modes = dict(fabric='race', B2_verify='verify', B3_habit='habit')
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
            b0 = sum(closed_form(world, u, v) for u, v in sets[s])
            b1 = sum(1 if (u, v) in known else closed_form(world, u, v) + 1 for u, v in sets[s])
            closed['checked'] += 2
            closed['equal'] += int(b0 == row['systems']['B0_none']['checkpoints'][final][s]['events'] and len(sets[s]) == row['set_sizes'][s])
            closed['equal'] += int(b1 == row['systems']['B1_memo']['checkpoints'][final][s]['events'])
        for name, mode in modes.items():
            store = Store(base, spec['capacity'])
            done = 0
            for c in spec['checkpoints']:
                for u, v in tasks['stream'][done:c]:
                    answer, _, trace, used = run(world, u, v, store, mode)
                    if answer and truth(u, v):
                        store.learn(trace)
                    elif answer:
                        store.weaken(used)
                done = c
                for s in SETS:
                    events = correct = 0
                    for u, v in sets[s]:
                        answer, cost, _, _ = run(world, u, v, store, mode)
                        events += cost['total']
                        correct += int(answer == truth(u, v))
                    recorded = row['systems'][name]['checkpoints'][str(c)][s]
                    cells['checked'] += 1
                    cells['equal'] += int(events == recorded['events'] and correct == recorded['correct'])
    out['closed_form_B0_B1_against_recording'] = closed
    out['fabric_B2_B3_cells_against_recording'] = cells
    check(closed['checked'] == closed['equal'], 'B0 and B1 event sums equal the closed-form count for every seed and set')
    check(cells['checked'] == cells['equal'] == 30 * 3 * 6 * 6, 'fabric, B2 and B3 checkpoint cells equal to the recording')

    rows = analysis['rows']

    def per_query(row, system, s):
        cell = row['systems'][system]['checkpoints'][final][s]
        return cell['events'] / cell['queries'] if cell['queries'] else None

    def relative(system, s, against='B0_none'):
        usable = [r for r in rows if r['set_sizes'][s] > 0]
        return interval([(per_query(r, system, s) - per_query(r, against, s)) / per_query(r, against, s) for r in usable])
    k = spec['kill']
    k1, k2, k3 = relative('fabric', 'held'), relative('fabric', 'held', 'B1_memo'), relative('fabric', 'unrelated')
    exact = all(r['systems']['fabric']['checkpoints'][final][s]['correct'] == r['set_sizes'][s] for r in rows for s in SETS) and all(r['systems']['fabric']['training_wrong'] == 0 for r in rows)
    kill = dict(K1=k1[0] <= -k['k1_min_reduction'] and k1[2] < 0, K2=k2[0] <= -k['k1_min_reduction'] and k2[2] < 0, K3=not k3[1] > k['k3_max_increase'], K4=exact)
    recorded_kill = {name: v['passed'] for name, v in analysis['summary']['kill'].items()}
    close = lambda a, b: abs(a - b) <= 1e-9
    rk = analysis['summary']['kill']
    check(kill == recorded_kill, 'kill criteria equal to the recording')
    check(close(k1[0], rk['K1']['held_relative_to_B0']['mean']) and close(k1[2], rk['K1']['held_relative_to_B0']['ci95'][1]) and close(k3[1], rk['K3']['unrelated_relative_to_B0']['ci95'][0]), 'K1 / K3 statistics equal to the recording within 1e-9')
    check(('PASS' if all(kill.values()) else 'FAIL') == analysis['summary']['stage1'], 'stage 1 status equal to the recording')

    false_rel, sub, comp = relative('fabric', 'false'), relative('fabric', 'held_sub'), relative('fabric', 'held_comp')
    sens = {}
    for name in spec['sensitivity']:
        a, b = relative('sens_' + name, 'held'), relative('sens_' + name, 'unrelated')
        sens[name] = dict(K1=a[0] <= -k['k1_min_reduction'] and a[2] < 0, K3=not b[1] > k['k3_max_increase'])
    nested = sum(r['systems']['fabric']['store']['nested'] for r in rows) / len(rows)
    predictions = dict(
        P1=stage0['status'] == 'PASS' and analysis['summary']['stage0_all'],
        P2=kill['K1'] and kill['K2'] and kill['K4'],
        P3=not kill['K3'],
        P4=false_rel[1] > 0.10,
        P5=comp[0] < sub[0],
        P6=relative('B3_habit', 'held_comp')[0] < comp[0] and relative('B2_verify', 'unrelated')[0] > k3[0],
        P7=nested >= 1,
        P8=all(v['K1'] == kill['K1'] and v['K3'] == kill['K3'] for v in sens.values()))
    out['kill'] = kill
    out['predictions'] = {name: 'supported' if v else 'falsified' for name, v in predictions.items()}
    latent_held, latent_unrelated = relative('fabric_latent', 'held'), relative('fabric_latent', 'unrelated')
    out['statistics'] = dict(fabric_held=k1, fabric_held_vs_memo=k2, fabric_unrelated=k3, fabric_false=false_rel, fabric_held_sub=sub, fabric_held_comp=comp,
                             sensitivity=sens, nested_mean=nested, fabric_latent_held=latent_held, fabric_latent_unrelated=latent_unrelated,
                             fabric_latent_kill=dict(K1=latent_held[0] <= -k['k1_min_reduction'] and latent_held[2] < 0, K3=not latent_unrelated[1] > k['k3_max_increase']))
    out['failures'] = failures
    out['status'] = 'PASS' if not failures else 'FAIL'
    return out


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('--evidence', default=str(ROOT / 'evidence/fabric-stage1-20261120-r55'))
    a.add_argument('--write', metavar='NAME', help='write the report to NAME inside the evidence folder (must not exist)')
    args = a.parse_args()
    result = main(Path(args.evidence))
    text = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n'
    if args.write:
        with (Path(args.evidence) / args.write).open('x', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print(text)
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
