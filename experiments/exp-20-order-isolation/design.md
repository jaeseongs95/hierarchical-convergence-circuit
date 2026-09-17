# EXP-20 / R0.3.9 — identity 고정 · 분기 배열 순서 단독 조작

## 결론에서 출발한 연구 질문

코드 기준선은 main의 `8713f17eedf684b8392f3d07d9d67a3b8f8f61cd`다. EXP-19의 `three_branch_l3_early / legacy`에서 사후 선택은 170 native ticks, 온라인 선택은 102 ticks를 사용했고 같은 지지 정답을 채택했다. `late`에서는 두 방식 모두 170 ticks였다. 기존 EXP-19 생성기는 분기 배열과 함께 edge ID 배치·episode ID도 바꾸었다. 이 선행 관찰을 새 독립 증거로 다시 합산하지 않는다.

근거 파일: 기준 commit의 `HCR-Evidence/exp19/r038-20260917T121349_552337Z/analysis/paired.csv`, `raw/t0061.json`, `analysis/records/t0061.json`, `tools/r038_early_adoption/spec.py`.

이번 질문은 **외부 identity와 관계·관측값을 고정해도, 분기 배열 순서만으로 지지 경로 형성 시점과 온라인 절감량이 달라지는가?**다. ID 효과의 크기를 직접 측정하는 실험은 아니다.

## 입력과 개입

EXP-19의 `three_branch_l3_early` observation을 원문 기준으로 재사용한다. episode ID는 `exp19-input-10`, revision은 0이다. S는 `e0: s→a0`, `e1: a0→g`이며 두 score는 0.92다. M은 `e2: s→b0`의 missing score와 `e3: b0→g`의 0.92다. D는 `e4: s→c0`의 -0.92, `e5: c0→c1`, `e6: c1→g`의 0.92로 구성된다.

고정 항목: node/edge/episode ID, revision, 시작·목표, ID별 관계와 관측값, missing/zero 의미, 평가 world의 ID별 truth, 학습 memory, kernel config, 예산. 변경 항목은 **S/M/D 분기 블록이 observation.edges 배열에 놓이는 순서 하나**다. 각 분기 내부의 forward edge 순서는 유지한다.

순열은 SMD, SDM, MSD, MDS, DSM, DMS의 6개다. 각 순열 × legacy/route_only × native/posthoc_support/online_support의 36개 fresh session을 실행한다. 6개의 독립 topology나 36개의 독립 문제로 세지 않는다. 입력·결과에 따라 유리한 순열을 선별하지 않는다.

배열 위치를 바꾸면 observation digest, 내부 slot 번호, 그 hash에서 파생된 session/node reference는 자연스럽게 달라진다. 이를 강제로 동일하게 만들지 않는다. 여기서 추정하는 것은 고정된 명시적 입력 ID 아래에서 배열을 바꾸는 개입의 효과이며, hash·slot·tie-break 같은 구현 매개경로의 기여를 분리한 것은 아니다.

## 실행 구조

R038 `TimingTrial`, R037 `OnlineTrial`과 `NativeBackend`, R035 `run_policy`를 수정 없이 재사용한다. 새 native kernel 또는 selector를 만들지 않았다.

- native는 기존 native_saved가 채택할 때 종료한다.
- posthoc_support는 위와 같은 native 흐름을 끝낸 후, 현재 terminal readout에 support_first를 한 번 적용한다.
- online_support는 실제 readout마다 support_first를 적용하고 채택되면 종료한다.

Runtime에 전달하는 값은 observation/config/memory/scope/arm/budget뿐이다. case 이름, 분기 역할 라벨, permutation label, world, 평가용 opportunity는 전달하지 않는다. 최초 candidate를 selector 호출 전에 보존하고, 실패를 자동 retry하거나 reference를 보정하지 않는다. raw 값 반전·관측 요청·prior 전환·재학습은 수행하지 않는다.

원 memory는 EXP-19가 보존한 EXP-15 학습 seed를 사용한다. 새 trial마다 복사하여 시작하며, 기존 완성 Graph를 재사용하지 않는다. 기록의 native schema가 R037, timing wrapper schema가 R038인 것은 의도된 재사용이다. 외부 EXP-20 plan/raw/analysis schema만 새 버전이다.

