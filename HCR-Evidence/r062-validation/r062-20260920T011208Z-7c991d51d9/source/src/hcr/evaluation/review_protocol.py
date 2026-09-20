"""EXP-14 실행/검산. shared baseline을 한 번만 생성하고 각 개입을 별도 기록한다."""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
import csv
import hashlib
import io
from .. import codec,session_io
from ..model import AdaptiveConfig,Feedback,Mode,fingerprint
from ..circuits import AdaptiveMemory
from .review_spec import condition_plan,baselines,cells,provider_for
from .review_audit import audit_rollout,assess_rollout,packet_states,verify_candidate
from .prior_spec import training_world
from .reference import assess
from .audit import require


def load(p):return codec.loads(session_io.read_bytes(p))
def digest(p):return hashlib.sha256(session_io.read_bytes(p)).hexdigest()
def base_key(n,c,s):return f"{n}/{c if isinstance(c,str) else c['name']}/{s}.json"


def make_plan(training_counts=(6,)):
    return dict(schema='hcr-exp14-plan-v1',conditions=condition_plan(training_counts),
        source_hashes=session_io.source_hashes(),created_at_utc=datetime.now(timezone.utc).isoformat())


def validate_plan(plan):
    require(set(plan)=={'schema','conditions','source_hashes','created_at_utc'} and plan['schema']=='hcr-exp14-plan-v1','plan schema')
    require(plan['conditions']==condition_plan(plan['conditions']['training_counts']) and plan['source_hashes']==session_io.source_hashes(),'frozen conditions/source mismatch')


def expected_files(plan):
    cp=plan['conditions']
    names={'plan.json','training.json','summary.json','summary.ko.md','costs.csv','audit.json'}
    names|={'source/'+s for s in plan['source_hashes']}
    names|={f'seed/{n}.json' for n in cp['training_counts']}
    names|={'baselines/'+base_key(n,c,s) for n,c,s in baselines(cp)}
    for cell in cells(cp):names|={f"raw/{cell['id']}.json",f"records/{cell['id']}.json"}
    return names


def inventory(root):
    names=set()
    for p in root.rglob('*'):
        session_io.safe_path(p)
        if p.is_file():names.add(p.relative_to(root).as_posix())
    return names


def summarize(plan,base_map,rows):
    groups=defaultdict(Counter);table=[]
    for cell,r,a in rows:
        key=cell['group']+'/'+cell['scope']+'/'+cell['policy'];g=groups[key]
        g['rollouts']+=1;g['correct']+=int(a['external_correct'] is True)
        g['incorrect']+=int(a['external_correct'] is False);g['abstained']+=int(a['external_correct'] is None)
        g['recovered_output']+=int(a['recovered_supported_output']);g['unsupported_commitments']+=int(a['unsupported_commitment'])
        for name in ('extra_advances','extra_kernel_ticks','measurements','restarts'):g[name]+=r['usage'][name]
        g['queries_on_initially_identifiable_input']+=a['queries_on_initially_identifiable_input']
        table.append(dict(**cell,value=r['result']['value'],reason=r['result']['reason'],correct=a['external_correct'],
            initial_gated_value=a['initial_gated_value'],initial_raw_value=r['candidates'][0]['decision']['value'],
            new_information=a['new_information'],**r['usage'],candidate_readouts=len(r['candidates']),
            proof_items=r['cost']['proof_readout_items'],
            continuation_operations=sum(e['event']=='review_action' and e['payload']['action']=='continue_dependency' for e in r['controller']),
            initial_ticks=r['cost']['initial_kernel_ticks'],pathway_ticks=r['cost']['engine']['kernel_ticks'],
            changed_conclusion=a['changed_conclusion']))
    initial_ticks=sum(b['ready']['document']['engine']['pending']['cost']['kernel_ticks'] for b in base_map.values())
    extra_ticks=sum(r['usage']['extra_kernel_ticks'] for _,r,_ in rows)
    starts=sum(r['usage']['restarts'] for _,r,_ in rows)
    return dict(schema='hcr-exp14-summary-v1',baseline_inferences=len(base_map),review_rollouts=len(rows),
        training_inferences=max(plan['conditions']['training_counts']),additional_session_starts=starts,
        total_task_starts=len(base_map)+starts,baseline_kernel_ticks=initial_ticks,additional_kernel_ticks=extra_ticks,
        task_kernel_ticks=initial_ticks+extra_ticks,
        candidate_readout_computations=len(base_map)+sum(len(r['candidates'])-1 for _,r,_ in rows),
        measurement_requests=sum(r['usage']['measurements'] for _,r,_ in rows),
        groups={k:dict(v) for k,v in sorted(groups.items())},cases=table,
        boundaries=dict(shared_baselines_not_recounted=True,rollouts_not_independent_tasks=True,
            simulated_sensor=True,no_learning_during_review=True,extra_work_is_not_free=True,
            failed_hypotheses_not_runtime_failures=True,whole_controller_checkpoint=False,
            sign_support_not_truth=True,wall_time_speedup_claim=False))


