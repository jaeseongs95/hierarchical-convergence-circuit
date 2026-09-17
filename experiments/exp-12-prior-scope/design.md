# R0.3.1 — Prior 적용 범위 분리

기준 저장소 main: `7803ec250efc950e848298ba79c141946d89c2df` (`exp11 실행결과 commit`).
이 단계는 EXP-11 후속 설계의 §6·§12를 구현한다. R0.3.2의 수정 정책이나 R0.4의 공유 dependency/structural consolidation을 함께 구현하지 않는다.

## 1. 질문

회로를 선택하는 데 유용한 prior를 최종 판단의 relation/goal drive에까지 전달하는 것이 약한 반례의 오수렴을 만드는가?

기존 관찰과 새 실험을 구분한다. EXP-09는 회로 우회 시 같은 점수로 수정됨과 다른 부분회로의 재선택을 관찰했다. EXP-11은 방법 간 충돌·보류 및 일부 메시지의 경로 변경을 관찰했다. 이 패치는 그 결과를 새로운 추론의 결과로 재사용하지 않는다.

## 2. 조작

| arm | 같은 AdaptiveEngine의 회로 선택 | 최종 learned drive |
|---|---|---|
| legacy | 기존 pool/매칭/macro | 기존 prior |
| route_only | **기존과 동일** | relation·goal에 전달하지 않음 |
| graph_only | `use_circuits=False` | 회로 없음 |

세 arm 모두 동일한 기본 frontier 정책, 관측, config, 시작 memory를 사용한다. 여기의 graph_only는 EXP-11 Sequential의 breadth-first profile을 사용하는 것이 아니다. MethodEngine의 교대·메시지·integration을 이 실험에 넣지 않아 M profile과 prior 효과를 섞지 않는다.

`activation.py`, `expansion.py`, `learning.py`, `circuits.py`, `dynamics.py`, `methods.py`, `integration.py`는 변경하지 않는다. `workspace.adaptive_network`의 이미 binding된 prior 전달 위치에서만 policy를 적용한다. source→target topology, 공개 evidence drive, top-down link, pool dynamics는 동일하다.

## 3. 정책·상태 계약

`PriorPolicy`는 legacy/route_only만 허용한다. 한 engine의 정책은 읽기 전용이다. 다른 조건은 새 engine/session으로 시작한다. memory의 config signature나 학습 이력을 다시 쓰지 않고 같은 memory를 비교할 수 있다.

기본 legacy의 과거 이벤트·상태 필드는 유지한다. 새 route_only는 engine 생성 이벤트, engine state, pending state, 판단 network metadata에 `prior_policy`와 그 해시를 명시한다. 새 session packet schema는 `hcr-session-checkpoint-r031-v1`이다. policy가 있으면 반드시 이 schema를 쓰며 누락·위변조·상위 schema 불일치를 거부한다.

기존 `hcr-session-checkpoint-r021-v1`, `r03-v1`은 원래 의미로 검산한다. 소스가 바뀐 옛 packet을 현재 소스로 복원하지 않는다. 과거 자료는 동결된 source로 읽거나 read-only 검산의 source 제한을 명시한다. migration으로 과거 hash를 수정하지 않는다.

관측 revision, memory version, generation, kernel tick은 다른 값이다. `D_DAG`는 primitive proof 기준 그대로이며 macro hop 감소를 D 감소로 세지 않는다. 참 판단에서 거짓 판단으로 바뀐 경우 proof 자체가 달라질 수 있다.

### 판단 근거 guard

기존 guard는 모든 관측이 None/0이고 판단에 적용할 prior도 없으면 보류한다. route_only에서 **사용하지 않은 pool prior를 판단 근거로 세지 않도록** 이 조건을 유효한 judgment prior 기준으로 평가한다. 이것은 `all_missing/all_zero`에 영향을 줄 수 있다. 다른 evidence가 남은 부분결측 입력을 전부 보류하도록 바꾸지는 않는다.

이 guard와 수치 drive 효과를 혼동하지 않도록 fixed-network 진단에는 task readout guard를 적용하지 않는다. raw의 network state/convergence와 task의 value/status는 별개로 기록한다.

## 4. 평가 구성

조건은 `evaluation/prior_spec.py`에 고정한다. seed는 빈 memory에서 검증된 성공 9회를 실제 학습하고 3·6·9회 시점에 snapshot한다. 학습량별 독립 재학습을 3+6+9회 한 것으로 세지 않는다. 각 평가 cell은 해당 시점 memory의 별도 복사본에서 동결 추론하며 feedback/retry를 하지 않는다.

공개 입력 13개 × 학습량 3개 × arm 3개 = **117개 task inference**다.

- 첫 edge 점수 6개: −0.98, −0.06, 0.0, +0.06, +0.98, None. 나머지 두 점수는 0.92 고정. topology와 이름·episode ID도 고정.
- 보존 과제 5개: familiar, counterfactual, longer, diamond, renamed_reordered.
- 식별성 과제 2개: all_missing, all_zero.

