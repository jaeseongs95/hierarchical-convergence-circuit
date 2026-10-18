"""r14 Linux supervisor; pinned numeric/persistence code is reused unchanged."""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

import termination_compare_core as core
import termination_compare_runner as runner
import termination_certificate_cost as cost
import termination_forward_crossover as base

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
PUB = ROOT / 'evidence/server-crossover-20261018-r14'
ORIGINAL_OBSERVER = base.Observer


def load(path):
    return core.decode(Path(path).read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assignment(seed):
    if len(seed) != 32:
        raise ValueError('32-byte seed')
    return [v for bit in (0, 1) for v in
            (['C1', 'C0'] if seed[0] >> bit & 1 else ['C0', 'C1'])]


def read_optional(path):
    try:
        return {'status': 'AVAILABLE', 'text': Path(path).read_text()}
    except OSError as error:
        return {'status': 'UNAVAILABLE', 'error': type(error).__name__}


def host_snapshot():
    start = time.perf_counter_ns()
    stat = Path('/proc/stat').read_text().splitlines()
    mem = Path('/proc/meminfo').read_text().splitlines()
    group = Path('/proc/self/cgroup').read_text().strip()
    relative = next((line[3:] for line in group.splitlines() if line.startswith('0::')), '')
    root = Path('/sys/fs/cgroup')
    leaf = (root / relative.lstrip('/')).resolve()
    if not leaf.is_relative_to(root):
        raise ValueError('cgroup traversal')
    groups = {}
    for p in [leaf, *leaf.parents]:
        if not p.is_relative_to(root):
            break
        groups[str(p)] = {n: read_optional(p / n) for n in
            ('cpu.max', 'cpu.stat', 'memory.max', 'memory.events')}
    return {'before_ns': start, 'after_ns': time.perf_counter_ns(),
            'cpu': {line.split()[0]: list(map(int, line.split()[1:]))
                    for line in stat if line.startswith('cpu')},
            'memory_kib': {line.split(':')[0]: int(line.split()[1]) for line in mem
                           if line.split(':')[0] in ('MemAvailable', 'SwapTotal', 'SwapFree')},
            'pressure': {n: read_optional('/proc/pressure/' + n) for n in ('cpu', 'memory', 'io')},
            'cgroup': group, 'ancestors': groups,
            'affinity': sorted(os.sched_getaffinity(0)), 'load': list(os.getloadavg())}


class LinuxObserver(ORIGINAL_OBSERVER):
    def __init__(self, out):
        super().__init__(out, host=host_snapshot)


def process_record(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return {'pid': pid, 'state': fields[0], 'ppid': int(fields[1]),
                'pgrp': int(fields[2]), 'start_ticks': int(fields[19])}
    except (OSError, ValueError, IndexError):
        return None


def live_group(pgid):
    members = [process_record(int(p.name)) for p in Path('/proc').iterdir() if p.name.isdigit()]
    return [p for p in members if p and p['pgrp'] == pgid and p['state'] != 'Z']


def kill_owned_group(pgid):
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def usage():
    import resource
    r = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {'user': r.ru_utime, 'system': r.ru_stime}


def interference_flags(before, after):
    flags = []
    if before['affinity'] != after['affinity'] or before['cgroup'] != after['cgroup']:
        flags.append('EXECUTION_IDENTITY_CHANGED')
    if after['cpu']['cpu'][7] > before['cpu']['cpu'][7]:
        flags.append('HOST_STEAL_OBSERVED')
    for name in ('cpu', 'memory', 'io'):
        a, b = before['pressure'][name], after['pressure'][name]
        if a['status'] != 'AVAILABLE' or b['status'] != 'AVAILABLE':
            flags.append(name.upper() + '_PSI_UNAVAILABLE')
            continue
        def total(value):
            line = next(line for line in value['text'].splitlines() if line.startswith('some '))
            return int(dict(item.split('=') for item in line.split()[1:])['total'])
        if total(b) > total(a):
            flags.append(name.upper() + '_PRESSURE_OBSERVED')
    readable = 0
    for path, values in before['ancestors'].items():
        a, b = values['cpu.stat'], after['ancestors'].get(path, {}).get('cpu.stat', {})
        if a['status'] == b.get('status') == 'AVAILABLE':
            readable += 1
            left = dict(line.split() for line in a['text'].splitlines())
            right = dict(line.split() for line in b['text'].splitlines())
            if any(int(right.get(k, 0)) > int(left.get(k, 0)) for k in ('nr_throttled', 'throttled_usec')):
                flags.append('CGROUP_THROTTLING_OBSERVED')
    if not readable:
        flags.append('CGROUP_CPU_ACCOUNTING_UNAVAILABLE')
    return sorted(set(flags))


def owned(worker_args, out, cap, global_deadline):
    """Only this script's non-spawning worker group is owned; no arbitrary-tree claim."""
    out = Path(out)
    out.mkdir(exist_ok=False)
    start = time.monotonic()
    if not math.isfinite(cap) or cap <= 0 or start >= global_deadline:
        raise ValueError('positive reserved phase budget required')
    deadline = min(start + cap, global_deadline)
    q0, c0, prior = time.perf_counter_ns(), time.process_time_ns(), usage()
    before = host_snapshot()
    command = [sys.executable, '-B', '-X', 'utf8', str(SELF), *worker_args,
               '--parent', str(os.getpid())]
    timed_out = False
    with (out / 'stdout.txt').open('xb') as stdout, (out / 'stderr.txt').open('xb') as stderr:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout,
                                   stderr=stderr, start_new_session=True)
        pid = process.pid
        birth = process_record(pid)
        runner.write_new(out / 'launch.json', {'argv': command, 'process': birth,
                          'start': start, 'deadline': deadline, 'parent': os.getpid()})
        try:
            process.stdin.write(core.canonical({'start': start, 'deadline': deadline, 'out': str(out)}) + b'\n')
            process.stdin.close()
            next_sample = start + 30
            with (out / 'host-samples.jsonl').open('xb') as samples:
                while process.poll() is None:
                    now = time.monotonic()
                    if now >= deadline:
                        timed_out = True
                        kill_owned_group(pid)
                        break
                    if now >= next_sample:
                        sample = {'scheduled_monotonic': next_sample, 'actual_monotonic': now,
                                  'host': host_snapshot(), 'supervisor_cpu_ns': time.process_time_ns() - c0}
                        samples.write(core.canonical(sample) + b'\n')
                        samples.flush()
                        next_sample += 30
                    time.sleep(min(.05, max(.001, deadline - now)))
        finally:
            if process.poll() is None:
                kill_owned_group(pid)
            process.wait(timeout=10)
    observed_end = time.monotonic()
    timed_out = timed_out or observed_end > deadline
    remaining = live_group(pid)
    if remaining:
        kill_owned_group(pid)
        raise RuntimeError('owned group remained alive; study must stop')
    after = host_snapshot()
    result = {'status': 'BUDGET_INCOMPLETE' if timed_out else
                       'COMPLETE' if process.returncode == 0 else 'WORKER_FAILURE',
              'returncode': process.returncode, 'pid': pid, 'birth': birth,
              'completion_observed_monotonic': observed_end,
              'start_monotonic': start, 'deadline_monotonic': deadline,
              'active_processes': len(remaining), 'host_before': before, 'host_after': after,
              'whole_wall_seconds': (time.perf_counter_ns() - q0) / 1e9,
              'supervisor_cpu_seconds': (time.process_time_ns() - c0) / 1e9,
              'child_cpu_seconds': {k: v - prior[k] for k, v in usage().items()},
              'interference_flags': interference_flags(before, after),
              'wall_minus_CPU_not_pure_interference': True,
              'receipt_serialization_is_shared_outer_overhead': True}
    runner.write_new(out / 'supervision.json', result)
    return result


def bootstrap(args):
    import resource
    # No sudo, affinity/priority/global changes. Fail closed if parent vanished before prctl.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != args.parent:
        raise RuntimeError('parent-death binding')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (3020, 3030))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    release = core.decode(sys.stdin.buffer.readline())
    if (set(release) != {'start', 'deadline', 'out'} or
            not all(math.isfinite(release[k]) for k in ('start', 'deadline')) or
            not release['start'] < release['deadline']):
        raise ValueError('release handshake')
    runner.write_new(Path(release['out']) / 'bootstrap.json', {
        'pid': os.getpid(), 'ppid': os.getppid(), 'pgrp': os.getpgrp(), 'PDEATHSIG': 'SIGKILL',
        'limits': {n: list(resource.getrlimit(getattr(resource, n))) for n in
                   ('RLIMIT_CORE', 'RLIMIT_AS', 'RLIMIT_CPU', 'RLIMIT_FSIZE')},
        'affinity': sorted(os.sched_getaffinity(0)), 'virtual_address_limit_not_Windows_job_commit': True})
    return release