## 예측과 판정

배열 순서가 경로 형성 순서를 바꾸고 지지 경로 뒤에 frontier가 남으면, 기존 native 보류와 support-first 채택이 갈리는 경계가 발생할 수 있다. 이 경우 사후군과 같은 정답을 유지하며 온라인 native ticks가 감소할 것으로 예측한다.

지지 경로가 마지막에 형성되면 채택 개선은 남아도 추가 계산을 생략할 기회는 없을 수 있다. 기존 native도 같은 시점에 지지 출력을 채택하면 selector 온라인화의 추가 이득은 없어야 한다.

모든 순열에서 결과·경로·비용이 같다면 이 입력 범위에서 배열 효과를 관찰하지 못한 결과다. 그것만으로 과거 차이의 원인이 ID였다고 확정하지 않는다. 효과 발생, 절감, 정답은 audit 통과 요건이 아니다.

## 측정

순열 내부의 3군에서는 첫 native view, native/posthoc의 전체 semantic trace와 비용, online의 native prefix를 비교한다. native ticks 절감은 `posthoc − online`이며, 같은 출력·외부 정답·prefix 정합성을 함께 요구한다.

순열 간에는 raw slot 번호를 직접 동일시하지 않는다. 독립 evaluator에서만 slot을 **해당 원문 observation의 변경되지 않은 edge ID**로 대응한다. `completion_trace`는 완성 경로의 ID 순서, expansion 번호, event seq를 보존한다. 완성 순위는 event 내 append 순서를 포함하므로 같은 expansion인지도 함께 본다.

다음 경계를 구분한다: 지지된 completed path 최초 readout, activation과 raw True까지 만족하는 최초 readout, frontier 잔존과 native 보류까지 만족하는 최초 differential opportunity. `first_supported_readout_ticks`는 두 번째 경계(채택 가능한 지지 경로)의 시점이다. 최종 proof의 D_DAG와 native proof의 D_DAG도 기록한다. 이번 실험은 D축이나 정답 proof 길이를 바꾸지 않는다.

Native ticks, advance/expansion, selector 경로·edge 검사, proof 생성/재사용은 별도 단위다. 전체 시간·전력 절감으로 합산하지 않는다. 정정된 assumptions_checked / supported_assumptions / unsupported_assumptions를 유지한다. 채택 proof가 없을 때 최종 가정 수 0과 원 native proof의 지지 실패는 다른 의미다.

## 원자료와 독립 검산

생성 `spec.make_cases`와 별도의 `input_audit`가 6개 입력의 정확한 ID·관계·score·world·순서·대응표를 검사한다. Canonical observation은 원자료 fingerprint로 고정하고, parent EXP-19 raw manifest SHA-256도 고정한다. 전체 EXP-19 verify가 실행기 preflight에 포함된다.

Native 상태·제어·proof·사후 경계의 재생은 기존 독립 audit_trial을 사용한다. 생산 TimingTrial.run 또는 run_policy를 재호출하여 정답 판정하지 않는다. 새로운 trajectory mapping은 평가 후에만 적용하며 원 native packet을 수정하지 않는다.

기존 2개 대조 입력 × prior 2 × arm 3의 native self-test는 배포 연결 검사다. 신규 6개 순열을 native 사전 탐색하여 고르지 않는다. 합성 self-test·독립 audit의 재생 비용·12개 사전 검사 실행을 36개 본 실험 결과와 섞지 않는다.

실패는 원문/부분 상태/traceback으로 보존하고 첫 실패에서 중단한다. 재실행은 사용자의 새 실행이며 새 폴더에 기록한다. 기존 plan/raw/analysis를 덮어쓰지 않는다.

## 주장 가능한 범위

이 장치는 하나의 고정된 topology에서 입력 배열 순서의 효과를 분리하는 최소 대조다. 효과가 있으면 명시적 ID 재명명 없이도 차이가 생긴다는 근거다. ID가 무관함, 일반 topology 전체로의 일반화, HCC 학습 원리 전체, LLM hidden state 또는 인간 뇌 메커니즘까지 증명한 것으로 확대하지 않는다.
