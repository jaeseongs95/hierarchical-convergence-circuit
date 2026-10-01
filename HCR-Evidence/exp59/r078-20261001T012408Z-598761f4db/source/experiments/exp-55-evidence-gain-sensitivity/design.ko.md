# EXP-55 / R074: evidence gain에 따른 유한 score 반응

R073은 score 증가와 함께 uncertainty prior가 줄어 기존 pool activation을 낮춘다는 수식 설명을 지지했다. 남은 질문은 prior를 고정했을 때 evidence-only 효과가 작은 이유다. 이번에는 기존 gain 4에서 양의 evidence가 포화된다는 설명과, 낮은 gain에서도 짧은 경로·top_down·prior 배치가 작은 효과를 유지한다는 대안을 비교한다. 같은 원자료의 계산이며 독립 표본을 추가하지 않는다.

## 동결 조건과 조작

봉인된 R072의 동일 program·initial 0.5·top_down=True·M0/M1 memory를 입력으로 쓴다. R073의 성공 run에서 evidence-only 여섯 궤적을 대응 자료로 고정한다. 기존 core, memory, observation, historical evidence를 수정하거나 재서명하지 않는다.

- gain은 4와 1이다. gain 하나를 바꾸면 e:0 drive도 4에서 1로 바뀐다. e0 score는 항상 1이다. 이는 evidence drive 전체의 gain bundle 개입이며 e:1 drive만 고정 배경에서 조작한 비교가 아니다.
- 각 gain·checkpoint 안에서는 e1 score 0.6/0.8/1.0만 달리한다. baseline은 같은 조건의 0.8이다.
- prior는 baseline score 0.8에서 계산한 기존 값으로 고정하거나, 모든 prior target에서 0으로 고정한다. score 조작과 prior 조작을 분리한다.
- 나머지 kernel config와 program·budget·초기 상태는 고정한다. gain 1의 config가 native memory signature와 호환된다고 해석하지 않는다. evaluator 수식에만 적용한다.

2 gain × 2 prior × 2 checkpoint × 3 score = 24개 evaluator replay다. 이 중 gain4/fixed-prior 여섯 개는 R073의 기존 계산과 대응한다. 새 native 실행·학습·feedback·독립 표본은 0이다.

## 실행 전 예측과 판정

`e:1`과 `c:0`의 최종 상태를 별도로 읽고 score 0.8 대비 차이를 계산한다. 각 조건에서 0.6은 음의 차이, 0.8은 0, 1.0은 양의 차이를 예측한다. 각 prior·checkpoint·endpoint 비교에서 gain1의 절대 차이가 gain4보다 `1e-12` 이상 커진다는 포화 설명의 예측을 노드별로 판정한다. 비율의 분모가 허용 오차 이하이면 비율은 null로 둔다. 방향과 효과 크기 예측은 검증 통과 조건이 아니며 반증도 정상 결과다.

e:1 반응만 커지고 c:0 반응이 커지지 않으면 downstream 경로 설명을 남긴다. 둘 다 커지면 이 gain bundle에서 포화 관련 설명을 제한적으로 지지한다. e0 배경 변화와 재귀 피드백까지 함께 바뀌므로 포화를 유일한 원인으로 확정하지 않는다. prior 0에서는 두 checkpoint의 숫자 입력·궤적이 같다는 예측도 별도로 판정한다.

수치 검산 허용 오차는 `2e-12`, 효과 방향·크기 판정 오차는 `1e-12`다. stable_decision과 stable_ambiguous는 수식 상태를 읽을 수 있으며 서로 구분한다. budget_exhausted·oscillating은 측정불가로 남기고 방향·비율은 null/not_evaluable로 둔다. evaluator iteration은 native/kernel 비용이 아니다. 실제 선택·expansion·decision cost·전력·peak memory를 부여하지 않는다.

## 실행과 근거

`Run-HCR-R074.cmd`: 원본·source·plan 동결 → 합성 장치 self-test → 24 replay → 분석 → 입력과 별도 recurrence로 매 tick·수렴·집계 검산 → R073 여섯 대응·변조 거부 → 최종 core 회귀 1회 → 원자료 bundle/ZIP.

새 출력 디렉터리만 생성하고 자동 retry·기존 결과 덮어쓰기를 하지 않는다. 실패와 부분 evidence를 보존한다. 합성 장치 검사는 연구 표본에 합산하지 않는다. 원클릭에는 Git 변경을 넣지 않는다.
