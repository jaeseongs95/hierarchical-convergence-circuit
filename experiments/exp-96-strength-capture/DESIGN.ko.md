# R50 / EXP-96 설계: 회로 강도 하나를 조작했을 때 포획 폭과 탈출 비용 — H07의 직접 시험이 현재 학습 규칙에서 가능한가

작성 2026-11-20. 이 문서와 [frozen_spec.json](frozen_spec.json)은 본 실행 전에 작성했고 실행 뒤에는 수정하지 않는다. 결과 문서에 두 파일의 SHA-256을 기록한다. 번호 R50 / EXP-96은 R49 / EXP-95 다음 순번을 잠정 사용한 것이다.

## 1. 출발점

- 동기 문서(`docs/AI chat/HCC_습관_고정관념_세션정리_2026-09-17.md`)는 Circuit Strength, Attractor Width, Escape Threshold를 후속 실험 변수로 제안했다. `evidence/claims.yaml`의 HCC-H07은 "attractor 강도가 커지면 익숙한 추론은 효율적이 되지만 수정 가능성이 줄어든다"는 파생 예측이다.
- 2026-10-15 연결표는 H07에 대해 "순수 attractor 강도 개입은 미입증"이라 적었다. EXP-50/52/53의 M0/M1 비교는 strength·version·failures·이력이 함께 바뀐 checkpoint 묶음이었고 결과 문서가 매번 "순수 strength 효과: unsupported"로 남겼다. 그 실험들은 `route_only`(학습 prior가 최종 판단에 들어가지 않음)에서 수행됐다.
- R0.2 기준선 검토(`docs/AI chat/R0.2 결과해석.md`)는 학습 3회와 9회의 수정 비용이 같았다고 기록했으나 원인은 분리하지 않았다.

## 2. 코드에서 읽은 사실 (실행 전)

`src/hcr/learning.py::update_adaptive`, `src/hcr/activation.py::instantiate_pool`, `src/hcr/workspace.py::adaptive_network`:

- 컴파일 시 `strength = 0.55`. 이후 서로 다른 episode의 첫 시도 정답마다 `strength += learning_rate × (1 − strength)` (learning_rate 0.25).
- 오답 feedback 한 번마다 사용된 회로의 `strength *= weakening` (0.2), `failures += 1`. `failures ≥ 3`이고 `strength < 0.05`이면 `active = False`.
- 회로의 prior drive는 `prior_gain × strength × balance × max(1 − |score|)`, `balance = episodes/(episodes+1)`. 학습 횟수는 strength와 balance를 **함께** 바꾼다.
- pool 자격은 `activation ≥ activation_threshold(0.55)`, `mismatch = max(0, −score) ≤ 0.80`, 안정 수렴.
- `legacy` 정책에서는 선택된 회로의 prior가 판단 network의 경로 노드와 goal의 drive로 들어간다. `route_only`에서는 0이다.

여기서 계산되는 값(엔진을 실행하지 않고 산술만):

| 학습 횟수 n | strength s_n | balance | 2·s·b (불확실성 1일 때 prior) |
|---:|---|---:|---:|
| 3 | 0.55 | 0.7500 | 0.825 |
| 4 | 0.6625000000000001 | 0.8000 | 1.060 |
| 5 | 0.7468750000000001 | 0.8333 | 1.245 |
| 6 | 0.81015625 | 0.8571 | 1.389 |
| 9 | 0.9199096679687501 | 0.9000 | 1.656 |
| 12 | 0.9662118911743165 | 0.9231 | 1.784 |
| 20 | 0.9966173739318038 | 0.9524 | 1.898 |

오답 한 번 뒤의 strength는 n=3에서 0.110, n=20에서 0.199다. 세 번 뒤에는 어떤 n에서도 0.008 미만이라 비활성화 조건을 만족한다.

## 3. 질문

- **Q1 (포획 폭)**: 강도가 커지면, 증거가 약하거나 반대인데도 회로 때문에 True로 수렴하는 입력 범위가 넓어지는가?
- **Q2 (순수 강도)**: 그 변화는 strength 숫자만 바꿔도 재현되는가, 학습 이력 묶음이 필요한가?
- **Q3 (탈출 비용)**: 오답 feedback으로 그 수렴에서 벗어나는 데 필요한 횟수가 학습량에 따라 늘어나는가?
- **Q4 (익숙한 입력의 이득)**: 강도가 커지면 익숙한 입력의 expansion·tick이 줄어드는가?

## 4. 고정 조건

