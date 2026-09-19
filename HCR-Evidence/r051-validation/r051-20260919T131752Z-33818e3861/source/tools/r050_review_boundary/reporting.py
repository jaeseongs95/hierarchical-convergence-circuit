"""Render only independently audited records; do not score producer summaries."""
from __future__ import annotations
from collections import Counter
import argparse
import csv
import io
from pathlib import Path
from .common import dump, load, publish, require


def render_artifacts(audit: dict) -> tuple[dict, dict[str, bytes]]:
    """Render an audited record without modifying any run or invoking inference."""
    require(audit.get('verified') is True and audit['baseline_count'] == 24 and audit['arm_records'] == 96,
            'A complete independent audit is required before reporting')
    from .analysis_contract import validate_audit_tables
    validate_audit_tables(audit)
    groups = {}
    rows = audit['rows']
    for arm in ('hold','same_input_restart','echo_revision_restart','strength_revision_restart'):
        selected = [r for r in rows if r['arm'] == arm]
        counts = Counter()
        for r in selected:
            counts['correct_adoptions'] += r['final']['adopted_correct'] is True
            counts['incorrect_adoptions'] += r['final']['adopted_correct'] is False
            counts['abstentions'] += not r['final']['accepted']
            counts['restarts'] += r['restarts']
            counts['probe_requests'] += r['probe_requests']
            counts['additional_kernel_ticks'] += r['additional_counters']['kernel_ticks']
            counts['additional_signal_transmissions'] += r['additional_counters']['signal_transmissions']
        groups[arm] = dict(counts)
    native = Counter()
    for r in rows:
        if r['arm'] == 'hold':
            native[r['native_observe_first_next_action']['action']] += 1
    pairs = []
    by_key = {(r['case_id'],r['arm']):r for r in rows}
    for case in sorted({r['case_id'] for r in rows}):
        echo = by_key[case,'echo_revision_restart']
        strengthened = by_key[case,'strength_revision_restart']
        pairs.append(dict(case_id=case, paired_probe_executed=echo['probe_requests']==strengthened['probe_requests']==1,
                     echo_adopted_correct=echo['final']['adopted_correct'],
                     strength_adopted_correct=strengthened['final']['adopted_correct'],
                     changed_adopted_output=echo['final']['adopted_value'] != strengthened['final']['adopted_value'],
                     echo_failure_class=echo['final']['failure_class'],
                     strength_failure_class=strengthened['final']['failure_class']))
    numeric_groups = {}
    for prediction in ('P1','P2','P3'):
        selected = [x for x in audit['numerical_comparisons'] if x['prediction'] == prediction]
        numeric_groups[prediction] = dict(
            applicable=sum(x['evaluated'] for x in selected),
            not_applicable=sum(not x['evaluated'] for x in selected),
            final_state_close=sum(x['evaluated'] and x['comparison']['final_state_close'] is True for x in selected),
            final_state_different=sum(x['evaluated'] and x['comparison']['final_state_close'] is False for x in selected),
            final_state_unmeasured=sum(x['evaluated'] and x['comparison']['final_state_close'] is None for x in selected),
            trajectory_close=sum(x['evaluated'] and x['comparison']['trajectory_close'] is True for x in selected),
            trajectory_different=sum(x['evaluated'] and x['comparison']['trajectory_close'] is False for x in selected),
            trajectory_unmeasured=sum(x['evaluated'] and x['comparison']['trajectory_close'] is None for x in selected))
    summary = dict(schema='hcc-r050-summary-v1', verified=True, baselines=24, paired_arm_records=96,
                   groups=groups, native_next_action_counts=dict(native), strength_vs_echo=pairs,
                   numeric_predictions=numeric_groups,numerical_comparisons=audit['numerical_comparisons'],
                   unique_baseline_counters=audit['unique_baseline_counters'],
                   baseline_probe_selector_slots_inspected=sum(r['probe_target']['slots_inspected'] for r in rows if r['arm']=='hold'),
                   additional_counters=audit['additional_counters'],
                   inference_success_is_not_a_validation_requirement=True,
                   score_strength_intervention_not_independent_sensor_evidence=True,
                   learning_and_state_reuse_tested=False, actual_energy_joules=None)
    flat=[]
    for r in rows:
        flat.append(dict(case_id=r['case_id'],arm=r['arm'],strength=r['strength'],relation=r['relation'],
                    identity_variant=r['identity_variant'],top_down=r['top_down'],
                    initial_raw=r['initial']['raw_decision'],initial_pending_value=r['initial']['pending_value'],
                    initial_numeric_goal_side=r['initial']['numeric_goal_side'],
                    initial_failure_class=r['initial']['failure_class'],initial_adopted_value=r['initial']['adopted_value'],
                    initial_internal_edge_conflicts=r['initial']['internal_edge_conflicts'],
                    final_raw=r['final']['raw_decision'],final_pending_value=r['final']['pending_value'],
                    final_numeric_goal_side=r['final']['numeric_goal_side'],
                    convergence_status=r['final']['convergence_status'],native_failure_reason=r['final']['native_failure_reason'],
                    adopted_value=r['final']['adopted_value'],
                    adopted_correct=r['final']['adopted_correct'],failure_class=r['final']['failure_class'],
                    internal_edge_conflicts=r['final']['internal_edge_conflicts'],D_DAG=r['final']['D_DAG'],
                    restarts=r['restarts'],probe_requests=r['probe_requests'],
                    target_edge=r['probe_target']['edge_id'],target_slot=r['probe_target']['slot'],
                    target_selection_slots_inspected=r['probe_target']['slots_inspected'],
                    target_selection_reason=r['probe_target']['reason'],
                    extra_ticks=r['additional_counters']['kernel_ticks'],
                    extra_signal_transmissions=r['additional_counters']['signal_transmissions'],
                    extra_proof_nodes=r['additional_counters']['proof_nodes_reconstructed'],
                    stop_reason=r['stop_reason'],arm_wall_seconds=r['arm_wall_seconds'],
                    actual_energy_joules=None,measured_process_memory_bytes=None,raw_path=r['raw_path']))
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=list(flat[0]))
    writer.writeheader()
    writer.writerows(flat)
    csv_bytes = stream.getvalue().encode('utf-8-sig')
    lines=['# EXP-31 / R050 — 재검토 경계 판별 실험','',
           '## 결론','',
           '원자료의 독립 검산을 통과했다. 정답 증가 여부는 아래 결과이며, 검산 통과 자체가 가설 성공을 뜻하지 않는다.',
           '실제 AdaptiveSession 24개 기준선에서 4개 개입 기록을 분기했다. 96개를 독립 표본으로 세지 않는다.',
           '관측 개입은 기존 공개 score의 부호를 보존하고 강도 하나를 1로 바꾼 조작이다. 독립 센서에서 새 정보를 얻은 실험이 아니다.','',
           '## 관찰','',
           '| 개입 | 정답 채택 | 오답 채택 | 보류 | 재시작 | probe 요청 | 추가 ticks | 추가 signal transmissions |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,g in groups.items():
        lines.append(f"| {name} | {g['correct_adoptions']} | {g['incorrect_adoptions']} | {g['abstentions']} | {g['restarts']} | {g['probe_requests']} | {g['additional_kernel_ticks']} | {g['additional_signal_transmissions']} |")
    lines += ['', '## 사전 예측의 수치·궤적 비교', '',
              '| 예측 | 비교 실행 | 미실행 | 최종 상태 같음/다름/측정불가 | 궤적 같음/다름/측정불가 |',
              '|---|---:|---:|---|---|']
    for name,g in numeric_groups.items():
        lines.append(f"| {name} | {g['applicable']} | {g['not_applicable']} | {g['final_state_close']}/{g['final_state_different']}/{g['final_state_unmeasured']} | {g['trajectory_close']}/{g['trajectory_different']}/{g['trajectory_unmeasured']} |")
    lines += ['', 'P1=최초 실행 대 동일 입력 재시작, P2=동일 입력 재시작 대 echo/revision 대조, P3=echo 대 강도 조작이다.',
              '관련 재시작이 실제 실행되지 않은 조건은 비교 미실행으로 남긴다. 이를 같음이나 성공으로 세지 않는다.',
              '최종 상태와 tick별 궤적은 abs_tol/rel_tol=1e-12로 별도 비교한다. 종료 tick 수나 network 구조가 다르면 궤적 차이로 기록한다.',
              '예측과 다른 수치가 나와도 개입·원자료 계약이 지켜졌다면 audit failure로 바꾸지 않는다.','']
    lines += ['', '공유 기준선의 native ticks 합계: '+str(audit['unique_baseline_counters']['kernel_ticks']),
              '추가 실행의 native ticks 합계: '+str(audit['additional_counters']['kernel_ticks']),
              '위 값은 같은 단위끼리만 합산했다. wall time·에너지·D_DAG를 이 값과 합치지 않는다.','',
              '## 기존 관측 선택기의 다음 action','']
    lines += [f'- `{key}`: {value}개 기준선' for key,value in sorted(native.items())]
    lines += ['', '이는 기존 choose_action의 다음 action을 실행 없이 진단한 기록이다. 전체 native ReviewFlow rollout을 수행했다는 뜻이 아니다.','',
              '## 해석과 대안 설명','',
              '`hold → same_input_restart`는 새 입력 없이 재계산한 차이를 본다. `same_input_restart → echo_revision_restart`는 요청 및 revision-only metadata 개입을 분리한다.',
              '`echo_revision_restart → strength_revision_restart`는 같은 대상·revision·초기화·top-down 설정에서 score 강도 하나의 차이를 본다.',
              '선택한 edge 하나만 조작하며, 실패했다고 두 번째 edge를 자동 조작하거나 예산을 늘리지 않는다.',
              '내부 edge 부호 정합성, pre-proof pending value, 원 decision, proof 지지, terminal adoption은 별도 기록했다.',
              '동일 입력의 재계산과 revision control에서 차이가 발견되면 identity/metadata 경로의 영향도 함께 검토해야 한다.','',
              '## 현재 주장 가능한 범위','',
              '학습·회로 재사용·상태 보존형 재검토·남은 frontier의 Graph 재확장·LLM 성능·전력 효율은 이 실험의 측정 대상이 아니다.',
              '낮은 관측 강도에서 해당 실패가 실제 session에서도 재현됐는지는 trials.csv의 initial 항목으로 판단한다. EXP-30 상태를 이식하지 않았다.',
              '오류가 수정되지 않거나 native selector가 관측 대상을 찾지 못하는 결과도 그대로 보존한다.','',
              '## 다음 판별 실험','',
              '이번 1회 강도 조작의 결과를 먼저 검토한다. 이후 측정 횟수·독립 센서·상태 보존을 확장하려면 별도 조건 동결이 필요하다.','']
    from .common import canonical
    return summary, {'summary.json': canonical(summary) + b'\n',
                     'trials.csv': csv_bytes, 'summary.ko.md': '\n'.join(lines).encode('utf-8')}


def create(root: Path) -> dict:
    audit = load(root / 'analysis' / 'audit.json')
    from .analysis_contract import validate_report_inputs
    validate_report_inputs(root, audit)
    summary, artifacts = render_artifacts(audit)
    for name, content in artifacts.items():
        publish(root / 'analysis' / name, content)
    return summary


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--run',required=True,type=Path)
    a=p.parse_args(argv)
    create(a.run)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
