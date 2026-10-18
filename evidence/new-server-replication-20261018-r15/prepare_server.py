"""Prepare the isolated r15 bundle; never execute a scientific policy."""
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

PUB = Path(__file__).resolve().parent
ROOT = PUB.parents[1]
sys.path.insert(0, str(ROOT / 'tools/analysis'))
import termination_new_server_replication as adapter


def prepare():
    start = time.monotonic()
    assert platform.node() == 'ip-172-26-4-106'
    assert not (ROOT / 'PREPARED.json').exists()
    cfg = adapter.server.contract()
    assert cfg['target'] == 'AI Research SSH/default'
    host = adapter.server.host_snapshot()
    assert host['memory_kib']['MemAvailable'] >= 1024 * 1024
    results = []
    for name, expected in [('test_server_crossover.py', 4), ('test_certificate_cost.py', 5),
                           ('test_new_server_replication.py', 1)]:
        command = [sys.executable, '-B', 'tools/analysis/' + name]
        p = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
        count = re.search(r'Ran (\d+) tests? in', p.stderr)
        results.append(dict(argv=command, returncode=p.returncode, expected=expected,
            count=int(count.group(1)) if count else None, stdout=p.stdout, stderr=p.stderr))
    passed = all(r['returncode'] == 0 and r['count'] == r['expected'] and
                 'skipped' not in r['stderr'] for r in results)
    record = dict(status='PASS' if passed else 'FAIL', tests=results, scientific_runs=0,
        host=host, hostname=platform.node(), python=sys.version,
        contract_sha256=hashlib.sha256((PUB / 'execution-contract.json').read_bytes()).hexdigest(),
        preparation_seconds=time.monotonic() - start)
    adapter.server.runner.write_new(ROOT / 'PREPARED.json', record)
    print(json.dumps(dict(status=record['status'], tests=[r['count'] for r in results],
        scientific_runs=0, contract_sha256=record['contract_sha256'])))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(prepare())
