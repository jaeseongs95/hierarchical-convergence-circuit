"""EXP-13: 기존 판단을 보존한 근거 진단과 세 readout 정책의 대응 평가.

과제 추론 하나에 세 readout view를 생성한다. view는 신규 모델/과제 표본이 아니다.
각 원시 packet은 진단 전에 저장한다. 지원 부족을 보정하거나 숨은 참값을 주입하지 않는다.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from time import perf_counter
import csv
import hashlib
import io
from .. import codec, session_io
from ..model import AdaptiveConfig, Feedback, Mode, fingerprint
from .audit import require
from .reference import assess
from .prior_protocol import run_task
from .prior_audit import audit_packet
from .grounding_spec import ARMS, TRAINING_COUNTS, READOUT_POLICIES, SUPPORT, training_world, fixtures, cells, condition_plan
from .grounding_audit import verify_record, verify_conflicts, assess_views


def load(path):return codec.loads(session_io.read_bytes(path))
def file_hash(path):return hashlib.sha256(session_io.read_bytes(path)).hexdigest()


def inventory(root):
    out=set()
    for p in root.rglob('*'):
        session_io.safe_path(p)
        if p.is_file():out.add(p.relative_to(root).as_posix())
    return out


def expected_files(sources):
    paths={'plan.json','training.json','summary.json','summary.ko.md','audit.json','costs.csv'}
    paths|={'source/'+n for n in sources}
    paths|={f'seed/{n}.json' for n in TRAINING_COUNTS}
    for n,c,a in cells():
        tail=f"{n}/{c['name']}/{a}.json"
        paths|={'raw/'+tail,'records/'+tail}
        paths.add(f"conflicts/{n}/{c['name']}.json")
    return paths


def make_record(raw,case):
    from ..grounding import diagnose,apply_readout
    before=fingerprint(raw);obs=codec.observation_from(raw['observation']);d=codec.adaptive_decision_from(raw['decision'])
    t=perf_counter();diagnostic=diagnose(obs,d,raw['packet']['document']['events']);duration=perf_counter()-t
    readouts={};readout_times={}
    for p in READOUT_POLICIES:
        t=perf_counter();readouts[p]=apply_readout(d,diagnostic,p);readout_times[p]=perf_counter()-t
    require(fingerprint(raw)==before,'diagnostic/readout mutated original task')
    return dict(schema='hcr-exp13-record-v1',source_task_sha256=before,diagnostic=diagnostic,readouts=readouts,
        assessment=assess_views(raw,case,diagnostic,readouts),
        timing=dict(diagnostic_seconds=duration,readout_seconds=readout_times))


def conflict_groups(named):
    return {'legacy_route':{k:named[k] for k in ('legacy','route_only')},
            'route_graph':{k:named[k] for k in ('route_only','graph_only')},'all':named}


def make_conflicts(named):
    from ..grounding import compare_diagnostics
    return {k:compare_diagnostics(v) for k,v in conflict_groups(named).items()}


def summarize(rows,conflicts):
    counts=defaultdict(Counter);table=[]
    for raw,r in rows:
        key=(raw['training_count'],raw['case'],raw['arm']);dg=r['diagnostic'];d=raw['decision']
        views={p:v['value'] for p,v in r['readouts'].items()}
        table.append(dict(training_count=key[0],case=key[1],family=raw['family'],arm=key[2],
            original=d['value'],support=dg['evidence_support_sufficient'],support_gaps=dg['support_gap_edges'],
            dependency_gate=views['dependency_gate'],blanket_unknown_gate=views['blanket_unknown_gate'],
            original_status=d['convergence']['status'],original_primitive_D=d['proof']['primitive_depth'],
            kernel_ticks=d['cost']['kernel_ticks'],expansions=d['cost']['expansions'],circuit_reuses=d['cost']['circuit_reuses'],
            assumed_edges=d['proof']['assumed_edges'],unknown_outside_proof=dg['unknown_outside_selected_proof'],
            identifiable_under_sign_contract=r['assessment']['compatible_worlds']['identifiable_under_sign_contract']))
        for p,view in r['assessment']['policies'].items():
            c=counts[raw['arm']+'/'+p];c['policy_views']+=1
            c['answered']+=int(view['value'] is not None);c['abstained']+=int(view['value'] is None)
            c['unsupported_commitments']+=int(view['unsupported_commitment'])
            c['unidentified_commitments']+=int(view['unidentified_commitment'])
            c['withheld_identifiable_cases']+=int(view['withheld_identifiable_case'])
            for v in view['external_correct'].values():
                c['world_evaluations']+=1;c['external_correct']+=int(v is True)
                c['external_incorrect']+=int(v is False);c['external_abstained']+=int(v is None)
    conflict_counts=defaultdict(Counter)
    for _,_,cs in conflicts:
        for k,v in cs.items():conflict_counts[k][v['status']]+=1
    return dict(schema='hcr-exp13-summary-r032-v1',task_inferences=len(rows),training_inferences=9,
        readout_policy_evaluations=len(rows)*len(READOUT_POLICIES),paired_input_memory_cells=len(conflicts),
        diagnostic_only_preserved=all(r['readouts']['diagnostic_only']['value'] is raw['decision']['value'] for raw,r in rows),
        no_output_flips=all(v['value'] is None or v['value'] is raw['decision']['value'] for raw,r in rows for v in r['readouts'].values()),
        groups={k:dict(v) for k,v in sorted(counts.items())},conflicts={k:dict(v) for k,v in sorted(conflict_counts.items())},cases=table,
        boundaries=dict(policy_views_are_not_new_inferences=True,external_worlds_not_independent_samples=True,
            correction_or_new_learning=False,truth_accuracy_not_implied_by_support=True,
            diagnostic_cost_separate_from_engine=True,measurement_requests_executed=0,
            production_gate_only_abstains=True,whole_controller_resume_not_implemented=True))


def render(s):
    lines=['# EXP-13 / R0.3.2 — 근거 출처·결측 dependency·충돌 진단','',
        '원래 판단/가정/proof를 보존한 진단이다. 두 gate는 명시적인 사후 readout 개입이며 참·거짓을 뒤집지 않는다.',
        'directional-support는 score 방향과의 일치 계약이지 참값·보정확률·정답의 보증이 아니다.',
        f"과제 추론 {s['task_inferences']}회 / 학습 {s['training_inferences']}회 / readout 평가 {s['readout_policy_evaluations']}건.",
        'readout 평가와 hidden-world 채점 수를 과제 추론 수에 더하지 않는다.','',
        '| 학습 | 사례 | 엔진 | 원 판단 | 선택 proof 지지 | dependency gate | blanket gate | 지지 부족 edge |',
        '|---:|---|---|---|---|---|---|---|']
    for r in s['cases']:
        lines.append(f"| {r['training_count']} | {r['case']} | {r['arm']} | {r['original']} | {r['support']} | {r['dependency_gate']} | {r['blanket_unknown_gate']} | {','.join(r['support_gaps'])} |")
    lines+=['','## 정책별 집계','',
        '| 엔진/정책 | 출력 | 보류 | 근거 부족 확정 | 식별 불가 확정 | 식별 가능한 입력의 보류 |',
        '|---|---:|---:|---:|---:|---:|']
    for k,v in s['groups'].items():lines.append(f"| {k} | {v['answered']} | {v['abstained']} | {v['unsupported_commitments']} | {v['unidentified_commitments']} | {v['withheld_identifiable_cases']} |")
    lines+=['','## 해석 경계','',
        '- score가 잘못된 관측이면 지지 계약을 만족해도 오답이다. misleading_direction은 이 구분의 대조다.',
        '- 기존 proof에 쓰이지 않은 결측과 실제 결론에 필요한 결측을 구분한다. 새 proof를 자동 생성하지 않는다.',
        '- 진단은 선택된 proof 중심이다. 다른 지지 가능한 경로가 있어도 그 경로로 proof를 자동 교체하지 않는다.',
        '- compatible_worlds는 평가기 전용이며 sign 계약의 식별 가능성을 판정한다. engine/gate에 공급하지 않는다.',
        '- agreement_with_support_gap은 합의도 근거 부족을 해결하지 못한다는 뜻이다. 다수결 정답 판정이 아니다.',
        '- suggestion은 제안 기록이다. 추가 관측·재시도·학습은 실행하지 않았다.',
        '- engine 비용은 raw에 그대로 남으며 diagnostic/readout 처리 시간은 costs.csv에 별도 기록한다.',
        '- 과거 EXP-12 결과를 갱신하지 않으며 새 run을 해당 연구 증거와 혼합하지 않는다.','']
    return '\n'.join(lines)


def cost_rows(rows):
    out=[]
    for raw,r in rows:
        d=raw['decision'];out.append(dict(training_count=raw['training_count'],case=raw['case'],arm=raw['arm'],
            expansions=d['cost']['expansions'],kernel_ticks=d['cost']['kernel_ticks'],signal_transmissions=d['cost']['signal_transmissions'],
            binding_operations=d['cost']['binding_operations'],engine_active_seconds=d['cost']['wall_seconds'],
            task_total_seconds=raw['timing']['total_wall_seconds'],packet_seconds=raw['timing']['packet_seconds'],diagnostic_seconds=r['timing']['diagnostic_seconds'],
            **{p+'_seconds':r['timing']['readout_seconds'][p] for p in READOUT_POLICIES}))
    return out


def verify_data(root):
    plan=load(root/'plan.json');sources=session_io.source_hashes()
    require(set(plan)=={'schema','conditions','source_hashes','created_at_utc'} and plan['schema']=='hcr-exp13-plan-v1'
        and plan['conditions']==condition_plan() and plan['source_hashes']==sources,'frozen EXP-13 plan/source')
    for n,digest in sources.items():require(hashlib.sha256(session_io.read_bytes(root/'source'/n).replace(b'\r\n',b'\n')).hexdigest()==digest,'source hash')
    from ..circuits import AdaptiveMemory
    cfg=AdaptiveConfig();training=load(root/'training.json');require(len(training)==9,'training count')
    memories={};totals=Counter()
    for n in TRAINING_COUNTS:
        seed=load(root/'seed'/f'{n}.json');audit=audit_packet(seed);core=seed['document']['engine']
        require(core['config']==codec.plain(cfg) and 'prior_policy' not in core
            and core['switches']==dict(use_circuits=True,top_down=True,allow_reexpansion=True)
            and len(core['held'])==len(core['feedback'])==n,'seed configuration')
        require(seed['document']['events'][0]['payload']['memory_document']==AdaptiveMemory.empty(cfg).document(),'empty seed')
        for i,row in enumerate(training[:n]):
            w=training_world(i);d=codec.adaptive_decision_from(row['decision']);a=assess(d,w.observation,dict(w.hidden))
            require(row==dict(observation=codec.plain(w.observation),external_truth=dict(w.hidden),decision=row['decision'],assessment=codec.plain(a))
                    and a.correct is True,'training external evaluation')
            require(core['held'][d.id]['decision']==row['decision'] and core['held'][d.id]['observation']==row['observation'],'training source')
            require(core['feedback'][d.id]==codec.plain(Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True)),'training feedback')
        memories[n]=core['memory']
        if n==9:totals['training_scalar_ticks_replayed']=audit['scalar_ticks_replayed']
    rows=[];bycell=defaultdict(dict)
    for n,c,a in cells():
        tail=f"{n}/{c['name']}/{a}.json";raw=load(root/'raw'/tail);r=load(root/'records'/tail)
        report=verify_record(raw,r,c,n,a,memories[n],cfg);rows.append((raw,r));bycell[(n,c['name'])][a]=r['diagnostic']
        totals['scalar_ticks_replayed']+=report['task']['scalar_ticks_replayed'];totals['graph_steps_checked']+=report['task']['graph_steps_checked']
        totals['world_evaluations_per_policy']+=len(c['worlds']);totals['assumptions_checked']+=len(r['diagnostic']['assumptions'])
    conflicts=[]
    for (n,c),named in sorted(bycell.items()):
        require(set(named)==set(ARMS),'missing engine arm')
        cs=load(root/'conflicts'/str(n)/(c+'.json'));require(set(cs)==set(conflict_groups(named)),'conflict groups')
        for k,v in conflict_groups(named).items():verify_conflicts(v,cs[k])
        conflicts.append((n,c,cs))
    summary=summarize(rows,conflicts)
    require(load(root/'summary.json')==summary,'summary reaggregation')
    require(session_io.read_bytes(root/'summary.ko.md').decode('utf-8')==render(summary),'rendered summary')
    actual=list(csv.DictReader(io.StringIO(session_io.read_bytes(root/'costs.csv').decode('utf-8'))))
    require(actual==[{k:str(v) for k,v in r.items()} for r in cost_rows(rows)],'CSV reaggregation')
    return dict(schema='hcr-exp13-audit-r032-v1',verified=True,source_checked=True,task_inferences=len(rows),training_inferences=9,
        readout_policy_evaluations=len(rows)*3,paired_input_memory_cells=len(conflicts),
        original_decisions_preserved=summary['diagnostic_only_preserved'],no_value_flips=summary['no_output_flips'],
        **dict(totals),new_inferences=0,diagnostic_rules_independently_reimplemented=True,
        existing_session_and_primitive_auditors_reused=True,
        limitations=['기록 일관성 검산이며 OS 실행 인증이 아니다.','score 방향의 지지는 외부 정답을 보증하지 않는다.',
                     '시간은 비음수/연결 범위만 검사한다.','보류 개입은 별도 readout 계층이며 내부 수렴을 수정하지 않는다.'])


def verify_run(root):
    root=session_io.safe_path(root);manifest=load(root/'manifest.json');expected=expected_files(session_io.source_hashes())
    require(manifest.get('schema')=='hcr-exp13-manifest-v1' and manifest.get('state')=='complete','incomplete EXP-13')
    require(set(manifest['files'])==expected and inventory(root)==expected|{'manifest.json'},'missing/extra run files')
    for n,digest in manifest['files'].items():
        p=PurePosixPath(n);require(not p.is_absolute() and '..' not in p.parts and '\\' not in n,'unsafe manifest path')
        require(file_hash(root/n)==digest,'run hash '+n)
    audit=verify_data(root);require(load(root/'audit.json')==audit,'stored audit mismatch');return audit


def run_demo(out):
    from ..sessions import AdaptiveSession
    from ..circuits import AdaptiveMemory
    out=session_io.new_output(Path(out));out.mkdir(parents=True,exist_ok=False)
    plan=dict(schema='hcr-exp13-plan-v1',conditions=condition_plan(),source_hashes=session_io.source_hashes(),created_at_utc=datetime.now(timezone.utc).isoformat())
    codec.save(out/'plan.json',plan);stage='source';completed=0
    try:
        for name in plan['source_hashes']:
            p=out/'source'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((session_io.project_root()/name).read_bytes())
        stage='training';cfg=AdaptiveConfig();seed=AdaptiveSession(cfg,session_id='grounding-training');training=[];memories={}
        for i in range(9):
            w=training_world(i);seed.begin(w.observation,Mode.TRAIN);d=seed.complete();a=assess(d,w.observation,dict(w.hidden))
            training.append(dict(observation=codec.plain(w.observation),external_truth=dict(w.hidden),decision=codec.plain(d),assessment=codec.plain(a)))
            seed.feedback(Feedback('f-'+d.id,d.id,w.observation.digest,a.correct,a.proof_valid and a.assumption_correct is True))
            if i+1 in TRAINING_COUNTS:
                codec.save(out/'seed'/f'{i+1}.json',seed.packet());memories[i+1]=seed.memory_document
        codec.save(out/'training.json',training)
        rows=[];named=defaultdict(dict);stage='task'
        for n,c,a in cells():
            raw=run_task(cfg,AdaptiveMemory.from_document(memories[n],cfg),n,c,a)
            tail=f"{n}/{c['name']}/{a}.json";codec.save(out/'raw'/tail,raw);completed+=1
            stage='diagnostic';r=make_record(raw,c);codec.save(out/'records'/tail,r)
            verify_record(raw,r,c,n,a,memories[n],cfg);rows.append((raw,r));named[(n,c['name'])][a]=r['diagnostic'];stage='task'
        stage='conflict';conflicts=[]
        for (n,c),ds in sorted(named.items()):
            cs=make_conflicts(ds);codec.save(out/'conflicts'/str(n)/(c+'.json'),cs);conflicts.append((n,c,cs))
        stage='summary';summary=summarize(rows,conflicts);codec.save(out/'summary.json',summary)
        (out/'summary.ko.md').write_bytes(render(summary).encode('utf-8'))
        costs=cost_rows(rows)
        with (out/'costs.csv').open('x',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(costs[0]));writer.writeheader();writer.writerows(costs)
        stage='audit';audit=verify_data(out);codec.save(out/'audit.json',audit)
        require(inventory(out)==expected_files(plan['source_hashes']),'output inventory')
        codec.save(out/'manifest.json',dict(schema='hcr-exp13-manifest-v1',state='complete',files={n:file_hash(out/n) for n in sorted(inventory(out))}))
        verify_run(out)
        return dict(state='complete',directory=str(out),**{k:v for k,v in audit.items() if k!='new_inferences'},new_task_inferences=completed,audit_new_inferences=0)
    except BaseException as error:
        if stage=='training' and 'seed' in locals():codec.save(out/'partial_training.json',dict(packet=seed.packet(),rows=training))
        codec.save(out/'FAILED.json',dict(state='failed',stage=stage,task_inferences_recorded=completed,error=type(error).__name__+': '+str(error),original_failures_preserved=True))
        raise
