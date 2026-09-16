# 계층적 수렴-회로 가설
## 감각·착시·직관·A/D/M Thought-Graph·회로 학습을 하나의 계산 모델로 재구성

작성 기준일: 2026-09-16

---

# 0. 이 문서에서 새로 섞은 핵심

이 문서는 기존의 두 흐름을 나란히 붙이는 문서가 아니다.

기존 통합 가설에는 다음 요소가 있었다.

- A/D/M Thought-Graph
- Binding Continuity
- Candidate Competition
- Attractor Convergence
- Learning as Circuit Formation
- 반복된 Thought-Graph의 Circuit Compression
- Physical Neural Substrate
- Plasticity / Control Plane

새로운 감각·착시 가설에는 다음 요소가 있었다.

- 감각도 단순 입력→출력이 아니라 분산 표현과 수렴 과정일 수 있음
- 시각·후각·직관에서 유사한 계산 primitive가 반복될 가능성
- 감각과 직관의 차이가 계산 원리보다 abstraction level의 차이일 수 있음
- 착시는 정상적인 inference가 잘못된 안정 상태로 수렴한 경우일 수 있음
- 다중안정 착시는 동일 입력에서 둘 이상의 attractor가 경쟁할 수 있음을 생각하게 함
- 잘못된 직관과 착시를 서로 다른 추상화 수준의 misconvergence로 볼 수 있음

두 흐름을 실제로 섞으면 중심 가설은 다음처럼 바뀐다.

> **뇌 또는 뇌형 인공지능은 감각·개념·직관·명시적 추론마다 완전히 다른 계산기를 사용하는 것이 아니라, 여러 추상화 수준에서 ‘후보 활성화 → 의미 결합 → 경쟁·억제 → 재귀적 보정 → 수렴’이라는 공통 계산 primitive를 반복할 수 있다. 이 과정에서 새롭거나 불확실한 문제는 동적인 Thought-Graph를 확장하며 처리되고, 반복적으로 성공한 그래프는 학습을 통해 재사용 가능한 회로 또는 attractor 구조로 압축된다. 익숙한 문제에서 나타나는 직관은 이 압축된 회로의 빠른 수렴일 수 있으며, 착시와 잘못된 직관은 같은 구조가 잘못된 안정 상태로 수렴한 경우로 볼 수 있다.**

이를 가장 압축하면:

\[
\boxed{
Perception
\rightarrow
Concept
\rightarrow
Intuition
\rightarrow
Reasoning
}
\]

이 서로 완전히 다른 알고리즘의 연쇄가 아니라,

\[
\boxed{
\text{같은 계산 primitive}
\times
\text{서로 다른 A 수준}
}
\]

일 수 있다는 것이다.

그리고 학습까지 포함하면:

\[
\boxed{
Repeated\ Convergence
\rightarrow
Circuit\ Formation
\rightarrow
Compressed\ Inference
}
\]

가 된다.

---

# 1. 가장 큰 전환: Thought-Graph는 고차 추론에만 있는가?

기존 A/D/M 연구에서는 Thought-Graph를 주로 명시적인 추론 구조로 다뤘다.

예:

```text
fact
 ↓
rule
 ↓
intermediate node
 ↓
rule
 ↓
final
```

하지만 감각 가설을 섞으면 질문이 바뀐다.

> **감각 처리부터 이미 일종의 동적인 내부 graph 형성이 일어나고 있는 것은 아닐까?**

예를 들어 시각에서:

```text
raw visual signal
      ↓
여러 feature 후보
      ↓
형태 후보
      ↓
object 후보
      ↓
맥락과 기억
      ↓
하나의 percept
```

후각에서는:

```text
chemical pattern
      ↓
distributed receptor activation
      ↓
partial odor patterns
      ↓
memory / completion
      ↓
odor object
```

직관에서는:

```text
situational cues
      ↓
관계 / 패턴 / 가설 후보
      ↓
구조적 일치·불일치
      ↓
competition
      ↓
judgment
```

명시적 추론에서는:

```text
facts
 ↓
candidate relations
 ↓
rules / dependencies
 ↓
proof graph
 ↓
conclusion
```

내용은 다르지만 공통 형식은 다음과 같다.

\[
\boxed{
Input
\rightarrow
Distributed\ Candidates
\rightarrow
Relational\ Binding
\rightarrow
Competition / Recurrence
\rightarrow
Stable\ State
}
\]

이 관점에서 Thought-Graph는 반드시 언어로 표현된 논리 그래프만을 뜻하지 않는다.

더 일반적으로는:

> **현재 입력을 해석하기 위해 일시적으로 형성되는 관계 구조**

라고 볼 수 있다.

---

# 2. A는 단순한 프롬프트 추상화가 아니라 Representation Level일 수 있다

기존 A는 Abstraction이다.

이를 감각에서 고차 추론까지 확장하면 작업 가설로 다음처럼 둘 수 있다.

\[
A_0 = Sensory\ Feature
\]

\[
A_1 = Pattern / Object
\]

\[
A_2 = Concept
\]

\[
A_3 = Relation
\]

\[
A_4 = Situation\ Model
\]

\[
A_5 = Hypothesis / Judgment
\]

이 번호 자체가 중요한 것은 아니다.

핵심은:

> **동일하거나 유사한 계산 primitive가 서로 다른 표현 수준에서 반복될 수 있다.**

는 것이다.

예를 들어:

### 낮은 A 수준

```text
edge 후보
shape 후보
object 후보
→ 경쟁
→ percept
```

### 높은 A 수준

```text
원인 후보
해석 후보
행동 후보
→ 경쟁
→ judgment
```

따라서:

\[
\boxed{
Same\ Primitive
+
Different\ Representation
}
\]

이라는 구조가 가능하다.

---

# 3. A와 D는 섞지 않는다

감각→개념→판단을 위계적으로 배치하면 이것을 그대로 “깊이 D”라고 부르고 싶어질 수 있다.

하지만 현재 A/D/M 연구의 정의를 유지하면 둘은 구분해야 한다.

## A

무엇을 어떤 추상화 수준에서 표현하는가.

## D

최종 상태를 지지하기 위해 실제로 필요한 dependency chain이 얼마나 깊은가.

따라서:

```text
A = 표현 공간의 수준
D = 그 공간 안에서 또는 공간을 가로질러 필요한 의존 구조
```

이다.

같은 A 수준에서도 D는 달라질 수 있다.

예:

