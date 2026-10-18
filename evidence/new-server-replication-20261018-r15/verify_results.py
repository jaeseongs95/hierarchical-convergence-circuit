"""Reuse pinned r14 metadata/accounting checks for the r15 result directory."""
import hashlib
import json
from pathlib import Path
import sys

PUB = Path(__file__).resolve().parent
PRIOR = PUB.parent / 'server-crossover-20261018-r14'
assert hashlib.sha256((PRIOR / 'verify_results.py').read_bytes()).hexdigest() == (
    '167fc85a37513ad9cd71978be63bffa471d8abf4fbba501a77746a1775af4944')
sys.path.insert(0, str(PRIOR))
import verify_results as pinned

pinned.PUB = PUB
pinned.ROOT = PUB.parents[1]
pinned.RESULTS = PUB / 'results'

if __name__ == '__main__':
    prep = pinned.load(pinned.RESULTS / 'preparation.json')
    launch = pinned.load(pinned.RESULTS / 'launch.json')
    normalization = pinned.load(pinned.RESULTS / 'runtime-normalization.json')
    assert prep['status'] == 'PASS' and prep['scientific_runs'] == 0
    assert prep['hostname'] == 'ip-172-26-4-106'
    assert [t['count'] for t in prep['tests']] == [4, 5, 1]
    assert all(t['count'] == t['expected'] and t['returncode'] == 0 for t in prep['tests'])
    assert launch['freeze_commit'] == normalization['frozen_git_commit'] == (
        'a8e57ecc1b923b10347ff4ea431a89c62c75bd35')
    assert launch['preparation_contract_sha256'] == prep['contract_sha256']
    assert launch['contract_sha256'] == pinned.sha(PUB / 'execution-contract.json')
    assert normalization['semantic_equality'] is True
    assert normalization['code_or_values_changed'] is False
    assert normalization['scientific_runs'] == 0
    for entry in normalization['entries']:
        assert pinned.sha(pinned.ROOT / entry['path']) == entry['after_sha256']
    contract_entry = normalization['entries'][0]
    assert contract_entry['before_sha256'] == prep['contract_sha256']
    assert contract_entry['after_sha256'] == launch['contract_sha256']
    print(json.dumps(pinned.verify(), ensure_ascii=False, sort_keys=True))