def verify(out, release):
    """Fresh pinned predicate on every distinct complete gate payload, never replay answer cache."""
    import check_termination_comparison as evaluator
    out = Path(out)
    rows = load(out / 'cells-sealed.json')['rows']
    data = load(PUB / 'public-input.json')
    model = runner.validate_input(data)
    if model != evaluator.independent_model(data['public']):
        raise ValueError('independent model')
    meter = core.Meter(release['deadline'])
    arithmetic = core.Arithmetic(data['math_sources'], meter)
    common, unique, equalities, expected_gates, certificates = {}, {}, 0, 0, []
    for row in rows:
        meter.guard()
        if row['last_tick'] is None:
            continue
        child = out / row['cell_id']
        state_boxes = {}
        for tick in range(row['last_tick'] + 1):
            meter.guard()
            s = load(child / f'state-{tick:06d}.json')
            if (s['tick'] != tick or s['model_digest'] != data['model_digest'] or
                    s['observation_digest'] != data['observation_digest'] or
                    s['processed_digest'] != data['processed_digest'] or
                    s['diagnostic'] != core.diagnostic(s['current_x_box'])):
                raise ValueError('state binding')
            state_boxes[tick] = s['current_x_box']
            encoded = core.canonical(s['current_x_box'])
            if tick in common:
                if common[tick] != encoded:
                    raise ValueError('full7 divergence')
                equalities += 1
            else:
                common[tick] = encoded
        if row['status'] != 'COMPLETE':
            continue
        final, timings = load(child / 'final.json'), load(child / 'timings.json')
        gates = timings['gate_attempts']
        if final['counters'] != timings['counts'] or len(gates) != row['last_tick'] // 16:
            raise ValueError('gate coverage')
        successes = []
        for i, gate in enumerate(gates, 1):
            meter.guard()
            tick = i * 16
            box = state_boxes[tick]
            if gate['attempt'] != i or gate['state_digest'] != core.digest(box):
                raise ValueError('gate payload binding')
            payload = {'model': model, 'current_x_box': box,
                       'radius_x_exact': str(core.RADIUS), 'epsilon_p_exact': [str(core.EPSILON)],
                       'helper_pins': core.LIB_PINS}
            key = core.canonical(payload)
            if key not in unique:
                unique[key] = arithmetic.certificate(model, box)
            original = unique[key]
            if gate['status'] != original['bounds']['component_vector'][0]['status']:
                raise ValueError('fresh original predicate mismatch')
            if gate['screen'] is not None and gate['status'] != 'NOT_CERTIFIED':
                raise ValueError('screen falsely certified')
            if gate['status'] == 'CERTIFIED_WITHIN_EPS':
                successes.append(tick)
                if core.canonical(original) != core.canonical(final['certificate']):
                    raise ValueError('canonical success certificate mismatch')
            expected_gates += 1
        if successes != [row['last_tick']] or final['stop_reason'] != 'CERTIFIED':
            raise ValueError('first success coverage')
        certificates.append(sha(child / 'final.json'))
    complete = len(rows) == 4 and all(r['status'] == 'COMPLETE' and
        r.get('evaluation', {}).get('candidate_correct') is True and
        r.get('evaluation', {}).get('distance', {}).get('status') == 'INSIDE' for r in rows)
    if complete and (len(unique) != 323 or any(r['last_tick'] != 5168 for r in rows)):
        raise ValueError('same trajectory expected invariants')
    runner.write_new(Path(release['out']) / 'result.json', {
        'status': 'PASS' if complete else 'PASS_INTEGRITY_ONLY',
        'all_four_quality': complete, 'full7_equalities': equalities,
        'fresh_unique_full_payloads': len(unique), 'gate_occurrences': expected_gates,
        'canonical_success_certificates_checked': len(certificates),
        'shared_helpers_and_accepted_anchor_trusted': True, 'nonlinear_full_prefix_replay': False})


