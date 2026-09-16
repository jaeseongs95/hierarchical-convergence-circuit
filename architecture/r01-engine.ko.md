# HCR R0.1 실제 실행 아키텍처

버전: 0.1.0. 상태: 기능적 CPU reference. 설계 원문과 구현 선택을 구분한다.

## 실제 의존성

```text
model/codec
  ├─ binding → workspace
  ├─ dynamics (두 A 수준의 동일 수식)
  ├─ circuits ↔ compiler → learning
  ├─ proof (판단 이후 정당화 복원)
  └─ trace
       ↓
     runtime (정답/World/evaluator 없음)
       ↓
tasks + evaluation/reference + evaluation/protocol
       ↓
 CLI / 개발 integration / 기록 후 audit
```

| 파일 | 실제 책임 |
|---|---|
| model.py | 공개 관측, Mode, 상태, 2후보 Group, Link, Program, Decision, Feedback, 비용 계약 |
| codec.py | strict JSON, 원자적 메모리 snapshot 교체, 공개 입력 검증 |
| binding.py | 대상 이름과 무관한 역할 topology 대조 및 current edge binding, revision 검사 |
| workspace.py | 공개 topology의 모든 제한된 단순 경로 열거, 후보와 신호 연결 생성 |
| dynamics.py | 같은 동기 recurrence, softmax 두 후보, 안정/모호/진동/예산 상태 |
| circuits.py | role Program/guard/prior의 versioned memory, 새 입력 recall, snapshot 검증 |
| compiler.py | 구조 certificate 검사 후 반복 검증 Program을 회로로 등록 |
| learning.py | 허용 feedback에 따른 recall strength·outcome frequency·회로 등록/약화 |
| runtime.py | infer와 feedback, 새로운 attempt와 measurement request의 시점 제어 |
| proof.py | 현재 활성 후보를 primitive DAG로 복원. 원래 판단을 고치지 않음 |
| trace.py | append-only hash-chained JSONL event |
| tasks/toy_world.py | 실제 참/거짓과 공개 noisy observation을 가진 작은 환경, 요청된 측정 |
| evaluation/reference.py | 외부 reachability, 직접 premise·경로 coverage·proof D 재검산 |
| evaluation/protocol.py | TRAIN→snapshot→4조건 frozen→ADAPT→저장/재로드→retention |
| evaluation/audit.py | 독립 tick 재계산, 순서/권한/summary/cost, 기존 reference 재실행 |
| cli.py | check/demo/verify/infer. 다른 계산 엔진을 만들지 않음 |

## 세 가지 그래프를 혼합하지 않는다

1. `Program`: recurrence 신호 연결. cycle 허용. 각 Group은 `(p,1-p)`라는 경쟁 후보 쌍이다.
2. `events.jsonl`: 시간순 실제 실행 기록. feedback 이전 판단과 이후 판단을 따로 보존한다.
3. `Proof`: assumption과 primitive 직접 전제의 DAG. 신호상 top_down을 증명 premise로 쓰지 않는다.

그룹의 identity는 현재 observation/attempt + Program 내부 role id로 scope된다. 동일 Program의 e:0은 새 episode에서 새 값으로 시작하며 예전 활성값을 저장해 답으로 돌려주지 않는다. `Binding`은 관측 digest와 revision을 갖고, 이전 revision binding을 새 입력에 쓰면 거부한다. 분산 임베딩에서 의미를 학습하는 binding은 아니다.

## 단일 커널

각 group은 두 후보 positive/negative를 갖는다. 현재 p가 양수 후보 활성이다. 모든 A 수준에 동일한 함수가 적용된다.

```text
drive = bias + public_observation_or_learned_prior
        + Σ weight × (2 × previous_source_p - 1)
positive_logit = drive + self_excitation × p - inhibition × (1-p)
negative_logit = -drive + self_excitation × (1-p) - inhibition × p
target = softmax(positive_logit, negative_logit).positive
next_p = (1-damping) × p + damping × target
```

모든 갱신은 같은 이전 snapshot을 읽는다. A0는 edge의 통과 가능/불가능 특징, A1은 prefix 경로·최종 경로 후보다. 연결 topology와 bias는 AND/OR 문법을 수치적으로 표현한다. weight와 encoder 자체를 데이터로 학습했다는 주장은 하지 않는다. top_down 옵션을 끄면 해당 링크 전달만 빠진다.

## 실제 학습값과 수작업 상수

수작업: feature score 해석, relation gain, recurrence, AND/OR topology, 모든 예산, threshold, feedback 후 credit 정책.
경험에서 바뀌는 것: 검증된 Program의 장기 등록, cue/topology→회로 recall strength, 성공한 사례의 양·음 outcome frequency, 활성/은퇴 여부.

