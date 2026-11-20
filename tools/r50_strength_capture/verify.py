"""Second-path check of the R50 / EXP-96 analysis (verification schema v2).

Does not import the R50 probe.  Everything is recomputed on the host that runs this file:
  1. the 14 memory documents, re-trained through the AdaptiveSession driver;
  2. all 672 width evaluations on two drivers (AdaptiveEngine.infer and AdaptiveSession), which
     must agree bit for bit with each other on the same host;
  3. the 8 escape series through AdaptiveSession;
  4. capture sets and prediction verdicts, with code separate from the probe.

Comparison with the recorded analysis.json is split in two, because the kernel calls the
platform's libm exp() and last-bit results are not guaranteed to be identical across hosts:
  - discrete outcomes (adopted value, status, circuit selection, expansions, capture sets,
    escape sequences, verdicts P1-P5/P7 and the H07 reading) must be identical: blocking;
  - floating-point states, pool activations and tick counts are compared and reported as a
    host-reproducibility diagnostic: not blocking, except control C0 within 1e-9.

v1 of this file required bitwise equality with the recording for every float and failed on a
second host (638/672) while every discrete check passed.  See RESULTS.ko.md section 6.
"""
import argparse
import copy
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
EXP = ROOT / 'experiments/exp-96-strength-capture'
TENTHS = list(range(-10, 11))
POLICIES = ['legacy', 'route_only']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def install_exp_variant(name):
    """Diagnostic only: replace the kernel's exp to emulate a libm with different last-bit rounding."""
    if name == 'platform':
        return
    import decimal
    import hcr.dynamics as dynamics
    context = decimal.Context(prec=60)

    def correctly_rounded(z):
        return float(context.create_decimal(repr(z)).exp(context)) if z > -745 else 0.0
    if name != 'correctly_rounded':
        raise ValueError('unknown exp variant')
    dynamics.exp = correctly_rounded


def observation(identity, e1):
    from hcr.tasks.toy_world import chain
    return chain(identity, (True, False), scores=(1.0, e1), prefix='v').observation


def retrain(cfg, spec):
    from hcr.model import Feedback, Mode
    from hcr.sessions import AdaptiveSession
    from hcr.tasks.toy_world import chain
    session = AdaptiveSession(cfg, None, session_id='r50-verify-train', judgment_prior=spec['training']['judgment_prior'])
    docs = {}
    for i in range(1, spec['training']['episodes'] + 1):
        obs = chain('r50-train-%02d' % i, (True, True), scores=tuple(spec['training']['scores']), prefix='t%02d' % i).observation
        session.begin(obs, Mode(spec['training']['mode']))
        decision = session.complete()
        session.feedback(Feedback('r50-fb-train-%02d' % i, decision.id, obs.digest, decision.value is True, decision.proof.under_assumptions_valid))
        if i in spec['training']['snapshots']:
            docs[i] = copy.deepcopy(session.memory_document)
    return docs


def view(decision, events):
    pools = [a['activation'] for r in events if r['event'] == 'r02_pool_result' for a in r['payload']['activations']]
    return dict(value=decision.value, status=decision.convergence.status.value, selected=bool(decision.circuit_ids), goal=dict(decision.state).get('goal'),
                expansions=decision.cost['expansions'], kernel_ticks=decision.cost['kernel_ticks'], pool=pools)


def session_eval(cfg, document, e1, policy, use_circuits, identity):
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Mode
    from hcr.sessions import AdaptiveSession
    session = AdaptiveSession(cfg, AdaptiveMemory.from_document(copy.deepcopy(document), cfg), session_id='r50-verify-' + identity,
                              use_circuits=use_circuits, judgment_prior=policy)
    session.begin(observation(identity, e1), Mode.FROZEN_EVAL)
    return view(session.complete(), session.events)


def engine_eval(cfg, document, e1, policy, use_circuits, identity):
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Mode
    from hcr.runtime import AdaptiveEngine
    engine = AdaptiveEngine(cfg, AdaptiveMemory.from_document(copy.deepcopy(document), cfg), use_circuits=use_circuits, judgment_prior=policy)
    return view(engine.infer(observation(identity, e1), Mode.FROZEN_EVAL), engine.trace.records)


