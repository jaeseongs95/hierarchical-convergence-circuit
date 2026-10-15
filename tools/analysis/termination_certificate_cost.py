"""고정 C의 잔차 음성 필터와 비용 대조. 기존 수치/봉인/Job 장치를 재사용한다."""
from __future__ import annotations
import argparse
import ctypes as C
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import termination_compare_core as core
import termination_compare_runner as runner

SELF=Path(__file__).resolve()
ROOT=SELF.parents[2]
CONTRACT=ROOT/'evidence/certificate-cost-20261015-r11/execution-contract.json'
BASE_ARITHMETIC=core.Arithmetic


def screened_certificate(arithmetic, model, encoded):
    """r is an upper witness, not a distance lower bound. Never certifies itself."""
    arithmetic.meter.guard()
    local=arithmetic.local
    scope=local.__globals__
    payload={'model':model,'current_x_box':encoded,'radius_x_exact':str(core.RADIUS),
             'epsilon_p_exact':[str(core.EPSILON)]}
    (_,_,_),current,radius=scope['validatepayload'](payload)
    scope['informationaudit'](arithmetic.numeric)
    mids=[(lo+hi)/2 for lo,hi in current]
    lower,upper=[m-radius for m in mids],[m+radius for m in mids]
    scope['require'](all(-1<lo<hi<1 and (lo*10**31).denominator==1
                        and (hi*10**31).denominator==1 for lo,hi in zip(lower,upper)),
                     'region geometry/grid31')
    arithmetic.meter.counts['residual_calls']+=1
    residual=scope['current_residual'](payload,arithmetic.numeric)
    scope['require'](set(residual)=={'model','current_x_box','eH','witness'}
                     and residual['model']==model and residual['current_x_box']==encoded,
                     'shared residual current context')
    r=list(map(Q,residual['witness']['coordinate_residual_x_upper']))
    scope['require'](len(r)==7 and all(v>=0 for v in r) and max(r)==Q(residual['eH'])
                     and residual['witness']['all7'] is True,'shared wholeB residual shape')
    # In every valid comparison v=r+Kv >= r. Strict > preserves the equality boundary.
    if max(r)>2*core.EPSILON:
        arithmetic.meter.counts['prefilter_rejections']+=1
        arithmetic.meter.guard()
        return {'screen':'SCREENED_NOT_CERTIFIABLE','proof':'NOT_EVALUATED',
                'bounds':{'component_vector':[{'status':'NOT_CERTIFIED'}]}}
    arithmetic.meter.counts['region_proofs']+=1
    result=local(payload,arithmetic.numeric,residual=residual)
    arithmetic.meter.guard()
    return result


class Timings:
    def __init__(self):self.rows={}
    def call(self,name,fn,*args,**kwargs):
        w,c=time.monotonic(),time.process_time();completed=False
        try:
            result=fn(*args,**kwargs);completed=True;return result
        finally:
            row=self.rows.setdefault(name,{'calls':0,'completed':0,'wall_seconds':0.,'cpu_seconds':0.})
            row['calls']+=1;row['completed']+=int(completed)
            row['wall_seconds']+=time.monotonic()-w;row['cpu_seconds']+=time.process_time()-c


def policy(input_path,input_sha,variant,release):
    if variant not in ('F','C0','C1'):raise ValueError('variant')
    timings=Timings();gates=[];instances=[]
    class Measured(BASE_ARITHMETIC):
        def __init__(self,*args):
            timings.call('arithmetic_init',super().__init__,*args)
            self.meter.counts.update(certificate_attempts=0,prefilter_rejections=0)
            instances.append(self)
        def step(self,*args):return timings.call('advance',super().step,*args)
        def certificate(self,model,encoded):
            self.meter.counts['certificate_attempts']+=1
            previous=dict(self.meter.counts)
            fn=screened_certificate if variant=='C1' else lambda a,m,b:BASE_ARITHMETIC.certificate(a,m,b)
            value=timings.call('certificate',fn,self,model,encoded)
            # No full current-state history is fed to the numerical certificate API.
            gates.append({'attempt':len(gates)+1,'status':value['bounds']['component_vector'][0]['status'],
                          'screen':value.get('screen'),'state_digest':core.digest(encoded),
                          'taylor_calls':self.meter.counts['taylor_calls']-previous['taylor_calls']})
            return value
    original_commit=runner.commit_state
    def measured_commit(*args):return timings.call('state_persistence',original_commit,*args)
    core.Arithmetic=Measured;runner.commit_state=measured_commit
    try:
        runner.policy_worker(input_path,input_sha,'F' if variant=='F' else 'C',release)
        # Written inside the same policy deadline. Failure/timeout retains only earlier immutable bytes.
        if instances:instances[0].meter.guard()
        runner.write_new(Path(release['out'])/'timings.json',{'schema':'HCCCertificatePhaseTiming.v1',
            'variant':variant,'phases_disjoint':True,'phases':timings.rows,'gate_attempts':gates,
            'counts':dict(instances[0].meter.counts) if instances else None,
            'scope':'completed callbacks; hard-kill partial callback cost not recoverable',
            'timing_read_overhead_in_policy_budget':True})
    except core.BudgetStop:pass
    finally:core.Arithmetic=BASE_ARITHMETIC;runner.commit_state=original_commit