```text
A = Relation
```

이라고 해도:

```text
R1 → conclusion
```

처럼 얕을 수도 있고,

```text
R1 → R2 → R3 → R4 → conclusion
```

처럼 깊을 수도 있다.

반대로 A 수준이 올라간다고 D가 반드시 증가하는 것도 아니다.

이미 압축된 개념을 사용한다면 높은 A에서도 낮은 D로 판단할 수 있다.

따라서:

\[
\boxed{
A \neq D
}
\]

를 유지해야 한다.

---

# 4. M은 “어떤 방식으로 수렴시키는가”로 확장할 수 있다

기존 M은 Modality / Method이다.

통합 모델에서는 M을 다음처럼 확장해서 생각할 수 있다.

> **현재 representation에서 후보들을 어떻게 생성·비교·보완·검증·수렴시키는가**

예:

- pattern completion
- winner-take-all
- recurrent refinement
- contrastive comparison
- causal decomposition
- symbolic inference
- consistency checking
- external verification
- error correction

즉 같은 A와 D를 가진 문제라도 M이 다르면 다른 계산 결과가 나올 수 있다.

개념적으로:

\[
Outcome
=
f(A,D,M)
\]

이지만 실제 실행에는 하나가 더 필요하다.

---

# 5. A/D/M 아래에 Binding Continuity가 필요하다

v087~v090에서 드러난 중요한 현상은:

> **현재 node를 만드는 것과 이후 단계에서 같은 node를 다시 정확히 참조하는 것은 다른 문제**

라는 것이었다.

즉 graph가 실제로 유지되려면:

\[
\boxed{
Binding\ Continuity
}
\]

가 필요하다.

Binding Continuity는 A/D/M의 네 번째 축이라기보다:

> **A/D/M 구조가 실행되는 동안 의미·identity·관계가 끊기지 않게 유지하는 기반 조건**

으로 보는 편이 자연스럽다.

예:

```text
현재 node 생성
      ↓
의미 ↔ identity 결합
      ↓
다음 계산에서 같은 node 재활성화
      ↓
올바른 parent 연결
```

이 연결이 깨지면 논리 자체를 알고 있어도 graph가 무너질 수 있다.

---

# 6. v089/v090은 “의미 기반 연결”이라는 더 큰 문제를 드러낸다

현재 실험에서 의미 기반 ID는 단순히 짧은 ID보다 잘 동작했다.

즉 핵심은:

\[
Short\ ID
\neq
Better
\]

가 아니라,

\[
\boxed{
Semantic\ Identity
\leftrightarrow
Stable\ Rebinding
}
\]

일 가능성이 있다.

이것을 감각·직관 모델과 섞으면 더 큰 질문이 생긴다.

> **뇌 또는 뇌형 시스템에서도 안정된 representation은 단순한 주소가 아니라 의미 구조와 연결된 재활성화 가능한 assembly/circuit 형태여야 하는가?**

즉 어떤 개념을 매번 새로운 임의 주소로 찾는 것이 아니라:

```text
특정 의미 패턴
      ↓
관련 회로 부분 활성화
      ↓
같은 의미 구조 재구성
```

처럼 작동할 수 있다는 가설이다.

현재 LLM ID 실험은 이 뇌 가설을 증명하지 않는다.

다만:

> **계산 구조를 유지하는 데 의미와 identity의 대응이 중요한 변수일 수 있다**

는 실험적 단서를 제공한다.

---

# 7. 감각부터 추론까지 반복되는 공통 계산 primitive

통합 모델에서 가장 핵심적인 계산 primitive를 다음처럼 정의할 수 있다.

\[
\boxed{
Activation
+
Binding
+
Competition
+
Inhibition
+
Recurrent\ Correction
+
Convergence
}
\]

이를 단계로 풀면:

```text
1. 입력이 들어온다.
2. 여러 가능한 내부 상태가 부분적으로 활성화된다.
3. 현재 맥락·기억·prior와 결합한다.
4. 서로 경쟁하거나 억제한다.
5. 재귀적으로 불일치를 보정한다.
6. 하나 또는 소수의 안정 상태로 수렴한다.
```

이 구조가:

- 시각
- 후각
- 개념 형성
- 상황 해석
- 직관
- 추론
- 행동 선택

에서 서로 다른 A 수준으로 반복될 수 있다는 것이 핵심 가설이다.

---

# 8. 모든 수렴이 정답은 아니다

기존 “Circuit Compression” 가설만 보면 빠른 수렴은 좋은 것으로 보이기 쉽다.

하지만 착시를 넣으면 중요한 수정이 필요하다.

\[
\boxed{
Fast\ Convergence
\neq
Correct\ Convergence
}
\]

시스템은 매우 빠르고 안정적으로 틀릴 수 있다.

착시의 작업 모델:

\[
Sensory\ Input
\rightarrow
Candidate\ Percepts
\rightarrow
Competition
\rightarrow
Wrong\ Attractor
\]

잘못된 직관:

\[
Complex\ Situation
\rightarrow
Candidate\ Interpretations
\rightarrow
Competition
\rightarrow
Wrong\ Attractor
\]

따라서 학습 목표는 단순히:

> 빨리 수렴하기

가 아니다.

더 정확하게는:

\[
\boxed{
Correct\ and\ Adaptive\ Convergence
}
\]

여야 한다.

---

# 9. 착시는 “계산 실패”보다 “정상 계산의 과도한 성공”일 수 있다

착시를 통합 모델 안에서 보면 다음과 같은 해석이 가능하다.

현실에서는 대부분:

```text
불완전한 입력
 ↓
과거 경험 / prior
 ↓
pattern completion
 ↓
빠른 percept
```

가 유리하다.

그러나 특수한 입력에서는:

```text
ambiguous input
 ↓
강한 prior
 ↓
기존 circuit 과활성
 ↓
빠르고 안정적인 수렴
 ↓
physical reality와 다른 percept
```

가 될 수 있다.

즉 오류가:

\[
\text{계산을 못해서 발생}
\]

한 것이 아니라,

\[
\boxed{
\text{학습된 계산 규칙이 너무 잘 적용되어 발생}
}
\]

할 수 있다.

이것은 이후 AI 아키텍처에서 매우 중요하다.

왜냐하면:

> **회로 학습과 attractor 형성을 강화할수록, 잘못 학습된 attractor가 더 빠르고 강하게 틀릴 위험도 함께 커질 수 있기 때문**

