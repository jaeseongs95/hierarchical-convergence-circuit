"""Second-path check of the R53 / EXP-99 analysis (host-aware, same policy as R50 verify v2).

Does not import the R53 probe.  On the host that runs it: re-runs every native inference through
the AdaptiveSession driver, then

* recounts theta = 0 events directly from the native per-tick states (no executor involved);
* re-runs the event executor (tools/r53_event_cost/core.py) for theta > 0;
* recomputes the primary theta, the Part A table, the verdicts and the reading with separate code.

Blocking: native discrete outcomes and ticks of all 111 inferences, theta = 0 event counts,
outcome preservation, primary theta, verdicts and reading.  Diagnostic only: theta > 0 event counts
(they depend on floating-point comparisons against theta) and final-state differences.
"""
import argparse
import copy
import hashlib
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
EXP = ROOT / 'experiments/exp-99-event-cost'

from tools.r53_event_cost.core import decision_outcome, event_settle, pool_outcome  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exact_counts(program, top_down, states):
    """theta = 0 events from recorded native states only: a group sends when its state changed in the previous tick."""
    groups = [g['id'] for g in program['groups']]
    links = [l for l in program['links'] if top_down or l['kind'] != 'top_down']
    previous = {g: 0.5 for g in groups}
    changed = {g: True for g in groups}
    link_events = group_updates = 0
    for i, state in enumerate(states):
        senders = set(groups) if i == 0 else {g for g in groups if changed[g]}
        link_events += sum(1 for l in links if l['source'] in senders)
        touched = {l['target'] for l in links if l['source'] in senders}
        group_updates += sum(1 for g in groups if g in touched or changed[g])
        changed = {g: state[g] != previous[g] for g in groups}
        previous = state
    return link_events, group_updates


def run_session(cfg, memory, obs, mode, use_circuits, policy, identity, thetas, give_feedback):
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Feedback
    from hcr.sessions import AdaptiveSession
    session = AdaptiveSession(cfg, AdaptiveMemory.from_document(copy.deepcopy(memory), cfg) if memory is not None else None,
                              session_id='r53-verify-' + identity, use_circuits=use_circuits, judgment_prior=policy)
    session.begin(obs, mode)
    decision = session.complete()
    kernel = asdict(cfg.kernel)
    nets, order, applied = {}, [], []
    for r in session.events:
        p = r['payload']
        if r['event'] == 'r02_network':
            nets[p['network_id']] = dict(p=p, states=[], settled=None)
            order.append(p['network_id'])
        elif r['event'] == 'r02_tick':
            nets[p['network_id']]['states'].append(p['state'])
        elif r['event'] == 'r02_settled':
            nets[p['network_id']]['settled'] = p
        elif r['event'] == 'r02_expansion' and p['candidate']['source'] == 'circuit':
            applied.append(list(p['candidate']['edges']))
    totals = {repr(float(t)): dict(link_events=0, group_updates=0, pool_link_events=0, preserved=True) for t in thetas}
    max_state = 0.0
    for n in order:
        p, native = nets[n]['p'], nets[n]['settled']
        outcome = (lambda r: pool_outcome(r, p['metadata']['candidates'], cfg.activation_threshold, cfg.mismatch_threshold)) if p['kind'] == 'pool' else decision_outcome
        want = outcome(dict(state=native['state'], status=native['convergence']['status']))
        for theta in thetas:
            t = repr(float(theta))
            if theta == 0:
                le, gu = exact_counts(p['program'], p['top_down'], nets[n]['states'])
                same = True
            else:
                r = event_settle(p['program'], p['drives'], kernel, p['top_down'], theta)
                le, gu, same = r['link_events'], r['group_updates'], outcome(r) == want
                max_state = max(max_state, max(abs(r['state'][g] - native['state'][g]) for g in native['state']))
            totals[t]['link_events'] += le
            totals[t]['group_updates'] += gu
            totals[t]['pool_link_events'] += le if p['kind'] == 'pool' else 0
            totals[t]['preserved'] = totals[t]['preserved'] and same
    if give_feedback:
        session.feedback(Feedback('fb-' + identity, decision.id, obs.digest, decision.value is True, decision.proof.under_assumptions_valid))
    return dict(value=decision.value, status=decision.convergence.status.value, applied=applied, expansions=decision.cost['expansions'],
                ticks_total=decision.cost['kernel_ticks'], dense_link_events=decision.cost['signal_transmissions'], totals=totals,
                max_state_abs_diff=max_state), session.memory_document