def render(s):
    lines=['# EXP-14 / R0.3.3 — 근거 기반 재검토·추가 전개·선택적 관측','',
        '관측은 모의 환경의 요청별 score 응답이다. 실제 센서·LLM 실험이 아니다.',
        '최초 판단을 공유하고 분기하므로 rollout 수를 독립 과제 수/추론 수로 합산하지 않는다.',
        'expand_only는 기존 prior/proof 선택을 그대로 둔다. 추가 경로를 만들고도 실패할 수 있다.',
        'route_review는 명시적 route_only 전체 재계산이며 그 비용을 전부 합산한다.',
        'supported는 방향성 지지 계약이며 외부 정답을 보증하지 않는다.','',
        f"기준 추론 {s['baseline_inferences']} / 추가 session 시작 {s['additional_session_starts']} / 학습 {s['training_inferences']} / rollout {s['review_rollouts']}",
        f"실제 task tick: 기준 {s['baseline_kernel_ticks']} + 추가 {s['additional_kernel_ticks']} = {s['task_kernel_ticks']}",'',
        '| 그룹 / 초기 정책 / 개입 | 정답 | 오답 | 보류 | 출력 회복 | 추가 advance | 추가 tick | 관측 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for k,g in s['groups'].items():lines.append(f"| {k} | {g['correct']} | {g['incorrect']} | {g['abstained']} | {g['recovered_output']} | {g['extra_advances']} | {g['extra_kernel_ticks']} | {g['measurements']} |")
    lines+=['','## 개별 조건','',
        '| ID | 학습 | 사례 | 초기 | 개입 | 환경/world | 출력 | 정답 | 종료 이유 | 추가 advance/tick | 관측 |',
        '|---|---:|---|---|---|---|---|---|---|---|---:|']
    for r in s['cases']:lines.append(f"| {r['id']} | {r['training']} | {r['case']} | {r['scope']} | {r['policy']} | {r['group']} / {r['world']} | {r['value']} | {r['correct']} | {r['reason']} | {r['extra_advances']}/{r['extra_kernel_ticks']} | {r['measurements']} |")
    lines+=['','## 판정 경계','',
        '후속 판단은 실제 finish branch와 새 candidate ID로 연결된다. engine-local ID는 같은 계속 계산 안에서 유지된다.',
        '추가 전개는 ready 상태의 기존 frontier를 이어간다. 관측/정책 변경은 새 session이며 기존 비용은 유지한다.',
        '예산·정보 미변경·관측 불가 때문에 보류하면 그 상태를 그대로 보존한다. 자동 retry는 없다.',
        '전역 최적 관측 선택, 지지되는 다른 proof의 자동 교체, 장기 학습/entanglement/consolidation은 이 실험의 범위가 아니다.','']
    return '\n'.join(lines)


def costs(rows):
    return [dict(id=c['id'],group=c['group'],scope=c['scope'],policy=c['policy'],case=c['case'],world=c['world'],
        initial_kernel_ticks=r['cost']['initial_kernel_ticks'],extra_kernel_ticks=r['usage']['extra_kernel_ticks'],
        pathway_kernel_ticks=r['cost']['engine']['kernel_ticks'],extra_advances=r['usage']['extra_advances'],measurements=r['usage']['measurements'],
        proof_readout_items=r['cost']['proof_readout_items'],baseline_seconds=r['timing']['baseline_seconds'],
        validation_seconds=r['timing']['validation_seconds'],review_wall_seconds=r['timing']['review_wall_seconds'],
        candidate_capture_seconds=r['timing']['candidate_capture_seconds']) for c,r,a in rows]


def audit_data(root):
    plan=load(root/'plan.json');validate_plan(plan);cp=plan['conditions'];cfg=AdaptiveConfig()
    for n,h in plan['source_hashes'].items():require(hashlib.sha256(session_io.read_bytes(root/'source'/n).replace(b'\r\n',b'\n')).hexdigest()==h,'frozen source '+n)
    training=load(root/'training.json');require(len(training)==max(cp['training_counts']),'training cardinality')
    memories={}
    for n in cp['training_counts']:
        seed=load(root/'seed'/f'{n}.json');_,au=packet_states(seed);core=seed['document']['engine']
        require(seed['document']['events'][0]['payload']['memory_document']==AdaptiveMemory.empty(cfg).document()
            and core['config']==codec.plain(cfg) and len(core['held'])==len(core['feedback'])==n,'training seed')
        require(read_scope_of(core)=='legacy' and core['switches']==dict(use_circuits=True,top_down=True,allow_reexpansion=True),'training flags')
        for i,row in enumerate(training[:n]):
            w=training_world(i);d=codec.adaptive_decision_from(row['decision']);a=assess(d,w.observation,dict(w.hidden))
            require(row==dict(observation=codec.plain(w.observation),external_truth=dict(w.hidden),decision=row['decision'],assessment=codec.plain(a))
                and a.correct is True and core['held'][d.id]['decision']==row['decision'],'training raw evidence')
            require(core['feedback'][d.id]==codec.plain(Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True)),'seed feedback')
        memories[n]=core['memory']
    base_map={}
    for n,c,scope in baselines(cp):
        key=base_key(n,c,scope);b=load(root/'baselines'/key);sm,au=packet_states(b['ready'])
        require(b['sha256']==fingerprint({k:v for k,v in b.items() if k!='sha256'}) and b['observation']==c['observation'] and b['judgment_prior']==scope,'baseline cell')
        core=b['ready']['document']['engine']
        require(core['memory']==memories[n] and core['config']==codec.plain(cfg) and read_scope_of(core)==scope,'initial frozen memory/policy')
        require(set(t['operation'] for t in b['ready']['document']['transitions'])<={'init','begin','advance'},'base has review intervention')
        verify_candidate(b['first'],b['ready'],sm);base_map[key]=b
    rows=[];total=Counter();case_map={c['name']:c for c in cp['cases']}
    for cell in cells(cp):
        name=cell['id'];raw=load(root/'raw'/f'{name}.json');record=load(root/'records'/f'{name}.json')
        require(raw['cell']==cell and set(raw)=={'cell','result'},'run identity/condition matrix')
        r=raw['result'];b=base_map[base_key(cell['training'],cell['case'],cell['scope'])];world=case_map[cell['case']]['worlds'][cell['world']]
        require(r['policy']==cell['policy'] and r['limits']==cell['limits'],'intervention bounds')
        au=audit_rollout(b,r,world=world,provider_mode=cell['provider']);a=assess_rollout(b,r,world)
        require(record==dict(source_sha256=fingerprint(raw),audit=au,assessment=a),'record/assessment differs')
        for k in ('extra_advances','extra_kernel_ticks','requests_checked','candidate_readouts_checked','new_session_starts','continuation_operations'):total[k]+=au[k]
        rows.append((cell,r,a))
    s=summarize(plan,base_map,rows)
    require(load(root/'summary.json')==s and session_io.read_bytes(root/'summary.ko.md').decode('utf-8')==render(s),'summary recomputation')
    csvrows=list(csv.DictReader(io.StringIO(session_io.read_bytes(root/'costs.csv').decode('utf-8'))))
    require(csvrows==[{k:str(v) for k,v in row.items()} for row in costs(rows)],'cost CSV')
    return dict(schema='hcr-exp14-audit-v1',verified=True,baseline_inferences=len(base_map),review_rollouts=len(rows),
        training_inferences=max(cp['training_counts']),total_task_starts=s['total_task_starts'],
        **dict(total),new_inferences=0,original_decisions_preserved=True,controller_replayed=True,
        state_and_primitive_auditors_reused=True,source_checked=True,
        limitations=['모의 관측 provider다. 실제 센서 정확도/LLM 성능을 검증하지 않는다.',
        '동일 baseline을 공유하는 rollout은 독립 표본이 아니다.',
        'wall time은 범위/참조만 검사한다. 실제 CPU 시간을 재현하지 않는다.',
        '추가 전개나 관측 뒤에도 선택 proof 지지가 부족하면 실패/보류를 유지한다.'])