양수·음수 sweep의 외부 세계는 각각 첫 edge open/closed인 선언된 toy fixture다. 0/None sweep 및 all_missing/all_zero는 **같은 추론**을 first_open/first_closed 두 외부 세계에서 평가한다. 총 외부 평가는 153건이지만 추론은 117회다. 보류(None), 부정 답(False), 외부 평가 참(False/True)을 혼동하지 않는다. 조건당 wall time 반복은 1회이므로 속도 우월성을 검증했다고 쓰지 않는다.

## 5. 두 가지 비교

### End-to-end

첫 pool·매칭·후보·최초 expansion은 legacy와 route_only에서 동일해야 한다. audit는 이를 실제 raw에서 비교한다. 그 뒤 drive 조작 때문에 경로가 달라지면 `full_expansion_sequence_equal=false`로 남긴다. 호스트가 경로·답·ID를 고치지 않는다.

pool/decision tick·signal을 분리하며 전체 값에 다시 합산하지 않는다. engine active time과 session 복사 등 관리 시간을 포함한 전체 시간을 구분한다. 평가 중 디스크 checkpoint를 끼우지 않는다. 마지막 packet 구성 시간도 별도 기록한다.

### Fixed-network

각 legacy cell의 **마지막 실제 판단 network**를 source event seq/hash로 참조한다. 동일한 program·0.5 초기 상태·공개 evidence drive·top-down 설정을 유지하고 learned drive만 다르게 두 번 계산한다. 39개 대응쌍, **78회 numerical replay**이며 추가 task inference가 아니다. 원래 program이나 없는 path를 oracle로 채우지 않는다.

생성은 공통 kernel을 사용하고 검산은 `independent_step`으로 tick/잔차/정지 조건/카운터를 다시 계산한다. endpoint만 같다는 검사로 대체하지 않는다.

## 6. 후보 단계 관찰

`record_metrics`는 실제 scan, pool result, proposal, expansion을 연결한다. 평가기는 각 **실제로 방문한 frontier**에서 topology상 가능한 motif binding을 별도로 열거하되 이를 engine에 전달하지 않는다.

inactive, primitive 길이 예산, incomplete scan, pool 미구성, activation/mismatch 탈락, eligible-not-selected, expansion budget 미실행, executed를 구분한다. 관측 자체가 없는 미방문 frontier의 전체 universe를 알았다고 하지 않는다. 이 분류는 후보 상태의 관찰이지 activation failure/competition failure/고정관념의 원인 확정이 아니다.

회로 strength, 검증 episode 수, balance, failures, active, version을 별도 기록한다. 사용 횟수/나이/rigidity를 같은 변수로 만들지 않는다. 여섯 score 점의 재사용·오적용 표를 연속적인 attractor basin 폭으로 환산하지 않는다.

## 7. 검산과 저장

- raw session의 event chain·generation·binding·frontier·수치·학습 상태는 기존 session auditor의 별도 재생으로 검사한다.
- 새 policy에 따른 expected judgment drive는 생산 workspace 함수를 호출하지 않고 audit support에서 계산한다.
- external truth는 평가기의 `assess`/`reachable`에만 전달한다.
- `records`, `costs.csv`, `summary`는 raw에서 다시 집계한다. 해시까지 재작성한 요약 변조도 거부한다.
- 이 감사는 독립적인 OS 실행 인증이 아니라 기록의 정합성 검산이다. source/fixture/외부 reference 재사용 범위를 남긴다.
- 새 출력은 `HCR-Evidence/exp12/<run>`을 허용한다. 기존 결과·sealed manifest 폴더 내부·symlink/junction은 거부한다.
- 실패는 FAILED.json에 단계와 이미 기록한 추론 수를 남기며 원자료를 삭제하거나 자동 retry하지 않는다.

## 8. 다음 단계와의 경계

이번 구현은 습관·고정관념 가설 중 **재사용의 효용과 해석 bias의 분리**를 위한 최소 장치다. rigidity 수치를 인위적으로 키우는 변수, 전체 유사 회로 약화, 부정 예외 학습, 공유 subcircuit, pool 최적화, 새 scheduler는 넣지 않았다.

결과에서 initial routing 보존과 판단 변화가 확인되면 다음 R0.3.2에서 반례 뒤 수정/유지 정책을 별도 실험한다. 효과가 없거나 보류만 늘면 그 결과를 그대로 두고 매칭·후속 전개·통합 쪽 대안 설명을 비교한다. R0.4의 얽힘·consolidation은 그 이후다.

원문: `theory/source/HCC_habit_fixed_schema_20260917.md`.
직전 분석·설계 원본: `docs/reference/EXP11_habit_followup_design_20260917.md`.
