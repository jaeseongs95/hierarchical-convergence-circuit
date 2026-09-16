"""EXP-09 r2의 순수 기록 분석. 엔진을 import하거나 원인을 추측하지 않는다."""
from __future__ import annotations
from collections import Counter, defaultdict
from copy import deepcopy
from statistics import median
from collect import BaselineError, canonical, canonical_cost, pattern_id, require, sha
from memory_equivalence import compare_revision_memory


def semantic_decision(raw: dict) -> dict:
    """정확히 같은 입력·memory의 비교에서 decision ID와 실측 시간만 제외한다."""
    out = deepcopy(raw)
    out.pop('id')
    out['cost'].pop('wall_seconds')
    return out


def input_content(obs: dict) -> dict:
    """재시도/새 episode 비교용. 이 함수를 strict persistence 비교에 쓰지 않는다."""
    return {k: v for k, v in obs.items() if k not in ('episode_id', 'revision')}


def memory_content(document: dict) -> dict:
    """이력 증가와 circuit의 실제 상태 변경을 구별한다. 비교에서 이력을 삭제하지 않는다."""
    return {k: document[k] for k in ('circuits', 'pending')}


def memory_changes(before: dict, after: dict) -> list[dict]:
    b = {pattern_id(c): c for c in before['circuits']}
    a = {pattern_id(c): c for c in after['circuits']}
    result = []
    for cid in sorted(set(b) | set(a)):
        old, new = b.get(cid), a.get(cid)
        result.append(dict(circuit_id=cid,
            before_strength=old['strength'] if old else None, after_strength=new['strength'] if new else None,
            before_failures=old['failures'] if old else None, after_failures=new['failures'] if new else None,
            before_active=old['active'] if old else None, after_active=new['active'] if new else None,
            before_evidence=len(old['evidence_episodes']) if old else None,
            after_evidence=len(new['evidence_episodes']) if new else None))
    return result


def decompose(rows: list[dict], events: list[dict]) -> dict:
    """pool/decision 카운터와 선택 회로를 실제 trace에 연결한다. 비용 별칭은 합산하지 않는다."""
    rowmap = {r['decision']['id']: r for r in rows}
    require(len(rowmap) == len(rows), '중복 decision')
    memory = None
    memory_at, networks = {}, {}
    costs, applied = defaultdict(Counter), defaultdict(list)
    candidate_rows, feedback_rows = [], []
    for event in events:
        p, name = event['payload'], event['event']
        if name == 'r02_engine_created':
            memory = p['memory_document']
        elif name == 'r02_attempt_started':
            require(memory is not None, 'memory 없는 attempt')
            memory_at[p['decision_id']] = memory
        elif name == 'r02_network':
            require(p['network_id'] not in networks, '중복 network')
            networks[p['network_id']] = p
        elif name == 'r02_tick':
            n = networks[p['network_id']]
            require(n['decision_id'] == p['decision_id'], 'network/decision 불일치')
            c = costs[(p['decision_id'], n['kind'])]
            c['kernel_ticks'] += 1
            c['signal_transmissions'] += sum(n['top_down'] or link['kind'] != 'top_down' for link in n['program']['links'])
            c['group_updates'] += len(n['program']['groups'])
        elif name == 'r02_expansion' and p['candidate']['source'] == 'circuit':
            candidate = p['candidate']
            applied[p['decision_id']].append((candidate['circuit_id'], canonical(candidate['binding'])))
        elif name == 'r02_pool_result':
            did = p['decision_id']
            require(did in rowmap and did in memory_at, '후보의 decision 누락')
            circuit_map = {pattern_id(c): c for c in memory_at[did]['circuits']}
            for a in p['activations']:
                c = circuit_map[a['circuit_id']]
                candidate_rows.append(dict(decision_id=did, phase=rowmap[did]['phase'], arm=rowmap[did]['arm'],
                    case=rowmap[did]['case'], network_id=p['network_id'], circuit_id=a['circuit_id'],
                    pattern_length=len(c['pattern']['relations']), strength=c['strength'], failures=c['failures'],
                    evidence_count=len(c['evidence_episodes']), prior=a['prior'], activation=a['activation'],
                    mismatch=a['mismatch'], eligible=a['eligible'], binding=a['binding']))
        elif name == 'r02_memory_updated':
            require(memory is not None, 'memory update 이전 상태 누락')
            did = p['patch']['decision_id']
            row = rowmap[did]
            feedback_rows.append(dict(decision_id=did, phase=row['phase'], arm=row['arm'],
                output=row['decision']['value'], correct=row['assessment']['correct'],
                changes=p['patch']['changes'], circuit_state_changed=memory_content(memory) != memory_content(p['memory_document']),
                history_changed=memory != p['memory_document'], circuit_delta=memory_changes(memory, p['memory_document']),
                cost=canonical_cost(p['cost'])))
            memory = p['memory_document']
    for c in candidate_rows:
        key = (c['circuit_id'], canonical(c['binding']))
        c['binding_applied_in_attempt'] = key in applied[c['decision_id']]
        c['in_final_decision'] = c['circuit_id'] in rowmap[c['decision_id']]['decision']['circuit_ids']
    cost_rows = []
    for row in rows:
        d = row['decision']; c = canonical_cost(d['cost'])
        for field in ('kernel_ticks', 'signal_transmissions', 'group_updates'):
            require(sum(costs[(d['id'], k)][field] for k in ('pool', 'decision')) == c[field], '역할별 비용 불일치: ' + field)
        cost_rows.append(dict(decision_id=d['id'], phase=row['phase'], arm=row['arm'], case=row['case'],
            attempt=d['attempt'], correct=row['assessment']['correct'], value=d['value'],
            primitive_D=d['proof']['primitive_depth'], **c,
            pool_ticks=costs[(d['id'], 'pool')]['kernel_ticks'],
            decision_ticks=costs[(d['id'], 'decision')]['kernel_ticks'],
            pool_signals=costs[(d['id'], 'pool')]['signal_transmissions'],
            decision_signals=costs[(d['id'], 'decision')]['signal_transmissions']))
    return dict(costs=cost_rows, candidates=candidate_rows, feedback=feedback_rows)


