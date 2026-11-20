"""R50 / EXP-96: capture width and escape cost under a pure circuit-strength manipulation.

Research harness around the unchanged AdaptiveEngine.  Design, predictions and decision rules:
experiments/exp-96-strength-capture/DESIGN.ko.md
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
EXP = ROOT / 'experiments/exp-96-strength-capture'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def expected_strengths(count):
    """Arithmetic of the learning rule only; used for prediction P1, never fed to the engine."""
    s = 0.55
    out = {3: s}
    for n in range(4, count + 1):
        s += 0.25 * (1 - s)
        out[n] = s
    return out


def reference_feedback(value, proof_valid, identity, decision_id, digest):
    """External reference: the hidden second edge is closed, so the correct answer is False.

    Receives only the public decision value.  The engine never sees the hidden state.
    """
    from hcr.model import Feedback
    correct = None if value is None else (value is False)
    return Feedback(identity, decision_id, digest, correct, proof_valid)


def observation(episode, e1, prefix='v'):
    from hcr.tasks.toy_world import chain
    return chain(episode, (True, False), scores=(1.0, e1), prefix=prefix).observation


def circuit_view(document):
    require(len(document['circuits']) == 1, 'exactly one compiled circuit')
    c = document['circuits'][0]
    episodes = len(c['evidence_episodes'])
    return dict(pattern_length=c['pattern']['program']['edge_count'], strength=c['strength'], episodes=episodes, balance=episodes / (episodes + 1),
                version=c['version'], failures=c['failures'], active=c['active'])


def train(cfg, spec):
    from hcr.model import Feedback, Mode
    from hcr.runtime import AdaptiveEngine
    from hcr.tasks.toy_world import chain
    engine = AdaptiveEngine(cfg, judgment_prior=spec['training']['judgment_prior'])
    snapshots, log = {}, []
    for i in range(1, spec['training']['episodes'] + 1):
        world = chain('r50-train-%02d' % i, (True, True), scores=tuple(spec['training']['scores']), prefix='t%02d' % i)
        obs = world.observation
        decision = engine.infer(obs, Mode(spec['training']['mode']))
        # Training reference: both edges are open, so True is correct.
        correct = None if decision.value is None else (decision.value is True)
        patch = engine.feedback(Feedback('r50-fb-train-%02d' % i, decision.id, obs.digest, correct, decision.proof.under_assumptions_valid))
        document = engine.memory.document()
        log.append(dict(episode=i, value=decision.value, correct=correct, circuit_ids=list(decision.circuit_ids),
                        changes=[c['kind'] for c in patch['changes']], circuits=len(document['circuits']), pending=len(document['pending']),
                        strength=document['circuits'][0]['strength'] if document['circuits'] else None))
        if i in spec['training']['snapshots']:
            snapshots[i] = copy.deepcopy(document)
    return snapshots, log


def evaluate(cfg, document, obs, policy, use_circuits):
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Mode
    from hcr.runtime import AdaptiveEngine
    engine = AdaptiveEngine(cfg, AdaptiveMemory.from_document(copy.deepcopy(document), cfg), use_circuits=use_circuits, judgment_prior=policy)
    before = engine.memory.digest
    decision = engine.infer(obs, Mode.FROZEN_EVAL)
    require(engine.memory.digest == before, 'frozen evaluation left memory unchanged')
    pools = [a for r in engine.trace.records if r['event'] == 'r02_pool_result' for a in r['payload']['activations']]
    cost = decision.cost
    return dict(value=decision.value, status=decision.convergence.status.value, circuit_ids=list(decision.circuit_ids),
                expanded_paths=[list(p) for p in decision.expanded_paths], graph_complete=decision.graph_complete,
                goal=dict(decision.state).get('goal'), expansions=cost['expansions'], kernel_ticks=cost['kernel_ticks'],
                pool_calls=cost['pool_calls'], circuit_reuses=cost['circuit_reuses'],
                pool=[dict(activation=a['activation'], prior=a['prior'], mismatch=a['mismatch'], eligible=a['eligible']) for a in pools])


def escape_series(cfg, document, e1, spec, tag):
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Mode
    from hcr.runtime import AdaptiveEngine
    engine = AdaptiveEngine(cfg, AdaptiveMemory.from_document(copy.deepcopy(document), cfg), judgment_prior=spec['escape']['policy'])
    steps = []
    for k in range(1, spec['escape']['max_episodes'] + 1):
        obs = observation('r50-escape-%s-%d' % (tag, k), e1, prefix='x%d' % k)
        decision = engine.infer(obs, Mode(spec['escape']['mode']))
        feedback = reference_feedback(decision.value, decision.proof.under_assumptions_valid, 'r50-fb-escape-%s-%d' % (tag, k), decision.id, obs.digest)
        patch = engine.feedback(feedback)
        steps.append(dict(step=k, value=decision.value, status=decision.convergence.status.value, circuit_ids=list(decision.circuit_ids),
                          feedback_correct=feedback.correct, changes=[c['kind'] for c in patch['changes']],
                          after=circuit_view(engine.memory.document())))
    wrong_true = 0
    for s in steps:
        if s['value'] is not True:
            break
        wrong_true += 1
    escaped = wrong_true < len(steps)
    final = engine.memory.document()
    post = evaluate(cfg, final, observation('r50-escape-%s-post' % tag, e1, prefix='xp'), spec['escape']['policy'], True)
    return dict(steps=steps, escape_count=wrong_true, escaped=escaped, post_evaluation=post, final_circuit=circuit_view(final))


def run(out, smoke):
    from hcr.circuits import AdaptiveMemory
    from hcr.model import AdaptiveConfig
    from hcr.tasks.toy_world import World

    def forbidden(*a, **k):
        raise ValueError('R50 world measurement forbidden')
    World.measure = forbidden
    started, cpu0 = time.monotonic(), time.process_time()
    spec = read(EXP / 'frozen_spec.json')
    require(all(sha(ROOT / n) == h for n, h in read(EXP / 'input_manifest.json').items()), 'input SHA pins')
    cfg = AdaptiveConfig()
    snapshots, training_log = train(cfg, dict(spec, training=dict(spec['training'], episodes=3, snapshots=[3])) if smoke else spec)
    if smoke:
        print(canonical(dict(smoke=True, training=training_log, circuit=circuit_view(snapshots[3]), document_keys=sorted(snapshots[3]))))
        return
    s_expected = expected_strengths(spec['training']['episodes'])
    names = {'s6': s_expected[6], 's20': s_expected[20]}
    memories = {'n%d' % n: dict(kind='native_training', base=n, document=snapshots[n]) for n in spec['training']['snapshots']}
    for item in spec['synthetic']:
        document = copy.deepcopy(snapshots[item['base']])
        document['circuits'][0]['strength'] = eval(item['strength_expr'], {'__builtins__': {}}, names)
        AdaptiveMemory.from_document(document, cfg)  # must satisfy the memory contract
        changed = [k for k in document['circuits'][0] if document['circuits'][0][k] != snapshots[item['base']]['circuits'][0][k]]
        require(changed in (['strength'], []) and {k: v for k, v in document.items() if k != 'circuits'} == {k: v for k, v in snapshots[item['base']].items() if k != 'circuits'}, 'only strength edited')
        memories[item['name']] = dict(kind='synthetic_strength_edit', base=item['base'], document=document)

    # width evaluations
    rows = []
    ev = spec['evaluation']
    for name, memory in memories.items():
        for policy in ev['policies']:
            for t in ev['e1_tenths']:
                e1 = t / 10
                r = evaluate(cfg, memory['document'], observation('r50-eval-%s-%s-%+03d-on' % (name, policy, t), e1), policy, True)
                rows.append(dict(memory=name, policy=policy, e1_tenths=t, e1=e1, use_circuits=True, **r))
    for n in ev['off_memories']:
        for policy in ev['policies']:
            for t in ev['e1_tenths']:
                e1 = t / 10
                r = evaluate(cfg, memories['n%d' % n]['document'], observation('r50-eval-n%d-%s-%+03d-off' % (n, policy, t), e1), policy, False)
                rows.append(dict(memory='n%d' % n, policy=policy, e1_tenths=t, e1=e1, use_circuits=False, **r))
    require(len(rows) == spec['expected_counts']['width_evaluations'], 'declared width evaluations')

    # escape series
    escapes = []
    for n in spec['escape']['memories']:
        for e1 in spec['escape']['e1']:
            tag = 'n%d-%+03d' % (n, round(e1 * 10))
            escapes.append(dict(memory='n%d' % n, e1=e1, **escape_series(cfg, memories['n%d' % n]['document'], e1, spec, tag)))
    require(len(escapes) == spec['expected_counts']['escape_series'], 'declared escape series')

    result = dict(schema='hcr-r50-strength-capture-analysis-v1',
                  design_sha256=sha(EXP / 'DESIGN.ko.md'), frozen_spec_sha256=sha(EXP / 'frozen_spec.json'), input_manifest_sha256=sha(EXP / 'input_manifest.json'),
                  config_signature=cfg.signature, training_log=training_log,
                  memories={k: dict(kind=v['kind'], base=v['base'], circuit=circuit_view(v['document']), document_sha256=hashlib.sha256(canonical(v['document']).encode()).hexdigest()) for k, v in memories.items()},
                  rows=rows, escapes=escapes, learning_updates=len(training_log) + sum(len(e['steps']) for e in escapes),
                  world_measurement=0, revision_requests=0)
    result['rows_sha256'] = hashlib.sha256(canonical(rows).encode()).hexdigest()
    result['escapes_sha256'] = hashlib.sha256(canonical(escapes).encode()).hexdigest()
    result['summary'] = summarize(result, spec, s_expected)
    result['environment'] = dict(python=sys.version, platform=platform.platform(), libc=list(platform.libc_ver()), machine=platform.machine())
    result['cost'] = dict(wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu0)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    with (out / 'analysis.json').open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n')
    print(canonical(dict(predictions={k: v['verdict'] for k, v in result['summary']['predictions'].items()}, control=result['summary']['control_c0']['status'],
                         h07_reading=result['summary']['h07_reading'], rows_sha256=result['rows_sha256'], seconds=result['cost']['wall_seconds'])))


def summarize(result, spec, s_expected):
    """Verdicts exactly as fixed in DESIGN sections 6 and 7."""
    rows, memories = result['rows'], result['memories']
    on = {(r['memory'], r['policy'], r['e1_tenths']): r for r in rows if r['use_circuits']}
    off = {(r['memory'], r['policy'], r['e1_tenths']): r for r in rows if not r['use_circuits']}
    tenths = spec['evaluation']['e1_tenths']
    policies = spec['evaluation']['policies']
    off_same = all({k: v for k, v in off[('n3', p, t)].items() if k != 'memory'} == {k: v for k, v in off[('n20', p, t)].items() if k != 'memory'} for p in policies for t in tenths)

    def width(memory, policy):
        captured = [t for t in tenths if on[(memory, policy, t)]['value'] is True and off[('n3', policy, t)]['value'] is not True]
        both = [t for t in tenths if on[(memory, policy, t)]['value'] is True and off[('n3', policy, t)]['value'] is True]
        selected = [t for t in tenths if on[(memory, policy, t)]['circuit_ids']]
        return dict(captured_tenths=captured, width=len(captured), true_with_off_true_tenths=both, circuit_selected_tenths=selected)

    widths = {m: {p: width(m, p) for p in policies} for m in memories}
    w = lambda m: widths[m]['legacy']['width']
    natives = ['n%d' % n for n in spec['training']['snapshots']]
    P = {}
    # P1
    p1 = all(memories['n%d' % n]['circuit']['strength'] == s_expected[n] and memories['n%d' % n]['circuit']['episodes'] == n and memories['n%d' % n]['circuit']['pattern_length'] == 2 for n in spec['training']['snapshots'])
    P['P1'] = dict(verdict='supported' if p1 else 'falsified', strengths={m: memories[m]['circuit']['strength'] for m in natives})
    # P2
    differing = [[m, t] for m in memories for t in tenths if on[(m, 'route_only', t)]['value'] != off[('n3', 'route_only', t)]['value']]
    P['P2'] = dict(verdict='supported' if not differing and all(widths[m]['route_only']['width'] == 0 for m in memories) else 'falsified', cells_differing_from_off=differing)
    # P3
    seq = [w(m) for m in natives]
    monotone = all(a <= b for a, b in zip(seq, seq[1:]))
    grows = w('n20') > w('n3')
    saturates = (w('n20') - w('n9')) <= (w('n6') - w('n3'))
    P['P3'] = dict(verdict='supported' if monotone and grows and saturates else 'falsified', widths=dict(zip(natives, seq)), monotone=monotone, grows=grows, saturates=saturates)
    # P4
    below = [[m, p, t] for m in memories for p in policies for t in tenths if t < -8 and on[(m, p, t)]['circuit_ids']]
    reference = {t: on[('n3', 'legacy', t)]['pool'] for t in (-10, 10)}
    same_pool = all(on[(m, p, t)]['pool'] == reference[t] for m in memories for p in policies for t in (-10, 10))
    P['P4'] = dict(verdict='supported' if not below and same_pool else 'falsified', selected_below_mismatch_bound=below, identical_pool_at_abs_one=same_pool)
    # P5
    pair = [(on[('b3@p6', p, t)], on[('n6', p, t)]) for p in policies for t in tenths]
    same_decision = all(a['value'] == b['value'] and bool(a['circuit_ids']) == bool(b['circuit_ids']) for a, b in pair)
    gap = max([abs(x['activation'] - y['activation']) for a, b in pair for x, y in zip(a['pool'], b['pool'])] + [0.0])
    same_shape = all(len(a['pool']) == len(b['pool']) for a, b in pair)
    balance_order = w('b20@s6') >= w('b3@s6')
    P['P5'] = dict(verdict='supported' if same_decision and same_shape and gap <= spec['tolerances']['p5_activation'] and balance_order else 'falsified',
                   product_matched_same_decision=same_decision, max_activation_gap=gap, width_b3_s6=w('b3@s6'), width_b20_s6=w('b20@s6'), width_n6=w('n6'))
    # P6 / C0
    c0 = {}
    for name, table in spec['control_c0']['expected'].items():
        for key, expected in table.items():
            pool = on[(name, 'route_only', round(float(key) * 10))]['pool']
            c0[name + '/' + key] = dict(expected=expected, observed=pool[0]['activation'] if pool else None)
    c0_ok = all(v['expected'] == v['observed'] for v in c0.values())
    P['P6'] = dict(verdict='supported' if c0_ok else 'falsified')
    # P7
    esc = result['escapes']
    arithmetic = True
    for e in esc:
        s = result['memories'][e['memory']]['circuit']['strength']
        fails = 0
        for step in e['steps']:
            if 'weaken' in step['changes']:
                s *= 0.2
                fails += 1
            arithmetic = arithmetic and step['after']['strength'] == s and step['after']['failures'] == fails and step['after']['active'] == (not (fails >= 3 and s < 0.05))
    counts = {e['memory'] + '/' + str(e['e1']): e['escape_count'] for e in esc}
    bounded = all(e['escape_count'] <= 3 for e in esc)
    near = all(abs(counts['n20/' + str(x)] - counts['n3/' + str(x)]) <= 1 for x in spec['escape']['e1'])
    P['P7'] = dict(verdict='supported' if bounded and near and arithmetic else 'falsified', escape_counts=counts, bounded_by_three=bounded, n20_minus_n3_within_one=near, strength_arithmetic_exact=arithmetic)
    # P8
    fam = {m: (on[(m, 'legacy', 9)], off[('n3', 'legacy', 9)]) for m in natives}
    fewer = all(a['expansions'] < b['expansions'] for a, b in fam.values())
    more_ticks = all(a['kernel_ticks'] > b['kernel_ticks'] for a, b in fam.values())
    constant = len({(a['expansions'], a['kernel_ticks']) for a, _ in fam.values()}) == 1
    P['P8'] = dict(verdict='supported' if fewer and more_ticks and constant else 'falsified', on={m: [a['expansions'], a['kernel_ticks']] for m, (a, _) in fam.items()},
                   off=[fam['n3'][1]['expansions'], fam['n3'][1]['kernel_ticks']], fewer_expansions=fewer, more_ticks=more_ticks, constant_over_n=constant)
    if not c0_ok:
        reading = 'CONTROL_FAILED'
    elif P['P3']['verdict'] != 'supported':
        reading = 'WIDTH_PREMISE_NOT_SUPPORTED'
    elif P['P7']['verdict'] == 'supported':
        reading = 'WIDTH_GROWS_ESCAPE_COST_FLAT__H07_NOT_TESTABLE_UNDER_CURRENT_RULE'
    else:
        reading = 'TRADEOFF_CANDIDATE_OBSERVED'
    return dict(off_identical_across_memories=off_same, widths=widths, predictions=P, control_c0=dict(status='EXACT' if c0_ok else 'MISMATCH', values=c0), h07_reading=reading)


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--out', help='new output folder (must not exist)')
    a.add_argument('--smoke', action='store_true', help='three training episodes only; prints memory shape; not evidence')
    args = a.parse_args()
    require(sys.version_info >= (3, 12), 'Python 3.12 required')
    require(args.smoke or args.out, '--out required')
    run(args.out, args.smoke)