- 엔진: `hcr.runtime.AdaptiveEngine`, `AdaptiveConfig()` 기본값, `top_down=True`. `src/hcr`는 수정하지 않는다.
- 과제: 2-edge chain(`chain(...)`), 공개 관측 `e0 = 1.0` 고정, `e1`을 조작한다. 참조 세계에서 e0는 열림, **e1은 닫힘**으로 고정한다. 따라서 평가 입력의 정답은 항상 False이고, True 판단은 모두 오답이다.
- 참조 판정은 엔진 밖 함수가 판단 결과만 받아 만든다. 엔진은 hidden truth를 받지 않는다. `World.measure`는 호출하지 않고(예외로 차단), revision 요청도 하지 않는다.
- 평가는 `FROZEN_EVAL`, 매 평가마다 memory 문서 사본으로 새 엔진을 만든다.

## 5. 조작

### 5.1 native 학습 memory (7개)
빈 memory에서 `legacy`·`TRAIN` 모드로 진실한 양수 chain(두 edge 모두 열림, score 0.92/0.92, episode마다 다른 정점 이름) 20개를 차례로 학습하고, n ∈ {3, 4, 5, 6, 9, 12, 20} 시점의 memory 문서를 snapshot한다. 하나의 학습 순서의 중첩 checkpoint이며 독립 학습 7회가 아니다.

### 5.2 합성 강도 편집 memory (7개)
native snapshot의 문서 사본에서 **`strength` 필드 하나만** 바꾼다(`AdaptiveMemory.from_document` 검증 통과 필수). 저장소의 native 학습 결과가 아니라 연구 외피의 개입이며 모든 기록에 `synthetic_strength_edit`로 표시한다.

| 이름 | 기반 | strength | 목적 |
|---|---|---|---|
| `b3@0.11` | n=3 | `0.55*0.2` | R072의 M0(오답 1회 뒤)와 같은 strength·balance. 통제 C0 |
| `b3@0.022` | n=3 | `0.55*0.2*0.2` | R072의 M1. 통제 C0 |
| `b3@s6` | n=3 | s_6 | balance 3/4에서 strength만 n=6 수준 |
| `b3@s20` | n=3 | s_20 | balance 3/4에서 strength만 n=20 수준 |
| `b3@p6` | n=3 | `s_6*(6/7)/(3/4)` | 곱 s·b를 native n=6과 맞춤 |
| `b20@0.55` | n=20 | 0.55 | balance 20/21에서 strength만 n=3 수준 |
| `b20@s6` | n=20 | s_6 | balance 20/21에서 strength만 n=6 수준 |

### 5.3 포획 폭 평가
14개 memory × `e1 ∈ {−1.0, −0.9, …, +1.0}` 21점 × 정책 {`legacy`, `route_only`}, 회로 ON = 588 평가. 회로 OFF 대조는 정책별·score별로 n=3과 n=20 memory에서 = 84 평가. 합계 672.

정의: 한 memory·정책의 **회로 귀속 포획 집합 W** = ON이 True를 채택했고 같은 score·정책의 OFF(n=3 memory)가 True가 아닌 score들의 집합. 폭 |W|는 격자점 개수다. ON과 OFF가 모두 True인 점(관측 자체가 오도하는 경우)은 W에 넣지 않고 따로 센다.

### 5.4 탈출 비용
n ∈ {3, 6, 9, 20} × `e1 ∈ {0.0, −0.2}`의 8개 계열. 각 계열은 해당 native memory 사본에서 `legacy`·`ADAPT`로 같은 관측의 새 episode를 최대 6회 제시한다. 매 판단 뒤 참조 feedback(True면 `correct=False`, False면 `correct=True`, 미결정이면 `correct=None`)을 소비시킨다. **탈출 횟수 E** = 처음으로 True가 아닌 판단이 나오기 전까지의 True 오답 횟수. 6회 모두 True면 "6 초과"로 기록한다. 계열이 끝난 memory로 같은 관측의 frozen 평가를 1회 더 한다.

### 5.5 통제 C0
`b3@0.11`, `b3@0.022`의 `route_only` 평가에서 `e1 ∈ {0.6, 0.8, 1.0}`의 pool activation 6개가 EXP-53 / R072 결과표의 값과 **정확히 같은지** 확인한다: 0.9946031190005065, 0.9939711377690879, 0.9942212668099926, 0.9938918635122408, 0.9938074999629096, 0.9938074999629096. R072의 memory는 이번 것과 학습 경로(길이 2·3·4 chain, 오답 feedback 1~2회)가 다르고 strength·balance만 같다. 불일치하면 하네스 또는 "strength·balance만 중요하다"는 전제가 틀린 것이므로 결과 해석 전에 원인을 기록한다.

## 6. 사전 예측 (엔진 실행 전, 위 코드 사실에서 도출)

