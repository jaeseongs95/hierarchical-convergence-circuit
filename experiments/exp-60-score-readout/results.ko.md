# R079 / EXP-60 결과: 검사한 양수점에서 첫 readout 허용

## 결론
고정 grid에서 교환 배열 OFF의 새 양수 0.05·0.2·0.4는 모두 첫 decision에서 stable true·ready에 도달했다. e3=0은 잠정 stable false와 `negative_requires_dependency_coverage` 뒤 재확장했다. 따라서 동결 P2의 **“새 양수 세 점 중 비true·coverage 유지가 존재한다”는 유한 grid 예측은 falsified**다. P1은 검사한 양수점들에서만 supported다. 두 예측은 같은 대안 판별 한 건이며 별도의 독립 지지 둘로 세지 않는다.

이 결과는 **모든 양수 또는 sign 자체가 충분하다**는 원인 설명을 입증하지 않는다. (0,0.05)에는 관측점이 없으며, ambiguous도 관측되지 않았다. 안정 상태·readout 규칙은 재생됐지만 gate 자체의 필요성은 개입하지 않았다.

## 관찰
원자료: `HCR-Evidence/exp60/r079-20261001T021912Z-016c6bc358`. 원클릭 `Run-HCR-R079.cmd`는 exit 0이며 자동 retry·host correction 없이 완료했다.

20회 native 실행 = R078 입력의 재현 8회(0/0.6) + 새 score 입력 12회(0.05/0.2/0.4). 새 입력 12회 중 첫 readout 경계를 직접 구별하는 것은 교환 OFF 3회, 원래 OFF 3회는 불변성 대조, ON 6회는 pool·선택 대조다. 재학습·feedback·새 독립 발견 표본은 0이다. 재현 8셀은 입력·native journal event 전체·final ancestry·정수 비용이 R078과 일치했다.

### 교환 배열 OFF의 첫 decision과 후속 결과
| e3 score | 첫 status / candidate | 첫 goal | 첫 network ticks | 같은 advance의 progress | 전체 kernel ticks | expansions | final 지원 |
|---:|---|---:|---:|---|---:|---:|---|
| 0 | stable_decision / False | 0.019030482450931 | 35 | negative_requires_dependency_coverage | 116 | 3 | ['e0', 'e1'] |
| 0.05 | stable_decision / True | 0.984715809703183 | 71 | 없음 | 71 | 2 | ['e2', 'e3'] |
| 0.2 | stable_decision / True | 0.987331227943767 | 35 | 없음 | 35 | 2 | ['e2', 'e3'] |
| 0.4 | stable_decision / True | 0.987678837775122 | 33 | 없음 | 33 | 2 | ['e2', 'e3'] |
| 0.6 | stable_decision / True | 0.987732595757791 | 33 | 없음 | 33 | 2 | ['e2', 'e3'] |

e3=0의 첫 network는 graph_complete=False, ready=False, candidate_value=False이며 pending.value는 None이다. 공개 negative 판단을 채택한 것이 아니다. 이후 [e0,e1]을 확장해 두 경로 network 81 tick을 추가하고 True를 채택했다. 이 셀의 proof.paths inventory는 두 경로이고 Proof.final의 부모 closure는 [e0,e1] 하나를 지지한다. 양수 네 셀은 첫 candidate True·ready, graph_complete=False인 상태로 끝나며 [e2,e3]가 final ancestry다.

모든 20셀에서 최종 raw decision·readout 채택값은 True이고 world상 정답이며 D_DAG=2다. 첫 안정 상태, 공개 ready, graph complete, final adoption을 서로 대신 사용하지 않았다. 첫 network 이전 `network_id=None` progress와 생성 advance의 progress도 분리했다. 측정 불가·budget 종료·oscillation은 이번 native에서 관측되지 않았다.

### ON의 pool과 선택
두 배열 ON은 모든 점에서 첫 decision goal=0.9877325957577907, 33 tick으로 같았다. 원래 OFF의 다섯 점도 같은 goal·33 tick이었다. 이들은 첫 goal 수치의 score 효과를 새로 지지하는 셀이 아니다. 원래 첫 decision program은 [e0,e1]만 goal로 연결한다. 다른 group의 residual이 전체 종료 시점을 결정할 가능성은 source상 있지만 이번 grid에서는 종료 tick까지 불변이었다.

