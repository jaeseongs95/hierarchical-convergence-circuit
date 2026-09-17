"""R0.2 개발 실험. 숨은 truth와 실험 분류는 이 실행기/외부 평가기에만 둔다."""
from __future__ import annotations
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import platform
import sys
from .. import codec
from ..model import AdaptiveConfig, Mode, Feedback, ContractError
from ..runtime import AdaptiveEngine
from ..circuits import AdaptiveMemory
from ..trace import Trace
from ..tasks.toy_world import chain, diamond
from .reference import assess


def counts(rows):
    return dict(attempts=len(rows), correct=sum(r['assessment']['correct'] is True for r in rows),
                incorrect=sum(r['assessment']['correct'] is False for r in rows),
                unresolved=sum(r['assessment']['correct'] is None for r in rows),
                strict_correct=sum(r['assessment']['correct'] is True and r['assessment']['proof_valid']
                                   and r['assessment']['assumption_correct'] is True for r in rows),
                wrong_stable=sum(r['assessment']['wrong_stable'] for r in rows),
                circuit_reuse=sum(bool(r['decision']['circuit_ids']) for r in rows))


def pair_summary(rows):
    pairs = {}
    for row in rows:
        if row['phase'] == 'familiarity':
            pairs.setdefault(row['case'], {})[row['arm']] = row
    result = {}
    for case, pair in pairs.items():
        cold, warm = pair['cold'], pair['warm']
        result[case] = dict(cold_decision=cold['decision']['id'], warm_decision=warm['decision']['id'],
            cold_correct=cold['assessment']['correct'], warm_correct=warm['assessment']['correct'],
            cold_primitive_D=cold['decision']['proof']['primitive_depth'],
            warm_primitive_D=warm['decision']['proof']['primitive_depth'],
            warm_minus_cold={k: warm['decision']['cost'][k] - cold['decision']['cost'][k]
                            for k in ('graph_nodes_created', 'graph_edges_created', 'expansions',
                                      'binding_operations', 'signal_events', 'convergence_ticks', 'wall_seconds')})
    return result


def summarize(rows, events):
    grouped = defaultdict(list)
    cost = defaultdict(Counter)
    learning = Counter()
    for row in rows:
        key = row['phase'] + '/' + row['arm']
        grouped[key].append(row)
        cost[key].update(row['decision']['cost'])
        cost[key]['verification_checks'] += row['assessment']['verification_checks']
    for event in events:
        if event['event'] == 'r02_memory_updated':
            learning.update(event['payload']['cost'])
    adaptation = {}
    for key, group in grouped.items():
        if key.startswith(('misconvergence/', 'tradeoff/')):
            adaptation[key] = dict(attempts=len(group), initial=group[0]['assessment'], final=group[-1]['assessment'],
                                   initial_decision=group[0]['decision']['id'], final_decision=group[-1]['decision']['id'])
    return dict(schema='hcr-development-summary-r02', hypothesis_proved=False,
        groups={key: counts(group) for key, group in sorted(grouped.items())},
        costs={key: dict(value) for key, value in sorted(cost.items())}, learning_costs=dict(learning),
        familiarity_pairs=pair_summary(rows), adaptation=adaptation,
        checkpoints=[e['payload'] for e in events if e['event'] == 'r02_memory_checkpoint'],
        event_counts=dict(Counter(e['event'] for e in events)), actual_llm_calls=0, actual_network_calls=0,
        authored=['binary observations', 'two fixed A levels', 'common recurrence', 'bounded path motif grammar',
                  'expansion ordering', 'feedback credit assignment', 'measurement policy', 'development fixtures'],
        learned=['verified role-pattern availability', 'pattern strength', 'future circuit routing/prior'],
        limitations=[
            '개발용 deterministic symbolic toy-world 실험이다. 독립 일반화 표본이나 생물학 검증이 아니다.',
            '부분 컴파일 범위는 연속 directed path motifs다. arbitrary graph mining이나 A/M 자동화가 아니다.',
            '동적 dependency node 감소와 총 연산/시간 감소는 별개다. matching/pool/proof 비용도 포함한다.',
            'signal_events=signal_transmissions, convergence_ticks=kernel_ticks 등 별칭은 중복 합산하지 않는다.',
            '오수렴 또는 trade-off의 발생은 측정 결과다. 실험 성공 조건을 맞추려고 최초 판단을 강제하지 않는다.',
            '오류 수정은 외부 feedback와 요청된 추가 측정을 쓴다. feedback bit만으로 정답을 뒤집지 않는다.',
            'primitive proof D는 macro 호출 횟수로 대체하지 않는다. 실제 계측 wall time은 단일 실행의 관측값이다.'
        ])


