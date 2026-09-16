"""EXP-09 첫 오류 전이의 동등성. 실행 ID만 증거에 따라 대응하고 이력을 삭제하지 않는다."""
from __future__ import annotations
from copy import deepcopy
from collect import canonical, require, sha


def differences(left, right, path: str = '') -> list[str]:
    """타입·리스트 순서를 포함해 서로 다른 필드 경로를 반환한다."""
    if type(left) is not type(right):
        return [path or '$']
    if isinstance(left, dict):
        out = []
        for key in sorted(set(left) | set(right)):
            p = path + '/' + str(key).replace('~', '~0').replace('/', '~1')
            out.extend([p] if key not in left or key not in right else differences(left[key], right[key], p))
        return out
    if isinstance(left, list):
        if len(left) != len(right):
            return [path or '$']
        return [p for i, (a, b) in enumerate(zip(left, right)) for p in differences(a, b, f'{path}/{i}')]
    return [] if left == right else [path or '$']


def _correspond(document: dict, decision_id: str, feedback_id: str,
                target_decision: str, target_feedback: str) -> tuple[dict, list[str]]:
    """정해진 참조 필드만 치환한다. 문자열 전체 replace나 키 삭제는 사용하지 않는다."""
    out = deepcopy(document)
    paths = []
    for bucket in ('circuits', 'pending'):
        for i, item in enumerate(out[bucket]):
            for j, value in enumerate(item['feedback_ids']):
                if value == feedback_id:
                    item['feedback_ids'][j] = target_feedback
                    paths.append(f'/{bucket}/{i}/feedback_ids/{j}')
    for i, value in enumerate(out['consumed_feedback']):
        if value == feedback_id:
            out['consumed_feedback'][i] = target_feedback
            paths.append(f'/consumed_feedback/{i}')
    for i, patch in enumerate(out['patches']):
        if patch['decision_id'] == decision_id:
            patch['decision_id'] = target_decision
            paths.append(f'/patches/{i}/decision_id')
        if patch['feedback_id'] == feedback_id:
            patch['feedback_id'] = target_feedback
            paths.append(f'/patches/{i}/feedback_id')
    return out, paths


def _transition_index(events: list[dict]) -> dict:
    """attempt 직전 memory와 바로 뒤 feedback 전이를 append-only 이벤트에서 연결한다."""
    current = None
    pending = None
    records = {}
    for e in events:
        p, kind = e['payload'], e['event']
        if kind == 'r02_engine_created':
            require(pending is None, '미완료 feedback 중 engine 교체')
            current = p['memory_document']
            require(sha(canonical(current)) == p['memory_hash'], 'engine memory digest')
        elif kind == 'r02_attempt_started':
            did = p['decision_id']
            require(current is not None and pending is None and did not in records, 'attempt memory 순서/중복')
            require(sha(canonical(current)) == p['memory_hash'] and current['version'] == p['memory_version'],
                    'attempt memory 문서/hash 불일치')
            records[did] = dict(start=p, before=current, engine_epoch=e['seq'])
        elif kind == 'r02_feedback':
            did = p['decision_id']
            require(did in records and 'feedback' not in records[did] and pending is None, 'feedback 순서/중복')
            records[did]['feedback'] = p
            pending = did
        elif kind == 'r02_memory_updated':
            did = p['patch']['decision_id']
            require(did == pending and 'after' not in records[did], 'memory 전이 순서/중복')
            r = records[did]
            require(p['patch']['feedback_id'] == r['feedback']['id'], 'patch feedback 참조 불일치')
            require(p['patch']['before_hash'] == sha(canonical(r['before'])), 'patch 시작 hash')
            require(sha(canonical(p['memory_document'])) == p['memory_after'], 'patch 결과 hash')
            require(p['memory_document']['patches'][-1] == p['patch'], 'memory 마지막 patch 불일치')
            r.update(after=p['memory_document'], update=p)
            current = p['memory_document']
            pending = None
    require(pending is None, '마지막 feedback 전이 누락')
    return records