- **P1 (학습 산술)**: snapshot의 strength는 2절 표와 정확히 같고 balance는 n/(n+1)이다. 길이 2 회로 하나만 형성된다.
- **P2 (`route_only`에서 폭 0)**: 모든 memory·score에서 `route_only` ON의 채택값은 OFF와 같다. |W| = 0.
- **P3 (`legacy`에서 폭이 넓어지고 포화)**: |W(n)|는 n에 대해 줄지 않는다. |W(20)| > |W(3)|. 증가분은 포화한다: |W(20)| − |W(9)| ≤ |W(6)| − |W(3)|.
- **P4 (자격 경계)**: `e1 < −0.8`인 점은 mismatch 때문에 어떤 memory에서도 회로가 선택되지 않는다. `e1 = ±1.0`에서는 prior가 0이라 모든 memory가 같은 pool 궤적을 가진다.
- **P5 (순수 강도로 충분)**: 채택값과 회로 선택은 곱 s·b만의 함수다. `b3@p6`는 21점 모두에서 native n=6과 채택값·선택이 같고 pool activation 차이는 1e-9 이하다. 같은 strength에서 balance가 큰 쪽(`b20@s6` 대 `b3@s6`)의 |W|는 작지 않다.
- **P6 (통제)**: C0의 6개 activation이 R072와 정확히 일치한다.
- **P7 (탈출 비용은 학습량과 거의 무관)**: 모든 계열에서 E ≤ 3이다. 같은 score에서 |E(20) − E(3)| ≤ 1이다. feedback 뒤 strength는 `s_n × 0.2^k`와 정확히 같고, 세 번째 오답 뒤 `active = False`가 된다.
- **P8 (익숙한 입력의 이득)**: `e1 = 0.9`에서 ON은 OFF보다 expansion이 적고 전체 kernel tick은 많다(EXP-44와 같은 방향). 이 두 값은 n에 따라 변하지 않는다.

작성자가 가장 자신 없는 예측은 P3의 포화 부등식과 P7의 E 값 자체다(판단 network의 실제 경계를 계산하지 않았다). P2·P4·P6은 코드에서 거의 따라 나오므로 틀리면 하네스 오류를 먼저 의심한다.

## 7. 판정 규칙

- 각 예측은 `supported` / `falsified` / `not_evaluable`로 판정한다. 결과를 본 뒤 격자·memory 집합·정의를 바꾸지 않는다.
- H07에 대한 해석은 다음 표로 고정한다.

| P3 | P7 | 해석 |
|---|---|---|
| supported | supported | 강도는 포획 폭을 넓히지만 탈출 비용을 높이지 않는다. 현재 학습 규칙에는 H07의 "수정 가능성 감소" 쪽을 만들 기제가 없어, 이 엔진으로는 H07의 trade-off를 시험할 수 없다. H07의 상태는 바꾸지 않고 "현 엔진에서 시험 불가" 사유를 기록한다. |
| supported | falsified (E가 n에 따라 2 이상 증가) | 현재 규칙에서도 trade-off가 나타난다. H07의 좁은 지지 후보로 기록하고 원인을 분해한다. |
| falsified | 무관 | 강도가 포획 폭을 넓힌다는 전제부터 성립하지 않는다. 원인을 기록하고 H07 해석을 보류한다. |

- C0가 불일치하면 위 해석 표를 적용하지 않고 `CONTROL_FAILED`로 보고한다.

## 8. 예산과 경계

- 학습 20 episode, 평가 672, 탈출 계열 최대 48 episode + 사후 평가 8. worker 1, retry 0, **본 실행 1회**, 결정성 확인용 같은 명령 재실행 1회.
- 실행 전 허용한 엔진 접촉: 하네스의 API 동작을 확인하는 `--smoke`(학습 3 episode와 memory 문서 형식만 출력, 평가·탈출 계열은 실행하지 않음). smoke는 증거로 세지 않는다.
- 2-edge chain 하나, 길이 2 회로 하나, 고정 Config의 결정적 비교다. 독립 표본이 아니며 통계 추론을 하지 않는다. 격자 간격 0.1보다 가는 경계는 보지 않는다.
- 합성 강도 편집은 memory 계약(문서 검증)은 통과하지만 native 학습으로 도달한 상태가 아닐 수 있다(예: `b20@0.55`). native 결과와 합산하지 않는다.
- 인간의 습관·고정관념, LLM 내부, 생물학에 대한 주장이 아니다. H03의 효율 주장도 아니다. wall time·에너지는 판정하지 않는다.
- 설계·구현·실행·검산을 한 작성자(AI 연구 보조)가 한 세션에서 수행한다. blind 토론·별도 Judge는 없다.