학습 prior는 `prior_gain × strength × balance × 최대관측불확실성`이다. balance는 `(positive-negative)/(positive+negative+1)`이다. 현재 관측이 강하면 prior 입력이 작아진다. output frequency는 prior 신호일 뿐 반환할 답이 아니다. 같은 회로에 명확한 반대 관측을 넣으면 같은 kernel이 다른 답을 계산한다.

## Graph ↔ Circuit 범위

처음에는 공개 topology에서 경로를 열거하고 group/link를 만든다. 회로화 후에는 topology 역할 binding으로 저장된 Program을 재사용해 경로 탐색과 동적 재구성을 생략한다. 양쪽 모두 settle을 거친다. 회로가 이전 정답을 직접 반환하는 분기는 없다.

R0.1 compiler는 전체의 작은 관계 graph를 보존한다. 일반 subgraph mining/논리 단축/코드 JIT가 아니다. cold와 warm의 Program 크기나 primitive proof D가 같을 수 있다. 비용 감소를 주장할 때 이를 숨기지 않는다.

새 topology는 recall guard가 거부해 새 workspace가 된다. 오류 뒤 공개된 새 측정으로 재시도할 때는 이전 circuit 의존을 중단하고 graph를 다시 전개한다. 이것은 범용 바이트코드 decompiler나 무한한 후보 발명기가 아니다. 이미 모든 공개 경로가 있고 더 공개된 정보가 없다면 보류하며, 의미 없는 반복을 '확장 성공'으로 세지 않는다.

## Feedback 권한과 정책

- TRAIN: 최초 결정 이후에만 외부 평가를 읽고 학습한다.
- FROZEN_EVAL: 예측 중 메모리 checksum이 그대로이며 feedback 호출도 거부한다.
- ADAPT: 외부 incorrect 뒤에만 낮은 확신 관측을 재측정하도록 요청한다. 현재는 최대 두 번의 요청이다.

객체에 잘못된 값을 넣어 강제로 수정한 것이 아니라, `ObservationRequest` 이후 환경이 정해진 edge만 더 정확히 측정한다. 그 관측을 새 attempt에서 계산한다. 정보가 없으면 정답을 보장하지 않는다. 엔진은 case명이 예외/모호/정상인지 알지 못한다.

개발 중, 정밀 측정으로 correction에 성공했다는 이유만으로 실패했던 recall prior까지 곧바로 강화하면 원래 약한 관측에서 다시 오수렴하는 것을 확인했다. 그래서 correction에서 얻은 structural evidence와 prior 신뢰를 구분했다. 재확장으로 검증한 음성 사례는 evidence에 추가하되 약화된 strength를 그 attempt에서 되돌리지 않는다. 이후 새로운 정상 episode에서의 증거로는 다시 강화할 수 있다. 이는 명시적 수작업 credit 정책이며 메타학습된 규칙이 아니다.

## 평가 경계

내부 안정 상태는 세계 정답이 아니다. stable margin도 calibrated 확률이 아니다. 공개 관측과 prior가 모두 없을 때는 `unsupported`로 보류한다. 대칭 상태의 작은 margin은 `stable_ambiguous`다. 진동/예산/후보 없음도 별도다.

`Decision readout`을 먼저 event로 남기고, 이후 Proof를 재구성한다. proof가 성립하지 않아도 답을 바꾸지 않는다. proof의 assumptions는 사실로 승격되지 않는다. reference는 세계 정답, assumption 정합성, proof의 구조적 유효성을 각각 판정한다.

양의 proof는 start_edge/extend_path, 음의 proof는 각 경로의 blocked witness와 모든 경로 coverage로 검증한다. 원래 primitive D는 이 그래프에서 재계산한다. circuit 1회 호출이라는 이유로 D를 1로 바꾸지 않는다.

## 운영 제한

순차 CPU reference이며 Python 3.12+ 표준 라이브러리만 사용한다. 후보 group 최대32(후보64), edge8, 경로4, 경로길이4, circuit16부터 시작한다. 출발점과 목표가 다른 유한 directed graph이며 self-loop와 중복 arc는 거부한다. 부모 callback으로 숨은 정답이 들어오는 API는 없다.

메모리 JSON은 checksum+schema+프로그램 구조를 검사한다. 학습 feedback은 신뢰된 외부 실행기의 API다. checksum이 악의적인 외부 정답 공급자까지 인증한다는 뜻은 아니다. 실제 보안 격리나 하드웨어 local execution은 구현하지 않았다.
