# EXP-31 / R050 — 재검토 경계 판별 실험

## 결론

원자료의 독립 검산을 통과했다. 정답 증가 여부는 아래 결과이며, 검산 통과 자체가 가설 성공을 뜻하지 않는다.
실제 AdaptiveSession 24개 기준선에서 4개 개입 기록을 분기했다. 96개를 독립 표본으로 세지 않는다.
관측 개입은 기존 공개 score의 부호를 보존하고 강도 하나를 1로 바꾼 조작이다. 독립 센서에서 새 정보를 얻은 실험이 아니다.

## 관찰

| 개입 | 정답 채택 | 오답 채택 | 보류 | 재시작 | probe 요청 | 추가 ticks | 추가 signal transmissions |
|---|---:|---:|---:|---:|---:|---:|---:|
| hold | 20 | 0 | 4 | 0 | 0 | 0 | 0 |
| same_input_restart | 20 | 0 | 4 | 4 | 0 | 250 | 1704 |
| echo_revision_restart | 20 | 0 | 4 | 4 | 4 | 250 | 1704 |
| strength_revision_restart | 22 | 0 | 2 | 4 | 4 | 326 | 2232 |

## 사전 예측의 수치·궤적 비교

| 예측 | 비교 실행 | 미실행 | 최종 상태 같음/다름/측정불가 | 궤적 같음/다름/측정불가 |
|---|---:|---:|---|---|
| P1 | 4 | 20 | 4/0/0 | 4/0/0 |
| P2 | 4 | 20 | 4/0/0 | 4/0/0 |
| P3 | 4 | 20 | 0/4/0 | 0/4/0 |

P1=최초 실행 대 동일 입력 재시작, P2=동일 입력 재시작 대 echo/revision 대조, P3=echo 대 강도 조작이다.
관련 재시작이 실제 실행되지 않은 조건은 비교 미실행으로 남긴다. 이를 같음이나 성공으로 세지 않는다.
최종 상태와 tick별 궤적은 abs_tol/rel_tol=1e-12로 별도 비교한다. 종료 tick 수나 network 구조가 다르면 궤적 차이로 기록한다.
예측과 다른 수치가 나와도 개입·원자료 계약이 지켜졌다면 audit failure로 바꾸지 않는다.


공유 기준선의 native ticks 합계: 1098
추가 실행의 native ticks 합계: 826
위 값은 같은 단위끼리만 합산했다. wall time·에너지·D_DAG를 이 값과 합치지 않는다.

## 기존 관측 선택기의 다음 action

- `stop_no_measurement_target`: 4개 기준선
- `stop_supported`: 20개 기준선

이는 기존 choose_action의 다음 action을 실행 없이 진단한 기록이다. 전체 native ReviewFlow rollout을 수행했다는 뜻이 아니다.

## 해석과 대안 설명

`hold → same_input_restart`는 새 입력 없이 재계산한 차이를 본다. `same_input_restart → echo_revision_restart`는 요청 및 revision-only metadata 개입을 분리한다.
`echo_revision_restart → strength_revision_restart`는 같은 대상·revision·초기화·top-down 설정에서 score 강도 하나의 차이를 본다.
선택한 edge 하나만 조작하며, 실패했다고 두 번째 edge를 자동 조작하거나 예산을 늘리지 않는다.
내부 edge 부호 정합성, pre-proof pending value, 원 decision, proof 지지, terminal adoption은 별도 기록했다.
동일 입력의 재계산과 revision control에서 차이가 발견되면 identity/metadata 경로의 영향도 함께 검토해야 한다.

## 현재 주장 가능한 범위

학습·회로 재사용·상태 보존형 재검토·남은 frontier의 Graph 재확장·LLM 성능·전력 효율은 이 실험의 측정 대상이 아니다.
낮은 관측 강도에서 해당 실패가 실제 session에서도 재현됐는지는 trials.csv의 initial 항목으로 판단한다. EXP-30 상태를 이식하지 않았다.
오류가 수정되지 않거나 native selector가 관측 대상을 찾지 못하는 결과도 그대로 보존한다.

## 다음 판별 실험

이번 1회 강도 조작의 결과를 먼저 검토한다. 이후 측정 횟수·독립 센서·상태 보존을 확장하려면 별도 조건 동결이 필요하다.
