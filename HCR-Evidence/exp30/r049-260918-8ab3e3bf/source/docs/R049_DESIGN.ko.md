# R049 / EXP-30 — 역방향 신호 × 초기조건과 판단 경계

기준 commit: `426ad699235935a97b74b1dcd1acbcd4890313b2` (`R048_EXP29 commit`).
부모 실행: `HCR-Evidence/exp29/r048-260918-144636-9af6bf45`.
원인 분리를 위한 연구 장치이며 기존 kernel을 정답이 잘 나오도록 고치는 패치가 아니다.

## 1. 연구 계보

EXP-27은 이전 수치 상태의 전달과 proof 구성의 재사용을 분리했다. EXP-28에서는 초기화 위치에 따라 수렴 ticks의 절감량이 달랐지만, 실제 수치와 0.99 대조의 ticks는 같았다. EXP-29에서는 유효한 36비교 중 실제 수치 우위가 없었으며, 관측 강도 0.02에서 A가 잘못된 방향으로 안정된 뒤 채택이 거부됐다.

그다음 검토에서 기존 식을 별도로 계산한 양성 탐색은 top-down OFF만으로 goal이 바로 맞아지지 않으며, top-down ON에서는 초기조건에 따라 다른 방향으로 안정될 수 있음을 보였다. 그 값은 이번 EXP-30을 보기 전에 알려진 탐색 대조다. 이번 소스는 이 대조를 native 엔진에 연결하고 음성 대조·신호 분해·proof/adoption 경계를 추가한다.

사용자의 연구 방향과 공동 검토에서 도출한 질문을 구현한다. 고정된 잠재 연결 공간, 가소성, 인간 문맥 처리의 구현·검증으로 표현하지 않는다. EXP-27/28/29의 실패 판정은 소급 수정하지 않는다.

## 2. 실행 행렬 — 48조건

A의 길이 2 chain만 사용한다. `u→v→w`이며 새로운 B 계산은 하지 않는다.

| 요인 | 값 |
|---|---|
| 관측 강도 | 0.02 / 0.10 / 0.92 |
| 관계·world 대조 | positive (++), mixed_negative (+−) |
| ID | identity / fresh_ids |
| 처리 | on_neutral / off_neutral / on_high / off_high |

관측 크기는 두 edge에 같게 적용한다. 음성 대조에서는 **두 번째 edge만** 음수이고 world도 해당 edge만 False다. world는 명세에서 따로 고정하며 실행기에 보내지 않는다. ID 순서/의미 role을 새로 탐색하는 실험이 아니라 일관된 ID 재명명 대조다.

| 처리 | top_down | edge·prefix 초기값 | goal 초기값 |
|---|---|---|---|
| on_neutral | True | 0.5 | 0.5 |
| off_neutral | False | 0.5 | 0.5 |
| on_high | True | 0.99 | 0.5 |
| off_high | False | 0.99 | 0.5 |

0.99는 모든 world·관측에 같은 방식으로 준 **실험자 초기조건**이다. 실제 A의 양성 채택 gate를 우회해 이전 상태를 가져온 것이 아니며, carry/reuse/학습이라고 부르지 않는다. 상태를 clamp하지 않고 첫 tick부터 기존 규칙으로 모두 갱신한다. 종료 기준·bias·gain·damping·온도·proof 선택은 그대로다. top_down OFF는 저장된 link 목록을 지우지 않지만 실제 전달함수를 바꾸는 개입이다.

총 48개 query를 한 번씩 실행한다. 중간 실패의 조건별 재시도, 결과 기반 초기값 변경, 일부 조건 필터링, 모델 다운로드는 없다. ID별 반복을 독립 무작위 표본으로 세지 않는다. 처리 순서는 block별 회전 순서로 고정한다.

## 3. 기존에 이미 본 조건

양성 세 강도의 neutral ON/OFF와 양성 0.02의 high ON/OFF는 앞선 별도 방정식 탐색에서 이미 봤다. 두 ID에 해당하는 **16개 실행은 `prior_exploration_replication`**으로 표시한다. 남은 32조건은 `new_condition_in_frozen_matrix`다. 이 태그는 독립 발견 수가 아니다.

