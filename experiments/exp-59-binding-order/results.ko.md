# EXP-59 / R078 결과: 비동률 선호 유지와 동률 순서 민감도

## 결론

R077의 봉인 memory·config·world·공개 graph ID를 유지하고 edge 배열의 두 경로 블록만 교환했을 때, ON의 비동률 최초 circuit 선택과 최종 proof 지원 경로는 유지됐다. e3 score 0에서는 [e0,e1], 1에서는 [e2,e3]였다. 동률 0.6에서는 activation이 같고 후보 순서가 뒤집혔으며, 최초 선택과 최종 proof 지원 경로가 [e0,e1]에서 [e2,e3]로 바뀌었다. **이 조건에서 비동률 선호는 배열 교환에 유지되고 동률 선택은 후보 순서에 민감함이 observed**다.

OFF는 모든 score에서 최초 primitive 선택이 첫 블록을 따랐지만, 최종 proof가 항상 그 경로 하나로 끝난다는 예측은 falsified다. 교환 배열·score 0은 첫 경로를 처리한 뒤 다른 경로를 추가 확장하고 최종적으로 [e0,e1]을 지원 경로로 선택했다. 최초 선택·경로 inventory·최종 proof 지원·terminal adoption을 구분해야 한다.

## 관찰

원자료: `HCR-Evidence/exp59/r078-20261001T012408Z-598761f4db`. 새 native 평가 12회이며 재학습·feedback·host correction·자동 retry는 0회다. R077 과거 journal 9개의 재검산은 부모 evidence 확인이고 새 증거로 합산하지 않았다. 모든 평가의 raw correctness·채택 correctness·채택 값은 True, `D_DAG`는 2였다.

원래 배열의 6셀은 R077과 입력·memory·config가 같은 결정적 재현이며 activation·정수 비용도 일치한다. 배열 개입 예측을 새로 구별하는 입력은 교환 배열의 6셀이다. 실행수 12를 서로 다른 독립 발견 12개나 같은 조건의 재현을 새로운 독립 지지로 세지 않는다.

원래 배열은 [e0,e1,e2,e3], 교환 배열은 [e2,e3,e0,e1]이다. ON의 최초 pool은 모두 같은 pattern ID의 두 완결 binding뿐이었다. 공개 ID 경로로 대응하면 후보 순서만 반전됐고 각 경로의 activation은 그대로였다. prior/mismatch는 모두 0, prefix는 0이다. 양방향 inhibition과 모든 후보의 binding·eligibility·state·순서를 독립 검산했다. score 0에서 [e2,e3] activation은 0.0282763008402952로 ineligible이었다. 동률에서는 두 activation이 모두 0.9918157251346338이다. score 1의 작은 약 8.24e-6 차이도 배열 교환 뒤 유지됐다.

| e3 score | ON 최종 지원: 원래 / 교환 | OFF 최종 지원: 원래 / 교환 | ON expansion·tick: 원래 / 교환 | OFF expansion·tick: 원래 / 교환 |
| --- | --- | --- | --- | --- |
| 0 | [e0,e1] / [e0,e1] | [e0,e1] / [e0,e1] | 1·67 / 1·67 | 2·33 / 3·116 |
| 0.6 | [e0,e1] / [e2,e3] | [e0,e1] / [e2,e3] | 1·65 / 1·65 | 2·33 / 2·33 |
| 1 | [e2,e3] / [e2,e3] | [e0,e1] / [e2,e3] | 1·65 / 1·65 | 2·33 / 2·33 |

ON의 pool/decision tick은 score 0에서 34/33, 0.6·1에서 32/33이다. OFF 교환 배열·score 0의 첫 decision network는 35 tick 뒤 goal activation 0.019030482450930503으로 stable_decision에 도달했고 `negative_requires_dependency_coverage`를 기록했다. 이때 공개 readout-ready가 아니고 pending value는 null이었다. 다른 경로 확장 후 두 경로 network에 81 tick을 사용해 goal activation 0.9999922914575685, raw value True와 채택 True로 끝났다. 이는 host가 후속 판단을 교정한 실행이 아니다.

score 0의 중립은 개별 edge의 관측 drive가 0이라는 계약이다. 모든 edge가 0/None일 때의 전체 UNSUPPORTED 규칙과 구분한다. 이 셀에서는 다른 edge가 비영 score이므로 첫 network의 goal<0.5가 내부 잠정 candidate_value=False와 coverage 진행으로 연결됐다. 따라서 작은 양수라도 goal이 0.5를 넘지 않으면 같은 coverage 동작이 남을 수 있다. 또한 kernel의 margin은 `abs(2*goal-1)`이므로 동률 pool의 stable_decision을 후보 사이의 분리 근거로 사용하지 않는다.

