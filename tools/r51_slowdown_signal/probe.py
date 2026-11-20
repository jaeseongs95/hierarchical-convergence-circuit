"""R51 / EXP-97: is slow convergence a usable signal that a decision depends on the circuit prior?

Research harness around the unchanged AdaptiveEngine.  Design, predictions and decision rules:
experiments/exp-97-slowdown-signal/DESIGN.ko.md
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
EXP = ROOT / 'experiments/exp-97-slowdown-signal'

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


def evaluate(cfg, document, e0, e1, policy, use_circuits, identity):
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Mode
    from hcr.runtime import AdaptiveEngine
    from hcr.tasks.toy_world import chain
    obs = chain(identity, (True, False), scores=(e0, e1), prefix='v').observation
    engine = AdaptiveEngine(cfg, AdaptiveMemory.from_document(copy.deepcopy(document), cfg), use_circuits=use_circuits, judgment_prior=policy)
    decision = engine.infer(obs, Mode.FROZEN_EVAL)
    kinds, ticks, pools = {}, dict(pool=0, decision=0), []
    for r in engine.trace.records:
        if r['event'] == 'r02_network':
            kinds[r['payload']['network_id']] = r['payload']['kind']
        elif r['event'] == 'r02_settled':
            ticks[kinds[r['payload']['network_id']]] += r['payload']['convergence']['ticks']
        elif r['event'] == 'r02_pool_result':
            pools.extend(r['payload']['activations'])
    require(ticks['pool'] + ticks['decision'] == decision.cost['kernel_ticks'], 'per-network ticks add up to the cost counter')
    selected = bool(decision.circuit_ids)
    goal = dict(decision.state).get('goal')
    row = dict(value=decision.value, status=decision.convergence.status.value, selected=selected, goal=goal,
               expansions=decision.cost['expansions'], ticks_pool=ticks['pool'], ticks_decision=ticks['decision'], ticks_total=decision.cost['kernel_ticks'],
               activation=pools[0]['activation'] if pools else None, prior=pools[0]['prior'] if pools else None)
    if use_circuits and selected:
        row['signals'] = dict(ticks_total=row['ticks_total'], ticks_pool=row['ticks_pool'], ticks_decision=row['ticks_decision'],
                              goal_margin=-abs(2 * goal - 1), pool_margin=-abs(2 * row['activation'] - 1),
                              uncertainty=max(1 - abs(e0), 1 - abs(e1)), min_score=-min(e0, e1), prior=row['prior'])
    return row


def cells(block):
    return [(n, a, b) for n in block['memories'] for a in block['e0_tenths'] for b in block['e1_tenths']]


def metrics(rows, off, thresholds, signals):
    """rows: applicable ON cells of one set.  Returns per-signal AUC and fixed-threshold outcomes."""
    out = {}
    targets = [r for r in rows if r['target']]
    others = [r for r in rows if not r['target']]
    for s in signals:
        flagged = [r for r in rows if r['signals'][s] >= thresholds[s]] if thresholds[s] is not None else []
        hit = [r for r in flagged if r['target']]
        false_flags = [r for r in flagged if not r['target']]
        removed = [r for r in flagged if r['value'] is True and off[(r['e0_tenths'], r['e1_tenths'])]['value'] is not True]
        out[s] = dict(auc=auc([r['signals'][s] for r in targets], [r['signals'][s] for r in others]),
                      flagged=len(flagged), recall=(len(hit) / len(targets)) if targets else None,
                      reuse_preserved=(1 - len(false_flags) / len(others)) if others else None,
                      closed_world_captures_removed=len(removed), open_world_correct_true_lost=len(removed),
                      extra_off_ticks=sum(off[(r['e0_tenths'], r['e1_tenths'])]['ticks_total'] for r in flagged),
                      extra_off_expansions=sum(off[(r['e0_tenths'], r['e1_tenths'])]['expansions'] for r in flagged))
    types = {}
    for r in targets:
        types[r['target']] = types.get(r['target'], 0) + 1
    captures = sum(1 for r in rows if r['value'] is True and off[(r['e0_tenths'], r['e1_tenths'])]['value'] is not True)
    both_true = sum(1 for r in rows if r['value'] is True and off[(r['e0_tenths'], r['e1_tenths'])]['value'] is True)
    return dict(applicable=len(rows), targets=len(targets), target_types=types, non_targets=len(others),
                closed_world_wrong_true_before=captures + both_true, closed_world_captures_before=captures, signals=out)


def run(out, smoke):
    from hcr.model import AdaptiveConfig
    from hcr.tasks.toy_world import World

    def forbidden(*a, **k):
        raise ValueError('R51 world measurement forbidden')
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
    r50 = read(ROOT / 'evidence/strength-capture-20261120-r50/analysis.json')['memories']
    same_as_r50 = {('n%d' % n): hashlib.sha256(canonical(snapshots[n]).encode()).hexdigest() == r50['n%d' % n]['document_sha256'] for n in snapshots if ('n%d' % n) in r50}
    require(all(same_as_r50.values()) and len(same_as_r50) == 7, 'memories shared with R50 are bit-identical documents')
    policy = spec['policy']
    sets = dict(calibration=spec['calibration'], **spec['test'])
    off, rows = {}, {name: [] for name in sets}
    for name, block in sets.items():
        for n, a, b in cells(block):
            e0, e1 = a / 10, b / 10
            if (a, b) not in off:
                off[(a, b)] = evaluate(cfg, snapshots[3], e0, e1, policy, False, 'r51-off-%+03d-%+03d' % (a, b))
            r = evaluate(cfg, snapshots[n], e0, e1, policy, True, 'r51-on-%s-n%d-%+03d-%+03d' % (name, n, a, b))
            r.update(set=name, memory='n%d' % n, e0_tenths=a, e1_tenths=b, e0=e0, e1=e1)
            r['target'] = target_type(r['value'], off[(a, b)]['value']) if r['selected'] else None
            rows[name].append(r)
    counts = spec['expected_counts']
    require(len(rows['calibration']) == counts['calibration_on'] and sum(len(rows[k]) for k in spec['test']) == counts['test_on'] and len(off) == counts['off'], 'declared evaluation counts')

    signals = spec['signals']
    applicable = {name: [r for r in rs if r['selected']] for name, rs in rows.items()}
    cal_targets = [r for r in applicable['calibration'] if r['target']]
    thresholds = {s: (min(r['signals'][s] for r in cal_targets) if cal_targets else None) for s in signals}
    test_all = [r for name in spec['test'] for r in applicable[name]]
    weak = [r for name in ('T-a', 'T-b') for r in applicable[name]]
    summary = dict(thresholds=thresholds, calibration=metrics(applicable['calibration'], off, thresholds, signals),
                   test_all=metrics(test_all, off, thresholds, signals), test_weak_e0=metrics(weak, off, thresholds, signals),
                   **{name: metrics(applicable[name], off, thresholds, signals) for name in spec['test']})
    # costs over every cell of the test sets (applicable or not)
    all_test = [r for name in spec['test'] for r in rows[name]]
    cost = dict(always_on=dict(ticks=sum(r['ticks_total'] for r in all_test), expansions=sum(r['expansions'] for r in all_test)),
                always_off=dict(ticks=sum(off[(r['e0_tenths'], r['e1_tenths'])]['ticks_total'] for r in all_test), expansions=sum(off[(r['e0_tenths'], r['e1_tenths'])]['expansions'] for r in all_test)))
    for s in signals:
        m = summary['test_all']['signals'][s]
        cost['gate_' + s] = dict(ticks=cost['always_on']['ticks'] + m['extra_off_ticks'], expansions=cost['always_on']['expansions'] + m['extra_off_expansions'])
    summary['cost_test_cells'] = cost

    primary = spec['primary_signal']
    A = lambda block, s: summary[block]['signals'][s]['auc']
    P = {}
    P['P1'] = dict(verdict=verdict(A('test_all', primary) is not None and A('test_all', primary) >= 0.80), auc=A('test_all', primary))
    tc = summary['T-c']['signals'][primary]
    P['P2'] = dict(verdict=verdict(tc['recall'] is not None and tc['recall'] >= 0.9 and tc['reuse_preserved'] >= 0.8), recall=tc['recall'], reuse_preserved=tc['reuse_preserved'])
    tw = summary['test_weak_e0']['signals'][primary]
    P['P3'] = dict(verdict=verdict(tw['recall'] is None or tw['recall'] < 0.9 or tw['reuse_preserved'] < 0.5) if summary['test_weak_e0']['targets'] else 'not_evaluable', recall=tw['recall'], reuse_preserved=tw['reuse_preserved'])
    ms_c, ms_w = A('T-c', 'min_score'), A('test_weak_e0', 'min_score')
    P['P4'] = dict(verdict=verdict(ms_c == 1.0 and ms_c >= A('T-c', primary) and ms_w < 0.9) if ms_c is not None and ms_w is not None else 'not_evaluable', min_score_auc_T_c=ms_c, primary_auc_T_c=A('T-c', primary), min_score_auc_weak=ms_w)
    ranking = sorted(signals, key=lambda s: -(A('test_all', s) if A('test_all', s) is not None else -1))
    P['P5'] = dict(verdict=verdict(ranking[0] in ('goal_margin', 'ticks_decision')), ranking=[[s, A('test_all', s)] for s in ranking])
    P['P6'] = dict(verdict=verdict(all(m['closed_world_captures_removed'] == m['open_world_correct_true_lost'] for m in summary['test_all']['signals'].values())))
    baseline_best = max(A('test_all', s) for s in spec['input_baselines'])
    if P['P1']['verdict'] != 'supported':
        reading = 'SLOWDOWN_NOT_A_SIGNAL'
    elif A('test_all', primary) - baseline_best >= spec['decision_margin_auc']:
        reading = 'SLOWDOWN_ADDS_INFORMATION'
    else:
        reading = 'SLOWDOWN_REDUNDANT_HERE'
    summary['predictions'] = P
    summary['reading'] = reading
    summary['primary_minus_best_input_baseline_auc'] = A('test_all', primary) - baseline_best

    flat = [r for name in sets for r in rows[name]]
    off_rows = [dict(e0_tenths=a, e1_tenths=b, **v) for (a, b), v in sorted(off.items())]
    result = dict(schema='hcr-r51-slowdown-signal-analysis-v1', design_sha256=sha(EXP / 'DESIGN.ko.md'), frozen_spec_sha256=sha(EXP / 'frozen_spec.json'),
                  input_manifest_sha256=sha(EXP / 'input_manifest.json'), config_signature=cfg.signature,
                  memories={'n%d' % n: dict(strength=d['circuits'][0]['strength'], episodes=len(d['circuits'][0]['evidence_episodes']), document_sha256=hashlib.sha256(canonical(d).encode()).hexdigest()) for n, d in snapshots.items()},
                  memories_shared_with_r50_identical=same_as_r50, rows=flat, off_rows=off_rows, summary=summary, world_measurement=0, revision_requests=0, feedback_consumed=spec['training']['episodes'])
    result['rows_sha256'] = hashlib.sha256(canonical(flat).encode()).hexdigest()
    result['environment'] = dict(python=sys.version, platform=platform.platform(), libc=list(platform.libc_ver()), machine=platform.machine())
    result['cost'] = dict(wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu0)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    with (out / 'analysis.json').open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n')
    print(canonical(dict(reading=reading, predictions={k: v['verdict'] for k, v in P.items()}, rows_sha256=result['rows_sha256'], seconds=result['cost']['wall_seconds'])))


def verdict(ok):
    return 'supported' if ok else 'falsified'


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--out', help='new output folder (must not exist)')
    a.add_argument('--smoke', action='store_true', help='three training episodes only; not evidence')
    args = a.parse_args()
    require(sys.version_info >= (3, 12), 'Python 3.12 required')
    require(args.smoke or args.out, '--out required')
    run(args.out, args.smoke)