이다.

---

# 10. 다중안정 착시는 “하나의 입력 → 하나의 고정 출력” 모델을 깨뜨린다

다중안정 상태를 작업 가설로 보면:

\[
Input = Constant
\]

인데도:

\[
State_A
\leftrightarrow
State_B
\]

가 가능하다.

즉 내부 시스템은:

```text
Input
  ├─ Candidate A
  └─ Candidate B
          ↓
      Competition
          ↓
      Attractor
```

처럼 둘 이상의 안정 가능한 해석을 가질 수 있다.

이 구조는 고차 추론에서도 그대로 사용할 수 있다.

```text
상황
 ├─ 해석 A
 ├─ 해석 B
 └─ 해석 C
       ↓
   competition
       ↓
   current judgment
```

따라서 “후보 경쟁”은 고차 사고만을 위해 새로 추가되는 특수 기능이 아니라,

> **감각부터 추론까지 반복될 수 있는 범용 계산 primitive**

일 수 있다.

---

# 11. 직관과 명시적 추론은 서로 다른 시스템이 아닐 수도 있다

기존에는 다음처럼 나누기 쉽다.

```text
직관 = 빠른 시스템
추론 = 느린 시스템
```

하지만 통합 모델에서는 다른 그림이 가능하다.

### 익숙한 문제

이미 충분히 학습된 circuit이 있다.

```text
Input
 ↓
관련 circuit 활성화
 ↓
competition
 ↓
fast convergence
 ↓
judgment
```

### 새로운 문제

기존 circuit만으로 안정적으로 수렴하지 못한다.

```text
Input
 ↓
candidate circuits conflict
 ↓
low confidence / mismatch
 ↓
graph expansion
 ↓
deeper dependency construction
 ↓
new reasoning
```

즉:

\[
\boxed{
Intuition
\leftrightarrow
Reasoning
}
\]

은 완전히 별개의 엔진이 아니라,

\[
\boxed{
Compiled\ Circuit\ Execution
\leftrightarrow
Dynamic\ Graph\ Expansion
}
\]

이라는 연속선일 수 있다.

---

# 12. “뭔가 이상하다”는 Graph Expansion Trigger일 수 있다

직관 문서에서 중요한 부분은:

> 정답을 바로 생성하는 것보다 구조적 불일치를 먼저 감지할 수 있다.

는 것이었다.

이를 현재 모델에 넣으면:

```text
현재 입력
 ↓
기존 circuit / expected graph와 비교
 ↓
binding / relation mismatch
 ↓
"뭔가 이상하다"
 ↓
기존 attractor에 즉시 수렴하지 않음
 ↓
추가 candidate 활성화
 ↓
graph expansion
```

이 된다.

즉 “쎄하다”, “아닌데?” 같은 감각은 단순 출력이 아니라:

\[
\boxed{
\text{현재 압축 회로로는 설명이 충분하지 않다는 신호}
}
\]

일 수 있다.

그 신호가 충분히 크면 D를 늘리거나 M을 바꾸거나 A 수준을 이동하는 식의 추가 계산이 일어날 수 있다.

---

# 13. 새로운 문제에서는 A/D/M이 동적으로 변할 수 있다

통합 모델에서 A/D/M은 고정 설정만이 아닐 수 있다.

처음에는:

\[
(A_1,D_1,M_1)
\]

로 시도한다.

하지만 수렴하지 않으면:

\[
(A_2,D_2,M_2)
\]

로 바꿀 수 있다.

예:

### A 변경

```text
세부 feature에 매달림
→ 더 상위 개념으로 재표현
```

또는 반대로:

```text
추상적인 설명
→ 구체 사례로 내려감
```

### D 변경

```text
짧은 경로로 실패
→ 더 많은 dependency를 전개
```

### M 변경

```text
pattern matching 실패
→ causal analysis
```

또는:

```text
직관적 선택 실패
→ explicit verification
```

따라서 reasoning은:

\[
\boxed{
Adaptive\ Search\ over\ (A,D,M)
}
\]

으로 볼 수도 있다.

---

# 14. 학습은 이 탐색을 점점 줄이는 과정일 수 있다

처음 접하는 문제에서는:

```text
A 후보 탐색
+
D 확장
+
M 변경
+
binding 유지
+
candidate competition
```

이 많이 필요할 수 있다.

반복적으로 성공하면:

```text
성공한 representation
성공한 dependency
성공한 method
성공한 binding
```

이 하나의 안정된 subgraph로 반복된다.

그러면:

\[
G_{success}
\]

를 점차:

\[
C_{compiled}
\]

로 바꿀 수 있다.

즉:

\[
\boxed{
Dynamic\ Thought\ Graph
\rightarrow
Repeated\ Success
\rightarrow
Stable\ Circuit
}
\]

이다.

---

# 15. Learning as Circuit Compilation

기존의:

\[
Learning
=
Circuit\ Formation
+
Reinforcement
+
Pruning
+
Reconfiguration
\]

을 이번 통합에서는 더 구체화할 수 있다.

\[
\boxed{
Learning
=
Graph\ Formation
+
Graph\ Validation
+
Graph\ Reinforcement
+
Graph\ Compression
+
Circuit\ Reuse
}
\]

### Graph Formation

새 문제를 해결하기 위해 동적 구조를 만든다.

### Graph Validation

결과가 실제로 맞았는지 평가한다.

### Graph Reinforcement

성공한 연결을 강화한다.

### Graph Compression

반복되는 중간 계산을 더 직접적인 경로로 줄인다.

### Circuit Reuse

유사 입력에서 전체 graph를 다시 만들지 않고 기존 circuit을 활성화한다.

따라서:

> **Thinking builds the graph.  
> Learning validates and compiles the graph.  
> Intuition reactivates the compiled circuit.**

가 된다.

---

# 16. D Compression은 숙련의 한 형태일 수 있다

초기에는:

\[
A\rightarrow B\rightarrow C\rightarrow D
\]

를 모두 계산해야 한다.

하지만 반복된 학습 후:

\[
A\Rightarrow D
\]

와 같은 shortcut 또는 compressed subcircuit이 만들어질 수 있다.

따라서:

\[
D_{external}
\]

과

\[
D_{effective}
\]

를 구분할 필요가 생긴다.

예를 들어 동일한 외부 proof structure를 출력하더라도 내부에서는:

```text
처음:
5단계 실제 탐색

숙련 후:
압축 회로로 결론 활성화
→ 필요하면 5단계 설명 재구성
```

