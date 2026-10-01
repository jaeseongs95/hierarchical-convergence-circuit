# R080 / EXP-61 결과: 작은 양수에서도 첫 False와 coverage 확장

## 결론
고정 교환 배열 OFF에서 새 양수 .005/.01/.02/.03은 첫 `stable_decision`의 candidate False·ready False와 `negative_requires_dependency_coverage`를 보였다. .04와 재현 .05는 첫 True·ready였다. **H1의 검사한 양수점 첫 True 예측은 falsified, H2의 내부 다섯 점 중 stable 비True·coverage 증인 존재는 supported**다. 이는 같은 대안 판별 한 건이다. H3의 내부 다섯 점 중 첫 network budget/oscillation 존재 예측은 falsified다. 어느 점에서도 ambiguous·budget_exhausted·oscillating이 관측되지 않았다.

R079의 기존 유한 양수점 결과는 유지된다. 이번 더 작은 양수의 반례는 이 고정 조건에서 양수라는 사실만으로 첫 True가 보장되지 않음을 보여준다. 전체 HCC 이론의 증명이나 반증은 아니다.

## 관찰
원자료는 `HCR-Evidence/exp61/r080-20261001T030938Z-3e5b710c6f`다. native7=R079 입력 재현2(0/.05)+새 입력5(.005/.01/.02/.03/.04), 학습·feedback·새 독립 발견 표본0이다. 재현은 새 지지 표본으로 세지 않는다. source/runtime/scheduler/selector/readout/core는 변경하지 않았다.

| e3 score | 첫 category | 첫 goal | 첫 ticks | 같은 생성 advance progress | 전체 kernel ticks | expansions | final 지원 |
|---:|---|---:|---:|---|---:|---:|---|
| 0 | stable_false | 0.0190304824509305 | 35 | negative_requires_dependency_coverage | 116 | 3 | e0,e1 |
| 0.005 | stable_false | 0.0201491080953853 | 36 | negative_requires_dependency_coverage | 111 | 3 | e0,e1 |
| 0.01 | stable_false | 0.0215821736341908 | 44 | negative_requires_dependency_coverage | 114 | 3 | e0,e1 |
| 0.02 | stable_false | 0.0261172113472479 | 60 | negative_requires_dependency_coverage | 122 | 3 | e0,e1 |
| 0.03 | stable_false | 0.0368833202326897 | 95 | negative_requires_dependency_coverage | 152 | 3 | e0,e1 |
| 0.04 | stable_true | 0.984068755506494 | 111 | 없음 | 111 | 2 | e2,e3 |
| 0.05 | stable_true | 0.984715809703183 | 71 | 없음 | 71 | 2 | e2,e3 |

첫 False인 다섯 셀(0 포함)은 graph_complete=False·ready=False·candidate False·pending.value=None다. 공개 False가 채택된 것이 아니다. 선행 network_id=None progress는 1차 지표에서 제외했다. 이후 두 경로 network를 추가하여 모두 stable True로 끝났다. 후속 ticks는 score 순서대로 81/75/70/62/57이다. 이 셀들의 proof.paths inventory는 두 경로지만 Proof.final parent closure는 [e0,e1]만 지원한다. 첫 True인 .04/.05는 graph_complete=False에서 종료하며 inventory와 final 지원은 [e2,e3]다. 모든 final raw value·grounding readout·terminal adoption은 True, world상 정답이고 독립 재계산 D_DAG=2다.

모든 첫 network의 slot→공개 ID는 [e2,e3,e0,e1], 첫 route slot은 [0,1], 공개 경로는 [e2,e3]다. program_digest는 R079와 같은 `eff846df37d8cc635cb29c204281bbd23aa3226a636b4c8ff82ce2bb44a6343a`이며 e3(slot e:1)는 goal dependency closure에 실제 연결돼 있다. e:1 drive만 4×score로 달라진다. 첫 network 생성 advance는 반열린 event 범위로 유일하게 대응했고, candidate/ready/pending·progress 존재와 reason을 독립 규칙으로 대조했다. score 외 natural observation digest·node ID·궤적을 host가 같은 값으로 고치지 않았다.

