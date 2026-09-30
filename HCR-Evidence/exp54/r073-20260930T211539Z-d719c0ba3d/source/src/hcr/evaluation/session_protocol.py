"""EXP-10: R0.2.1 진행 중 snapshot/restore의 동작 보존 개발 실험.

Generator는 로컬 toy world를, verifier는 기록·state audit·외부 proof 판정을 사용한다.
이 실험은 성능 우월성이나 새로운 연구 일반화를 측정하지 않는다.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from math import isfinite
from pathlib import Path, PurePosixPath
from .. import codec, session_io
from ..model import AdaptiveConfig, ContractError, Mode, Feedback, fingerprint
from .audit import require
from .reference import assess

PROTOCOL = 'exp10-r021-session-continuity-v1'


def clean_decision(d):
    d = deepcopy(d)
    d['cost'].pop('wall_seconds')
    return d


def clean_events(events):
    result=[]
    for e in events:
        p=deepcopy(e['payload'])
        if 'cost' in p:
            p['cost'].pop('wall_seconds',None)
        result.append(dict(seq=e['seq'],event=e['event'],payload=p))
    return result


def save_jsonl(path, records):
    session_io.publish(path, ''.join(codec.dumps(r)+'\n' for r in records).encode('utf-8'))


def read_jsonl(path):
    return [codec.loads(line) for line in session_io.read_bytes(path).splitlines() if line.strip()]


def summarize_records(records):
    bygroup={}
    for r in records:
        bygroup.setdefault(r['group'],{})[r['arm']]=r
    checks=[]
    costs=[]
    for group,arms in sorted(bygroup.items()):
        require(set(arms)=={'legacy','continuous','resumed'}, 'missing EXP-10 arm')
        legacy=arms['legacy']
        for arm in ('continuous','resumed'):
            r=arms[arm]
            checks.append(dict(group=group,arm=arm,
                decisions_equal=[clean_decision(x['decision']) for x in legacy['rows']]==[clean_decision(x['decision']) for x in r['rows']],
                assessments_equal=[x['assessment'] for x in legacy['rows']]==[x['assessment'] for x in r['rows']],
                observations_equal=[x['observation'] for x in legacy['rows']]==[x['observation'] for x in r['rows']],
                external_truth_equal=[x['external_truth'] for x in legacy['rows']]==[x['external_truth'] for x in r['rows']],
                memory_equal=legacy['memory']==r['memory'],
                engine_events_equal=clean_events(legacy['events'])==clean_events(r['events'])))
        for row in legacy['rows']:
            d=row['decision']
            costs.append(dict(group=group,case=row['case'],attempt=d['attempt'],value=d['value'],
                              correct=row['assessment']['correct'],primitive_D=d['proof']['primitive_depth'],
                              circuits=d['circuit_ids'],kernel_ticks=d['cost']['kernel_ticks'],
                              signal_transmissions=d['cost']['signal_transmissions'],expansions=d['cost']['expansions']))
    return dict(schema='hcr-exp10-summary-r021-v1', checks=checks,
        equivalent=all(all(c[k] for k in ('decisions_equal','assessments_equal','observations_equal','external_truth_equal','memory_equal','engine_events_equal')) for c in checks),
        baseline_behavior=costs, comparison_inferences=sum(len(r['rows']) for r in records),
        engine_improved=False, hypothesis_proved=False,
        timings_compared_for_equality=False, excluded_from_equality=['cost.wall_seconds','derived event SHA chain'],
        meaning='같은 R0.2 정책의 실행 방식 대조. 오답과 비용 증가도 보존해야 한다.')


def render(summary):
    lines=['# EXP-10 — R0.2.1 중단·복원·재개 비교', '',
           '현재 실행이 만든 개발 검증 기록이다. EXP-09의 새 연구 표본이 아니다.', '',
           f"동작 동등성: {summary['equivalent']}", '',
           '| 조건 | 비교 | 판단·proof·카운터 | 관측 | memory | engine 이벤트 |',
           '|---|---|---|---|---|---|']
    for c in summary['checks']:
        lines.append(f"| {c['group']} | legacy/{c['arm']} | {c['decisions_equal']} | {c['observations_equal']} | {c['memory_equal']} | {c['engine_events_equal']} |")
    lines+=['','## 그대로 보존한 판단','',
            '| 조건 | 사례 | 시도 | 출력 | 정답 | primitive D | tick | 확장 |',
            '|---|---|---:|---|---|---:|---:|---:|']
    for c in summary['baseline_behavior']:
        lines.append(f"| {c['group']} | {c['case']} | {c['attempt']} | {c['value']} | {c['correct']} | {c['primitive_D']} | {c['kernel_ticks']} | {c['expansions']} |")
    lines+=['', '## 검증 범위', '',
        'legacy는 현재 AdaptiveEngine.infer, continuous는 같은 진행 API의 중단 없는 session, resumed는 각 전이 뒤 실제 JSON 저장·복원을 수행한다.',
        'pool과 판단 settle은 한 dependency step 안에서 완료된다. 임의 tick 중단이나 background cognition을 구현한 실험이 아니다.',
        'cost.wall_seconds는 실제 계산 구간의 누적 시간이며 디스크 대기·세션 복사·검산 비용은 포함하지 않는다. checkpoint_io.jsonl에서 저장/복원 관리 비용(검산·직렬화 포함)을 따로 읽는다.',
        '오수렴·다른 부분회로 재선택·same-score 우회 정답은 동작 보존 대상이다. 이를 정답률 개선으로 집계하지 않는다.',
        'feedback은 generator의 외부 world 평가에서 생성된다. session 자체에는 hidden truth를 넣지 않는다.', '']
    return '\n'.join(lines)


def run_demo(out):
    from ..sessions import AdaptiveSession
    from ..runtime import AdaptiveEngine
    from ..circuits import AdaptiveMemory
    from ..tasks.toy_world import chain, diamond
    out=session_io.new_output(out)
    out.mkdir(parents=True,exist_ok=False)
    config=AdaptiveConfig()
    plan=dict(schema='hcr-exp10-plan-r021-v1',protocol=PROTOCOL,config=codec.plain(config),
              created_at_utc=datetime.now(timezone.utc).isoformat(),source_hashes=session_io.source_hashes(),
              training_episodes=6,arms=['legacy','continuous','resumed'],
              groups=['main','unknown','budget','no_reexpansion'],hypothesis_proved=False)
    codec.save(out/'plan.json',plan)
    try:
        for name in plan['source_hashes']:
            p=out/'source'/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes((session_io.project_root()/name).read_bytes())
        seed=AdaptiveSession(config,session_id='exp10-training')
        training=[]
        for i in range(6):
            w=chain(f'e{i:03}',(True,)*3,prefix=f'o{i:03}')
            seed.begin(w.observation,Mode.TRAIN);d=seed.complete();a=assess(d,w.observation,dict(w.hidden))
            training.append(dict(observation=codec.plain(w.observation),external_truth=dict(w.hidden),decision=codec.plain(d),assessment=codec.plain(a)))
            seed.feedback(Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True))
        seed.save(out/'seed.json');codec.save(out/'training.json',training)
        records=[]
        for group in plan['groups']:
            for arm in plan['arms']:
                cfg=replace(config,max_expansions=1) if group=='budget' else config
                memory=AdaptiveMemory.from_document(seed.memory_document,cfg) if group in ('main','no_reexpansion') else None
                flags=dict(use_circuits=group!='unknown',allow_reexpansion=group!='no_reexpansion')
                folder=out/group/arm;folder.mkdir(parents=True)
                s=None if arm=='legacy' else AdaptiveSession(cfg,memory,session_id='exp10-'+group,**flags)
                e=AdaptiveEngine(cfg,memory,**flags) if s is None else None
                rows=[];io=[]
                def invoke(name,*args,**kwargs):
                    nonlocal s
                    if s is None:
                        return getattr(e,name)(*args,**kwargs)
                    result=getattr(s,name)(*args,**kwargs)
                    if arm=='resumed':
                        ref=s.reference
                        p=folder/'checkpoints'/f"g{ref['generation']:04}.json"
                        saved=s.save(p);io.append(dict(saved,path=p.relative_to(out).as_posix()))
                        s=AdaptiveSession.load(p,expected_ref=ref)
                        io.append(dict(s.last_io,path=p.relative_to(out).as_posix()))
                    return result
                def infer(w,case,mode=Mode.FROZEN_EVAL,revision_of=None):
                    if s is None:
                        d=e.infer(w.observation,mode,revision_of=revision_of)
                    else:
                        invoke('begin',w.observation,mode,revision_of=revision_of)
                        while s.phase=='running':invoke('advance')
                        invoke_result=invoke('finish');d=invoke_result
                    a=assess(d,w.observation,dict(w.hidden))
                    rows.append(dict(case=case,observation=codec.plain(w.observation),external_truth=dict(w.hidden),
                                     decision=codec.plain(d),assessment=codec.plain(a)))
                    return d,a
                def feedback(w,d,a):
                    return invoke('feedback',Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True))
                if group=='main':
                    infer(chain('e101',(True,)*3,prefix='o101'),'familiar')
                    infer(chain('e102',(False,True,True),prefix='o102'),'counterfactual')
                    infer(chain('e103',(True,)*4,prefix='o103'),'longer')
                    infer(diamond('e104',(False,True,True,True),prefix='o104'),'branch')
                    w=chain('e105',(False,True,True),(-.06,.92,.92),prefix='o105')
                    d,a=infer(w,'weak_conflict',Mode.ADAPT);feedback(w,d,a)
                    req=invoke('request_revision',d.id)
                    require(req is not None,'expected authored revision fixture')
                    revised=replace(w,observation=replace(w.observation,revision=req.revision))
                    d2,a2=infer(revised,'same_score_revision',Mode.ADAPT,d.id);feedback(revised,d2,a2)
                    infer(chain('e106',(False,True,True),(-.06,.92,.92),prefix='o106'),'retention')
                elif group=='unknown':
                    infer(chain('e201',(True,True),(None,None),prefix='o201'),'unknown')
                elif group=='budget':
                    infer(chain('e301',(True,)*3,prefix='o301'),'budget')
                else:
                    w=chain('e401',(False,True,True),(-.06,.92,.92),prefix='o401')
                    d,a=infer(w,'disabled_revision',Mode.ADAPT);feedback(w,d,a)
                    require(invoke('request_revision',d.id) is None,'ablation must not revise')
                events=e.trace.records if s is None else s.events
                mem=e.memory.document() if s is None else s.memory_document
                if s is not None:s.save(folder/'final.json')
                record=dict(group=group,arm=arm,rows=rows,memory=mem,events=events)
                codec.save(folder/'record.json',record);save_jsonl(folder/'checkpoint_io.jsonl',io)
                records.append(record)
        summary=summarize_records(records)
        require(summary['equivalent'],'R0.2.1 behavior divergence')
        codec.save(out/'summary.json',summary)
        session_io.publish(out/'summary.ko.md',render(summary).encode('utf-8'))
        audit=_verify_artifacts(out)
        codec.save(out/'audit.json',audit)
        manifest=dict(schema='hcr-exp10-manifest-r021-v1',state='complete',files={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(out.rglob('*')) if p.is_file()})
        codec.save(out/'manifest.json',manifest)
        return dict(state='complete',verified=True,directory=str(out),**{k:summary[k] for k in ('equivalent','comparison_inferences')},
                    training_inferences=len(training),checkpoint_count=audit['checkpoint_count'],actual_llm_calls=0,actual_network_calls=0)
    except BaseException as exc:
        codec.save(out/'FAILED.json',dict(state='failed',error=str(exc)))
        raise


def _verify_artifacts(root):
    from ..sessions import verify_packet
    plan=codec.loads(session_io.read_bytes(root/'plan.json'))
    require(plan['protocol']==PROTOCOL and plan['source_hashes']==session_io.source_hashes(),'EXP-10 source/protocol')
    require(plan['training_episodes']==6 and plan['groups']==['main','unknown','budget','no_reexpansion']
            and plan['arms']==['legacy','continuous','resumed'],'EXP-10 plan matrix')
    for name,expected in plan['source_hashes'].items():
        p=PurePosixPath(name)
        require(p.as_posix()==name and '..' not in p.parts and name.startswith('src/hcr/') and '\\' not in name,'source path')
        raw=session_io.read_bytes(root/'source'/name)
        require(hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()==expected,'source snapshot')
    records=[];checkpoint_count=0;event_count=0
    from ..circuits import AdaptiveMemory
    cfg0=codec.adaptive_config_from(plan['config'])
    seed=codec.loads(session_io.read_bytes(root/'seed.json'));verify_packet(seed)
    training=codec.loads(session_io.read_bytes(root/'training.json'))
    require(len(training)==6,'seed episode count')
    def assess_rows(rows):
        for row in rows:
            obs=codec.observation_from(row['observation']);decision=codec.adaptive_decision_from(row['decision'])
            require(codec.plain(assess(decision,obs,row['external_truth']))==row['assessment'],'external assessment/proof mismatch')
    assess_rows(training)
    require([v['decision'] for v in seed['document']['engine']['held'].values()]==[r['decision'] for r in training]
            or {v['decision']['id']:v['decision'] for v in seed['document']['engine']['held'].values()}=={r['decision']['id']:r['decision'] for r in training},'seed decision correspondence')
    for group in plan['groups']:
        for arm in plan['arms']:
            folder=root/group/arm
            r=codec.loads(session_io.read_bytes(folder/'record.json'))
            require(r['group']==group and r['arm']==arm,'record label')
            require(len(r['rows'])==(7 if group=='main' else 1),'scenario coverage')
            assess_rows(r['rows'])
            cfg=replace(cfg0,max_expansions=1) if group=='budget' else cfg0
            initial=r['events'][0]
            require(initial['event']=='r02_engine_created','missing initial engine')
            ev=initial['payload']
            require(ev['config']==codec.plain(cfg) and ev['use_circuits'] is (group!='unknown')
                    and ev['top_down'] is True and ev['allow_reexpansion'] is (group!='no_reexpansion'),'configuration intervention')
            expected_seed=seed['document']['engine']['memory'] if group in ('main','no_reexpansion') else AdaptiveMemory.empty(cfg).document()
            require(ev['memory_document']==expected_seed,'seed memory intervention')
            if arm!='legacy':
                final=codec.loads(session_io.read_bytes(folder/'final.json'))
                result=verify_packet(final)
                event_count+=result['events'];checkpoint_count+=1
                doc=final['document'];held=doc['engine']['held']
                require(r['memory']==doc['engine']['memory'] and r['events']==doc['events']
                        and {row['decision']['id']:row['decision'] for row in r['rows']}=={k:v['decision'] for k,v in held.items()},'record/snapshot mismatch')
                snapshots=sorted((folder/'checkpoints').glob('*.json')) if (folder/'checkpoints').exists() else []
                if arm=='resumed':
                    require(len(snapshots)==len(doc['transitions'])-1,'every transition requires a checkpoint')
                else:require(not snapshots,'continuous arm wrote intermediate checkpoints')
                for generation,p in enumerate(snapshots,1):
                    cp=codec.loads(session_io.read_bytes(p));verify_packet(cp);checkpoint_count+=1
                    old=cp['document']
                    require(old['session_id']==doc['session_id'] and len(old['transitions'])==generation+1
                            and old['transitions']==doc['transitions'][:generation+1]
                            and old['events']==doc['events'][:len(old['events'])],'checkpoint prefix/ancestry mismatch')
                io=read_jsonl(folder/'checkpoint_io.jsonl')
                require(len(io)==2*len(snapshots),'checkpoint I/O count')
                for i,row in enumerate(io):
                    require(row['operation']==('save' if i%2==0 else 'load') and type(row['bytes']) is int and row['bytes']>0
                            and type(row['wall_seconds']) in (int,float) and isfinite(row['wall_seconds']) and row['wall_seconds']>=0,'checkpoint cost contract')
                    require(row['bytes']==snapshots[i//2].stat().st_size, 'checkpoint byte accounting')
                    relative=snapshots[i//2].relative_to(root).as_posix()
                    require(row['path']==relative and row['reference']==dict(session_id=doc['session_id'],generation=i//2+1,
                        state_hash=doc['transitions'][i//2+1]['after_state'],transition_hash=doc['transitions'][i//2+1]['sha256']), 'I/O generation linkage')
            records.append(r)
    summary=summarize_records(records)
    require(summary==codec.loads(session_io.read_bytes(root/'summary.json')) and summary['equivalent'],'summary recalculation')
    require(render(summary)==session_io.read_bytes(root/'summary.ko.md').decode('utf-8'),'summary text mismatch')
    return dict(schema='hcr-exp10-audit-r021-v1',verified=True,checkpoint_count=checkpoint_count+1,
                final_engine_events_checked=event_count,external_decisions_checked=sum(len(r['rows']) for r in records)+len(training),
                source_checked=True,new_inferences=0,r02_policy_changed=False,
                limitations=['현재 R0.2 정책의 중단/복원 동등성 개발 검증이다.',
                    '동일한 감사 함수를 재사용한다. feedback/seed의 외부 타당성은 제시한 toy world에 대해서만 평가한다.',
                    '기록 시간은 범위·연결만 검산하며 실제 측정 시간을 재현하지 않는다.'])


def verify_run(root):
    root=session_io.safe_path(root)
    manifest=codec.loads(session_io.read_bytes(root/'manifest.json'))
    require(manifest['schema']=='hcr-exp10-manifest-r021-v1' and manifest['state']=='complete','incomplete EXP-10 run')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'manifest.json'}
    require(actual==set(manifest['files']),'missing/extra EXP-10 artifacts')
    for name,expected in manifest['files'].items():
        rel=PurePosixPath(name)
        require(rel.as_posix()==name and not rel.is_absolute() and '..' not in rel.parts and '\\' not in name and ':' not in name,'unsafe artifact')
        require(hashlib.sha256(session_io.read_bytes(root/name)).hexdigest()==expected,'artifact hash mismatch: '+name)
    result=_verify_artifacts(root)
    require(codec.loads(session_io.read_bytes(root/'audit.json'))==result,'saved audit mismatch')
    return result
