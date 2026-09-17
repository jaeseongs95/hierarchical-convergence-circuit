# R0.3.4 / EXP-15 — 추가 전개, 재시작, judgment prior, proof 선택의 분리

## 1. 근거와 이번 변경의 범위

기준선은 `54330d01c979cb942b39558186c206b4373b758e` (`실행결과 commit`)이다.
근거 자료는 `HCR-Evidence/exp14/r033-first`의 plan, summary, audit 및 개별 raw/records다.

EXP-14에서는 `irrelevant_missing/legacy`가 충분한 공개 정보를 가지고도 보류했다. 추가 전개만으로는 회복하지 않았고, `route_review` 또는 관측 후 재계산으로 지지된 출력을 회복했다. `critical_missing/zero`에서는 실제 정보 획득이 필요했고, `weak_negative`에서는 새 정보 없는 policy 재검토가 유효했다. 이번 패치는 이 차이를 다음 실험으로 분리한다.

**관찰에서 나온 다음 질문:** 선택된 proof의 support gap을 문제 전체의 정보 부족으로 취급하고 있는가? 재시작의 효과, judgment prior 변경의 효과, 이미 생성된 경로 중 proof를 고르는 효과가 다른가?

새 support-first 규칙과 running-boundary 대조는 EXP-14 결과 자체가 아니라, 그 결과를 구별하기 위해 추가한 실험 설계다. 성공은 예상일 뿐 실험 수용 조건이 아니다.

## 2. 기존 구조를 유지하는 방식

기존 `runtime.py`, `proof.py`, `grounding.py`, `review.py`, `sessions.py`, 학습·pool 규칙, 과거 시험·evidence는 수정하지 않는다. 새 모듈과 전용 실행기만 추가한다. 기존 패키지 버전 문자열과 `RELEASE_MANIFEST.json`도 보존하고, 추가 파일은 `R034_MANIFEST.json`으로 별도 검증한다.

기존 `finish()`가 만든 native decision/proof는 그대로 보존한다. `selection.py`가 만드는 것은 새 schema의 **명시적인 sidecar proof 후보**다. 이를 정상 finish가 처음부터 만든 proof처럼 기록하지 않는다.

## 3. main의 7개 arm

| arm | 변하는 것 | 유지되는 것 |
|---|---|---|
| `hold` | 없음 | 최초 native decision과 dependency gate |
| `expand_only` | 기존 frontier의 추가 전개 | 관측, memory, prior, native proof 규칙 |
| `restart_same` | 같은 초기 정책으로 새 session | 관측, memory, circuit 사용, judgment prior |
| `restart_route_only` | 새 session에서 judgment prior를 route_only로 | 관측, memory, circuit routing 사용 |
| `select_only` | 이미 생성된 경로의 proof 선택 | 관측, memory, activation, Graph, raw 참·거짓 |
| `expand_then_select` | 필요 시 전개 후 같은 선택 규칙 적용 | 관측, memory, judgment prior, raw 값 뒤집기 금지 |
| `observe_first` | 필요한 gap의 모의 관측 후 재계산 | EXP-14 `ReviewFlow`를 그대로 참조 조건으로 사용 |

`restart_same`와 `restart_route_only`를 대응 비교하여 재시작과 prior 변경을 구별한다. `select_only`는 아직 만들지 않은 대안 경로를 얻을 수 없다. `expand_then_select`는 실제 추가 생성 이후에만 그 경로를 사용할 수 있다.

이미 native gate를 통과한 판단은 모든 arm에서 먼저 종료한다. 따라서 `misleading_direction`에서 재검토가 발동하지 않는 기존 경계도 보존한다.

## 4. support-first의 정확한 계약

입력은 실제 finish candidate에서 추출한 공개 관측, native raw 값, state, completed paths, 원 proof, source reference다. program의 경로 목록, metadata의 실제 routes, decision의 expanded_paths를 대조한다. evaluator는 이 projection을 생산 함수를 호출하지 않고 원자료에서 다시 만든다.

현재 raw 값이 **True인 경우에만** 다음 절차를 실행한다.

1. 기존 terminal activation 내림차순과 path index 순서를 유지한다.
2. 해당 경로의 모든 edge activation이 0.5 이상인지 확인한다. 이는 기존 reconstruct의 양성 경로 적격 조건을 보존한다.
3. 모든 관측 score가 선언된 `min_abs_score`보다 큰지 확인한다. `None`, 0, 음수는 양성 지지가 아니다.
4. 처음 만족하는 **이미 생성된 경로**의 primitive proof DAG를 별도로 만든다.
5. 선택 후보에 원 native candidate ID, ready/finished hash, generation, segment, 원 decision hash를 결속한다.

raw False/None를 True로 바꾸거나 raw True를 False로 바꾸지 않는다. 부정 판단의 증명 규칙도 새로 만들지 않는다. 이 범위에서는 약한 반례에 대한 값 수정은 여전히 명시적인 prior 재계산 arm의 역할이다.

