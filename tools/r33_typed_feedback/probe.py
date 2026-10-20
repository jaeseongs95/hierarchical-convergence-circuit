"""Frozen factorial R33; worker1, no retries, no training/world measurement."""
import argparse,base64,hashlib,json,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from hcr import codec
from hcr.model import fingerprint
from tools.r19_cross_level.probe import read,put,sha,require
SPEC=ROOT/'experiments/exp-79-typed-feedback/frozen_spec.json';OUT=ROOT/'runs/technical'

def inputs():
    p=read(SPEC);require(all(sha(ROOT/n)==h for n,h in read(SPEC.with_name('input_manifest.json')).items()),'input pins');return p

def preparation():
    import ast,itertools
    p=inputs();n=0
    from tools.r33_typed_feedback.runtime import program
    from hcr.model import Config
    for doc in p['programs'].values():program(doc).validate(Config(**p['kernel']))
    seen=set()
    for c in p['cases']:
        key=(c['namespace'],c['order'],c['initial'],c['mode'],c['prior'],c['t']);require(key not in seen,'factor duplicate');seen.add(key)
        require(len(c['candidates'])==2 and len(c['context'])==2 and len(set(c['vocabulary']))==2,'binary slot grammar');n+=1
    require(n==288 and len(p['sources'])==12 and len(p['chunks'])==12 and sum(map(len,p['chunks']))==288,'frozen factorial counts')
    # Exhaustive authored Boolean graph logic and role coding, no native call.
    for name in ['one','either','both']:
        doc=p['programs'][name];features=[g['id'] for g in doc['groups'] if g['level']==0]
        for bits in itertools.product([False,True],repeat=len(features)):
            v=dict(zip(features,bits))
            for g in doc['groups']:
                if g['id'] in v:continue
                incoming=[e for e in doc['links'] if e['kind']=='support' and e['target']==g['id']]
                terms=[v[e['source']] if e['weight']>0 else not v[e['source']] for e in incoming]
                v[g['id']]=all(terms) if g['bias']<0 else any(terms)
            matches=[bits[0]==bits[i] for i in range(1,len(bits))]
            expected=matches[0] if name=='one' else any(matches) if name=='either' else all(matches)
            require(v['goal']==expected,'Boolean graph grammar');n+=1
    # Final consumer cannot directly receive first C or feedback.
    tree=ast.parse((ROOT/'tools/r33_typed_feedback/runtime.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='consume_t')
    require([x.arg for x in fn.args.args]==['binding','t','vocabulary','cfg','doc','initial'],'T boundary signature')
    put(OUT/'preparation.json',dict(status='PASS',structural_checks=n,native_calls=0,maximum_calls=p['maximum_native_settle_calls']))

def sources():
    from tools.r32_semantic_join.runtime import lower
    p=inputs();result={s['key']:lower(s['observation'],s['predicate'],p['kernel']) for s in p['sources']};put(OUT/'sources.json',result)

def batch(index):
    from tools.r33_typed_feedback.runtime import export,execute
    p=inputs();source=read(OUT/'sources.json');by_key={c['key']:c for c in p['cases']};metrics=[]
    for key in p['chunks'][index]:
        c=by_key[key]
        for arm in c['arms']:
            cpu=time.process_time();wall=time.perf_counter()
            used=c['candidates']+c['context']+[c['t']];packets={k:export(source[k]) for k in used}
            require(all(packets[k]['predicate']==source[k]['predicate'] and packets[k]['origin_sha256']==fingerprint(source[k]) for k in packets),'source guard')
            r=execute([packets[k] for k in c['candidates']],[packets[k] for k in c['context']],packets[c['t']],c['vocabulary'],c['evidence'],c['mode'],arm,p['kernel'],p['programs'],c['initial']);r['case']=key
            r['bridge']=dict(source_records_loaded=len(used),source_record_bytes=sum(len(codec.dumps(source[k]).encode()) for k in used),packet_bytes=sum(len(codec.dumps(packets[k]).encode()) for k in used),source_hash_recomputations=len(used)*2,packet_hash_fields=len(used)*4,independent_evidence_added=0)
            name=key+'__'+arm+'.json';put(OUT/name,r)
            metrics.append(dict(case=key,arm=arm,file=name,cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall,serialized_bytes=(OUT/name).stat().st_size))
    put(OUT/('metrics%02d.json'%index),metrics)

def audit_all():
    from tools.r33_typed_feedback.verify import audit,mutants
    from tools.r32_semantic_join.runtime import export
    from tools.r32_semantic_join.verify import audit_lower
    p=inputs();source=read(OUT/'sources.json');packets={k:export(s) for k,s in source.items()};lower=[audit_lower(source[s['key']],s,p) for s in p['sources']];rows=[];representative=None
    for c in p['cases']:
        for arm in p['arms']:
            r=read(OUT/(c['key']+'__'+arm+'.json'));rows.append(audit(r,c,packets,p))
            if representative is None and arm=='full' and r['packet']['selected'] is not None:representative=(r,c)
    rejected=mutants(*representative,packets,p);calls=len(lower)+sum(r['native_settles'] for r in rows);ticks=sum(r['ticks'] for r in lower)+sum(r['ticks'] for r in rows)
    require(calls==p['maximum_native_settle_calls'] and ticks<=p['maximum_logical_ticks'],'call/tick caps')
    put(OUT/'summary.json',dict(status='AUDITED',sources=lower,rows=rows,rejected_mutations=rejected,native_settle_calls=calls,kernel_ticks=ticks,training_calls=0,world_measure_calls=0,
        numeric_replay_max_absolute_error=max(r['numeric_replay_max_absolute_error'] for r in lower+rows),production_adoption=False,statistical_speed_verdict=None))

def handle_terminate(signum,frame):raise TimeoutError('termination signal '+str(signum))

def run(started):
    import resource,signal,subprocess,traceback
    p=inputs();limits=p['limits'];OUT.mkdir(parents=True,exist_ok=False);signal.signal(signal.SIGTERM,handle_terminate);stages=[];failure=None;deadline=started+limits['total_seconds']-30;manifest=read(ROOT/'source_manifest.json')
    def source_check():return {n:(ROOT/n).is_file() and sha(ROOT/n)==h for n,h in manifest.items()}
    def stage(phase,item=''):
        require(deadline-time.monotonic()>30,'budget reserve');before=time.monotonic();u=resource.getrusage(resource.RUSAGE_CHILDREN)
        def limit():
            resource.setrlimit(resource.RLIMIT_AS,(limits['child_address_space_bytes'],)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(limits['child_file_bytes'],)*2)
        with (OUT/(phase+item+'.stdout')).open('xb') as stdout,(OUT/(phase+item+'.stderr')).open('xb') as stderr:
            child=subprocess.Popen([sys.executable,'-B',str(Path(__file__)),'--phase',phase,'--item',item],stdout=stdout,stderr=stderr,preexec_fn=limit)
            try:rc=child.wait(timeout=min(limits['stage_seconds'],deadline-time.monotonic()-20))
            except BaseException:child.kill();child.wait();raise
        v=resource.getrusage(resource.RUSAGE_CHILDREN);raw=sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file());stages.append(dict(phase=phase,item=item,returncode=rc,raw_bytes=raw,wall_seconds=time.monotonic()-before,child_cpu_seconds=v.ru_utime+v.ru_stime-u.ru_utime-u.ru_stime));require(rc==0 and raw<=limits['raw_bytes'],'stage/cap failure '+phase+item)
    try:
        require(all(source_check().values()),'source preflight');stage('preparation');stage('sources')
        for i in range(len(p['chunks'])):stage('batch',str(i))
        stage('audit')
    except BaseException:failure=traceback.format_exc()
    finally:
        post=source_check();put(OUT/'source-postcheck.json',dict(unchanged=all(post.values()),files=post))
        if not all(post.values()):failure=(failure or '')+'\nsource postcheck failed'
        if failure:put(OUT/'failure.json',dict(traceback=failure,stages=stages,automatic_retry=False))
        put(OUT/'result.json',dict(status='FAILED' if failure else 'COMPLETED',stages=stages,source_unchanged=all(post.values()),seconds_before_seal=time.monotonic()-started,source_manifest_sha256=sha(ROOT/'source_manifest.json'),python_version=sys.version.split()[0],platform=sys.platform,automatic_retry=False,total_wall_limit_seconds=limits['total_seconds']))
        put(OUT/'manifest.json',{f.relative_to(OUT).as_posix():sha(f) for f in sorted(OUT.rglob('*')) if f.is_file()})
        with zipfile.ZipFile(ROOT/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
            for f in sorted(OUT.rglob('*')):
                if f.is_file():z.write(f,'technical/'+f.relative_to(OUT).as_posix())
        completion=dict(completed=failure is None,seconds_including_seal=time.monotonic()-started,within_wall_limit=time.monotonic()-started<limits['total_seconds'],evidence_sha256=sha(ROOT/'evidence.zip'),evidence_bytes=(ROOT/'evidence.zip').stat().st_size)
        put(ROOT/'completion.json',completion)
        # Generated experimental evidence only: transport archive for hosts without binary save.
        put(ROOT/'transfer.json',dict(schema='hcr-r33-evidence-transfer-v1',archive_sha256=completion['evidence_sha256'],archive_bytes=completion['evidence_bytes'],base64_zip=base64.b64encode((ROOT/'evidence.zip').read_bytes()).decode()))
    if failure:raise SystemExit(1)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--phase',required=True,choices=['run','preparation','sources','batch','audit']);a.add_argument('--item',default='');a.add_argument('--started',type=float);args=a.parse_args()
    from hcr.tasks.toy_world import World
    def forbidden(*a,**k):raise ValueError('R33 world measurement forbidden')
    World.measure=forbidden
    if args.phase=='run':run(args.started if args.started is not None else time.monotonic())
    elif args.phase=='preparation':preparation()
    elif args.phase=='sources':sources()
    elif args.phase=='batch':batch(int(args.item))
    else:audit_all()
