# R047 / EXP-28 — A→B 상태 전달의 기여 분해

## 1. 연구 계보와 이번 질문

기준선은 `bdd24df2d783a1cea82a6050f4f793c9eb06ca0a` (`R046 exp27 commit`)이다.
EXP-27의 정상 연장 조건에서 state_carry는 B의 native 수렴 ticks를 36→29로 줄였다. 당시에는 앞선 A의 edge activation 두 개와 path-prefix activation 두 개를 동시에 전달했으므로 어느 부분의 기여인지 분리하지 못했다. 반면 proof_memo/relation_carry는 새 proof 생성량을 줄였지만 수렴 ticks를 줄이지 않았다.

이번 질문은 **“A에서 얻은 상태 중 무엇이 B의 수렴을 줄이며, A의 실제 수치 대신 같은 위치에 높은 고정 초기값을 주어도 같은 효과가 나는가?”**이다.

통합 세션의 잠재 연결 공간, 문맥 binding, 가소성 가설을 한 번에 구현하지 않는다. 연결 공간을 재사용하는 효과와 현재 activation을 재사용하는 효과를 먼저 분리한다. 이 단계는 그중 activation 부분의 최소 실험이다. `prefix`는 기존 native path-prefix signal group을 뜻하며 자연어 의미·일반적 사고 깊이와 같은 개념으로 놓지 않는다.

사용자의 큰 발상은 미리 확보한 잠재 연결 공간의 binding/strength가 경험으로 달라진다는 가설이다. 그 발상을 바로 입증한 구현이 아니라, 공동 논의에서 도출된 상태 성분 분해를 이번 장치로 구체화한다. 고정값 0.99와 7-arm 배치는 이번 소스 작성에서 추가한 실험 설계 선택이다.

## 2. 사전 고정한 조작

| 처리 | 이전 edge 초기값 | 이전 prefix 초기값 | B의 새 부분·새 goal |
|---|---|---|---|
| cold | 0.5 | 0.5 | 0.5 |
| carry_edge | 실제 A 상태 | 0.5 | 0.5 |
| carry_prefix | 0.5 | 실제 A 상태 | 0.5 |
| carry_both | 실제 A 상태 | 실제 A 상태 | 0.5 |
| fixed_edge | 0.99 | 0.5 | 0.5 |
| fixed_prefix | 0.5 | 0.99 | 0.5 |
| fixed_both | 0.99 | 0.99 | 0.5 |

0.99는 새 EXP-28 처리의 실행 결과를 보기 전에 정한 단일 높은 원형 값이다. 결과를 본 후 조정하거나 유리한 값만 선택하지 않는다. 원래 EXP-27의 A 상태가 양성으로 수렴했다는 사실은 알고 설계했으므로, 완전히 정보 없는 초기값 대조라고 부르지 않는다. 이는 **A의 정밀한 수치 자체의 추가 이득**을 묻는 제한된 대조다.

fixed 처리도 actual carry와 같은 source packet, 근거 검사, group matching, target mask를 사용한다. 값 대입만 다르다. 따라서 이 비교로 binding이나 dependency validation이 필요 없다고 주장하지 않는다. 모든 non-cold 군은 전체 A state packet을 만든다. 부분 mask가 통신량을 최적화한 구현도 아니다.

A의 goal 값은 provenance packet에 남을 수 있지만 B의 goal에 복사하지 않는다. 안정화 이력은 전달하지 않는다. 전달된 group도 B 수렴 중 계속 갱신되며 고정/clamp하지 않는다.

## 3. 조건과 실행 단위

기존 EXP-27 공개 관측과 kernel config를 유지한다. A는 `u→v→w`, B 정상 연장은 `u→v→w→z`이다. 정상 관측은 +0.92이다.

- 정상 연장: 기존 A support가 그대로이며 새 관측 `w→z`가 추가된다.
- 대상 불일치: B가 `p→q→r→s`이다. 같은 edge ID여도 start/endpoints가 다르므로 A를 사용하지 않는다.
- 근거 변경: B에서 A의 `v→w` score만 -0.92로 반전된다. A의 상태를 전부 거부한 뒤 cold로 계산한다.

각 상황에 identity/fresh_ids 두 배치, 7개 처리를 적용한다. **B 3×2×7=42조건**, A source는 ID별 1회로 **총 2개를 공유**한다. 개별 처리 순서는 block별 회전으로 균형을 맞추며 자동 retry/반복이 없다. 같은 A를 독립 표본 여러 개로 세지 않는다. ID 변형도 독립 무작위 반복이 아니다. 통계적 일반화나 p-value를 산출하지 않는다.

fresh_ids는 A와 B 모두 같은 alias 체계를 사용하는 일관된 재명명이다. A→B 경계에서 ID가 새로 교체됐을 때 참조를 복구하는 실험이 아니다.

## 4. 가설과 판정

`spec.py:design()`의 문자열과 `plan.json`이 실행 전 동결된 기준이다.

| 가설 | 판정 대상 |
|---|---|
| H_carry_both_ticks | 정상 연장에서 carry_both의 B ticks < cold |
| H_edge_ticks | 정상 연장에서 carry_edge의 B ticks < cold |
| H_prefix_ticks | 정상 연장에서 carry_prefix의 B ticks < cold |
| H_source_specificity | 각 mask에서 actual carry의 B ticks < fixed 초기값 |
| H_outcome | 같은 case에서 non-cold 군의 raw value와 adoption이 cold와 동일 |
| H_rejection | 대상·근거 변경에서 reuse 거부, 초기값 전달 group=0 |
| H_ID_native | 같은 arm/scenario에서 일관된 ID 재명명 후 native counts·수치 궤적 동일 |

