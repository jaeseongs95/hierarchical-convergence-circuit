"""Pinned EXP25 capsule and recursively verified, unmodified native dependencies."""
from copy import deepcopy
from pathlib import Path
from . import storage as io
from .contracts import BASE_COMMIT, R044_MANIFEST_BLOB, PARENT_RAW_SHA256

FIXED_FILES = ('manifest.json', 'plan.json', 'analysis/manifest.json', 'analysis/audit.json',
    'upstream/plan.json', 'upstream/seed/6.json', 'upstream/training.json')
REGRESSION_IDS = ('t0000', 't0001', 't0002', 't0003')
PARENT_FILES = FIXED_FILES + tuple('raw/' + tid + '.json' for tid in REGRESSION_IDS)


def repo_root():
    return Path(__file__).resolve().parents[2]


def merge_hashes(*inventories):
    result = {}
    for inventory in inventories:
        for name, value in inventory.items():
            io.require(name not in result or result[name] == value, 'source hash collision: ' + name)
            result[name] = value
    return result


def dependencies():
    from r038_early_adoption.sources import check_manifest
    from r044_reuse_contribution import sources as previous
    check_manifest(repo_root(), 'R044_MANIFEST.json', R044_MANIFEST_BLOB)
    return merge_hashes(previous.dependencies(), previous.addon_hashes())


def addon_hashes():
    root = repo_root(); manifest = io.load(root / 'R045_MANIFEST.json')
    io.require(set(manifest) == {'schema', 'basis_commit', 'files'} and
        manifest['schema'] == 'hcr-r045-additive-release-v1' and manifest['basis_commit'] == BASE_COMMIT,
        'R045 release schema/basis')
    inventory = manifest['files']
    io.require(type(inventory) is dict and inventory, 'R045 release inventory')
    for name, value in inventory.items():
        io.require(io.text_hash(io.child(root, name)) == value, 'R045 release file changed: ' + name)
    actual = {p.relative_to(root).as_posix() for p in Path(__file__).parent.rglob('*.py')}
    listed = {n for n in inventory if n.startswith('tools/r045_direct_support/') and n.endswith('.py')}
    io.require(actual == listed, 'unlisted/missing R045 Python source')
    return merge_hashes(inventory, {'R045_MANIFEST.json': io.text_hash(root / 'R045_MANIFEST.json')})


def capsule_name(name):
    io.require(name in PARENT_FILES, 'unregistered EXP25 capsule path')
    return name if name.startswith('upstream/') else 'basis/exp25/' + name


def validate_parent_documents(documents, hashes):
    from r044_reuse_contribution.protocol import validate_plan as validate_exp25
    io.require(set(documents) == set(hashes) == set(PARENT_FILES), 'EXP25 capsule inventory')
    io.require(hashes['manifest.json'] == PARENT_RAW_SHA256, 'pinned EXP25 raw manifest mismatch')
    manifest, plan = documents['manifest.json'], documents['plan.json']
    io.require(manifest['schema'] == 'hcr-exp25-raw-manifest-v1' and manifest['state'] == 'raw_complete', 'EXP25 incomplete raw')
    validate_exp25(plan, check_parent=False)
    for name in set(PARENT_FILES) - {'manifest.json','analysis/manifest.json','analysis/audit.json'}:
        io.require(manifest['files'][name] == hashes[name], 'EXP25 capsule checksum: ' + name)
    analysis, audit = documents['analysis/manifest.json'], documents['analysis/audit.json']
    io.require(analysis['schema'] == 'hcr-exp25-analysis-manifest-v1' and
        analysis['raw_manifest_sha256'] == PARENT_RAW_SHA256 and
        analysis['files']['audit.json'] == hashes['analysis/audit.json'], 'EXP25 audit lineage')
    io.require(audit['schema'] == 'hcr-exp25-audit-v1' and audit['verified'] is True and
        audit['native_trials'] == 24 and audit['raw_manifest_sha256'] == PARENT_RAW_SHA256,
        'EXP25 stored audit state')
    packet = documents['upstream/seed/6.json']
    io.require(packet['sha256'] == io.digest(packet['document']), 'seed packet seal')
    seed = packet['document']['engine']
    for key in ('memory', 'config'):
        io.require(io.digest(seed[key]) == plan[key + '_sha256'], 'EXP25 frozen ' + key)
    trials = {t['id']: t for t in plan['trials']}
    cells = set()
    for tid in REGRESSION_IDS:
        raw = documents['raw/' + tid + '.json']; trial = trials[tid]
        io.require(set(raw) == {'schema', 'trial', 'run'} and raw['schema'] == 'hcr-exp25-raw-trial-v1' and raw['trial'] == trial,
                   'EXP25 regression raw binding')
        io.require(trial['scope'] == 'route_only' and trial['arm'] == 'online_support' and trial['scheduler'] == 'input_order',
                   'regression policy')
        cells.add((trial['case'], trial['use_circuits']))
    io.require(cells == {(v + '__order_SMD', g) for v in ('identity', 'swap_SD') for g in (True, False)}, 'regression cells')
    return deepcopy(plan), deepcopy(seed)


def read_parent(path):
    root = io.safe(path); documents, hashes = {}, {}
    io.require(io.file_hash(root / 'manifest.json') == PARENT_RAW_SHA256, 'EXP25 manifest checksum')
    for name in PARENT_FILES:
        data = io.read(io.child(root, name))
        documents[name], hashes[name] = io.loads(data), io.bytes_hash(data)
    parent, seed = validate_parent_documents(documents, hashes)
    return root, parent, seed, hashes, documents