def render(summary):
    lines = ['# HCR R0.2 개발 실행 결과', '',
             '실제 실행이 만든 결과다. 가설 입증 여부와 구분하며, 이 문서의 수치는 소스 배포 때 미리 작성하지 않는다.', '',
             '## 조건별 판단', '| 조건 | 실행 | 정답 | 오답 | 보류 | 근거 포함 정답 | 안정 오답 | 회로 사용 |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for key, values in summary['groups'].items():
        lines.append('| ' + key + ' | ' + ' | '.join(str(values[k]) for k in
            ('attempts', 'correct', 'incorrect', 'unresolved', 'strict_correct', 'wrong_stable', 'circuit_reuse')) + ' |')
    lines += ['', '## Familiarity: warm − cold',
              '음수는 해당 계측량 감소다. 서로 단위가 다른 비용을 더하지 않는다.', '',
              '| 사례 | dependency node | 확장 | binding | 신호 | tick | primitive D (cold / warm) |',
              '|---|---:|---:|---:|---:|---:|---|']
    for case, p in summary['familiarity_pairs'].items():
        d = p['warm_minus_cold']
        lines.append('| ' + case + ' | ' + ' | '.join(str(d[k]) for k in
            ('graph_nodes_created', 'expansions', 'binding_operations', 'signal_events', 'convergence_ticks'))
            + f" | {p['cold_primitive_D']} / {p['warm_primitive_D']} |")
    lines += ['', '## 해석 범위', *['- ' + x for x in summary['limitations']], '']
    return '\n'.join(lines)


def source_hashes():
    root = Path(__file__).resolve().parents[3]
    paths = list((root / 'src/hcr').rglob('*.py')) + [root / 'hcr.py', root / 'configs/r01.toml', root / 'configs/r02.toml']
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths) if p.is_file() and '__pycache__' not in p.parts}


