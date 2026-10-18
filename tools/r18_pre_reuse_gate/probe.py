"""R18: existing native learner, sixteen fixed evaluations, separate reference/replay.

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
SPEC = ROOT / 'experiments/exp-64-pre-reuse-gate/frozen_spec.json'
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
    require(p['arms'] == ['always_on', 'pregated', 'learned_off', 'unlearned_off'], 'exact arms')
    require(cfg.pattern_lengths == (2,) and cfg.kernel.prior_gain == 0, 'fixed learned target')
    require(cfg.max_pool_candidates == 4 and len(p['execution_order']) == 16, 'fixed gate design')
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
        memory = read(out / 'memory' / ('0.json' if arm == 'unlearned_off' else '3.json'))
        gate, mode, where = arm == 'always_on', 'frozen_eval', out / 'evaluation' / item
        from tools.r18_pre_reuse_gate.policy import preflight
        before_wall=time.monotonic(); before_cpu=time.process_time()
        policy=preflight(case['observation'],bool(memory['circuits'])) if arm=='pregated' else dict(enabled=gate,reason='fixed_arm',metadata_reads=0,edge_records_read=0,chain_links_followed=0)
        gate=policy['enabled']
        policy.update(wall_seconds=time.monotonic()-before_wall,cpu_seconds=time.process_time()-before_cpu,started=before_wall,finished=time.monotonic())
    native_started=time.monotonic()
    e = execute(p, case, memory, gate, mode, where / 'progress', 'r18-' + phase + '-' + item)
    if phase=='eval':e.update(pregate=policy,native_started=native_started)
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
    f = Feedback('r18-external-' + item, d.id, obs.digest, assessment.correct,
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


def measures(e, case, truth):
    from hcr import codec
    from hcr.evaluation.reference import assess, reachable
    pending=e['packet']['document']['engine']['pending'];c=e['candidate']
    row=dict(stop=e['stop'],cost=pending['cost'],pregate=e['pregate'],actual=reachable(codec.observation_from(case['observation']),truth))
    if c is None:return dict(row,assessment=None,accepted=False,adopted_value=None)
    d=codec.adaptive_decision_from(c['decision']);a=assess(d,codec.observation_from(case['observation']),truth)
    return dict(row,cost=d.cost,assessment=codec.plain(a),accepted=c['readout']['accepted'],adopted_value=c['readout']['value'],raw_value=d.value,
        final_support_edges=[x[0] for x in d.proof.assumed_edges],primitive_depth=d.proof.primitive_depth)


def check_policy(e,case,memory,arm):
    from tools.r18_pre_reuse_gate.policy import preflight,independent_allow
    rec=e['pregate'];expected=preflight(case['observation'],bool(memory['circuits'])) if arm=='pregated' else dict(enabled=arm=='always_on',reason='fixed_arm',metadata_reads=0,edge_records_read=0,chain_links_followed=0)
    require(all(rec[k]==v for k,v in expected.items()),'gate record source binding')
    if arm=='pregated':require(expected['enabled']==independent_allow(case['observation'],bool(memory['circuits'])),'independent gate predicate')
    require(rec['started']<=rec['finished']<=e['native_started'] and rec['wall_seconds']>=0 and rec['cpu_seconds']>=0,'gate before native boundary')
    return rec['enabled']


def integers(cost):
    aliases={'signal_events','convergence_ticks','proof_reconstruction_cost','storage_cost'}
    return {k:v for k,v in cost.items() if type(v) is int and k not in aliases}


def add_cost(costs):
    result={}
    for c in costs:
        for k,v in integers(c).items():result[k]=result.get(k,0)+v
    return result


def account(out,p,rows,formation):
    ledger=read(out/'workload-stage-ledger.json')
    expected=[('init','')]+[(phase,str(i)) for i in range(3) for phase in ['train','reference','learn']]+[('eval',item) for item in p['execution_order']]
    require([(s['phase'],s['item']) for s in ledger]==expected and all(s['returncode']==0 and s['seconds']>=0 and s['child_cpu_seconds']>=0 for s in ledger),'stage ledger binding')
    init=ledger[:1];training=ledger[1:10];training_costs=[];reference_checks=0
    for i in range(3):
        e=read(out/'training'/str(i)/'execution.json');training_costs.append(e['candidate']['decision']['cost'])
        training_costs.append(formation[i]['cost']);reference_checks+=read(out/'training'/str(i)/'reference.json')['assessment']['verification_checks']
    totals=[]
    for arm in p['arms']:
        learned=arm!='unlearned_off';prefix=[]
        for k,case in enumerate(p['cases'],1):
            prefix.append(next(r for r in rows if r['case']==case['id'] and r['arm']==arm))
            stages=init+(training if learned else [])+[next(s for s in ledger if s['phase']=='eval' and s['item']==r['case']+'__'+arm) for r in prefix]
            totals.append(dict(arm=arm,K=k,native=add_cost((training_costs if learned else [])+[r['cost'] for r in prefix]),
                training_reference_verification_checks=reference_checks if learned else 0,
                gate_features={key:sum(r['pregate'][key] for r in prefix) for key in ['metadata_reads','edge_records_read','chain_links_followed']},
                gate_cpu_seconds=sum(r['pregate']['cpu_seconds'] for r in prefix),gate_wall_seconds=sum(r['pregate']['wall_seconds'] for r in prefix),
                process_stage_wall_seconds=sum(s['seconds'] for s in stages),process_stage_child_cpu_seconds=sum(s['child_cpu_seconds'] for s in stages)))
    return dict(training_native=add_cost(training_costs),training_reference_verification_checks=reference_checks,
        shared_init_stage=init[0],training_stages_wall_seconds=sum(s['seconds'] for s in training),training_stages_child_cpu_seconds=sum(s['child_cpu_seconds'] for s in training),prefix_totals=totals,
        accounting='observed shared training charged to learned strategies; K actual prefix uses; no heterogeneous unit sum; stage times already include gate',independent_end_to_end_replicates=False)


def audit(out, publish=True):
    from hcr import codec
    from hcr.evaluation.reference import assess
    from hcr.evaluation.review_audit import packet_states
    from hcr.model import Feedback
    p, _ = inputs(); worlds = read(WORLD); formation = []
    for i, case in enumerate(p['training']):
        where = out / 'training' / str(i); e = read(where / 'execution.json')
        memory = read(out / 'memory' / (str(i) + '.json'))
        check_execution(e, case, memory, True, 'train', 'r18-train-' + str(i), p)
        ref = read(where / 'reference.json'); d = codec.adaptive_decision_from(e['candidate']['decision'])
        obs = codec.observation_from(case['observation']); a = assess(d, obs, worlds[case['id']])
        expected = Feedback('r18-external-' + str(i), d.id, obs.digest, a.correct, a.proof_valid and a.assumption_correct is True)
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
            m = read(out / 'memory' / ('0.json' if arm == 'unlearned_off' else '3.json'))
            gate=check_policy(e,case,m,arm)
            check_execution(e, case, m, gate, 'frozen_eval', 'r18-eval-' + item, p)
            rows.append(dict(case=case['id'], arm=arm, **measures(e, case, worlds[case['id']])))
            if not rejected:
                # A real adversarial check of source-bound readout/proof linkage, no native run.
                for field in ['value', 'proof', 'gate']:
                    bad = deepcopy(e)
                    if field == 'value': bad['candidate']['decision']['value'] = not bad['candidate']['decision']['value']
                    elif field=='proof': bad['candidate']['decision']['proof']['primitive_depth'] = 999
                    else: bad['pregate']['enabled']=not bad['pregate']['enabled']
                    try:
                        check_policy(bad,case,m,arm)
                        check_execution(bad, case, m, gate, 'frozen_eval', 'r18-eval-' + item, p)
                    except (ValueError, AssertionError, KeyError): rejected.append(field)
                    else: raise ValueError('tamper accepted: ' + field)
    require(len(list((out / 'evaluation').glob('*/execution.json'))) == 16, 'exact sixteen evaluations')
    predictions=[]
    for case in p['cases']:
        cells={r['arm']:r for r in rows if r['case']==case['id']};g=cells['pregated'];on=cells['always_on'];off=cells['learned_off'];empty=cells['unlearned_off']
        quality=lambda r:r['assessment'] is not None and r['assessment']['correct'] is True and r['assessment']['proof_valid'] and r['assessment']['assumption_correct'] is True and r['accepted'] and r['adopted_value']==r['actual']
        predictions.append(dict(case=case['id'],quality=all(quality(r) for r in cells.values()),gate_expected=g['pregate']['enabled']==case['expected_gate'],
            native_dispatch_equal=integers(g['cost'])==integers((on if g['pregate']['enabled'] else off)['cost']),
            denied_recall_binding_pool_zero=None if g['pregate']['enabled'] else all(g['cost'][key]==0 for key in ['recall_checks','binding_checks','pool_calls']),
            off_unlearned_equal=integers(off['cost'])==integers(empty['cost'])))
    summary=dict(status='TECHNICAL_CHECK_RECORDED_AND_REPLAYED',training=formation,rows=rows,predictions=predictions,
        accounting=account(out,p,rows,formation),rejected_mutations=rejected,native_training_executions=3,native_evaluation_executions=16,automatic_retry=False,
        structural_families=2,independent_discovery_samples=0,generalization_established=False,learning_efficiency_established=False,actual_energy_joules=None,peak_rss_bytes=None)
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
        before_usage=resource.getrusage(resource.RUSAGE_CHILDREN)
        with (out / ('stage-' + phase + '-' + item + '.stdout')).open('xb') as stdout, (out / ('stage-' + phase + '-' + item + '.stderr')).open('xb') as stderr:
            child = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, env=dict(os.environ, PYTHONPATH=str(ROOT / 'src') + os.pathsep + str(ROOT), PYTHONDONTWRITEBYTECODE='1'), preexec_fn=limit)
            try: rc = child.wait(timeout=min(60 if phase != 'audit' else 90, remaining))
            except BaseException:
                child.kill(); child.wait(); raise
        after_usage=resource.getrusage(resource.RUSAGE_CHILDREN)
        stages.append(dict(phase=phase,item=item,seconds=time.monotonic()-before,returncode=rc,child_cpu_seconds=after_usage.ru_utime+after_usage.ru_stime-before_usage.ru_utime-before_usage.ru_stime))
        require(rc == 0, 'stage failure: ' + phase + ' ' + item)
        require(sum(f.stat().st_size for f in out.rglob('*') if f.is_file()) < 128 * 1024**2, '128MiB output cap')
    try:
        manifest = read(ROOT / 'source_manifest.json')
        require(all(digest(ROOT / n) == h for n,h in manifest.items()), 'source hash preflight')
        stage('init')
        for i in range(3):
            for phase in ['train', 'reference', 'learn']: stage(phase, str(i))
        for item in p['execution_order']:stage('eval',item)
        put(out/'workload-stage-ledger.json',stages)
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
    from tools.r18_pre_reuse_gate.policy import preflight,independent_allow
    p,_=inputs();checks=[]
    for c in p['cases']:
        a=preflight(c['observation'],True)
        require(a['enabled']==c['expected_gate']==independent_allow(c['observation'],True),'frozen gate predicate')
        checks.append(c['id'])
    obs=p['cases'][0]['observation']
    require(not preflight(obs,False)['enabled'],'empty memory')
    for score in [None,0,-1,0.99]:
        bad=deepcopy(obs);bad['edges'][0]['score']=score
        require(not preflight(bad,True)['enabled'],'measurement boundary')
    bad=deepcopy(obs);bad['edges'][-1]['target']='A'
    require(not preflight(bad,True)['enabled'],'cycle or endpoint')
    bad=deepcopy(obs);bad['edges'].pop()
    require(not preflight(bad,True)['enabled'],'short span')
    bad=deepcopy(obs);bad['edges'].reverse()
    require(preflight(bad,True)['enabled'],'edge order independent')
    require(add_cost([dict(kernel_ticks=2,convergence_ticks=2,storage_bytes=3,storage_cost=3),dict(kernel_ticks=4,storage_bytes=5)])==dict(kernel_ticks=6,storage_bytes=8),'no alias double counting')
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        out=Path(directory)
        for i in range(3):
            put(out/'training'/str(i)/'execution.json',dict(candidate=dict(decision=dict(cost=dict(kernel_ticks=2)))))
            put(out/'training'/str(i)/'reference.json',dict(assessment=dict(verification_checks=7)))
        tags=[('init','')]+[(phase,str(i)) for i in range(3) for phase in ['train','reference','learn']]+[('eval',item) for item in p['execution_order']]
        put(out/'workload-stage-ledger.json',[dict(phase=phase,item=item,returncode=0,seconds=3,child_cpu_seconds=2) for phase,item in tags])
        rows=[dict(case=c['id'],arm=arm,cost=dict(kernel_ticks=5),pregate=dict(metadata_reads=1,edge_records_read=1,chain_links_followed=1,wall_seconds=.1,cpu_seconds=.05)) for c in p['cases'] for arm in p['arms']]
        totals=account(out,p,rows,[dict(cost=dict(kernel_ticks=1)) for _ in range(3)])
        for row in totals['prefix_totals']:
            trained=row['arm']!='unlearned_off';k=row['K']
            require(row['native']['kernel_ticks']==(9 if trained else 0)+5*k,'training charged exactly once')
            require(row['training_reference_verification_checks']==(21 if trained else 0),'reference included')
            require(row['gate_features']['edge_records_read']==k,'gate feature cost included')
            require(row['process_stage_wall_seconds']==(30 if trained else 3)+3*k,'stage wall includes gate; no double charge')
            require(row['process_stage_child_cpu_seconds']==(20 if trained else 2)+2*k,'whole child CPU accounting')
    print(json.dumps(dict(policy_checks=12,cost_alias_checks=1,synthetic_prefix_accounting_checks=80,native_executions=0)))


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