def contract():
    cfg = load(PUB / 'execution-contract.json')
    for pin in cfg['code_pins'] + cfg['input_pins']:
        runner.load_verified(ROOT, pin)
    return cfg


def study(out):
    cfg = contract()
    out = Path(out)
    out.mkdir(exist_ok=False)
    start = time.monotonic()
    deadline = start + cfg['global_seconds']
    seed = os.urandom(32)
    order = assignment(seed)
    runner.write_new(out / 'draw.json', {'seed_hex': seed.hex(), 'order': order,
        'contract_sha256': sha(PUB / 'execution-contract.json'), 'one_draw': True})
    environment = {'platform': platform.platform(), 'python': sys.version,
                   'clocks': base.clock_inventory(), 'host': host_snapshot(),
                   'mounts': Path('/proc/self/mountinfo').read_text(), 'source_commit': cfg['source_commit']}
    runner.write_new(out / 'environment.json', environment)
    # Fixed preflight: no policy outcome, no performance pilot, no opportunistic delayed start.
    if environment['host']['memory_kib']['MemAvailable'] < 1024 * 1024:
        runner.write_new(out / 'safety-stop.json', {'reason': 'initial available memory <1GiB'})
        return
    time.sleep(30)
    rows = []
    input_path = PUB / 'public-input.json'
    data = load(input_path)
    for index, variant in enumerate(order, 1):
        row = {'cell_id': f'{index:02d}-{variant}', 'variant': variant,
               'status': 'NOT_RUN', 'last_tick': None}
        rows.append(row)
        remaining = 5 - index
        if deadline - time.monotonic() < remaining * 3025 + cfg['verification_seconds']:
            continue
        if host_snapshot()['memory_kib']['MemAvailable'] < 256 * 1024:
            row['status'] = 'SAFETY_NOT_RUN'
            continue
        child = out / row['cell_id']
        supervision = owned(['--worker', 'policy', '--input', str(input_path),
            '--input-sha', sha(input_path), '--variant', variant], child, cfg['policy_seconds'], deadline)
        last = runner.last_snapshot(child, supervision)
        final = load(child / 'final.json') if (child / 'final.json').exists() else None
        row.update(status=supervision['status'], policy_supervision=supervision,
                   last_tick=last['snapshot']['tick'] if last else None)
        if row['status'] == 'COMPLETE' and (final is None or final['stop_reason'] != 'CERTIFIED' or
                not all((child / n).exists() for n in ('timings.json', 'trace.json'))):
            row['status'] = 'MEASUREMENT_INCOMPLETE'
        seal = {'schema': 'HCCTerminationSealedCell.v1', 'input_sha256': sha(input_path),
                'model_digest': data['model_digest'], 'observation_digest': data['observation_digest'],
                'processed_digest': data['processed_digest'], 'supervision': supervision,
                'last_complete': last, 'final': final}
        runner.write_new(child / 'sealed-cell.json', seal)
        request = {'schema': 'HCCTerminationEvaluationInput.v1', 'repo': str(ROOT),
            'policy_seal': {'path': str(child / 'sealed-cell.json'), 'sha256': sha(child / 'sealed-cell.json')},
            'public_input': {'path': str(input_path), 'sha256': sha(input_path)},
            'world': {'path': str(PUB / 'world.json'), 'sha256': sha(PUB / 'world.json')},
            'distance_reference': cfg['distance_reference']}
        runner.write_new(child / 'evaluation-input.json', request)
        evaluation = owned(['--worker', 'evaluate', '--input', str(child / 'evaluation-input.json'),
            '--input-sha', sha(child / 'evaluation-input.json')], child / 'evaluation', 15, deadline)
        result = child / 'evaluation/result.json'
        row['evaluation_supervision'] = evaluation
        if evaluation['status'] == 'COMPLETE' and result.exists():
            row['evaluation'] = load(result)
        else:
            row['evaluation_failure'] = True
        runner.write_new(child / 'cell-result.json', row)
    runner.write_new(out / 'cells-sealed.json', {'planned': 4, 'rows': rows})
    verification = owned(['--worker', 'verify', '--study', str(out)], out / 'verification',
                         cfg['verification_seconds'], deadline)
    quality = load(out / 'verification/result.json') if (out / 'verification/result.json').exists() else None
    verified = verification['status'] == 'COMPLETE' and quality and quality['status'] == 'PASS'
    differences = []
    for pair in (rows[:2], rows[2:]):
        by = {r['variant']: r for r in pair}
        differences.append(by['C1']['policy_supervision']['whole_wall_seconds'] -
                           by['C0']['policy_supervision']['whole_wall_seconds'] if
                           verified and all(r['status'] == 'COMPLETE' for r in pair) else None)
    runner.write_new(out / 'comparison.json', {'rows': rows, 'planned': 4,
        'verification_supervision': verification, 'verification': quality,
        'verdict': 'DESCRIPTIVE_SERVER_COMPARISON' if verified else 'ABSTAIN_INCOMPLETE_EVIDENCE',
        'paired_C1_minus_C0_seconds': differences,
        'mean_seconds': sum(differences) / 2 if all(v is not None for v in differences) else None,
        'environment_flags': sorted({flag for row in rows for flag in
            row.get('policy_supervision', {}).get('interference_flags', [])}),
        'charged_seconds': time.monotonic() - start, 'global_seconds': cfg['global_seconds'],
        'interference_excluded': False, 'windows_retrospective_correction': False})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output')
    parser.add_argument('--worker', choices=('policy', 'evaluate', 'verify', 'smoke-ok', 'smoke-hang'))
    parser.add_argument('--parent', type=int)
    parser.add_argument('--input')
    parser.add_argument('--input-sha')
    parser.add_argument('--variant')
    parser.add_argument('--study')
    args = parser.parse_args()
    if args.worker:
        release = bootstrap(args)
        if args.worker == 'policy':
            base.Observer = LinuxObserver
            base.policy(args.input, args.input_sha, args.variant, release)
        elif args.worker == 'evaluate':
            import check_termination_comparison as evaluator
            evaluator.evaluate_worker(args.input, args.input_sha, release)
        elif args.worker == 'verify':
            verify(args.study, release)
        elif args.worker == 'smoke-hang':
            time.sleep(60)
        return
    if not args.execute or not args.output:
        parser.error('explicit --execute --output required')
    study(args.output)


if __name__ == '__main__':
    main()