def contract():
    raw=CONTRACT.read_bytes();data=core.decode(raw)
    for ref in data['code_pins']:
        p=ROOT/ref['path'];b=p.read_bytes()
        if len(b)!=ref['bytes'] or hashlib.sha256(b).hexdigest()!=ref['sha256']:raise ValueError('r11 code pin')
    return data,hashlib.sha256(raw).hexdigest()


class KillOnlyJob(runner.Job):
    def __init__(self):
        super().__init__();limits=runner.ExtendedLimits();limits.BasicLimitInformation.LimitFlags=0x2000
        self.call('SetInformationJobObject',self.handle,9,C.byref(limits),C.sizeof(limits))
        seen=runner.ExtendedLimits()
        self.call('QueryInformationJobObject',self.handle,9,C.byref(seen),C.sizeof(seen),None)
        if seen.BasicLimitInformation.LimitFlags!=0x2000 or seen.JobMemoryLimit!=0:raise ValueError('outer kill-only flags')


def study(out,outer_deadline):
    cfg,_=contract();out=Path(out);out.mkdir(exist_ok=False)
    start=time.monotonic();deadline=min(start+6900,outer_deadline)
    setup_command=[sys.executable,'-B','-X','utf8',str(ROOT/'tools/analysis/termination_compare_runner.py'),
                   '--worker','setup','--plan-sha',cfg['plan_sha256'],'--implementation-sha',cfg['implementation_sha256']]
    setup=runner.owned_phase(setup_command,out/'setup',170,deadline,min(start+180,deadline))
    if setup['status']!='COMPLETE':raise ValueError('setup incomplete')
    input_path=out/'setup/public-input.json';raw=input_path.read_bytes();input_sha=hashlib.sha256(raw).hexdigest()
    data=core.decode(raw);plan=core.decode((ROOT/runner.PLAN).read_bytes());rows=[]
    for variant in cfg['sequential_order']:
        row={'variant':variant,'policy_cap_seconds':1800,'status':'NOT_RUN'};rows.append(row)
        if time.monotonic()>=deadline:continue
        child=out/variant;cell_start=time.monotonic();cell_end=min(cell_start+1930,deadline)
        command=[sys.executable,'-B','-X','utf8',str(SELF),'--worker','policy',
                 '--input',str(input_path),'--input-sha',input_sha,'--variant',variant]
        supervision=runner.owned_phase(command,child,1800,deadline,cell_end)
        last=runner.last_snapshot(child,supervision)
        final_path=child/'final.json'
        final=core.decode(final_path.read_bytes()) if supervision['status']=='COMPLETE' and final_path.exists() else None
        row.update(policy_supervision=supervision,status=supervision['status'])
        if supervision['status']=='COMPLETE' and (final is None or not (child/'timings.json').exists()):row['status']='MEASUREMENT_FAILURE'
        sealed={'schema':'HCCTerminationSealedCell.v1','input_sha256':input_sha,'model_digest':data['model_digest'],
                'observation_digest':data['observation_digest'],'processed_digest':data['processed_digest'],
                'supervision':supervision,'last_complete':last,'final':final,
                'counters_scope':'last committed lower bound if interrupted; uncommitted work unknown'}
        sealed_path=child/'sealed-cell.json';runner.write_new(sealed_path,sealed)
        evaluation_input={'schema':'HCCTerminationEvaluationInput.v1','repo':str(ROOT),
            'policy_seal':{'path':str(sealed_path),'sha256':hashlib.sha256(sealed_path.read_bytes()).hexdigest()},
            'public_input':{'path':str(input_path),'sha256':input_sha},
            'world':{'path':str(out/'setup/world.json'),'sha256':hashlib.sha256((out/'setup/world.json').read_bytes()).hexdigest()},
            'distance_reference':next(r for r in plan['source_pins'] if 'on-fixed-point-distance-entry-certificates' in r['path'])}
        request=child/'evaluation-input.json';runner.write_new(request,evaluation_input)
        grace=time.monotonic()-cell_start-supervision['wall_seconds_after_report']+max(0,supervision['wall_seconds_after_report']-1800)
        if supervision.get('active_processes')==0 and grace<=10 and time.monotonic()<cell_end:
            command=[sys.executable,'-B','-X','utf8',str(ROOT/'tools/analysis/termination_compare_runner.py'),
                     '--worker','evaluation','--input',str(request),'--input-sha',hashlib.sha256(request.read_bytes()).hexdigest()]
            e=runner.owned_phase(command,child/'evaluation',min(120,max(.001,cell_end-time.monotonic()-max(0,10-grace))),deadline,cell_end)
            row['evaluation_supervision']=e
            result=child/'evaluation/result.json'
            row['evaluation']=core.decode(result.read_bytes()) if e['status']=='COMPLETE' and result.exists() else None
        row.update(cell_wall_seconds=time.monotonic()-cell_start,grace_before_evaluation_seconds=grace)
        runner.write_new(child/'row.json',row)
    runner.write_new(out/'cells-sealed.json',{'rows':rows,'setup_supervision':setup,'global_deadline':deadline})
    command=[sys.executable,'-B','-X','utf8',str(ROOT/'tools/analysis/test_certificate_cost.py'),'--verify-study',str(out)]
    verification=runner.owned_phase(command,out/'verification',600,deadline,deadline)
    runner.write_new(out/'summary.json',{'rows':rows,'verification_supervision':verification,'setup_supervision':setup,
        'study_wall_seconds':time.monotonic()-start,'global_cap_seconds':6900,'global_exceeded':time.monotonic()>deadline,
        'scientific_retries':0,'independent_discovery_samples':0,'order':cfg['sequential_order']})


