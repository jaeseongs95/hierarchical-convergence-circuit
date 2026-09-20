"""EXP-15 raw 생성과 별도 evaluator. raw 생성 시 최종 정답을 성공 조건으로 삼지 않는다."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import io
import json
import platform
import subprocess
import sys
import traceback

from .. import selection_io as io15
from ..selection import digest
from .selection_spec import BASE_COMMIT, conditions, baseline_specs, cells, all_cases
from .selection_audit import demand, audit_flow


class TrainingSeedFailure(RuntimeError):
    """학습 seed의 논리 실패. schema/runtime 실패와 구분한다."""


def make_plan():
    from .. import session_io
    return dict(schema='hcr-exp15-plan-v1',conditions=conditions(),source_hashes=session_io.source_hashes(),
        created_at_utc=datetime.now(timezone.utc).isoformat())


def validate_plan(plan):
    from .. import session_io
    demand(set(plan)=={'schema','conditions','source_hashes','created_at_utc'} and plan['schema']=='hcr-exp15-plan-v1', 'plan schema')
    demand(plan['conditions']==conditions(), 'frozen experimental conditions changed')
    demand(plan['source_hashes']==session_io.source_hashes(), 'source changed since plan freeze')


def environment():
    from .. import session_io
    root=session_io.project_root()
    try:
        cp=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True,check=True,timeout=10)
        commit=cp.stdout.strip()
    except (OSError,subprocess.SubprocessError):commit=None
    return dict(python=sys.version,platform=platform.platform(),repository_head=commit,
        patch_basis=BASE_COMMIT,source_hashes_are_execution_identity=True,external_llm_used=False)


def generate(out,plan):
    """생성 단계. 최종 audit/summary는 다른 프로세스의 audit 명령이 작성한다."""
    from .. import codec, session_io
    from ..model import AdaptiveConfig, Feedback, Mode
    from ..circuits import AdaptiveMemory
    from ..sessions import AdaptiveSession
    from ..review import prepare_baseline, ReviewLimits
    from ..selection import SelectionLimits
    from ..selection_runtime import SelectionFlow, prepare_running
    from .prior_spec import training_world
    from .review_spec import provider_for
    from .reference import assess
    validate_plan(plan)
    root=io15.safe(out);root.mkdir(parents=True,exist_ok=False)
    cp=plan['conditions'];case_map=all_cases(cp);stage='plan';current=None;flow=None;completed=0
    try:
        io15.put(root/'plan.json',plan);io15.put(root/'environment.json',environment())
        stage='source'
        for name,h in plan['source_hashes'].items():
            data=io15.read(session_io.project_root()/name)
            demand(hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()==h, 'source snapshot differs: '+name)
            io15.put_bytes(io15.child(root,'source/'+name),data)
        stage='training'
        cfg=AdaptiveConfig();training=AdaptiveSession(cfg,session_id='selection-training');training_rows=[]
        for i in range(cp['training_count']):
            w=training_world(i);training.begin(w.observation,Mode.TRAIN);d=training.complete()
            a=assess(d,w.observation,dict(w.hidden))
            row=dict(observation=codec.plain(w.observation),external_truth=dict(w.hidden),decision=codec.plain(d),assessment=codec.plain(a))
            training_rows.append(row)
            # 학습 feedback은 평가 층에서만 계산한다. 잘못된 학습 seed는 결과를 보존하고 중단한다.
            if a.correct is not True:
                io15.put(root/'training_partial.json',training_rows)
                raise TrainingSeedFailure('training did not produce the declared verified seed')
            training.feedback(Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True))
        io15.put(root/'training.json',training_rows);io15.put(root/'seed/6.json',training.packet())
        memory=training.memory_document;bases={};stage='baselines'
        for spec in baseline_specs(cp):
            case=case_map[spec['case']];obs=codec.observation_from(case['observation'])
            mem=AdaptiveMemory.from_document(memory,cfg)
            b=(prepare_baseline(obs,cfg,mem,judgment_prior=spec['scope']) if spec['phase']=='readout_ready' else
               prepare_running(obs,cfg,mem,initial_advances=case['initial_advances']))
            bases[spec['key']]=b
            io15.put(io15.child(root,'baselines/'+spec['key']+'.json'),b)
        stage='rollouts'
        for cell in cells(cp):
            current=cell;flow=None
            log=io15.child(root,'attempt_logs/'+cell['id']+'.jsonl');log.parent.mkdir(parents=True,exist_ok=True)
            with log.open('x',encoding='utf-8',newline='\n') as f:
                def sink(e):
                    f.write(json.dumps(e,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n');f.flush()
                flow=SelectionFlow(bases[cell['baseline_key']],cell['arm'],limits=ReviewLimits(**cell['limits']),
                    selection_limits=SelectionLimits(**cell['selection_limits']),event_sink=sink)
                if cell['arm']=='observe_first':
                    case=case_map[cell['case']]
                    observer=provider_for(case['observation'],case['worlds'][cell['world']],cell['provider'])
                    result=flow.run(observer)
                else:result=flow.run()
            io15.put(root/'raw'/f"{cell['id']}.json",dict(cell=cell,result=result));completed+=1
        names=io15.inventory(root)
        io15.put(root/'manifest.json',dict(schema='hcr-exp15-raw-manifest-v1',state='raw_complete',
            independent_audit_pending=True,files={n:io15.checksum(root/n) for n in sorted(names)}))
        return dict(raw_complete=True,baselines=len(bases),rollouts=completed,independent_audit_pending=True)
    except BaseException as exc:
        failure_type=('logical_training_failure' if isinstance(exc,TrainingSeedFailure) else
            'parsing_failure' if isinstance(exc,(json.JSONDecodeError,UnicodeError)) else
            'runtime_io_failure' if isinstance(exc,OSError) else
            'schema_contract_failure' if isinstance(exc,ValueError) else 'runtime_failure')
        payload=dict(stage=stage,cell=current,completed_rollouts=completed,status=failure_type,
            error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),automatic_retry=False,
            partial_actions=[] if flow is None else flow.actions)
        if flow is not None and hasattr(flow,'partial_evidence'):
            try:payload['partial_evidence']=flow.partial_evidence()
            except BaseException as pe:payload['partial_capture_error']=str(pe)
        io15.put(root/'failure.json',payload)
        raise


def reachable(obs,truth):
    """평가 전용 BFS. 실행기는 이 함수나 hidden truth를 호출하지 않는다."""
    demand(set(truth)=={e['id'] for e in obs['edges']} and all(type(v)is bool for v in truth.values()), 'world contract')
    visited={obs['start']};queue=[obs['start']]
    for vertex in queue:
        for e in obs['edges']:
            if e['source']==vertex and truth[e['id']] and e['target'] not in visited:
                visited.add(e['target']);queue.append(e['target'])
    return obs['goal'] in visited


def identifiable(obs):
    """부호 계약의 하한/상한 도달성을 사용한 평가 지표. 선택기에 전달하지 않는다."""
    lower={e['id']:e['score'] is not None and e['score']>0 for e in obs['edges']}
    upper={e['id']:e['score'] is None or e['score']>=0 for e in obs['edges']}
    lo=reachable(obs,lower);hi=reachable(obs,upper)
    return dict(identifiable=lo==hi,value=lo if lo==hi else None)


def assess_result(b,run,world):
    if run['schema']=='hcr-selection-observation-reference-r034-v1':
        from .review_audit import assess_rollout
        r=run['reference'];a=assess_rollout(b,r,world)
        val=r['result']['value'];reason=r['result']['reason'];u=r['usage']
        return dict(value=val,reason=reason,origin='native' if val is not None else 'none',
            external_correct=a['external_correct'],initial_raw_value=b['first']['decision']['value'],
            initial_gated_value=b['first']['readout']['value'],initial_identifiability=identifiable(b['observation']),
            recovered_output=a['recovered_supported_output'],changed_raw_value=a['changed_conclusion'],
            extra_advances=u['extra_advances'],extra_kernel_ticks=u['extra_kernel_ticks'],restarts=u['restarts'],
            measurements=u['measurements'],unnecessary_queries=a['queries_on_initially_identifiable_input'],
            selection_calls=0,ranked_paths=0,path_checks=0,edge_checks=0,sidecar_proof_nodes=0,
            extra_native_proof_nodes=r['cost']['proof_readout_items']-len(b['first']['decision']['proof']['nodes']),
            new_native_readouts=len(r['candidates'])-1,first_decision_existed=True)
    result=run['result'];u=run['usage'];value=result['value'];first=b['first']
    expected=reachable(b['observation'],world)
    initial_raw=None if first is None else first['decision']['value']
    initial_gated=None if first is None else first['readout']['value']
    return dict(value=value,reason=result['reason'],origin=result['origin'],
        external_correct=None if value is None else value is expected,
        initial_raw_value=initial_raw,initial_gated_value=initial_gated,
        initial_identifiability=identifiable(b['observation']),
        recovered_output=first is not None and initial_gated is None and value is not None,
        changed_raw_value=initial_raw is not None and value is not None and initial_raw is not value,
        extra_advances=u['extra_advances'],extra_kernel_ticks=u['extra_kernel_ticks'],restarts=u['restarts'],
        measurements=0,unnecessary_queries=0,selection_calls=u['selection_calls'],ranked_paths=u['ranked_paths'],
        path_checks=u['path_checks'],edge_checks=u['edge_checks'],sidecar_proof_nodes=u['proof_nodes'],
        extra_native_proof_nodes=run['cost']['extra_native_proof_nodes'],
        new_native_readouts=len(run['candidates'])-int(first is not None),first_decision_existed=first is not None)


def verify_raw(root):
    """raw 전량 재검산. 이 함수는 raw나 기존 analysis를 쓰지 않는다."""
    from .. import session_io,codec
    from ..model import AdaptiveConfig, Feedback
    from ..circuits import AdaptiveMemory
    from ..prior_policy import read_scope
    from .review_audit import packet_states,verify_candidate
    from .prior_spec import training_world
    from .reference import assess
    root=io15.safe(root);plan=io15.load(root/'plan.json');validate_plan(plan);cp=plan['conditions']
    m=io15.load(root/'manifest.json')
    demand(set(m)=={'schema','state','independent_audit_pending','files'} and
        m['schema']=='hcr-exp15-raw-manifest-v1' and m['state']=='raw_complete'
        and m['independent_audit_pending'] is True, 'raw incomplete/manifest')
    names={'plan.json','environment.json','training.json','seed/6.json'}
    names|={'source/'+n for n in plan['source_hashes']}
    names|={'baselines/'+s['key']+'.json' for s in baseline_specs(cp)}
    names|={p+'/'+c['id']+ext for c in cells(cp) for p,ext in [('raw','.json'),('attempt_logs','.jsonl')]}
    demand(set(m['files'])==names, 'raw manifest inventory')
    actual={n for n in io15.inventory(root) if not n.startswith(('analysis/','audit_failures/'))}
    demand(actual==names|{'manifest.json'}, 'missing/extra raw evidence')
    for n,h in m['files'].items():demand(io15.checksum(io15.child(root,n))==h,'raw file checksum: '+n)
    for n,h in plan['source_hashes'].items():
        demand(hashlib.sha256(io15.read(root/'source'/n).replace(b'\r\n',b'\n')).hexdigest()==h, 'source provenance: '+n)
    cfg=AdaptiveConfig();seed=io15.load(root/'seed/6.json');_,seed_audit=packet_states(seed)
    core=seed['document']['engine'];training=io15.load(root/'training.json')
    demand(len(training)==6 and len(core['held'])==len(core['feedback'])==6 and core['pending'] is None, 'training size')
    demand(core['config']==codec.plain(cfg) and read_scope(core)=='legacy' and
        core['switches']==dict(use_circuits=True,top_down=True,allow_reexpansion=True), 'training policy')
    demand(seed['document']['events'][0]['payload']['memory_document']==AdaptiveMemory.empty(cfg).document(), 'seed must begin from empty memory')
    for i,row in enumerate(training):
        w=training_world(i);d=codec.adaptive_decision_from(row['decision']);a=assess(d,w.observation,dict(w.hidden))
        demand(row==dict(observation=codec.plain(w.observation),external_truth=dict(w.hidden),decision=row['decision'],assessment=codec.plain(a))
            and a.correct is True and core['held'][d.id]['decision']==row['decision'], 'training record provenance')
        demand(core['feedback'][d.id]==codec.plain(Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True)), 'training feedback')
    bases={};case_map=all_cases(cp)
    for spec in baseline_specs(cp):
        b=io15.load(root/'baselines'/(spec['key']+'.json'));p=b['ready'];states,_=packet_states(p);c=p['document']['engine']
        demand(b['sha256']==digest({k:v for k,v in b.items() if k!='sha256'}), 'baseline hash')
        demand(b['observation']==case_map[spec['case']]['observation']==c['pending']['observation']
            and b['judgment_prior']==spec['scope']==read_scope(c), 'baseline case/scope')
        demand(c['config']==codec.plain(cfg) and c['memory']==core['memory'] and
            c['switches']==dict(use_circuits=spec['phase']=='readout_ready',top_down=True,allow_reexpansion=True), 'baseline setup')
        demand(set(t['operation'] for t in p['document']['transitions'])<={'init','begin','advance'}, 'baseline contains intervention')
        if spec['phase']=='readout_ready':
            demand(c['pending']['ready'] and b['first'] is not None, 'ready baseline')
            verify_candidate(b['first'],p,states)
        else:
            demand(not c['pending']['ready'] and b['first'] is None and b['initial_advances']==1
                and sum(t['operation']=='advance' for t in p['document']['transitions'])==1, 'running baseline')
        bases[spec['key']]=b
    rows=[];records={};log_rows=0
    for cell in cells(cp):
        raw=io15.load(root/'raw'/f"{cell['id']}.json")
        demand(set(raw)=={'cell','result'} and raw['cell']==cell, 'cell matrix/identity')
        run=raw['result'];b=bases[cell['baseline_key']];world=case_map[cell['case']]['worlds'][cell['world']]
        demand(run['arm']==cell['arm'], 'arm binding')
        if cell['arm']=='observe_first':
            demand(run['reference']['limits']==cell['limits'], 'reference limits')
        else:
            demand(run['limits']==cell['limits'] and run['selection_limits']==cell['selection_limits'], 'condition limits')
        audit=audit_flow(b,run,world=world,provider_mode=cell['provider'])
        lines=io15.read(root/'attempt_logs'/f"{cell['id']}.jsonl").decode('utf-8').splitlines()
        log=[io15.loads(line) for line in lines];log_rows+=len(log)
        demand(log==([] if cell['arm']=='observe_first' else run['actions']), 'streamed first-attempt actions differ')
        a=assess_result(b,run,world);rows.append(dict(**cell,**a))
        records[cell['id']]=dict(raw_sha256=digest(raw),audit=audit,assessment=a)
    groups=defaultdict(Counter)
    for row in rows:
        g=groups[row['group']+'/'+row['scope']+'/'+row['arm']]
        g['rollouts']+=1;g['correct']+=row['external_correct'] is True;g['incorrect']+=row['external_correct'] is False;g['abstained']+=row['value'] is None
        for k in ('recovered_output','changed_raw_value','extra_advances','extra_kernel_ticks','restarts','measurements','unnecessary_queries',
                  'selection_calls','ranked_paths','path_checks','edge_checks','sidecar_proof_nodes','extra_native_proof_nodes','new_native_readouts'):
            g[k]+=row[k]
    initial=sum(b['ready']['document']['engine']['pending']['cost']['kernel_ticks'] for b in bases.values())
    extra=sum(r['extra_kernel_ticks'] for r in rows)
    summary=dict(schema='hcr-exp15-summary-v1',raw_manifest_sha256=io15.checksum(root/'manifest.json'),
        baselines=len(bases),ready_baselines=sum(b['first'] is not None for b in bases.values()),
        running_baselines=sum(b['first'] is None for b in bases.values()),training_inferences=6,rollouts=len(rows),
        baseline_kernel_ticks=initial,extra_kernel_ticks=extra,task_kernel_ticks=initial+extra,
        extra_session_starts=sum(r['restarts'] for r in rows),
        native_readout_computations=sum(b['first'] is not None for b in bases.values())+sum(r['new_native_readouts'] for r in rows),
        selection_calls=sum(r['selection_calls'] for r in rows),
        groups={k:dict(v) for k,v in sorted(groups.items())},rows=rows,
        boundaries=dict(simulated_toy_engine=True,not_llm_execution=True,shared_baselines_not_independent_samples=True,
            running_control_not_pooled_with_ready_baselines=True,support_is_not_external_truth=True,
            sidecar_selection_is_explicit_intervention=True,kernel_ticks_not_total_cpu_cost=True))
    audit=dict(schema='hcr-exp15-audit-v1',verified=True,raw_manifest_sha256=summary['raw_manifest_sha256'],
        baselines=len(bases),rollouts=len(rows),streamed_action_rows=log_rows,source_checked=True,
        original_native_readouts_independently_audited=True,selection_DAGs_independently_checked=True,
        controller_replayed=True,final_correctness_not_required=True)
    return summary,audit,records


def render(summary):
    lines=['# EXP-15 / R0.3.4 — 전개·재시작·prior·proof 선택 분리','',
        '모의 toy-engine 실행이다. LLM/인간 뇌/현실 센서 결과가 아니다.',
        'main은 최초 판단을 공유한다. running 대조는 최초 판단 이전이며 별도 그룹이다.',
        'support-first는 원 판단과 activation을 바꾸지 않는 명시적 증명 선택 개입이다.',
        'kernel ticks와 선택 검사/증명 노드 수는 서로 다른 비용 단위다. 합쳐 CPU 비용이라 부르지 않는다.','',
        f"기준 계산 {summary['baselines']} (readout-ready {summary['ready_baselines']}, running {summary['running_baselines']}) / rollout {summary['rollouts']}",
        f"task kernel ticks: {summary['baseline_kernel_ticks']} + {summary['extra_kernel_ticks']} = {summary['task_kernel_ticks']}",'',
        '| 그룹 / 초기 정책 / 개입 | 정답 | 오답 | 보류 | 출력 회복 | 추가 ticks | 관측 | 경로 검사 | 새 proof 노드 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for key,g in summary['groups'].items():
        lines.append(f"| {key} | {g['correct']} | {g['incorrect']} | {g['abstained']} | {g['recovered_output']} | {g['extra_kernel_ticks']} | {g['measurements']} | {g['path_checks']} | {g['sidecar_proof_nodes']} |")
    lines+=['','## 개별 조건','',
        '| ID | 입력 | 그룹 | 초기 | 개입 | world | 출력 | 외부 정확성 | 출처 | 종료 | 추가 ticks |',
        '|---|---|---|---|---|---|---|---|---|---|---:|']
    for r in summary['rows']:
        lines.append(f"| {r['id']} | {r['case']} | {r['group']} | {r['scope']} | {r['arm']} | {r['world']} | {r['value']} | {r['external_correct']} | {r['origin']} | {r['reason']} | {r['extra_kernel_ticks']} |")
    lines+=['','## 해석 경계','',
        '실험 조건의 이름은 결과를 보장하지 않는다. 오류·보류를 정답으로 보정하지 않는다.',
        '재시작은 동일 정책과 route_only 정책을 구분한다. 선택 개입은 기존 생성 경로만 검사한다.',
        'support-first가 실패한 경우도 유지한다. 관측 자체가 틀린 방향이면 여전히 오답을 확정할 수 있다.',
        '학습량은 6회 하나이며 장기 수정/rigidity 실험이 아니다.','']
    return '\n'.join(lines)


def write_analysis(root,*,check_only=False):
    summary,audit,records=verify_raw(root)
    target=io15.safe(Path(root)/'analysis')
    columns=('id','case','scope','arm','group','world','value','external_correct','origin','extra_advances',
             'extra_kernel_ticks','restarts','measurements','selection_calls','ranked_paths','path_checks','edge_checks','sidecar_proof_nodes','extra_native_proof_nodes')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=columns,lineterminator='\n');writer.writeheader()
    writer.writerows({k:r[k] for k in columns} for r in summary['rows'])
    contents={'summary.json':summary,'audit.json':audit}
    contents.update({'records/'+k+'.json':v for k,v in records.items()})
    text={'summary.ko.md':render(summary),'costs.csv':stream.getvalue()}
    if check_only:
        demand(target.is_dir(), 'no independently published analysis')
        expected=set(contents)|set(text)|{'manifest.json'}
        demand(io15.inventory(target)==expected, 'analysis file inventory')
        am=io15.load(target/'manifest.json')
        demand(am['schema']=='hcr-exp15-analysis-manifest-v1' and am['raw_manifest_sha256']==audit['raw_manifest_sha256']
               and set(am['files'])==expected-{'manifest.json'}, 'analysis manifest')
        for name,obj in contents.items():demand(io15.load(target/name)==obj,'analysis recomputation: '+name)
        for name,value in text.items():demand(io15.read(target/name).decode('utf-8')==value,'analysis render: '+name)
        for name,h in am['files'].items():demand(io15.checksum(io15.child(target,name))==h,'analysis checksum: '+name)
    else:
        target.mkdir(parents=True,exist_ok=False)
        for name,obj in contents.items():io15.put(target/name,obj)
        for name,value in text.items():io15.put_bytes(target/name,value.encode('utf-8'))
        names=io15.inventory(target)
        io15.put(target/'manifest.json',dict(schema='hcr-exp15-analysis-manifest-v1',
            raw_manifest_sha256=audit['raw_manifest_sha256'],files={n:io15.checksum(target/n) for n in sorted(names)}))
    return audit