`R049_PRIOR_EXPLORATION.json`에는 앞선 파일의 hash와 8개 수치 조건의 궤적 서명이 있다. `prior_regressions.csv`는 이를 이번 native 결과와 대조한다. 실험 구조는 새 음성 조건을 개발 환경에서 실행하기 전에 `R049_FROZEN_DESIGN.json`으로 동결했다. self-test의 계산은 구현 검증 모집단이며 사용자 정식 run과 합산하지 않는다.

## 4. 관측·상태·proof의 의미

- observation.score: [-1,1]의 공개 측정. 원자료는 그대로 보존한다.
- edge activation: 관측·연결·자기 피드백을 처리한 내부 수치. 원자료와 같지 않을 수 있다.
- raw: native 안정화 기준을 만족했을 때 goal에서 읽은 방향. 정답 판정이 아니다.
- proof: 그 raw를 기존 규칙과 내부 edge 가정으로 재구성한 DAG.
- support: 그 proof의 가정이 현재 관측의 비영점 부호로 지지되는지 확인한다.
- adoption: 지지된 proof가 있는 raw만 채택한다. 거부는 올바른 답으로 수정한 것이 아니다.
- world: 실행 후 독립 평가기에만 주는 실제 True/False 상태다.

최초 `abs(2*goal−1) >= margin_threshold`인 실행 tick에 `first_margin_readout`을 기록한다. 안정화 patience를 충족했다는 뜻이 아니고 중간 관찰값일 뿐이다. 이를 종료나 채택에 사용하지 않는다. provisional 값이 나중에 바뀌어도 기록을 바꾸지 않는다. 각 proof node ID는 trial 내부 ID이며 서로 다른 query의 노드 참조가 아니다.

## 5. 실패를 겹쳐 기록한다

`boundaries.csv`는 다음을 서로 배타적인 단일 상태로 합치지 않는다.

`raw_value_incorrect`, `edge_activation_observation_sign_conflict`, `proof_construction_failed`, `proof_assumption_support_conflict`, `adoption_rejected`, `budget_terminated`, `measurement_failed`.

raw가 없으면 raw 정오답은 null이다. runtime·계약·감사 자체가 실패하면 failure.json과 부분 stream을 보존하고 성공 analysis를 만들지 않는다. measurement_failed=False는 실제로 감사가 통과한 record에만 출력한다.

edge/관측 부호 충돌은 `(2*activation−1)*score < 0`인 엄격한 반대 부호로 정의한다. 정확히 0.5는 이 지표에서 중립이다. native proof의 `>=0.5` True 규칙은 별개로 유지한다. 초기 high가 음성 관측과 충돌하면 tick 0의 initial_sign_conflicts에 남긴다. 최초 음성 tick, 최초 부호 충돌 tick, 종단 충돌을 함께 기록한다.

## 6. 신호 분해 — 원 계산을 바꾸지 않는다

실제 query는 기존 `discover_paths`, `make_program`, `settle`, `reconstruct`를 직접 호출한다. top_down 인자를 명시적으로 전달한다. native 8파일은 Git blob으로 고정하며 수정하지 않는다.

계산을 끝낸 뒤 독립 auditor가 모든 tick/group을 tanh 형태의 동치식으로 재계산한다. 그 다음 기록된 전후 상태에서 `signal_ledger.csv`를 만든다. 분해 계산은 native logger나 update에 되먹임하지 않는다.

각 tick/group에는 bias, 외부 drive, support 합, 실제 top-down 합, 합성 자기 피드백 logit, 전체 logit, 갱신 전후 값, damping, 변화량, 실제 메시지 수가 기록된다.

`masked_top_down_term`은 꺼진 link가 같은 기록 상태에서 갖는 대수적 항이다. 실제로 전송된 값이나 OFF의 반사실적 전체 궤적이 아니다. 메시지 비용에 합산하지 않는다.

`target_implied_by_native_update`는 `(after-(1-damping)*before)/damping`으로 역산한 native 목표값이다. 별도 tanh 감사가 이를 포함한 전체 궤적의 정합성을 검증한다. 플랫폼의 마지막 exp/tanh bit 차이가 파생파일 byte 검증을 깨지 않도록 분석표에는 원자료의 대수적 재구성만 저장하며, 오차 최대값을 원본 데이터처럼 고정하지 않는다. 허용오차는 2e-12이다.