.03은 첫 False 수렴95tick 후 두 경로 True57tick(총152)이며 .04는 첫 True111tick으로 끝난다. 첫 상태 변화는 관측한 이웃 점 .03/.04 사이에 있다. 이는 연속 구간의 정확한 임계값이나 단조성을 뜻하지 않는다. 전체 ticks는 116/111/114/122/152/111/71로 단조적이지 않다.

cost의 정수 counter·D_DAG·expansion·ticks와 실제 duration은 별도로 보존했다. OFF pool_metrics는 null/비해당이며 pool tick ledger는 관측된 0이다. pending cost.wall_seconds=0은 실제 duration이 아니다. native_active_seconds·proof_finish_seconds·finished_decision_wall_seconds와 겹칠 수 있는 capture_seconds를 분리했다. 모든 링크에 마지막 tick의 이전 state를 쓴 `last_tick_centered_link_input=weight*(2*previous_activation-1)`, 종료 state의 `terminal_centered_link_term`, 비중심 `terminal_uncentered_activation_product`를 따로 기록했다. 에너지와 peak memory는 null이다.

## 해석
R078의 교환 OFF zero 예외는 R079/R080에서 재현됐다. R079가 검사한 .05 이상에서 첫 True였던 사실은 새 내부 양수 .005~.03의 첫 False와 양립한다. 기존 P2의 세 점 예측 반증은 유지되며, 다른 domain의 R080 H2는 지지됐다. 이전 반증을 지우거나 이번 결과를 그 실험의 사후 성공으로 바꾸지 않았다.

이번 첫 False는 안정된 수치 상태이면서 아직 coverage가 부족한 잠정 판단이다. 이후 확장해 정답 True를 채택했다는 점에서 첫 안정성·최종 정답·재수정·trajectory를 분리해야 한다. D_DAG는 모든 셀에서2로 같지만 ticks/확장/final 지원은 다르다. 이를 사고 깊이·LLM 내부 계산·인간 인지·전력 차이로 일반화하지 않는다.

## 대안 설명
비선형 recurrence와 초기 state .5에서의 경로·top-down 연결·self-excitation·안정 종료 기준 조합이 유한 점의 두 상태 영역과 지연을 만들 수 있다. source와 raw는 같은 회로 구조의 연속 drive 변화를 확인하지만 어느 요소가 경계의 원인인지는 개입하지 않았다. .03~.04에 안정 영역 전환·느린 수렴·ambiguous 또는 유한 budget 영역이 있을 수 있으나 현재 점에는 그중 어떤 것도 직접 관측되지 않았다. 수학적 fixed-point 분석 없이 bifurcation/attractor 구조를 확정하지 않는다.

## 판별 실험
다음 후보는 같은 OFF 조건의 {.03,.0325,.035,.0375,.04} 5셀이다. .03/.04는 재현2, 내부3은 새 입력이며 아직 동결/실행하지 않았다. 첫 stable 상태와 별도 budget/oscillation 예측을 유지하고 사후 점수·budget을 추가하지 않는다. 별도의 고정점·안정성 수식 분석도 가능하지만 native 표본에 합산하지 않는다. 상세는 NEXT에 기록했다.

## 현재 주장 가능한 범위
- observed: 한 authored graph/memory·고정 config와 OFF 배열에서 위 7점의 첫 상태/progress·후속 경로·final ancestry·분리 비용.
- falsified: R080 H1의 유한 양수6점 첫 stable True 예측과 H3의 새 내부5점 첫 budget/oscillation 존재 예측.
- supported: R080 H2의 내부5점 중 stable 비True·ready False·coverage 증인 존재. 관측 증인은 False4개이며 ambiguous 지지로 바꾸지 않는다.
- hypothesis: .03/.04 사이의 더 세부 상태·수렴 구조와 그 인과 원인.
- unsupported: 정확한 연속 임계값·전구간 단조성·gate/inhibition의 독립 필요성·일반 학습 효과·에너지 또는 인간 인지 우월성.

