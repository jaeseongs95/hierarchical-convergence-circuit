"""R20 bounded evidence gate experiment using the unchanged R19 task/kernel."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr.codec import plain
from hcr.model import Config, fingerprint
from tools.r19_cross_level import probe as common
from tools.r20_evidence_feedback.policy import decide,require,validate

SPEC=ROOT/'experiments/exp-66-evidence-feedback/frozen_spec.json'
read,put,sha=common.read,common.put,common.sha
def spec():return read(SPEC)
def unpack(record):return {k:v for k,v in record.items() if k!='kind'}
def promotion(case,lower,round_number,gate):
    return dict(common.promote(case,lower,round_number),gate_sha256=fingerprint(gate))


def execute(case,arm,p):
    validate(case);require(arm in p['arms'],'arm')
    cfg=Config(**p['kernel']);low_program,high_program=common.programs(cfg)
    def low_run(feedback):
        return common.settle_one(low_program,dict(f0=cfg.evidence_gain*case['measurements'][0],
            f1=cfg.evidence_gain*case['measurements'][1],goal=feedback),cfg)
    def high_run(packet):
        return common.settle_one(high_program,dict(promoted=cfg.evidence_gain*(2*packet['raw_confidence']-1),
            context=cfg.evidence_gain*case['context']),cfg)
    lower=low_run(0.0);kernels=[dict(kind='lower_initial',**lower)];packets=[]
    gate=None;gate_wall=0.0
    if arm=='gated':
        started=time.perf_counter();gate=decide(case,lower,p);gate_wall=time.perf_counter()-started
    feedback=0.0;relation=None
    if gate is None or gate['action']!='abstain':
        packet=promotion(case,lower,0,gate);packets.append(packet)
        upper=high_run(packet);kernels.append(dict(kind='upper_initial',**upper));relation=upper['adopted']
        if arm=='unconditional' or (gate is not None and gate['action']=='feedback'):
            feedback=p['feedback_gain']*(upper['state']['match_A']-upper['state']['match_B'])
            lower=low_run(feedback);kernels.append(dict(kind='lower_recomputed',**lower))
            packet=promotion(case,lower,1,gate);packets.append(packet)
            upper=high_run(packet);kernels.append(dict(kind='upper_recomputed',**upper));relation=upper['adopted']
    withheld=arm=='gated' and lower['adopted'] is None
    if withheld:relation=None
    return dict(public=case,arm=arm,gate=gate,gate_wall_seconds=gate_wall,feedback=feedback,
        category=lower['adopted'],relation=relation,relation_withheld_due_to_lower=withheld,
        kernels=kernels,promotions=packets,native_settle_calls=len(kernels),training_calls=0,
        adapter_vectors=dict(lower=sum(k['kind'].startswith('lower') for k in kernels),
            upper=len(packets),feedback=1 if len(kernels)==4 else 0),
        native_adaptive_session=False,native_route_proof=False)


def audit_execution(e,case,arm,p,tolerance=0.0):
    validate(case);require(e['public']==case and e['arm']==arm,'frozen public binding')
    lo,hi=common.programs(Config(**p['kernel']));lower=unpack(e['kernels'][0])
    expected_gate=decide(case,lower,p) if arm=='gated' else None
    require(e['gate']==expected_gate,'gate binding')
    kinds=['lower_initial']
    if expected_gate is None or expected_gate['action']!='abstain':
        kinds.append('upper_initial')
        if arm=='unconditional' or (expected_gate and expected_gate['action']=='feedback'):
            kinds+=['lower_recomputed','upper_recomputed']
    require([k['kind'] for k in e['kernels']]==kinds and e['native_settle_calls']==len(kinds),'cost-before-upper branch')
    require(len(e['promotions'])==len(kinds)//2,'promotion count')
    require(e['training_calls']==0 and not e['native_adaptive_session'] and not e['native_route_proof'],'scope flags')
    require(e['gate_wall_seconds']>=0 and (arm=='gated' or e['gate_wall_seconds']==0),'gate timing')
    maximum_error=0.0
    for k in e['kernels']:
        require(k['program']==plain(lo if k['kind'].startswith('lower') else hi),'fixed program')
        maximum_error=max(maximum_error,common.independent_kernel(k,p['kernel'],tolerance))
    feedback=0.0
    for round_number in range((len(kinds)+1)//2):
        low=e['kernels'][2*round_number]
        require(low['drives']==dict(f0=p['kernel']['evidence_gain']*case['measurements'][0],
            f1=p['kernel']['evidence_gain']*case['measurements'][1],goal=feedback),'lower drive')
        if 2*round_number+1<len(kinds):
            upper=e['kernels'][2*round_number+1];packet=e['promotions'][round_number]
            require(packet==promotion(case,unpack(low),round_number,expected_gate),'promotion lineage/revision/value')
            require(upper['drives']==dict(promoted=p['kernel']['evidence_gain']*(2*packet['raw_confidence']-1),
                context=p['kernel']['evidence_gain']*case['context']),'upper drive')
            feedback=p['feedback_gain']*(upper['state']['match_A']-upper['state']['match_B'])
    last_lower=e['kernels'][-2] if len(kinds)%2==0 else e['kernels'][-1]
    withheld=arm=='gated' and last_lower['adopted'] is None
    relation=None if len(kinds)==1 or withheld else e['kernels'][-1]['adopted']
    require(e['category']==last_lower['adopted'] and e['relation']==relation and e['relation_withheld_due_to_lower']==withheld,'adoption contract')
    expected_feedback=p['feedback_gain']*(e['kernels'][1]['state']['match_A']-e['kernels'][1]['state']['match_B']) if len(kinds)==4 else 0.0
    require(e['feedback']==expected_feedback,'feedback drive')
    require(e['adapter_vectors']==dict(lower=(len(kinds)+1)//2,upper=len(kinds)//2,feedback=1 if len(kinds)==4 else 0),'adapter vectors')
    return maximum_error


def audit(out):
    p=spec();truth=read(SPEC.with_name('reference.json'));rows=[];rejected=[]
    for cell in p['cases']:
        key,case=cell['key'],cell['public']
        for arm in p['arms']:
            path=out/(key+'__'+arm+'.json');e=read(path)
            error=audit_execution(e,case,arm,p,p['numeric_replay_absolute_tolerance_server'])
            if key=='independent_A' and arm=='gated':
                for mutation in ['gate_action','promotion_revision','promotion_value','tick_state','program_bias']:
                    bad=deepcopy(e)
                    if mutation=='gate_action':bad['gate']['action']='abstain'
                    elif mutation=='promotion_revision':bad['promotions'][0]['revision']+=1
                    elif mutation=='promotion_value':bad['promotions'][0]['raw_confidence']+=.1
                    elif mutation=='tick_state':bad['kernels'][0]['ticks'][0]['state']['goal']+=.01
                    else:bad['kernels'][0]['program']['groups'][0]['bias']+=.1
                    try:audit_execution(bad,case,arm,p,p['numeric_replay_absolute_tolerance_server'])
                    except (ValueError,AssertionError):rejected.append(mutation)
                    else:raise ValueError('mutation accepted: '+mutation)
            ref=truth[key]
            rows.append(dict(key=key,arm=arm,revision=case['revision'],category=e['category'],relation=e['relation'],
                category_correct=e['category'] is not None and e['category']==ref['category'],
                category_wrong=e['category'] is not None and e['category']!=ref['category'],category_abstained=e['category'] is None,
                relation_correct=e['relation'] is not None and e['relation']==ref['relation'],
                relation_wrong=e['relation'] is not None and e['relation']!=ref['relation'],relation_abstained=e['relation'] is None,
                lower_initial=e['kernels'][0]['adopted'],gate=e['gate'],gate_wall_seconds=e['gate_wall_seconds'],
                native_settle_calls=len(e['kernels']),kernel_ticks=sum(k['cost']['kernel_ticks'] for k in e['kernels']),
                group_updates=sum(k['cost']['group_updates'] for k in e['kernels']),
                signal_transmissions=sum(k['cost']['signal_transmissions'] for k in e['kernels']),
                promotion_bytes=sum(len(json.dumps(packet,sort_keys=True).encode()) for packet in e['promotions']),
                execution_bytes=path.stat().st_size,numeric_replay_max_absolute_error=error))
    require(len(rows)==33 and len(rejected)==5,'exact frozen matrix and mutations')
    same_predictions={}
    for arm in p['arms']:
        left=next(row for row in rows if row['key']=='independent_B' and row['arm']==arm)
        right=next(row for row in rows if row['key']=='independent_wrong' and row['arm']==arm)
        same_predictions[arm]=all(left[k]==right[k] for k in ['category','relation','kernel_ticks','group_updates','signal_transmissions'])
        require(same_predictions[arm],'information-limit paired worlds changed behavior')
    totals={arm:{name:sum(row[name] for row in rows if row['arm']==arm) for name in
        ['native_settle_calls','kernel_ticks','group_updates','signal_transmissions','category_correct','category_wrong',
         'category_abstained','relation_correct','relation_wrong','relation_abstained','promotion_bytes','execution_bytes','gate_wall_seconds']} for arm in p['arms']}
    require(sum(row['native_settle_calls'] for row in rows)<=p['maximum_native_settle_calls'],'native settle budget')
    put(out/'summary.json',dict(status='TECHNICAL_PROBE_REPLAYED',rows=rows,totals=totals,rejected_mutations=rejected,
        numeric_replay_absolute_tolerance=p['numeric_replay_absolute_tolerance_server'],training_calls=0,
        paired_world_same_predictions=same_predictions,
        source_independence_is_declared=True,statistical_reliability_established=False,learning_efficiency_established=False))


def run(started):
    import resource
    out=ROOT/'runs/technical';out.mkdir(parents=True,exist_ok=False)
    stages=[];deadline=started+580;failure=None;manifest=read(ROOT/'source_manifest.json')
    def source_check():return {name:sha(ROOT/name)==digest for name,digest in manifest.items()}
    def stage(phase,item=''):
        require(deadline-time.monotonic()>30,'budget reserve')
        before=time.monotonic();usage=resource.getrusage(resource.RUSAGE_CHILDREN)
        def limit():resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
        with (out/(phase+'-'+item+'.stdout')).open('xb') as stdout,(out/(phase+'-'+item+'.stderr')).open('xb') as stderr:
            child=subprocess.Popen([sys.executable,'-B',str(Path(__file__)),'--phase',phase,'--item',item],stdout=stdout,stderr=stderr,preexec_fn=limit)
            try:rc=child.wait(timeout=min(60,deadline-time.monotonic()-20))
            except BaseException:child.kill();child.wait();raise
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        stages.append(dict(phase=phase,item=item,returncode=rc,wall_seconds=time.monotonic()-before,
            child_cpu_seconds=after.ru_utime+after.ru_stime-usage.ru_utime-usage.ru_stime))
        require(rc==0,'stage failure '+phase+' '+item)
        require(sum(f.stat().st_size for f in out.rglob('*') if f.is_file())<128*1024**2,'raw size')
    try:
        require(all(source_check().values()),'source preflight')
        stage('preparation')
        for cell in spec()['cases']:
            for arm in spec()['arms']:stage('case',cell['key']+'__'+arm)
        stage('audit')
    except BaseException:failure=traceback.format_exc()
    finally:
        post=source_check();put(out/'source-postcheck.json',dict(unchanged=all(post.values()),files=post))
        if not all(post.values()):failure=(failure or '')+'\nsource postcheck failed'
        if failure:put(out/'failure.json',dict(traceback=failure,stages=stages,automatic_retry=False))
        put(out/'result.json',dict(status='FAILED' if failure else 'COMPLETED',stages=stages,source_unchanged=all(post.values()),
            source_manifest_sha256=sha(ROOT/'source_manifest.json'),seconds_before_seal=time.monotonic()-started,
            host=os.uname().nodename,python=sys.version,total_wall_limit_seconds=600,automatic_retry=False))
        put(out/'manifest.json',{f.relative_to(out).as_posix():sha(f) for f in sorted(out.rglob('*')) if f.is_file()})
        with zipfile.ZipFile(ROOT/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.rglob('*')):
                if f.is_file():z.write(f,'technical/'+f.relative_to(out).as_posix())
        put(ROOT/'completion.json',dict(completed=failure is None,seconds_including_seal=time.monotonic()-started,
            within_600_seconds=time.monotonic()-started<600,evidence_sha256=sha(ROOT/'evidence.zip'),evidence_bytes=(ROOT/'evidence.zip').stat().st_size))
    if failure:raise SystemExit(1)


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','preparation','case','audit']);a.add_argument('--item',default='');a.add_argument('--started',type=float);args=a.parse_args()
    out=ROOT/'runs/technical'
    if args.phase=='run':run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='preparation':
        from tools.r20_evidence_feedback.selfcheck import check
        put(out/'preparation.json',check(portable=False))
    elif args.phase=='audit':audit(out)
    else:
        key,arm=args.item.split('__');p=spec();cell=next(c for c in p['cases'] if c['key']==key)
        put(out/(args.item+'.json'),execute(cell['public'],arm,p))
