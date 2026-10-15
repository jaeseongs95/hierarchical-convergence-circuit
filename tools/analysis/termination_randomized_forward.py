"""무작위 2블록 C0/C1 대조. 원 수치/Job을 재사용하고 수동 스레드 관측만 더한다."""
from __future__ import annotations
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import termination_forward_crossover as base

SELF = Path(__file__).resolve()
ROOT = SELF.parents[2]
CONTRACT = ROOT/'evidence/randomized-forward-20261015-r13/execution-contract.json'
BASE_OBSERVER, BASE_OWNED = base.Observer, base.owned
core, runner = base.core, base.runner


def assignment(seed_hex):
    seed = bytes.fromhex(seed_hex)
    if len(seed) != 32: raise ValueError('32-byte seed required')
    return [v for bit in (0, 1) for v in
            (['C1', 'C0'] if (seed[0] >> bit) & 1 else ['C0', 'C1'])]


def contract():
    raw = CONTRACT.read_bytes(); data = core.decode(raw)
    for ref in data['code_pins']: runner.load_verified(ROOT, ref)
    draw = runner.load_verified(ROOT, data['draw_pin'])
    draw = core.decode(draw)
    protocol = runner.load_verified(ROOT, data['randomization_protocol_pin'])
    if draw['protocol_sha256'] != hashlib.sha256(protocol).hexdigest():
        raise ValueError('draw protocol binding')
    if data['sequential_order'] != assignment(draw['seed_hex']):
        raise ValueError('random order binding')
    if draw['order'] != data['sequential_order']: raise ValueError('draw order')
    timing = core.decode(runner.load_verified(ROOT, data['draw_timing_pin']))
    if timing['draw_sha256'] != data['draw_pin']['sha256']: raise ValueError('draw timing binding')
    debit = (timing['after_draw_receipt_qpc_ns']-timing['before_entropy_qpc_ns'])/1e9
    if data['draw_debit_seconds'] != timing['debit_seconds'] or debit != timing['debit_seconds']:
        raise ValueError('draw debit binding')
    if data['code_pins'] != core.decode(protocol)['code_pins']: raise ValueError('predraw code binding')
    for pair in (data['sequential_order'][:2], data['sequential_order'][2:]):
        if sorted(pair) != ['C0', 'C1']: raise ValueError('blocked assignment')
    if not 0 <= data['draw_debit_seconds'] < 40: raise ValueError('draw debit reserve')
    return data, hashlib.sha256(raw).hexdigest()


def thread_snapshot():
    """Raw native accounting, not a frequency meter or an off-CPU trace."""
    q0 = time.perf_counter_ns()
    result = {'pid': __import__('os').getpid(), 'tid': __import__('threading').get_native_id()}
    try:
        dll = C.WinDLL('kernel32', use_last_error=True)
        for kind, handle in (('thread', -2), ('process', -1)):
            fn = getattr(dll, 'GetThreadTimes' if kind == 'thread' else 'GetProcessTimes')
            fn.argtypes = [C.c_void_p]+[C.POINTER(C.c_ulonglong)]*4
            fn.restype = C.c_int
            values = [C.c_ulonglong() for _ in range(4)]
            if fn(C.c_void_p(handle), *(C.byref(v) for v in values)):
                result[kind] = {'status': 'AVAILABLE', 'kernel_100ns': values[2].value,
                                'user_100ns': values[3].value}
            else: result[kind] = {'status': 'UNAVAILABLE', 'error': C.get_last_error()}
        fn = dll.QueryThreadCycleTime
        fn.argtypes = [C.c_void_p, C.POINTER(C.c_ulonglong)]; fn.restype = C.c_int
        cycles = C.c_ulonglong()
        result['cycles'] = ({'status': 'AVAILABLE', 'raw': cycles.value} if
            fn(C.c_void_p(-2), C.byref(cycles)) else
            {'status': 'UNAVAILABLE', 'error': C.get_last_error()})
        # Read after the API call above, rather than before its output is filled.
        if result['cycles']['status'] == 'AVAILABLE': result['cycles']['raw'] = cycles.value
    except (AttributeError, OSError) as exc:
        result['api_failure'] = {'status': 'UNAVAILABLE', 'type': type(exc).__name__}
    result.update(qpc_before_ns=q0, qpc_after_ns=time.perf_counter_ns())
    return result


def span(a, b):
    if (a['pid'], a['tid']) != (b['pid'], b['tid']): raise ValueError('thread lifetime')
    wall = (b['qpc_before_ns']-a['qpc_after_ns'])/1e9
    result = {'wall_seconds': wall,
              'read_bracket_seconds': ((a['qpc_after_ns']-a['qpc_before_ns'])+
                                       (b['qpc_after_ns']-b['qpc_before_ns']))/1e9}
    for kind in ('thread', 'process'):
        left, right = a.get(kind, {}), b.get(kind, {})
        if left.get('status') == right.get('status') == 'AVAILABLE':
            kernel = (right['kernel_100ns']-left['kernel_100ns'])/1e7
            user = (right['user_100ns']-left['user_100ns'])/1e7
            if min(kernel, user) < 0: raise ValueError('CPU counter regressed')
            result[kind] = {'status': 'AVAILABLE', 'kernel_seconds': kernel,
                            'user_seconds': user, 'cpu_seconds': kernel+user,
                            'wall_minus_cpu_seconds': wall-kernel-user}
        else: result[kind] = {'status': 'UNAVAILABLE'}
    left, right = a.get('cycles', {}), b.get('cycles', {})
    if left.get('status') == right.get('status') == 'AVAILABLE':
        value = right['raw']-left['raw']
        if value < 0: raise ValueError('cycle counter regressed')
        result['cycles'] = {'status': 'AVAILABLE', 'raw_difference': value}
    else: result['cycles'] = {'status': 'UNAVAILABLE'}
    return result