자가흥분과 억제는 현재 식에서 `(self_excitation+inhibition)*(2p−1)`로 결합한다. 두 메커니즘을 별도 원인으로 분리했다고 주장하지 않는다.

## 7. 사전 가설과 대비

| 가설 | 판정 |
|---|---|
| H_off_edge_alignment | 비중단 OFF 조건에서 종단 edge activation이 각 관측과 엄격히 같은 부호인가 |
| H_negative_high_raw | 음성 대조의 high 초기화에서 raw가 False인가; raw 없음/예산 종료는 판정불가 |
| H_adoption_safety | 비중단 조건에서 world에 틀린 답을 채택하지 않았는가; 거부를 정확도 성공으로 세지는 않음 |
| H_ID_native | 같은 강도·관계·처리의 두 ID에서 native 비용과 전체 수치 궤적이 같은가 |

주요 비교는 같은 초기화 안의 OFF−ON, 같은 top_down 안의 high−neutral이다. 한 비교에서 하나의 변수만 바꾼다. 기술적 상호작용은 `(on_high−on_neutral)−(off_high−off_neutral)`로 ticks와 Boolean raw 지표에 각각 계산한다. 어느 방향으로 나와야 성공이라는 사후 기준을 추가하지 않는다. 산출물이 판별할 수 있는 결과를 모두 남긴다.

가설이 실패해도 원자료·감사가 유효하면 실행 성공 bundle을 만들 수 있다. audit는 가설을 성공시켜 주는 코드가 아니다. 예산 중단은 논리 실패가 아니며, 관측 지지 부족·proof 없음·raw 오판도 구분한다.

## 8. 비용과 재현성

stored program과 effective program을 구분한다. effective signature는 program, config, 외부 drives, top_down 값, 활성 link index를 포함한다. 초기값 hash와 전체 dynamics hash는 따로 기록한다.

ticks, graph 생성량, 경로 검사, group updates, signals, normalization, proof node 수, support 검사, wall time을 각각 보존한다. 미측정 에너지·peak memory·AdaptiveSession expansion은 null이다. OFF의 link 감소를 원래와 동일한 계산의 일반적 효율 개선으로 부르지 않는다. wall time에는 append-only 기록/fsync 비용이 포함된다.

## 9. 배포·원본 보존

실행기와 설치기는 작동한 R048 형식을 계승한다. 기존 파일을 수정하지 않고 R049 전용 경로만 추가한다. 부모 EXP-29의 원본을 건드리지 않고 run/parent에 정확한 사본을 둔다. 부모 manifest는 기준 commit의 blob으로 고정하고 모든 file hash를 대조한다. 줄바꿈 복원은 기존 hash와 정확하게 맞는 후보만 허용하며 과거 로그 생성/manifest 축소는 없다.

부모 verifier는 원본 snapshot의 `r048_cli.py verify`를 새 프로세스로 실행해 EXP-29와 그 부모까지 재검산한다. 새 snapshot은 부모 source 전체를 이어받고 새 R049 파일만 추가한다. 기존 R047/R048 self-test와 새 self-test도 실제 실행기에서 수행한다.

새 evidence는 Git 줄바꿈·filter·ident 변환을 막는 scoped 속성을 사용한다. 실제 clean-filter 출력과 ignore 상태를 읽기 전용으로 확인한다. 사용자 Git index, checkout, commit, push를 자동 변경하지 않는다. 테스트에서 사용하는 disposable Git fixture는 사용자 저장소와 별개다.

새 폴더 이름은 `r049-YYMMDD-<8자리 ID>`다. 부모 nesting으로 Windows 경로가 더 길어지지 않도록 R048보다 짧게 했으며, 정확한 시작 시각은 로그에 보존한다.

## 10. 이 단계 다음

이 단계는 잘 수렴하도록 kernel을 최적화하는 작업이 아니다. 신호·초기조건이 어떤 경계에서 영향을 주는지 정리하고 기존 R0.3.3 재검토/session 개입과 연결하는 후속 실험으로 돌아간다. 모든 경로를 이미 전개한 chain에서 tick만 늘리는 것은 Graph 재확장이 아니다.

다음에 별도 검증할 항목은 selective re-evaluation, 동일 자원의 공간 재사용×상태 재사용, 반복 경험에 따른 binding/강도 변화다. 이번 결과를 그 기능의 구현이나 실증으로 쓰지 않는다.
