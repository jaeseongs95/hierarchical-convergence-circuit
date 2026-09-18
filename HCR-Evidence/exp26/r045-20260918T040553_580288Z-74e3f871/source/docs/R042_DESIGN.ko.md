# EXP-23 / R042 설계 — edge ID와 경로 역할 분리

## 1. 이전 결과에서 이어지는 질문

EXP-22의 고정 조건에서는 `edge_id_min`과 `edge_id_max`가 모두 입력 배열 순열에 따른 native tick 격차를 제거했지만 절대 비용은 달랐다. legacy/online_support에서는 102 대 170 ticks, route_only에서는 164 대 262 ticks였다. 이 숫자는 **EXP-22의 관찰값**이며 R042 실행의 기대값이나 통과 조건으로 사용하지 않는다.

현재 지원 경로 S가 작은 ID를 갖고 있으므로, 효율 차이가 ID 이름 자체의 장점인지 ID 정렬 순서와 경로 역할의 결합인지를 다음 단계에서 분리한다.

## 2. 최소 실험의 범위

- topology 1개: EXP-22의 고정된 6개 배열 순열을 그대로 사용한다.
- prior와 policy는 `legacy / online_support` 하나로 제한한다.
- 두 ID 배치(identity, swap_SD)와 두 scheduler(edge_id_min, edge_id_max)를 교차한다.
- 총 24조건이다. 독립 문제 24개 또는 통계적으로 독립인 표본 24개가 아니다.

route_only, native, posthoc_support, 새로운 score 기반 scheduler, adaptive ID 보정은 이번 범위에 넣지 않는다.

## 3. 조작

### 생산 입력 변환

`transform.py`가 native begin 이전에 다음 bijection을 한 번 적용한다.

```text
e0 ↔ e4
e1 ↔ e5
e2, e3, e6 유지
```

따라서 S의 ID tuple은 `(e4,e5)`, D의 ID tuple은 `(e0,e1,e6)`이 된다. M의 ID는 유지한다. 전체 ID 집합과 길이도 유지한다. 배열 순열을 만드는 조작과 ID 배치를 바꾸는 조작은 서로 분리한다.

변경하는 입력은 observation의 `edges[*].id`뿐이다. 평가 world는 ID-key를 동일하게 운반한다. source/target/node/score/null/episode/revision은 그대로 둔다. 새 observation digest, session reference, proof ID는 기존 native 코드가 새 입력에서 자연스럽게 생성하게 한다. 예전 hash를 강제로 유지하거나 생성 후 고치지 않는다.

### Memory 경계

훈련된 seed memory와 config를 그대로 사용한다. current edge ID의 정확한 JSON 문자열 참조가 발견되면 `check_seed_reference_scope`가 중단한다. 이 범위 밖의 memory 재작성이나 embedded-string 추측 치환은 하지 않는다. 기존 학습 packet, provenance, 과거 proof를 재명명하지 않는다.

### Runtime 경계

새 runtime adapter는 R041의 `ScheduledTimingTrial`을 그대로 호출한다. 공개 observation/config/memory/budget, 고정 scope/arm, scheduler 이름만 전달한다. case label, variant label, edge map, S/M/D role, evaluation world는 native worker 또는 scheduler로 전달하지 않는다.

## 4. 가설과 구별되는 관찰

**역할 정렬 설명:** ID 배치를 바꾸면 min/max의 비용 관계가 뒤집히고, identity/min과 swap_SD/max, identity/max와 swap_SD/min 사이에 역변환된 경로가 대응할 수 있다.

**비용 역전만 관찰되는 경우:** 다른 ID 사용 지점의 영향, 초기 후보 구성의 변화, native proof 선택 변화가 추가 설명 후보로 남는다. 비용 차이만 보고 scheduler 하나의 인과효과로 결론 내리지 않는다.

**역전이 없는 경우:** 결과를 실패로 폐기하지 않는다. 어떤 경로가 먼저 완성되었는지, 사용 가능한 지원 proof가 언제 생겼는지, 그때 online 채택이 가능했는지를 readout 및 event로 구분한다.

**순열 민감도가 남는 경우:** 배열 순서 강건성, ID 재명명 강건성, 비용은 다른 지표로 보고한다. scheduler 이름이 같다는 이유만으로 강건성을 가정하지 않는다.

## 5. 독립 검사