## 장치 실패 보존과 실행 전 보완
첫 원클릭 `r080-20261001T030431Z-27c6c5c001`은 self-test 결과 dict의 중복 research_sample keyword 때문에 저장 직전 TypeError로 중단됐다. native0·core회귀0이며 source/로그/traceback을 보존했다. 자동 retry 없이 중복 키 한 개를 제거한 표적 검사와 실행 전 amendment를 기록했다. 수정 입력으로 새 원클릭을 명시적으로 실행했다.

독립 peer의 F1은 H1을 H2 coverage 증인 부재로 지지할 위험이었다. native 전에 H1 literal `stable_true+ready+no progress`를 직접 대조하고 H2는 별도로 유지했다. complete graph 비True는 일반 classifier상 H1 반례지만 H2 증인이 아니며 합성 검사로 확인했다. 고정 OFF source에서는 score를 읽지 않는 slot 순서·side exit 보존으로 첫 [e2,e3] route 때 [e0] frontier가 남는다. 원 동결 spec/design을 바꾸지 않고 construct 보완을 별도 기록했다.

F2는 hash 사슬에서만 거부된 raw 변조의 의미검사 공백이었다. native 전에 event 사슬·packet을 재해시한 대조군이 통과하고 status/goal/progress/coverage 변조가 독립 의미검사에서 거부되게 보완했다. 실제 raw15종 거부 중 재해시 event/input6종의 오류 메시지를 기록했다. e3 goal 연결은 측정값으로 보존해 기대와 다른 연결 여부를 apparatus 오류로 숨기지 않도록 했다. 최초 실패/보완은 봉인 native source에서 구분된다.

## 검증과 선후
설계 동결 2026-10-01T03:02:15.215585+00:00(spec SHA256 82ff34bd464606be117b2b4c8b99b95f12a5da8a47ce772c282a3285560aee04) 후 세 실행 전 보완을 기록했다. 성공 원클릭 self-test 완료 2026-10-01T03:09:46.195702+00:00 → native 시작 2026-10-01T03:09:46.195702+00:00 → native 종료 2026-10-01T03:09:47.092935+00:00 → 최종 검증 2026-10-01T03:12:25.551709+00:00다. 동등 UTC를 허용하며 별도 subprocess exit0 영수증과 순차 stage 호출, perf_counter stage duration을 보존했다. native stage monotonic duration은 0.8946802999998908초이며 세션의 active/finish 측정값과 다른 범위다.

독립 native journal 재생7·기존 R079 재현2·raw 변조15 거부(재해시 대조 통과/의미검사6 사유 포함)·summary 변조20 거부를 통과했다. self-test는 R077 기존9+R079 기존2 journal 재분석, grammar7·readout6/margin4·nonstable2 및 H1/H2·budget 합성 판정이며 새 native 표본이 아니다. 최종 core 회귀는1회,602개 중599 pass·기존 Windows symlink skip3·새 실패/skip0이다. 성공 원클릭 exit0, source/input/raw/ZIP byte 검증을 통과했다. 클라우드 검증은 실행하지 않았다.

독립 peer는 생산자/evaluator 코드를 사용하지 않은 JSON 재계산에서 원자료·표·first graph·goal 연결·final closure·재현과 H1/H2/H3 판정의 불일치0을 보고했다. 결과는 readout-ready 이전 잠정 False이며 terminal misconvergence 또는 e3 불통 판단으로 해석하지 않는다. H3 반증은 내부5점 한정이고 .03/.04 사이 budget 영역 가능성을 배제하지 않는다.