def comparison(left: dict, right: dict, name: str, *, strict_input=True) -> dict:
    require(left['external_truth'] == right['external_truth'], '짝의 정답 조건 불일치: ' + name)
    same_public = left['observation'] == right['observation']
    if strict_input:
        require(same_public, '짝의 공개 입력 불일치: ' + name)
    a, b = left['decision'], right['decision']
    ca, cb = canonical_cost(a['cost']), canonical_cost(b['cost'])
    require(set(ca) == set(cb), '비용 필드 불일치')
    return dict(name=name, left_id=a['id'], right_id=b['id'], same_public_input=same_public,
        same_input_except_episode_revision=input_content(left['observation']) == input_content(right['observation']),
        left_correct=left['assessment']['correct'], right_correct=right['assessment']['correct'],
        left_value=a['value'], right_value=b['value'], left_circuits=a['circuit_ids'], right_circuits=b['circuit_ids'],
        left_primitive_D=a['proof']['primitive_depth'], right_primitive_D=b['proof']['primitive_depth'],
        cost_delta={k: cb[k] - ca[k] for k in ca},
        is_observed_paired_contrast=True, population_generalization_claimed=False)


def benchmark_report(rows: list[dict]) -> dict:
    groups = defaultdict(dict)
    for r in rows:
        if r['phase'] == 'cost_pairs':
            key = (r['case'], r['replicate'])
            require(r['arm'] not in groups[key], '중복 비용 짝')
            groups[key][r['arm']] = r
    pairs, cases = [], defaultdict(list)
    for (case, replicate), arms in sorted(groups.items()):
        require(set(arms) == {'graph_only', 'circuits'}, '비용 짝 누락')
        p = comparison(arms['graph_only'], arms['circuits'], f'{case}/{replicate}')
        p.update(case=case, replicate=replicate,
            first_arm=min(arms, key=lambda a: arms[a]['order_in_pair']),
            graph_ms=arms['graph_only']['decision']['cost']['wall_seconds'] * 1000,
            circuits_ms=arms['circuits']['decision']['cost']['wall_seconds'] * 1000)
        pairs.append(p); cases[case].append(p)
    summary = []
    for case, ps in sorted(cases.items()):
        summary.append(dict(case=case, pairs=len(ps), first_arm_counts=dict(Counter(p['first_arm'] for p in ps)),
            graph_median_ms=median(p['graph_ms'] for p in ps), circuits_median_ms=median(p['circuits_ms'] for p in ps),
            median_paired_delta_ms=median(p['circuits_ms'] - p['graph_ms'] for p in ps),
            operation_deltas_constant=all({k:v for k,v in p['cost_delta'].items() if k != 'wall_seconds'} ==
                {k:v for k,v in ps[0]['cost_delta'].items() if k != 'wall_seconds'} for p in ps),
            all_pairs_correct=all(p['left_correct'] is True and p['right_correct'] is True for p in ps)))
    return dict(pairs=pairs, cases=summary, independent_task_samples=False,
                timing_scope='동일 프로세스의 새 Engine/Trace 기록 포함 infer. 초기화/학습/I-O 전체 비용은 아님.')


