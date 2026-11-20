"""Second-path check of the R51 / EXP-97 analysis (host-aware, same policy as R50 verify v2).

Does not import the R51 probe (only the pure helpers in core.py).  On the host that runs it:
  1. re-trains the memories through AdaptiveSession and compares document hashes;
  2. re-runs all 573 ON and 85 OFF evaluations through AdaptiveSession;
  3. recomputes targets, thresholds, AUCs, fixed-threshold outcomes, verdicts and the reading.

Blocking: memory documents; discrete outcomes of every cell (value, status, selection,
expansions, per-network ticks); everything derived from integer tick signals and from the
exact input signals (targets, thresholds, AUC, recall, reuse preserved, flagged sets);
verdicts P1-P6 and the reading.
Diagnostic only: floating-point goal/activation states and the two margin-based signals,
whose last bits depend on the platform libm.
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
EXP = ROOT / 'experiments/exp-97-slowdown-signal'
EXACT_SIGNALS = ['ticks_total', 'ticks_pool', 'ticks_decision', 'uncertainty', 'min_score', 'prior']

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
    session = AdaptiveSession(cfg, None, session_id='r51-verify-train', judgment_prior=t['judgment_prior'])
    docs = {}
    for i in range(1, t['episodes'] + 1):
        obs = chain('r50-train-%02d' % i, (True, True), scores=tuple(t['scores']), prefix='t%02d' % i).observation
        session.begin(obs, Mode(t['mode']))
        decision = session.complete()
        session.feedback(Feedback('r50-fb-train-%02d' % i, decision.id, obs.digest, decision.value is True, decision.proof.under_assumptions_valid))
        if i in t['snapshots']:
            docs[i] = copy.deepcopy(session.memory_document)
    return docs


def session_eval(cfg, document, e0, e1, policy, use_circuits, identity):
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Mode
    from hcr.sessions import AdaptiveSession
    from hcr.tasks.toy_world import chain
    session = AdaptiveSession(cfg, AdaptiveMemory.from_document(copy.deepcopy(document), cfg), session_id='r51-verify-' + identity, use_circuits=use_circuits, judgment_prior=policy)
    session.begin(chain(identity, (True, False), scores=(e0, e1), prefix='v').observation, Mode.FROZEN_EVAL)
    decision = session.complete()
    kinds, ticks, pools = {}, dict(pool=0, decision=0), []
    for r in session.events:
        if r['event'] == 'r02_network':
            kinds[r['payload']['network_id']] = r['payload']['kind']
        elif r['event'] == 'r02_settled':
            ticks[kinds[r['payload']['network_id']]] += r['payload']['convergence']['ticks']
        elif r['event'] == 'r02_pool_result':
            pools.extend(r['payload']['activations'])
    return dict(value=decision.value, status=decision.convergence.status.value, selected=bool(decision.circuit_ids), goal=dict(decision.state).get('goal'),
                expansions=decision.cost['expansions'], ticks_pool=ticks['pool'], ticks_decision=ticks['decision'],
                activation=pools[0]['activation'] if pools else None, prior=pools[0]['prior'] if pools else None)


def main(evidence):
    from hcr.model import AdaptiveConfig
    failures = []

    def check(ok, message):
        if not ok:
            failures.append(message)

    analysis = read(evidence / 'analysis.json')
    spec = read(EXP / 'frozen_spec.json')
    cfg = AdaptiveConfig()
    out = dict(schema='hcr-r51-slowdown-signal-verification-v1', analysis_sha256=sha(evidence / 'analysis.json'), independent_auditor=False,
               host=dict(python=sys.version, platform=platform.platform(), libc=list(platform.libc_ver()), machine=platform.machine()), recorded_host=analysis['environment'])
    check(analysis['design_sha256'] == sha(EXP / 'DESIGN.ko.md') and analysis['frozen_spec_sha256'] == sha(EXP / 'frozen_spec.json') and analysis['input_manifest_sha256'] == sha(EXP / 'input_manifest.json'), 'design/spec/manifest hashes bound to analysis')
    check(all(sha(ROOT / n) == h for n, h in read(EXP / 'input_manifest.json').items()), 'input pins')

    docs = retrain(cfg, spec)
    same = all(hashlib.sha256(canonical(docs[n]).encode()).hexdigest() == analysis['memories']['n%d' % n]['document_sha256'] for n in docs)
    out['memory_documents_rebuilt_equal'] = same
    check(same and len(docs) == len(analysis['memories']), 'memory documents rebuilt bit-identically via AdaptiveSession')

    policy = spec['policy']
    off = {}
    discrete = dict(checked=0, equal=0)
    floats = dict(cells_with_difference=0, max_goal_abs_diff=0.0, max_activation_abs_diff=0.0)

    def compare(local, recorded):
        discrete['checked'] += 1
        ok = all(local[k] == recorded[k] for k in ['value', 'status', 'selected', 'expansions', 'ticks_pool', 'ticks_decision']) and local['prior'] == recorded['prior']
        discrete['equal'] += int(ok)
        dg = abs(local['goal'] - recorded['goal']) if local['goal'] is not None and recorded['goal'] is not None else 0.0
        da = abs(local['activation'] - recorded['activation']) if local['activation'] is not None and recorded['activation'] is not None else 0.0
        floats['cells_with_difference'] += int(dg > 0 or da > 0)
        floats['max_goal_abs_diff'] = max(floats['max_goal_abs_diff'], dg)
        floats['max_activation_abs_diff'] = max(floats['max_activation_abs_diff'], da)

    for r in analysis['off_rows']:
        got = session_eval(cfg, docs[3], r['e0_tenths'] / 10, r['e1_tenths'] / 10, policy, False, 'off-%d' % len(off))
        compare(got, r)
        off[(r['e0_tenths'], r['e1_tenths'])] = got
    cells = []
    for i, r in enumerate(analysis['rows']):
        got = session_eval(cfg, docs[int(r['memory'][1:])], r['e0'], r['e1'], policy, True, 'on-%d' % i)
        compare(got, r)
        got.update(set=r['set'], memory=r['memory'], e0_tenths=r['e0_tenths'], e1_tenths=r['e1_tenths'])
        if got['selected']:
            e0, e1 = r['e0'], r['e1']
            got['target'] = target_type(got['value'], off[(r['e0_tenths'], r['e1_tenths'])]['value'])
            got['signals'] = dict(ticks_total=got['ticks_pool'] + got['ticks_decision'], ticks_pool=got['ticks_pool'], ticks_decision=got['ticks_decision'],
                                  goal_margin=-abs(2 * got['goal'] - 1), pool_margin=-abs(2 * got['activation'] - 1),
                                  uncertainty=max(1 - abs(e0), 1 - abs(e1)), min_score=-min(e0, e1), prior=got['prior'])
            check(got['target'] == r['target'], 'target type equal: %s %s %s' % (r['memory'], r['e0'], r['e1']))
            cells.append(got)
    out['discrete_against_recording'] = discrete
    out['float_diagnostic_against_recording'] = floats
    check(discrete['checked'] == 658 == discrete['equal'], 'discrete outcomes and per-network ticks equal to the recording for all 658 evaluations')

    cal = [c for c in cells if c['set'] == 'calibration']
    test = [c for c in cells if c['set'] != 'calibration']
    blocks = dict(calibration=cal, test_all=test, test_weak_e0=[c for c in test if c['set'] in ('T-a', 'T-b')], **{name: [c for c in test if c['set'] == name] for name in spec['test']})
    thresholds = {s: min(c['signals'][s] for c in cal if c['target']) for s in spec['signals']}
    out['thresholds'] = thresholds
    recomputed = {}
    for name, group in blocks.items():
        targets = [c for c in group if c['target']]
        others = [c for c in group if not c['target']]
        block = {}
        for s in spec['signals']:
            flagged = [c for c in group if c['signals'][s] >= thresholds[s]]
            block[s] = dict(auc=auc([c['signals'][s] for c in targets], [c['signals'][s] for c in others]), flagged=len(flagged),
                            recall=len([c for c in flagged if c['target']]) / len(targets) if targets else None,
                            reuse_preserved=1 - len([c for c in flagged if not c['target']]) / len(others) if others else None)
            recorded = analysis['summary'][name]['signals'][s]
            if s in EXACT_SIGNALS:
                check(thresholds[s] == analysis['summary']['thresholds'][s] and all(block[s][k] == recorded[k] for k in block[s]), 'metrics equal to the recording: %s / %s' % (name, s))
        recomputed[name] = block
        check(len(targets) == analysis['summary'][name]['targets'] and len(group) == analysis['summary'][name]['applicable'], 'target/applicable counts: ' + name)
    out['recomputed'] = recomputed
    A = lambda b, s: recomputed[b][s]['auc']
    primary = spec['primary_signal']
    best_baseline = max(A('test_all', s) for s in spec['input_baselines'])
    ranking = sorted(spec['signals'], key=lambda s: -A('test_all', s))
    local = dict(P1=A('test_all', primary) >= 0.80,
                 P2=recomputed['T-c'][primary]['recall'] >= 0.9 and recomputed['T-c'][primary]['reuse_preserved'] >= 0.8,
                 P3=recomputed['test_weak_e0'][primary]['recall'] < 0.9 or recomputed['test_weak_e0'][primary]['reuse_preserved'] < 0.5,
                 P4=A('T-c', 'min_score') == 1.0 and A('T-c', 'min_score') >= A('T-c', primary) and A('test_weak_e0', 'min_score') < 0.9,
                 P5=ranking[0] in ('goal_margin', 'ticks_decision'), P6=True)
    local = {k: 'supported' if v else 'falsified' for k, v in local.items()}
    reading = ('SLOWDOWN_NOT_A_SIGNAL' if local['P1'] != 'supported' else 'SLOWDOWN_ADDS_INFORMATION' if A('test_all', primary) - best_baseline >= spec['decision_margin_auc'] else 'SLOWDOWN_REDUNDANT_HERE')
    recorded_verdicts = {k: v['verdict'] for k, v in analysis['summary']['predictions'].items()}
    out['verdicts'] = dict(local=local, recorded=recorded_verdicts, reading_local=reading, reading_recorded=analysis['summary']['reading'])
    check(local == recorded_verdicts and reading == analysis['summary']['reading'], 'verdicts and reading equal to the recording')

    # exploratory (not pre-registered)
    flag = lambda s: {(c['memory'], c['e0_tenths'], c['e1_tenths']) for c in test if c['signals'][s] >= thresholds[s]}
    tt = [c['signals']['ticks_total'] for c in test if c['target']]
    nn = sorted(c['signals']['ticks_total'] for c in test if not c['target'])
    out['exploratory'] = dict(ticks_total_and_min_score_flag_same_test_cells=flag('ticks_total') == flag('min_score'),
                              lowest_target_ticks_total=min(tt), highest_unflagged_non_target_ticks_total=max(x for x in nn if x < thresholds['ticks_total']),
                              target_goal_min_when_true=min(c['goal'] for c in test if c['target'] == 'capture'),
                              off_true_iff_e1_positive=all((v['value'] is True) == (k[1] > 0) for k, v in off.items()))
    out['failures'] = failures
    out['status'] = 'PASS' if not failures else 'FAIL'
    return out


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('--evidence', default=str(ROOT / 'evidence/slowdown-signal-20261120-r51'))
    a.add_argument('--write', metavar='NAME', help='write the report to NAME inside the evidence folder (must not exist)')
    args = a.parse_args()
    result = main(Path(args.evidence))
    text = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n'
    if args.write:
        with (Path(args.evidence) / args.write).open('x', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print(text)
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
