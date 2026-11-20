"""Second-path check of the R52 / EXP-98 analysis (host-aware, same policy as R50 verify v2).

Does not import the R52 probe (only the pure helpers of tools/r51_slowdown_signal/core.py).
On the host that runs it: re-trains the memories and re-runs all 1,536 ON and 256 OFF
evaluations through the AdaptiveSession driver, then recomputes targets, thresholds, AUCs,
fixed-threshold outcomes, verdicts and the reading with separate code.

Blocking: memory documents; discrete outcomes of every cell (value, status, applied circuit
spans, expanded paths, expansions, per-network ticks); all metrics of tick and input signals;
verdicts and reading.  Diagnostic only: floating-point goal states and the goal_margin signal.
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
EXP = ROOT / 'experiments/exp-98-slowdown-diamond'
EXACT = ['ticks_total', 'ticks_pool', 'ticks_decision', 'simple_any', 'selected_route', 'structure_aware']

from tools.r51_slowdown_signal.core import auc, target_type  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def retrain(cfg, spec):
    from hcr.model import Feedback, Mode
    from hcr.sessions import AdaptiveSession
    from hcr.tasks.toy_world import chain
    t = spec['training']
    session = AdaptiveSession(cfg, None, session_id='r52-verify-train', judgment_prior=t['judgment_prior'])
    docs = {}
    for i in range(1, t['episodes'] + 1):
        obs = chain('r50-train-%02d' % i, (True, True), scores=tuple(t['scores']), prefix='t%02d' % i).observation
        session.begin(obs, Mode(t['mode']))
        decision = session.complete()
        session.feedback(Feedback('r50-fb-train-%02d' % i, decision.id, obs.digest, decision.value is True, decision.proof.under_assumptions_valid))
        if i in t['snapshots']:
            docs[i] = copy.deepcopy(session.memory_document)
    return docs


def session_eval(cfg, spec, document, scores, use_circuits, identity):
    from hcr.circuits import AdaptiveMemory
    from hcr.model import EdgeObservation, Mode, Observation
    from hcr.sessions import AdaptiveSession
    d = spec['diamond']
    obs = Observation(identity, 0, d['vertices'][0], d['vertices'][-1], tuple(EdgeObservation('qe%d' % i, s, t, score) for i, ((s, t), score) in enumerate(zip(d['edges'], scores))))
    session = AdaptiveSession(cfg, AdaptiveMemory.from_document(copy.deepcopy(document), cfg), session_id='r52-verify-' + identity, use_circuits=use_circuits, judgment_prior=spec['policy'])
    session.begin(obs, Mode.FROZEN_EVAL)
    decision = session.complete()
    kinds, ticks, applied = {}, dict(pool=0, decision=0), []
    for r in session.events:
        p = r['payload']
        if r['event'] == 'r02_network':
            kinds[p['network_id']] = p['kind']
        elif r['event'] == 'r02_settled':
            ticks[kinds[p['network_id']]] += p['convergence']['ticks']
        elif r['event'] == 'r02_expansion' and p['candidate']['source'] == 'circuit':
            applied.append(list(p['candidate']['edges']))
    return dict(value=decision.value, status=decision.convergence.status.value, applied=applied, expanded_paths=[list(x) for x in decision.expanded_paths],
                expansions=decision.cost['expansions'], ticks_pool=ticks['pool'], ticks_decision=ticks['decision'], goal=dict(decision.state).get('goal'))


def main(evidence):
    from hcr.model import AdaptiveConfig
    failures = []

    def check(ok, message):
        if not ok and message not in failures:
            failures.append(message)

    analysis = read(evidence / 'analysis.json')
    spec = read(EXP / 'frozen_spec.json')
    cfg = AdaptiveConfig()
    out = dict(schema='hcr-r52-slowdown-diamond-verification-v1', analysis_sha256=sha(evidence / 'analysis.json'), independent_auditor=False,
               host=dict(python=sys.version, platform=platform.platform(), libc=list(platform.libc_ver()), machine=platform.machine()), recorded_host=analysis['environment'])
    check(analysis['design_sha256'] == sha(EXP / 'DESIGN.ko.md') and analysis['frozen_spec_sha256'] == sha(EXP / 'frozen_spec.json') and analysis['input_manifest_sha256'] == sha(EXP / 'input_manifest.json'), 'design/spec/manifest hashes bound to analysis')
    check(all(sha(ROOT / n) == h for n, h in read(EXP / 'input_manifest.json').items()), 'input pins')
    docs = retrain(cfg, spec)
    same = all(hashlib.sha256(canonical(docs[n]).encode()).hexdigest() == analysis['memories']['n%d' % n]['document_sha256'] for n in docs)
    out['memory_documents_rebuilt_equal'] = same
    check(same and len(docs) == len(analysis['memories']), 'memory documents rebuilt bit-identically via AdaptiveSession')

    first = spec['diamond']['fixed_first_edges']
    routes = spec['diamond']['routes']
    scores_of = lambda a, b: (first, a / 10, first, b / 10)
    discrete = dict(checked=0, equal=0)
    floats = dict(cells_with_difference=0, max_goal_abs_diff=0.0)

    def compare(local, recorded):
        discrete['checked'] += 1
        discrete['equal'] += int(all(local[k] == recorded[k] for k in ['value', 'status', 'applied', 'expanded_paths', 'expansions', 'ticks_pool', 'ticks_decision']))
        dg = abs(local['goal'] - recorded['goal']) if local['goal'] is not None and recorded['goal'] is not None else 0.0
        floats['cells_with_difference'] += int(dg > 0)
        floats['max_goal_abs_diff'] = max(floats['max_goal_abs_diff'], dg)

    off = {}
    for r in analysis['off_rows']:
        key = (r['a1_tenths'], r['b1_tenths'])
        off[key] = session_eval(cfg, spec, docs[3], scores_of(*key), False, 'off-%d' % len(off))
        compare(off[key], r)
    cells = []
    for i, r in enumerate(analysis['rows']):
        key = (r['a1_tenths'], r['b1_tenths'])
        scores = scores_of(*key)
        got = session_eval(cfg, spec, docs[int(r['memory'][1:])], scores, True, 'on-%d' % i)
        compare(got, r)
        got.update(memory=r['memory'], role=r['role'], key=key)
        if got['applied']:
            got['target'] = target_type(got['value'], off[key]['value'])
            got['signals'] = dict(ticks_total=got['ticks_pool'] + got['ticks_decision'], ticks_pool=got['ticks_pool'], ticks_decision=got['ticks_decision'],
                                  simple_any=-min(scores), selected_route=-min(scores[j] for span in got['applied'] for j in span),
                                  structure_aware=-max(min(scores[j] for j in route) for route in routes), goal_margin=-abs(2 * got['goal'] - 1))
            check(got['target'] == r['target'], 'target type equal to the recording')
            cells.append(got)
    out['discrete_against_recording'] = discrete
    out['float_diagnostic_against_recording'] = floats
    check(discrete['checked'] == 1792 == discrete['equal'], 'discrete outcomes and per-network ticks equal to the recording for all 1792 evaluations')

    cal = [c for c in cells if c['role'] == 'calibration']
    test = [c for c in cells if c['role'] == 'test']
    thresholds = dict(carried=spec['carried_thresholds'], recalibrated={s: min(c['signals'][s] for c in cal if c['target']) for s in spec['signals']})
    recomputed = {}
    for name, group in [('calibration', cal), ('test', test)]:
        targets = [c for c in group if c['target']]
        others = [c for c in group if not c['target']]
        block = {}
        for s in spec['signals']:
            entry = dict(auc=auc([c['signals'][s] for c in targets], [c['signals'][s] for c in others]))
            for label, table in thresholds.items():
                if table.get(s) is None:
                    continue
                flagged = [c for c in group if c['signals'][s] >= table[s]]
                entry[label] = dict(threshold=table[s], flagged=len(flagged), recall=len([c for c in flagged if c['target']]) / len(targets), reuse_preserved=1 - len([c for c in flagged if not c['target']]) / len(others))
            block[s] = entry
            if s in EXACT:
                rec = analysis['summary'][name]['signals'][s]
                check(entry['auc'] == rec['auc'] and all(all(entry[label][k] == rec[label][k] for k in entry[label]) for label in ('carried', 'recalibrated')), 'metrics equal to the recording: %s / %s' % (name, s))
        recomputed[name] = block
        check(len(targets) == analysis['summary'][name]['targets'] and len(group) == analysis['summary'][name]['applicable'], 'target/applicable counts: ' + name)
    out['recomputed'] = recomputed
    T = recomputed['test']
    A = lambda s: T[s]['auc']
    primary, margin = spec['primary_signal'], spec['decision_margin_auc']
    local = dict(P1=T['simple_any']['carried']['recall'] == 1.0 and T['simple_any']['carried']['reuse_preserved'] < 0.7, P2=A(primary) >= 0.80, P3=A(primary) - A('simple_any') >= 0.05,
                 P4=A('structure_aware') >= A(primary), P5=T[primary]['carried']['recall'] < 0.9 or T[primary]['carried']['reuse_preserved'] < 0.5,
                 P6=A('selected_route') > A('simple_any') and A('selected_route') <= A('structure_aware'))
    local = {k: 'supported' if v else 'falsified' for k, v in local.items()}
    beats = all(A(primary) - A(s) >= margin for s in spec['simple_rules'])
    reading = ('NOT_A_SIGNAL_ON_DIAMOND' if local['P2'] != 'supported' else 'SLOWDOWN_MATCHES_STRUCTURE_AWARE' if beats and A(spec['strong_rule']) - A(primary) <= margin else 'SLOWDOWN_BETWEEN' if beats else 'SLOWDOWN_REDUNDANT_AGAIN')
    recorded = {k: v['verdict'] for k, v in analysis['summary']['predictions'].items()}
    out['verdicts'] = dict(local=local, recorded=recorded, reading_local=reading, reading_recorded=analysis['summary']['reading'])
    check(local == recorded and reading == analysis['summary']['reading'], 'verdicts and reading equal to the recording')

    # exploratory (not pre-registered), from the local table
    flag = lambda s: {(c['memory'], c['key']) for c in test if c['signals'][s] >= thresholds['recalibrated'][s]}
    one_clean = [c for c in test if (c['key'][0] > 0) != (c['key'][1] > 0)]
    used_conflicted = [c for c in one_clean if (c['key'][0] if c['applied'][0] == routes[0] else c['key'][1]) <= 0]
    both_pos = [c for c in test if c['key'][0] > 0 and c['key'][1] > 0 and c['key'][0] != c['key'][1]]
    weaker = [c for c in both_pos if (c['key'][0] if c['applied'][0] == routes[0] else c['key'][1]) == min(c['key'])]
    override = [c for c in test if c['signals']['selected_route'] >= 0]
    out['exploratory'] = dict(
        ticks_decision_and_selected_route_flag_same_test_cells=flag('ticks_decision') == flag('selected_route'),
        off_true_iff_some_route_positive=all((v['value'] is True) == (k[0] > 0 or k[1] > 0) for k, v in off.items()),
        one_clean_route_cells=len(one_clean), of_which_circuit_applied_to_the_conflicted_route=len(used_conflicted),
        of_which_adopted_true=sum(1 for c in used_conflicted if c['value'] is True),
        both_routes_positive_unequal_cells=len(both_pos), of_which_weaker_route_applied=len(weaker),
        cells_where_applied_route_has_nonpositive_evidence=len(override), of_which_targets=sum(1 for c in override if c['target']),
        of_which_masked_by_other_route=sum(1 for c in override if not c['target']),
        auc_ticks_decision_for_applied_route_override=auc([c['signals']['ticks_decision'] for c in override], [c['signals']['ticks_decision'] for c in test if c['signals']['selected_route'] < 0]))
    out['failures'] = failures
    out['status'] = 'PASS' if not failures else 'FAIL'
    return out


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('--evidence', default=str(ROOT / 'evidence/slowdown-diamond-20261120-r52'))
    a.add_argument('--write', metavar='NAME', help='write the report to NAME inside the evidence folder (must not exist)')
    args = a.parse_args()
    result = main(Path(args.evidence))
    text = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n'
    if args.write:
        with (Path(args.evidence) / args.write).open('x', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print(text)
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