class Observer(BASE_OBSERVER):
    def __init__(self, out, clocks=None, host=base.host_times, snapshot=thread_snapshot):
        super().__init__(out, clocks, host)
        self.snapshot = snapshot
        self.forward_start = None
        self.forward_tick = 0
        self.windows = {'forward': 0, 'certificate': 0}

    def save_window(self, kind, start, end, first, last, complete):
        self.windows[kind] += 1
        runner.write_new(self.out/f'{kind}-window-{self.windows[kind]:04d}.json', {
            'kind': kind, 'tick_start_exclusive': first, 'tick_end_inclusive': last,
            'complete': complete, 'start': start, 'end': end, 'metrics': span(start, end),
            'state_digest_at_end': self.state_hash,
            'no_cycle_to_frequency_or_elapsed_conversion': True})

    def call(self, name, fn, *args, **kwargs):
        if name == 'advance' and self.forward_start is None:
            # Before base's possible stride128 boundary: includes that block write.
            self.forward_tick, self.forward_start = self.tick, self.snapshot()
        if name != 'certificate': return super().call(name, fn, *args, **kwargs)
        if self.forward_start is None: raise ValueError('certificate without forward window')
        end = self.snapshot()
        self.save_window('forward', self.forward_start, end, self.forward_tick, self.tick, True)
        self.forward_start = None
        start = self.snapshot(); completed = False
        try:
            value = super().call(name, fn, *args, **kwargs)
            completed = True
            return value
        finally:
            end = self.snapshot()
            self.save_window('certificate', start, end, self.tick, self.tick, completed)

    def boundary(self, final=False):
        super().boundary(final)
        if final:
            if self.forward_start is not None:
                self.save_window('forward', self.forward_start, self.snapshot(),
                                 self.forward_tick, self.tick, False)
            runner.write_new(self.out/'mechanisms.json', {
                'schema': 'HCCForwardMechanisms.v1', 'windows': self.windows,
                'partial_forward': self.forward_start is not None,
                'forward_scope': 'before first advance and stride128 write, through state persistence, before certificate call',
                'certificate_scope': 'base certificate observer only; excludes subsequent gate bookkeeping',
                'window_writes_outside_window_but_inside_whole_policy': True,
                'CPU_update_resolution_not_100ns_accuracy': True,
                'window_residual_not_pure_descheduling': True})


def owned(command, *args, **kwargs):
    if '--verify-study' in command:
        command = [str(SELF.with_name('test_randomized_forward.py')) if
                   str(x).endswith('test_forward_crossover.py') else x for x in command]
    return BASE_OWNED(command, *args, **kwargs)


def activate():
    # ponytail: reuse the frozen r12 lifecycle; only observer, contract and verifier route differ.
    base.Observer, base.contract, base.SELF, base.owned = Observer, contract, SELF, owned


def main():
    activate()
    if '--execute' not in sys.argv:
        if sys.argv[1:] == ['--self-test']:
            subprocess.run([sys.executable, '-B', '-X', 'utf8', str(SELF.with_name('test_randomized_forward.py'))], check=True)
        else: base.main()
        return
    p = argparse.ArgumentParser(); p.add_argument('--execute', action='store_true'); p.add_argument('--output', required=True)
    args = p.parse_args()
    start, qstart = time.monotonic(), time.perf_counter_ns()
    cfg, sha = contract(); debit = cfg['draw_debit_seconds']; deadline = start+6900-debit
    out = Path(args.output).resolve(); out.mkdir(exist_ok=False)
    command = [sys.executable, '-B', '-X', 'utf8', str(SELF), '--study', '--output', str(out/'study'), '--deadline', str(deadline)]
    runner.write_new(out/'execution-start.json', dict(contract_sha256=sha, argv=command,
        start_monotonic=start, deadline_monotonic=deadline, draw_debit_seconds=debit,
        effective_outer_cap_seconds=6900-debit, draw_pin=cfg['draw_pin'], retry=False))
    result = owned(command, out/'watchdog', max(.001, deadline-time.monotonic()), deadline, deadline, base.cost.KillOnlyJob)
    elapsed = (time.perf_counter_ns()-qstart)/1e9
    runner.write_new(out/'execution-end.json', dict(supervision=result, physical_highres_wall_seconds=elapsed,
        draw_debit_seconds=debit, charged_highres_wall_seconds=elapsed+debit, cap_seconds=6900,
        exceeded=time.monotonic()>deadline or elapsed+debit>6900,
        outer_cpu_overlaps_inner_do_not_sum=True))
    print(json.dumps(dict(status=result['status'], active_processes=result['active_processes'], charged_wall_seconds=elapsed+debit)), flush=True)


if __name__ == '__main__': main()
