# R079 이후 최소 판별 후보

R078 교환 OFF·e3=0의 잠정 stable false→dependency coverage→다른 final 지원은 R079에서 재현됐다. R079의 새 양수0.05/0.2/0.4는 모두 첫 stable true·ready였고 ambiguous는 없었다. 따라서 “이번 새 양수 grid 중 비true가 있다”는 예측은 반증됐다. 그러나 검사한 양수점의 성공은 sign 자체의 충분성을 입증하지 않는다. 0과0.05 사이가 비어 있다.

다음 후보는 같은 R077 memory, config/world/public IDs, 교환 배열 [e2,e3,e0,e1], OFF만 고정하고 e3∈{0,0.005,0.01,0.02,0.03,0.04,0.05}를 실행하는 7셀이다. 0/0.05 두 셀은 R079 재현, 내부 다섯 점은 새 입력이다. 이는 아직 동결되지 않은 제안이며 이번 턴에서 실행하지 않았다. 사전 source·construct 검토에서 더 작은 장치가 같은 대안을 구별하면 그 이유를 먼저 기록한다.

대안은 검사 가능한 양수에서 첫 true가 유지되는 설명과, 작은 양수에서도 stable_false/ambiguous 또는 안정성 budget 경계가 존재하는 설명이다. 첫 decision status+같은 생성 advance progress.kind, candidate_value와 ready/completeness, residual/stable_steps/ticks, 모든 후속 network·final ancestry를 그대로 측정한다. 없음/측정불가/unstable·budget 종료는 false로 합치지 않는다. 한 점에서 실패해도 점수나 budget을 결과를 본 뒤 늘리지 않는다. ambiguous를 기대한다고 반드시 관측되는 것은 아니며 전체 구간의 임계값/단조성을 주장하지 않는다.

이번 original OFF와 ON first decision은 모두 같은 goal·33tick이었다. 전자는 직접 e3→goal 경로가 없는 불변성 대조였고 ON의 새 정보는 주로 pool의 activation gap·선택·수렴 tick이었다. 따라서 다음 OFF readout 경계 질문에 ON·원래 배열을 자동으로 다시 곱하지 않는다. 필요성이 새로 생기면 별도 계약으로 설명한다.

0.05의 OFF71tick·ON pool68tick과 큰 goal 변화는 느린 수렴·여러 안정 영역 등의 수식 분석 후보를 만든다. fixed-point/안정성 분석은 새 native 독립 증거로 합산하지 않는다. gate 필요성을 평가하려면 gate 자체 개입이 별도로 필요하며, 현재 고정 runtime score 개입과 섞지 않는다.

후속 harness에서는 R079의 보조 label 보완을 처음부터 명시해야 한다. pending cost.wall_seconds=0을 실제 시간으로 사용하지 않고 active_seconds/finish duration을 보존한다. inhibition 항은 weight×(2×previous_activation−1)이며, terminal state에서 계산한 항과 마지막 tick에 실제 쓰인 이전 state 항을 구분한다. R079 봉인 source/raw/summary는 역사 근거로 그대로 둔다.

한 authored graph/memory의 반복 실행이다. 재학습/feedback/host correction/automatic retry0, independent discovery0, energy·peak memory null을 유지한다. D_DAG·expansion·ticks·검사·wall time을 단일 비용으로 합산하지 않는다. 이번 결과는 전체 HCC/Graph↔Circuit 이론의 증명이나 반증이 아니다.
