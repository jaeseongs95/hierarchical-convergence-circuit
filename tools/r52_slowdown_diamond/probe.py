"""R52 / EXP-98: slowdown versus input rules on a two-route (diamond) task.

Research harness around the unchanged AdaptiveEngine.  Design, predictions and decision rules:
experiments/exp-98-slowdown-diamond/DESIGN.ko.md
"""
import argparse
import copy
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
EXP = ROOT / 'experiments/exp-98-slowdown-diamond'

from tools.r51_slowdown_signal.core import auc, target_type  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def train(cfg, spec, episodes=None):
    from hcr.model import Feedback, Mode
    from hcr.runtime import AdaptiveEngine
    from hcr.tasks.toy_world import chain
    t = spec['training']
    engine = AdaptiveEngine(cfg, judgment_prior=t['judgment_prior'])
    snapshots = {}
    for i in range(1, (episodes or t['episodes']) + 1):
        obs = chain('r50-train-%02d' % i, (True, True), scores=tuple(t['scores']), prefix='t%02d' % i).observation
        decision = engine.infer(obs, Mode(t['mode']))
        engine.feedback(Feedback('r50-fb-train-%02d' % i, decision.id, obs.digest, decision.value is True, decision.proof.under_assumptions_valid))
        if i in t['snapshots']:
            snapshots[i] = copy.deepcopy(engine.memory.document())
    return snapshots


def diamond(spec, identity, scores):
    from hcr.model import EdgeObservation, Observation
    d = spec['diamond']
    edges = tuple(EdgeObservation('qe%d' % i, s, t, score) for i, ((s, t), score) in enumerate(zip(d['edges'], scores, strict=True)))
    return Observation(identity, 0, d['vertices'][0], d['vertices'][-1], edges)


def evaluate(cfg, spec, document, scores, use_circuits, identity):
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Mode
    from hcr.runtime import AdaptiveEngine
    engine = AdaptiveEngine(cfg, AdaptiveMemory.from_document(copy.deepcopy(document), cfg), use_circuits=use_circuits, judgment_prior=spec['policy'])
    decision = engine.infer(diamond(spec, identity, scores), Mode.FROZEN_EVAL)
    kinds, ticks, applied = {}, dict(pool=0, decision=0), []
    for r in engine.trace.records:
        p = r['payload']
        if r['event'] == 'r02_network':
            kinds[p['network_id']] = p['kind']
        elif r['event'] == 'r02_settled':
            ticks[kinds[p['network_id']]] += p['convergence']['ticks']
        elif r['event'] == 'r02_expansion' and p['candidate']['source'] == 'circuit':
            applied.append(list(p['candidate']['edges']))
    require(ticks['pool'] + ticks['decision'] == decision.cost['kernel_ticks'], 'per-network ticks add up to the cost counter')
    require(bool(applied) == bool(decision.circuit_ids), 'applied circuit spans agree with decision.circuit_ids')
    goal = dict(decision.state).get('goal')
    row = dict(value=decision.value, status=decision.convergence.status.value, selected=bool(applied), applied=applied, goal=goal,
               expanded_paths=[list(p) for p in decision.expanded_paths], expansions=decision.cost['expansions'], pool_calls=decision.cost['pool_calls'],
               ticks_pool=ticks['pool'], ticks_decision=ticks['decision'], ticks_total=decision.cost['kernel_ticks'])
    if use_circuits and applied:
        routes = spec['diamond']['routes']
        row['signals'] = dict(ticks_total=row['ticks_total'], ticks_pool=row['ticks_pool'], ticks_decision=row['ticks_decision'],
                              simple_any=-min(scores), selected_route=-min(scores[i] for span in applied for i in span),
                              structure_aware=-max(min(scores[i] for i in route) for route in routes), goal_margin=-abs(2 * goal - 1))
    return row


