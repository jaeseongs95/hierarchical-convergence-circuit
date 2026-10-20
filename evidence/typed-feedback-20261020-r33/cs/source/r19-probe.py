"""Frozen R19 feasibility and cross-level technical probe; core remains unchanged."""
import argparse
from dataclasses import asdict
from copy import deepcopy
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/'experiments/exp-65-substitution-cross-level/frozen_spec.json'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def put(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write((json.dumps(obj,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n').encode())
def require(ok,msg):
    if not ok:raise ValueError(msg)
def spec():return read(SPEC)

def programs(cfg):
    from hcr.model import Group,Link,Program
    low=Program((Group('f0',0),Group('f1',0),Group('goal',1)),
        tuple([Link(k,'goal',cfg.relation_gain,'support') for k in ['f0','f1']]+
              [Link('goal',k,cfg.top_down_gain,'top_down') for k in ['f0','f1']]),((0,1),),2)
    high=Program((Group('promoted',0),Group('context',0),Group('match_A',1,-cfg.relation_gain),
                  Group('match_B',1,-cfg.relation_gain),Group('goal',1,cfg.relation_gain)),
        tuple([Link(k,m,sign*cfg.relation_gain,'support') for m,sign in [('match_A',1),('match_B',-1)] for k in ['promoted','context']]+
              [Link(m,k,sign*cfg.top_down_gain,'top_down') for m,sign in [('match_A',1),('match_B',-1)] for k in ['promoted','context']]+
              [Link(m,'goal',cfg.relation_gain,'support') for m in ['match_A','match_B']]+
              [Link('goal',m,cfg.top_down_gain,'top_down') for m in ['match_A','match_B']]),((0,1),),2)
    low.validate(cfg);high.validate(cfg)
    return low,high

def classify(state,convergence):
    if convergence['status']!='stable_decision':return None
    return state['goal']>=.5

def settle_one(program,drives,cfg):
    from hcr.model import Cost
    from hcr.dynamics import settle
    cost=Cost();ticks=[]
    state,conv=settle(program,drives,cfg,cost,observe=lambda n,s,r,k:ticks.append(dict(tick=n,state=dict(s),residual=r,stable_steps=k)))
    c=asdict(conv);c['status']=conv.status.value
    return dict(program=asdict(program),program_sha256=program.digest,drives=drives,initial={g.id:.5 for g in program.groups},
        ticks=ticks,state=state,convergence=c,cost=cost.snapshot(),adopted=classify(state,c))

def promote(case,low,round_number):
    from hcr.model import fingerprint
    return dict(case_id=case['id'],revision=case['revision'],round=round_number,public_sha256=fingerprint(case),
        source_sha256=fingerprint(low),raw_confidence=low['state']['goal'],adopted=low['adopted'],
        measurement_ids=['f0','f1'],measurement_scores=case['measurements'],uncertainty=1-abs(2*low['state']['goal']-1))

def check_promotion(packet,case,low,round_number):
    require(packet==promote(case,low,round_number),'promotion provenance/revision/value mismatch')

def execute(case,arm,p):
    from hcr.model import Config
    cfg=Config(**p['kernel']);low_program,high_program=programs(cfg)
    if arm=='separate_algorithms':
        # A declared task-specific baseline; no iterative common kernel or hidden reference.
        signed=sum(case['measurements'])+p['feedback_gain']*case['context']
        category=None if signed==0 else signed>0
        relation=None if category is None else category==(case['context']>0)
        return dict(case=case['id'],arm=arm,public=case,category=category,relation=relation,
            declared_baseline_operations=dict(additions=2,multiplications=1,comparisons=3),kernels=[],promotions=[])
    def low_run(feedback):return settle_one(low_program,dict(f0=cfg.evidence_gain*case['measurements'][0],
        f1=cfg.evidence_gain*case['measurements'][1],goal=feedback),cfg)
    def high_run(packet):return settle_one(high_program,dict(promoted=cfg.evidence_gain*(2*packet['raw_confidence']-1),
        context=cfg.evidence_gain*case['context']),cfg)
    low=low_run(0.0);packet=promote(case,low,0);check_promotion(packet,case,low,0)
    high=high_run(packet);kernels=[dict(kind='lower_initial',**low),dict(kind='upper_initial',**high)];packets=[packet]
    feedback=0.0
    if arm=='coupled':
        feedback=p['feedback_gain']*(high['state']['match_A']-high['state']['match_B'])
        low=low_run(feedback);packet=promote(case,low,1);check_promotion(packet,case,low,1)
        high=high_run(packet);kernels.extend([dict(kind='lower_recomputed',**low),dict(kind='upper_recomputed',**high)]);packets.append(packet)
    return dict(case=case['id'],arm=arm,public=case,category=low['adopted'],relation=high['adopted'],feedback=feedback,
        kernels=kernels,promotions=packets,adapter_scalar_operations=dict(initial_lower_drives=2,upper_drive_conversions=len(packets)*3,
        feedback_conversion=2 if arm=='coupled' else 0),native_adaptive_session=False,primitive_route_proof=False)

def independent_kernel(record,cfg,absolute_tolerance=0.0):
    """Scalar replay independent of hcr.dynamics helpers; no additional native execution."""
    from hcr.model import fingerprint
    pr=record['program'];require(record['program_sha256']==fingerprint(pr),'program digest')
    maximum_error=0.0
    def near(a,b):
        nonlocal maximum_error
        maximum_error=max(maximum_error,abs(a-b))
        return math.isclose(a,b,rel_tol=0.0,abs_tol=absolute_tolerance)
    def same_state(a,b):return set(a)==set(b) and all(near(a[k],b[k]) for k in a)
    state={g['id']:.5 for g in pr['groups']};stable=0;history=[];stop=None
    require(record['initial']==state,'initial state')
    for i,row in enumerate(record['ticks'],1):
        sums={g['id']:g['bias']+record['drives'].get(g['id'],0) for g in pr['groups']}
        for link in pr['links']:sums[link['target']]+=link['weight']*(2*state[link['source']]-1)
        nxt={}
        for group in pr['groups']:
            key=group['id'];v=state[key];d=sums[key]
            plus=d+cfg['self_excitation']*v-cfg['inhibition']*(1-v)
            minus=-d+cfg['self_excitation']*(1-v)-cfg['inhibition']*v
            z=(plus-minus)/cfg['temperature']
            sig=1/(1+math.exp(-z)) if z>=0 else math.exp(z)/(1+math.exp(z))
            nxt[key]=(1-cfg['damping'])*v+cfg['damping']*sig
        residual=max(abs(nxt[k]-state[k]) for k in state)
        stable=stable+1 if residual<=cfg['residual_tolerance'] else 0
        require(set(row)=={'tick','state','residual','stable_steps'} and row['tick']==i and
            row['stable_steps']==stable and same_state(row['state'],nxt) and near(row['residual'],residual),'scalar replay tick mismatch')
        margin=abs(2*nxt['goal']-1)
        if stable>=cfg['patience']:stop='stable_decision' if margin>=cfg['margin_threshold'] else 'stable_ambiguous'
        elif len(history)>=1 and residual>cfg['residual_tolerance']*10 and max(abs(nxt[k]-history[-1][k]) for k in nxt)<cfg['residual_tolerance']:stop='oscillating'
        if stop is not None:
            state=nxt;require(i==len(record['ticks']),'continued after stop');break
        history.append(state);history=history[-3:];state=nxt
    if stop is None:require(len(record['ticks'])==cfg['max_ticks'],'premature stop');stop='budget_exhausted'
    c=record['convergence'];require(set(c)=={'status','ticks','residual','margin','stable_steps'} and c['status']==stop and
        c['ticks']==i and c['stable_steps']==stable and near(c['residual'],residual) and near(c['margin'],margin),'convergence mismatch')
    require(same_state(record['state'],state) and record['adopted']==classify(state,c),'readout mismatch')
    cost=record['cost'];require(cost['kernel_ticks']==i and cost['group_updates']==i*len(pr['groups']) and
        cost['normalization_ops']==i*len(pr['groups']) and cost['signal_transmissions']==i*len(pr['links']),'kernel cost mismatch')
    return maximum_error

def audit_execution(e,case,arm,p,absolute_tolerance=0.0):
    from hcr.model import Config
    from hcr.codec import plain
    low,high=programs(Config(**p['kernel']))
    require(e['public']==case and e['case']==case['id'] and e['arm']==arm,'public input binding')
    if arm=='separate_algorithms':require(e==execute(case,arm,p),'baseline mismatch');return 0.0
    require(len(e['kernels'])==(4 if arm=='coupled' else 2),'exact bounded coupling')
    require(len(e['promotions'])==(2 if arm=='coupled' else 1),'promotion count')
    require([k['kind'] for k in e['kernels']]==(['lower_initial','upper_initial','lower_recomputed','upper_recomputed'] if arm=='coupled' else ['lower_initial','upper_initial']),'kernel order')
    maximum_error=0.0
    for j,k in enumerate(e['kernels']):
        require(k['program']==plain(low if j%2==0 else high),'adapter program changed')
        maximum_error=max(maximum_error,independent_kernel(k,p['kernel'],absolute_tolerance))
    feedback=0.0
    for round_number,packet in enumerate(e['promotions']):
        lo=e['kernels'][2*round_number];hi=e['kernels'][2*round_number+1]
        check_promotion(packet,case,{k:v for k,v in lo.items() if k!='kind'},round_number)
        require(lo['drives']==dict(f0=p['kernel']['evidence_gain']*case['measurements'][0],f1=p['kernel']['evidence_gain']*case['measurements'][1],goal=feedback),'lower drive binding')
        require(hi['drives']==dict(promoted=p['kernel']['evidence_gain']*(2*packet['raw_confidence']-1),context=p['kernel']['evidence_gain']*case['context']),'upper drive binding')
        feedback=p['feedback_gain']*(hi['state']['match_A']-hi['state']['match_B'])
    require(e['category']==e['kernels'][-2]['adopted'] and e['relation']==e['kernels'][-1]['adopted'],'final adoption binding')
    require(e['feedback']==(p['feedback_gain']*(e['kernels'][1]['state']['match_A']-e['kernels'][1]['state']['match_B']) if arm=='coupled' else 0.0),'feedback mismatch')
    return maximum_error

def preparation():
    from hcr.model import Config,Cost
    from hcr.patterns import make_pattern
    from hcr.dynamics import tick
    from tools.r18_pre_reuse_gate.policy import preflight,independent_allow
    from tools.r19_cross_level.policy import preflight as fixed
    cfg=Config(**spec()['kernel']);pattern=make_pattern(2,cfg);states=[]
    for boundary in [.1,.9]:
        current={g.id:.5 for g in pattern.program.groups};current['goal']=boundary
        cost=Cost();nxt=tick(pattern.program,current,{'e:0':4.0,'e:1':4.0},cfg,cost)
        states.append(dict(boundary=boundary,local_state={k:v for k,v in current.items() if k!='goal'},next_local_output=nxt['p:0:1'],cost=cost.snapshot()))
    require(states[0]['local_state']==states[1]['local_state'] and states[0]['next_local_output']!=states[1]['next_local_output'],'context-free replacement counterexample')
    cycle=dict(start='A',goal='B',edges=[dict(source=a,target=b,score=1) for a,b in [('A','B'),('B','C'),('C','D'),('D','B')]])
    require(preflight(cycle,True)['enabled'] and not independent_allow(cycle,True) and not fixed(cycle,True)['enabled'],'cycle regression')
    checked=0;vertices=list('ABCDE');possible=[(a,b) for a in vertices for b in vertices if a!=b]
    for edges in itertools.combinations(possible,4):
        for start in vertices:
            for goal in vertices:
                if start==goal or start not in {v for edge in edges for v in edge} or goal not in {v for edge in edges for v in edge}:continue
                obs=dict(start=start,goal=goal,edges=[dict(source=a,target=b,score=1) for a,b in edges])
                require(fixed(obs,True)['enabled']==independent_allow(obs,True),'small graph differential')
                checked+=1
    return dict(candidate='context-free local transition replacement',candidate_rejected=True,counterexamples=states,
        limitation='Only this boundary-omitting candidate is refuted; no general impossibility of compression.',
        original_cycle_reproduced=True,corrected_cycle_rejected=True,differential_graph_checks=checked,
        gate_not_used_by_cross_level=True,adaptive_training_executions=0,diagnostic_native_ticks=2)

def audit(out,absolute_tolerance=0.0):
    p=spec();truth=read(SPEC.with_name('reference.json'));rows=[];rejected=[]
    for case in p['cases']:
        for arm in p['arms']:
            e=read(out/(case['id']+'__'+arm+'.json'));maximum_error=audit_execution(e,case,arm,p,absolute_tolerance)
            if arm=='coupled' and not rejected:
                for field in ['promotion_revision','promotion_value','tick_state']:
                    bad=deepcopy(e)
                    if field=='promotion_revision':bad['promotions'][0]['revision']+=1
                    elif field=='promotion_value':bad['promotions'][0]['raw_confidence']+=.1
                    else:bad['kernels'][0]['ticks'][0]['state']['goal']+=.01
                    try:audit_execution(bad,case,arm,p,absolute_tolerance)
                    except (ValueError,AssertionError):rejected.append(field)
                    else:raise ValueError('tamper accepted')
                newer=dict(case,revision=case['revision']+1)
                try:check_promotion(e['promotions'][0],newer,{k:v for k,v in e['kernels'][0].items() if k!='kind'},0)
                except ValueError:rejected.append('stale_promotion')
                else:raise ValueError('stale promotion accepted')
            rows.append(dict(case=case['id'],arm=arm,category=e['category'],relation=e['relation'],
                numeric_replay_max_absolute_error=maximum_error,
                execution_bytes=(out/(case['id']+'__'+arm+'.json')).stat().st_size,
                promotion_serialized_bytes=sum(len(json.dumps(packet,sort_keys=True).encode()) for packet in e['promotions']),
                category_correct=e['category'] is not None and e['category']==truth[case['id']]['category'],
                relation_correct=e['relation'] is not None and e['relation']==truth[case['id']]['relation'],
                kernel_ticks=sum(k['cost']['kernel_ticks'] for k in e['kernels']),group_updates=sum(k['cost']['group_updates'] for k in e['kernels']),
                signal_transmissions=sum(k['cost']['signal_transmissions'] for k in e['kernels']),
                lower_initial=None if not e['kernels'] else e['kernels'][0]['adopted'],
                upper_initial=None if not e['kernels'] else e['kernels'][1]['adopted']))
    require(len(rows)==18 and len(rejected)==4,'exact rows and rejection checks')
    summary=dict(status='TECHNICAL_PROBE_REPLAYED',rows=rows,rejected_mutations=rejected,case_count=6,native_settle_calls=36,
        numeric_replay_absolute_tolerance=absolute_tolerance,
        adaptive_training_executions=0,common_primitive_generalization_established=False,learning_efficiency_established=False,
        native_route_proof=False,autonomous_hierarchy_learning=False,exact_substitution_candidate_rejected=read(out/'preparation.json')['candidate_rejected'])
    put(out/'summary.json',summary)

def run(started):
    import resource
    out=ROOT/'runs/technical';out.mkdir(parents=True,exist_ok=False);stages=[];deadline=started+580
    def stage(phase,item=''):
        require(deadline-time.monotonic()>30,'budget reserve exhausted')
        before=time.monotonic();usage=resource.getrusage(resource.RUSAGE_CHILDREN)
        def limit():resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
        with (out/(phase+'-'+item+'.stdout')).open('xb') as stdout,(out/(phase+'-'+item+'.stderr')).open('xb') as stderr:
            child=subprocess.Popen([sys.executable,'-B',str(Path(__file__)),'--phase',phase,'--item',item],stdout=stdout,stderr=stderr,preexec_fn=limit)
            try:rc=child.wait(timeout=min(60,deadline-time.monotonic()-20))
            except BaseException:child.kill();child.wait();raise
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        stages.append(dict(phase=phase,item=item,returncode=rc,wall_seconds=time.monotonic()-before,child_cpu_seconds=after.ru_utime+after.ru_stime-usage.ru_utime-usage.ru_stime))
        require(rc==0,'stage failure '+phase+' '+item)
        require(sum(f.stat().st_size for f in out.rglob('*') if f.is_file())<128*1024**2,'raw size budget')
    try:
        manifest=read(ROOT/'source_manifest.json');require(all(sha(ROOT/n)==h for n,h in manifest.items()),'source preflight')
        stage('preparation')
        require(read(out/'preparation.json')['candidate_rejected'],'candidate not rejected; do not pivot automatically')
        for case in spec()['cases']:
            for arm in spec()['arms']:stage('case',case['id']+'__'+arm)
        stage('audit')
        require(all(sha(ROOT/n)==h for n,h in manifest.items()),'source changed')
        put(out/'result.json',dict(status='COMPLETED',stages=stages,source_unchanged=True,seconds_before_seal=time.monotonic()-started,
            host=os.uname().nodename,python=sys.version,source_manifest_sha256=sha(ROOT/'source_manifest.json'),worker_limit=1,total_wall_limit_seconds=600,automatic_retry=False))
    except BaseException:
        put(out/'failure.json',dict(traceback=traceback.format_exc(),stages=stages,automatic_retry=False));raise
    finally:
        put(out/'manifest.json',{f.relative_to(out).as_posix():sha(f) for f in sorted(out.rglob('*')) if f.is_file()})
        with zipfile.ZipFile(ROOT/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.rglob('*')):
                if f.is_file():z.write(f,'technical/'+f.relative_to(out).as_posix())
        put(ROOT/'completion.json',dict(completed=(out/'result.json').exists(),seconds_including_seal=time.monotonic()-started,
            within_600_seconds=time.monotonic()-started<600,evidence_sha256=sha(ROOT/'evidence.zip'),evidence_bytes=(ROOT/'evidence.zip').stat().st_size))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','case','audit','preparation']);a.add_argument('--item',default='');a.add_argument('--started',type=float,default=None);args=a.parse_args()
    out=ROOT/'runs/technical'
    if args.phase=='run':run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='preparation':put(out/'preparation.json',preparation())
    elif args.phase=='audit':audit(out)
    else:
        name,arm=args.item.split('__');p=spec();case=next(c for c in p['cases'] if c['id']==name)
        require(arm in p['arms'],'frozen arm');put(out/(args.item+'.json'),execute(case,arm,p))
