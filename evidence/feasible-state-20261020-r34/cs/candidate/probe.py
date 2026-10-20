"""R34 physical-call execution with lossless identical-trace storage sharing."""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import codec
from hcr.model import fingerprint,Config
from tools.r19_cross_level.probe import read,put,sha,require
SPEC=ROOT/'experiments/exp-80-feasible-state/frozen_spec.json';OUT=ROOT/'runs/technical'

def inputs():
    p=read(SPEC);require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'input pins');return p

def preparation():
    import itertools,ast
    from tools.r33_typed_feedback.runtime import program
    p=inputs();checks=0
    for doc in p['programs'].values():program(doc).validate(Config(**p['kernel']))
    for name,features in [('one',['x','y0']),('either',['x','y0','y1']),('both',['x','y0','y1']),('feasible',['f0','f1']),('query',['f0','f1','t0','t1'])]:
        for bits in itertools.product([False,True],repeat=len(features)):
            state=dict(zip(features,bits))
            for g in p['programs'][name]['groups']:
                if g['id'] in state:continue
                links=[e for e in p['programs'][name]['links'] if e['kind']=='support' and e['target']==g['id']];terms=[state[e['source']] if e['weight']>0 else not state[e['source']] for e in links];state[g['id']]=all(terms) if g['bias']<0 else any(terms)
            if name=='feasible':require([state[k] for k in ['none','u0','u1','many']]==[not bits[0] and not bits[1],bits[0] and not bits[1],not bits[0] and bits[1],bits[0] and bits[1]],'feasible Boolean grammar')
            elif name=='query':
                values=[bits[i+2] for i in range(2) if bits[i]];expected=[bool(values) and all(values),bool(values) and not any(values),not values,bool(values) and any(values) and not all(values)];require([state[k] for k in ['qtrue','qfalse','empty','mixed']]==expected,'universal query Boolean grammar')
            else:
                m=[bits[0]==b for b in bits[1:]];require(state['goal']==(m[0] if name=='one' else any(m) if name=='either' else all(m)),'role Boolean grammar')
            checks+=1
    factors={(c['namespace'],c['order'],c['initial'],c['mode'],c['t_mode'],c['prior']) for c in p['cases']};require(len(factors)==len(p['cases'])==576,'factorial completeness');checks+=576
    tree=ast.parse((ROOT/'tools/r34_feasible_state/runtime.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='consume_t');require([a.arg for a in fn.args.args]==['binding','t','t_mode','vocabulary','cfg','docs','initial'],'T boundary signature')
    put(OUT/'preparation.json',dict(status='PASS',checks=checks,native_calls=0))

class Recorder:
    def __init__(self,p):self.p=p;self.seen={};self.items={};self.calls=0;self.keys={fingerprint(v):k for k,v in p['programs'].items()}
    def add(self,k):
        self.calls+=1;digest=fingerprint(dict(kernel=k,config=self.p['kernel']))
        if digest in self.seen:
            key=self.seen[digest];require(self.items[key]==k,'content collision exact equality');return key
        key='n%03d'%len(self.seen);self.seen[digest]=key;self.items[key]=k;pr=k['program'];ids=[g['id'] for g in pr['groups']];iv=list(k['initial'].values());require(len(set(iv))==1,'uniform initial codec')
        doc=dict(schema='hcr-r34-lossless-native-v1',program_key=self.keys[fingerprint(pr)],program_sha256=k['program_sha256'],config_sha256=fingerprint(self.p['kernel']),content_sha256=digest,drives=k['drives'],initial_scalar=iv[0],tick_vectors=[[r['residual'],r['stable_steps'],*[r['state'][x] for x in ids]] for r in k['ticks']],final_vector=[k['state'][x] for x in ids],convergence=k['convergence'],cost=k['cost'],adopted=k['adopted'])
        put(OUT/(key+'.json'),doc);return key

def work():
    from tools.r34_feasible_state.runtime import lower,export,execute
    p=inputs();started=time.process_time();sources={s['key']:lower(s['observation'],s['predicate'],p['kernel']) for s in p['sources']};put(OUT/'sources.json',sources);source_cpu=time.process_time()-started
    recorder=Recorder(p);metrics=[];batch=[];part=0
    for c in p['cases']:
        for arm in c['arms']:
            start=time.process_time();wall=time.perf_counter();needed=c['candidates']+c['context']+c['T'];packets={key:export(sources[key]) for key in needed};require(all(packets[key]['origin_sha256']==fingerprint(sources[key]) for key in packets),'source guard')
            r=execute([packets[k] for k in c['candidates']],[packets[k] for k in c['context']],c['mode'],[packets[k] for k in c['T']],c['t_mode'],c['vocabulary'],c['evidence'],arm,p['kernel'],p['programs'],c['initial']);core_cpu=time.process_time()-start;storage=time.process_time();r['case']=c['key']
            if arm=='exact':r['network_ids']=[]
            else:
                ks=[*r.pop('context_kernels'),r.pop('feasible_kernel'),*r['final'].pop('matches'),r['final'].pop('kernel')];r['network_ids']=[recorder.add(k) for k in ks]
                del r['binding']['alternatives'];r['binding']['alternative_keys']=c['candidates']
            batch.append(r);metrics.append(dict(case=c['key'],arm=arm,core_cpu_seconds=core_cpu,storage_cpu_seconds=time.process_time()-storage,wall_seconds=time.perf_counter()-wall))
        if len(batch)==144:
            put(OUT/('batch%02d.json'%part),batch);part+=1;batch=[]
    require(not batch and part==12 and recorder.calls==6912,'all physical calls emitted')
    put(OUT/'work-ledger.json',dict(physical_numeric_calls=recorder.calls,source_calls=12,unique_trace_records=len(recorder.items),storage_references=recorder.calls,computation_reused=False,trace_storage_only_shared=True,source_cpu_seconds=source_cpu,metrics=metrics))

def audit_all():
    from tools.r34_feasible_state.verify import verify_networks,audit,mutations
    from tools.r32_semantic_join.runtime import export
    from tools.r32_semantic_join.verify import audit_lower
    p=inputs();documents={f.stem:read(f) for f in OUT.glob('n[0-9][0-9][0-9].json')};networks,error=verify_networks(documents,p);sources=read(OUT/'sources.json');packets={k:export(v) for k,v in sources.items()};lower=[audit_lower(sources[s['key']],s,p) for s in p['sources']];records=[r for i in range(12) for r in read(OUT/('batch%02d.json'%i))];by_case={c['key']:c for c in p['cases']};rows=[audit(r,by_case[r['case']],packets,p,networks) for r in records];r=next(r for r in records if r['arm']=='full');rejected=mutations(r,by_case[r['case']],packets,p,networks)
    calls=12+sum(r['physical_native_calls'] for r in rows);ticks=sum(r['ticks'] for r in rows)+sum(r['ticks'] for r in lower);require(calls==6924 and ticks<=1107840,'native caps')
    counts={}
    for arm in p['arms']:
        subset=[r for r in rows if r['arm']==arm];counts[arm]=dict(cases=len(subset),strict=sum(r['strict_correct'] for r in subset),value=sum(r['value_correct'] for r in subset),kind=sum(r['kind_correct'] for r in subset),reason=sum(r['query_reason_correct'] for r in subset),calls=sum(r['physical_native_calls'] for r in subset),ticks=sum(r['ticks'] for r in subset),groups=sum(r['groups'] for r in subset),links=sum(r['links'] for r in subset))
    put(OUT/'summary.json',dict(status='AUDITED',counts=counts,sources=lower,unique_traces=len(networks),physical_calls=calls,ticks=ticks,max_scalar_error=max(error,max(x['numeric_replay_max_absolute_error'] for x in lower)),mutation_rejections=rejected,learning=0,world_measurement=0,production_adoption=False))

def run(started):
    import resource,signal,subprocess,traceback,zipfile
    p=inputs();limits=p['limits'];OUT.mkdir(parents=True,exist_ok=False);deadline=started+limits['total_seconds']-30;stages=[];failure=None;manifest=read(ROOT/'source_manifest.json')
    def terminate(signum,frame):raise TimeoutError('termination signal '+str(signum))
    signal.signal(signal.SIGTERM,terminate)
    def source_check():return {n:(ROOT/n).is_file() and sha(ROOT/n)==h for n,h in manifest.items()}
    def limit():resource.setrlimit(resource.RLIMIT_AS,(limits['child_address_space_bytes'],)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(limits['child_file_bytes'],)*2)
    try:
        require(all(source_check().values()),'source preflight')
        for phase in ['preparation','work','audit']:
            before=time.monotonic();u=resource.getrusage(resource.RUSAGE_CHILDREN);require(deadline-before>30,'deadline reserve')
            with (OUT/(phase+'.stdout')).open('xb') as stdout,(OUT/(phase+'.stderr')).open('xb') as stderr:
                child=subprocess.Popen([sys.executable,'-B',str(Path(__file__)),'--phase',phase],stdout=stdout,stderr=stderr,preexec_fn=limit)
                try:rc=child.wait(timeout=min(limits['stage_seconds'],deadline-time.monotonic()-20))
                except BaseException:child.kill();child.wait();raise
            v=resource.getrusage(resource.RUSAGE_CHILDREN);raw=sum(f.stat().st_size for f in OUT.iterdir() if f.is_file());stages.append(dict(phase=phase,returncode=rc,wall_seconds=time.monotonic()-before,cpu_seconds=v.ru_utime+v.ru_stime-u.ru_utime-u.ru_stime,raw_bytes=raw));require(rc==0 and raw<=limits['raw_bytes'],'stage/cap failure '+phase)
    except BaseException:failure=traceback.format_exc()
    finally:
        post=source_check();put(OUT/'source-postcheck.json',dict(unchanged=all(post.values()),files=post))
        if not all(post.values()):failure=(failure or '')+'\nsource postcheck failed'
        if failure:put(OUT/'failure.json',dict(traceback=failure,retry=False))
        put(OUT/'result.json',dict(status='FAILED' if failure else 'COMPLETED',stages=stages,source_unchanged=all(post.values()),source_manifest_sha256=sha(ROOT/'source_manifest.json'),seconds_before_seal=time.monotonic()-started,python=sys.version.split()[0],platform=sys.platform,retry=False))
        put(OUT/'manifest.json',{f.name:dict(sha256=sha(f),bytes=f.stat().st_size) for f in sorted(OUT.iterdir()) if f.is_file()})
        with zipfile.ZipFile(ROOT/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for f in sorted(OUT.iterdir()):
                if f.is_file():z.write(f,'technical/'+f.name)
        put(ROOT/'completion.json',dict(completed=failure is None,seconds_including_seal=time.monotonic()-started,within_wall_limit=time.monotonic()-started<limits['total_seconds'],evidence_sha256=sha(ROOT/'evidence.zip'),evidence_bytes=(ROOT/'evidence.zip').stat().st_size))
    if failure:raise SystemExit(1)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','preparation','work','audit']);a.add_argument('--started',type=float);args=a.parse_args()
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise ValueError('R34 world measurement forbidden')
    World.measure=forbidden
    if args.phase=='run':run(args.started or time.monotonic())
    elif args.phase=='preparation':preparation()
    elif args.phase=='work':work()
    else:audit_all()