`input_audit.py`는 생산 `spec.py`와 `transform.py`를 import하지 않는다. 별도 선언된 대응표로 새 observation을 역변환하고 원본 전체와 비교한다. ID 외 변경, world truth 변조, case/trial 누락·중복, counterbalance 변경, budget 변경을 거부한다.

실행 이후 R041 `audit_trial`이 native 상태, proof DAG, 선택, adoption/stop, scheduler 결정, priority 전이, 비용을 기존 독립 방식으로 replay한다. R036 `check_seed`가 훈련 seed를 별도 검산한다.

identity 12조건은 EXP-22의 같은 prior/arm/scheduler/배열 조건과 비교한다. parent raw 12개도 다시 native audit한다. 이 회귀는 기존 계산의 보존 조건이며 재명명 가설의 성공 조건이 아니다.

## 6. 계보와 최소 capsule

기준 commit은 `11f43790c0cb1b4732199ae4fb17c5bbbed4cd5b`다. R041 release manifest의 Git blob과 모든 기존 의존 source hash를 검증한다. 본 실험의 parent raw manifest는 다음 SHA-256으로 고정한다.

```text
72cce1ef020908c4d2d9b3c219c68b1343d89d8a01d178a029518dc427f8e5e8
```

EXP-22 전체 원자료 재검산은 launcher preflight에서 수행한다. R042 자체 evidence에는 parent plan/manifest/analysis lineage, 원 훈련 자료, 직접 회귀에 필요한 raw 12개만 넣는다. 기존 실험의 중첩 raw 전체를 매번 복제하지 않는다.

R042 audit에서 parent 108조건 전체를 다시 replay했다고 주장하지 않는다. R042 audit가 직접 replay하는 parent 조건은 12개이며, preflight의 전체 재검산은 execution log에서 구분한다.

## 7. 지표

### 원자료와 역변환 투영

raw ID trace, native proof, reference, 상태는 그대로 보존한다. 평가기의 inverse-ID 경로/assumption/activation 투영을 별도 diagnostics로 만든다. 이는 host correction이 아니라 평가용 대응이며 실행기에 되돌려 주지 않는다.

### 독립 보고 항목

native ticks의 최소/최대/spread/합계/평균, canonical 경로 완성 순서 수, canonical readout 궤적 수, 최종 채택/값/분류, 지원 S의 완성 순위, 최초 supported 및 usable-supported readout 시점, 최종 `D_DAG`, 남은 frontier, scheduler/selector 세부 작업량, 기록된 wall time을 분리한다.

`D_DAG`는 기존 proof auditor가 계산한 의존 깊이다. tick 또는 경로 탐색 단계 수로 추정하지 않는다.

`final_proof_projection`은 canonical assumed edges/paths/D_DAG를 비교한다. 전체 proof DAG의 graph-isomorphism 증명이라고 부르지 않는다.

### 초기 대조의 범위

첫 경쟁 scheduling 시점의 frontier set과 그 이전 readout을 역변환하여 `pre_competitive_probe`로 비교한다. 없는 probe는 null로 남긴다. 이는 전체 초기 engine state 동치 검사가 아니라 제한된 관측 대조다.

### 해석 제한

native ticks 감소는 전체 실행시간 또는 전력 절감률이 아니다. scheduler/selector/파일 보존 overhead는 서로 다른 계수와 wall time으로 남긴다. 미측정 비용을 0으로 치환하지 않는다.

## 8. 실패 보존

prepare는 기존 plan을 덮어쓰지 않는다. execute는 새 디렉터리와 append-only attempts stream을 생성하고 각 이벤트를 flush/fsync한다. 첫 schema/reference/runtime 실패에서 중단하며 partial evidence와 failure.json을 남긴다. 자동 retry/restart/ID correction은 없다.

잘못된 값이나 abstention이 유효한 native 출력이면 그대로 분석한다. raw 미완료와 오답을 같은 상태로 처리하지 않는다. audit 불일치는 별도의 audit_failures에 기록한다. 분석 파일은 새 디렉터리에 한 번 쓰고 verify는 원자료에서 다시 계산해 비교한다.

## 9. 성공 기준

장치의 성공 기준은 입력 조작의 분리, 계보 보존, 독립 replay, 기존 identity 조건의 회귀다. 비용 역전, 정답, spread=0, 교차 궤적 동치는 관찰 대상이며 audit가 요구하지 않는다.

코드 unit fixture와 native integration smoke는 연구 표본에 합산하지 않는다. 실제 연구 결과는 사용자 환경에서 실행된 24조건 raw와 해당 독립 audit로 판단한다.
