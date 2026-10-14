"""고정 실수 continuation의 chunk 의존성과 terminal 수축 증명을 검산한다."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time

ORDER = ['e:0', 'e:1', 'e:2', 'e:3', 'p:0:0', 'p:0:1', 'goal']
BASE = 'experiments/exp-62-top-down/'
OLD_PROTOCOL = BASE + 'on-real-stop-protocol-20261014.json'
OLD_RECORD = BASE + 'on-real-stop-certificates-20261014.json'
OLD_CHECKER = 'tools/analysis/check_on_real_stop.py'
OLD_PRODUCER = 'tools/analysis/on_real_stop.py'
ROOT_CHECKER = 'tools/analysis/check_on_fixed_points.py'
PRODUCER = 'tools/analysis/on_real_escape.py'
CHECKER = 'tools/analysis/check_on_real_escape.py'
SOURCE_PATHS = {'src/hcr/dynamics.py', 'src/hcr/model.py', 'src/hcr/workspace.py',
                'src/hcr/runtime.py', 'tools/analysis/on_fixed_points.py',
                'tools/analysis/check_on_basins.py', 'tools/analysis/check_on_native_stop.py',
                'tools/analysis/check_on_critical_strip.py', 'tools/analysis/check_on_fold.py',
                BASE + 'on-native-stop-protocol-20261014.json',
                BASE + 'on-native-stop-certificates-20261014.json',
                BASE + 'on-critical-strip-protocol-20261013.json',
                BASE + 'on-critical-strip-certificates-20261013.json',
                OLD_PROTOCOL, OLD_RECORD, OLD_CHECKER, OLD_PRODUCER, ROOT_CHECKER}
SAMPLE = {'sample_id': 'above_near', 'score_hex': '0x1.277babda5a221p-5',
          'drive_hex': '0x1.277babda5a221p-3'}
SHA = re.compile(r'[0-9a-f]{64}\Z')
RECEIPT_FIELDS = {'schema', 'accepted', 'status', 'chunk_index', 'start_tick', 'end_tick',
                  'verified_transitions', 'protocol_sha256', 'proposal_sha256', 'prefix_pin',
                  'checker_pin', 'producer_pin', 'source_pins', 'model_digest', 'state_order',
                  'start_x_box', 'end_x_box', 'slice_sha256', 'previous_receipt_sha256'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected), label + ' fields mismatch')


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError('nonfinite JSON constant: ' + value)

    return json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def file_pin(path, label):
    data = Path(path).read_bytes()
    return {'path': label, 'sha256': digest(data), 'bytes': len(data)}


def pinned(root, ref):
    fields(ref, {'path', 'sha256', 'bytes'}, 'pin')
    require(isinstance(ref['path'], str) and isinstance(ref['sha256'], str)
            and SHA.fullmatch(ref['sha256']) and type(ref['bytes']) is int and ref['bytes'] > 0,
            'invalid pin')
    name = Path(ref['path'])
    require('..' not in name.parts, 'pin traversal')
    path = (root / name).resolve()
    require(path.is_relative_to(root), 'pin outside allowed root')
    data = path.read_bytes()
    require(len(data) == ref['bytes'] and digest(data) == ref['sha256'], 'pin bytes/hash mismatch')
    return data


def box(encoded, places=30):
    require(isinstance(encoded, list) and len(encoded) == 7, 'ordered7 box required')
    pattern = re.compile(r'-?(?:0|[1-9][0-9]*)\.[0-9]{' + str(places) + r'}\Z')
    result = []
    for pair in encoded:
        require(isinstance(pair, list) and len(pair) == 2, 'endpoint pair required')
        require(all(isinstance(s, str) and len(s) <= places + 4 and pattern.fullmatch(s)
                    for s in pair), 'invalid fixed-grid endpoint')
        lo, hi = map(Q, pair)
        require(-1 <= lo <= hi <= 1 and not any(s.startswith('-') and Q(s) == 0 for s in pair),
                'box domain/order/negative zero')
        result.append((lo, hi))
    return result


def sample_binding(document, protocol):
    require(all(document.get(k) == protocol.get(k) == v for k, v in SAMPLE.items()),
            'sample/score/drive mismatch')
    score, drive = (Q(*float.fromhex(document[k]).as_integer_ratio())
                    for k in ('score_hex', 'drive_hex'))
    require(drive == 4 * score, 'drive is not exact score4')
    return True


def validate_suffix(prefix_end, suffix, document_end=None):
    box(prefix_end)
    require(isinstance(suffix, list) and len(suffix) == 4096, 'suffix count is not4096')
    for tick, entry in enumerate(suffix, 2049):
        fields(entry, {'tick', 'x_box'}, 'suffix')
        require(type(entry['tick']) is int and entry['tick'] == tick, 'suffix gap/order')
        box(entry['x_box'])
    if document_end is not None:
        require(document_end == suffix[-1]['x_box'], 'terminal box mismatch')
    return True


def root_geometry(terminal, root):
    fields(root, {'lower', 'upper', 'weights'}, 'root box')
    require(isinstance(root['lower'], list) and isinstance(root['upper'], list)
            and len(root['lower']) == len(root['upper']) == 7, 'root dimensions')
    require(isinstance(root['weights'], list) and len(root['weights']) == 7
            and all(type(w) is int and w == 1 for w in root['weights']), 'fixed root weights')
    endpoints = box([[lo, hi] for lo, hi in zip(root['lower'], root['upper'])], 31)
    terminal_values = box(terminal)
    radius = Q(1, 1000000)
    for (lo, hi), (tl, th) in zip(endpoints, terminal_values):
        center = (tl + th) / 2
        require(-1 < lo < hi < 1 and lo == center - radius and hi == center + radius,
                'root is not exact terminal midpoint plus/minus fixed radius')
    return [p[0] for p in endpoints], [p[1] for p in endpoints], [Q(1)] * 7


def protocol_check(protocol, old):
    expected_fields = {'schema', 'source_commit', 'sources', 'raw', 'state_order', 'network_id',
                       'initial_x', 'sample_id', 'score_hex', 'drive_hex', 'continuation',
                       'prefix_ticks', 'first_suffix_tick', 'terminal_tick', 'root_proposal',
                       'arithmetic', 'budget', 'checkpoint_contract', 'success', 'failure_policy',
                       'scope_limits'}
    fields(protocol, expected_fields, 'protocol')
    require(protocol['schema'] == 'HCCONRealEscapeProtocol.v1'
            and protocol['source_commit'] == '1bb463d3c510fb37864456fe68f328bae9fc3f8e'
            and protocol['state_order'] == ORDER and protocol['network_id'] == 'network-8'
            and protocol['initial_x'] == '0'
            and protocol['continuation'] == 'unconditional_F_after_old_firststop', 'frozen model')
    sample_binding(protocol, protocol)
    require(all(type(protocol[k]) is int and protocol[k] == v for k, v in
                [('prefix_ticks', 2048), ('first_suffix_tick', 2049), ('terminal_tick', 6144)]),
            'frozen horizon')
    require(protocol['root_proposal'] == {'center': 'exact_terminal_box_midpoint',
            'radius_exact': '1/1000000', 'weights': [1] * 7, 'grid_places': 31}
            and type(protocol['root_proposal']['grid_places']) is int
            and all(type(w) is int for w in protocol['root_proposal']['weights']), 'root contract')
    require(protocol['arithmetic'] == {'decimal_precision': 80, 'interval_grid_places': 30,
            'taylor_degree': 96, 'exact_tanh_cache': False}
            and all(type(protocol['arithmetic'][k]) is int for k in
                    ('decimal_precision', 'interval_grid_places', 'taylor_degree'))
            and protocol['arithmetic']['exact_tanh_cache'] is False, 'arithmetic contract')
    require(protocol['budget'] == {'max_new_transitions': 4096, 'chunks': 64, 'ticks_per_chunk': 64,
            'wall_time_seconds_absolute': 1800, 'auto_retry': False, 'adaptive_precision': False,
            'cap_escalation': False}
            and all(type(protocol['budget'][k]) is int for k in
                    ('max_new_transitions', 'chunks', 'ticks_per_chunk', 'wall_time_seconds_absolute'))
            and all(protocol['budget'][k] is False for k in
                    ('auto_retry', 'adaptive_precision', 'cap_escalation')), 'budget contract')
    require(protocol['checkpoint_contract'] == {
            'deadline': 'persist UTC start+1800s; downtime included; notreset',
            'completion': 'actualchildexit0 + immutablechunkreceipt + externallyobservedhashjournal atomiccommit',
            'reuse': 'committedsuccessful conditionalproofs trusteddependency; notJSON-only/hostattestation',
            'resume': 'onlyneverstartednextchunk; any starteduncommittedrange =>INCONCLUSIVE'},
            'checkpoint contract')
    require(protocol['success'] == {'all7_strict_entry': True, 'strict_H_self_inclusion': True,
            'qH_qF_public_lt_one': True, 'y_x_lower_strict': '9/10', 'goal_x_lower_strict': '9/10'}
            and all(protocol['success'][k] is True for k in
                    ('all7_strict_entry', 'strict_H_self_inclusion', 'qH_qF_public_lt_one')),
            'success contract')
    expected = old['SOURCES'] | {OLD_PROTOCOL, OLD_RECORD, OLD_CHECKER, OLD_PRODUCER, ROOT_CHECKER}
    require(isinstance(protocol['sources'], list) and len(protocol['sources']) == 18
            and {r['path'] for r in protocol['sources']} == expected, 'source inventory')


def prefix_binding(prior, previous_protocol, refs, old):
    old['protocol_check'](previous_protocol)
    require(prior['schema'] == 'HCCONRealStopCertificates.v1'
            and prior['source_commit'] == previous_protocol['source_commit']
            and prior['protocol'] == refs[OLD_PROTOCOL], 'old real header/protocol')
    proposal, result, frozen = (prior[k] for k in
                               ('proposal', 'independent_verification', 'frozen_execution'))
    sample_binding(proposal, previous_protocol)
    require(proposal['schema'] == 'HCCONRealStopProposal.v1'
            and result['schema'] == 'HCCONRealStopCheck.v1'
            and proposal['protocol_sha256'] == result['protocol_sha256'] == refs[OLD_PROTOCOL]['sha256'],
            'old real proof protocol')
    require(result['accepted'] is True and result['witness'] is True
            and result['status'] == 'CERTIFIED' and result['outcome'] == 'CERTIFIED_LOW_STOP'
            and result['sample_id'] == SAMPLE['sample_id'], 'old real proof not accepted witness')
    require(all(type(result[k]) is int and result[k] == v for k, v in
                [('rechecked_prefix_transitions', 160), ('verified_suffix_transitions', 1888),
                 ('verified_transitions', 2048), ('native_replays', 0)]), 'old transition counts')
    stop = result['stop']
    require(stop['status'] == 'stable_decision' and type(stop['tick']) is int and stop['tick'] == 1848
            and type(stop['stable_steps']) is int and stop['stable_steps'] == 4,
            'old stop result mismatch')
    require(frozen['protocol'] == refs[OLD_PROTOCOL]
            and type(frozen['numerical_runs_before_freeze']) is int
            and frozen['numerical_runs_before_freeze'] == 0, 'old freeze protocol')
    frozen_refs = {r['path']: r for r in frozen['files']}
    require(all(frozen_refs.get(path) == refs[path] for path in
                (OLD_PROTOCOL, OLD_CHECKER, OLD_PRODUCER)), 'old frozen implementation pins')
    require(all(refs.get(r['path']) == r for r in previous_protocol['sources']), 'old sources differ')
    suffix = proposal['suffix']
    require(isinstance(suffix, list) and len(suffix) == 1888, 'old suffix inventory')
    for tick, entry in enumerate(suffix, 161):
        fields(entry, {'tick', 'x_box'}, 'old suffix')
        require(type(entry['tick']) is int and entry['tick'] == tick, 'old suffix tick gap')
        box(entry['x_box'])
    return suffix[-1]['x_box']


def load_binding(repo, protocol, protocol_sha, proposal, proposal_sha, guard):
    # Helpers are loaded only from pinned bytes; five-state CLI loaders are never called.
    inventory = protocol.get('sources')
    require(isinstance(inventory, list), 'sources required')
    refs = {ref['path']: ref for ref in inventory}
    require(len(refs) == len(inventory) == 18 and set(refs) == SOURCE_PATHS,
            'duplicate/missing/unexpected source')
    data = {}
    for name, ref in refs.items():
        guard()
        data[name] = pinned(repo, ref)
    sys.dont_write_bytecode = True
    def helper(path, name):
        # Execute the bytes whose pin was checked, avoiding a hash/read race.
        scope = {'__name__': name, '__file__': str(repo / path)}
        exec(compile(data[path], str(repo / path), 'exec'), scope)
        return scope

    old = helper(OLD_CHECKER, 'escape_old_stop_dependency')
    protocol_check(protocol, old)
    previous_protocol, prior = decode(data[OLD_PROTOCOL]), decode(data[OLD_RECORD])
    prefix = prefix_binding(prior, previous_protocol, refs, old)
    require(protocol['raw'] == previous_protocol['raw'], 'raw differs from old proof')
    require(isinstance(protocol['raw'], list) and len(protocol['raw']) == 2, 'raw inventory')
    raws = []
    for ref in protocol['raw']:
        fields(ref, {'model_id', 'path', 'sha256', 'bytes'}, 'raw pin')
        raws.append(decode(pinned(repo, {k: ref[k] for k in ('path', 'sha256', 'bytes')})))
    native = helper(old['NATIVE_CHECKER'], 'escape_native_model_helper')
    exact = helper(old['BASIN_CHECKER'], 'escape_exact_helper')
    critical = helper(old['CRITICAL_CHECKER'], 'escape_census_helper')
    roots = helper(ROOT_CHECKER, 'escape_root_helper')
    require(exact['DEGREE'] == roots['DEGREE'] == 96 and native['ORDER'] == ORDER, 'helper geometry')
    b, G, d = old['model_binding'](raws, protocol['raw'], refs, previous_protocol, native, exact, data)
    old['root_dependency'](decode(data[old['CRITICAL_RECORD']]), decode(data[old['CRITICAL_PROTOCOL']]),
                           refs, critical['REGIONS'], previous_protocol, exact)
    fields(proposal, {'schema', 'protocol_sha256', 'sample_id', 'score_hex', 'drive_hex', 'prefix_pin',
                      'prefix_end_x_box', 'suffix', 'root_box'}, 'proposal')
    require(proposal['schema'] == 'HCCONRealEscapeProposal.v1'
            and proposal['protocol_sha256'] == protocol_sha, 'proposal protocol')
    sample_binding(proposal, protocol)
    require(proposal['prefix_pin'] == refs[OLD_RECORD]
            and proposal['prefix_end_x_box'] == prefix, 'complete old B2048 mismatch')
    validate_suffix(prefix, proposal['suffix'])
    root_geometry(proposal['suffix'][-1]['x_box'], proposal['root_box'])
    model_digest = digest(canonical({'b': list(map(str, b)),
                                    'G': [list(map(str, row)) for row in G], 'd': str(d)}))
    binding = {'protocol_sha256': protocol_sha, 'proposal_sha256': proposal_sha,
               'prefix_pin': refs[OLD_RECORD],
               'checker_pin': file_pin(__file__, str(Path(__file__).resolve())),
               'producer_pin': file_pin(repo / PRODUCER, str((repo / PRODUCER).resolve())),
               'source_pins': protocol['sources'],
               'model_digest': model_digest, 'state_order': ORDER}
    guard()
    return binding, (b, G, d), exact, roots


def chunk_expected(index, proposal):
    require(type(index) is int and 0 <= index < 64, 'chunk index')
    start = 64 * index
    entries = proposal['suffix'][start:start + 64]
    return {'chunk_index': index, 'start_tick': 2049 + start, 'end_tick': 2112 + start,
            'verified_transitions': 64,
            'start_x_box': (proposal['prefix_end_x_box'] if index == 0
                            else proposal['suffix'][start - 1]['x_box']),
            'end_x_box': entries[-1]['x_box'], 'slice_sha256': digest(canonical(entries))}


def verify_chunk(index, previous_sha, proposal, binding, model, exact, guard):
    require(isinstance(previous_sha, str) and SHA.fullmatch(previous_sha), 'previous receipt SHA')
    if index == 0:
        require(previous_sha == binding['prefix_pin']['sha256'], 'first receipt prefix SHA')
    expected = chunk_expected(index, proposal)
    current = box(expected['start_x_box'])
    for entry in proposal['suffix'][index * 64:(index + 1) * 64]:
        guard()
        lo, hi = exact['advance'](*model, [v[0] for v in current], [v[1] for v in current])
        following = box(entry['x_box'])
        require(exact['contains_transition'](lo, hi, [v[0] for v in following],
                                            [v[1] for v in following]),
                'transition inclusion failed at tick ' + str(entry['tick']))
        current = following
    guard()
    return dict(binding, **expected, schema='HCCONRealEscapeChunk.v1', accepted=True,
                status='CERTIFIED', previous_receipt_sha256=previous_sha)


def argv_options(argv):
    require(isinstance(argv, list) and len(argv) >= 5 and all(isinstance(a, str) for a in argv)
            and argv[1:4] == ['-B', '-X', 'utf8'],
            'observation argv')
    args = argv[5:]
    require(len(args) % 2 == 0, 'argv must use explicit option values')
    options = {}
    for key, value in zip(args[::2], args[1::2]):
        require(key.startswith('--') and key not in options, 'duplicate/invalid argv option')
        options[key] = value
    require(set(options) == {'--repo', '--protocol', '--protocol-sha256', '--input', '--output',
                            '--remaining-seconds', '--chunk-index', '--previous-receipt-sha256'},
            'unexpected checker argv options')
    return options


def verify_chain(receipts, observations, binding, proposal):
    require(isinstance(receipts, list) and isinstance(observations, list)
            and len(receipts) == len(observations) == 64, 'exactly64 actual receipts required')
    previous_sha = binding['prefix_pin']['sha256']
    for index, (receipt, observation) in enumerate(zip(receipts, observations)):
        fields(receipt, RECEIPT_FIELDS, 'chunk receipt')
        require(receipt['schema'] == 'HCCONRealEscapeChunk.v1' and receipt['accepted'] is True
                and receipt['status'] == 'CERTIFIED', 'chunk not certified')
        require(all(receipt.get(k) == value for k, value in binding.items()), 'chunk binding mismatch')
        expected = chunk_expected(index, proposal)
        require(all(receipt.get(k) == value for k, value in expected.items())
                and all(type(receipt[k]) is int for k in
                        ('chunk_index', 'start_tick', 'end_tick', 'verified_transitions')),
                'chunk range/start/end/slice mismatch')
        require(receipt['previous_receipt_sha256'] == previous_sha, 'receipt chain fork/gap')
        fields(observation, {'index', 'argv', 'exit_code', 'stdout', 'stderr', 'execution_observed',
                             'input_pin', 'identity', 'elapsed_seconds', 'receipt'}, 'observation')
        require(type(observation['index']) is int and observation['index'] == index
                and type(observation['exit_code']) is int and observation['exit_code'] == 0
                and observation['execution_observed'] is True, 'actual success observation missing')
        require(isinstance(observation['stdout'], str) and isinstance(observation['stderr'], str)
                and type(observation['elapsed_seconds']) in (int, float)
                and math.isfinite(observation['elapsed_seconds'])
                and 0 <= observation['elapsed_seconds'] <= 1800, 'invalid execution capture')
        fields(observation['identity'], {'protocol_sha256', 'producer_pin', 'checker_pin'}, 'identity')
        require(all(observation['identity'][k] == binding[k] for k in observation['identity']),
                'observed execution identity mismatch')
        fields(observation['input_pin'], {'path', 'sha256', 'bytes'}, 'observed input pin')
        require(observation['input_pin']['sha256'] == binding['proposal_sha256']
                and type(observation['input_pin']['bytes']) is int
                and observation['input_pin']['bytes'] > 0
                and isinstance(observation['input_pin']['path'], str)
                and Path(observation['input_pin']['path']).is_absolute(), 'observed input binding')
        fields(observation['receipt'], {'path', 'sha256', 'bytes'}, 'receipt pin')
        require(isinstance(observation['receipt']['sha256'], str)
                and SHA.fullmatch(observation['receipt']['sha256'])
                and type(observation['receipt']['bytes']) is int and observation['receipt']['bytes'] > 0,
                'receipt pin invalid')
        options = argv_options(observation['argv'])
        require(options['--chunk-index'] == str(index)
                and options['--previous-receipt-sha256'] == previous_sha
                and options['--protocol-sha256'] == binding['protocol_sha256'], 'execution argv binding')
        previous_sha = observation['receipt']['sha256']
    return True


def verify_ledger(path, proposal, binding, args, guard):
    path = Path(path).resolve()
    ledger = decode(path.read_bytes())
    fields(ledger, {'schema', 'protocol_sha256', 'proposal_sha256', 'deadline_utc', 'producer_pin',
                    'checker_pin', 'observations'}, 'execution ledger')
    require(ledger['schema'] == 'HCCONRealEscapeExecutionLedger.v1'
            and all(ledger[k] == binding[k] for k in
                    ('protocol_sha256', 'proposal_sha256', 'producer_pin', 'checker_pin')),
            'ledger candidate/code binding')
    require(isinstance(ledger['deadline_utc'], str), 'deadline UTC string required')
    deadline = datetime.fromisoformat(ledger['deadline_utc'].replace('Z', '+00:00'))
    require(deadline.tzinfo is not None and deadline.utcoffset().total_seconds() == 0,
            'deadline must be UTC')

    def deadline_guard():
        guard()
        require(datetime.now(timezone.utc) < deadline, 'absolute UTC deadline expired')

    observations = ledger['observations']
    require(isinstance(observations, list) and len(observations) == 64, 'ledger64 coverage')
    receipts = []
    seen_paths = set()
    for observation in observations:
        deadline_guard()
        fields(observation, {'index', 'argv', 'exit_code', 'stdout', 'stderr', 'execution_observed',
                             'input_pin', 'identity', 'elapsed_seconds', 'receipt'}, 'observation')
        ref = observation['receipt']
        receipt_data = pinned(path.parent, ref)
        receipt_path = (path.parent / ref['path']).resolve()
        require(receipt_path not in seen_paths, 'receipt path reused')
        seen_paths.add(receipt_path)
        receipts.append(decode(receipt_data))
        argv = observation['argv']
        options = argv_options(argv)
        require(Path(argv[0]).resolve() == Path(sys.executable).resolve()
                and Path(argv[4]).resolve() == Path(__file__).resolve(), 'observed executable/checker path')
        require(Path(options['--repo']).resolve() == Path(args.repo).resolve()
                and Path(options['--protocol']).resolve() == Path(args.protocol).resolve()
                and Path(options['--input']).resolve() == Path(args.input).resolve()
                and Path(options['--output']).resolve() == receipt_path, 'observed input/output paths')
        require(observation['input_pin'] == file_pin(args.input, str(Path(args.input).resolve())),
                'observed input bytes/path mismatch')
        remaining = float(options['--remaining-seconds'])
        require(math.isfinite(remaining) and 0 < remaining <= 1800, 'observed remaining budget')
    verify_chain(receipts, observations, binding, proposal)
    deadline_guard()
    return deadline_guard, ledger


def root_conditions(result, lower, upper, terminal):
    require(len(lower) == len(upper) == len(terminal) == 7, 'terminal/root dimensions')
    require(all(-1 < lo < hi < 1 and lo < tl <= th < hi
                for lo, hi, (tl, th) in zip(lower, upper, terminal)), 'all7 strict entry failed')
    require(lower[5] > Q(9, 10) and lower[6] > Q(9, 10), 'high y/goal location failed')
    require(result.get('accepted') is True and result.get('exact_qH_lt_one') is True
            and result.get('exact_qF_lt_one') is True
            and Q(result['qH_upper']) < 1 and Q(result['qF_upper']) < 1,
            'exact/public contraction failed')
    require(len(result['H_lower']) == len(result['H_upper']) == 7
            and all(lo < Q(hl) <= Q(hh) < hi for lo, hi, hl, hh in
                    zip(lower, upper, result['H_lower'], result['H_upper'])), 'strict public H inclusion')
    return True


def verify(args):
    require(math.isfinite(args.remaining_seconds) and 0 < args.remaining_seconds <= 1800,
            'remaining budget outside0..1800')
    start = time.monotonic()

    def guard():
        require(time.monotonic() - start < args.remaining_seconds, 'cooperative remaining budget expired')

    require(isinstance(args.protocol_sha256, str) and SHA.fullmatch(args.protocol_sha256), 'protocol SHA')
    protocol_data = Path(args.protocol).read_bytes()
    require(digest(protocol_data) == args.protocol_sha256, 'protocol bytes/hash mismatch')
    proposal_data = Path(args.input).read_bytes()
    protocol, proposal = decode(protocol_data), decode(proposal_data)
    binding, model, exact, roots = load_binding(Path(args.repo).resolve(), protocol,
                    args.protocol_sha256, proposal, digest(proposal_data), guard)
    if args.chunk_index is not None:
        require(args.receipts is None, 'chunk and final modes are exclusive')
        return verify_chunk(args.chunk_index, args.previous_receipt_sha256, proposal,
                            binding, model, exact, guard)
    require(args.receipts is not None and args.previous_receipt_sha256 is None, 'final ledger required')
    deadline_guard, ledger = verify_ledger(args.receipts, proposal, binding, args, guard)
    terminal = box(proposal['suffix'][-1]['x_box'])
    lower, upper, weights = root_geometry(proposal['suffix'][-1]['x_box'], proposal['root_box'])
    result = roots['check_box'](*model, lower, upper, weights)
    deadline_guard()
    root_conditions(result, lower, upper, terminal)
    return dict(binding, schema='HCCONRealEscapeCheck.v1', accepted=True, witness=True,
                status='CERTIFIED', outcome='CERTIFIED_EVENTUAL_HIGH_CONVERGENCE',
                verified_new_transitions=4096, trusted_actual_chunks=64,
                reused_old_transitions=2048, old_transitions_rechecked=0,
                prior_census_rerun=False, native_replays=0, terminal_tick=6144,
                certified_entry_upper_bound=6144, first_entry_established=False,
                unconditional_F_continuation=True, old_first_stop_unchanged=1848,
                all7_strict_entry=True, contraction_proof=result, root_box=proposal['root_box'],
                high_y_x_lower=str(lower[5]), high_goal_x_lower=str(lower[6]),
                high_goal_p_enclosure=[str((1 + lower[6]) / 2), str((1 + upper[6]) / 2)],
                deadline_utc=ledger['deadline_utc'], elapsed_seconds=time.monotonic() - start,
                limits=['Old accepted2048 and pinned fullstrip census are trusted proof dependencies, not rerun.',
                        'Actual chunk execution observations are trusted Coordinator records, not host attestation.',
                        'Final checker composes64 receipts; it does not recalculate4096 transitions.',
                        'Single lifted-binary64 exactreal unconditional trajectory only; no native/libm or primitivequantization claim.',
                        'Entry6144 is an upper bound, not first entry/escape onset/global basin/fullEngine behavior.',
                        'Chunk cooperative budget relies on caller absolute deadline and no-retry started-range journal.'])


def main():
    parser = argparse.ArgumentParser()
    for name in ('repo', 'protocol', 'protocol-sha256', 'input', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--remaining-seconds', type=float, default=1800)
    parser.add_argument('--chunk-index', type=int)
    parser.add_argument('--previous-receipt-sha256')
    parser.add_argument('--receipts')
    args = parser.parse_args()
    schema = 'HCCONRealEscapeChunk.v1' if args.chunk_index is not None else 'HCCONRealEscapeCheck.v1'
    result = {'schema': schema, 'protocol_sha256': args.protocol_sha256,
              'accepted': False, 'witness': False, 'status': 'INCONCLUSIVE'}
    try:
        result = verify(args)
    except (ValueError, KeyError, TypeError, IndexError, OSError, OverflowError) as error:
        result['reason'] = str(error)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
                                 encoding='utf-8', newline='\n')
    print(json.dumps({'accepted': result['accepted'], 'status': result['status'],
                      'reason': result.get('reason')}, ensure_ascii=False), flush=True)
    if not result['accepted']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