아래 gap은 공개 경로 [e0,e1] activation − [e2,e3] activation이다. 두 배열에서 허용오차 2e-12 안에 같다.

| score | pool ticks | 후보 activation gap | pool goal margin | ON 전체 ticks |
|---:|---:|---:|---:|---:|
| 0 | 34 | 0.967069718031 | 0.980684049363 | 67 |
| 0.05 | 68 | 0.00200562379023 | 0.999990925278 | 101 |
| 0.2 | 35 | 0.000267587284985 | 0.999991018203 | 68 |
| 0.4 | 32 | 3.58598962151e-05 | 0.999990947868 | 65 |
| 0.6 | 32 | 0 | 0.99999096203 | 65 |

score0에서 [e2,e3]는 eligibility=False, 0.05부터 두 후보 모두 True였다. score<0.6의 선택은 [e0,e1]이며, 0.6의 정확한 동률에서는 첫 native 후보를 선택해 원래 배열은 [e0,e1], 교환 배열은 [e2,e3]다. gap이 3.586e-5인 0.4에서도 선택이 갈렸으므로 pool stable_decision이나 큰 goal margin을 후보 간 강한 분리로 해석할 수 없다. P3/P4/P5는 각 동결 범위에서 supported지만, P3는 불변성 확인이고 P5의 새 입력 근거는 내부 점 ON 6셀이다.

### 비용과 보조 필드의 명시적 보완
ON은 전 셀 expansion1, 원래 OFF는 expansion2, 교환 OFF는 0에서 expansion3·양수에서 expansion2다. ON/OFF tick 비교는 score0 교환 셀에서 67/116이고, 0.05 교환에서는 101/71이다. 0.05의 ON 101 tick은 pool68+decision33으로 분해된다. tick 증가를 사고 깊이·노력·난이도·전력으로 해석하지 않는다. D_DAG, expansion, kernel ticks, binding·검사 counter와 wall duration은 합치지 않았다.

봉인 summary의 상속된 두 보조 label은 사후에 원자료로 구별했다. `rows[].wall_seconds`는 runtime pending cost의 0 값으로, 실제 소요시간이 아니다. `pool.candidates[].inhibition_inputs[].final_signed_input`는 이전 helper가 기록한 weight×terminal activation이며, kernel이 쓰는 중심화된 weight×(2×activation−1) 항이 아니다. 원자료·수치 재생·1차 지표·예측은 이 값들을 근거로 판정하지 않았다.

`HCR-Evidence/r079-validation/secondary-metric-clarification.json`에 native active duration, proof finish duration, finished decision duration, 겹침 가능한 capture duration, 실제 마지막 tick의 이전 state를 사용한 중심화 링크 입력, 종료 state의 중심화 항을 따로 재계산했다. `verify-delivery.py`가 동일 raw에서 재현한다. 원 봉인 summary와 source를 덮어쓰지 않았고 native/회귀를 추가하지 않았다. energy·peak memory는 null이다. 향후 이 원클릭의 봉인 summary를 읽을 때도 이 두 필드의 뜻을 적용해야 한다.

## 해석
R078의 “첫 경로가 final까지 유지된다”는 보편 예측 반증은 유지된다. R079는 그 예외가 이번 grid에서 e3=0에 한정됐음을 보였다. 검사한 최소 양수 0.05부터 첫 상태가 이미 높은 true goal에 도달해 후속 coverage 확장이 없었다. 단순히 zero와 positive라는 이름이 원인이라고 말할 수는 없다.

0.05의 첫 decision 71 tick과 pool68 tick은 0 또는 더 큰 score의 대부분보다 길다. 이는 같은 update·허용오차·budget에서 종료까지 필요한 수치 갱신 횟수 관찰이다. 경계 부근의 느린 수렴이나 여러 안정 영역이라는 해석은 가능하지만 현재 endpoint/trace만으로 특정 bifurcation·attractor 메커니즘을 확정하지 않는다.

## 대안 설명
- sign=0 경계에서의 구분과 (0,0.05) 내부의 작은 양수 임계 영역은 현재 관측점에서 구별되지 않는다.
- 연속 입력에 대한 비선형 recurrence, top-down 경로, stable_steps/residual·margin과 유한 budget의 결합이 관측된 상태 변경과 tick 변화를 낼 수 있다. 요소별 인과 기여는 분리하지 않았다.
- ON/OFF는 pool·binding·reuse·경로 전개 전체 개입이다. inhibition 단독 효과·필요성이나 일반 계산 효율 우위를 주장할 수 없다.

