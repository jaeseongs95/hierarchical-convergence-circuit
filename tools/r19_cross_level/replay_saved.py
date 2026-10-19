"""Replay saved R19 JSON without executing native tick/settle or changing inputs."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]

from hcr import dynamics
from tools.r19_cross_level import probe


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw', type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    manifest = probe.read(args.raw / 'manifest.json')
    records = sorted(args.raw.glob('*.json'))
    inputs = [path for path in records if path.name in manifest]
    probe.require(len(inputs) == 20, '18 cells plus preparation/failure required')
    for path in inputs:
        probe.require(probe.sha(path) == manifest[path.name], 'raw digest ' + path.name)
    def forbidden(*args, **kwargs):
        raise AssertionError('native computation forbidden during saved-record replay')
    dynamics.tick = dynamics.settle = forbidden
    p = probe.spec()
    first = probe.read(args.raw / 'clear_A_match__bottom_up.json')
    changed = deepcopy(first)
    changed['kernels'][0]['program']['groups'][0]['bias'] += 0.1
    try:
        probe.audit_execution(changed, p['cases'][0], 'bottom_up', p)
    except ValueError:
        pass
    else:
        raise AssertionError('changed program accepted after JSON normalization')
    # Windows/Linux libm can differ at the last bit; discrete contracts remain exact.
    probe.audit(args.raw, absolute_tolerance=1e-15)
    for path in inputs:
        probe.require(probe.sha(path) == manifest[path.name], 'raw changed during replay')
    receipt = dict(status='SAVED_RECORD_REPLAY_PASSED', raw_json_verified=len(inputs),
        native_tick_calls=0, native_settle_calls=0, changed_program_rejected=True,
        summary_sha256=probe.sha(args.raw / 'summary.json'),
        corrected_probe_sha256=probe.sha(Path(probe.__file__)),
        numeric_replay_absolute_tolerance=1e-15,
        replay_wall_seconds=time.perf_counter()-started,
        original_remote_run_status='FAILED_AT_AUDIT', original_records_unchanged=True)
    probe.put(args.raw / 'replay-receipt.json', receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