def summarize(rows: list[dict], events: list[dict], persistence: dict) -> dict:
    detail = decompose(rows, events)
    factorial = [r for r in rows if r['phase'] == 'factorial']
    cells = {r['arm']: r for r in factorial}
    contrasts = []
    for profile in ('weak', 'measured'):
        for routing in ('circuits', 'graph_only'):
            contrasts.append(comparison(cells[f'before/{profile}/{routing}'], cells[f'after/{profile}/{routing}'],
                'memory/' + profile + '/' + routing))
    for memory in ('before', 'after'):
        for profile in ('weak', 'measured'):
            contrasts.append(comparison(cells[f'{memory}/{profile}/graph_only'], cells[f'{memory}/{profile}/circuits'],
                'routing/' + memory + '/' + profile))
        for routing in ('circuits', 'graph_only'):
            a,b=cells[f'{memory}/weak/{routing}'],cells[f'{memory}/measured/{routing}']
            contrasts.append(comparison(a,b,'measurement/'+memory+'/'+routing,strict_input=False))
    trajectories = defaultdict(list)
    for r in rows:
        if r['phase'] == 'adaptation': trajectories[r['arm']].append(r)
    trajectory_results = {}
    feedback_by_id = {f['decision_id']:f for f in detail['feedback']}
    for arm, group in trajectories.items():
        infer_total, learning_total = Counter(), Counter()
        for r in group:
            infer_total.update(canonical_cost(r['decision']['cost']))
            f = feedback_by_id.get(r['decision']['id'])
            if f is not None: learning_total.update(f['cost'])
        trajectory_results[arm] = dict(attempts=len(group), initial_correct=group[0]['assessment']['correct'],
            final_correct=group[-1]['assessment']['correct'], decision_ids=[r['decision']['id'] for r in group],
            initial_circuits=group[0]['decision']['circuit_ids'], final_circuits=group[-1]['decision']['circuit_ids'],
            inference_cost=dict(infer_total), feedback_cost=dict(learning_total))
    repeat = [r for r in rows if r['phase'] == 'adaptation' and r['arm'] == 'same_score_control']
    measured = [r for r in rows if r['phase'] == 'adaptation' and r['arm'] == 'measured_replay']
    require(repeat and measured, '재시도 대조 누락')
    correction = dict(available=len(repeat)>1 and len(measured)>1)
    if correction['available']:
        r,m=repeat[1],measured[1]
        require(input_content(repeat[0]['observation']) == input_content(r['observation']), '같은 점수 대조의 입력 변경')
        memory_comparison = compare_revision_memory(repeat[0], r, measured[0], m, events)
        require(not r['decision']['circuit_ids'] and not m['decision']['circuit_ids'], '재시도에 회로가 사용됨')
        correction.update(same_score_correct=r['assessment']['correct'], measured_correct=m['assessment']['correct'],
            same_score_output=r['decision']['value'], measured_output=m['decision']['value'],
            extra_measurement_needed_in_this_pair=(m['assessment']['correct'] is True and r['assessment']['correct'] is not True),
            same_score_revision_id=r['decision']['id'], measured_revision_id=m['decision']['id'],
            memory_equal_at_revision=memory_comparison['exact_document_equal'],
            memory_execution_state_equal=memory_comparison['execution_state_equal'],
            provenance_correspondence_valid=memory_comparison['provenance_correspondence_valid'],
            memory_comparison=memory_comparison, circuits_disabled_in_both=True,
            caveat='동일 점수 revision은 추가 정보 없는 공개 입력 대조다. 실제 정밀 측정으로 보고하지 않는다.')
    return dict(schema='hcr-r02-exp09-summary-v2', summary_contract='paired-provenance-v1',
        inferences=len(rows), persistence=persistence,
        factorial=[dict(condition=r['arm'], value=r['decision']['value'], correct=r['assessment']['correct'],
            circuit_ids=r['decision']['circuit_ids'], memory_digest=r['memory_before']) for r in factorial],
        contrasts=contrasts, trajectories=trajectory_results, correction_controls=correction,
        benchmark=benchmark_report(rows), details=detail,
        inference_outcomes=dict(correct=sum(r['assessment']['correct'] is True for r in rows),
            incorrect=sum(r['assessment']['correct'] is False for r in rows), unresolved=sum(r['assessment']['correct'] is None for r in rows)),
        boundaries=dict(engine_changed=False, hypothesis_proved=False, negative_exception_learning_added=False,
            full_runtime_graph_audit=False, timings_are_single_machine_diagnostics=True))