def run_demo(out: Path, config: AdaptiveConfig | None = None):
    config = config or AdaptiveConfig()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    plan = dict(schema='hcr-plan-r02', created_at=datetime.now(timezone.utc).isoformat(),
                config=codec.plain(config), config_signature=config.signature, source_hashes=source_hashes(),
                protocol='r02-authored-path-motifs-v1', training_episodes=6,
                tradeoff_training_counts=[3, 9], phase_order=['training', 'familiarity', 'novelty',
                    'misconvergence', 'retention', 'tradeoff_training', 'tradeoff'],
                evaluation_labels_passed_to_engine=False,
                python=sys.version, platform=platform.platform(), hypothesis_proved=False)
    codec.save(out / 'plan.json', plan)
    codec.save(out / 'status.json', dict(state='running', schema='hcr-status-r02'))
    trace = Trace(out / 'events.jsonl')
    rows = []
    next_episode = 0

    def world(length=3, values=None, scores=None, branched=False):
        nonlocal next_episode
        next_episode += 1
        # 평가 분류를 담지 않는 opaque episode/object ID만 관측으로 보낸다.
        eid, prefix = 'e' + str(next_episode).zfill(5), 'o' + str(next_episode).zfill(5)
        if branched:
            return diamond(eid, values if values is not None else (True, True, True, True), prefix=prefix)
        return chain(eid, values if values is not None else (True,) * length, scores, prefix=prefix)

    def record(engine, item, phase, arm, case, mode=Mode.FROZEN_EVAL, revision_of=None):
        before = engine.memory.digest
        decision = engine.infer(item.observation, mode, revision_of=revision_of)
        after = engine.memory.digest
        assessment = assess(decision, item.observation, dict(item.hidden))
        trace.emit('r02_external_assessment', dict(decision_id=decision.id, assessment=codec.plain(assessment)))
        row = dict(phase=phase, arm=arm, case=case, observation=codec.plain(item.observation),
                   external_truth=dict(item.hidden), decision=codec.plain(decision), assessment=codec.plain(assessment),
                   memory_before=before, memory_after_inference=after)
        rows.append(row)
        with (out / 'episodes.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(codec.dumps(row) + '\n')
        if mode != Mode.FROZEN_EVAL:
            engine.feedback(Feedback('feedback-' + decision.id, decision.id, decision.observation_digest,
                            assessment.correct, assessment.proof_valid and assessment.assumption_correct is True))
        return decision, assessment

    def checkpoint(engine, name):
        path = out / name
        engine.memory.save(path)
        restored = AdaptiveMemory.load(path, config)
        if restored.digest != engine.memory.digest:
            raise ContractError('R0.2 persistence mismatch')
        trace.emit('r02_memory_checkpoint', dict(path=name, memory_hash=restored.digest,
            memory_version=restored.version, bytes_written=path.stat().st_size))
        return restored

    def adapt(engine, item, phase, arm, case):
        decision, assessment = record(engine, item, phase, arm, case, Mode.ADAPT)
        # 측정된 오류가 없으면 억지 오답/수정을 만들지 않는다.
        while assessment.correct is False:
            request = engine.request_revision(decision.id)
            if request is None:
                break
            obs = item.measure(request)
            trace.emit('r02_measurement_delivered', dict(request=codec.plain(request), observation=codec.plain(obs)))
            item = replace(item, observation=obs)
            decision, assessment = record(engine, item, phase, arm, case, Mode.ADAPT, decision.id)
        return engine

    try:
        training = AdaptiveEngine(config, trace=trace)
        for i in range(6):
            record(training, world(), 'training', 'full', 'train-' + str(i), Mode.TRAIN)
        learned = checkpoint(training, 'memory_after_training.json')
        familiar = [('same_structure', world()),
                    ('counterfactual', world(values=(False, True, True))),
                    ('renamed_reordered', world())]
        name, item = familiar[-1]
        familiar[-1] = (name, replace(item, observation=replace(item.observation,
                                               edges=tuple(reversed(item.observation.edges)))))
        for case, item in familiar:
            for arm in ('cold', 'warm'):
                memory = deepcopy(learned) if arm == 'warm' else AdaptiveMemory.empty(config)
                record(AdaptiveEngine(config, memory, trace), item, 'familiarity', arm, case)
        for case, item in [('longer_composition', world(length=4)), ('branched_composition', world(branched=True))]:
            for arm in ('graph_only', 'full'):
                record(AdaptiveEngine(config, deepcopy(learned), trace, use_circuits=arm == 'full'),
                       item, 'novelty', arm, case)
        conflict = world(values=(False, True, True), scores=(-.06, .92, .92))
        updated = None
        for arm in ('full', 'no_reexpansion'):
            engine = AdaptiveEngine(config, deepcopy(learned), trace, allow_reexpansion=arm == 'full')
            adapt(engine, conflict, 'misconvergence', arm, 'weak_conflict')
            if arm == 'full':
                updated = checkpoint(engine, 'memory_after_adaptation.json')
        record(AdaptiveEngine(config, updated, trace), world(values=(False, True, True), scores=(-.06, .92, .92)),
               'retention', 'reload', 'new_episode_same_measurement_profile')
        for repeats in (3, 9):
            arm = 'training_' + str(repeats)
            engine = AdaptiveEngine(config, trace=trace)
            for i in range(repeats):
                record(engine, world(), 'tradeoff_training', arm, 'train-' + str(i), Mode.TRAIN)
            checkpoint(engine, 'memory_' + arm + '.json')
            adapt(engine, world(values=(False, True, True), scores=(-.06, .92, .92)),
                  'tradeoff', arm, 'matched_weak_conflict')
        trace.close()
        summary = summarize(rows, trace.records)
        codec.save(out / 'summary.json', summary)
        (out / 'summary.ko.md').write_text(render(summary), encoding='utf-8', newline='\n')
        codec.save(out / 'status.json', dict(schema='hcr-status-r02', state='complete',
            episode_records=len(rows), event_count=trace.count, event_head=trace.head,
            actual_llm_calls=0, actual_network_calls=0), replace=True)
        files = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'manifest.json'}
        codec.save(out / 'manifest.json', dict(schema='hcr-run-manifest-r02', state='complete', files=files))
        return summary
    except Exception as error:
        trace.close()
        codec.save(out / 'status.json', dict(schema='hcr-status-r02', state='failed',
                    error_type=type(error).__name__, error=str(error), episode_records=len(rows),
                    event_count=trace.count, event_head=trace.head), replace=True)
        raise