그 특이 셀의 `proof.paths`에는 [[e2,e3],[e0,e1]]가 있지만, `Proof.final=r:1:1`의 dependency closure와 assumed edges는 [e0,e1]만 지원한다. 원래 동결 집계의 `proof_edge_id_paths`는 경로 inventory를 보존하는 필드다. 이를 최종 지원 경로와 동일시하지 않도록 실행 후 `HCR-Evidence/r078-validation/proof-support-audit.json`에서 final ancestry·path index·depth·terminal path ranking을 별도 검산했다. raw·동결 summary·예측은 변경하지 않았고 새 native 실행도 없다. inventory 판정과 실제 final 지원 판정 모두 OFF 첫 경로 고정 예측을 반증한다.

동결 예측 여섯 항목 중 비동률 최초 선택/경로 inventory, 동률 최초 선택/경로 inventory, OFF 최초 선택은 supported이고 OFF 단일 첫 경로 inventory는 falsified다. 모든 ON proof inventory가 단일 경로여서 final 지원 검산도 같은 결론이다. 모든 비교는 판정 가능했고 가설 반증을 장치 실패로 처리하지 않았다.

독립 journal 12개와 pool recurrence의 최대 오차는 5.551115123125783e-16이다. 원자료 변조 11종, 집계 변조 13종, 최종 proof ancestry 변조 4종을 거부했다. 최종 core 회귀 1회는 602개 중 599 pass·기존 환경 skip 3·새 실패/skip 0이다. bundle·ZIP·원본/복사 R077·현재 동결 source bytes를 대조했다. 근거는 `HCR-Evidence/r078-validation/delivery-verification.json`에 보존했다.

## 해석

R077의 비동률 선택을 첫 slot이나 앞선 경로 고정만으로 설명할 수는 없다. 실제 edge ID의 높은 score 경로 선호가 블록 위치를 바꿔도 유지됐기 때문이다. 반면 동률은 앞선 native 후보를 따라 선택이 바뀌므로 입력 order→후보 order→최초 선택/proof 연결이 이 조건에서 partially-supported로 올라간다. slot 경로가 같다는 이유로 공개 graph identity가 같거나 다르다고 판단하지 않았다.

OFF에서 최초 primitive 선택은 배열 순서를 따르지만 final 지원은 항상 최초 경로를 따르지 않는다. score 0의 배열 교환은 first route·후속 dependency coverage·계산 궤적·비용을 바꿨다. ON은 모든 셀에서 expansion을 줄였고 교환 배열·score 0에서는 kernel tick도 116에서 67로 줄었지만, 나머지 다섯 셀에서는 tick을 늘렸다. 따라서 R077의 비용 결론은 이번 조건 집합에서 조건부로 수정된다. 단위가 다른 expansion·tick·검사·wall time을 합치거나 전력·총 효율로 일반화하지 않는다.

R077에서 OFF가 모든 score에 [e0,e1]을 썼다는 관찰도 원래 배열의 조건으로 제한된다. R078 교환 배열의 score 0.6·1에서는 OFF가 [e2,e3]를 지원하므로, R077의 ON/OFF 경로 대조를 입력 순서와 무관한 회로 효과로 일반화할 수 없다.

## 대안 설명

블록 순서 개입은 observation digest·내부 node/binding ID·native group/후보 순서도 자연히 바꾼다. 이 관찰만으로 후보 order의 독립 인과 효과를 identity/digest 배치와 완전히 분리하지 못한다. inhibition·top-down recurrence·selector·scheduler가 함께 작동하며 ON/OFF는 inhibition 단독 개입이 아니다. OFF score 0의 차이는 neutral evidence·first route·음성 잠정 수렴 뒤 coverage 조건의 결합과 양립한다. 한 authored world·한 memory·두 배열만으로 일반적인 순서 불변성이나 최적/학습된 scheduling을 주장할 수 없다.

## 판별 실험

다음 후보는 OFF 교환 배열의 score 0에서 나타난 coverage 전환을 먼저 구별하는 것이다. 동일 graph·ID·memory·config·world와 배열을 고정하고 e3를 neutral 0에서 작은 양수로 바꾸되, 최초 decision network의 goal state·잠정 progress reason·ready 경계·후속 expansion·최종 ancestry·비용을 보존한다. 원래 배열과 ON은 대응 대조로 두고, 구체적 score·예산·예측은 다음 세션에서 native 실행 전에 동결한다. 이전 원자료를 추가 실행으로 확장하지 않는다.

후속 예측의 경계는 단순히 e3가 0인지 양수인지가 아니라 첫 network의 goal 0.5 readout threshold와 수렴 상태로 정해야 한다. 관측 방향성·kernel의 연속 반응·runtime의 ready/coverage 규칙을 별도로 판정한다.

## 현재 주장 가능한 범위

비동률 ON 선호의 블록 교환 유지와 동률/OFF 최초 선택의 배열 민감도는 이 고정 native 조건에서 observed다. OFF 최종 지원의 단순 첫 경로 가설은 falsified이며, neutral·coverage와의 연결은 raw progress로 partially-supported다. inhibition 필요성·독립 의미 이해·일반 HCC 우위·독립 학습 효율·인간/생물학적 메커니즘은 hypothesis 또는 unsupported로 남는다. 새 독립 발견 표본은 0, energy·peak memory는 null이다. 별도 연구자 감사·클라우드 환경 검증은 실행하지 않았다.