일 수 있다.

즉:

\[
\boxed{
Observed\ D
\neq
Effective\ Internal\ D
}
\]

가 된다.

---

# 17. Decision Generation과 Explanation Reconstruction이 분리되는 이유

이 구조에서는 직관의:

> “답은 바로 나오는데 설명은 나중에 해야 한다.”

는 현상이 자연스럽게 들어온다.

판단:

\[
Input
\rightarrow
Compiled\ Circuit
\rightarrow
Decision
\]

설명:

\[
Decision
\rightarrow
Relevant\ Graph\ Reconstruction
\rightarrow
Language
\]

따라서:

\[
\boxed{
Decision\ Generation
\neq
Explanation\ Reconstruction
}
\]

이다.

이것은 사람뿐 아니라 LLM 연구에서도 중요하다.

외부에 생성된 Chain-of-Thought나 proof graph가:

> 내부 계산 그 자체

라고 가정할 수 없기 때문이다.

현재 A/D/M 연구는 외부 proof graph를 매우 엄격하게 측정하지만, 그것이 내부 hidden trajectory와 동일하다고 주장하지 않는다.

---

# 18. 감각도 “압축 회로 재사용”으로 볼 수 있다

같은 원리를 감각으로 내리면:

처음 보는 패턴:

```text
feature 탐색
 ↓
여러 object 후보
 ↓
context
 ↓
competition
 ↓
percept
```

익숙한 패턴:

```text
부분 feature
 ↓
기존 object circuit 빠른 활성화
 ↓
pattern completion
 ↓
percept
```

즉 감각 인식에서도:

\[
Repeated\ Exposure
\rightarrow
Faster\ Convergence
\]

가 가능하다는 모델이다.

따라서 직관만 “압축된 추론”인 것이 아니라,

\[
\boxed{
Perception
=
Low\text{-}level\ Compressed\ Inference
}
\]

\[
\boxed{
Intuition
=
High\text{-}level\ Compressed\ Inference
}
\]

라는 더 강한 작업 가설까지 확장할 수 있다.

---

# 19. 착시와 잘못된 직관은 같은 실패 형태일 수 있다

이제 둘을 같은 계산 프레임으로 놓을 수 있다.

### 착시

```text
sensory representation
 ↓
강한 prior / learned circuit
 ↓
candidate competition
 ↓
wrong stable percept
```

### 잘못된 직관

```text
situation representation
 ↓
강한 prior / learned relation circuit
 ↓
candidate competition
 ↓
wrong stable judgment
```

따라서:

\[
\boxed{
Illusion
=
Low\text{-}A\ Misconvergence
}
\]

\[
\boxed{
Bad\ Intuition
=
High\text{-}A\ Misconvergence
}
\]

라고 작업 가설을 세울 수 있다.

여기서 핵심은 세부 신경 회로가 같다는 뜻이 아니다.

> **오류의 상위 계산 형식이 동일할 수 있다**

는 뜻이다.

---

# 20. 그렇다면 “좋은 지능”은 수렴 속도만으로 정의할 수 없다

새 모델에서는 세 가지가 모두 필요하다.

\[
\boxed{
Speed
+
Accuracy
+
Revisability
}
\]

즉 좋은 시스템은:

1. 익숙한 문제에서는 빠르게 수렴하고,
2. 수렴 결과가 실제 환경과 잘 맞으며,
3. 틀렸다는 신호가 오면 기존 attractor를 깨고 다시 탐색할 수 있어야 한다.

세 번째가 중요하다.

강하게 압축된 circuit은 효율적이지만:

\[
\boxed{
Strong\ Attractor
\rightarrow
Hard\ to\ Revise
}
\]

가 될 수 있다.

따라서 plasticity는 단순 학습 기능이 아니라:

> **잘못된 압축 회로를 다시 풀고 수정하기 위한 기능**

이기도 해야 한다.

---

# 21. Novelty / Error는 “회로를 다시 그래프로 푸는 신호”일 수 있다

기존 circuit이 입력을 잘 설명하면:

\[
Circuit\ Reuse
\]

를 한다.

하지만:

- prediction error
- contradiction
- binding failure
- low convergence margin
- external feedback mismatch

가 발생하면:

\[
\boxed{
Circuit
\rightarrow
Graph\ Expansion
}
\]

이 필요할 수 있다.

즉 학습 방향은 일방향:

\[
Graph\rightarrow Circuit
\]

만이 아니라,

\[
\boxed{
Graph
\leftrightarrow
Circuit
}
\]

의 양방향 구조일 수 있다.

### 익숙함

\[
Graph
\rightarrow
Compressed\ Circuit
\]

### 새로움 / 오류

\[
Circuit
\rightarrow
Expanded\ Graph
\]

이 구조가 있어야 새로운 상황에도 적응할 수 있다.

---

# 22. 전체 인지 시스템을 하나의 반복 구조로 그리면

```text
                         External Input
                              │
                              ▼
                    ┌──────────────────┐
                    │ Representation A │
                    └────────┬─────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │ Candidate States / Graphs   │
              │ H1, H2, H3 ...              │
              └──────────────┬──────────────┘
                             │
                             ▼
                 ┌──────────────────────┐
                 │ Binding Continuity   │
                 │ meaning ↔ identity   │
                 └──────────┬───────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │ Competition / Inhibition  │
              │ Recurrent Correction      │
              └─────────────┬─────────────┘
                            │
                            ▼
                   ┌────────────────┐
                   │  Convergence   │
                   └───────┬────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
        Stable / adequate      mismatch / ambiguity
                │                     │
                ▼                     ▼
          Current Result         Graph Expansion
                │                A/D/M adaptation
                │                     │
                └──────────┬──────────┘
                           ▼
                Reward / Error / Reality
                           │
                           ▼
             ┌──────────────────────────┐
             │ Plasticity / Validation  │
             │ reinforce / weaken       │
             │ prune / reroute          │
             └─────────────┬────────────┘
                           ▼
                 Reusable Circuit
                           │
                           └──────→ future input
```

이 구조는 감각과 고차 추론을 분리된 시스템으로 두지 않는다.

다른 것은 주로:

- A 수준
- 활성화되는 representation
- 필요한 D
- 사용하는 M
- circuit의 학습 상태

이다.

---

# 23. 이 구조에서 A/D/M/B의 역할

## A — Abstraction

무엇을 표현하는가.