효율 이득은 대조와 같은 정답을 채택하고 측정이 가능할 때만 판정한다. 불안정, unsupported, budget termination, 오답의 값은 덮어쓰지 않으며 효율 지지로 세지 않는다. `H_outcome`은 정확도와 별개의 동등성 비교다. 실험 가설이 `falsified`여도 원자료와 측정이 유효하면 audit 자체는 통과할 수 있다.

**actual와 fixed의 ticks가 같으면 엄격한 H_source_specificity는 실패**다. 이것은 A의 어떤 상태 정보도 필요 없다는 반증이 아니다. 전체 궤적이 같은지, 현재 mask/고정값 범위에서만 같은지 구분한다.

기술적 상호작용은 `T_both − T_edge − T_prefix + T_cold`로 보고한다. 이 하나의 차이로 상태 성분의 통계적 독립성을 증명하지 않는다.

## 5. 기존 H_ID 실패와 요약 누락의 처리

EXP-27의 원래 H_ID는 native뿐 아니라 전체 연산 수 불변성을 포함했다. ID순 `assumed_edges`가 export 순서가 되고 첫 dependency 불일치에서 종료하므로, 근거 변경 조건에서 identity는 2회, fresh_ids는 1회 검사했다. 원래 세 carry 군의 실패 판정을 유지한다.

EXP-28도 그 순서를 강제로 정규화하지 않는다. `dependency_scans.csv`에 실제 순서를 보존하고 `ID_controls.csv`에 native·bridge 비용을 분리한다. H_ID_native는 **새 실험의 더 좁은 예측**일 뿐 원래 실패를 소급 수정하는 기준이 아니다.

기존 `summary.ko.md`는 변경하지 않는다. 별도 `analysis/parent_review.ko.md`에서 원래 ID 판정 전체를 표시한다. 새 summary에는 성공뿐 아니라 모든 가설 판정을 출력한다.

## 6. 실행/감사의 독립성과 측정

producer는 기존 `discover_paths`, `make_program`, `settle`, `reconstruct`를 직접 호출한다. native source 8개는 변경하지 않고 Git blob으로 고정한다. adapter는 공개 observation/config/처리명/A 기록만 받는다. 숨은 world, scenario명, 정답은 runtime에 전달하지 않는다.

독립 auditor는 native/runtime을 import하지 않는다. BFS로 경로를 확인하고, tanh 형태의 별도 스칼라 식으로 매 tick의 모든 group·residual·stable steps·정지 조건을 재계산한다. proof는 edge/reachable/blocked term의 결합 규칙으로 검사하며 펼친 dependency에서 D_DAG를 계산한다. 사건 순서와 중복 저장된 tick, source 참조, raw 파일과 append-only stream도 대조한다.

수치 허용오차는 2e-12이다. portable verify의 결과 파일에는 허용오차 충족 여부를 저장한다. 플랫폼별 마지막 부동소수점 오차의 차이를 raw 오류로 오판하지 않도록 재계산 오차의 정확한 소수값을 byte-equality 계약에 넣지 않는다. raw native 궤적은 원본 수치 그대로 보존한다.

비용은 ticks, group updates, signals, graph construction, support 검사, dependency 검사, descriptor matching, 상태 read/write, bytes, proof node 수, wall time을 각각 보고한다. native/bridge proof node 계수는 같은 생성 작업의 별칭이므로 더하지 않는다. wall time에는 기록/fsync 비용이 포함된다. energy, peak memory, native AdaptiveSession expansion은 미측정 `null`이다.

## 7. 증거·배포 경계

부모 run의 plan/manifest 자체를 고정한 해시로 확인하고, manifest에 선언된 모든 파일과 analysis를 원래 코드의 독립 auditor로 재검산한다. 누락/해시 불일치 시 새 실험 전에 중단한다. 오류는 새 deployment/run 폴더에 남기며 부모 파일을 수정하지 않는다.

Git에 없는 원래 로그를 만들어 채우거나 manifest 항목을 삭제하지 않는다. 실행한 원래 로컬 checkout의 파일 또는 정확히 같은 해시를 가진 원본 archive가 필요하다. 실행 단계 `01.log`~`08.log`는 부모 raw manifest 외부 자료이므로 이번 precondition이 원래 launcher 전 과정을 독립 증명했다고 주장하지 않는다. 부모 raw/source/analysis의 계약은 축소하지 않는다.

새 실행은 source snapshot과 부모 evidence 사본을 포함하고, 모든 파일을 hash manifest로 봉인한다. ZIP을 다시 열어 inventory와 bytes를 확인하고 receipt를 별도로 만든다. 새 execution 로그는 `.txt`로 저장한다. 추가하는 두 scoped `.gitignore`는 연구 log가 상위 `*.log` 규칙에 묻히는 것을 방지할 뿐 git add/commit/push는 하지 않는다.

## 8. 통합 가설에서 이번 구현의 위치

이번 단계: state 성분 분해 → 다음 단계 후보: binding을 유지한 초기값 효과와 내부 referent 대조 → 이후: 공간 재사용×상태 재사용의 교차 실험 → 충분한 기초 검증 후 경험에 따른 strength/binding 변화.

Preallocation, synaptic plasticity, 학습된 Circuit competition, 자연어 문맥 해석, full HCC lifecycle, pool-to-decision warm start는 이번 결과로 주장하지 않는다.

## 원자료 연결

- 기준선: https://github.com/jaeseongs95/hierarchical-convergence-circuit/commit/bdd24df2d783a1cea82a6050f4f793c9eb06ca0a
- 부모 evidence: 같은 commit의 `HCR-Evidence/exp27/r046-20260918T052020_778586Z-c3aecba2`
- 세션 근거: 첨부 인계문서, EXP-27 검토, 문맥·시냅스·HCC 핵심 정리 및 이 세션의 통합 논의.