## 판별 실험
다음 최소 후보는 같은 memory/config/world와 교환 배열 OFF에서 (0,0.05) 내부를 사전에 정한 작은 grid로 확인하는 것이다. 0과 0.05는 재현 대조로 두고 양수의 stable_false/ambiguous 또는 budget 종료가 나오는지 같은 첫 status+progress metric으로 판정한다. 자세한 후보와 중단 규칙은 NEXT에 있으며 이번 턴에는 실행하지 않았다. fixed-point 수식 분석은 별도 수학적 근거이고 새 native 표본이 아니다.

## 현재 주장 가능한 범위
- observed: 봉인된 단일 authored graph/memory와 고정 config에서 위 유한 score들에 대한 첫 상태·선택·후속 ancestry·비용.
- falsified: P2의 새 세 양수점 중 coverage 유지점 존재 예측. 더 작은 양수에 대한 일반 가설이나 HCC 전체 이론의 반증이 아니다.
- hypothesis: (0,0.05) 안의 상태 변경 구조와 수렴 지연의 원인. ambiguous·정밀 임계값은 미관측이다.
- unsupported: sign 자체의 충분성, readout gate 또는 inhibition의 독립 필요성, 일반 학습·인간 인지·에너지 우월성.

## 검증과 선후
설계 동결 2026-10-01T02:09:45.653394Z → 실행 전 construct 보완 02:17:35.332338Z → 원클릭 self-test 완료 `2026-10-01T02:19:28.823103+00:00` → native 시작 `2026-10-01T02:19:28.823103+00:00` → native 종료 `2026-10-01T02:19:29.975790+00:00` 순서다. 최초 spec SHA256은 `c4422485087856f3b2fa405d4cd846f12acee6231a76ae11fb527f8e1a9ee592`, 보완 SHA256은 `e88617bd95e833ceec247aafc0bedb1e78d389ccdfc42957560287b79f60a1bd`다. 보완은 셀·점수·예측·metric을 변경하지 않았다.

독립 journal/recurrence·progress/readout·final ancestry 재생20, 기존 입력 재현8, raw 변조18종과 summary/측정 변조18종 거부를 통과했다. 최대 pool 재생 오차는 9.992007221626409e-15로 동결 허용오차 2e-12 이내다. self-test는 기존17 journal 재분석·grammar20·합성 readout6·margin4이며 새 native 표본이 아니다. 최종 core 회귀는 1회, 602개 중 599 pass·기존 Windows symlink skip3·새 실패/skip0이다. 클라우드 검증은 실행하지 않았다.

원클릭 실행 중 장치 실패·자동 retry는 없었다. Git 준비 단계에서 과거 01:55:15Z의 0바이트 index.lock을 발견해 활성 Git/열린 핸들 부재와 복원 preflight 뒤 원본을 `.git/index.lock.r079-preserved-015515`로 보존했다. 생성 원인은 unknown이다. 당시 index 전후 hash 동일성은 실행 중 assert로 확인했으나 실제 digest 두 값은 저장하지 못했다(`lock-evidence-limitation.json`). 기존 `.cmd`의 stat 변경 표시는 원본 바이트와 분리해 보존했다.

사후 전달 검산의 최초 실패 두 건도 보존했다. 카탈로그의 의도된 EXP60 등록만 frozen snapshot과 달랐던 경우는 이전 entries·상위 필드 불변으로 재검증했고, independent/native inhibition 값의 2.7755575615628914e-17 차이는 동결된 2e-12 오차 안에서 비교했다. `delivery-first-failure.json`, `delivery-numeric-diagnosis.json`과 각 diagnosis 검증이 근거다. 이 과정은 native 장치 실패나 자동 retry가 아니다.

self-test 완료와 native 시작은 pipeline에서 별도 `now()` 호출로 기록했지만 반환 timestamp가 동일했다. 이 wall-clock 기록만으로 둘 사이의 미세 시간 간격을 판별할 수는 없다. self-test subprocess exit0 영수증과 그 반환 후 native stage를 호출하는 고정 pipeline 순서가 실행 선후의 근거다.
