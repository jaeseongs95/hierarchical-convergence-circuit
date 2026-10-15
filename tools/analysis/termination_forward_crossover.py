"""고정 C0/C1 교차 대조. 원본 수치·정책·Job을 보존하고 수동 계측만 추가한다."""
from __future__ import annotations
import argparse
import ctypes
import gc
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import termination_compare_core as core
import termination_compare_runner as runner
import termination_certificate_cost as cost

SELF = Path(__file__).resolve()
ROOT = SELF.parents[2]
CONTRACT = ROOT / 'evidence/forward-crossover-20261015-r12/execution-contract.json'
ORIGINAL = core.Arithmetic


def host_times():
    """GetSystemTimes: kernel includes idle; aggregate, not per-core availability."""
    values = [ctypes.c_ulonglong() for _ in range(3)]
    ok = ctypes.windll.kernel32.GetSystemTimes(*(ctypes.byref(v) for v in values))
    return dict(zip(('idle_100ns', 'kernel_including_idle_100ns', 'user_100ns'),
                    (v.value for v in values))) if ok else None


def clock_inventory():
    return {name: vars(time.get_clock_info(name)) for name in
            ('monotonic', 'perf_counter', 'process_time', 'thread_time')}


def paired_effects(rows):
    """Adjacent pairs have opposite order. Positive C1-C0 means slower."""
    effects = []
    for pair in (rows[:2], rows[2:]):
        if len(pair) != 2 or {r['variant'] for r in pair} != {'C0', 'C1'}:
            raise ValueError('crossed adjacent pair')
        if any(r['status'] != 'COMPLETE' for r in pair):
            effects.append(None)
        else:
            by = {r['variant']: r for r in pair}
            effects.append(by['C1']['policy_supervision']['highres_wall_seconds'] -
                           by['C0']['policy_supervision']['highres_wall_seconds'])
    return {'C1_minus_C0_seconds': effects,
            'mean_seconds': sum(effects)/2 if all(x is not None for x in effects) else None,
            'planned_pairs': 2, 'all_four_complete': all(r['status'] == 'COMPLETE' for r in rows)}