def session_escape(cfg, document, e1, spec, tag):
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Feedback, Mode
    from hcr.sessions import AdaptiveSession
    from hcr.tasks.toy_world import chain
    session = AdaptiveSession(cfg, AdaptiveMemory.from_document(copy.deepcopy(document), cfg), session_id='r50-verify-escape-' + tag, judgment_prior=spec['escape']['policy'])
    steps = []
    for k in range(1, spec['escape']['max_episodes'] + 1):
        obs = chain('r50-escape-%s-%d' % (tag, k), (True, False), scores=(1.0, e1), prefix='x%d' % k).observation
        session.begin(obs, Mode(spec['escape']['mode']))
        decision = session.complete()
        correct = None if decision.value is None else (decision.value is False)
        session.feedback(Feedback('r50-fb-escape-%s-%d' % (tag, k), decision.id, obs.digest, correct, decision.proof.under_assumptions_valid))
        c = session.memory_document['circuits'][0]
        steps.append(dict(value=decision.value, selected=bool(decision.circuit_ids), strength=c['strength'], failures=c['failures'], active=c['active']))
    return steps


def main(evidence, exp_variant):
    from hcr.model import AdaptiveConfig
    install_exp_variant(exp_variant)
    failures = []

    def check(ok, message):
        if not ok:
            failures.append(message)

    analysis = read(evidence / 'analysis.json')
    spec = read(EXP / 'frozen_spec.json')
    cfg = AdaptiveConfig()
    out = dict(schema='hcr-r50-strength-capture-verification-v2', analysis_sha256=sha(evidence / 'analysis.json'), independent_auditor=False, exp_variant=exp_variant,
               host=dict(python=sys.version, platform=platform.platform(), libc=list(platform.libc_ver()), machine=platform.machine()),
               recorded_host=analysis['environment'])
    check(analysis['design_sha256'] == sha(EXP / 'DESIGN.ko.md') and analysis['frozen_spec_sha256'] == sha(EXP / 'frozen_spec.json') and analysis['input_manifest_sha256'] == sha(EXP / 'input_manifest.json'), 'design/spec/manifest hashes bound to analysis')
    check(all(sha(ROOT / n) == h for n, h in read(EXP / 'input_manifest.json').items()), 'input pins')

    # 1. memories: only IEEE add/multiply, so documents must be identical on any host
    docs = retrain(cfg, spec)
    s = 0.55
    arithmetic = {3: s}
    for n in range(4, 21):
        s += 0.25 * (1 - s)
        arithmetic[n] = s
    edits = {'b3@0.11': (3, 0.55 * 0.2), 'b3@0.022': (3, 0.55 * 0.2 * 0.2), 'b3@s6': (3, arithmetic[6]), 'b3@s20': (3, arithmetic[20]),
             'b3@p6': (3, arithmetic[6] * (6 / 7) / (3 / 4)), 'b20@0.55': (20, 0.55), 'b20@s6': (20, arithmetic[6])}
    memories = {'n%d' % n: docs[n] for n in docs}
    for name, (base, strength) in edits.items():
        d = copy.deepcopy(docs[base])
        d['circuits'][0]['strength'] = strength
        memories[name] = d
    same_docs = {m: hashlib.sha256(canonical(memories[m]).encode()).hexdigest() == analysis['memories'][m]['document_sha256'] for m in analysis['memories']}
    out['memory_documents_rebuilt_equal'] = all(same_docs.values())
    check(set(memories) == set(analysis['memories']) and all(same_docs.values()), 'all 14 memory documents rebuilt bit-identically via AdaptiveSession')
    p1 = all(docs[n]['circuits'][0]['strength'] == arithmetic[n] and len(docs[n]['circuits'][0]['evidence_episodes']) == n for n in docs)

    # 2. all 672 evaluations on two drivers on this host, then against the recording
    local = {}
    drivers_equal = 0
    discrete_equal = 0
    float_cells = []
    tick_cells = []
    max_goal = max_pool = 0.0
    max_tick = 0
    for i, r in enumerate(analysis['rows']):
        key = (r['memory'], r['policy'], r['e1_tenths'], r['use_circuits'])
        a = session_eval(cfg, memories[r['memory']], r['e1'], r['policy'], r['use_circuits'], 's-%d' % i)
        b = engine_eval(cfg, memories[r['memory']], r['e1'], r['policy'], r['use_circuits'], 'e-%d' % i)
        drivers_equal += int(a == b)
        local[key] = a
        recorded_pool = [p['activation'] for p in r['pool']]
        discrete = (a['value'] == r['value'] and a['status'] == r['status'] and a['selected'] == bool(r['circuit_ids']) and a['expansions'] == r['expansions'] and len(a['pool']) == len(recorded_pool))
        discrete_equal += int(discrete)
        dg = abs(a['goal'] - r['goal']) if a['goal'] is not None and r['goal'] is not None else 0.0
        dp = max([abs(x - y) for x, y in zip(a['pool'], recorded_pool)] + [0.0])
        dt = abs(a['kernel_ticks'] - r['kernel_ticks'])
        max_goal, max_pool, max_tick = max(max_goal, dg), max(max_pool, dp), max(max_tick, dt)
        if dg > 0 or dp > 0:
            float_cells.append(dict(memory=r['memory'], policy=r['policy'], e1=r['e1'], use_circuits=r['use_circuits'], goal_abs_diff=dg, pool_abs_diff=dp, tick_diff=a['kernel_ticks'] - r['kernel_ticks']))
        if dt:
            tick_cells.append(dict(memory=r['memory'], policy=r['policy'], e1=r['e1'], use_circuits=r['use_circuits'], local=a['kernel_ticks'], recorded=r['kernel_ticks']))
    float_cells.sort(key=lambda c: -max(c['goal_abs_diff'], c['pool_abs_diff']))
    out['drivers'] = dict(checked=len(analysis['rows']), engine_and_session_bitwise_equal=drivers_equal)
    out['against_recording'] = dict(discrete_equal=discrete_equal, cells_with_any_float_difference=len(float_cells), bitwise_equal_cells=len(analysis['rows']) - len(float_cells) if not tick_cells else len(analysis['rows']) - len({(c['memory'], c['policy'], c['e1'], c['use_circuits']) for c in float_cells + tick_cells}),
                                    max_goal_abs_diff=max_goal, max_pool_activation_abs_diff=max_pool, cells_with_tick_difference=len(tick_cells), max_tick_abs_diff=max_tick,
                                    largest_float_differences=float_cells[:20], tick_differences=tick_cells[:40])
    check(len(analysis['rows']) == 672 == drivers_equal, 'engine and session drivers bitwise equal on this host for all 672 evaluations')
    check(discrete_equal == 672, 'discrete outcomes (value, status, selection, expansions) equal to the recording for all 672 evaluations')

    # 3. escape series re-run through AdaptiveSession; discrete sequences against the recording
    escape = {}
    for e in analysis['escapes']:
        tag = '%s-%+03d' % (e['memory'], round(e['e1'] * 10))
        steps = session_escape(cfg, memories[e['memory']], e['e1'], spec, tag)
        count = 0
        for step in steps:
            if step['value'] is not True:
                break
            count += 1
        same = [(x['value'], x['selected'], x['strength'], x['failures'], x['active']) for x in steps] == [(y['value'], bool(y['circuit_ids']), y['after']['strength'], y['after']['failures'], y['after']['active']) for y in e['steps']]
        check(same and count == e['escape_count'], 'escape series equal to the recording: %s %s' % (e['memory'], e['e1']))
        escape['%s/%s' % (e['memory'], e['e1'])] = dict(escape_count=count, values=[x['value'] for x in steps], final_strength=steps[-1]['strength'], final_active=steps[-1]['active'])
    out['escape'] = escape

    # 4. capture sets and verdicts from the local table
    on = lambda m, p, t: local[(m, p, t, True)]
    off = lambda p, t: local[('n3', p, t, False)]
    captured = {m: [t for t in TENTHS if on(m, 'legacy', t)['value'] is True and off('legacy', t)['value'] is not True] for m in memories}
    out['legacy_capture_tenths'] = captured
    for m in memories:
        check(captured[m] == analysis['summary']['widths'][m]['legacy']['captured_tenths'], 'capture set equal to the recording: ' + m)
    w = lambda m: len(captured[m])
    natives = ['n%d' % n for n in spec['training']['snapshots']]
    seq = [w(m) for m in natives]
    verdict = {}
    verdict['P1'] = p1
    verdict['P2'] = all(on(m, 'route_only', t)['value'] == off('route_only', t)['value'] for m in memories for t in TENTHS)
    verdict['P3'] = all(a <= b for a, b in zip(seq, seq[1:])) and w('n20') > w('n3') and (w('n20') - w('n9')) <= (w('n6') - w('n3'))
    verdict['P4'] = (not any(on(m, p, t)['selected'] for m in memories for p in POLICIES for t in TENTHS if t < -8)
                     and all(on(m, p, t)['pool'] == on('n3', 'legacy', t)['pool'] for m in memories for p in POLICIES for t in (-10, 10)))
    pairs = [(on('b3@p6', p, t), on('n6', p, t)) for p in POLICIES for t in TENTHS]
    gap = max([abs(x - y) for a, b in pairs for x, y in zip(a['pool'], b['pool'])] + [0.0])
    verdict['P5'] = (all(a['value'] == b['value'] and a['selected'] == b['selected'] and len(a['pool']) == len(b['pool']) for a, b in pairs)
                     and gap <= spec['tolerances']['p5_activation'] and w('b20@s6') >= w('b3@s6'))
    c0 = {name + '/' + k: (v, on(name, 'route_only', round(float(k) * 10))['pool'][0]) for name, t in spec['control_c0']['expected'].items() for k, v in t.items()}
    c0_gap = max(abs(a - b) for a, b in c0.values())
    verdict['P6'] = all(a == b for a, b in c0.values())
    counts = {k: v['escape_count'] for k, v in escape.items()}
    verdict['P7'] = all(c <= 3 for c in counts.values()) and all(abs(counts['n20/' + str(x)] - counts['n3/' + str(x)]) <= 1 for x in spec['escape']['e1'])
    fam = {m: on(m, 'legacy', 9) for m in natives}
    base = off('legacy', 9)
    p8 = dict(fewer_expansions=all(v['expansions'] < base['expansions'] for v in fam.values()), more_ticks=all(v['kernel_ticks'] > base['kernel_ticks'] for v in fam.values()),
              constant_over_n=len({(v['expansions'], v['kernel_ticks']) for v in fam.values()}) == 1, on_ticks={m: v['kernel_ticks'] for m, v in fam.items()}, off_ticks=base['kernel_ticks'])
    verdict['P8'] = p8['fewer_expansions'] and p8['more_ticks'] and p8['constant_over_n']
    local_verdicts = {k: 'supported' if v else 'falsified' for k, v in verdict.items()}
    recorded_verdicts = {k: v['verdict'] for k, v in analysis['summary']['predictions'].items()}
    reading = ('CONTROL_FAILED' if c0_gap > 1e-9 else 'WIDTH_PREMISE_NOT_SUPPORTED' if not verdict['P3'] else
               'WIDTH_GROWS_ESCAPE_COST_FLAT__H07_NOT_TESTABLE_UNDER_CURRENT_RULE' if verdict['P7'] else 'TRADEOFF_CANDIDATE_OBSERVED')
    out['verdicts'] = dict(local=local_verdicts, recorded=recorded_verdicts, h07_reading_local=reading, h07_reading_recorded=analysis['summary']['h07_reading'],
                           host_sensitive=dict(P6_c0_exact=verdict['P6'], P6_c0_max_abs_diff=c0_gap, P8_detail=p8))
    for k in ['P1', 'P2', 'P3', 'P4', 'P5', 'P7']:
        check(local_verdicts[k] == recorded_verdicts[k], 'verdict equal to the recording: ' + k)
    check(reading == analysis['summary']['h07_reading'], 'H07 reading equal to the recording')
    check(c0_gap <= 1e-9, 'control C0 within 1e-9 of the R072 table')

    # 5. exploratory summaries (not pre-registered), from the local table
    product = {m: 2 * memories[m]['circuits'][0]['strength'] * len(memories[m]['circuits'][0]['evidence_episodes']) / (len(memories[m]['circuits'][0]['evidence_episodes']) + 1) for m in memories}
    order = sorted(memories, key=lambda m: product[m])
    out['exploratory_width_by_product'] = [[m, product[m], w(m)] for m in order]
    out['exploratory_width_monotone_in_product'] = all(w(a) <= w(b) for a, b in zip(order, order[1:]))
    slow = {}
    for m in ['n3', 'n6', 'n9', 'n20']:
        ticks = {t: on(m, 'legacy', t)['kernel_ticks'] for t in TENTHS}
        peak = max(ticks, key=ticks.get)
        slow[m] = dict(peak_tenths=peak, peak_ticks=ticks[peak], ticks_at_plus_0_9=ticks[9], lowest_captured_tenths=min(captured[m]) if captured[m] else None)
    out['exploratory_ticks_near_boundary'] = slow

    out['failures'] = failures
    out['status'] = 'PASS' if not failures else 'FAIL'
    return out


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('--evidence', default=str(ROOT / 'evidence/strength-capture-20261120-r50'))
    a.add_argument('--exp-variant', default='platform', choices=['platform', 'correctly_rounded'], help='diagnostic: emulate a libm with different last-bit rounding of exp')
    a.add_argument('--write', metavar='NAME', help='write the report to NAME inside the evidence folder (must not exist)')
    args = a.parse_args()
    result = main(Path(args.evidence), args.exp_variant)
    text = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n'
    if args.write:
        with (Path(args.evidence) / args.write).open('x', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print(text)
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
