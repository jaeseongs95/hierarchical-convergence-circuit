#!/usr/bin/env python3
"""동결된 R0.2 capture에서 오류 상태·설명 근거 범위를 읽는다. 재추론·원인 확정은 하지 않는다."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path
import sys

# 캡처의 소스를 실행하지 않는다. 배포된 로컬 읽기 전용 수집기의 검사를 재사용한다.
_BASE = Path(__file__).resolve().parents[1] / 'r02_baseline' / 'collect.py'
_SPEC = importlib.util.spec_from_file_location('hcr_baseline_readonly', _BASE)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError('기존 tools/r02_baseline/collect.py가 필요하다')
baseline = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(baseline)
require = baseline.require

STATUSES = {'stable_decision', 'stable_ambiguous', 'oscillating', 'budget_exhausted',
            'no_candidate', 'unsupported'}
CAUSES = ('activation_failure', 'binding_failure', 'competition_failure',
          'over_compression', 'graph_expansion_failure')


def label_outcome(decision: dict, assessment: dict) -> dict:
    """관측 가능한 현상만 분류. 오답/보류에서 원인을 역으로 단정하지 않는다."""
    status = decision['convergence']['status']
    require(status in STATUSES, '알 수 없는 convergence 상태')
    value, correct = decision['value'], assessment['correct']
    require(value is None or type(value) is bool, 'value는 bool/None')
    require(correct is None or type(correct) is bool, 'correct는 bool/None')
    require(type(assessment['wrong_stable']) is bool and type(assessment['proof_valid']) is bool,
            'assessment bool 계약')
    require(not assessment['wrong_stable'] or (correct is False and status == 'stable_decision'),
            'stable wrong 판정 충돌')
    require((value is None) == (correct is None), '보류/correct 계약 충돌')
    labels = []
    if value is None:
        labels.append('abstention')
    if assessment['wrong_stable']:
        labels.append('misconvergence')
    if status == 'stable_ambiguous':
        labels.append('stable_ambiguous')
    if status == 'oscillating':
        labels.append('oscillation_observed')
    if status == 'budget_exhausted':
        labels.append('budget_boundary')
    if status == 'no_candidate':
        labels.append('no_candidate_observed')
    if status == 'unsupported':
        labels.append('unsupported_decision_prevented')
    if value is not None and not assessment['proof_valid']:
        labels.append('invalid_proof_reported')
    if value is not None and assessment.get('assumption_correct') is False:
        labels.append('assumption_reality_mismatch')
    return dict(convergence_status=status, correct=correct, observed_labels=labels,
                cause_status='not_identified_by_this_review',
                causes_not_diagnosed=list(CAUSES))


def explanation_observation(row: dict, events: list[dict]) -> dict:
    """정당화에 쓰인 가정과 당시 decision program의 포함 관계만 비교한다.

    모든 탐색 가지가 proof에 있어야 한다고 가정하지 않으며, signal graph를 proof DAG로 취급하지 않는다.
    """
    decision, obs = row['decision'], row['observation']
    did = decision['id']
    decisions = [e for e in events if e['event'] == 'r02_decision' and e['payload']['id'] == did]
    require(len(decisions) == 1, 'decision event 누락/중복')
    end = decisions[0]['seq']
    starts = [e for e in events if e['event'] == 'r02_attempt_started' and e['payload']['decision_id'] == did]
    require(len(starts) == 1 and starts[0]['seq'] < end, 'attempt event 누락/순서')
    require(starts[0]['payload']['observation'] == obs, 'attempt/row 관측 불일치')
    networks = [e for e in events if e['event'] == 'r02_network'
                and e['payload']['decision_id'] == did and e['payload']['kind'] == 'decision'
                and starts[0]['seq'] < e['seq'] < end]
    proof = decision['proof']
    names = [e['id'] for e in obs['edges']]
    require(len(names) == len(set(names)), '관측 edge ID 중복')
    assumptions = proof['assumed_edges']
    for item in assumptions:
        require(isinstance(item, (list, tuple)) and len(item) == 2 and type(item[1]) is bool,
                'proof assumption 계약')
    assumed_ids = {item[0] for item in assumptions}
    proof_paths = {tuple(p) for p in proof['paths']}
    program_paths = set()
    settled_seq = None
    if decision['program_digest'] is not None:
        require(bool(networks), '기록된 program 없음')
        network = networks[-1]['payload']
        require(network['program_digest'] == decision['program_digest'], '마지막 decision program digest 불일치')
        for path in network['program']['paths']:
            require(all(type(i) is int and 0 <= i < len(names) for i in path), 'program path index')
            program_paths.add(tuple(names[i] for i in path))
        settled = [e for e in events if e['event'] == 'r02_settled'
                   and e['payload']['network_id'] == network['network_id']
                   and networks[-1]['seq'] < e['seq'] < end]
        require(len(settled) == 1, 'settled event 누락/중복')
        settled_seq = settled[0]['seq']
    else:
        require(not networks, 'program 없는 판단에 decision network가 있음')
    program_edge_ids = {eid for path in program_paths for eid in path}
    positive_assumptions = sum(truth for _, truth in assumptions)
    return dict(decision_id=did, attempt_start_seq=starts[0]['seq'], last_settled_seq=settled_seq,
        bundled_decision_seq=end, separate_readout_event_recorded=False,
        separate_explanation_event_recorded=False, separate_latencies_measured=False,
        proof_node_count=len(proof['nodes']), primitive_proof_depth=proof['primitive_depth'],
        proof_reconstruction_items=decision['cost']['proof_nodes_reconstructed'],
        program_path_count=len(program_paths), proof_path_count=len(proof_paths),
        assumption_count=len(assumptions), positive_assumption_count=positive_assumptions,
        assumption_ids_outside_public_observation=sorted(assumed_ids - set(names)),
        assumption_ids_outside_last_program_paths=sorted(assumed_ids - program_edge_ids),
        proof_paths_outside_last_program=sorted(proof_paths - program_paths),
        inference_wall_seconds=decision['cost']['wall_seconds'],
        primitive_proof_revalidated=False, actual_causal_path_reconstructed=False,
        omitted_dependencies_diagnosed=False,
        interpretation='set containment / recorded provenance only; unused explored branches are not omitted proof premises')


def analyze_records(rows: list[dict], events: list[dict]) -> dict:
    require(len({r['decision']['id'] for r in rows}) == len(rows), '중복 decision 행')
    by_decision = defaultdict(list)
    for event in events:
        payload = event['payload']
        did = payload.get('decision_id')
        if event['event'] == 'r02_decision':
            did = payload['id']
        if did:
            by_decision[did].append(event)
    records, groups = [], defaultdict(Counter)
    for row in rows:
        decision = row['decision']
        labels = label_outcome(decision, row['assessment'])
        explanation = explanation_observation(row, by_decision[decision['id']])
        group = row['phase'] + '/' + row['arm']
        groups[group].update(labels['observed_labels'])
        record = dict(phase=row['phase'], arm=row['arm'], case=row['case'],
                      attempt=decision['attempt'], **explanation, **labels)
        records.append(record)
    return dict(schema='hcr-r02-concept-run-review-v1', records=records,
                group_observed_labels={k: dict(v) for k, v in sorted(groups.items())},
                boundaries=dict(inference_executed=False, project_source_imported=False,
                    numerical_audit_executed=False, proof_revalidated=False,
                    causal_explanation_verified=False, new_research_samples=0),
                limitations=['정당화 포함 관계와 기록 상태를 읽는다. 독립 numerical audit를 대체하지 않는다.',
                    'R0.2에는 독립 readout/explanation 이벤트·개별 시간값이 없다. 과거 기록에 추가하지 않는다.',
                    'no_candidate는 activation failure, 오답은 over-compression의 확정 근거가 아니다.',
                    '현상 분류는 중첩 가능하므로 label 합계는 고유 실패 수가 아니다.'])


def render(report: dict) -> str:
    lines = ['# R0.2 개념 대응 / 실행 기록 관찰', '',
             '이 보고서는 기존 capture의 재분석이며 새 추론 표본·원인 규명·독립 수치 검산이 아니다.', '',
             '| 조건 | 판단 | 시도 | 수렴 상태 | 정답 | 관측 label | proof D |',
             '|---|---|---:|---|---|---|---:|']
    for r in report['records']:
        lines.append(f"| {r['phase']}/{r['arm']} | {r['decision_id']} | {r['attempt']} | "
                     f"{r['convergence_status']} | {r['correct']} | {', '.join(r['observed_labels'])} | "
                     f"{r['primitive_proof_depth']} |")
    lines += ['', '## 설명 비교의 범위', '',
              'review.json에서 assumption_ids_outside_public_observation, '
              'assumption_ids_outside_last_program_paths, proof_paths_outside_last_program을 확인한다. '
              '공집합은 포함 관계에 이상이 없다는 뜻이며 설명이 실제 원인 경로와 동일하다는 증명이 아니다.', '',
              *['- ' + item for item in report['limitations']], '']
    return '\n'.join(lines)


def review(capture: Path, out: Path) -> dict:
    require(not baseline.linked(capture) and not baseline.linked(out), '입출력 루트 링크 거부')
    for path in (capture, out):
        require(all(not baseline.linked(p) for p in path.absolute().parents), '상위 링크/junction 거부')
    capture, out = capture.resolve(), out.resolve()
    repo = Path(__file__).resolve().parents[2]
    require(not out.exists() and not out.is_relative_to(capture) and not out.is_relative_to(repo),
            '출력은 저장소/capture 밖의 새 폴더여야 한다')
    manifest = baseline.verify_bundle(capture)
    manifest_hash = baseline.sha(baseline.read(capture / 'bundle_manifest.json'))
    data = baseline.examine(capture / 'run', capture / 'source')
    report = analyze_records(data['rows'], data['events'])
    # 읽는 동안 원본이 바뀌었는지 다시 확인한다.
    require(baseline.verify_bundle(capture) == manifest
            and baseline.sha(baseline.read(capture / 'bundle_manifest.json')) == manifest_hash,
            '검토 중 capture 변경')
    report['input'] = dict(capture_manifest_sha256=manifest_hash,
        source_plan_sha256=baseline.sha(data['run_bytes']['plan.json']),
        run_manifest_sha256=baseline.sha(data['run_bytes']['manifest.json']))
    out.mkdir(parents=True, exist_ok=False)
    try:
        baseline.write_json(out / 'review.json', report)
        with (out / 'review.ko.md').open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(render(report))
        receipt = dict(schema='hcr-r02-concept-review-receipt-v1', state='complete',
            records=len(report['records']), original_capture_modified=False,
            inference_executed=False, numerical_audit_executed=False,
            capture_integrity_checked=True, **report['input'])
        baseline.write_json(out / 'receipt.json', receipt)
        baseline.write_json(out / 'manifest.json', dict(schema='hcr-concept-review-files-v1',
            state='complete', files={p.name: baseline.sha(baseline.read(p)) for p in sorted(out.iterdir()) if p.is_file()}))
        return dict(output=str(out), **receipt)
    except BaseException as error:
        if not (out / 'FAILED.json').exists():
            baseline.write_json(out / 'FAILED.json', dict(state='failed', error=str(error)))
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(review(args.capture, args.out), ensure_ascii=False, indent=2))
        return 0
    except (baseline.BaselineError, OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps(dict(state='failed', error=str(error)), ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