class Observer:
    """QPC primary; legacy clock reads bracket the identical callback body.

    Parent phases are disjoint. Numeric and GC spans are nested and never added
    to their parent. Callback CPU sums are diagnostic, not independent CPU truth.
    """
    def __init__(self, out, clocks=None, host=host_times):
        self.out = Path(out)
        self.qpc, self.legacy, self.cpu = clocks or (
            time.perf_counter_ns, time.monotonic_ns, time.process_time_ns)
        self.host = host
        self.rows, self.nested, self.stack = {}, {}, []
        self.gc_rows, self.gc_pending = {}, {}
        self.tick = 0
        self.state_hash = None
        self.block_start_tick = 0
        self.block_input_hash = None
        self.block_start_qpc, self.block_start_cpu = self.qpc(), self.cpu()
        self.host_start = self.host()
        self.prior_totals = {}
        self.block_count = 0
        self.arithmetic = None
        self.gc_before = {'enabled': gc.isenabled(), 'threshold': list(gc.get_threshold())}

    def call(self, name, fn, *args, **kwargs):
        if name == 'advance' and self.tick and self.tick % 128 == 0:
            self.boundary()
        q0 = self.qpc(); m0 = self.legacy(); c0 = self.cpu(); qbody = self.qpc()
        self.stack.append(name)
        completed = False
        try:
            value = fn(*args, **kwargs)
            completed = True
            return value
        finally:
            qend = self.qpc(); c1 = self.cpu(); m1 = self.legacy(); q1 = self.qpc()
            self.stack.pop()
            target = self.nested if name == 'numeric_advance' else self.rows
            row = target.setdefault(name, dict(calls=0, completed=0, wall_seconds=0.,
                cpu_seconds=0., legacy_wall_seconds=0., clock_bracket_seconds=0.))
            row['calls'] += 1; row['completed'] += int(completed)
            row['wall_seconds'] += (qend-qbody)/1e9
            row['legacy_wall_seconds'] += (m1-m0)/1e9
            row['cpu_seconds'] += (c1-c0)/1e9
            row['clock_bracket_seconds'] += ((q1-q0)-(qend-qbody))/1e9

    def gc_callback(self, phase, info):
        generation = info['generation']
        if phase == 'start':
            self.gc_pending[generation] = (self.qpc(), self.stack[-1] if self.stack else 'outside')
        elif generation in self.gc_pending:
            start, owner = self.gc_pending.pop(generation)
            elapsed = self.qpc()-start
            key = f'{owner}/generation-{generation}'
            row = self.gc_rows.setdefault(key, dict(calls=0, wall_seconds=0., collected=0, uncollectable=0))
            row['calls'] += 1; row['wall_seconds'] += elapsed/1e9
            row['collected'] += info['collected']; row['uncollectable'] += info['uncollectable']

    def totals(self):
        return {'phases': self.rows, 'nested': self.nested, 'gc_nested': self.gc_rows}

    def boundary(self, final=False):
        if self.state_hash is None or (self.tick == self.block_start_tick and not final):
            return
        now, cpu, host = self.qpc(), self.cpu(), self.host()
        totals = core.decode(core.canonical(self.totals()))
        delta = {}
        for group, entries in totals.items():
            delta[group] = {name: {key: value-self.prior_totals.get(group, {}).get(name, {}).get(key, 0)
                                  for key, value in values.items()} for name, values in entries.items()}
        self.block_count += 1
        runner.write_new(self.out/f'block-{self.block_count:04d}.json', {
            'tick_start_exclusive': self.block_start_tick, 'tick_end_inclusive': self.tick,
            'boundary': 'before next step, after preceding cadence certificate; final after final output',
            'start_qpc_ns': self.block_start_qpc, 'end_qpc_ns': now,
            'wall_seconds': (now-self.block_start_qpc)/1e9,
            'single_difference_process_cpu_seconds': (cpu-self.block_start_cpu)/1e9,
            'input_state_digest': self.block_input_hash, 'output_state_digest': self.state_hash,
            'host_start': self.host_start, 'host_end': host, 'cumulative': totals, 'delta': delta,
            'counts': dict(self.arithmetic.meter.counts) if self.arithmetic else None,
            'parent_child_gc_overlap_do_not_sum': True, 'observer_cost_in_policy_budget': True})
        self.block_start_tick, self.block_input_hash = self.tick, self.state_hash
        self.block_start_qpc, self.block_start_cpu, self.host_start = now, cpu, host
        self.prior_totals = totals


def policy(input_path, input_sha, variant, release):
    observer = Observer(release['out'])
    old_timings, old_base, old_commit = cost.Timings, cost.BASE_ARITHMETIC, runner.commit_state

    class Instrumented(ORIGINAL):
        def __init__(self, *args):
            super().__init__(*args)
            original_advance = self.advance
            self.advance = lambda *a: observer.call('numeric_advance', original_advance, *a)
            observer.arithmetic = self

    def committed(out, snapshot, meter):
        result = old_commit(out, snapshot, meter)
        observer.tick, observer.state_hash = snapshot['tick'], core.digest(snapshot['current_x_box'])
        if snapshot['tick'] == 0: observer.block_input_hash = observer.state_hash
        return result

    cost.Timings, cost.BASE_ARITHMETIC, runner.commit_state = lambda: observer, Instrumented, committed
    gc.callbacks.append(observer.gc_callback)
    try:
        cost.policy(input_path, input_sha, variant, release)
        if observer.arithmetic: observer.arithmetic.meter.guard()
        observer.boundary(final=True)
        after = {'enabled': gc.isenabled(), 'threshold': list(gc.get_threshold())}
        if after != observer.gc_before: raise ValueError('GC settings changed')
        runner.write_new(Path(release['out'])/'trace.json', {
            'schema': 'HCCForwardTrace.v1', 'clocks': clock_inventory(),
            'gc_before': observer.gc_before, 'gc_after': after, 'gc_pending': observer.gc_pending,
            'blocks': observer.block_count, **observer.totals(),
            'parent_phases_disjoint': True, 'numeric_and_gc_nested_do_not_sum': True,
            'callback_cpu_resolution_limited': True,
            'phase_clock_brackets_include_nested_instrumentation': True,
            'trace_final_serialization_not_in_phase_totals_but_in_policy_wholecost': True})
        if observer.arithmetic: observer.arithmetic.meter.guard()
    finally:
        gc.callbacks.remove(observer.gc_callback)
        cost.Timings, cost.BASE_ARITHMETIC = old_timings, old_base
        core.Arithmetic, runner.commit_state = ORIGINAL, old_commit