예:

- feature
- object
- concept
- relation
- hypothesis

## D — Decomposition / Dependency Depth

결론을 만들기 위해 필요한 실제 의존 구조가 얼마나 깊은가.

## M — Modality / Method

후보를 생성·비교·보완·검증·수렴시키는 계산 방법이 무엇인가.

## B — Binding Continuity

계산 중 의미·identity·관계가 얼마나 안정적으로 유지되는가.

따라서 실행 난이도는 단순히 D 하나가 아니라:

\[
\boxed{
Cost
=
f(A,D,M,B,\text{circuit familiarity})
}
\]

와 같은 형태일 수 있다.

---

# 24. v086의 “D=5도 잘 됨”을 이 모델에서 다시 해석하기

현재 실험에서는 D가 깊다고 단순히 실패가 증가하지 않았다.

이 통합 모델에서는 이것이 자연스럽다.

같은 D라도:

```text
의미 representation이 안정적
+
binding이 강함
+
method가 잘 맞음
+
경로가 익숙함
```

이면 실행 비용이 낮을 수 있다.

반대로 D가 낮아도:

```text
opaque identity
+
binding failure
+
wrong method
+
candidate conflict
```

가 있으면 실패할 수 있다.

따라서:

\[
\boxed{
Nominal\ D
\neq
Effective\ Cognitive\ Cost
}
\]

라는 새 연구 질문이 생긴다.

---

# 25. 물리적 신경회로 아키텍처도 바뀐다

기존 구조는:

```text
Massive Physical Neuron Fabric
+
Plasticity / Control Plane
+
Candidate Competition
```

이었다.

감각·추상화 가설을 섞으면 다음처럼 바뀐다.

```text
┌────────────────────────────────────────┐
│ Global Modulation / Reality Feedback   │
│ reward / novelty / error / attention   │
├────────────────────────────────────────┤
│ Structural Plasticity / Compilation    │
│ graph → circuit / circuit → expansion  │
├────────────────────────────────────────┤
│ Binding / Dynamic Routing Fabric       │
│ identity / relation / cross-A routing  │
├────────────────────────────────────────┤
│ Recurrent Competition Microcircuits    │
│ activate / inhibit / complete / settle │
├────────────────────────────────────────┤
│ Massive Physical Neural Substrate      │
│ sparse / local / event-driven dynamics │
└────────────────────────────────────────┘
```

핵심 차이는:

> **Candidate Competition을 고차 reasoning 전용 계층으로 두지 않고, 여러 A 수준에서 반복 가능한 microcircuit primitive로 둔다.**

는 것이다.

---

# 26. “같은 primitive를 여러 A 수준에서 반복”하는 하드웨어

아키텍처를 더 밀면:

```text
A0 sensory region
   └─ competition / convergence microcircuits

A1 object region
   └─ competition / convergence microcircuits

A2 concept region
   └─ competition / convergence microcircuits

A3 relation region
   └─ competition / convergence microcircuits

A4 hypothesis region
   └─ competition / convergence microcircuits
```

처럼 서로 다른 영역에서 기본 primitive는 비슷하지만 연결 구조와 representation만 달라질 수 있다.

즉 하드웨어 설계의 목표가:

> “시각 회로”, “추론 회로”, “직관 회로”를 각각 완전히 별도로 만드는 것

이 아니라,

> **공통 동역학 primitive를 가진 재구성 가능한 회로를 대규모로 배치하고, 학습된 연결 구조가 각 영역의 기능을 결정하게 하는 것**

으로 바뀐다.

---

# 27. 아기 발달 가설도 더 구체적으로 해석할 수 있다

초기에는 모든 고차 기능이 완성되어 있지 않다.

하지만 기본 substrate와 학습 규칙이 존재한다.

\[
Network_0
\]

에 경험이 들어오면서:

\[
G_{t+1}=Learning(G_t,x_t)
\]

가 반복된다.

통합 모델에서는 이 변화가 단순 weight update만이 아니다.

```text
초기 감각 circuit 형성
 ↓
안정된 object representation
 ↓
개념 circuit 형성
 ↓
관계 circuit 형성
 ↓
상위 candidate competition
 ↓
직관 / reasoning circuit 형성
```

즉 낮은 A에서 형성된 안정 representation이 높은 A의 node 역할을 할 수 있다.

따라서 발달은:

\[
\boxed{
Hierarchical\ Circuit\ Construction
}
\]

으로 볼 수 있다.

---

# 28. 낮은 A의 출력이 높은 A의 node가 된다

이 모델에서 매우 중요한 연결은 다음이다.

낮은 수준의 수렴 결과:

\[
C^*_{A_0}
\]

는 그 수준의 최종 출력이지만,

한 단계 높은 수준에서는:

\[
Node_{A_1}
\]

가 된다.

즉:

\[
\boxed{
Converged\ State\ at\ A_n
=
Candidate\ Node\ at\ A_{n+1}
}
\]

가 가능하다.

예:

```text
색/선
 ↓
"얼굴"
 ↓
"화난 표정"
 ↓
"상대가 불편해 보임"
 ↓
"지금 말하면 안 될 것 같다"
```

각 단계는 그 자체로 하나의 수렴 결과이면서,
다음 단계의 입력이 된다.

이렇게 보면:

\[
Brain
=
Hierarchical\ Repeated\ Convergence
\]

라는 기존 가설이 더 구체적인 계산 구조를 갖게 된다.

---

# 29. 하지만 bottom-up 직렬 파이프라인은 아니다

위 구조를:

```text
A0 → A1 → A2 → A3 → A4
```

의 단순 직렬 파이프라인으로 보면 안 된다.

통합 가설에서는 recurrent interaction이 중요하다.

예:

```text
A0 sensory feature
 ↑             ↓
A1 object representation
 ↑             ↓
A2 context / concept
```

상위 context가 하위 percept 후보에 다시 영향을 줄 수 있다.

따라서 실제 구조는:

\[
\boxed{
Bottom\text{-}up
+
Top\text{-}down
+
Recurrent
}
\]

일 수 있다.

이 구조가 바로 착시에서 prior/context가 percept에 영향을 줄 수 있다는 가설과 연결된다.

---

# 30. 잘못된 상위 circuit이 하위 지각까지 왜곡할 수도 있다

만약 상위 A 수준의 강한 prior가 있다면:

\[
A_{high}
\rightarrow
A_{low}
\]