def compare_revision_memory(left_first: dict, left_next: dict, right_first: dict,
                            right_next: dict, events: list[dict]) -> dict:
    """두 arm의 첫 오류 뒤 상태 비교. direct/reload의 exact 비교에는 사용하지 않는다.

    첫 입력·최초 판단·feedback·시작 memory를 먼저 대조한다. 현재 최초 오류 전이만
    지원하며 다단계 학습 이력의 임의 alpha-equivalence를 주장하지 않는다.
    """
    from probe_analysis import semantic_decision  # 분석 모듈간 순환은 호출 시점에만 해소한다.
    records = _transition_index(events)
    ld, rd = left_first['decision']['id'], right_first['decision']['id']
    ln, rn = left_next['decision']['id'], right_next['decision']['id']
    require(len({ld, rd, ln, rn}) == 4, '별도 arm/시도의 고유 ID 필요')
    l, r = records[ld], records[rd]
    require(left_first['decision']['attempt'] == right_first['decision']['attempt'] == 1
            and left_next['decision']['attempt'] == right_next['decision']['attempt'] == 2, '첫 재시도 비교만 지원')
    require(left_first['observation'] == right_first['observation']
            and left_first['external_truth'] == right_first['external_truth'], '재시도군 최초 입력/정답 차이')
    require(semantic_decision(left_first['decision']) == semantic_decision(right_first['decision'])
            and left_first['assessment'] == right_first['assessment'], '최초 판단/평가 차이')
    require(l['before'] == r['before'] and left_first['memory_before'] == right_first['memory_before']
            == sha(canonical(l['before'])), '재시도군 초기 memory 차이')
    for row, rec, first_id, next_id in ((left_first, l, ld, ln), (right_first, r, rd, rn)):
        require('after' in rec and rec['feedback']['correct'] is False, '최초 오류 feedback 전이 필요')
        require(records[next_id]['start']['revision_of'] == first_id
                and rec['after'] == records[next_id]['before'], '해당 오류 전이와 재시도 memory 연결 누락')
        require(rec['start']['observation'] == row['observation'], '최초 관측/trace 차이')
        require(rec['feedback']['observation_digest'] == row['decision']['observation_digest'], 'feedback 관측 참조 차이')
        require(rec['after']['version'] == rec['before']['version'] + 1, '첫 전이 version 차이')
    for row, rec in ((left_next, records[ln]), (right_next, records[rn])):
        require(row['memory_before'] == row['memory_after_inference'] == sha(canonical(rec['before'])),
                '재시도 행 memory hash')
    lf, rf = l['feedback']['id'], r['feedback']['id']
    require(lf != rf and lf not in l['before']['consumed_feedback'] and rf not in r['before']['consumed_feedback'],
            'feedback ID 재사용/충돌')
    require(rf not in l['before']['consumed_feedback'] and lf not in r['before']['consumed_feedback'], 'ID 대응 충돌')
    matched_feedback = deepcopy(l['feedback'])
    matched_feedback.update(id=rf, decision_id=rd)
    require(matched_feedback == r['feedback'], 'feedback ID 외 내용 차이')
    matched, paths = _correspond(l['after'], ld, lf, rd, rf)
    require(not differences(matched, r['after']), '재시도 대조의 실제 memory 상태/이력 불일치')
    exact = l['after'] == r['after']
    return dict(contract='paired-first-error-provenance-v1', exact_document_equal=exact,
                execution_state_equal=True, provenance_correspondence_valid=True,
                before_document_equal=True, full_document_equal_after_correspondence=True,
                left_memory_sha256=sha(canonical(l['after'])), right_memory_sha256=sha(canonical(r['after'])),
                left_first_decision_id=ld, right_first_decision_id=rd,
                id_correspondence=dict(decision=[ld, rd], feedback=[lf, rf]),
                remapped_reference_paths=paths, raw_difference_paths=differences(l['after'], r['after']),
                excluded_fields=[], original_documents_modified=False,
                scope='첫 오류 전이의 ID 대응 포함 상태 동등성. direct/reload는 전체 문서·hash 동일성 검사 유지.')
