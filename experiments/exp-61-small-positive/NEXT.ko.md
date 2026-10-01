# R080 이후 판별 후보

R079의 작은 최소 양수 .05 첫 True와 zero 첫 False 사이를 R080 7셀로 검사했다. .005/.01/.02/.03은 첫 stable False·coverage 확장, .04/.05는 첫 stable True였다. ambiguous·oscillation·network/session budget 종료0, 최종 채택은 전 셀 True·D_DAG2다. 내부 양수의 비True 존재는 이번 유한 domain에서 지지됐으며 R079 P2의 세 점 반증은 유지한다.

다음 최소 후보는 같은 고정 runtime/memory/config/world/IDs/episode·배열[e2,e3,e0,e1]·OFF에서 e3={.03,.0325,.035,.0375,.04} 5셀이다. 양끝은 R080 재현2, 내부3만 새 입력이다. 이 제안은 아직 동결/실행되지 않았다. 한 턴 동안 사전 점수와 max_ticks160·session budget을 고정하고 결과에 따른 추가 점수·budget 연장·자동 retry를 하지 않는다. ON/원래 배열을 곱하지 않는다.

단순히 임계값 자릿수를 늘리기보다 내부점의 first stable False/True/ambiguous 또는 budget/oscillation이 어떻게 구별되는지가 목적이다. H1과 H2의 literal predicate·coverage 증인은 각각 직접 검사하고 measured nonstable은 안정 상태 예측의 not_evaluable로 남긴다. H3 별도 stability 질문은 실제 network status만 사용한다. Session external budget·measurement failure는 False/반증 증인이 아니다. proof.paths inventory·final parent closure·D_DAG·raw/readout/adoption·모든 후속 route와 frontier를 보존한다.

관측된 .03/.04의 first category 차이는 인접 점 차이이지 정확한 연속 임계값이나 단조성 증거가 아니다. .03 첫95tick 후 후속57tick, .04 첫111tick은 느린 수렴 등의 수식 검토를 유도하지만 원인 판정은 아직 없다. 별도 최소 fixed-point/안정성 계산은 같은 raw 재분석/수학적 근거이며 새 native 독립 표본으로 합산하지 않는다. 사전 source 검토에서 단순 refinement보다 이 대안을 더 잘 구별하는 장치가 있으면 동결 전에 근거를 기록해 선택한다.

R080의 최초 selftest TypeError는 native 전에 중복 keyword 수정으로 해결했고 실패본을 보존했다. 후속 harness는 성공한 봉인 source와 실행 전 보완을 기준으로 한다. 중심화 이전-state 링크 입력·종료-state 중심화 항·비중심 product와 실제 active/finish duration 정의를 유지한다. 재현은 새 연구 지지나 독립 발견으로 세지 않으며 학습/feedback/host correction/자동 retry0·energy/peak memory null을 유지한다.
