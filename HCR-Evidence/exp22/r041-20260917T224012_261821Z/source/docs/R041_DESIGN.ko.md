# EXP-22 / R0.4.1 — 순열 불변성과 계산 효율의 분리

## 1. 출발점

코드 기준선은 `37bb3c19f27dfbd73de7519fc8cad399395bcf3a`이다. 기준 evidence는
`HCR-Evidence/exp21/r040-20260917T204742_957648Z`다.
EXP-21의 `analysis/mediation.csv`, `scheduler_contrasts.csv`, `scheduler_decisions.csv`와
`analysis/records/t0038.json`은 입력 배열을 유지하고 frontier head만 ID 최소값 기준으로 선택했을 때
기존 순열별 경로 차이와 native ticks 격차가 제거된 결과를 담는다.
그 결과는 기존 실험의 근거이며 신규 EXP-22 관찰로 다시 세지 않는다.

기존 해석에서 남은 질문은 두 가지다. 고정된 처리 기준이 입력 순서 의존성을 줄인 것과,
그 고정 기준이 현재 ID 배치에서 우연히 지지 경로를 앞세운 것은 서로 다른 성질인가?
이를 구별하기 위해 `edge_id_max` 역방향 대조를 추가한다.

## 2. 조작과 고정 조건

| 변수 | 이번 설정 |
|---|---|
| scheduler | `input_order`, `edge_id_min`, `edge_id_max` |
| 입력 배열 | EXP-20/21의 SMD, SDM, MSD, MDS, DSM, DMS 6개 그대로 |
| prior | `legacy`, `route_only` |
| 채택 방식 | `native`, `posthoc_support`, `online_support` |
| 고정 | topology, node/edge/episode ID, revision, score, world, 학습 memory, config, 계산/선택 예산 |

6 순열 × 2 prior × 3 채택 방식 × 3 scheduler = 108회 fresh native 실행이다.
이 중 기존 input_order/edge_id_min의 72회는 EXP-21 원자료와 직접 회귀 비교한다.
새 edge_id_max의 36회는 별도 intervention 조건이다.
한 topology를 재배치한 조건들이므로 독립적인 108개 문제로 세지 않는다.

S는 지지 분기 e0→e1, M은 관측 누락 분기 e2→e3, D는 음의 관측 포함 분기 e4→e5→e6이다.
이 표기는 입력의 평가용 라벨이며 A/D/M 연구 축의 D·M을 뜻하지 않는다.
라벨은 scheduler나 native 실행에 전달하지 않는다.

## 3. 생산 실행 경계

기존 R037의 OnlineTrial 제어 loop, R038의 사후 채택 wrapper, R035 selector를 재사용한다.
새 R041 모듈은 R040을 기준으로 버전이 명시된 scheduling/검산 외피를 추가한다.
기존 R040 이하 파일은 수정하지 않는다.

```
기존 종료·예산 검사
→ 실제 advance가 가능한 running 경계
→ 공개 edge ID 목록 + 이미 등록된 frontier_paths만 투영
→ input_order: 기존 head
   edge_id_min: ID 경로 tuple의 사전식 최소값
   edge_id_max: ID 경로 tuple의 사전식 최대값
→ 선택 항목이 이미 head면 API 이동 없음
→ 다를 때만 AdaptiveSession.prioritize_frontier(path)
→ 기존 native advance / readout / proof 선택 / 채택 경계
```

입력 자체의 정렬이나 전체 frontier의 선행 정렬이 아니다. 다음 head 하나를 정한다.
새 경로를 생성하거나 hidden world를 검사하지 않는다. 점수, raw 값, case/분기 라벨,
외부 정답을 scheduler에 넘기지 않는다. ID/parent/dependency 자동 교정은 없다.
최초 root frontier가 하나인 시점의 후보 pool 정책은 변경하지 않는다.

같은 관측/prior에는 arm/scheduler에 무관한 기존 session identity 규칙을 유지한다.
입력 순열에 따라 자연스럽게 달라지는 slot/hash를 host가 다시 고정하지 않는다.
각 trial은 동일한 동결 학습 memory의 복사본으로 시작하며 trial 사이에 학습하지 않는다.
9개 scheduler×arm 조합의 실행 순서는 순열/prior에 따라 순환 배치하며 계획에 동결한다.

## 4. 사전 예측과 대안

**주 예측:** min과 max는 모두 배열 순서 의존성을 줄일 수 있지만, 두 고정 정책의 평균 비용은
서로 다를 수 있다. 현재 ID 배치에서 M 이후 S를 앞세우는 min과 D를 앞세우는 max가 각각
동일하게 빠른 순서와 동일하게 느린 순서를 만들 가능성을 시험한다.
이는 예측이며 원자료의 결과나 통과 기준에 미리 넣지 않는다.

**결합 예측:** scheduling으로 지지 proof를 빨리 확보하더라도 native가 그 proof를 선택하지
못하면 보류가 남을 수 있다. 사후 선택은 실행이 끝난 뒤에만 적용되므로 이미 쓴 계산을
되돌려 절약한 것으로 세지 않는다. 온라인 선택은 실제 생략한 뒤쪽 계산만 절감으로 센다.

