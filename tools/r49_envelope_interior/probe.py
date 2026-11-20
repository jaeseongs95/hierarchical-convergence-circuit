"""R49 / EXP-95: containment and interior-point test of the R48 six-stage corner envelopes.

Reads the sealed R48 server raw as reference, never writes into it, and leaves the engine and
the R48 tools unchanged.  Design and decision rules: experiments/exp-95-envelope-interior/DESIGN.ko.md
"""
import argparse
import hashlib
import itertools
import json
import platform
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
EXP = ROOT / 'experiments/exp-95-envelope-interior'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def strip_ids(value):
    """Drop recorder-assigned network ids so that only computed values are compared."""
    if isinstance(value, dict):
        return {k: strip_ids(v) for k, v in value.items() if k != 'network_id'}
    if isinstance(value, list):
        return [strip_ids(v) for v in value]
    return value


class Stream:
    """Order-sensitive digest of every evaluated row; rows themselves are not stored."""

    def __init__(self):
        self.h = hashlib.sha256()
        self.rows = 0

    def add(self, row):
        self.h.update((json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode())
        self.rows += 1


class Box:
    """Closed value interval of one Boolean class."""

    def __init__(self, lo, hi):
        require(lo <= hi, 'ordered interval')
        self.lo, self.hi = lo, hi

    def excess(self, v):
        return self.lo - v if v < self.lo else v - self.hi if v > self.hi else 0.0

    def level(self, name):
        return self.lo if name == 'lo' else self.hi if name == 'hi' else (self.lo + self.hi) / 2

    def inflate(self, delta):
        return Box(max(0.0, self.lo - delta), min(1.0, self.hi + delta))

    def plain(self):
        return [self.lo, self.hi]


def boxes(transfer):
    pb, mb, jb, eb = (transfer[k] for k in ['pair_bounds', 'membership_bounds', 'projection_bounds', 'eligibility_bounds'])
    return dict(
        pair={False: Box(pb['false_min'], pb['false_max']), True: Box(pb['true_val'], pb['true_val'])},
        membership={False: Box(mb['false_min'], mb['false_max']), True: Box(mb['true_min'], mb['true_max'])},
        projection={False: Box(jb['false_min'], jb['false_max']), True: Box(jb['true_min'], jb['true_max'])},
        eligibility={False: Box(eb['false_min'], eb['false_max']), True: Box(eb['true_min'], eb['true_max'])},
        coverage={False: Box(eb['cov_false_min'], eb['cov_false_max']), True: Box(eb['cov_true_min'], eb['cov_true_max'])})


class Tally:
    """Per-stage counters, worst decision slack, envelope excursions and capped witnesses."""

    def __init__(self, cap):
        self.cap = cap
        self.settles = 0
        self.semantic_mismatch = 0
        self.outputs = 0
        self.outside = 0
        self.rows_outside = 0
        self.max_excess = 0.0
        self.min_slack = None
        self.ticks = [None, None]
        self.status = {}
        self.witnesses = []
        self.mismatches = []
        self.observed = {}

    def tick(self, k):
        t = k['cost']['kernel_ticks']
        self.settles += 1
        self.ticks = [t if self.ticks[0] is None else min(self.ticks[0], t), t if self.ticks[1] is None else max(self.ticks[1], t)]
        s = k['convergence']['status']
        self.status[s] = self.status.get(s, 0) + 1

    def slack(self, value, truth, hi, lo):
        s = value - hi if truth else lo - value
        self.min_slack = s if self.min_slack is None else min(self.min_slack, s)

    def observe(self, name, truth, value):
        key = name + ('_true' if truth else '_false')
        cur = self.observed.get(key)
        self.observed[key] = [value, value] if cur is None else [min(cur[0], value), max(cur[1], value)]

    def mismatch(self, row):
        self.semantic_mismatch += 1
        if len(self.mismatches) < self.cap:
            self.mismatches.append(row)

    def excursion(self, row, excesses):
        self.outputs += len(excesses)
        bad = [e for e in excesses if e > 0]
        if not bad:
            return
        self.outside += len(bad)
        self.rows_outside += 1
        worst = max(bad)
        self.max_excess = max(self.max_excess, worst)
        self.witnesses.append(dict(row, max_excess=worst))
        self.witnesses.sort(key=lambda r: -r['max_excess'])
        del self.witnesses[self.cap:]

    def plain(self):
        return dict(settles=self.settles, semantic_mismatch=self.semantic_mismatch, mismatches=self.mismatches,
                    outputs_checked=self.outputs, outputs_outside_envelope=self.outside, rows_outside_envelope=self.rows_outside,
                    max_excess=self.max_excess, min_decision_slack=self.min_slack, ticks_range=self.ticks, status=self.status,
                    observed_output_ranges=self.observed, witnesses=self.witnesses)


def control(p, cfg, kernel, onehot, raw):
    import tools.r48_joint_tuple_codebook_transfer.probe as r48
    counter = itertools.count()
    role, transfer = r48.run_stage_transfer(p, cfg, kernel, onehot, lambda k: 'local%05d' % next(counter))
    calls = next(counter)
    local = json.loads(json.dumps(dict(roles=strip_ids(role), transfer=strip_ids(transfer)), allow_nan=False))
    server = dict(roles=strip_ids(read(raw / 'roles.json')), transfer=strip_ids(read(raw / 'transfer.json')))
    parts = {name: local['transfer'][name] == server['transfer'][name] for name in server['transfer']}
    parts['roles'] = local['roles'] == server['roles']
    return dict(settles=calls, exact_equal=all(parts.values()) and set(local['transfer']) == set(server['transfer']), parts=parts)


def containment(p, cfg, raw, bx):
    gain = cfg.evidence_gain
    drive = lambda v: gain * (2 * v - 1)
    reps = [drive(v) for v in read(raw / 'transfer.json')['role_representatives'].values()]
    refs = {}
    for i in range(12):
        for record in read(raw / ('batch%02d.json' % i)):
            for nid in record['network_ids']:
                refs[nid] = refs.get(nid, 0) + 1
    ids = {key: [g['id'] for g in doc['groups']] for key, doc in p['programs'].items()}

    def gap(d, choices):
        """Distance in value units from drive d to the nearest allowed drive interval."""
        return min((drive(b.lo) - d if d < drive(b.lo) else d - drive(b.hi) if d > drive(b.hi) else 0.0) for b in choices) / (2 * gain)

    stages = {}
    for nid in sorted(refs):
        doc = read(raw / (nid + '.json'))
        key = doc['program_key']
        stage = 'or' if key.startswith('or') else 'projection' if key.startswith('projection') else key
        state = dict(zip(ids[key], doc['final_vector'], strict=True))
        d = doc['drives']
        ins, outs = [], []
        if stage == 'role':
            pass
        elif stage == 'pair':
            ins = [min(abs(d[m] - r) for r in reps) / (2 * gain) for m in ['m0', 'm1']] + [abs(d['m2'] + gain) / (2 * gain)]
            outs = [min(b.excess(state['goal']) for b in bx['pair'].values())]
        elif stage == 'or':
            ins = [gap(v, bx['pair'].values()) for v in d.values()]
            outs = [min(b.excess(state['goal']) for b in bx['membership'].values())]
        elif stage == 'projection':
            ins = [gap(v, bx['membership'].values()) for v in d.values()]
            outs = [min(b.excess(state['e' + str(i)]) for b in bx['projection'].values()) for i in range(4)]
        elif stage == 'feasible':
            allowed = [*bx['membership'].values(), *bx['projection'].values()]
            ins = [gap(d['e' + str(i)], allowed) for i in range(4)] + [abs(d['complete'] - gain) / (2 * gain)]
            outs = [min(b.excess(state['e' + str(i)]) for b in bx['eligibility'].values()) for i in range(4)] + [bx['coverage'][True].excess(state['complete'])]
        elif stage == 'query':
            ins = [gap(d['e' + str(i)], bx['eligibility'].values()) for i in range(4)] + [gap(d['t' + str(i)], bx['membership'].values()) for i in range(4)] + [gap(d['complete'], bx['coverage'].values())]
        else:
            raise ValueError('unexpected program key ' + key)
        s = stages.setdefault(stage, dict(unique_traces=0, references=0, inputs_checked=0, inputs_outside=0, traces_with_input_outside=0,
                                          references_with_input_outside=0, max_input_excess=0.0, outputs_checked=0, outputs_outside=0,
                                          traces_with_output_outside=0, references_with_output_outside=0, max_output_excess=0.0, worst_input_trace=None, worst_output_trace=None))
        s['unique_traces'] += 1
        s['references'] += refs[nid]
        for kind, values in [('input', ins), ('output', outs)]:
            bad = [v for v in values if v > 0]
            s[kind + 's_checked'] += len(values)
            s[kind + 's_outside'] += len(bad)
            if bad:
                s['traces_with_' + kind + '_outside'] += 1
                s['references_with_' + kind + '_outside'] += refs[nid]
                if max(bad) > s['max_' + kind + '_excess']:
                    s['max_' + kind + '_excess'] = max(bad)
                    s['worst_' + kind + '_trace'] = nid
    total_refs = sum(refs.values())
    return dict(referenced_unique_traces=len(refs), references=total_refs, stages=stages)


def run(out, smoke):
    from hcr.model import Config
    from hcr.tasks.toy_world import World
    from tools.r33_typed_feedback.runtime import kernel
    from tools.r34_feasible_state.runtime import onehot

    def forbidden(*a, **k):
        raise ValueError('R49 world measurement forbidden')
    World.measure = forbidden
    started = time.monotonic()
    cpu0 = time.process_time()
    spec = read(EXP / 'frozen_spec.json')
    pins = read(EXP / 'input_manifest.json')
    require(all(sha(ROOT / n) == h for n, h in pins.items()), 'input SHA pins')
    raw = ROOT / spec['reference']['raw']
    manifest = read(raw / 'manifest.json')
    for name in ['transfer.json', 'roles.json'] + ['batch%02d.json' % i for i in range(12)]:
        require(sha(raw / name) == manifest[name]['sha256'], 'reference raw matches server manifest: ' + name)
    p = read(ROOT / spec['reference']['spec'])
    cfg = Config(**p['kernel'])
    gain = cfg.evidence_gain
    hi = (1 + cfg.margin_threshold) / 2
    lo = (1 - cfg.margin_threshold) / 2
    initial = spec['initial']
    transfer = read(raw / 'transfer.json')
    bx = boxes(transfer)
    drive = lambda v: gain * (2 * v - 1)
    cap = spec['counterexample_cap_per_stage']
    levels = spec['levels']
    delta = spec['inflation_delta']
    result = dict(schema='hcr-r49-envelope-interior-analysis-v1', smoke=smoke,
                  design_sha256=sha(EXP / 'DESIGN.ko.md'), frozen_spec_sha256=sha(EXP / 'frozen_spec.json'), input_manifest_sha256=sha(EXP / 'input_manifest.json'),
                  thresholds=dict(high=hi, low=lo), reference_boxes={k: {str(b): v[b].plain() for b in v} for k, v in bx.items()})

    result['control'] = control(p, cfg, kernel, onehot, raw)
    result['containment'] = containment(p, cfg, raw, bx)

    stream = Stream()
    stages = {}

    # B1: exhaustive or0..4 over the 16 actual pair outputs of the server table.
    pair_values = [(row['goal'], row['expected']) for row in transfer['pair_transfer']]
    require(len(pair_values) == 16 and sum(b for _, b in pair_values) == 1, '16 pair outputs with one true')
    t = stages['or/envelope'] = Tally(cap)
    for L in range(2 if smoke else 5):
        doc = p['programs']['or' + str(L)]
        for combo in itertools.product(range(16), repeat=L):
            vals = [pair_values[i][0] for i in combo]
            expected = any(pair_values[i][1] for i in combo)
            k = kernel(doc, {'m' + str(i): drive(v) for i, v in enumerate(vals)}, cfg, initial)
            goal = k['state']['goal']
            t.tick(k)
            row = dict(stage='or', arity=L, pair_indices=list(combo), inputs=vals, expected=expected, goal=goal, ticks=k['cost']['kernel_ticks'], adopted=k['adopted'])
            stream.add(row)
            if k['adopted'] is not expected or k['convergence']['status'] != 'stable_decision' or not (goal >= hi if expected else goal <= lo):
                t.mismatch(row)
            t.slack(goal, expected, hi, lo)
            t.observe('goal', expected, goal)
            t.excursion(row, [bx['membership'][expected].excess(goal)])

    grid4 = list(itertools.product(levels, repeat=4))
    arms = [('envelope', lambda b: b), ('inflated', lambda b: b.inflate(delta))]

    # B2: projection0/1 interior grid.
    proj_expected = {(r['order'], tuple(r['f_bool'])): r['expected_e'] for r in transfer['projection_envelope']}
    require(len(proj_expected) == 32, '32 projection reference rows')
    for arm, shape in arms:
        t = stages['projection/' + arm] = Tally(cap)
        inbox = {b: shape(bx['membership'][b]) for b in [False, True]}
        for (order, f_bool), exp_e in sorted(proj_expected.items())[:1 if smoke else None]:
            doc = p['programs']['projection' + str(order)]
            for lv in grid4:
                f_in = [inbox[b].level(n) for b, n in zip(f_bool, lv, strict=True)]
                k = kernel(doc, {'f' + str(i): drive(v) for i, v in enumerate(f_in)}, cfg, initial)
                e = [k['state']['e' + str(i)] for i in range(4)]
                t.tick(k)
                row = dict(stage='projection', arm=arm, order=order, f_bool=list(f_bool), levels=list(lv), f_in=f_in, expected_e=exp_e, e_out=e, ticks=k['cost']['kernel_ticks'])
                stream.add(row)
                if k['convergence']['status'] not in ['stable_decision', 'stable_ambiguous'] or any(not (v >= hi if b else v <= lo) for b, v in zip(exp_e, e, strict=True)):
                    t.mismatch(row)
                for b, v in zip(exp_e, e, strict=True):
                    t.slack(v, b, hi, lo)
                    t.observe('e', b, v)
                if arm == 'envelope':
                    t.excursion(row, [bx['projection'][b].excess(v) for b, v in zip(exp_e, e, strict=True)])

    # B3: feasible4 interior grid for both input sources; complete stays at +-gain as in R48.
    feas_expected = {(r['source_kind'], tuple(r['e_bool']), r['complete_bool']): r['kind'] for r in transfer['feasible_envelope']}
    require(len(feas_expected) == 64, '64 feasible reference rows')
    source_box = dict(direct_or='membership', via_projection='projection')
    for arm, shape in arms:
        t = stages['feasible/' + arm] = Tally(cap)
        for (source, e_bool, complete), kind in sorted(feas_expected.items())[:1 if smoke else None]:
            inbox = {b: shape(bx[source_box[source]][b]) for b in [False, True]}
            for lv in grid4:
                e_in = [inbox[b].level(n) for b, n in zip(e_bool, lv, strict=True)]
                drives = {'e' + str(i): drive(v) for i, v in enumerate(e_in)}
                drives['complete'] = gain * (1 if complete else -1)
                k = kernel(p['programs']['feasible'], drives, cfg, initial)
                got = onehot(k, ['none', 'unique', 'many', 'incomplete'], cfg.margin_threshold)
                el = [k['state']['e' + str(i)] for i in range(4)]
                cov = k['state']['complete']
                t.tick(k)
                row = dict(stage='feasible', arm=arm, source=source, e_bool=list(e_bool), complete=complete, levels=list(lv), e_in=e_in, expected_kind=kind, kind=got, eligibility=el, coverage_activation=cov, ticks=k['cost']['kernel_ticks'])
                stream.add(row)
                if got != kind:
                    t.mismatch(row)
                for b, v in zip(e_bool, el, strict=True):
                    t.slack(v, b, hi, lo)
                    t.observe('e', b, v)
                t.slack(cov, complete, hi, lo)
                t.observe('complete', complete, cov)
                if arm == 'envelope':
                    t.excursion(row, [bx['eligibility'][b].excess(v) for b, v in zip(e_bool, el, strict=True)] + [bx['coverage'][complete].excess(cov)])

    # B4: query4, three fixed and thirteen seeded level assignments per Boolean pattern.
    query_expected = {(tuple(r['e_bool']), tuple(r['t_bool']), r['complete_bool']): r['tag'] for r in transfer['query_envelope']}
    require(len(query_expected) == 512, '512 query reference rows')
    labels = ['qtrue', 'qfalse', 'empty', 'mixed', 'incomplete']
    patterns = sorted(query_expected.items())
    for arm, shape in arms:
        t = stages['query/' + arm] = Tally(cap)
        eb = {b: shape(bx['eligibility'][b]) for b in [False, True]}
        mb = {b: shape(bx['membership'][b]) for b in [False, True]}
        cb = {b: shape(bx['coverage'][b]) for b in [False, True]}
        for index, ((e_bool, t_bool, complete), tag) in enumerate(patterns[:2 if smoke else None]):
            bools = [*e_bool, *t_bool, complete]
            rng = random.Random(spec['query_assignments']['seed_format'].format(pattern=index))
            assignments = [('r48_corner', ['lo' if b else 'hi' for b in bools]), ('all_mid', ['mid'] * 9), ('opposite_corner', ['hi' if b else 'lo' for b in bools])]
            assignments += [('random%02d' % j, [rng.choice(levels) for _ in range(9)]) for j in range(spec['query_assignments']['random_count'])]
            for name, lv in assignments:
                e_in = [eb[b].level(n) for b, n in zip(e_bool, lv[:4], strict=True)]
                t_in = [mb[b].level(n) for b, n in zip(t_bool, lv[4:8], strict=True)]
                c_in = cb[complete].level(lv[8])
                drives = {'e' + str(i): drive(v) for i, v in enumerate(e_in)}
                drives.update({'t' + str(i): drive(v) for i, v in enumerate(t_in)})
                drives['complete'] = drive(c_in)
                k = kernel(p['programs']['query'], drives, cfg, initial)
                got = onehot(k, labels, cfg.margin_threshold)
                label_state = {x: k['state'][x] for x in labels}
                t.tick(k)
                row = dict(stage='query', arm=arm, pattern=index, e_bool=list(e_bool), t_bool=list(t_bool), complete=complete, assignment=name, levels=lv, e_in=e_in, t_in=t_in, complete_in=c_in, expected_tag=tag, tag=got, label_state=label_state, ticks=k['cost']['kernel_ticks'])
                stream.add(row)
                if got != tag:
                    t.mismatch(row)
                for x, v in label_state.items():
                    t.slack(v, x == tag, hi, lo)

    result['interior'] = {name: t.plain() for name, t in stages.items()}
    result['row_stream'] = dict(rows=stream.rows, sha256=stream.h.hexdigest())
    result['new_native_settles'] = result['control']['settles'] + stream.rows
    result['learning'] = 0
    result['world_measurement'] = 0
    if not smoke:
        e = spec['expected_settles']
        require(result['control']['settles'] == e['control'] and stages['or/envelope'].settles == e['or_exhaustive'], 'control/or settle counts')
        require(all(stages[s + '/' + a].settles == e[s + '_per_arm'] for s in ['projection', 'feasible', 'query'] for a in spec['arms']), 'grid settle counts')
        require(result['new_native_settles'] == e['total'], 'declared total settles')

    # Verdicts exactly as fixed in DESIGN section 5.
    c = result['containment']['stages']
    covered = all(s['inputs_outside'] == 0 and s['outputs_outside'] == 0 for s in c.values())
    semantic = {name: 'PRESERVED' if t.semantic_mismatch == 0 else 'VIOLATED' for name, t in stages.items()}
    extremal = {name: 'NOT_REFUTED_IN_SAMPLE' if t.outside == 0 else 'REFUTED' for name, t in stages.items() if name.endswith('/envelope') and t.outputs}
    if not result['control']['exact_equal']:
        extremal = {name: 'CONTROL_FAILED' for name in extremal}
    result['verdict'] = dict(control='EXACT' if result['control']['exact_equal'] else 'CONTROL_FAILED', containment='COVERED' if covered else 'NOT_COVERED', semantic=semantic, extremal=extremal)
    result['environment'] = dict(python=sys.version, platform=platform.platform(), libc=list(platform.libc_ver()), machine=platform.machine(), processor=platform.processor())
    result['cost'] = dict(wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu0)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    with (out / 'analysis.json').open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=1, allow_nan=False) + '\n')
    print(json.dumps(dict(verdict=result['verdict'], rows=stream.rows, row_stream_sha256=result['row_stream']['sha256'], seconds=result['cost']['wall_seconds']), ensure_ascii=False))


if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--out', required=True, help='new output folder (must not exist)')
    a.add_argument('--smoke', action='store_true', help='tiny structural run for development; not evidence')
    args = a.parse_args()
    require(sys.version_info >= (3, 12), 'Python 3.12 required')
    run(args.out, args.smoke)