이 선택은 관측 지지 계약을 반영한 설계 개입이지, 저절로 학습된 신뢰도나 인간의 metacognition을 입증한 결과가 아니다. 관측 자체가 틀릴 때의 외부 정확도는 여전히 별도로 평가한다.

## 5. 순수 계산 부족의 양성 대조

`computation_chain3`, `computation_chain4`는 모두 양수 관측인 새 입력이다. circuit을 끈 `route_only` 계산을 정확히 1 advance 후 **아직 running인 경계**에서 저장한다.

이 경계에는 최초 decision이 없다. 가짜 `None` decision이나 proof를 만들지 않는다. `first=None`은 '원 엔진이 보류를 출력했다'가 아니라 '아직 최초 판단을 생성하지 않았다'는 뜻이다.

`hold`와 추가 advance 예산 0/1/8의 `continue`를 비교한다. 충분한 계속 계산으로 답이 생성되는지 확인하며, main의 readout-ready 조건과 합쳐 정책 정확도 순위를 내지 않는다. graph-only라는 별도 조건이므로 이 그룹을 circuit 효율 비교에도 사용하지 않는다.

## 6. 조건 수와 통계 단위

main은 EXP-14의 8개 입력을 그대로 사용한다. 입력·world 조합 13개 × 초기 정책 2개 × arm 7개 = 182 rollout이다.

running 대조 8개와 선택/추가 계산 예산 대조 4개를 더하면 총 194 rollout이다. 최초 계산은 readout-ready 16개와 running 2개, 총 18개를 공유한다. 학습은 6회 한 조건이며 검토 중 memory는 동결한다.

194를 독립 문제 194개나 독립 모델 추론 194회로 쓰면 안 된다. matched hidden-world 평가와 정책 분기는 공통 baseline을 공유한다. train count 변화, rigidity, entanglement, 장기 수정·재학습은 이번 축이 아니다.

## 7. 비용과 중단

engine kernel ticks, 추가 advances, session restarts, native proof 노드와 sidecar 선택 비용을 분리한다.

sidecar에는 rollout 전체에 걸친 `ranked_paths`, `path_checks`, `edge_checks`, `proof_nodes` 누적 예산이 있다. 각 readout에서 예산을 초기화하지 않는다. 처음부터 ranking 비용도 inventory에 기록한다. 이 값은 전체 CPU 명령 수나 에너지 추정이 아니다. wall time에는 projection/검사/정렬/증명 생성 및 제어·저장·검산 overhead가 섞일 수 있으므로 ticks와 구별한다.

기존 native 작업은 다음 advance의 최대 kernel 작업을 보수적으로 예약한다. 부족하면 `stop_compute_budget`으로 종료하며 이를 수학적 비수렴이라고 부르지 않는다.

## 8. 독립 검산과 provenance

생성과 검산은 별도 CLI 프로세스다. raw generation은 최종 정답 여부에 따라 결과를 고치지 않는다.

- 기존 session/EXP-14 auditor로 실제 state recurrence, frontier, binding, source, native finish와 grounding을 재검산한다.
- `selection_audit.py`는 생산 선택기와 제어기를 호출하지 않고 선택 순서·예산·controller action·새 proof DAG를 검산한다.
- proof final의 실제 dependency DAG에서 `D_DAG`를 다시 계산한다. 검사 횟수를 깊이로 사용하지 않는다.
- evaluator의 reachable/identifiable와 hidden truth는 실행기로 전달하지 않는다.
- 최초 raw, 모든 native candidates, sidecar candidates, 실제 추가 작업, 비용과 실패가 보존된다.

streamed action log는 첫 실행에서 즉시 기록한다. exception은 parsing/schema-contract/runtime-I/O/runtime으로 구분해 마지막 commit된 session과 함께 보존한다. 자동 retry는 없다. 독립 audit 실패도 raw를 바꾸지 않고 별도 기록한다.

## 9. 판별 기준

`restart_same`도 회복한다면 restart와 prior 변경을 구분해야 한다. `restart_same`은 실패하지만 `restart_route_only`가 회복한다면 동일 재시작 조건에서 prior의 역할이 더 좁혀진다.

`select_only`는 실패하고 `expand_then_select`만 회복하면, 대안 경로 생성과 선택을 함께 요구하는 경우다. `expand_only`는 실패하고 동일 관측에서 `expand_then_select`가 회복하면, 전개량만으로 설명되지 않는 proof 선택 병목을 지지한다.

`critical_missing/zero`가 관측 없이 계속 보류하는 것은 연구 실패가 아니다. 정보 부족 조건을 정보 없이 임의 확정하지 않는 경계다. `misleading_direction`의 오답은 별도 센서 신뢰성/재검토 발동 연구에 남긴다.
