"""Second-path check of the R49 / EXP-95 analysis.

Does not import the R49 probe or the R33 kernel wrapper.  It rebuilds the reference intervals
from the individual R48 rows, re-settles every stored witness directly with hcr.dynamics.settle,
recounts containment from the value-space fields of the R48 batch records, and adds an
exploratory (not pre-registered) split of every excursion by direction.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
RAW = ROOT / 'evidence/joint-tuple-codebook-transfer-20261023-r48/raw'
SPEC = ROOT / 'experiments/exp-94-joint-tuple-codebook-transfer/frozen_spec.json'
EXP = ROOT / 'experiments/exp-95-envelope-interior'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(ok, message, failures):
    if not ok:
        failures.append(message)


def span(values):
    return [min(values), max(values)]


def rebuilt_boxes(transfer):
    """Intervals from the rows themselves, ignoring the stored *_bounds summaries."""
    pair = {b: span([r['goal'] for r in transfer['pair_transfer'] if r['expected'] is b]) for b in [False, True]}
    member = {b: span([r['goal'] for r in transfer['or_transfer'] if r['expected'] is b]) for b in [False, True]}
    proj = {b: span([v for r in transfer['projection_envelope'] for x, v in zip(r['expected_e'], r['e_out']) if x is b]) for b in [False, True]}
    elig = {b: span([v for r in transfer['feasible_envelope'] for x, v in zip(r['e_bool'], r['eligibility']) if x is b]) for b in [False, True]}
    cov = {b: span([r['coverage_activation'] for r in transfer['feasible_envelope'] if r['complete_bool'] is b]) for b in [False, True]}
    return dict(pair=pair, membership=member, projection=proj, eligibility=elig, coverage=cov)


def signed(value, boxes, low, high):
    """Classify value by threshold side, then return (class, harmful excess, benign excess).

    Harmful means beyond the interval end that faces the decision threshold.
    """
    truth = value >= high if value >= high or value <= low else None
    if truth is None:
        return None, None, None
    lo, hi = boxes[truth]
    toward = (lo - value) if truth else (value - hi)
    away = (value - hi) if truth else (lo - value)
    return truth, max(toward, 0.0), max(away, 0.0)


def resettle(doc, drives, config, initial):
    from hcr.dynamics import settle
    from hcr.model import Cost, Group, Link, Program
    program = Program(tuple(Group(**g) for g in doc['groups']), tuple(Link(**e) for e in doc['links']), tuple(tuple(p) for p in doc['paths']), doc['edge_count'])
    cost = Cost(dynamic_groups_created=len(program.groups), dynamic_links_created=len(program.links))
    state, convergence = settle(program, drives, config, cost, initial={g.id: initial for g in program.groups})
    return state, convergence, cost.kernel_ticks


def main(evidence):
    from hcr.model import Config
    failures = []
    analysis = read(evidence / 'analysis.json')
    p = read(SPEC)
    cfg = Config(**p['kernel'])
    gain = cfg.evidence_gain
    high = (1 + cfg.margin_threshold) / 2
    low = (1 - cfg.margin_threshold) / 2
    transfer = read(RAW / 'transfer.json')
    out = dict(schema='hcr-r49-envelope-interior-verification-v1', analysis_sha256=sha(evidence / 'analysis.json'), independent_auditor=False)

    check(analysis['design_sha256'] == sha(EXP / 'DESIGN.ko.md') and analysis['frozen_spec_sha256'] == sha(EXP / 'frozen_spec.json') and analysis['input_manifest_sha256'] == sha(EXP / 'input_manifest.json'), 'design/spec/manifest hashes bound to analysis', failures)
    check(analysis['smoke'] is False and analysis['new_native_settles'] == 102650, 'full run with declared settle count', failures)

    # 1. reference intervals rebuilt from rows
    boxes = rebuilt_boxes(transfer)
    same = {k: {str(b): boxes[k][b] for b in [False, True]} == analysis['reference_boxes'][k] for k in boxes}
    out['reference_boxes_rebuilt_equal'] = same
    check(all(same.values()), 'reference intervals rebuilt from R48 rows', failures)

    # 2. every stored witness re-settled through hcr.dynamics.settle
    drive = lambda v: gain * (2 * v - 1)
    witness = dict(checked=0, bitwise_equal=0, excess_equal=0)
    for name, stage in analysis['interior'].items():
        check(not stage['mismatches'], 'no stored semantic mismatch in ' + name, failures)
        for w in stage['witnesses']:
            if w['stage'] == 'projection':
                state, conv, ticks = resettle(p['programs']['projection' + str(w['order'])], {'f' + str(i): drive(v) for i, v in enumerate(w['f_in'])}, cfg, 0.5)
                got = [state['e' + str(i)] for i in range(4)]
                equal = got == w['e_out'] and ticks == w['ticks']
                excess = max(max(boxes['projection'][b][0] - v, v - boxes['projection'][b][1], 0.0) for b, v in zip(w['expected_e'], got))
            elif w['stage'] == 'feasible':
                drives = {'e' + str(i): drive(v) for i, v in enumerate(w['e_in'])}
                drives['complete'] = gain * (1 if w['complete'] else -1)
                state, conv, ticks = resettle(p['programs']['feasible'], drives, cfg, 0.5)
                got = [state['e' + str(i)] for i in range(4)]
                equal = got == w['eligibility'] and state['complete'] == w['coverage_activation'] and ticks == w['ticks']
                parts = [max(boxes['eligibility'][b][0] - v, v - boxes['eligibility'][b][1], 0.0) for b, v in zip(w['e_bool'], got)]
                parts.append(max(boxes['coverage'][w['complete']][0] - state['complete'], state['complete'] - boxes['coverage'][w['complete']][1], 0.0))
                excess = max(parts)
            else:
                failures.append('unexpected witness stage ' + w['stage'])
                continue
            witness['checked'] += 1
            witness['bitwise_equal'] += int(equal)
            witness['excess_equal'] += int(excess == w['max_excess'] and excess > 0)
    out['witness_replay'] = witness
    check(witness['checked'] > 0 and witness['checked'] == witness['bitwise_equal'] == witness['excess_equal'], 'all witnesses reproduce bitwise with the same positive excess', failures)

    # 3. containment recount from value-space fields of the 512 native batch records
    records = [r for i in range(12) for r in read(RAW / ('batch%02d.json' % i)) if r['arm'] != 'exact_joint']
    check(len(records) == 512, '512 native records', failures)
    count = dict(messages_outside=0, projection_records=0, projection_records_outside=0, feasible_records_outside=0)
    direction = {k: dict(harmful_max=0.0, benign_max=0.0, harmful_values=0, benign_values=0, unclassified=0) for k in ['membership_messages', 'projection_outputs', 'feasible_eligibility', 'feasible_coverage']}

    def note(key, value, family):
        truth, toward, away = signed(value, boxes[family], low, high)
        d = direction[key]
        if truth is None:
            d['unclassified'] += 1
            return True
        d['harmful_max'] = max(d['harmful_max'], toward)
        d['benign_max'] = max(d['benign_max'], away)
        d['harmful_values'] += int(toward > 0)
        d['benign_values'] += int(away > 0)
        return toward > 0 or away > 0

    for r in records:
        count['messages_outside'] += int(any([note('membership_messages', v, 'membership') for v in r['messages']]))
        if r['arm'] == 'native_marginal':
            count['projection_records'] += 1
            count['projection_records_outside'] += int(any([note('projection_outputs', v, 'projection') for v in r['applied']]))
        outside = any([note('feasible_eligibility', v, 'eligibility') for v in r['binding']['eligibility']])
        outside = note('feasible_coverage', r['binding']['coverage_activation'], 'coverage') or outside
        count['feasible_records_outside'] += int(outside)
    stages = analysis['containment']['stages']
    out['containment_recount'] = count
    out['containment_direction_exploratory'] = direction
    check(count['messages_outside'] == 0 == stages['or']['outputs_outside'], 'membership outputs inside in both counts', failures)
    check(count['projection_records'] == stages['projection']['references'] and count['projection_records_outside'] == stages['projection']['references_with_output_outside'], 'projection output recount equals trace-based count', failures)
    check(count['feasible_records_outside'] == stages['feasible']['references_with_output_outside'], 'feasible output recount equals trace-based count', failures)
    check(all(d['unclassified'] == 0 for d in direction.values()), 'every pipeline value classifiable by threshold side', failures)

    # 4. exploratory direction split of the interior-point ranges (envelope arm)
    interior = {}
    for name, family_of in [('or/envelope', dict(goal='membership')), ('projection/envelope', dict(e='projection')), ('feasible/envelope', dict(e='eligibility', complete='coverage'))]:
        ranges = analysis['interior'][name]['observed_output_ranges']
        row = {}
        for key, (lo_seen, hi_seen) in ranges.items():
            label, cls = key.rsplit('_', 1)
            truth = cls == 'true'
            lo, hi = boxes[family_of[label]][truth]
            row[key] = dict(harmful=max((lo - lo_seen) if truth else (hi_seen - hi), 0.0), benign=max((hi_seen - hi) if truth else (lo - lo_seen), 0.0))
        interior[name] = row
    out['interior_direction_exploratory'] = interior
    out['min_decision_slack'] = {name: s['min_decision_slack'] for name, s in analysis['interior'].items()}
    worst_harmful = max([v['harmful'] for row in interior.values() for v in row.values()] + [d['harmful_max'] for d in direction.values()])
    out['largest_harmful_excess_anywhere'] = worst_harmful
    out['smallest_decision_slack_anywhere'] = min(out['min_decision_slack'].values())
    out['slack_to_harmful_excess_ratio'] = out['smallest_decision_slack_anywhere'] / worst_harmful if worst_harmful > 0 else None

    out['failures'] = failures
    out['status'] = 'PASS' if not failures else 'FAIL'
    return out


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--evidence', default=str(ROOT / 'evidence/envelope-interior-20261120-r49'))
    a.add_argument('--write', action='store_true', help='write verification.json next to analysis.json (must not exist)')
    args = a.parse_args()
    result = main(Path(args.evidence))
    text = json.dumps(result, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n'
    if args.write:
        with (Path(args.evidence) / 'verification.json').open('x', encoding='utf-8', newline='\n') as f:
            f.write(text)
    print(text)
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
