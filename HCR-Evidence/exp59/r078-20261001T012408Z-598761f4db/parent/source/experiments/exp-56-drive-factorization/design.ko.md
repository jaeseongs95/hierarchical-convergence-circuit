# EXP-56 / R075: 두 evidence drive의 scale 분리

R074는 evidence gain 4→1에서 e:1과 c:0의 유한 score 반응이 커졌지만 e:0 배경도 함께 바뀌었다. 이번에는 그 혼합 원인을 분리한다. 기존 authored pool의 수식 연구를 마무리하기 위한 최소 대조이며 새 native 능력·학습의 증거로 쓰지 않는다.

## 동결 조건과 조작

봉인된 R072의 M0 program과 initial 0.5, top_down=True, 기존 kernel config와 budget을 그대로 사용한다. 모든 prior drive는 0으로 고정한다. e:0 score는 1, e:1 score는 0.6/0.8/1.0이다. memory·observation·core·historical evidence를 수정하거나 재서명하지 않는다.

e0 drive scale 4/1 × e1 drive scale 4/1 × e1 score 세 점으로 12 evaluator 조건을 계산한다. scale은 config의 evidence_gain 변경이 아닌 직접 drive 개입이다. config는 evidence_gain=4를 포함해 그대로 보존한다. 동시 4/4와 1/1의 여섯 조건은 R074 prior0/M0와 대응하며 새 발견 표본으로 세지 않는다. 혼합 scale 여섯 조건만 새 개입이고, 같은 자료의 재분석이므로 새 독립 표본은 0이다.

## 예측과 판정

e:0·e:1·p:0:0·p:0:1·c:0의 최종 상태와 동일 scale의 score0.8 대비 차이를 따로 기록한다. e:1과 c:0는 0.6에서 음수, 0.8에서 0, 1.0에서 양수 차이를 예측한다.

1. e0 배경을 4 또는 1로 고정해도 e1 scale 4→1은 e:1과 c:0의 절대 score 반응을 키운다고 예측한다. 이는 e1 drive 변화가 bundle 효과에 기여한다는 설명을 시험한다. e1 자체 포화를 유일한 원인으로 확정하는 검사는 아니다.
2. e1 scale을 4 또는 1로 고정할 때 e0 scale 4→1은 c:0의 절대 score 반응을 키운다고 예측한다. 이 예측이 지지되면 e0 배경도 candidate 반응에 기여한다. 반증이면 해당 방향 예측을 기각하고 관찰된 방향과 효과를 보존한다.
3. endpoint별 signed score effect interaction을 Δ11−Δ14−Δ41+Δ44로 계산한다. 여기서 Δab는 e0 scale=a/e1 scale=b의 score0.8 대비 차이다. 상호작용의 부호나 크기는 성공 조건으로 요구하지 않는다. 고정 초기 상태의 유한 차이이며 derivative나 전역 안정성의 측정으로 해석하지 않는다.

수치 검산 오차는 2e-12, 방향·크기 판정 오차는 1e-12다. 비율 분모가 판정 오차 이하이면 null이다. stable_decision과 stable_ambiguous는 서로 구분해 상태를 읽고, budget_exhausted·oscillating이면 차이·비율·상호작용을 null/not_evaluable로 보존한다. 예측 반증은 장치 검증 실패가 아니다.

## 실행과 주장 경계

`Run-HCR-R075.cmd`: 원본·source·plan/hash 동결 → 합성 self-test → 12 replay → 집계 → 독립 입력·recurrence·집계 검산과 R074 여섯 대응·변조 거부 → 최종 core 회귀 1회 → bundle/ZIP.

새 출력만 만들고 자동 retry·덮어쓰기를 하지 않는다. 최초 실패와 부분 자료를 보존하며 원클릭에는 Git 동작을 넣지 않는다. evaluator iteration은 native/kernel 비용이 아니다. native 선택·proof·expansion·decision cost·실제 에너지·peak memory를 부여하지 않는다. top_down의 독립 인과 역할, 여러 경쟁 후보, 다른 topology, 실제 learning·memory 형성·약화·안정 영역은 검증하지 않는다.

결과가 어느 방향이든 이 toy 수식의 분해를 계속 반복하기보다, 다음 단계에서는 실제 native 계산에서 score가 선택과 채택에 영향을 주는지 새로운 계약으로 질문한다. 현재 예측을 지키기 위한 메커니즘 추가나 기존 조건의 사후 변경은 하지 않는다.
