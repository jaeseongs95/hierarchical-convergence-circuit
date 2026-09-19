"""EXP-00: 하나의 엔진에서 학습→회로화→전이→오수렴→재확장을 확인한다.

명시적인 개발 fixture다. 수치가 좋아지도록 선택한 후의 독립 연구 표본이나
생물학적 가설 검증으로 보고하지 않는다. 환경 truth는 이 실행기/평가기에만 있다.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import sys
import platform
from time import perf_counter
from ..model import Config, Mode, Feedback, ContractError
from ..runtime import Engine
from ..circuits import Memory
from ..trace import Trace
from ..tasks.toy_world import chain, diamond, World
from .. import codec
from .reference import assess


ARMS = {
    'full': dict(use_circuits=True, top_down=True, allow_reexpansion=True),
    'graph_only': dict(use_circuits=False, top_down=True, allow_reexpansion=True),
    'no_top_down': dict(use_circuits=True, top_down=False, allow_reexpansion=True),
    'no_reexpansion': dict(use_circuits=True, top_down=True, allow_reexpansion=False),
}


def source_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parents[3]
    paths = list((root/'src/hcr').rglob('*.py'))
    paths += [p for p in (root/'hcr.py', root/'configs/r01.toml') if p.is_file()]
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths) if '__pycache__' not in p.parts}


def worlds() -> list[tuple[str, World]]:
    # 시나리오 이름은 평가 metadata다. infer에는 Observation 하나만 전달한다.
    permuted = chain('eval-008', (True, True), prefix='새로운-대상')
    permuted = replace(permuted, observation=replace(permuted.observation,
                        edges=tuple(reversed(permuted.observation.edges))))
    return [
        ('transfer_open', chain('eval-001', prefix='unseen-open')),
        ('counterfactual_closed', chain('eval-002', (False, True), prefix='unseen-closed')),
        ('ambiguous_zero', chain('eval-003', (True, True), (0.0, 0.0), prefix='ambiguous')),
        ('weak_evidence_conflict', chain('eval-004', (False, True), (-0.06, 0.92), prefix='conflicting')),
        ('novel_chain', chain('eval-005', (True, True, True), prefix='longer')),
        ('novel_branch', diamond('eval-006', prefix='branch')),
        ('novel_branch_closed', diamond('eval-007', (False, False, False, False), prefix='blocked')),
        ('permuted_transfer', permuted),
    ]


def count(rows: list[dict]) -> dict:
    answers = [r['assessment']['correct'] for r in rows]
    return {'attempts': len(rows), 'correct': sum(x is True for x in answers),
            'incorrect': sum(x is False for x in answers), 'unresolved': sum(x is None for x in answers),
            'strict_correct': sum(r['assessment']['correct'] is True and r['assessment']['proof_valid']
                                  and r['assessment']['assumption_correct'] is True for r in rows),
            'proof_valid_under_assumptions': sum(r['assessment']['proof_valid'] for r in rows),
            'wrong_stable': sum(r['assessment']['wrong_stable'] for r in rows),
            'circuit_reuse': sum(r['decision']['method']=='circuit_reuse' for r in rows)}


def summarize(records: list[dict], events: list[dict], snapshots: list[dict]) -> dict:
    groups = {}
    for arm in ARMS:
        selected = [r for r in records if r['phase']=='frozen_eval' and r['arm']==arm]
        groups[arm] = count(selected)
    training = [r for r in records if r['phase']=='train']
    adaptations = {}
    for arm in ('full', 'no_reexpansion'):
        selected = [r for r in records if r['phase']=='adapt' and r['arm']==arm]
        adaptations[arm] = {'attempts': len(selected), 'initial': selected[0]['assessment'],
                            'final': selected[-1]['assessment'],
                            'initial_decision_id': selected[0]['decision']['id'],
                            'final_decision_id': selected[-1]['decision']['id']}
    costs = defaultdict(Counter)
    for r in records:
        key=r['phase']+'/'+r['arm']
        costs[key].update(r['decision']['cost'])
        costs[key]['verification_checks'] += r['assessment']['verification_checks']
    learning = Counter()
    for event in events:
        if event['event']=='memory_updated': learning.update(event['payload']['cost'])
    retained = [r for r in records if r['phase']=='retention']
    return {'schema':'hcr-development-summary-r01',
            'basis':'deterministic authored toy-world development cases; no external LLM/neural measurements',
            'training': count(training), 'frozen_eval': groups, 'adaptation': adaptations,
            'retention': count(retained), 'costs': {k:dict(v) for k,v in costs.items()},
            'learning_costs':dict(learning), 'persistence_io': snapshots,
            'event_counts':dict(Counter(e['event'] for e in events)),
            'new_llm_calls':0, 'learned_components':['role-parameterized program registry','recall strength','outcome-frequency prior'],
            'authored_components':['binary feature encoding','bounded common recurrence','AND/OR support graph grammar',
                'positive-only development training distribution','credit assignment/weakening policy','observation acquisition policy'],
            'limitations':[
                '하나의 합성 관계 환경과 두 A 수준의 기능적 원형이다. 생물학적 신경회로나 범용 지능 구현이 아니다.',
                '8개 개발 사례와 대조군 반복은 독립 구조 표본 수가 아니다. 성능 일반화/우월성을 평가한 자료가 아니다.',
                '학습된 회로는 전체 작은 공개 관계 graph의 역할화된 실행 구조다. 일반 부분그래프 압축 또는 학습된 encoder는 아니다.',
                '구조 재사용은 동적 탐색·재구성을 줄인다. primitive proof D와 내부 signal update는 그대로 별도 계측한다.',
                '평가 정답은 최초 판단 뒤에만 공개된다. ADAPT의 고정밀 edge 관측은 유료 계산 자원으로 별도 기록한다.',
                '오류 수정은 추가 관측을 이용했다. feedback bit만으로 정답을 반전시킨 결과가 아니다.',
                'no_top_down에서 높은 판단이 proof와 불일치할 수 있다. 진실과 구조적으로 지지된 판단을 별도 보고한다.',
                'Frozen은 메모리 무변경이다. TRAIN/ADAPT의 실제 feedback 처리에서만 memory version이 바뀐다.',
                'tick 수·간선 전달·search·binding·proof·learning·IO를 개별 보고한다. 서로 다른 단위를 임의로 합쳐 속도 개선으로 쓰지 않는다.'
            ]}


def render(summary: dict, records: list[dict]) -> str:
    lines=['# HCR R0.1 기능적 통합 실행', '',
           '이 결과는 개발용 합성 환경의 실행 증거다. 기존 LLM 실험의 후속 추론이나 뇌 가설의 실증이 아니다.', '',
           '## 동일 학습 snapshot의 동결 평가',
           '| 조건 | 정답 | 오답 | 보류 | 근거 포함 정답 | 안정된 오답 | 회로 재사용 |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for name,g in summary['frozen_eval'].items():
        lines.append('| '+name+' | '+' | '.join(str(g[k]) for k in ('correct','incorrect','unresolved','strict_correct','wrong_stable','circuit_reuse'))+' |')
    lines += ['', '## 각 사례의 결과', '| 조건 | 사례 | 판단 | 외부 정답 | proof 유효 | tick | graph 탐색 |', '|---|---|---|---|---|---:|---:|']
    for r in records:
        if r['phase']!='frozen_eval': continue
        d=r['decision'];a=r['assessment']
        lines.append(f"| {r['arm']} | {r['case']} | {d['value']} | {a['correct']} | {a['proof_valid']} | {d['cost']['kernel_ticks']} | {d['cost']['search_edge_checks']} |")
    lines += ['', '## 명시적 오류 이후의 재확장']
    for arm,a in summary['adaptation'].items():
        lines.append(f"{arm}: 첫 판단 correct={a['initial']['correct']}, 마지막 correct={a['final']['correct']}, 기록한 시도 {a['attempts']}개.")
    lines += ['', '학습 메모리를 저장·재로드한 후의 별도 재방문: '+str(summary['retention']), '', '## 계측·해석 경계']
    lines.extend(summary['limitations'])
    return '\n'.join(lines)+'\n'


def run_demo(out: Path, config: Config | None = None) -> dict:
    config=config or Config();out=Path(out)
    # 기존 사용자 결과/메모리를 지우거나 덮어쓰지 않는다.
    run_started=perf_counter()
    out.mkdir(parents=True,exist_ok=False)
    plan={'schema':'hcr-development-plan-r01','config':codec.plain(config),'config_signature':config.signature,
          'source_hashes':source_hashes(),'source_hash':hashlib.sha256(codec.dumps(source_hashes()).encode()).hexdigest(),
          'training_episodes':6,'training_distribution':'positive two-edge path, reliable observations, distinct instances',
          'eval_cases':[n for n,_ in worlds()],'arms':ARMS,'adaptive_arms':['full','no_reexpansion'],
          'feedback_contract':'after decision only; correctness bit and validation flag, no correct graph',
          'additional_observation':'requested low-confidence edges only, signed reliability 0.98',
          'retention_cases':['weak_return','normal_return'],'status':'development_fixture_not_preregistered_research',
          'created_at':datetime.now(timezone.utc).isoformat(),'python':sys.version,'platform':platform.platform()}
    codec.save(out/'plan.json',plan)
    trace=Trace(out/'events.jsonl');stream=(out/'episodes.jsonl').open('x',encoding='utf-8',newline='\n')
    records=[];snapshots=[]
    def checkpoint(name: str, mem:Memory, reload:bool=True) -> Memory:
        io_started=perf_counter()
        path=out/(name+'.json');mem.save(path)
        restored=Memory.load(path,config) if reload else mem
        if restored.digest!=mem.digest:raise ContractError('memory checkpoint mismatch')
        item={'path':path.name,'bytes_written':path.stat().st_size,'bytes_read':path.stat().st_size if reload else 0,
              'save_reload_wall_seconds':perf_counter()-io_started,'memory_hash':mem.digest,'memory_version':mem.version,'circuits':len(mem.circuits),'pending':len(mem.pending)}
        snapshots.append(item);trace.emit('memory_checkpoint',item)
        return restored
    def record(engine:Engine,obs,world:World,phase:str,case:str,arm:str,mode:Mode,revision_of=None):
        before=engine.memory.digest
        decision=engine.infer(obs,mode,revision_of=revision_of)
        # 처음으로 숨은 환경과 비교하는 시점: 결정 event가 기록된 뒤다.
        assessment=assess(decision,obs,dict(world.hidden))
        row={'phase':phase,'case':case,'arm':arm,'observation':codec.plain(obs),
             'external_truth':dict(world.hidden),'decision':codec.plain(decision),'assessment':codec.plain(assessment),
             'memory_before':before,'memory_after_inference':engine.memory.digest}
        if before!=engine.memory.digest: raise ContractError('inference changed memory')
        trace.emit('external_assessment',{'decision_id':decision.id,'assessment':codec.plain(assessment)})
        records.append(row);stream.write(codec.dumps(row)+'\n');stream.flush()
        return decision,assessment
    def learn(engine,decision,assessment):
        # 논리적으로 가정 아래 유효한 것과 실제 그 가정이 맞았던 것을 구분한다.
        validated=assessment.proof_valid and assessment.assumption_correct is True
        engine.feedback(Feedback('feedback-'+decision.id,decision.id,decision.observation_digest,
                                 assessment.correct,validated))
    state='failed'
    try:
        initial=checkpoint('memory_before',Memory())
        engine=Engine(config,initial,trace)
        for i in range(6):
            world=chain('train-%03d'%i,prefix='instance-%02d'%i)
            decision,a=record(engine,world.observation,world,'train','reliable_positive','full',Mode.TRAIN)
            learn(engine,decision,a)
        trained=checkpoint('memory_after_training',engine.memory)
        frozen_hash=trained.digest
        for arm,options in ARMS.items():
            evaluator=Engine(config,deepcopy(trained),trace,**options)
            for name,world in worlds(): record(evaluator,world.observation,world,'frozen_eval',name,arm,Mode.FROZEN_EVAL)
            if evaluator.memory.digest!=frozen_hash:raise ContractError('frozen evaluation modified training snapshot')
        retained=None
        for arm in ('full','no_reexpansion'):
            adaptive=Engine(config,deepcopy(trained),trace,**ARMS[arm])
            world=chain('adapt-'+arm,(False,True),(-.06,.92),prefix='adapt-current')
            d,a=record(adaptive,world.observation,world,'adapt','weak_conflict',arm,Mode.ADAPT)
            learn(adaptive,d,a)
            if a.correct is False:
                request=adaptive.request_revision(d.id)
                if request is not None:
                    observed=world.measure(request)
                    trace.emit('measurement_delivered',{'request':codec.plain(request),'observation':codec.plain(observed),
                                                        'measurement_count':len(request.edge_ids)})
                    d2,a2=record(adaptive,observed,world,'adapt','measured_revision',arm,Mode.ADAPT,revision_of=d.id)
                    learn(adaptive,d2,a2)
            snapshot=checkpoint('memory_after_adapt_'+arm,adaptive.memory)
            if arm=='full':retained=snapshot
        revisitor=Engine(config,retained,trace)
        for label,world in [('weak_return',chain('return-001',(False,True),(-.06,.92),prefix='new-return')),
                            ('normal_return',chain('return-002',prefix='normal-return'))]:
            record(revisitor,world.observation,world,'retention',label,'full',Mode.FROZEN_EVAL)
        checkpoint('memory_after',revisitor.memory)
        summary=summarize(records,trace.records,snapshots)
        codec.save(out/'summary.json',summary)
        with (out/'summary.ko.md').open('x',encoding='utf-8',newline='\n') as f:f.write(render(summary,records))
        state='complete'
    except BaseException as error:
        trace.emit('run_failed',{'type':type(error).__name__,'message':str(error)})
        raise
    finally:
        stream.close();trace.close()
        codec.save(out/'status.json',{'state':state,'episode_records':len(records),'event_count':trace.count,'event_head':trace.head,
                                      'llm_calls':0,'automatic_retry':False,'run_wall_seconds':perf_counter()-run_started})
        files={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'}
        codec.save(out/'manifest.json',{'schema':'hcr-run-manifest-r01','state':state,'files':files})
    return summary
