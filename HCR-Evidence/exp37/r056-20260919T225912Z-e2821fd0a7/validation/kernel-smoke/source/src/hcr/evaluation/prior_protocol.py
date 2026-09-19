"""EXP-12 생성기와 파일 검산 진입점. 기존 EXP-09/10/11 기록은 변경하지 않는다."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from time import perf_counter
import csv
import hashlib
from .. import codec, session_io
from ..model import AdaptiveConfig, AdaptiveCost, Feedback, Mode, Program, Group, Link
from .audit import require
from .reference import assess
from .prior_spec import PROTOCOL, ARMS, TRAINING_COUNTS, arm_options, fixtures, training_world, condition_plan, cells
from .prior_audit import audit_packet, verify_task, source_network, verify_fixed, fixed_pair
from .prior_analysis import record_metrics, summarize, render


def _load(path):return codec.loads(session_io.read_bytes(path))
def _hash(path):return hashlib.sha256(session_io.read_bytes(path)).hexdigest()


def run_task(config, memory, n, case, arm):
    from ..sessions import AdaptiveSession
    before=memory.document();start=perf_counter();options=arm_options(arm)
    session=AdaptiveSession(config,memory,session_id='prior-task',**options)
    init=perf_counter()-start
    obs=codec.observation_from(case['observation'])
    session.begin(obs,Mode.FROZEN_EVAL);decision=session.complete();total=perf_counter()-start
    require(session.memory_document==before and memory.document()==before,'inference changed frozen memory')
    t=perf_counter();packet=session.packet();packet_seconds=perf_counter()-t
    return dict(schema='hcr-exp12-task-r031-v1',training_count=n,case=case['name'],family=case['family'],arm=arm,
                **options,observation=codec.plain(obs),initial_memory=before,packet=packet,
                decision=codec.plain(decision),timing=dict(total_wall_seconds=total,initialization_seconds=init,
                engine_active_seconds=decision.cost['wall_seconds'],management_seconds=max(0.0,total-decision.cost['wall_seconds']),
                packet_seconds=packet_seconds))


def run_fixed(legacy, scope):
    from ..dynamics import settle_recorded
    from ..trace import Trace
    event,ref=source_network(legacy);p=event['payload'];config=codec.adaptive_config_from(legacy['packet']['document']['engine']['config'])
    program=Program(tuple(Group(**g) for g in p['program']['groups']),tuple(Link(**l) for l in p['program']['links']),
                    tuple(tuple(path) for path in p['program']['paths']),p['program']['edge_count'])
    # Here only learned relation/goal drives are ablated. No frontier manipulation or task readout guard.
    drives=dict(p['drives'])
    if scope=='route_only':drives={k:v if k.startswith('e:') else 0.0 for k,v in drives.items()}
    require(scope in ('legacy','route_only'),'unknown fixed scope')
    trace=Trace();cost=AdaptiveCost()
    state,conv,_=settle_recorded(program,drives,config.kernel,cost,trace,'fixed-network','decision',
        dict(fixed_network=True,source_ref=ref,scope=scope),top_down=True)
    return dict(schema='hcr-exp12-fixed-network-v1',training_count=legacy['training_count'],case=legacy['case'],scope=scope,
        source_ref=ref,config=codec.plain(config),program=codec.plain(program),initial={g.id:.5 for g in program.groups},
        drives=drives,events=trace.records,state=state,convergence=codec.plain(conv),cost=cost.snapshot())


def _inventory(root):
    names=set()
    for p in root.rglob('*'):
        session_io.safe_path(p)
        if p.is_file():names.add(p.relative_to(root).as_posix())
    return names


def _expected_files(sources):
    out={'plan.json','training.json','summary.json','summary.ko.md','costs.csv','audit.json'}
    out|={'source/'+n for n in sources}
    out|={'seed/'+str(n)+'.json' for n in TRAINING_COUNTS}
    for n,case,arm in cells():
        tail=f"{n}/{case['name']}/{arm}.json"
        out|={'raw/'+tail,'records/'+tail}
    for n in TRAINING_COUNTS:
        for case in fixtures():
            out|={f"fixed/{n}/{case['name']}/{scope}.json" for scope in ('legacy','route_only')}
    return out


def verify_data(root, *, require_summary=True):
    """완료 전/후 같은 검사를 사용한다. 새 inference 없이 기록·수치·조건·파생값만 검사."""
    plan=_load(root/'plan.json')
    require(set(plan)=={'schema','created_at_utc','conditions','source_hashes'} and plan['schema']=='hcr-exp12-plan-v1'
            and plan['conditions']==condition_plan(),'EXP-12 frozen plan')
    require(plan['source_hashes']==session_io.source_hashes(),'EXP-12 verifier source mismatch')
    for name,digest in plan['source_hashes'].items():
        require(hashlib.sha256(session_io.read_bytes(root/'source'/name).replace(b'\r\n',b'\n')).hexdigest()==digest,'frozen source bytes')
    training=_load(root/'training.json');require(len(training)==9,'training condition count')
    from ..circuits import AdaptiveMemory
    config=AdaptiveConfig();memories={};totals=Counter()
    for n in TRAINING_COUNTS:
        seed=_load(root/'seed'/f'{n}.json');report=audit_packet(seed);core=seed['document']['engine']
        require(core['config']==codec.plain(config) and core['switches']==dict(use_circuits=True,top_down=True,allow_reexpansion=True)
                and 'prior_policy' not in core and len(core['held'])==n and len(core['feedback'])==n,'seed legacy training')
        require(seed['document']['events'][0]['payload']['memory_document']==AdaptiveMemory.empty(config).document(),
                'seed must start with the complete empty memory document')
        for i,row in enumerate(training[:n]):
            w=training_world(i);d=codec.adaptive_decision_from(row['decision']);a=assess(d,w.observation,dict(w.hidden))
            require(row['observation']==codec.plain(w.observation) and row['external_truth']==dict(w.hidden)
                    and row['assessment']==codec.plain(a) and a.correct is True,'external training evaluation')
            require(core['held'][d.id]['decision']==row['decision'] and core['held'][d.id]['observation']==row['observation'], 'seed source binding')
            expected=codec.plain(Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True))
            require(core['feedback'][d.id]==expected,'training feedback was not externally evaluated')
        memories[n]=core['memory']
        if n==9:totals['training_scalar_ticks_replayed']=report['scalar_ticks_replayed']
    rows=[];bykey={}
    for n,case,arm in cells():
        tail=f"{n}/{case['name']}/{arm}.json";raw=_load(root/'raw'/tail)
        audit,outcomes=verify_task(raw,case,n,arm,memories[n],config)
        metrics=record_metrics(raw)
        stored=_load(root/'records'/tail)
        row=dict(raw=raw,metrics=metrics,assessments=outcomes)
        require(stored==dict(raw_sha256=_hash(root/'raw'/tail),metrics=metrics,assessments=outcomes,audit=audit),'derived record mismatch')
        rows.append(row);bykey[(n,case['name'],arm)]=raw
        totals['task_scalar_ticks_replayed']+=audit['scalar_ticks_replayed']
        totals['graph_steps_checked']+=audit['graph_steps_checked'];totals['world_evaluations']+=audit['worlds_evaluated']
    fixed=[]
    for n in TRAINING_COUNTS:
        for case in fixtures():
            parent=root/'fixed'/str(n)/case['name'];legacy=bykey[(n,case['name'],'legacy')]
            pair=fixed_pair(_load(parent/'legacy.json'),_load(parent/'route_only.json'),legacy)
            fixed.append(pair);totals['fixed_scalar_ticks_replayed']+=pair['scalar_ticks_replayed']
    summary=summarize(rows,fixed)
    require(all(p['same_memory'] and p['same_observation'] and p['initial_routing_equal'] for p in summary['paired_cells']), 'initial routing control failed')
    if require_summary:
        require(_load(root/'summary.json')==summary,'summary reaggregation')
        require(session_io.read_bytes(root/'summary.ko.md').decode('utf-8')==render(summary),'rendered summary mismatch')
        # CSV is verified semantically; absence/extra fields cannot hide an altered counter.
        import io
        actual=list(csv.DictReader(io.StringIO(session_io.read_bytes(root/'costs.csv').decode('utf-8'))))
        expected=[{k:str(v) for k,v in r.items()} for r in cost_rows(rows)]
        require(actual==expected,'cost CSV reaggregation')
    return dict(schema='hcr-exp12-audit-r031-v1',verified=True,task_inferences=len(rows),training_inferences=9,
                fixed_network_pairs=len(fixed),fixed_network_replays=2*len(fixed),source_checked=True,
                initial_routing_controls_checked=len(fixed),**dict(totals),new_inferences=0,
                legacy_learning_rule_changed=False,pool_rule_changed=False,
                scope='session event/state audit + independent fixed recurrence + external assessment + reaggregation',
                limitations=['검산은 기록 일관성이지 실제 OS 실행의 외부 인증이 아니다.',
                    '고정 network는 전체 추론과 별도 계산이며 같은 입력의 두 hidden world는 별도 추론이 아니다.',
                    'seed/외부 채점은 기존 reference를 재사용한다. wall time은 재현하지 않는다.']),summary


def cost_rows(rows):
    return [dict(training_count=r['raw']['training_count'],case=r['raw']['case'],arm=r['raw']['arm'],
                 **{k:r['metrics'][k] for k in ('expansions','circuit_reuses','binding_operations','pool_ticks','decision_ticks',
                 'pool_signals','decision_signals','end_to_end_wall_seconds','engine_active_seconds','management_seconds')}) for r in rows]


def verify_run(root):
    root=session_io.safe_path(root);manifest=_load(root/'manifest.json')
    require(manifest['schema']=='hcr-exp12-manifest-v1' and manifest['state']=='complete','incomplete EXP-12')
    expected=_expected_files(session_io.source_hashes())
    require(set(manifest['files'])==expected and _inventory(root)==expected|{'manifest.json'},'missing/extra artifacts')
    for name,digest in manifest['files'].items():
        rel=PurePosixPath(name)
        require(not rel.is_absolute() and '..' not in rel.parts and '\\' not in name,'unsafe manifest path')
        require(_hash(root/name)==digest,'manifest checksum '+name)
    audit,_=verify_data(root)
    require(_load(root/'audit.json')==audit,'stored audit mismatch')
    return audit


def run_demo(out):
    from ..sessions import AdaptiveSession
    from ..circuits import AdaptiveMemory
    out=session_io.new_output(Path(out));out.mkdir(parents=True,exist_ok=False)
    plan=dict(schema='hcr-exp12-plan-v1',created_at_utc=datetime.now(timezone.utc).isoformat(),
              conditions=condition_plan(),source_hashes=session_io.source_hashes())
    codec.save(out/'plan.json',plan)
    stage='source';completed=0
    try:
        for name in plan['source_hashes']:
            p=out/'source'/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes((session_io.project_root()/name).read_bytes())
        stage='training';cfg=AdaptiveConfig();seed=AdaptiveSession(cfg,session_id='prior-training');training=[];memories={}
        for i in range(9):
            w=training_world(i);seed.begin(w.observation,Mode.TRAIN);d=seed.complete();a=assess(d,w.observation,dict(w.hidden))
            training.append(dict(observation=codec.plain(w.observation),external_truth=dict(w.hidden),decision=codec.plain(d),assessment=codec.plain(a)))
            seed.feedback(Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True))
            if i+1 in TRAINING_COUNTS:
                codec.save(out/'seed'/f'{i+1}.json',seed.packet());memories[i+1]=seed.memory_document
        codec.save(out/'training.json',training)
        rows=[];bykey={};stage='task_inference'
        for n,case,arm in cells():
            raw=run_task(cfg,AdaptiveMemory.from_document(memories[n],cfg),n,case,arm)
            tail=f"{n}/{case['name']}/{arm}.json";codec.save(out/'raw'/tail,raw);completed+=1
            audit,outcomes=verify_task(raw,case,n,arm,memories[n],cfg);metrics=record_metrics(raw)
            codec.save(out/'records'/tail,dict(raw_sha256=_hash(out/'raw'/tail),metrics=metrics,assessments=outcomes,audit=audit))
            rows.append(dict(raw=raw,metrics=metrics,assessments=outcomes));bykey[(n,case['name'],arm)]=raw
        stage='fixed_network';fixed=[]
        for n in TRAINING_COUNTS:
            for case in fixtures():
                legacy=bykey[(n,case['name'],'legacy')];pair=[]
                for scope in ('legacy','route_only'):
                    raw=run_fixed(legacy,scope);codec.save(out/'fixed'/str(n)/case['name']/(scope+'.json'),raw)
                    verify_fixed(raw,legacy);pair.append(raw)
                fixed.append(fixed_pair(*pair,legacy))
        stage='summary';summary=summarize(rows,fixed);codec.save(out/'summary.json',summary)
        (out/'summary.ko.md').write_bytes(render(summary).encode('utf-8'))
        cr=cost_rows(rows)
        with (out/'costs.csv').open('x',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(cr[0]));w.writeheader();w.writerows(cr)
        stage='audit';audit,_=verify_data(out);codec.save(out/'audit.json',audit)
        files={n:_hash(out/n) for n in sorted(_inventory(out))}
        require(set(files)==_expected_files(plan['source_hashes']),'output artifact inventory')
        codec.save(out/'manifest.json',dict(schema='hcr-exp12-manifest-v1',state='complete',files=files))
        verify_run(out)
        return dict(state='complete',directory=str(out),**{k:v for k,v in audit.items() if k!='new_inferences'},
                    new_task_inferences=len(rows),new_training_inferences=9,new_fixed_network_replays=2*len(fixed),audit_new_inferences=0)
    except BaseException as exc:
        if stage == 'training' and 'seed' in locals():
            codec.save(out/'partial_training.json',dict(packet=seed.packet(),rows=training))
        codec.save(out/'FAILED.json',dict(state='failed',stage=stage,task_inferences_recorded=completed,
                    error=type(exc).__name__+': '+str(exc),original_errors_preserved=True))
        raise
