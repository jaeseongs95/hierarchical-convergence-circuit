# EXP-09 요약 오류 복구 보고서

원본은 실패 상태로 보존했다. 다음은 이미 기록된 추론의 재집계·검산이며 새 추론이 아니다.

기준 capture 재검사: True. False인 경우 초기 조건은 원시 기록 내부의 대응만 검사했다.
과거 초기화·save/load 시간이 남지 않았으면 null로 두며 0으로 대체하지 않는다.

# EXP-09 r2 — 재오답 원인분리와 비용 분해

이 파일의 수치는 실제 실행 후 생성된다. 과거 run이나 가설의 증명으로 대체하지 않는다.

## 저장·복원
- memory 문서 동등: True
- 행동 동등(ID·시간만 제외): True
- direct/reload 정답: [False, False]

둘 다 오답이면서 동등할 수 있다. 이는 해당 대조에서 직렬화가 행동 차이를 만들지 않았다는 뜻이다.

## memory × 입력 정보 × 회로 사용
| 조건 | 출력 | 정답 | 회로 |
|---|---|---|---|
| before/weak/circuits | True | False | pattern-ac8909863fce4682a84bf769 |
| before/weak/graph_only | False | True |  |
| before/measured/circuits | False | True | pattern-d7053e8a62ed20d50b15444c |
| before/measured/graph_only | False | True |  |
| after/weak/circuits | True | False | pattern-d7053e8a62ed20d50b15444c |
| after/weak/graph_only | False | True |  |
| after/measured/circuits | False | True | pattern-d7053e8a62ed20d50b15444c |
| after/measured/graph_only | False | True |  |

## 동일 점수 재시도 / 정밀 측정 재시도
```json
{
  "available": true,
  "same_score_correct": true,
  "measured_correct": true,
  "same_score_output": false,
  "measured_output": false,
  "extra_measurement_needed_in_this_pair": false,
  "same_score_revision_id": "r02-d-1056-4c72b323eb06decf",
  "measured_revision_id": "r02-d-92-725307a6055bdd61",
  "memory_equal_at_revision": false,
  "memory_execution_state_equal": true,
  "provenance_correspondence_valid": true,
  "memory_comparison": {
    "contract": "paired-first-error-provenance-v1",
    "exact_document_equal": false,
    "execution_state_equal": true,
    "provenance_correspondence_valid": true,
    "before_document_equal": true,
    "full_document_equal_after_correspondence": true,
    "left_memory_sha256": "25bdbbeb75306d690f631137fbe0c7b72c83bf843c4128623993d2b0705eaddd",
    "right_memory_sha256": "6d8ddd8dd3da7ff05f0dfa31de27a145df81c262e50abd1c4bec18c142ee791c",
    "left_first_decision_id": "r02-d-965-7efe62384f814d1e",
    "right_first_decision_id": "r02-d-1-7efe62384f814d1e",
    "id_correspondence": {
      "decision": [
        "r02-d-965-7efe62384f814d1e",
        "r02-d-1-7efe62384f814d1e"
      ],
      "feedback": [
        "f-r02-d-965-7efe62384f814d1e",
        "f-r02-d-1-7efe62384f814d1e"
      ]
    },
    "remapped_reference_paths": [
      "/circuits/1/feedback_ids/6",
      "/consumed_feedback/6",
      "/patches/6/decision_id",
      "/patches/6/feedback_id"
    ],
    "raw_difference_paths": [
      "/circuits/1/feedback_ids/6",
      "/consumed_feedback/6",
      "/patches/6/decision_id",
      "/patches/6/feedback_id"
    ],
    "excluded_fields": [],
    "original_documents_modified": false,
    "scope": "첫 오류 전이의 ID 대응 포함 상태 동등성. direct/reload는 전체 문서·hash 동일성 검사 유지."
  },
  "circuits_disabled_in_both": true,
  "caveat": "동일 점수 revision은 추가 정보 없는 공개 입력 대조다. 실제 정밀 측정으로 보고하지 않는다."
}
```

## 비용 — 같은 학습 memory에서 회로 사용만 변경
| 사례 | 반복 쌍 | graph 중앙값(ms) | circuit 중앙값(ms) | 쌍 차이 중앙값(ms) | 카운터 차이 일정 |
|---|---:|---:|---:|---:|---|
| branched_composition | 4 | 3.076 | 9.604 | 6.574 | True |
| counterfactual | 4 | 2.974 | 13.371 | 10.381 | True |
| longer_composition | 4 | 4.183 | 15.233 | 11.027 | True |
| renamed_reordered | 4 | 3.382 | 10.654 | 7.246 | True |
| same_structure | 4 | 3.395 | 10.409 | 7.040 | True |

## 재시도·학습 횟수별 경로
| 조건 | 시도 | 최초/최종 정답 | 추론 tick | 학습 update |
|---|---:|---|---:|---:|
| measured_replay | 2 | False/True | 103 | 2 |
| same_score_control | 2 | False/True | 114 | 2 |
| training_3 | 2 | False/True | 120 | 2 |
| training_6 | 2 | False/True | 103 | 2 |
| training_9 | 2 | False/True | 100 | 2 |

pool_ticks/pool_signals는 전체 tick/signal의 내역이다. 전체에 다시 더하지 않는다.
반복 실행은 새 독립 과제가 아니다. 각 실행의 원시 비용은 costs.csv, 짝 차이는 summary.json에 있다.

## 학습의 실제 범위
feedback_changes.json에서 변화 이력과 회로 내용 변화를 별도로 확인한다.
현재 학습기는 참인 검증 경로만 컴파일한다. 거짓 출력의 정답은 음의 예외회로로 자동 저장되지 않는다.
candidate_trace.json의 failures/strength/적용 binding을 통해 약화한 회로와 다른 후보의 재사용을 구분한다.
동반된 회로 선택만으로 특정 회로가 재오답의 유일한 원인이라고 판정하지 않는다.

## 다음 단계
이 대조 결과를 기준선에 기록한 후 R0.2.1 snapshot/restore/resume으로 이어간다.
negative exception memory, credit assignment 변경, pool 최적화는 별도 개입으로 비교해야 한다.
