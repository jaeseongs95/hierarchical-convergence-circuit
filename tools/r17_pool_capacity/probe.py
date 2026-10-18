"""R17: existing native learner, twelve fixed evaluations, separate reference/replay.

No engine changes, parameter search, automatic retries or outcome-dependent inputs.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / 'experiments/exp-63-pool-capacity/frozen_spec.json'
WORLD = SPEC.with_name('reference_worlds.json')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n').encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    from hcr.codec import adaptive_config_from
    p = read(SPEC)
    cfg = adaptive_config_from(p['config'])
    require(p['limits'] == dict(max_advances_per_session=16, max_kernel_ticks_per_session=5120), 'fixed limits')
    require(len(p['training']) == 3 and len(p['cases']) == 4, 'exact design')
    require(p['arms'] == ['learned_on', 'learned_off', 'unlearned_on'], 'exact arms')
    require(cfg.pattern_lengths == (2,) and cfg.kernel.prior_gain == 0, 'fixed learned target')
    require(cfg.max_pool_candidates == 4 and [c['fanout'] for c in p['cases']] == [4,4,5,5], 'fixed capacity boundary')
    return p, cfg


def native(out, phase, item):
    from hcr import codec
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Feedback
    from hcr.sessions import AdaptiveSession
    from tools.r063_formation.worker import execute
    p, cfg = inputs()
    if phase == 'init':
        put(out / 'memory/0.json', AdaptiveMemory.empty(cfg).document())
        return
    if phase == 'learn':
        where = out / 'training' / item
        e = read(where / 'execution.json')
        ref = read(where / 'reference.json')
        require(ref['execution_sha256'] == digest(where / 'execution.json'), 'feedback source binding')
        require(ref['assessment']['correct'] is True and ref['feedback']['proof_valid'] is True, 'training invalid; do not substitute')
        session = AdaptiveSession.from_packet(e['candidate']['packet'])
        patch = session.feedback(Feedback(**ref['feedback']))
        put(where / 'learning.json', dict(packet=session.packet(), patch=patch, feedback=ref['feedback']))
        put(out / 'memory' / (str(int(item) + 1) + '.json'), session.memory_document)
        return
    if phase == 'train':
        case = p['training'][int(item)]
        memory = read(out / 'memory' / (item + '.json'))
        gate, mode, where = True, 'train', out / 'training' / item
    else:
        case_id, arm = item.split('__')
        case = next(c for c in p['cases'] if c['id'] == case_id)
        memory = read(out / 'memory' / ('0.json' if arm == 'unlearned_on' else '3.json'))
        gate, mode, where = arm != 'learned_off', 'frozen_eval', out / 'evaluation' / item
    e = execute(p, case, memory, gate, mode, where / 'progress', 'r17-' + phase + '-' + item)
    put(where / 'execution.json', e)


def reference(out, item):
    from hcr import codec
    from hcr.evaluation.reference import assess
    from hcr.model import Feedback
    p, _ = inputs()
    case = p['training'][int(item)]
    where = out / 'training' / item
    e = read(where / 'execution.json')
    require(e['candidate'] is not None, 'no training candidate')
    d = codec.adaptive_decision_from(e['candidate']['decision'])
    obs = codec.observation_from(case['observation'])
    assessment = assess(d, obs, read(WORLD)[case['id']])
    f = Feedback('r17-external-' + item, d.id, obs.digest, assessment.correct,
                 assessment.proof_valid and assessment.assumption_correct is True)
    put(where / 'reference.json', dict(execution_sha256=digest(where / 'execution.json'),
        assessment=codec.plain(assessment), feedback=codec.plain(f)))


def check_execution(e, case, memory, gate, mode, identity, p):
    from hcr.evaluation.review_audit import packet_states, verify_candidate
    from hcr.prior_policy import read_scope
    states, report = packet_states(e['packet'])
    require(report['verified'], 'independent journal replay')
    doc = e['packet']['document']; core = doc['engine']; pending = core['pending']
    require(doc['session_id'] == identity and core['config'] == p['config'], 'identity/config')
    require(core['memory'] == memory and states[0]['memory'] == memory, 'memory boundary')
    require(read_scope(core) == 'route_only', 'route-only judgment')
    require(core['switches'] == dict(use_circuits=gate, top_down=True, allow_reexpansion=True), 'switches')
    require(not core['held'] and not core['feedback'] and not core['requests'], 'no hidden adaptation')
    require(pending['observation'] == case['observation'] and pending['mode'] == mode, 'same public information')
    require([t['operation'] for t in doc['transitions']] == ['init', 'begin'] + ['advance'] * e['advances'], 'exact operations')
    require(e['advances'] <= p['limits']['max_advances_per_session'] and pending['cost']['kernel_ticks'] <= 5120, 'session budget')
    require(e['ready'] is pending['ready'], 'readiness')
    if e['candidate'] is not None:
        require(e['ready'] and e['stop'] == 'readout_ready', 'completed candidate')
        verify_candidate(e['candidate'], e['packet'], states)
    else:
        require(not e['ready'] and e['stop'] == 'external_compute_budget', 'partial retained')
    return states


def trace_measures(events, fanout):
    scans = [x['payload'] for x in events if x['event'] == 'r02_binding_scan' and x['payload']['prefix']['path'] == []]
    expansions = [x['payload'] for x in events if x['event'] == 'r02_expansion']
    root = scans[0] if scans else None
    root_pools = [x for x in events if x['event'] == 'r02_pool_result' and any(
        n['event'] == 'r02_network' and n['payload'].get('kind') == 'pool' and n['payload']['network_id'] == x['payload']['network_id']
        and n['payload']['metadata']['prefix']['path'] == [] for n in events)]
    # Use actual network metadata: pool results are also independently journal-verified.
    pool_networks = [x for x in events if x['event'] == 'r02_network' and x['payload'].get('kind') == 'pool' and x['payload']['metadata']['prefix']['path'] == []]
    added_paths = [a['path'] for e in expansions for a in e['added']]
    return dict(root_scan=None if root is None else dict(complete=root['complete'], fallback_reason=root['fallback_reason'], matched=[a['binding']['edge_order'] for a in root['matched']], scan_count=len(root['scans'])),
        root_pool_networks=len(pool_networks), root_pool_results=len(root_pools),
        first_candidate=None if not expansions else expansions[0]['candidate'],
        all_branch_prefixes_retained=all(any(path[:2] == [0,i] for path in added_paths) for i in range(1,fanout+1)),
        negative_before_coverage=any(x['event'] == 'r02_progress' and x['payload']['mismatch']['kind'] == 'negative_requires_dependency_coverage' for x in events))


def measures(e, case, truth):
    from hcr import codec
    from hcr.evaluation.reference import assess, reachable
    doc=e['packet']['document']; pending=doc['engine']['pending']; c=e['candidate']
    row=dict(stop=e['stop'], advances=e['advances'], graph_complete=pending['workspace']['frontier'] == [], cost=pending['cost'],
        actual=reachable(codec.observation_from(case['observation']), truth), **trace_measures(doc['events'], case['fanout']))
    if c is None: return dict(row, raw_value=None, accepted=False, adopted_value=None, assessment=None, final_support_edges=[], primitive_depth=None)
    d=codec.adaptive_decision_from(c['decision']); a=assess(d, codec.observation_from(case['observation']), truth)
    return dict(row, raw_value=d.value, accepted=c['readout']['accepted'], adopted_value=c['readout']['value'], assessment=codec.plain(a),
        final_support_edges=[x[0] for x in d.proof.assumed_edges], primitive_depth=d.proof.primitive_depth, cost=d.cost)


def audit(out, publish=True):
    from hcr import codec
    from hcr.evaluation.reference import assess
    from hcr.evaluation.review_audit import packet_states
    from hcr.model import Feedback
    p, _ = inputs(); worlds = read(WORLD); formation = []
    for i, case in enumerate(p['training']):
        where = out / 'training' / str(i); e = read(where / 'execution.json')
        memory = read(out / 'memory' / (str(i) + '.json'))
        check_execution(e, case, memory, True, 'train', 'r17-train-' + str(i), p)
        ref = read(where / 'reference.json'); d = codec.adaptive_decision_from(e['candidate']['decision'])
        obs = codec.observation_from(case['observation']); a = assess(d, obs, worlds[case['id']])
        expected = Feedback('r17-external-' + str(i), d.id, obs.digest, a.correct, a.proof_valid and a.assumption_correct is True)
        require(ref == dict(execution_sha256=digest(where / 'execution.json'), assessment=codec.plain(a), feedback=codec.plain(expected)), 'external feedback recheck')
        learned = read(where / 'learning.json'); _, replay = packet_states(learned['packet'])
        require(replay['verified'], 'independent learning replay')
        before = e['candidate']['packet']['document']; after = learned['packet']['document']
        require(after['transitions'][:-1] == before['transitions'] and after['events'][:-2] == before['events'], 'exact assessed branch')
        require(after['transitions'][-1]['operation'] == 'feedback' and learned['feedback'] == ref['feedback'], 'feedback operation')
        memory_after = read(out / 'memory' / (str(i + 1) + '.json'))
        require(after['engine']['memory'] == memory_after, 'memory chain publication')
        formation.append(dict(episode=i, circuits=len(memory_after['circuits']), patch=learned['patch'], cost=after['events'][-1]['payload']['cost']))
    memory = read(out / 'memory/3.json')
    require(len(memory['circuits']) == 1 and len(memory['circuits'][0]['pattern']['relations']) == 2, 'construct: single learned length2 pattern')
    require(memory['circuits'][0]['evidence_episodes'] == [c['observation']['episode_id'] for c in p['training']], 'real training provenance')
    rows = []; rejected = []
    for case in p['cases']:
        for arm in p['arms']:
            item = case['id'] + '__' + arm; e = read(out / 'evaluation' / item / 'execution.json')
            m = read(out / 'memory' / ('0.json' if arm == 'unlearned_on' else '3.json'))
            check_execution(e, case, m, arm != 'learned_off', 'frozen_eval', 'r17-eval-' + item, p)
            rows.append(dict(case=case['id'], arm=arm, **measures(e, case, worlds[case['id']])))
            if not rejected:
                # A real adversarial check of source-bound readout/proof linkage, no native run.
                for field in ['value', 'proof']:
                    bad = deepcopy(e)
                    if field == 'value': bad['candidate']['decision']['value'] = not bad['candidate']['decision']['value']
                    else: bad['candidate']['decision']['proof']['primitive_depth'] = 999
                    try: check_execution(bad, case, m, arm != 'learned_off', 'frozen_eval', 'r17-eval-' + item, p)
                    except (ValueError, AssertionError, KeyError): rejected.append(field)
                    else: raise ValueError('tamper accepted: ' + field)
    require(len(list((out / 'evaluation').glob('*/execution.json'))) == 12, 'exact twelve evaluations')
    predictions = []
    for case in p['cases']:
        cells = {r['arm']: r for r in rows if r['case'] == case['id']}; on = cells['learned_on']; off = cells['learned_off']; empty = cells['unlearned_on']
        quality = lambda r: r['assessment'] is not None and r['assessment']['correct'] is True and r['assessment']['proof_valid'] and r['assessment']['assumption_correct'] is True and r['accepted'] and r['adopted_value'] == r['actual']
        supported = all(quality(r) for r in cells.values())
        available = all(r['assessment'] is not None for r in cells.values())
        scan=on['root_scan']; first=on['first_candidate']; n=case['fanout']
        capacity=(scan is not None and len(scan['matched']) == n and first is not None and
            ((n == 4 and scan['complete'] and scan['fallback_reason'] is None and first['source'] == 'circuit' and on['root_pool_networks'] == 1 and on['root_pool_results'] == 1) or
             (n == 5 and not scan['complete'] and scan['fallback_reason'] == 'pool_capacity' and first['source'] == 'primitive' and first['edges'] == [0] and on['root_pool_networks'] == 0 and on['root_pool_results'] == 0)))
        predictions.append(dict(case=case['id'], quality='not_evaluable' if not available else 'supported' if supported else 'falsified',
            capacity_boundary=capacity, all_branch_prefixes_retained=on['all_branch_prefixes_retained'],
            expansion_delta=on['cost']['expansions']-off['cost']['expansions'], kernel_tick_delta=on['cost']['kernel_ticks']-off['cost']['kernel_ticks'],
            off_empty_integer_cost_equal={k:v for k,v in off['cost'].items() if type(v) is int} == {k:v for k,v in empty['cost'].items() if type(v) is int},
            last_branch_final_support=(set(on['final_support_edges']) == {'e0',f'e{n}',f'e{n+1}'}) if case['expected_open'] else None))
    summary = dict(status='TECHNICAL_CHECK_RECORDED_AND_REPLAYED', training=formation, rows=rows, predictions=predictions,
        rejected_mutations=rejected, native_training_executions=3, native_evaluation_executions=12, automatic_retry=False,
        structural_families=1, independent_discovery_samples=0, generalization_established=False, learning_efficiency_established=False,
        actual_energy_joules=None, peak_rss_bytes=None)
    if publish: put(out / 'summary.json', summary)
    return summary


def run(started):
    import resource
    import signal
    out = ROOT / 'runs/technical'; out.mkdir(parents=True, exist_ok=False)
    deadline = started + 600
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('600s total limit')))
    signal.alarm(max(1, int(deadline - time.monotonic())))
    p, _ = inputs(); stages = []
    def stage(phase, item='', reserve=110):
        remaining = deadline - time.monotonic() - reserve
        require(remaining > 0, 'reserve exhausted; do not start more work')
        cmd = [sys.executable, '-B', str(Path(__file__).resolve()), '--phase', phase, '--out', str(out), '--item', item]
        def limit(): resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
        before = time.monotonic()
        with (out / ('stage-' + phase + '-' + item + '.stdout')).open('xb') as stdout, (out / ('stage-' + phase + '-' + item + '.stderr')).open('xb') as stderr:
            child = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, env=dict(os.environ, PYTHONPATH=str(ROOT / 'src') + os.pathsep + str(ROOT), PYTHONDONTWRITEBYTECODE='1'), preexec_fn=limit)
            try: rc = child.wait(timeout=min(60 if phase != 'audit' else 90, remaining))
            except BaseException:
                child.kill(); child.wait(); raise
        stages.append(dict(phase=phase, item=item, seconds=time.monotonic()-before, returncode=rc))
        require(rc == 0, 'stage failure: ' + phase + ' ' + item)
        require(sum(f.stat().st_size for f in out.rglob('*') if f.is_file()) < 128 * 1024**2, '128MiB output cap')
    try:
        manifest = read(ROOT / 'source_manifest.json')
        require(all(digest(ROOT / n) == h for n,h in manifest.items()), 'source hash preflight')
        stage('init')
        for i in range(3):
            for phase in ['train', 'reference', 'learn']: stage(phase, str(i))
        for case in p['cases']:
            for arm in p['arms']: stage('eval', case['id'] + '__' + arm)
        stage('audit', reserve=20)
        require(all(digest(ROOT / n) == h for n,h in manifest.items()), 'source changed during run')
        put(out / 'result.json', dict(status='COMPLETED', seconds_before_seal=time.monotonic()-started, stages=stages,
            python=sys.version, host=os.uname().nodename, source_manifest_sha256=digest(ROOT/'source_manifest.json'), worker_limit=1,
            per_child_address_space_limit_bytes=512*1024**2, total_wall_limit_seconds=600, source_unchanged=True))
    except BaseException:
        put(out / 'failure.json', dict(traceback=traceback.format_exc(), stages=stages, elapsed_seconds=time.monotonic()-started, automatic_retry=False))
        raise
    finally:
        put(out / 'manifest.json', {f.relative_to(out).as_posix():digest(f) for f in sorted(out.rglob('*')) if f.is_file()})
        with zipfile.ZipFile(ROOT / 'evidence.zip', 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.rglob('*')):
                if f.is_file(): z.write(f, 'technical/' + f.relative_to(out).as_posix())
        put(ROOT / 'completion.json', dict(total_seconds_including_seal=time.monotonic()-started,
            evidence_sha256=digest(ROOT/'evidence.zip'), evidence_bytes=(ROOT/'evidence.zip').stat().st_size,
            completed=(out/'result.json').is_file(), within_600_seconds=time.monotonic()-started <= 600))
        signal.alarm(0)


def selfcheck():
    # Synthetic trace inventory only; no AdaptiveSession or native execution.
    events=[dict(event='r02_binding_scan', payload=dict(prefix=dict(path=[]), complete=False, fallback_reason='pool_capacity', matched=[dict(binding=dict(edge_order=[0,i])) for i in range(1,6)], scans=[])),
        dict(event='r02_expansion', payload=dict(candidate=dict(source='primitive',edges=[0]), added=[dict(path=[0])])),
        dict(event='r02_expansion', payload=dict(candidate=dict(source='circuit',edges=[5,6]), added=[dict(path=[0,i]) for i in range(1,6)]))]
    a=trace_measures(events,5)
    require(not a['root_scan']['complete'] and a['root_pool_networks']==0 and a['all_branch_prefixes_retained'], 'synthetic fallback inventory')
    events[-1]['payload']['added'].pop()
    require(not trace_measures(events,5)['all_branch_prefixes_retained'], 'lost last branch must be detected')
    events.extend([dict(event='r02_network',payload=dict(kind='pool', network_id='n', metadata=dict(prefix=dict(path=[])))),
        dict(event='r02_pool_result',payload=dict(network_id='n'))])
    a=trace_measures(events,5)
    require(a['root_pool_networks']==1 and a['root_pool_results']==1, 'unexpected root pool must be counted')
    print(json.dumps(dict(synthetic_checks=3, native_executions=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', required=True, choices=['init','train','reference','learn','eval','audit','verify','run','selfcheck'])
    parser.add_argument('--out', type=Path)
    parser.add_argument('--item', default='')
    parser.add_argument('--started', type=float)
    args = parser.parse_args()
    if args.phase == 'selfcheck': selfcheck()
    elif args.phase == 'run': run(args.started)
    elif args.phase == 'reference': reference(args.out, args.item)
    elif args.phase == 'audit': audit(args.out)
    elif args.phase == 'verify':
        require(audit(args.out, publish=False) == read(args.out/'summary.json'), 'summary recomputation differs')
        require(all(digest(args.out/n) == h for n,h in read(args.out/'manifest.json').items()), 'raw manifest differs')
        print(json.dumps(dict(verified=True, independent_native_executions=0, summary_recomputed=True)))
    else: native(args.out, args.phase, args.item)
