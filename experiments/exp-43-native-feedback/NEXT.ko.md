# 후속 판별 질문: 회로 형성 전후와 새 instance에서의 재사용

이 문서는 다음 단계의 제안이며 EXP-44의 동결된 실행 계약이 아니다. R062의 최종 결과와 현재 소스 계약을 확인한 뒤 별도 조건·입력·예산·반증 기준을 동결한다.

## 기존 질문과 겹치지 않는 범위

EXP-25는 이미 학습된 동일 seed에서 use_circuits ON/OFF의 총 효과를 측정했다. 해당 설계와 원자료를 기준으로 계보를 잇고, 같은 실험을 새로운 학습 증거로 다시 세지 않는다. 다음에 필요한 것은 기존 seed의 사용 여부만이 아니라 검증된 경험이 쌓여 회로가 형성되는 전후의 변화다.

## 최소 대조

기존 AdaptiveSession의 학습 API와 SubgraphCompiler를 사용한다. 실험자가 circuit을 직접 삽입하거나 성공할 때까지 반복하지 않는다. 사전 지정한 서로 다른 training episode와 외부 검증 feedback을 한 번씩 실행하고, 빈 memory와 각 episode 이후 memory를 보존한다. min_valid_episodes에 따른 pending→compiled 변경을 evidence·proof·episode provenance와 연결한다. 단순한 episode ID 재명명만으로 독립 경험이나 일반화가 생겼다고 주장하지 않는다.

형성 전 memory와 형성 후 고정 snapshot에 동일한 사전 지정 held-out 입력을 주며 각 snapshot에서 use_circuits ON/OFF를 비교한다. 네 cell의 예산·top_down·selector·scheduler·judgment prior를 동일하게 고정한다. route_only 사용 여부는 사전에 정하고 legacy와 한 pair에서 함께 바꾸지 않는다. 회로가 형성되지 않거나 새로운 입력에 binding되지 않아도 실패·노출 부재로 남기며 추가 학습이나 구조 수정으로 메우지 않는다.

새 instance는 최소한 training의 관측·episode를 재사용하지 않으며, ID 재명명과 실제 구성 변화는 다른 대조로 분리한다. training에서 보지 못한 primitive 조합 또는 분기 안에서 학습된 subgraph의 적용을 시험한다. 하나의 toy family 결과를 광범위 일반화로 부르지 않는다.

## 측정과 반증

처음부터 raw decision, proof의 가정하 유효성, 관측 support, readout 채택을 나눈다. formation 전후의 memory 구조·strength·binding·실제 circuit use·graph expansion·pool ticks·decision ticks·reference checks를 각각 기록한다. ON/OFF 뒤에 자연스럽게 달라지는 궤적·예약량을 host가 맞추지 않는다.

형성 후 ON에서 실제 reuse가 생겨도 채택 품질이나 ticks가 개선되지 않을 수 있다. 회로 형성, 회로 사용, expansion 감소, native ticks 감소, 품질 보존을 각각 독립 예측으로 두며 하나의 성공으로 다른 실패를 상쇄하지 않는다. 계산 단위가 다른 계수를 합산하지 않고 에너지는 측정 전까지 null로 둔다.

## 그다음 순서

학습 전후·reuse 기여가 구별되면, 오류·novelty 뒤의 재확장과 수정 유지 여부를 별도 단계에서 검증한다. 현재 learning.update_adaptive에는 실패한 사용 circuit의 약화와 재개 후 검증 기록 규칙이 있으므로 그 규칙부터 측정하며 새 메커니즘을 덧붙이지 않는다.

동적 edge 생성과 사전 확보한 latent connectivity의 비교는 그 뒤에 한다. 동일한 표현 가능 범위·용량·자원 조건에서 binding/강도 상태 변화의 효과를 분리해야 한다. 고정 잠재 연결과 동결된 학습 상태를 같은 것으로 취급하지 않는다.