def main(evidence):
    from hcr import codec
    from hcr.model import AdaptiveConfig, Mode
    from hcr.tasks.toy_world import chain
    failures = []

    def check(ok, message):
        if not ok and message not in failures:
            failures.append(message)

    analysis = read(evidence / 'analysis.json')
    spec = read(EXP / 'frozen_spec.json')
    cfg = AdaptiveConfig()
    thetas = spec['thetas']
    names = [repr(float(t)) for t in thetas]
    out = dict(schema='hcr-r53-event-cost-verification-v1', analysis_sha256=sha(evidence / 'analysis.json'), independent_auditor=False,
               host=dict(python=sys.version, platform=platform.platform(), libc=list(platform.libc_ver()), machine=platform.machine()), recorded_host=analysis['environment'])
    check(analysis['design_sha256'] == sha(EXP / 'DESIGN.ko.md') and analysis['frozen_spec_sha256'] == sha(EXP / 'frozen_spec.json') and analysis['input_manifest_sha256'] == sha(EXP / 'input_manifest.json'), 'design/spec/manifest hashes bound to analysis')
    check(all(sha(ROOT / n) == h for n, h in read(EXP / 'input_manifest.json').items()), 'input pins')

    discrete = dict(checked=0, equal=0)
    exact = dict(checked=0, equal=0)
    approx = dict(inferences_with_count_difference=0, max_abs_link_event_difference=0, max_state_abs_diff_to_native=0.0)

    def compare(local, recorded):
        discrete['checked'] += 1
        discrete['equal'] += int(all(local[k] == recorded[k] for k in ['value', 'status', 'applied', 'expansions', 'ticks_total', 'dense_link_events'])
                                 and all(local['totals'][t]['preserved'] == recorded['totals'][t]['preserved'] for t in names))
        exact['checked'] += 1
        exact['equal'] += int(all(local['totals'][names[0]][k] == recorded['totals'][names[0]][k] for k in ['link_events', 'group_updates', 'pool_link_events']))
        diffs = [abs(local['totals'][t]['link_events'] - recorded['totals'][t]['link_events']) for t in names[1:]]
        approx['inferences_with_count_difference'] += int(any(diffs))
        approx['max_abs_link_event_difference'] = max(approx['max_abs_link_event_difference'], max(diffs))
        approx['max_state_abs_diff_to_native'] = max(approx['max_state_abs_diff_to_native'], local['max_state_abs_diff'])

    a = spec['part_a']
    source = read(ROOT / a['source'])['research']
    memory = None
    for i, case in enumerate(source['training'], 1):
        row, memory = run_session(cfg, memory, codec.observation_from(case['observation']), Mode(a['training_mode']), True, a['policy'], 'a-train-%d' % i, thetas, True)
        compare(row, analysis['part_a_training'][i - 1])
    rows_a, scope = [], []
    for recorded in analysis['part_a']:
        case = next(c for c in source['cases'] if c['id'] == recorded['case'])
        doc = memory if recorded['memory'] == 3 else None
        row, _ = run_session(cfg, doc, codec.observation_from(case['observation']), Mode.FROZEN_EVAL, recorded['use_circuits'], a['policy'], 'a-eval-%d' % len(rows_a), thetas, False)
        compare(row, recorded)
        row.update(case=recorded['case'], memory=recorded['memory'], use_circuits=recorded['use_circuits'])
        rows_a.append(row)
        scope.append(row)
    b = spec['part_b']
    series = {}
    for s in analysis['part_b']:
        doc, got = None, []
        for e in s['episodes']:
            i = e['episode']
            obs = chain('r53-b-%s-%02d' % (s['name'], i), (True,) * s['length'], scores=(b['score'],) * s['length'], prefix='b%s%02d' % (s['name'], i)).observation
            row, doc = run_session(cfg, doc, obs, Mode(b['mode']), s['use_circuits'], s['policy'], 'b-%s-%d' % (s['name'], i), thetas, True)
            compare(row, e)
            check(len(doc['circuits']) == e['circuits_after'], 'Part B circuit count after feedback')
            got.append(row)
            scope.append(row)
        series[s['name']] = got
    out['discrete_against_recording'] = discrete
    out['theta0_counts_from_native_states_against_recording'] = exact
    out['theta_positive_diagnostic_against_recording'] = approx
    check(discrete['checked'] == 111 == discrete['equal'], 'native discrete outcomes, ticks, dense counts and preservation flags equal to the recording for all 111 inferences')
    check(exact['equal'] == exact['checked'], 'theta = 0 event counts recounted from native states equal the executor counts in the recording')

    ok = [t for t in names if all(r['totals'][t]['preserved'] for r in scope)]
    primary = max(ok, key=float) if ok else names[0]
    pairs = []
    for case in a['anchors']['post_ticks_off_on']:
        off = next(r for r in rows_a if r['case'] == case and r['memory'] == 3 and not r['use_circuits'])
        on = next(r for r in rows_a if r['case'] == case and r['memory'] == 3 and r['use_circuits'])
        pairs.append((case, off, on))

    def reading(t):
        on_ge = sum(1 for _, off, on in pairs if on['totals'][t]['link_events'] >= off['totals'][t]['link_events'])
        pool_ge = sum(1 for _, off, on in pairs if on['totals'][t]['pool_link_events'] >= off['totals'][t]['link_events'])
        m = spec['reading_min_pairs']
        if len(pairs) - on_ge >= m:
            return 'ACCOUNTING_ARTIFACT'
        if on_ge >= m and len(pairs) - pool_ge >= m:
            return 'RECOMPUTATION'
        if on_ge >= m and pool_ge >= m:
            return 'SELECTION_COST'
        return 'MIXED'
    formed = b['formed_after']
    mean = lambda v: sum(v) / len(v)
    p6 = True
    for name, got in series.items():
        if not name.endswith('-on'):
            continue
        on = [r['totals'][primary]['link_events'] for r in got]
        off = [r['totals'][primary]['link_events'] for r in series[name[:-3] + '-off']]
        p6 = p6 and mean(on[formed:]) >= mean(on[:formed]) and all(x > y for x, y in zip(on[formed:], off[formed:]))
    local = dict(P3=all(t in ok for t in names if float(t) <= 1e-3) and repr(1e-2) not in ok,
                 P4=all(on['totals'][primary]['link_events'] > off['totals'][primary]['link_events'] for _, off, on in pairs),
                 P5=sum(1 for _, off, on in pairs if on['totals'][primary]['pool_link_events'] >= off['totals'][primary]['link_events']) >= spec['reading_min_pairs'], P6=p6)
    local = {k: 'supported' if v else 'falsified' for k, v in local.items()}
    recorded = {k: analysis['summary']['predictions'][k]['verdict'] for k in local}
    out['verdicts'] = dict(local=local, recorded=recorded, primary_theta_local=primary, primary_theta_recorded=analysis['summary']['primary_theta'],
                           reading_local=reading(primary), reading_recorded=analysis['summary']['reading'], reading_by_theta_local={t: reading(t) for t in ok})
    out['part_a_post_pairs_local'] = [dict(case=c, by_theta={t: dict(off=off['totals'][t]['link_events'], on=on['totals'][t]['link_events'], on_pool=on['totals'][t]['pool_link_events']) for t in names}) for c, off, on in pairs]
    check(local == recorded and primary == analysis['summary']['primary_theta'] and reading(primary) == analysis['summary']['reading'], 'primary theta, verdicts and reading equal to the recording')
    check({t: reading(t) for t in ok} == analysis['summary']['reading_by_theta'], 'reading at every preserving theta equal to the recording')
    out['failures'] = failures
    out['status'] = 'PASS' if not failures else 'FAIL'
    return out


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('--evidence', default=str(ROOT / 'evidence/event-cost-20261120-r53'))
    a.add_argument('--write', metavar='NAME', help='write the report to NAME inside the evidence folder (must not exist)')
    args = a.parse_args()
    result = main(Path(args.evidence))
    text = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n'
    if args.write:
        with (Path(args.evidence) / args.write).open('x', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print(text)
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