def metrics(rows, off, thresholds, signals):
    targets = [r for r in rows if r['target']]
    others = [r for r in rows if not r['target']]
    out = {}
    for s in signals:
        block = dict(auc=auc([r['signals'][s] for r in targets], [r['signals'][s] for r in others]))
        for label, table in thresholds.items():
            if table.get(s) is None:
                block[label] = None
                continue
            flagged = [r for r in rows if r['signals'][s] >= table[s]]
            block[label] = dict(threshold=table[s], flagged=len(flagged), recall=len([r for r in flagged if r['target']]) / len(targets) if targets else None,
                                reuse_preserved=1 - len([r for r in flagged if not r['target']]) / len(others) if others else None,
                                extra_off_ticks=sum(off[r['key']]['ticks_total'] for r in flagged), extra_off_expansions=sum(off[r['key']]['expansions'] for r in flagged))
        out[s] = block
    types = {}
    for r in targets:
        types[r['target']] = types.get(r['target'], 0) + 1
    return dict(applicable=len(rows), targets=len(targets), target_types=types, non_targets=len(others), signals=out)


def verdict(ok):
    return 'supported' if ok else 'falsified'


def run(out, smoke):
    from hcr.model import AdaptiveConfig
    from hcr.tasks.toy_world import World

    def forbidden(*a, **k):
        raise ValueError('R52 world measurement forbidden')
    World.measure = forbidden
    started, cpu0 = time.monotonic(), time.process_time()
    spec = read(EXP / 'frozen_spec.json')
    require(all(sha(ROOT / n) == h for n, h in read(EXP / 'input_manifest.json').items()), 'input SHA pins')
    cfg = AdaptiveConfig()
    if smoke:
        snap = train(cfg, dict(spec, training=dict(spec['training'], snapshots=[3])), episodes=3)
        print(canonical(dict(smoke=True, strength=snap[3]['circuits'][0]['strength'], circuits=len(snap[3]['circuits']))))
        return
    snapshots = train(cfg, spec)
    r51 = read(ROOT / 'evidence/slowdown-signal-20261120-r51/analysis.json')['memories']
    require(all(hashlib.sha256(canonical(snapshots[n]).encode()).hexdigest() == r51['n%d' % n]['document_sha256'] for n in snapshots), 'memories are bit-identical to the R51 documents')

    d = spec['diamond']
    grid = [(a, b) for a in d['second_edge_tenths'] for b in d['second_edge_tenths']]
    scores_of = lambda a, b: (d['fixed_first_edges'], a / 10, d['fixed_first_edges'], b / 10)
    off = {}
    for a, b in grid:
        off[(a, b)] = evaluate(cfg, spec, snapshots[3], scores_of(a, b), False, 'r52-off-%+03d-%+03d' % (a, b))
    rows = []
    for n in spec['calibration_memories'] + spec['test_memories']:
        for a, b in grid:
            r = evaluate(cfg, spec, snapshots[n], scores_of(a, b), True, 'r52-on-n%d-%+03d-%+03d' % (n, a, b))
            r.update(memory='n%d' % n, role='calibration' if n in spec['calibration_memories'] else 'test', a1_tenths=a, b1_tenths=b, key=[a, b])
            r['target'] = target_type(r['value'], off[(a, b)]['value']) if r['selected'] else None
            rows.append(r)
    require(len(rows) == spec['expected_counts']['on'] and len(off) == spec['expected_counts']['off'], 'declared evaluation counts')
    off_by_key = {(a, b): v for (a, b), v in off.items()}
    for r in rows:
        r['key'] = tuple(r['key'])
    signals = spec['signals']
    applicable = lambda role: [r for r in rows if r['role'] == role and r['selected']]
    cal, test = applicable('calibration'), applicable('test')
    cal_targets = [r for r in cal if r['target']]
    thresholds = dict(carried=dict(spec['carried_thresholds']), recalibrated={s: (min(r['signals'][s] for r in cal_targets) if cal_targets else None) for s in signals})
    summary = dict(thresholds=thresholds, calibration=metrics(cal, off_by_key, thresholds, signals), test=metrics(test, off_by_key, thresholds, signals),
                   test_by_memory={'n%d' % n: metrics([r for r in test if r['memory'] == 'n%d' % n], off_by_key, thresholds, signals) for n in spec['test_memories']})
    all_test = [r for r in rows if r['role'] == 'test']
    cost = dict(always_on=dict(ticks=sum(r['ticks_total'] for r in all_test), expansions=sum(r['expansions'] for r in all_test)),
                always_off=dict(ticks=sum(off[r['key']]['ticks_total'] for r in all_test), expansions=sum(off[r['key']]['expansions'] for r in all_test)))
    for s in signals:
        m = summary['test']['signals'][s]['recalibrated']
        if m:
            cost['gate_' + s] = dict(ticks=cost['always_on']['ticks'] + m['extra_off_ticks'], expansions=cost['always_on']['expansions'] + m['extra_off_expansions'])
    summary['cost_test_cells_recalibrated'] = cost

    T = summary['test']['signals']
    A = lambda s: T[s]['auc']
    primary = spec['primary_signal']
    P = {}
    sa = T['simple_any']['carried']
    P['P1'] = dict(verdict=verdict(sa['recall'] == 1.0 and sa['reuse_preserved'] < 0.7), recall=sa['recall'], reuse_preserved=sa['reuse_preserved'])
    P['P2'] = dict(verdict=verdict(A(primary) is not None and A(primary) >= 0.80), auc=A(primary))
    P['P3'] = dict(verdict=verdict(A(primary) - A('simple_any') >= 0.05), difference=A(primary) - A('simple_any'))
    P['P4'] = dict(verdict=verdict(A('structure_aware') >= A(primary)), structure_aware=A('structure_aware'), primary=A(primary))
    tc = T[primary]['carried']
    P['P5'] = dict(verdict=verdict(tc['recall'] < 0.9 or tc['reuse_preserved'] < 0.5), recall=tc['recall'], reuse_preserved=tc['reuse_preserved'])
    P['P6'] = dict(verdict=verdict(A('selected_route') > A('simple_any') and A('selected_route') <= A('structure_aware')), selected_route=A('selected_route'), simple_any=A('simple_any'), structure_aware=A('structure_aware'))
    margin = spec['decision_margin_auc']
    beats_simple = all(A(primary) - A(s) >= margin for s in spec['simple_rules'])
    if P['P2']['verdict'] != 'supported':
        reading = 'NOT_A_SIGNAL_ON_DIAMOND'
    elif beats_simple and A(spec['strong_rule']) - A(primary) <= margin:
        reading = 'SLOWDOWN_MATCHES_STRUCTURE_AWARE'
    elif beats_simple:
        reading = 'SLOWDOWN_BETWEEN'
    else:
        reading = 'SLOWDOWN_REDUNDANT_AGAIN'
    summary['predictions'] = P
    summary['reading'] = reading
    summary['auc_test'] = {s: A(s) for s in signals}

    for r in rows:
        r['key'] = list(r['key'])
    off_rows = [dict(a1_tenths=a, b1_tenths=b, **v) for (a, b), v in sorted(off.items())]
    result = dict(schema='hcr-r52-slowdown-diamond-analysis-v1', design_sha256=sha(EXP / 'DESIGN.ko.md'), frozen_spec_sha256=sha(EXP / 'frozen_spec.json'),
                  input_manifest_sha256=sha(EXP / 'input_manifest.json'), config_signature=cfg.signature,
                  memories={'n%d' % n: dict(strength=doc['circuits'][0]['strength'], document_sha256=hashlib.sha256(canonical(doc).encode()).hexdigest()) for n, doc in snapshots.items()},
                  rows=rows, off_rows=off_rows, summary=summary, world_measurement=0, revision_requests=0, feedback_consumed=spec['training']['episodes'])
    result['rows_sha256'] = hashlib.sha256(canonical(rows).encode()).hexdigest()
    result['environment'] = dict(python=sys.version, platform=platform.platform(), libc=list(platform.libc_ver()), machine=platform.machine())
    result['cost'] = dict(wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu0)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    with (out / 'analysis.json').open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
    print(canonical(dict(reading=reading, predictions={k: v['verdict'] for k, v in P.items()}, auc=summary['auc_test'], rows_sha256=result['rows_sha256'], seconds=result['cost']['wall_seconds'])))


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--out', help='new output folder (must not exist)')
    a.add_argument('--smoke', action='store_true', help='three training episodes only; not evidence')
    args = a.parse_args()
    require(sys.version_info >= (3, 12), 'Python 3.12 required')
    require(args.smoke or args.out, '--out required')
    run(args.out, args.smoke)