**대안 결과:** max가 더 빠르거나 같은 비용일 수 있고, 어느 고정 정책에서든 순열별 격차가
남을 수 있다. 원자료·계약이 유효하면 그대로 보고한다. 정답·불변성·개선·비용 차이의 부호는
검증의 합격 조건이 아니다. 기회가 발생하지 않은 조건도 누락하지 않는다.

이 실험이 구별하는 순열 불변성은 여섯 배열에서의 경로/비용 변동이다. 동역학적 수렴,
반복 시도의 안정성, 정확도, revisability와 동일한 지표로 사용하지 않는다.

## 5. 측정

1. 최초 native 판단, 각 실제 readout, 마지막 사용 가능 readout, terminal adoption을 분리한다.
2. ID로 대응한 경로 완성 순서, S 완성 순위, 지지·activation 적격 경로 출현 시점,
   남은 frontier와 차등 기회 시점을 기록한다.
3. 같은 scheduler 안의 native/사후/온라인 비교와 같은 arm 안의 scheduler 간 비교를 분리한다.
4. `invariance_efficiency.csv`에서 min/max의 순열별 ticks 범위 폭, 경로/궤적 불변성,
   최종 결과 일치, 각 평균/합계 ticks와 signed difference를 별도 열로 기록한다.
5. 원 proof와 새 proof의 D_DAG·가정을 기록하되, D축 조작 실험으로 분류하지 않는다.

`scheduler_contrasts.csv`는 input→min, input→max, min→max의 3종 비교이며
`tick_difference_left_minus_right`의 양수는 오른쪽 정책이 native ticks를 덜 사용한 뜻이다.
`invariance_efficiency.csv`의 `max_minus_min_total_native_ticks`는 반대 표기다.
양수면 max가 더 많이 계산했다는 뜻이다. 각 필드명과 방향을 해석에서 유지한다.

Native ticks는 최종 누적값을 trial당 한 번만 센다. 스케줄러의 frontier 검사·ID 조회·tuple
비교·priority 전이·native API 경로 일치 검사 수를 별도 inventory로 보존한다.
Selector의 경로/edge 검사, proof 생성/재사용과 native finish proof 생성도 분리한다.
단위가 다른 값을 총비용으로 더하지 않는다. 미계측 scan은 null이며 0이 아니다.
Wall time에는 보존·직렬화 비용이 섞여 있으므로 전력·전체 실행 속도 우위로 일반화하지 않는다.

## 6. 독립 검산과 회귀

생산 scheduler는 선형 순회로 극값을 선택한다. 별도 `schedule_audit.py`는 정렬 명세로
선택 head를 재계산하며 생산 project/choose/run 함수를 호출하지 않는다.
Priority 전후에는 frontier의 지정 항목 이동 외에 어떤 상태도 달라지지 않았는지 전체 비교한다.
Native packet과 finish fork는 기존 독립 state/event auditor를 사용하고,
proof·D_DAG·가정·선택 비용은 기존 R035 독립 auditor를 사용한다.
기존 supported_assumptions 보고 오류는 R038의 검사/지지/비지지 분리로 보정된 지표를 유지한다.

기존 두 scheduler의 72개 trial은 EXP-21 raw와 native 사건 의미, readout view, 선택 결과,
채택·종료 이유, selector 비용, scheduler 결정·비용을 비교한다.
벽시계 값과 버전이 명시된 외피 schema에서 달라지는 봉인값만 직접 동일성에서 제외한다.
이 제외를 ID/경로/activation/계산 변경을 덮는 일반 정규화로 사용하지 않는다.

6개 입력 순열은 생산 generator와 별도 명세로 대조하며 관측/world/ID의 대응을 검산한다.
생산 runtime에는 평가 world나 기회 판정 함수가 전달되지 않는다.
Native self-test와 본 실험 evidence는 분리한다. self-test에서 신규 6개 순열을 사전 선별하지 않는다.

## 7. 실패와 보존

처음 응답과 원 proof는 selector보다 먼저 stream에 flush/fsync한다. native 실행 종료 후
raw_complete를 기록하고 audit는 별도 단계로 수행한다. 실패 시 first-failure 원문,
부분 state, traceback을 보존한다. 자동 retry·resume·재봉인·기존 폴더 덮어쓰기는 없다.
정보 부족 보류, 계산 예산 종료, selector 예산 종료, schema/parsing/runtime/evaluator 실패를
동일한 실패 점수로 합치지 않는다. 미완성 terminal에서 예전 readout을 현재 채택으로 위장하지 않는다.

## 8. 최소 주장 범위

동결된 toy native engine에서 고정 scheduling 방향이 입력 순열 민감도와 계산 비용에 주는
영향을 구별한다. ID 최소/최대 기준은 의미를 학습한 정책이나 최적 탐색기가 아니다.
새 학습·관측·판단값 반전·회로 압축을 추가하지 않는다. 인간 뇌나 LLM hidden state의
메커니즘을 이 실험의 직접 결과로 주장하지 않는다.
