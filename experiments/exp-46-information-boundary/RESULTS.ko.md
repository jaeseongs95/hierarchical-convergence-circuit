# EXP-46 / R065 결과

## 결론

**현재 adaptive 구현은 절차적 회로와 교정 이력을 보존하지만, R064에서 얻은 교정 관측을 새 판단이 조회하는 세계 사실로 저장하지 않는다.** 원래 잘못된 관측을 다시 받으면 같은 오류가 나오는 현상은 이 정보 전달 경계와 일치한다. 이력 hash/version은 무결성 검사에 쓰이므로 “교정 뒤 아무 정보도 남지 않았다”는 표현은 부정확하다.

R065는 [R064 원자료](../../HCR-Evidence/exp45/r064-20260920T024825Z-d995fcc733/summary.json)의 재분석이다. [이번 evidence](../../HCR-Evidence/exp46/r065-20260920T054159Z-5a8a87d609/result.json)는 기존 frozen packet 12개의 참조 채점 24건을 담는다. 새 native 연구 실행과 새 독립 표본은 각각 0이다. 기존 결과를 추가 실험 성공으로 세지 않는다.

## 관찰

[memory 필드 대조](../../HCR-Evidence/exp46/r065-20260920T054159Z-5a8a87d609/memory_flow.json)에서 오류 feedback 뒤에는 circuit 약화와 이력 변화가 있었다. 올바른 False 판단의 feedback 뒤에는 다음만 바뀌었다.

| 항목 | after_feedback → after_correction |
|---|---|
| memory version | 4 → 5 |
| consumed_feedback / patches | 각각 이력 1개 추가 |
| patch changes | `[]` |
| circuits / pending | 전체 내용 동일 |
| full session | 교정 관측·판단·feedback을 보존 |
| fresh 평가 session | 과거 feedback / requests는 각각 `{}` |

[source 정보 흐름](FLOW.ko.md)도 일치한다. `update_adaptive`는 올바른 True proof에서만 구조 학습 분기에 들어간다. activation pool은 compiled circuit와 현재 관측을 사용한다. persistent memory에는 특정 상황의 edge truth를 저장하고 조회하는 계약이 없다. 반면 full session의 held/feedback 및 보존된 trace에는 교정 경험이 남는다. 이를 읽는 새로운 기능이 이미 구현돼 있다는 뜻은 아니다.

[참조 세계 대조](../../HCR-Evidence/exp46/r065-20260920T054159Z-5a8a87d609/counterfactual.json)는 동일 packet의 truth label만 바꿨다. 세 snapshot, ON/OFF 모두 아래와 같았다.

| 고정 public input | 기존 채택값 | closed: e0=True, e1=False | open: e0=True, e1=True |
|---|---|---|---|
| misleading-repeat: (0.8, 0.8) | True | 오답 | 정답 |
| truthful-control: (1, −1) | False | 정답 | 오답 |

`truthful-control`과 `misleading-repeat`은 R064에서 붙인 조건 이름이다. open 참조에서는 그 이름이 관측의 진실성을 뜻하지 않는다. 모두 채택된 Boolean 판단이며, None이나 채택 거부를 올바른 False로 처리하지 않았다.

## 해석

같은 관측·memory·config·packet은 동일한 채택값을 갖는다. 그런데 두 참조 정답은 반대이므로, 추가 구별 정보 없이 이 고정 packet이 둘 모두의 정답일 수는 없다. 이는 조건부 논리 관계이며 12개 독립 표본에서 얻은 일반 성능 추정이 아니다. randomness나 추가 계산만으로도, 세계와 상관없는 상태가 고정된 경우 양쪽 정답을 동시에 보장할 수는 없다.

구조 재사용 유지와 세계 사실 교정 유지는 분리된다. R064의 세 snapshot에서 동일한 저장 pattern은 misleading-repeat ON에서 계속 실제 재사용됐다. 교정 후에도 closed 참조에서 올바른 False는 유지되지 않았다. 따라서 **구조 재사용은 관찰됐지만, 그 구조가 새로 배운 e1=False를 기억한다는 주장은 지지되지 않는다.** R063의 양성 경로 회로 형성·재사용 결과를 바꾸지는 않는다.

오류 True에 대한 binary feedback 자체도 정보다. 참조가 신뢰할 수 있고 과제가 이진값이면 그 episode의 도달 불가능성을 알 수 있다. 다만 닫힌 edge의 위치까지 알 수는 없다. R064의 수정 관측에는 그보다 자세한 edge 정보가 들어갔다. 문제는 그 정보의 존재 여부뿐 아니라 어떤 지속 표현과 조회 경로로 다음 판단에 전달되는가다.

## 대안 설명

R064의 primitive OFF도 같은 잘못된 관측에서 틀렸다. 따라서 이 오류를 회로 재사용이 만든 오류로 한정할 수 없다. 약화 강도·activation 임계값·반복 feedback이 행동을 바꿀 가능성은 이번 재분석으로 측정하지 않았다. 그러나 그 조작을 반복하는 것만으로 어느 세계인지 새로 알게 된다는 결론도 나오지 않는다.

open 참조는 closed 세계의 경험으로 만든 memory에 다른 truth를 붙인 것이다. 같은 학습 이력과 두 세계가 동시에 양립함을 검증한 실험이 아니다. 실제 세계가 변했거나 기존 교정 정보가 낡았다면, 사실 memory도 적용 범위·유효 시점·갱신 정보 없이는 틀릴 수 있다. 이 한계는 현재 구현의 부재와 구분한다.

## 판별 실험

다음은 [명시적 사실 기록 baseline 설계](NEXT.ko.md)다. 같은 교정 관측과 같은 저장·조회 예산을 주고, 현재 memory와 단순한 상황별 사실표를 비교한다. HCC에 더 많은 정보가 주어진 군과 적게 주어진 군을 비교해 구조의 효과라고 부르지 않도록 한다. 새 기능 구현은 다음 계약에서 다룬다.

## 현재 주장 가능한 범위

- `observed`: R064 교정 후 구조 정보는 동일하고 관리 이력만 추가됐다. full session에는 교정 정보가 남지만 fresh 평가에는 persistent memory만 전달된다.
- `derived-prediction / 논리 검산 완료`: 동일한 고정 판단에 반대인 두 정답을 부여하면 둘을 동시에 맞힐 수 없다. 이번 12개 packet은 모두 이 관계를 따른다.
- `falsified`의 유지: R064의 고정 조건에서 교정 행동이 잘못된 관측의 재노출까지 유지된다는 예측. R065는 이 판정을 재검산했으며 새로운 반증 표본을 추가하지 않았다.
- `hypothesis`: 사실 기록·조회가 추가된 후 정보량을 맞춘 조건에서도 HCC의 구조가 독자적 이점을 갖는지. HCC 전체, LLM 내부, 인간 인지, 장기 유지, 에너지 효율은 이번 근거로 판정하지 않는다.

별도 로직·프로세스의 검산은 R064 raw의 수식 재생과 기존 summary 일치, 24건의 참조 정답 대조, 9건의 변조 거부를 확인했다. 합성 self-test는 4개 chain truth 조합, 3개 readout 경계, 잘못된 truth 2건의 거부를 확인했다. 전체 core 회귀는 602개 중 599개 통과, 기존 Windows 환경 skip 3개이며 새 실패·skip은 없었다. 검증 세부와 회귀 결과는 [전달 검증](../../HCR-Evidence/r065-validation/delivery-verification.json)에 기록한다. 이는 독립 연구자 감사가 아니다.