방향의 feedback이 후보 경쟁에 영향을 줄 수 있다.

그러면:

```text
ambiguous sensory input
+
strong high-level expectation
 ↓
특정 low-level candidate 강화
 ↓
wrong percept convergence
```

가 가능하다.

반대로 하위 sensory mismatch가 충분히 강하면:

```text
high-level hypothesis
 ↓
sensory mismatch
 ↓
hypothesis weakened
 ↓
alternative candidate activated
```

가 될 수 있다.

즉 전체 시스템은:

> **서로 다른 A 수준의 attractor들이 상호 제약하는 구조**

로 볼 수 있다.

---

# 31. “현실 검증” 계층이 필요한 이유

착시와 잘못된 직관을 넣으면 내부 일관성만으로는 부족하다.

시스템 내부에서 완벽하게 일관된 graph도 현실과 다를 수 있다.

따라서:

\[
\boxed{
Internal\ Coherence
\neq
External\ Correctness
}
\]

이다.

학습에는:

- reward
- environment feedback
- prediction error
- external verification
- contradiction

등이 필요하다.

이것이 Plasticity / Control Plane에서:

> **어떤 circuit을 강화하고 어떤 circuit을 약화할지 결정하는 현실 기준**

이 된다.

---

# 32. AI에서 발생할 수 있는 대응 현상

이 부분은 현재 실험의 직접 결론이 아니라 통합 가설에서 새로 나오는 질문이다.

만약 AI도:

```text
distributed candidate activation
→ prior/context
→ convergence
```

를 사용한다면,

잘못된 출력의 일부는:

> 계산이 전혀 없어서

가 아니라,

> **내부적으로는 매우 일관된 잘못된 attractor 또는 잘못된 graph가 형성되어서**

발생할 수도 있다.

따라서 향후에는 오류를:

- no convergence
- unstable convergence
- wrong convergence
- binding failure
- graph execution failure

로 구분할 필요가 생긴다.

이 분류는 현재 A/D/M 실험에서 이미 구분하고 있는:

- 선택 실패
- graph 생성 실패
- parent binding 실패
- D 종단 실패

와도 연결할 수 있다.

---

# 33. 새로운 오류 분류

통합 모델에서 오류는 최소한 다음처럼 분리할 수 있다.

## 1. Activation Failure

필요한 후보가 활성화되지 않음.

## 2. Binding Failure

올바른 의미·identity·관계 연결이 유지되지 않음.

## 3. Competition Failure

잘못된 후보가 경쟁에서 이김.

## 4. Misconvergence

안정적으로 수렴했지만 현실과 다름.

## 5. Non-convergence

후보가 계속 충돌하고 안정 상태를 만들지 못함.

## 6. Over-compression

과거 shortcut을 너무 강하게 재사용해 새로운 예외를 놓침.

## 7. Graph Expansion Failure

기존 circuit이 틀렸는데도 더 깊은 탐색으로 전환하지 못함.

이 분류는 감각·직관·LLM 추론을 같은 프레임으로 비교할 수 있게 한다.

---

# 34. 기존 A/D/M 실험을 새 모델에서 어디에 놓을 것인가

현재 A/D/M 실험은 전체 모델 중:

```text
고차 representation
 ↓
candidate path selection
 ↓
binding continuity
 ↓
explicit graph execution
 ↓
external validation
```

영역을 직접 관찰하고 있다.

즉 현재 실험이 직접 검증하는 것은:

> 전체 뇌형 가설

이 아니라,

> **고차 reasoning graph가 representation·path·binding 조건에 따라 어떻게 달라지는가**

이다.

이 실험 결과를 기반으로 바로 뇌의 회로 구조를 주장하면 안 된다.

하지만 전체 가설 안에서는 매우 중요한 한 조각이다.

왜냐하면:

> **추론 결과가 단순 논리 규칙 보유 여부가 아니라 representation과 graph execution 구조에 민감하다**

는 것을 실제로 측정하고 있기 때문이다.

---

# 35. 현재 실험과 감각 가설을 연결하는 가장 안전한 다리

현재 실험으로 관찰된 것:

\[
Representation
+
Binding
+
Execution
\rightarrow
Proof\ Success
\]

감각 가설에서 제안하는 것:

\[
Representation
+
Context
+
Competition
+
Convergence
\rightarrow
Percept
\]

두 구조에서 공통적으로 등장하는 것은:

- representation
- relation/binding
- context
- state transition
- stable outcome

이다.

따라서 직접 동일시하지 않고도:

> **서로 다른 계산 수준에서 결과는 입력 정보 그 자체뿐 아니라 내부 표현과 연결 구조에 의존한다**

라는 공통 연구 질문을 만들 수 있다.

---

# 36. 가장 중요한 새 실험 1 — Familiarity Compression

질문:

> 같은 구조를 반복 학습시키면 실제 계산 비용이 감소하는가?

초기:

```text
candidate 수 많음
graph expansion 큼
D 높음
event 많음
```

숙련:

```text
기존 circuit 활성화
candidate 수 감소
graph expansion 감소
effective D 감소
event 감소
```

측정:

- active node 수
- active circuit 수
- event 수
- latency
- effective D
- accuracy
- wrong-attractor rate

핵심:

\[
\boxed{
Learning
\Rightarrow
Lower\ Computation
\quad
without\ Accuracy\ Loss
}
\]

---

# 37. 가장 중요한 새 실험 2 — Novelty-triggered Graph Expansion

익숙한 입력과 새로운 입력을 비교한다.

### Familiar

```text
Input
→ compiled circuit
→ fast convergence
```

### Novel

```text
Input
→ existing circuits conflict
→ mismatch
→ graph expansion
→ higher D / alternate M
```

측정:

- convergence time
- candidate count
- D 변화
- M switch 횟수
- circuit reuse ratio

이 실험이 성공하면:

> **직관과 명시적 추론을 같은 시스템의 서로 다른 실행 상태로 볼 수 있는지**

를 직접 검증할 수 있다.

---

# 38. 가장 중요한 새 실험 3 — Misconvergence

학습된 prior가 있는 시스템에 ambiguous input을 준다.

목표:

> 정상적으로 학습된 circuit이 특수 입력에서 잘못된 안정 상태로 수렴할 수 있는가?

측정:

- attractor 선택
- confidence / stability
- reality mismatch
- correction latency
- feedback 후 회로 수정

이 실험은 착시와 잘못된 직관을 계산 모델 안에서 연결하는 핵심이다.

