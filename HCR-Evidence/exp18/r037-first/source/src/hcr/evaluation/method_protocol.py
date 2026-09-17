"""EXP-11: 한 축씩 분리한 작은 M 처리 정책 비교. 외부 truth는 이 평가 계층에만 있다."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
from pathlib import Path, PurePosixPath
from .. import codec, session_io
from ..model import AdaptiveConfig, ContractError, EdgeObservation, Feedback, Mode, Observation
from ..tasks.toy_world import World, chain, diamond
from ..sessions import verify_packet
from .reference import assess, reachable
from .method_audit import verify_result
from .audit import require

PROTOCOL = 'exp11-r03-method-interleaving-v1'
ARMS = ('sequential','associative','fixed','adaptive','fixed_no_messages','adaptive_no_messages')
CASE_NAMES = ('familiar','counterfactual','longer','fork','weak_conflict','unknown','diamond')
BUDGETS = {'standard':dict(max_advances=12,max_kernel_ticks=2048,max_messages=64),
           'limited':dict(max_advances=4,max_kernel_ticks=480,max_messages=64)}


def cases():
    """수작업 개발 fixture. 큰 문제 일반화나 새로운 독립 연구 표본으로 세지 않는다."""
    fork_edges = (('s','a'),('s','b'),('a','c'),('b','d'),('c','g'),('d','g'))
    edges = tuple(EdgeObservation(f'f{i}',a,b,.92) for i,(a,b) in enumerate(fork_edges))
    fork = World(Observation('m-fork',0,'s','g',edges),tuple((e.id,True) for e in edges))
    return dict(familiar=chain('m-familiar',(True,)*3),
        counterfactual=chain('m-counterfactual',(False,True,True)),
        longer=chain('m-longer',(True,)*4),fork=fork,
        weak_conflict=chain('m-conflict',(False,True,True),(-.06,.92,.92)),
        unknown=chain('m-unknown',(True,)*3,(None,)*3),
        diamond=diamond('m-diamond',(False,True,True,True)))


def external_assessment(result, world):
    truth = dict(world.hidden)
    actual = reachable(world.observation,truth)
    value = result['result']['value']
    component = {k:codec.plain(assess(codec.adaptive_decision_from(d),world.observation,truth))
                 for k,d in result['decisions'].items()}
    return dict(expected=actual,correct=None if value is None else value==actual,
        abstained=value is None,components=component,
        unresolved_is_not_correct=True,consensus_is_not_external_evidence=True)


def summarize(rows):
    counts=defaultdict(Counter);cases_table=[];contrasts=[]
    mapping={}
    for row in rows:
        result=row['record'];a=row['assessment'];k=row['budget_name']+'/'+result['arm']
        counts[k]['records']+=1
        counts[k]['correct']+=int(a['correct'] is True)
        counts[k]['incorrect']+=int(a['correct'] is False)
        counts[k]['abstained']+=int(a['correct'] is None)
        counts[k]['conflicts']+=int(result['result']['status']=='conflict_abstention')
        audit=row['audit']
        item=dict(case=row['case'],budget=row['budget_name'],arm=result['arm'],
            value=result['result']['value'],correct=a['correct'],status=result['result']['status'],
            kernel_ticks=result['cost']['kernel_ticks'],expansions=result['cost']['expansions'],
            signals=result['cost']['signal_transmissions'],advances=result['budget']['used_advances'],
            sent=audit['messages_checked'],consumed=audit['messages_consumed'],priority_changes=audit['priority_changes'],
            component_count=len(result['methods']),completed_components=len(result['decisions']),
            total_wall_seconds=result['timing']['total_wall_seconds'],
            engine_active_seconds=result['timing']['engine_active_seconds'],
            management_seconds=result['timing']['management_seconds'],
            unused_ticks=result['budget']['unused_kernel_ticks'])
        cases_table.append(item);mapping[(row['budget_name'],row['case'],result['arm'])]=item
    for budget in BUDGETS:
        for name in CASE_NAMES:
            for left,right in (('fixed_no_messages','fixed'),('adaptive_no_messages','adaptive'),('fixed','adaptive')):
                a,b=mapping[(budget,name,left)],mapping[(budget,name,right)]
                contrasts.append(dict(budget=budget,case=name,left=left,right=right,
                    left_value=a['value'],right_value=b['value'],
                    delta_advances=b['advances']-a['advances'],delta_ticks=b['kernel_ticks']-a['kernel_ticks'],
                    delta_priority_changes=b['priority_changes']-a['priority_changes']))
    return dict(schema='hcr-exp11-summary-r03-v1',comparison_runs=len(rows),
        component_attempts=sum(len(r['record']['workers']) for r in rows),training_episodes=6,
        groups={k:dict(v) for k,v in sorted(counts.items())},cases=cases_table,contrasts=contrasts,
        meaning='동일 총상한 아래의 방법·스케줄·경로 메시지 비교. 결과 우월성을 통과 조건으로 만들지 않는다.',
        learning_rule_changed=False,prior_rule_changed=False,
        wall_time_repeats_per_cell=1,wall_time_speedup_claim=False,independent_task_count=len(CASE_NAMES),
        reservations_can_cause_conservative_abstention=True)


def render(summary):
    lines=['# EXP-11 / R0.3 — 전문화 방법·메시지·총예산 비교','',
        '개발 fixture 결과다. agreement는 외부 정답 판정이 아니며 conflict는 보류다.',
        '동일한 총 advance/tick/message 상한을 부여한다. 동일 연산량·동일 wall time을 강제하지 않는다.',
        'tick은 실행 전 최악 상한을 예약하므로, 아직 남은 tick이 있어도 시작하지 못할 수 있다.','',
        '| 예산 | 사례 | 방법 | 출력 | 정답 | 상태 | 전개 | tick | 메시지 수신 | 우선순위 변경 |',
        '|---|---|---|---|---|---|---:|---:|---:|---:|']
    for r in summary['cases']:
        lines.append(f"| {r['budget']} | {r['case']} | {r['arm']} | {r['value']} | {r['correct']} | {r['status']} | {r['advances']} | {r['kernel_ticks']} | {r['consumed']} | {r['priority_changes']} |")
    lines+=['','## 해석 경계','',
        'Sequential은 breadth-first primitive 전개이고 Associative는 기존 macro 우선·depth-first 전개다.',
        '따라서 단독 두 방법의 차이는 두 정책을 묶은 제한된 M profile 차이이지, 각 구성요소의 독립 효과는 아니다.',
        '메시지의 효과는 fixed/no_messages 및 adaptive/no_messages 대응쌍으로 읽는다.',
        '같은 evidence가 두 처리기를 통과해도 지지도가 두 배가 되지 않는다. primitive proof는 처리기별로 보존한다.',
        '추론 중 장기 memory 갱신, prior 정책 수정, 음의 예외 학습, OS thread 병렬화는 없다.',
        'controller 관리·session 복사 시간을 total_wall_seconds에 포함하고 engine active time과 분리했다.',
        '이 run은 처리기 교대 중 디스크 checkpoint를 사용하지 않는다. 개별 worker의 R0.2.1 snapshot 검산은 결과 저장 후 수행한다.',
        '표본 반복이 없는 진단이므로 wall-time 가속을 주장하지 않는다. 실패·오답·보류를 분리한다.','']
    return '\n'.join(lines)


def _write(path, value):
    codec.save(path,value)


def _digest(path):
    return hashlib.sha256(session_io.read_bytes(path)).hexdigest()


def _verify_artifacts(root):
    plan=codec.loads(session_io.read_bytes(root/'plan.json'))
    require(plan['schema']=='hcr-exp11-plan-r03-v1' and plan['protocol']==PROTOCOL,'EXP-11 plan')
    require(plan['arms']==list(ARMS) and plan['cases']==list(CASE_NAMES) and plan['budgets']==BUDGETS,'frozen condition plan')
    require(plan['first_method'] in ('sequential','associative'),'plan first method')
    require(plan['source_hashes']==session_io.source_hashes(),'EXP-11 verifier source differs')
    for name,expected in plan['source_hashes'].items():
        raw=session_io.read_bytes(root/'source'/name).replace(b'\r\n',b'\n')
        require(hashlib.sha256(raw).hexdigest()==expected,'EXP-11 frozen source hash')
    seed=codec.loads(session_io.read_bytes(root/'seed.json'));seed_audit=verify_packet(seed)
    training=codec.loads(session_io.read_bytes(root/'training.json'))
    require(len(training)==6 and len(seed['document']['engine']['held'])==6,'seed count')
    for i,row in enumerate(training):
        w=chain(f'm-train-{i}',(True,)*3,prefix=f'train{i}')
        require(row['observation']==codec.plain(w.observation) and row['truth']==dict(w.hidden),'seed input')
        d=codec.adaptive_decision_from(row['decision']);a=codec.plain(assess(d,w.observation,dict(w.hidden)))
        require(row['assessment']==a and a['correct'] is True,'seed assessment')
        require(seed['document']['engine']['held'][d.id]['decision']==row['decision'],'seed provenance')
    rows=[];audit_counts=Counter()
    worlds=cases();config=codec.plain(AdaptiveConfig())
    for b in BUDGETS:
        for name in CASE_NAMES:
            for arm in ARMS:
                row=codec.loads(session_io.read_bytes(root/'records'/b/name/(arm+'.json')))
                r=row['record']
                require(r==codec.loads(session_io.read_bytes(root/'raw'/b/name/(arm+'.json'))),'raw/derived record differs')
                require(row['case']==name and row['budget_name']==b and r['arm']==arm,'cell identity')
                require(r['adaptive_config']==config and r['method_config']==dict(BUDGETS[b],first_method=plan['first_method']), 'condition budgets differ')
                require(r['observation']==codec.plain(worlds[name].observation) and row['external_truth']==dict(worlds[name].hidden),'case input/truth')
                require(r['initial_memory']==seed['document']['engine']['memory'],'unmatched seed')
                a=verify_result(r)
                require(a==row['audit'] and row['assessment']==external_assessment(r,worlds[name]),'audit/external outcome')
                for k in ('advances_checked','messages_checked','messages_consumed','priority_changes','scalar_ticks_replayed'):
                    audit_counts[k]+=a[k]
                rows.append(row)
    require(len(rows)==84,'cell inventory')
    summary=summarize(rows)
    require(summary==codec.loads(session_io.read_bytes(root/'summary.json')),'summary reaggregation')
    require(render(summary)==session_io.read_bytes(root/'summary.ko.md').decode('utf-8'),'summary markdown')
    return dict(schema='hcr-exp11-audit-r03-v1',verified=True,comparison_runs=len(rows),
        component_attempts=summary['component_attempts'],training_episodes=6,source_checked=True,
        condition_matrix_checked=True,**dict(audit_counts),new_inferences=0,
        seed_scalar_ticks_replayed=seed_audit['scalar_ticks_replayed'],
        scheduler_replayed=True,component_proof_and_truth_rechecked=True,
        limits=['동일 session auditor를 재사용하며 OS 실행 인증이 아니다.',
                'wall time은 범위와 합계만 검사하고 실제 측정 시간을 재현하지 않는다.',
                '결합 처리기 전체의 checkpoint/resume은 이번 범위 밖이다.'])


def verify_run(root):
    root=session_io.safe_path(root)
    manifest=codec.loads(session_io.read_bytes(root/'manifest.json'))
    require(manifest['schema']=='hcr-exp11-manifest-r03-v1' and manifest['state']=='complete','incomplete EXP-11')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'manifest.json'}
    require(actual==set(manifest['files']),'missing/extra EXP-11 artifact')
    for name,expected in manifest['files'].items():
        rel=PurePosixPath(name)
        require(rel.as_posix()==name and not rel.is_absolute() and '..' not in rel.parts and ':' not in name and '\\' not in name,'unsafe artifact path')
        require(_digest(root/name)==expected,'artifact hash mismatch: '+name)
    audit=_verify_artifacts(root)
    require(audit==codec.loads(session_io.read_bytes(root/'audit.json')),'audit mismatch')
    return audit


def run_demo(out, *, first_method='associative'):
    from ..sessions import AdaptiveSession
    from ..methods import MethodEngine, MethodConfig
    MethodConfig(first_method=first_method)
    out=session_io.new_output(out);out.mkdir(parents=True,exist_ok=False)
    plan=dict(schema='hcr-exp11-plan-r03-v1',protocol=PROTOCOL,created_at_utc=datetime.now(timezone.utc).isoformat(),
        source_hashes=session_io.source_hashes(),arms=list(ARMS),cases=list(CASE_NAMES),budgets=BUDGETS,
        first_method=first_method,training_episodes=6,analysis_type='authored_development_comparison',
        hidden_truth_passed_to_method_engine=False)
    _write(out/'plan.json',plan)
    rows=[];engine=None
    try:
        for name in plan['source_hashes']:
            path=out/'source'/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((session_io.project_root()/name).read_bytes())
        seed=AdaptiveSession(session_id='r03-seed');training=[]
        for i in range(6):
            w=chain(f'm-train-{i}',(True,)*3,prefix=f'train{i}')
            seed.begin(w.observation,Mode.TRAIN);d=seed.complete();a=assess(d,w.observation,dict(w.hidden))
            training.append(dict(observation=codec.plain(w.observation),truth=dict(w.hidden),decision=codec.plain(d),assessment=codec.plain(a)))
            seed.feedback(Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True))
        _write(out/'training.json',training);seed.save(out/'seed.json')
        from ..circuits import AdaptiveMemory
        memory=AdaptiveMemory.from_document(seed.memory_document,AdaptiveConfig())
        worlds=cases()
        for bi,b in enumerate(BUDGETS):
            for ci,name in enumerate(CASE_NAMES):
                # Runtime order reverses across cases; condition labels are never passed to the engine.
                arm_order=ARMS if (bi+ci)%2==0 else tuple(reversed(ARMS))
                for arm in arm_order:
                    engine=MethodEngine(memory=memory,method_config=MethodConfig(**BUDGETS[b],first_method=first_method))
                    r=engine.infer(worlds[name].observation,arm=arm)
                    # Persist the raw completed method record before its derived audit/summary.
                    path=out/'raw'/b/name/(arm+'.json');_write(path,r)
                    row=dict(case=name,budget_name=b,external_truth=dict(worlds[name].hidden),record=r,
                             assessment=external_assessment(r,worlds[name]),audit=verify_result(r))
                    _write(out/'records'/b/name/(arm+'.json'),row);rows.append(row)
        rows.sort(key=lambda row:(list(BUDGETS).index(row['budget_name']),CASE_NAMES.index(row['case']),ARMS.index(row['record']['arm'])))
        summary=summarize(rows);_write(out/'summary.json',summary)
        (out/'summary.ko.md').write_bytes(render(summary).encode('utf-8'))
        audit=_verify_artifacts(out);_write(out/'audit.json',audit)
        files={p.relative_to(out).as_posix():_digest(p) for p in sorted(out.rglob('*')) if p.is_file()}
        _write(out/'manifest.json',dict(schema='hcr-exp11-manifest-r03-v1',state='complete',files=files))
        return dict(state='complete',verified=True,output=str(out),comparison_runs=len(rows),
                    component_attempts=summary['component_attempts'],training_episodes=6,
                    priority_changes=audit['priority_changes'],new_llm_calls=0)
    except BaseException as exc:
        _write(out/'FAILED.json',dict(state='failed',error=type(exc).__name__+': '+str(exc),completed_records=len(rows)))
        if engine is not None and engine.last_trace is not None:
            _write(out/'failed_controller.json',engine.last_trace.records)
        raise