def read_scope_of(core):
    from ..prior_policy import read_scope
    return read_scope(core)


def verify_run(root):
    root=session_io.safe_path(root);plan=load(root/'plan.json');validate_plan(plan)
    m=load(root/'manifest.json');expected=expected_files(plan)
    require(m.get('schema')=='hcr-exp14-manifest-v1' and m.get('state')=='complete','incomplete EXP-14')
    require(set(m['files'])==expected and inventory(root)==expected|{'manifest.json'},'missing/extra result files')
    for n,h in m['files'].items():
        p=PurePosixPath(n);require(not p.is_absolute() and '..' not in p.parts and '\\' not in n,'unsafe manifest path')
        require(digest(root/n)==h,'result hash '+n)
    a=audit_data(root);require(load(root/'audit.json')==a,'stored audit differs');return a


def run_demo(out,training_counts=(6,),plan=None):
    from ..sessions import AdaptiveSession
    from ..review import prepare_baseline,ReviewFlow,ReviewLimits
    plan=plan or make_plan(training_counts);validate_plan(plan);cp=plan['conditions']
    out=session_io.new_output(Path(out));out.mkdir(parents=True,exist_ok=False)
    codec.save(out/'plan.json',plan);stage='source';completed=0;flow=None
    try:
        for n in plan['source_hashes']:
            p=out/'source'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((session_io.project_root()/n).read_bytes())
        stage='training';cfg=AdaptiveConfig();s=AdaptiveSession(cfg,session_id='review-training');training=[];memories={}
        for i in range(max(cp['training_counts'])):
            w=training_world(i);s.begin(w.observation,Mode.TRAIN);d=s.complete();a=assess(d,w.observation,dict(w.hidden))
            training.append(dict(observation=codec.plain(w.observation),external_truth=dict(w.hidden),decision=codec.plain(d),assessment=codec.plain(a)))
            s.feedback(Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True))
            if i+1 in cp['training_counts']:
                codec.save(out/'seed'/f'{i+1}.json',s.packet());memories[i+1]=s.memory_document
        codec.save(out/'training.json',training);stage='baseline';base_map={}
        for n,c,scope in baselines(cp):
            b=prepare_baseline(codec.observation_from(c['observation']),cfg,AdaptiveMemory.from_document(memories[n],cfg),judgment_prior=scope)
            key=base_key(n,c,scope);codec.save(out/'baselines'/key,b);base_map[key]=b
        rows=[];case_map={c['name']:c for c in cp['cases']}
        for cell in cells(cp):
            stage='rollout';name=cell['id'];c=case_map[cell['case']];b=base_map[base_key(cell['training'],cell['case'],cell['scope'])]
            flow=ReviewFlow(b,cell['policy'],ReviewLimits(**cell['limits']))
            world=c['worlds'][cell['world']];r=flow.run(provider_for(c['observation'],world,cell['provider']))
            raw=dict(cell=cell,result=r);codec.save(out/'raw'/f'{name}.json',raw);completed+=1
            stage='record_audit';a=audit_rollout(b,r,world=world,provider_mode=cell['provider']);assessment=assess_rollout(b,r,world)
            codec.save(out/'records'/f'{name}.json',dict(source_sha256=fingerprint(raw),audit=a,assessment=assessment))
            rows.append((cell,r,assessment))
        stage='summary';summary=summarize(plan,base_map,rows);codec.save(out/'summary.json',summary)
        (out/'summary.ko.md').write_bytes(render(summary).encode('utf-8'))
        cs=costs(rows)
        with (out/'costs.csv').open('x',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(cs[0]));writer.writeheader();writer.writerows(cs)
        stage='audit';audit=audit_data(out);codec.save(out/'audit.json',audit)
        require(inventory(out)==expected_files(plan),'EXP-14 output inventory')
        codec.save(out/'manifest.json',dict(schema='hcr-exp14-manifest-v1',state='complete',files={n:digest(out/n) for n in sorted(inventory(out))}))
        return dict(state='complete',directory=str(out),**audit)
    except BaseException as exc:
        if flow is not None:codec.save(out/'partial_controller.json',flow.trace.records)
        if stage=='training':codec.save(out/'partial_training.json',dict(packet=s.packet(),rows=training))
        codec.save(out/'FAILED.json',dict(state='failed',stage=stage,rollouts_recorded=completed,error=type(exc).__name__+': '+str(exc),automatic_retry=False))
        raise