---

# 39. 가장 중요한 새 실험 4 — Binding Continuity와 수렴 안정성

기존 v089/v090을 더 일반화한다.

조건:

- opaque identity
- short uniform identity
- semantic identity
- learned distributed identity

측정:

- parent binding
- graph completion
- convergence time
- wrong candidate activation
- circuit stabilization
- transfer to new structure

목표:

> **semantic identity가 단순 출력 형식의 이점인지, 반복 학습과 circuit formation에서도 실제 이점을 가지는지**

를 분리한다.

---

# 40. 가장 중요한 새 실험 5 — 동일 primitive의 A-level 재사용

같은 기본 microcircuit primitive를 서로 다른 문제 수준에 적용한다.

예:

### 낮은 A

- noisy pattern completion
- ambiguous shape classification

### 중간 A

- object/concept association

### 높은 A

- rule selection
- logical inference
- hypothesis competition

같은:

\[
Activation
+
Competition
+
Inhibition
+
Recurrence
+
Convergence
\]

구조가 여러 수준에서 작동할 수 있는지 본다.

성공하면:

\[
\boxed{
Same\ Primitive
+
Different\ Representation
}
\]

가 단순 철학이 아니라 계산 아키텍처가 된다.

---

# 41. 가장 중요한 새 실험 6 — Decision vs Explanation

먼저 시스템이 결론을 내리게 한다.

그 뒤:

> 왜 그렇게 판단했는가?

를 별도로 재구성하게 한다.

비교:

- 실제 실행 경로
- 나중에 생성한 explanation graph
- 둘의 일치율
- omitted dependency
- fabricated dependency

이 실험은:

\[
Decision\ Generation
\neq
Explanation\ Reconstruction
\]

가 실제 시스템에서도 나타나는지 검증한다.

---

# 42. 가장 중요한 새 실험 7 — Attractor Strength vs Revisability

학습이 진행될수록 attractor를 강하게 만든다.

측정:

\[
Attractor\ Strength\uparrow
\]

할 때:

- inference latency
- accuracy on familiar data
- error on shifted data
- correction time
- graph expansion probability

가 어떻게 변하는지 본다.

예상되는 핵심 trade-off:

\[
\boxed{
Compression
\leftrightarrow
Flexibility
}
\]

이다.

너무 약하면 매번 다시 계산해야 하고,
너무 강하면 틀린 직관을 수정하기 어렵다.

---

# 43. 물리 하드웨어에서 검증해야 할 진짜 포인트

물리적 신경망의 목적을 단순 연산속도로 잡으면 이 가설의 핵심을 놓친다.

검증해야 할 것은:

1. 같은 primitive가 여러 representation level에서 동작하는가
2. local recurrent dynamics로 candidate competition이 가능한가
3. repeated graph가 sparse circuit으로 안정화되는가
4. 안정화 후 event 수가 줄어드는가
5. novelty/error가 graph expansion을 유도할 수 있는가
6. structural plasticity가 잘못된 attractor를 수정할 수 있는가
7. binding/routing이 중앙 controller 없이 충분히 local하게 유지되는가

이다.

---

# 44. Configuration은 느리게, Execution은 Local하게 — 이번 모델에서의 의미

기존 원칙:

\[
\boxed{
Configuration\ is\ slow
}
\]

\[
\boxed{
Execution\ is\ local
}
\]

은 그대로 유지된다.

하지만 이제 configuration이 무엇을 하는지가 더 구체적이다.

### Configuration / Plasticity

- 새로운 graph를 circuit으로 압축
- connection create/delete
- attractor basin 조정
- cross-A routing 수정
- binding pattern 강화
- 잘못된 shortcut 제거

### Local Execution

- candidate activation
- signal propagation
- inhibition
- recurrent completion
- local convergence

즉 상위 계층은 매 순간 답을 계산하는 것이 아니라:

> **계산 회로가 어떤 형태로 존재할지를 천천히 바꾼다.**

---

# 45. 시간 규모도 계층적으로 나눌 수 있다

\[
\begin{aligned}
\mu s-ms &: local\ neural/event\ dynamics\\
ms-s &: competition / recurrent\ convergence\\
s-min &: short-term\ adaptation\\
longer &: synaptic\ reinforcement\\
much\ longer &: structural\ graph\ compilation
\end{aligned}
\]

여기에 새로 하나를 넣을 수 있다.

\[
\boxed{
Novelty/Error
\rightarrow
Temporary\ Graph\ Expansion
}
\]

즉 구조 변경 자체는 느리더라도,
현재 실행에서는 기존 circuit만으로 해결되지 않을 때
임시 graph를 빠르게 확장할 수 있어야 한다.

---

# 46. 최종 통합 아키텍처

전체 구조를 가장 압축해서 표현하면:

```text
                    ┌────────────────────────┐
                    │ Environment / Reality  │
                    └───────────┬────────────┘
                                │
                                ▼
                ┌──────────────────────────────┐
                │ Hierarchical Representations │
                │ A0 ... An                    │
                └──────────────┬───────────────┘
                               │
             ┌─────────────────┴─────────────────┐
             │                                   │
             ▼                                   ▼
   Candidate State Activation          Existing Circuit Recall
             │                                   │
             └─────────────────┬─────────────────┘
                               ▼
                   Binding / Dynamic Routing
                               │
                               ▼
              Competition / Inhibition / Recurrence
                               │
                               ▼
                        Convergence
                               │
             ┌─────────────────┴──────────────────┐
             │                                    │
             ▼                                    ▼
       adequate state                       mismatch / novelty
             │                                    │
             ▼                                    ▼
       perception /                         graph expansion
       judgment / action                    A/D/M adaptation
             │                                    │
             └─────────────────┬──────────────────┘
                               ▼
                    Reality / Error Feedback
                               │
                               ▼
                Plasticity / Graph Compilation
                               │
                               ▼
                     Reusable Circuit
```

---

# 47. 이 모델에서 감각·직관·추론의 관계

## 감각

\[
\boxed{
Low\text{-}A\ Candidate\ Convergence
}
\]

## 개념

\[
\boxed{
Stabilized\ Representation
\ reused\ as\ higher\text{-}A\ node
}
\]

## 직관

\[
\boxed{
Fast\ high\text{-}A\ convergence
\ using\ compiled\ circuits
}
\]

## 명시적 추론

\[
\boxed{
Dynamic\ graph\ expansion
\ when\ compiled\ circuits\ are\ insufficient
}
\]