def main():
    p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');p.add_argument('--execute',action='store_true')
    p.add_argument('--study',action='store_true');p.add_argument('--worker',choices=['policy']);p.add_argument('--output')
    p.add_argument('--input');p.add_argument('--input-sha');p.add_argument('--variant');p.add_argument('--deadline',type=float)
    args=p.parse_args()
    if args.worker:
        contract();release=core.decode(sys.stdin.buffer.readline());policy(args.input,args.input_sha,args.variant,release)
    elif args.self_test:
        subprocess.run([sys.executable,'-B','-X','utf8',str(SELF.with_name('test_certificate_cost.py'))],check=True)
    elif args.study:study(args.output,args.deadline)
    elif args.execute and args.output:
        _,sha=contract();out=Path(args.output).resolve();out.mkdir(exist_ok=False)
        start=time.monotonic();deadline=start+6900
        command=[sys.executable,'-B','-X','utf8',str(SELF),'--study','--output',str(out/'study'),'--deadline',str(deadline)]
        runner.write_new(out/'execution-start.json',{'contract_sha256':sha,'argv':command,'start_monotonic':start,'deadline_monotonic':deadline,'retry':False})
        result=runner.owned_phase(command,out/'watchdog',max(.001,deadline-time.monotonic()),deadline,deadline,KillOnlyJob)
        runner.write_new(out/'execution-end.json',{'supervision':result,'physical_wall_seconds':time.monotonic()-start,
            'cap_seconds':6900,'exceeded':time.monotonic()>deadline,'outer_stdin_release_written_not_consumed':True,
            'outer_cpu_overlaps_inner_do_not_sum':True})
        print(json.dumps({'status':result['status'],'active_processes':result['active_processes'],'wall_seconds':result['wall_seconds_after_report']}),flush=True)
    else:p.error('explicit --self-test or --execute --output required')

if __name__=='__main__':main()