def contract():
    raw = CONTRACT.read_bytes(); data = core.decode(raw)
    for ref in data['code_pins']:
        runner.load_verified(ROOT, ref)
    if sorted(data['sequential_order']) != ['C0', 'C0', 'C1', 'C1']:
        raise ValueError('four planned cells')
    if data['sequential_order'][0] != data['sequential_order'][3] or data['sequential_order'][1] != data['sequential_order'][2]:
        raise ValueError('ABBA/BAAB only')
    return data, hashlib.sha256(raw).hexdigest()


def owned(command, out, cap, deadline, cleanup_end, factory=runner.Job):
    q0 = time.perf_counter_ns()
    result = runner.owned_phase(command, out, cap, deadline, cleanup_end, factory)
    q1 = time.perf_counter_ns()
    result = dict(result, highres_start_ns=q0, highres_end_ns=q1,
                  highres_wall_seconds=(q1-q0)/1e9)
    runner.write_new(Path(out)/'highres-supervision.json', result)
    return result


def study(out, outer_deadline):
    cfg, _ = contract(); out = Path(out); out.mkdir(exist_ok=False)
    start, qstart = time.monotonic(), time.perf_counter_ns()
    deadline = min(start+6900, outer_deadline)
    setup_command = [sys.executable, '-B', '-X', 'utf8', str(ROOT/'tools/analysis/termination_compare_runner.py'),
        '--worker', 'setup', '--plan-sha', cfg['plan_sha256'], '--implementation-sha', cfg['implementation_sha256']]
    setup = owned(setup_command, out/'setup', 20, deadline, min(start+30, deadline))
    if setup['status'] != 'COMPLETE' or setup['active_processes'] != 0:
        raise ValueError('setup incomplete')
    input_path = out/'setup/public-input.json'; raw = input_path.read_bytes()
    input_sha = hashlib.sha256(raw).hexdigest(); data = core.decode(raw)
    plan = core.decode((ROOT/runner.PLAN).read_bytes())
    rows = [dict(cell_id=f'{i+1:02d}-{v}', period=i+1, variant=v, status='NOT_RUN',
                 policy_cap_seconds=1575) for i, v in enumerate(cfg['sequential_order'])]
    for row in rows:
        cell_start = time.monotonic(); cell_qstart = time.perf_counter_ns()
        # No recycling unused reservations. Every new cell gets exactly the same cap.
        if deadline-cell_start < 1595+450:
            row['not_run_reason'] = 'insufficient remaining full reservation'; continue
        child = out/row['cell_id']; cell_end = min(cell_start+1595, deadline)
        command = [sys.executable, '-B', '-X', 'utf8', str(SELF), '--worker', 'policy',
            '--input', str(input_path), '--input-sha', input_sha, '--variant', row['variant']]
        supervision = owned(command, child, 1575, deadline, min(cell_start+1585, deadline))
        last = runner.last_snapshot(child, supervision)
        final_path = child/'final.json'
        final = core.decode(final_path.read_bytes()) if supervision['status'] == 'COMPLETE' and final_path.exists() else None
        row.update(policy_supervision=supervision, status=supervision['status'])
        if supervision['status'] == 'COMPLETE' and (final is None or not (child/'trace.json').exists() or not (child/'timings.json').exists()):
            row['status'] = 'MEASUREMENT_FAILURE'
        sealed = dict(schema='HCCTerminationSealedCell.v1', input_sha256=input_sha,
            model_digest=data['model_digest'], observation_digest=data['observation_digest'],
            processed_digest=data['processed_digest'], supervision=supervision,
            last_complete=last, final=final,
            counters_scope='last committed lower bound if interrupted; uncommitted work unknown')
        sealed_path = child/'sealed-cell.json'; runner.write_new(sealed_path, sealed)
        request = child/'evaluation-input.json'
        runner.write_new(request, dict(schema='HCCTerminationEvaluationInput.v1', repo=str(ROOT),
            policy_seal=dict(path=str(sealed_path), sha256=hashlib.sha256(sealed_path.read_bytes()).hexdigest()),
            public_input=dict(path=str(input_path), sha256=input_sha),
            world=dict(path=str(out/'setup/world.json'), sha256=hashlib.sha256((out/'setup/world.json').read_bytes()).hexdigest()),
            distance_reference=next(r for r in plan['source_pins'] if 'on-fixed-point-distance-entry-certificates' in r['path'])))
        # Shared cell reservation =1575 policy +10 evaluator +10 cleanup/sealing.
        used_cleanup = (time.monotonic()-cell_start-supervision['wall_seconds_after_report']
                        + max(0, supervision['wall_seconds_after_report']-1575))
        if supervision.get('active_processes') == 0 and used_cleanup < 10 and time.monotonic()+10 < cell_end:
            command = [sys.executable, '-B', '-X', 'utf8', str(ROOT/'tools/analysis/termination_compare_runner.py'),
                '--worker', 'evaluation', '--input', str(request), '--input-sha', hashlib.sha256(request.read_bytes()).hexdigest()]
            evaluation_end = min(cell_end, time.monotonic()+10+max(0, 10-used_cleanup))
            e = owned(command, child/'evaluation', 10, deadline, evaluation_end)
            row['evaluation_supervision'] = e
            result = child/'evaluation/result.json'
            row['evaluation'] = core.decode(result.read_bytes()) if e['status'] == 'COMPLETE' and result.exists() else None
        row['cleanup_before_evaluation_seconds'] = used_cleanup
        row['cell_highres_wall_seconds'] = (time.perf_counter_ns()-cell_qstart)/1e9
        runner.write_new(child/'row.json', row)
        if time.monotonic() > cell_end: raise core.BudgetStop('cell reservation exceeded')
    runner.write_new(out/'cells-sealed.json', dict(rows=rows, setup_supervision=setup, global_deadline=deadline))
    command = [sys.executable, '-B', '-X', 'utf8', str(SELF.with_name('test_forward_crossover.py')), '--verify-study', str(out)]
    verification = owned(command, out/'verification', 450, deadline, deadline)
    runner.write_new(out/'summary.json', dict(rows=rows, verification_supervision=verification,
        setup_supervision=setup, study_highres_wall_seconds=(time.perf_counter_ns()-qstart)/1e9,
        global_cap_seconds=6900, global_exceeded=time.monotonic()>deadline,
        scientific_retries=0, independent_discovery_samples=0, order=cfg['sequential_order'],
        paired_policy_cost=paired_effects(rows), unused_budget_reallocated=False))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true'); p.add_argument('--execute', action='store_true')
    p.add_argument('--study', action='store_true'); p.add_argument('--worker', choices=['policy'])
    p.add_argument('--output'); p.add_argument('--input'); p.add_argument('--input-sha')
    p.add_argument('--variant', choices=['C0', 'C1']); p.add_argument('--deadline', type=float)
    args = p.parse_args()
    if args.worker:
        contract(); policy(args.input, args.input_sha, args.variant, core.decode(sys.stdin.buffer.readline()))
    elif args.self_test:
        subprocess.run([sys.executable, '-B', '-X', 'utf8', str(SELF.with_name('test_forward_crossover.py'))], check=True)
    elif args.study:
        study(args.output, args.deadline)
    elif args.execute and args.output:
        _, sha = contract(); out = Path(args.output).resolve(); out.mkdir(exist_ok=False)
        start, qstart = time.monotonic(), time.perf_counter_ns(); deadline = start+6900
        command = [sys.executable, '-B', '-X', 'utf8', str(SELF), '--study', '--output', str(out/'study'), '--deadline', str(deadline)]
        runner.write_new(out/'execution-start.json', dict(contract_sha256=sha, argv=command,
            start_monotonic=start, deadline_monotonic=deadline, retry=False))
        result = owned(command, out/'watchdog', max(.001, deadline-time.monotonic()), deadline, deadline, cost.KillOnlyJob)
        runner.write_new(out/'execution-end.json', dict(supervision=result,
            physical_highres_wall_seconds=(time.perf_counter_ns()-qstart)/1e9,
            cap_seconds=6900, exceeded=time.monotonic()>deadline,
            outer_cpu_overlaps_inner_do_not_sum=True, outer_stdin_release_written_not_consumed=True))
        print(json.dumps(dict(status=result['status'], active_processes=result['active_processes'],
                              wall_seconds=result['highres_wall_seconds'])), flush=True)
    else:
        p.error('explicit --self-test or --execute --output required')


if __name__ == '__main__': main()