def render(summary: dict) -> str:
    p=summary['persistence']
    lines=['# EXP-09 r2 — 재오답 원인분리와 비용 분해','',
        '이 파일의 수치는 실제 실행 후 생성된다. 과거 run이나 가설의 증명으로 대체하지 않는다.','',
        '## 저장·복원',f"- memory 문서 동등: {p['memory_equal']}",
        f"- 행동 동등(ID·시간만 제외): {p['behavior_equal']}",f"- direct/reload 정답: {p['both_correct']}",'',
        '둘 다 오답이면서 동등할 수 있다. 이는 해당 대조에서 직렬화가 행동 차이를 만들지 않았다는 뜻이다.','',
        '## memory × 입력 정보 × 회로 사용','| 조건 | 출력 | 정답 | 회로 |','|---|---|---|---|']
    for r in summary['factorial']:
        lines.append(f"| {r['condition']} | {r['value']} | {r['correct']} | {', '.join(r['circuit_ids'])} |")
    lines+=['','## 동일 점수 재시도 / 정밀 측정 재시도','```json',
        __import__('json').dumps(summary['correction_controls'],ensure_ascii=False,indent=2),'```','',
        '## 비용 — 같은 학습 memory에서 회로 사용만 변경',
        '| 사례 | 반복 쌍 | graph 중앙값(ms) | circuit 중앙값(ms) | 쌍 차이 중앙값(ms) | 카운터 차이 일정 |',
        '|---|---:|---:|---:|---:|---|']
    for r in summary['benchmark']['cases']:
        lines.append(f"| {r['case']} | {r['pairs']} | {r['graph_median_ms']:.3f} | {r['circuits_median_ms']:.3f} | {r['median_paired_delta_ms']:.3f} | {r['operation_deltas_constant']} |")
    lines+=['','## 재시도·학습 횟수별 경로', '| 조건 | 시도 | 최초/최종 정답 | 추론 tick | 학습 update |', '|---|---:|---|---:|---:|']
    for arm, t in summary['trajectories'].items():
        lines.append(f"| {arm} | {t['attempts']} | {t['initial_correct']}/{t['final_correct']} | {t['inference_cost'].get('kernel_ticks',0)} | {t['feedback_cost'].get('learning_updates',0)} |")
    lines+=['','pool_ticks/pool_signals는 전체 tick/signal의 내역이다. 전체에 다시 더하지 않는다.',
        '반복 실행은 새 독립 과제가 아니다. 각 실행의 원시 비용은 costs.csv, 짝 차이는 summary.json에 있다.','',
        '## 학습의 실제 범위','feedback_changes.json에서 변화 이력과 회로 내용 변화를 별도로 확인한다.',
        '현재 학습기는 참인 검증 경로만 컴파일한다. 거짓 출력의 정답은 음의 예외회로로 자동 저장되지 않는다.',
        'candidate_trace.json의 failures/strength/적용 binding을 통해 약화한 회로와 다른 후보의 재사용을 구분한다.',
        '동반된 회로 선택만으로 특정 회로가 재오답의 유일한 원인이라고 판정하지 않는다.','',
        '## 다음 단계','이 대조 결과를 기준선에 기록한 후 R0.2.1 snapshot/restore/resume으로 이어간다.',
        'negative exception memory, credit assignment 변경, pool 최적화는 별도 개입으로 비교해야 한다.','']
    return '\n'.join(lines)
