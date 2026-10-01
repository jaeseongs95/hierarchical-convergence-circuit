# R079 / EXP-60: score와 첫 decision readout 경계

## 결론을 정하기 전의 질문
R078 교환 배열·OFF·e3=0은 첫 decision의 goal 0.019030482450930503에서 stable false에 도달하고 `negative_requires_dependency_coverage`로 재확장했다. 최종 True의 지원은 [e0,e1]이었다. 따라서 첫 선택/첫 상태/공개 readout/최종 채택은 같지 않다. 이번에는 작은 양수가 곧 첫 true·ready를 만든다는 설명과, 연속 state 및 안정성·readout 규칙 때문에 양수에서도 coverage가 유지될 수 있다는 설명을 구별한다.

## 조건과 표본 경계
R077 봉인 memory/3.json, config, world, 공개 node·edge ID, episode/revision 및 budget을 그대로 쓴다. e0=e2=1, e1=0.6; e3∈{0,0.05,0.2,0.4,0.6}. 배열은 [e0,e1,e2,e3]와 [e2,e3,e0,e1], 각 ON/OFF로 20셀이다. 각 배열·gate 안에서 score만 paired 개입한다. 0/0.6의 8셀은 R078의 결정적 재현 확인이고 0.05/0.2/0.4의 12셀은 새 score 입력 개입이다. 독립 발견·재학습·feedback 표본은 0이다. 최소 3개 양수 내부 점과 양끝 재현을 유지하며 결과를 보고 점을 추가하지 않는다.

max_advances=16, max_kernel_ticks=5120/session, kernel max_ticks=160/network 및 모든 나머지 config는 frozen_spec에 기록한다. host correction·automatic retry·policy/core 변경은 없다. observation digest와 내부 node/binding ID, group/후보 순서는 자연 산출물로 기록하며 동일하게 강제하지 않는다.

## 1차 측정과 대응
1차 지표는 첫 decision network의 `(convergence.status, 같은 생성 advance의 progress mismatch.kind)`다. journal에서 kind=decision인 최초 r02_network를 선택한다. pool 및 network_id=None인 선행 progress는 제외한다. transition의 반열린 event_start/event_end 범위로 network·settled·progress를 같은 advance에 대응하고, 해당 generation의 독립 재생 pending과 원 progress packet을 대조한다. progress가 없으면 null로 기록하며 이전 mismatch 상태를 이번 event로 오인하지 않는다.

goal, margin=abs(2*goal-1), residual, stable_steps, ticks, candidate_value(True/False/None), pending.value, ready, graph_complete, 남은 frontier와 공개 edge 경로를 따로 기록한다. stable_decision만 candidate_value를 읽는다. margin threshold=0.3에서 안정 goal (0.35,0.65)는 stable_ambiguous이고 None을 유지한다. stable_false는 negative_requires_dependency_coverage, ambiguous/None은 unresolved_or_no_goal_candidate로 이어질 수 있다. 재확장만으로 양자를 구별하지 않는다. ready는 true candidate 또는 graph complete에서 가능하므로 ready와 true를 동일시하지 않는다.

단일 e3=0은 grounding 방향성 분류상 neutral이다. 전체 unsupported는 모든 edge가 0/None이고 판단 prior가 없을 때 적용되며 이번 혼합 입력에는 해당하지 않는다. 개별 neutral은 전체 판단 유보가 아니다. network 부재/상태·대응 측정 불가는 measurement_failure/null, 관측된 budget/oscillating은 그대로 보존하고 안정 상태 가설에는 not_evaluable로 둔다.

## 동결 예측
- P1 positive_sign_suffices: 교환 OFF의 모든 양수 0.05/0.2/0.4/0.6에서 첫 stable_true·ready이며 같은 advance의 progress가 없다. 양수 한 점의 stable_false 또는 stable_ambiguous·ready=False는 반증이다.
- P2 positive_subthreshold_exists: 교환 OFF의 새 양수 0.05/0.2/0.4 중 적어도 하나에서 stable_false/ambiguous·ready=False와 해당 progress가 유지된다. 세 점이 모두 stable_true·ready면 이 유한 grid 예측은 반증이다. 어떤 특정 점이 ambiguous라는 점예측은 하지 않는다.
- P3 original_off_stable_true: 원래 배열 OFF의 다섯 점은 첫 stable_true·ready다.
- P4 on_stable_true: 두 배열 ON의 다섯 점은 첫 decision stable_true·ready다.
- P5 on_public_selection: score<0.6은 [e0,e1], 0.6 동률은 첫 native 완결 후보를 선택한다. 동률은 후보 activation 차이≤2e-12일 때만 평가한다.

보편 예측은 측정 가능한 반례 하나면 falsified이며, supported에는 해당 전 셀의 evaluable이 필요하다. 존재 예측은 관측 증인 하나면 supported, 반증에는 모든 후보점의 evaluable이 필요하다. 예측 성공은 장치 성공 조건이 아니다. source의 gate 규칙 재생 일치는 구현 검산이지 gate 필요성의 독립 인과 증거가 아니다.

## 후속 궤적·증명·비용
모든 network와 후속 advance·expansion·선택을 연결한다. proof.paths는 inventory로 보존하고 Proof.final에서 부모 closure와 실제 final 지원 경로·D_DAG를 따로 계산한다. raw decision, grounding readout, terminal adoption을 분리한다. ON pool의 모든 binding/circuit/public edge ID, activation, eligibility, prior/mismatch, inhibition 입력, 후보 순서를 보존한다. 후보 activation gap과 pool goal margin을 별도 열로 기록한다. pool stable_decision은 후보 간 승리/분리의 뜻이 아니다.

D_DAG, expansions, kernel ticks(pool/decision별), binding/selector/기타 정수 검사, wall seconds는 합산하지 않는다. energy와 peak memory는 null이다. ON/OFF는 pool·binding·reuse 전체 개입이며 inhibition 단독 효과가 아니다. 최종 정확도가 같아도 궤적과 비용이 다르면 다른 계산이다.

## 검증과 주장 한계
별도 프로세스의 evaluator가 기존 독립 session/equation/proof/readout 검산을 재사용한다. 생성 worker와 runtime/selector/dynamics 구현을 import하지 않는다. source·memory·world·config·raw hash, slot→public ID, recurrence, progress/ready, final ancestry와 요약을 원자료에서 계산한다. 별도 synthetic 상태 분류/경계 self-test와 raw/metric/summary 변조거부를 native20에 합산하지 않는다. 최종 core 회귀는 구현 확정 후 1회만 수행한다. 원클릭은 freeze→self-test→native→독립검산→요약 검증→회귀→bundle이며 Git 조작은 넣지 않는다.

고정 grid가 ambiguous를 관측하거나 경계를 bracket하지 못하면 그대로 한계로 남긴다. 인접 관측점 사이의 유한 비교는 정밀 threshold 추정이나 전 구간 단조성의 증거가 아니다. readout gate 자체 개입이 없으므로 필요성의 독립 인과 효과는 미판정이다. 일반 HCC·인간 사고·학습 우월성으로 확대하지 않는다.
