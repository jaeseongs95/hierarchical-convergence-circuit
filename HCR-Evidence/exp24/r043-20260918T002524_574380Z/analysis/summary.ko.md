# EXP-24 / R043 — input_order ID 재명명 음성대조

## 결론

관찰 분류: `no_ID_effect_detected_in_input_order_measured_cost_and_trajectory`.
동일 순열의 ID pair 예측 지지 6/6, 예측 실패 0/6, 측정 불충분 0/6.
보조 측정에서 차이가 검출된 pair: 0/6.
audit 통과는 실행·측정 계약의 검산이며, ID 불변성의 성공 조건이 아니다.

## 관찰

| 배열 순서 | 기존 ID ticks | 재명명 ticks | 차이 | readout 궤적 동일 |
|---|---:|---:|---:|---|
| SMD | 102 | 102 | 0 | True |
| SDM | 102 | 102 | 0 | True |
| MSD | 102 | 102 | 0 | True |
| MDS | 170 | 170 | 0 | True |
| DSM | 170 | 170 | 0 | True |
| DMS | 170 | 170 | 0 | True |

## 해석

기존 EXP-23의 min/max ID-key 개입과 달리, 기존 input_order는 frontier의 첫 slot을 고른다.
선택 결정에 ID 순위를 사용하지 않지만, 입력 검증·로그용 ID 읽기는 그대로 존재한다.
같은 순열의 재명명 전후를 비교한다. 서로 다른 배열 순열 사이의 tick 불변성은 예측하지 않는다.

## 대안 설명

차이가 남으면 ID ranking 밖의 ID 의존성·참조 처리·투영 범위를 점검한다. 그 중 하나를 자동으로 원인으로 확정하지 않는다.
차이가 없으면 측정된 조건·투영에서 ID 효과가 검출되지 않았다는 뜻이다. 전체 내부 상태의 ID 독립성을 증명한 것은 아니다.

## 판별 실험

차이가 나타난 pair의 first_readout_difference 및 raw를 먼저 재생한다. 판정 전 topology나 scheduler를 추가하지 않는다.

## 현재 주장 가능한 범위

고정 toy topology 1개, ID 배치 2개, 배열 순열 6개, input_order 1개의 12조건(6쌍). LLM 실험이 아니다.
EXP-22 동일 입력 input_order 회귀 6/6. 이 재검산과 EXP-23 기존 결과는 신규 독립 증거로 합산하지 않는다.
D_DAG, native ticks, scheduler/selector 작업, wall time을 구분한다. 에너지와 프로세스 peak memory는 null이다.
최종 지원 signature(value, D_DAG, assumptions)와 완성 경로 목록은 별도다. 최소 goal proof DAG 동치는 측정하지 않아 null로 둔다.
native raw의 legacy wall_seconds placeholder는 실제 측정 시간과 별도 표기하고 비용 비교에서 제외한다.
오답·abstention은 결과로 보존한다. schema/reference/runtime/audit 실패는 최초 실패와 부분 evidence를 남긴다.