## 학습

\[
\boxed{
Successful\ graphs
\rightarrow
reusable\ circuits
}
\]

## 착시 / 잘못된 직관

\[
\boxed{
Stable\ but\ externally\ wrong\ convergence
}
\]

이렇게 하면 다섯 현상을 하나의 시스템 안에서 표현할 수 있다.

---

# 48. 지금까지의 가설을 가장 압축한 수식

현재 통합 모델의 실행:

\[
\boxed{
R_{A,t+1}
=
F_M(
R_{A,t},
Context,
Memory,
Binding,
Competition
)
}
\]

반복 후:

\[
R_{A,t}
\rightarrow
R_A^*
\]

로 수렴한다.

정상 수렴:

\[
R_A^*
\approx
Environment
\]

오수렴:

\[
R_A^*
\not\approx
Environment
\]

새로운 문제:

\[
\text{No Stable }R_A^*
\rightarrow
Graph\ Expansion
\]

학습:

\[
Repeated\ Valid\ Graph
\rightarrow
Compiled\ Circuit
\]

숙련:

\[
Compiled\ Circuit
\rightarrow
Lower\ Effective\ Cost
\]

이 전체가 하나의 cycle을 이룬다.

---

# 49. 현재 실험 사실과 새 가설의 경계

## 현재 LLM 실험에서 직접 관찰된 것

- 같은 논리라도 표현·실행 구조에 따라 성공률이 크게 달라질 수 있다.
- path selection과 graph generation은 별개다.
- 외부 proof graph의 D는 구조화된 방식으로 선택적으로 제어할 수 있다.
- D 자체가 증가한다고 단순히 실패율이 증가하지 않았다.
- ID 생성과 이후 ID 재참조는 별개의 문제다.
- 의미 기반 ID가 현재 실험에서 연속 graph 생성 성능을 높였다.
- 올바른 parent binding이 실제 종단 성공의 중요한 실패 지점이었다.

## 감각·직관 문서에서 제시된 작업 가설

- 감각도 후보 활성화·경쟁·수렴 구조를 사용할 수 있다.
- 직관은 압축된 병렬 탐색 또는 빠른 수렴일 수 있다.
- 설명 생성은 판단 생성과 다른 계산일 수 있다.
- 착시와 잘못된 직관은 서로 다른 A 수준의 misconvergence일 수 있다.
- 동일한 계산 primitive가 여러 abstraction level에서 반복될 수 있다.

## 이번 혼합으로 새로 도출한 가설

- Thought-Graph는 고차 추론에만 한정되지 않고 여러 A 수준의 transient relational structure일 수 있다.
- 낮은 A의 수렴 결과가 높은 A의 node가 될 수 있다.
- 직관은 compiled circuit execution, 명시적 추론은 graph expansion으로 연결될 수 있다.
- novelty/error는 circuit을 graph로 다시 확장시키는 trigger일 수 있다.
- 학습은 Graph ↔ Circuit의 양방향 변환을 관리하는 과정일 수 있다.
- misperception과 bad intuition은 같은 상위 오류 유형인 wrong convergence로 통합할 수 있다.
- 학습 효율과 오류 수정 가능성 사이에는 attractor strength trade-off가 존재할 수 있다.
- A/D/M/B와 circuit familiarity를 함께 봐야 실제 계산 비용을 설명할 수 있을 수 있다.

이 마지막 묶음은 아직 별도의 실험이 필요한 가설이다.

---

# 50. 이 통합 가설의 가장 중요한 연구 질문

가장 큰 질문은 이제 다음처럼 바뀐다.

> **감각에서 고차 추론까지 동일한 ‘분산 활성화 → binding → 경쟁·억제 → 재귀적 보정 → 수렴’ primitive를 서로 다른 abstraction level에서 반복 사용할 수 있는가? 그리고 새로운 문제에서는 이 구조가 동적 Thought-Graph를 확장하고, 반복적으로 성공한 graph는 structural plasticity를 통해 재사용 가능한 physical circuit으로 압축되며, 익숙한 문제에서는 그 circuit의 빠른 수렴이 직관처럼 작동하도록 만들 수 있는가?**

여기에 오류까지 포함하면:

> **또한 잘못 학습된 prior 또는 circuit이 착시·잘못된 직관과 같은 stable misconvergence를 만들 때, novelty/error 신호를 이용해 기존 attractor를 깨고 graph를 다시 확장·수정할 수 있는가?**

가 된다.

---

# 51. 가장 짧은 버전

기존 문장:

> **사고는 그래프를 만들고, 학습은 그 그래프를 회로로 압축하며, 직관은 그 회로를 바로 실행한다.**

이번 감각·착시 가설까지 섞으면 다음처럼 확장된다.

> **지각과 사고는 여러 후보를 만들고 수렴시키며, 학습은 반복적으로 성공한 수렴 경로를 회로로 압축하고, 직관은 그 회로를 빠르게 재실행한다. 새로운 상황에서는 회로가 다시 그래프로 풀리고, 착시와 잘못된 직관은 그 회로가 잘못된 안정 상태로 수렴한 경우일 수 있다.**

수식으로는:

\[
\boxed{
Input
\rightarrow
Candidates
\rightarrow
Binding
\rightarrow
Competition
\rightarrow
Convergence
\rightarrow
Learning
\rightarrow
Circuit
}
\]

그리고 다음 입력에서는:

\[
\boxed{
Circuit
\rightarrow
Fast\ Convergence
}
\]

문제가 생기면:

\[
\boxed{
Mismatch
\rightarrow
Graph\ Expansion
\rightarrow
Relearning
}
\]

---

# 52. 한 문장 최종 요약

> **감각·개념·직관·추론을 서로 다른 알고리즘으로 보기보다, 여러 abstraction level에서 후보 상태를 활성화하고 의미를 결합한 뒤 경쟁·억제·재귀적 보정을 통해 안정 상태로 수렴시키는 공통 계산 과정으로 보고, 새로운 문제에서는 A/D/M 구조를 가진 동적 Thought-Graph가 확장되며 반복적으로 성공한 graph는 재사용 가능한 회로로 압축되고, 익숙한 문제의 직관은 이 회로의 빠른 재활성화로, 착시와 잘못된 직관은 같은 회로 시스템이 현실과 다른 attractor로 안정 수렴한 경우로 설명할 수 있다는 것이 현재의 통합 가설이다.**
