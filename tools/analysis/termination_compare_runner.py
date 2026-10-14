"""Windows 자체 자식 트리의 정책/평가 예산 감독. 과학 실행에는 --execute가 필요하다."""
from __future__ import annotations
import argparse
import ctypes as C
from ctypes import wintypes as W
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import termination_compare_core as core

ROOT=Path(__file__).resolve().parents[2]
PLAN='experiments/exp-62-top-down/termination-policy-comparison-plan-20261015.json'
IMPLEMENTATION='experiments/exp-62-top-down/termination-comparison-implementation-20261015.json'
MEMORY_BYTES=512*1024*1024


def write_new(path, value):
    with Path(path).open('xb') as f:
        f.write(core.canonical(value)+b'\n');f.flush();os.fsync(f.fileno())


def atomic_owned(path, value):
    path=Path(path);tmp=path.with_suffix('.pending')
    with tmp.open('wb') as f:
        f.write(core.canonical(value)+b'\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)


class BasicLimits(C.Structure):
    _fields_=[('PerProcessUserTimeLimit',C.c_int64),('PerJobUserTimeLimit',C.c_int64),
        ('LimitFlags',W.DWORD),('MinimumWorkingSetSize',C.c_size_t),
        ('MaximumWorkingSetSize',C.c_size_t),('ActiveProcessLimit',W.DWORD),
        ('Affinity',C.c_size_t),('PriorityClass',W.DWORD),('SchedulingClass',W.DWORD)]


class IOCounts(C.Structure):
    _fields_=[(n,C.c_uint64) for n in ('ReadOperationCount','WriteOperationCount',
        'OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]


class ExtendedLimits(C.Structure):
    _fields_=[('BasicLimitInformation',BasicLimits),('IoInfo',IOCounts),
        ('ProcessMemoryLimit',C.c_size_t),('JobMemoryLimit',C.c_size_t),
        ('PeakProcessMemoryUsed',C.c_size_t),('PeakJobMemoryUsed',C.c_size_t)]


class Accounting(C.Structure):
    _fields_=[(n,C.c_int64) for n in ('TotalUserTime','TotalKernelTime',
        'ThisPeriodTotalUserTime','ThisPeriodTotalKernelTime')]+[(n,W.DWORD) for n in
        ('TotalPageFaultCount','TotalProcesses','ActiveProcesses','TotalTerminatedProcesses')]


class ThreadEntry(C.Structure):
    _fields_=[(n,W.DWORD) for n in ('dwSize','cntUsage','th32ThreadID','th32OwnerProcessID')]+[
        ('tpBasePri',W.LONG),('tpDeltaPri',W.LONG),('dwFlags',W.DWORD)]


def resume_owned_bootstrap(process):
    """Popen closes its primary thread handle; recover only this suspended PID's thread."""
    api=C.WinDLL('kernel32',use_last_error=True)
    api.CreateToolhelp32Snapshot.argtypes=[W.DWORD,W.DWORD];api.CreateToolhelp32Snapshot.restype=W.HANDLE
    for name in ('Thread32First','Thread32Next'):
        getattr(api,name).argtypes=[W.HANDLE,C.POINTER(ThreadEntry)];getattr(api,name).restype=W.BOOL
    api.OpenThread.argtypes=[W.DWORD,W.BOOL,W.DWORD];api.OpenThread.restype=W.HANDLE
    api.ResumeThread.argtypes=[W.HANDLE];api.ResumeThread.restype=W.DWORD
    api.CloseHandle.argtypes=[W.HANDLE];api.CloseHandle.restype=W.BOOL
    snapshot=api.CreateToolhelp32Snapshot(0x4,0)
    if snapshot==C.c_void_p(-1).value:raise C.WinError(C.get_last_error())
    ids=[]
    try:
        entry=ThreadEntry();entry.dwSize=C.sizeof(entry)
        more=api.Thread32First(snapshot,C.byref(entry))
        while more:
            if entry.th32OwnerProcessID==process.pid:ids.append(int(entry.th32ThreadID))
            entry.dwSize=C.sizeof(entry);more=api.Thread32Next(snapshot,C.byref(entry))
    finally:api.CloseHandle(snapshot)
    if len(ids)!=1:raise RuntimeError('owned suspended primary thread not uniquely observed')
    thread=api.OpenThread(0x2,False,ids[0])
    if not thread:raise C.WinError(C.get_last_error())
    try:
        previous=api.ResumeThread(thread)
        if previous!=1:raise RuntimeError('owned primary thread suspend count mismatch')
    finally:api.CloseHandle(thread)
    return ids[0]


class Job:
    """Anonymous Job, no breakaway; never operates on unrelated process IDs."""
    def __init__(self,memory_bytes=MEMORY_BYTES):
        if os.name!='nt':raise RuntimeError('Windows Job capability required; no fallback')
        self.api=C.WinDLL('kernel32',use_last_error=True)
        sig={'CreateJobObjectW':([C.c_void_p,W.LPCWSTR],W.HANDLE),
             'SetInformationJobObject':([W.HANDLE,C.c_int,C.c_void_p,W.DWORD],W.BOOL),
             'AssignProcessToJobObject':([W.HANDLE,W.HANDLE],W.BOOL),
             'QueryInformationJobObject':([W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.c_void_p],W.BOOL),
             'TerminateJobObject':([W.HANDLE,W.UINT],W.BOOL),
             'CloseHandle':([W.HANDLE],W.BOOL)}
        for name,(args,result) in sig.items():
            fn=getattr(self.api,name);fn.argtypes=args;fn.restype=result
        self.handle=self.api.CreateJobObjectW(None,None)
        if not self.handle:raise C.WinError(C.get_last_error())
        limits=ExtendedLimits();limits.BasicLimitInformation.LimitFlags=0x2000|0x200
        limits.JobMemoryLimit=memory_bytes
        try:self.call('SetInformationJobObject',self.handle,9,C.byref(limits),C.sizeof(limits))
        except BaseException:self.close();raise

    def call(self,name,*args):
        if not getattr(self.api,name)(*args):raise C.WinError(C.get_last_error())

    def assign(self,process):
        self.call('AssignProcessToJobObject',self.handle,W.HANDLE(int(process._handle)))

    def stats(self):
        accounting=Accounting();limits=ExtendedLimits()
        self.call('QueryInformationJobObject',self.handle,1,C.byref(accounting),C.sizeof(accounting),None)
        self.call('QueryInformationJobObject',self.handle,9,C.byref(limits),C.sizeof(limits),None)
        return {'tree_cpu_seconds':(accounting.TotalUserTime+accounting.TotalKernelTime)/10**7,
                'active_processes':int(accounting.ActiveProcesses),
                'total_processes':int(accounting.TotalProcesses),
                'peak_job_committed_bytes':int(limits.PeakJobMemoryUsed),
                'job_memory_limit_bytes':int(limits.JobMemoryLimit),
                'job_limit_flags':int(limits.BasicLimitInformation.LimitFlags)}

    def terminate(self):self.call('TerminateJobObject',self.handle,124)

    def close(self):
        if self.handle:self.api.CloseHandle(self.handle);self.handle=None


def owned_phase(command, out, cap, global_deadline=float('inf'), cleanup_deadline=None,
                job_factory=Job):
    """Same path for production and synthetic child/grandchild tests."""
    if not math.isfinite(cap) or cap<=0:raise ValueError('positive finite phase cap')
    start=time.monotonic();deadline=min(start+cap,global_deadline)
    out=Path(out);out.mkdir(exist_ok=False)
    end=min(deadline+10,global_deadline,
            cleanup_deadline if cleanup_deadline is not None else deadline+10)
    result={'start_monotonic':start,'deadline_monotonic':deadline,'released':False,
            'termination_requested_monotonic':None,'status':'MEASUREMENT_FAILURE'}
    p=None;job=None
    try:
        if time.monotonic()>=deadline:raise core.BudgetStop('global/phase deadline before launch')
        job=job_factory()
        with (out/'stdout.txt').open('xb') as stdout,(out/'stderr.txt').open('xb') as stderr:
            if time.monotonic()>=deadline:raise core.BudgetStop('deadline before launch')
            p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,
                               creationflags=subprocess.CREATE_NO_WINDOW|0x4)
            job.assign(p)
            if time.monotonic()>=deadline:raise core.BudgetStop('launch exceeded cap')
            result['assigned_before_resume']=True
            result['owned_primary_thread_id']=resume_owned_bootstrap(p)
            if time.monotonic()>=deadline:raise core.BudgetStop('resume exceeded cap')
            release={'start':start,'deadline':deadline,'out':str(out.resolve())}
            p.stdin.write(core.canonical(release)+b'\n');p.stdin.flush();p.stdin.close()
            result['released']=True
            while True:
                now=time.monotonic();code=p.poll()
                if code is not None and now<=deadline:
                    # A Python launcher/short-lived descendant can finish just after root exit.
                    quiet_end=min(deadline,now+.1)
                    while job.stats()['active_processes'] and time.monotonic()<quiet_end:
                        time.sleep(.001)
                    if job.stats()['active_processes']==0 and time.monotonic()<=deadline:
                        result['status']='COMPLETE' if code==0 else 'MEASUREMENT_FAILURE'
                    else:
                        result['status']='BUDGET_INCOMPLETE' if time.monotonic()>=deadline else 'DESCENDANT_CLEANUP'
                        result['termination_requested_monotonic']=time.monotonic();job.terminate()
                    break
                if now>=deadline:
                    result['status']='BUDGET_INCOMPLETE'
                    result['termination_requested_monotonic']=now
                    job.terminate();break
                time.sleep(min(.01,deadline-now))
        # A worker cannot leave a descendant running after a normal root exit.
        if job.stats()['active_processes']:
            if result['termination_requested_monotonic'] is None:
                result['termination_requested_monotonic']=time.monotonic()
                if result['status']=='COMPLETE':result['status']='DESCENDANT_CLEANUP'
            job.terminate()
    except BaseException as error:
        result['error']=type(error).__name__+': '+str(error)
        if isinstance(error,core.BudgetStop):result['status']='BUDGET_INCOMPLETE'
        if job and p:
            try:job.terminate()
            except OSError:pass
        if p and p.poll() is None:p.kill()  # Owned bootstrap only, before release if assignment failed.
    finally:
        if p:
            try:p.wait(timeout=max(.001,min(2,end-time.monotonic())))
            except subprocess.TimeoutExpired:pass
            if p.stdin and not p.stdin.closed:
                try:p.stdin.close()
                except OSError:pass
        if job:
            while time.monotonic()<end:
                try:
                    if job.stats()['active_processes']==0:break
                except OSError:break
                time.sleep(.01)
            try:result.update(job.stats())
            except OSError:result.update(tree_cpu_seconds=None,active_processes=None,
                                        peak_job_committed_bytes=None)
            if result.get('active_processes')!=0:result['status']='CLEANUP_NOT_CONFIRMED'
            job.close()
        result['finished_monotonic']=time.monotonic()
        result['wall_seconds']=result['finished_monotonic']-start
        result['exit_code']=p.returncode if p else None
        result['termination_overrun_seconds']=max(0,result['finished_monotonic']-deadline)
        result['hard_realtime_guarantee']=False
        result['memory_kind']='committed_virtual_not_RSS'
        write_new(out/'supervision.json',result)
        result['report_finished_monotonic']=time.monotonic()
        result['wall_seconds_after_report']=result['report_finished_monotonic']-start
    return result


def load_verified(repo, ref):
    relative=Path(ref['path'])
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('source traversal')
    p=(Path(repo)/relative).resolve()
    if not p.is_relative_to(Path(repo).resolve()):raise ValueError('source outside repo')
    raw=p.read_bytes()
    if len(raw)!=ref['bytes'] or hashlib.sha256(raw).hexdigest()!=ref['sha256']:
        raise ValueError('source pin mismatch')
    return raw


def model_from_public(public):
    if set(public)!= {'program','drives','kernel','observation','processed'}:
        raise ValueError('public payload fields')
    program=public['program'];k=public['kernel'];ids=[g['id'] for g in program['groups']]
    if ids!=core.ORDER or len(program['links'])!=8:raise ValueError('whole7 graph/order/links')
    if any(type(k[key]) not in (int,float) for key in ('temperature','damping','self_excitation','inhibition')):
        raise ValueError('primitive numeric types')
    if not (k['temperature']==1 and k['damping']==.45 and k['self_excitation']==.25
            and k['inhibition']==.2):raise ValueError('frozen primitive kernel')
    drives=public['drives'];index={key:i for i,key in enumerate(core.ORDER)}
    if set(drives)-set(index):raise ValueError('drive identity')
    b=[core.binary(g['bias'])+Q(drives.get(g['id'],'0')) for g in program['groups']]
    G=[[Q(0)]*7 for _ in range(7)]
    for edge in program['links']:
        if edge['kind'] not in ('support','top_down'):raise ValueError('link kind')
        G[index[edge['target']]][index[edge['source']]]+=core.binary(edge['weight'])
    diagonal=(core.binary(k['self_excitation'])+core.binary(k['inhibition']))/2
    for i in range(7):G[i][i]+=diagonal
    return {'b':list(map(str,b)),'G':[list(map(str,row)) for row in G],
            'd':str(core.binary(k['damping']))}


def prepare_input(repo,plan):
    refs={p['path']:p for p in plan['source_pins']}
    raw_path=next(p for p in refs if p.endswith('swapped-s003-td1-off/inference.json'))
    raw=core.decode(load_verified(repo,refs[raw_path]))
    events=raw['execution']['packet']['document']['events']
    network=events[8]['payload']
    if (events[8]['event']!='r02_network' or network['top_down'] is not True
            or network['kind']!='decision'):raise ValueError('first ON binding')
    if (events[0]['event']!='r02_engine_created' or events[0]['payload']['use_circuits'] is not False
            or events[0]['payload']['prior_policy']['judgment_scope']!='route_only'):
        raise ValueError('frozen circuit/prior switches')
    kernel=events[0]['payload']['config']['kernel']
    observation=json.loads(json.dumps(events[1]['payload']['observation']))
    drives={k:str(core.binary(v)) for k,v in network['drives'].items()}
    drives['e:1']=str(core.binary(float.fromhex(plan['model']['drive_hex'])))
    score=core.binary(float.fromhex(plan['model']['score_hex']))
    if Q(drives['e:1'])!=4*score:raise ValueError('score/drive lift')
    # Engine evidence IDs are positional: e:1 binds the second swapped public edge e3.
    if observation['edges'][1]['id']!='e3':raise ValueError('swapped public binding')
    observation['edges'][1]['score']=float.fromhex(plan['model']['score_hex'])
    public={'program':network['program'],'drives':drives,'kernel':kernel,
            'observation':observation,'processed':{'complete':False,'paths':[['e2','e3']],
                                                'remaining_public_path':['e0','e1']}}
    if network['program']['paths']!=[[0,1]]:raise ValueError('processed first path binding')
    sources={n:(Path(repo)/'tools/analysis'/n).read_text(encoding='utf-8') for n in core.LIB_PINS}
    model=model_from_public(public)
    return {'schema':'HCCTerminationInput.v1','public':public,'model_digest':core.digest(model),
            'observation_digest':core.digest(observation),'processed_digest':core.digest(public['processed']),
            'math_sources':sources,'tick_cap':6144,'cadence':16,
            'radius_x_exact':str(core.RADIUS),'epsilon_p_exact':str(core.EPSILON)}


def validate_input(data):
    expected={'schema','public','model_digest','observation_digest','processed_digest','math_sources',
              'tick_cap','cadence','radius_x_exact','epsilon_p_exact'}
    if set(data)!=expected or data['schema']!='HCCTerminationInput.v1':raise ValueError('input fields')
    if (data['tick_cap']!=6144 or data['cadence']!=16
            or data['radius_x_exact']!=str(core.RADIUS) or data['epsilon_p_exact']!=str(core.EPSILON)):
        raise ValueError('frozen policy recipe')
    model=model_from_public(data['public'])
    if core.digest(model)!=data['model_digest']:raise ValueError('model digest')
    if core.digest(data['public']['observation'])!=data['observation_digest']:raise ValueError('observation digest')
    if core.digest(data['public']['processed'])!=data['processed_digest']:raise ValueError('processed digest')
    return model


def commit_state(out, snapshot, meter):
    meter.guard();path=out/f'state-{snapshot["tick"]:06d}.json'
    write_new(path,snapshot)
    finished=time.monotonic();meter.guard()
    # This ack only references already completed state+diagnostic bytes; no new numeric work.
    ack={'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
         'completed_monotonic':finished,'tick':snapshot['tick']}
    atomic_owned(out/'last-complete.json',ack)
    return ack


def policy_worker(input_path,input_sha,arm,release):
    start,deadline=release['start'],release['deadline'];out=Path(release['out'])
    meter=core.Meter(deadline);meter.guard()
    raw=Path(input_path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=input_sha:raise ValueError('input hash')
    data=core.decode(raw);model=validate_input(data);arithmetic=core.Arithmetic(data['math_sources'],meter)
    if arm not in ('L','F','C'):raise ValueError('policy id')
    box=core.encode_box([(Q(0),Q(0))]*7);history=[];legacy=core.Legacy()
    try:
        initial={'tick':0,'current_x_box':box,'diagnostic':core.diagnostic(box),
                 'model_digest':data['model_digest'],'observation_digest':data['observation_digest'],
                 'processed_digest':data['processed_digest'],'policy':arm,'gate_state':'NOT_REQUESTED',
                 'counters':dict(meter.counts),'legacy':None}
        commit_state(out,initial,meter)
        for tick in range(1,6145):
            previous=box;now=arithmetic.step(model,previous)
            try:
                detail=legacy.update(tick,previous,now,history[-1] if history else None) if arm=='L' else None
            except ValueError as error:
                if 'threshold overlaps' not in str(error):raise
                meter.guard()
                write_new(out/'final.json',{'schema':'HCCTerminationPolicyOutput.v1',
                    'input_sha256':input_sha,'last_complete':core.decode((out/'last-complete.json').read_bytes()),
                    'stop_reason':'INCONCLUSIVE','certificate':None,'first_ambiguous_tick':tick,
                    'reason':str(error),'counters':dict(meter.counts)})
                meter.guard();return
            snapshot={'tick':tick,'current_x_box':now,'diagnostic':core.diagnostic(now),
                'model_digest':data['model_digest'],'observation_digest':data['observation_digest'],
                'processed_digest':data['processed_digest'],'policy':arm,'legacy':detail,
                'gate_state':'PENDING' if arm=='C' and tick%16==0 else 'NOT_REQUESTED',
                'counters':dict(meter.counts)}
            ack=commit_state(out,snapshot,meter)
            box=now;history.append(previous);history=history[-3:]
            reason=None;certificate=None
            if arm=='L' and detail['status']:reason=detail['status']
            if arm=='C' and tick%16==0:
                try:certificate=arithmetic.certificate(model,box)
                except ValueError as error:
                    if str(error)!='region geometry/grid31':raise
                    meter.guard();write_new(out/'final.json',{
                        'schema':'HCCTerminationPolicyOutput.v1','input_sha256':input_sha,
                        'last_complete':ack,'stop_reason':'INCONCLUSIVE','certificate':None,
                        'reason':str(error),'counters':dict(meter.counts)})
                    meter.guard();return
                if certificate['bounds']['component_vector'][0]['status']=='CERTIFIED_WITHIN_EPS':
                    reason='CERTIFIED'
            if reason or tick==6144:
                meter.guard()
                write_new(out/'final.json',{'schema':'HCCTerminationPolicyOutput.v1',
                    'input_sha256':input_sha,'last_complete':ack,'stop_reason':reason or 'TICK_CAP',
                    'certificate':certificate if reason=='CERTIFIED' else None,
                    'last_gate_status':certificate['bounds']['component_vector'][0]['status'] if certificate else 'NOT_REQUESTED',
                    'policy_cpu_seconds':time.process_time(),'policy_wall_seconds':time.monotonic()-start,
                    'counters':dict(meter.counts),'counters_scope':'observed completed work; Fraction bits sampled at forward endpoints only'})
                meter.guard();return
    except core.BudgetStop:
        return  # No final seal: supervisor preserves only already committed bytes.


def last_snapshot(out,supervision):
    out=Path(out);ack_path=out/'last-complete.json'
    if not ack_path.exists():return None
    ack=core.decode(ack_path.read_bytes())
    if (ack['completed_monotonic']>supervision['deadline_monotonic']
            or not re_state_name(ack['path'])):raise ValueError('late/invalid snapshot')
    raw=(out/ack['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ack['sha256']:raise ValueError('snapshot hash')
    snapshot=core.decode(raw)
    if snapshot['tick']!=ack['tick']:raise ValueError('snapshot tick')
    return {'ack':ack,'snapshot':snapshot}


def re_state_name(value):
    return isinstance(value,str) and len(value)==17 and value.startswith('state-') \
        and value[6:12].isdigit() and value[12:]=='.json'


def worker_main(args):
    release=core.decode(sys.stdin.buffer.readline())
    if set(release)!= {'start','deadline','out'}:raise ValueError('release handshake')
    if any(type(release[k]) not in (int,float) or not math.isfinite(release[k]) for k in ('start','deadline')) \
            or release['deadline']<=release['start']:raise ValueError('release clock')
    if args.worker=='policy':policy_worker(args.input,args.input_sha,args.arm,release)
    elif args.worker=='setup':setup_worker(args,release)
    else:
        import check_termination_comparison as evaluator
        evaluator.evaluate_worker(args.input,args.input_sha,release)


def setup_worker(args,release):
    meter=core.Meter(release['deadline']);meter.guard();out=Path(release['out'])
    plan_raw=(ROOT/PLAN).read_bytes()
    implementation_raw=(ROOT/IMPLEMENTATION).read_bytes()
    if hashlib.sha256(plan_raw).hexdigest()!=args.plan_sha:raise ValueError('plan hash')
    if hashlib.sha256(implementation_raw).hexdigest()!=args.implementation_sha:raise ValueError('implementation hash')
    plan=core.decode(plan_raw);impl=core.decode(implementation_raw)
    if load_verified(ROOT,impl['design_pin'])!=plan_raw:raise ValueError('implementation/design binding')
    for ref in impl['code_pins']+plan['source_pins']:meter.guard();load_verified(ROOT,ref)
    data=prepare_input(ROOT,plan);meter.guard()
    write_new(out/'public-input.json',data)
    write_new(out/'world.json',{'schema':'HCCTerminationWorld.v1',
        'observation_digest':data['observation_digest'],'truth':plan['world_contract']['hidden_truth'],
        'authored_synthetic_world':True})
    meter.guard();write_new(out/'setup-result.json',{'model_digest':data['model_digest'],
        'input_sha256':hashlib.sha256((out/'public-input.json').read_bytes()).hexdigest(),
        'setup_cpu_seconds':time.process_time()});meter.guard()


def study(args):
    global_start=time.monotonic();global_deadline=global_start+6900
    out=Path(args.output).resolve();out.mkdir(exist_ok=False)
    setup_end=min(global_start+180,global_deadline)
    setup_command=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--worker','setup',
                   '--plan-sha',args.plan_sha,'--implementation-sha',args.implementation_sha]
    setup=owned_phase(setup_command,out/'setup',max(.001,setup_end-time.monotonic()-10),
                      global_deadline,setup_end)
    if setup['status']!='COMPLETE':raise RuntimeError('setup not completed; no cells launched')
    plan=core.decode((ROOT/PLAN).read_bytes())
    input_path=out/'setup/public-input.json';data=core.decode(input_path.read_bytes())
    input_sha=hashlib.sha256(input_path.read_bytes()).hexdigest()
    setup_elapsed=time.monotonic()-global_start
    if setup_elapsed>180:raise core.BudgetStop('setup budget')
    rows=[]
    for label in plan['resource_envelope']['sequential_order']:
        budget_s,arm=label.split('/');cap=int(budget_s)
        row={'cell':label,'policy':arm,'budget_seconds':cap,'status':'NOT_RUN'}
        rows.append(row)
        if time.monotonic()>=global_deadline:continue
        cell_start=time.monotonic();cell_deadline=min(cell_start+cap+120+10,global_deadline)
        command=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--worker','policy',
                 '--input',str(input_path),'--input-sha',input_sha,'--arm',arm]
        child=out/label.replace('/','-')
        supervision=owned_phase(command,child,cap,global_deadline,cell_deadline)
        row['policy_supervision']=supervision
        last=last_snapshot(child,supervision)
        final_path=child/'final.json'
        final=core.decode(final_path.read_bytes()) if supervision['status']=='COMPLETE' and final_path.exists() else None
        if final is None and supervision['status']=='COMPLETE':row['status']='MEASUREMENT_FAILURE'
        else:row['status']='INCONCLUSIVE' if final and final['stop_reason']=='INCONCLUSIVE' else supervision['status']
        sealed={'schema':'HCCTerminationSealedCell.v1','input_sha256':input_sha,
                'model_digest':data['model_digest'],'observation_digest':data['observation_digest'],
                'processed_digest':data['processed_digest'],'supervision':supervision,
                'last_complete':last,'final':final,
                'counters_scope':'committed lower bound on interrupted worker; uncommitted work unknown'}
        sealed_path=child/'sealed-cell.json';write_new(sealed_path,sealed)
        evaluation_input={'schema':'HCCTerminationEvaluationInput.v1','repo':str(ROOT),
            'policy_seal':{'path':str(sealed_path),'sha256':hashlib.sha256(sealed_path.read_bytes()).hexdigest()},
            'public_input':{'path':str(input_path),'sha256':input_sha},
            'world':{'path':str(out/'setup/world.json'),'sha256':hashlib.sha256((out/'setup/world.json').read_bytes()).hexdigest()},
            'distance_reference':next(r for r in plan['source_pins'] if 'on-fixed-point-distance-entry-certificates' in r['path'])}
        eval_input=child/'evaluation-input.json';write_new(eval_input,evaluation_input)
        phase_elapsed=supervision['wall_seconds_after_report']
        metadata_elapsed=time.monotonic()-cell_start-phase_elapsed
        grace_used=max(0,phase_elapsed-cap)+max(0,metadata_elapsed)
        grace_left=max(0,10-grace_used)
        row['grace_before_evaluation_seconds']=grace_used
        if time.monotonic()<cell_deadline and supervision.get('active_processes')==0 and grace_used<=10:
            command=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--worker','evaluation',
                     '--input',str(eval_input),'--input-sha',hashlib.sha256(eval_input.read_bytes()).hexdigest()]
            eval_cap=min(120,max(.001,cell_deadline-time.monotonic()-grace_left))
            eval_cleanup_deadline=min(cell_deadline,time.monotonic()+eval_cap+grace_left)
            e=owned_phase(command,child/'evaluation',eval_cap,
                          global_deadline,eval_cleanup_deadline)
            row['evaluation_supervision']=e
            result=child/'evaluation/result.json'
            row['evaluation']=core.decode(result.read_bytes()) if e['status']=='COMPLETE' and result.exists() else None
        else:row['evaluation']=None
        row['cell_wall_seconds']=time.monotonic()-cell_start
        row['cell_envelope_exceeded']=row['cell_wall_seconds']>cap+120+10
        atomic_owned(out/'progress.json',{'rows':rows,'cells_seen':len(rows),
                                        'scientific_cells_attempted':sum(r.get('policy_supervision',{}).get('released',False) for r in rows),
                                        'global_wall_seconds':time.monotonic()-global_start})
    import check_termination_comparison as evaluator
    summary=evaluator.aggregate(rows)
    summary.update(global_wall_seconds=time.monotonic()-global_start,setup_wall_seconds=setup_elapsed,
                   global_budget_seconds=6900,global_envelope_exceeded=time.monotonic()>global_deadline,
                   native_runs=0,hard_realtime_guarantee=False)
    write_new(out/'summary.json',summary)
    write_new(out/'summary-seal-observation.json',{
        'global_wall_through_summary_seal_seconds':time.monotonic()-global_start,
        'global_envelope_exceeded_through_summary_seal':time.monotonic()>global_deadline,
        'receipt_write_excluded_from_this_observation':True})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker',choices=['setup','policy','evaluation'])
    parser.add_argument('--input');parser.add_argument('--input-sha');parser.add_argument('--arm')
    parser.add_argument('--execute',action='store_true');parser.add_argument('--output')
    parser.add_argument('--plan-sha');parser.add_argument('--implementation-sha')
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.worker:worker_main(args)
    elif args.self_test:
        subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).with_name('test_termination_comparison.py'))],check=True)
    elif args.execute and args.output and args.plan_sha and args.implementation_sha:study(args)
    else:parser.error('explicit --execute/--output/two hashes or --self-test required')


if __name__=='__main__':main()
