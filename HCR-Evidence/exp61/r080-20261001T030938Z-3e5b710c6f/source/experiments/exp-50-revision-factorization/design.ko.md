# EXP-50 / R069: checkpoint·관측 내용·revision 경로 분리

## 결론을 가르는 질문

R068에서 외부 오답 피드백 없이 native 요청 API를 사용할 수 없음을 확인했다. 이번에는 이미 지원하는 피드백 경로에서 지속 memory 변경, 전달 관측 내용, 정상 revision 경로를 나눠 비교한다. core와 이전 evidence를 바꾸지 않는다.

## 동결 조건

R064 after_correction memory를 M0로 사용한다. R068의 config·계산 상한·edge topology와 순서를 유지하되 e0 score를 1로 바꾼 새 조건임을 기록한다. episode는 r069-probe, e1 score는 +0.8이다. 참조 세계는 e0=True, e1=False로 고정한다. 관측의 score 부호가 참조 정답은 아니다.

최초 donor를 ADAPT·회로 ON·route_only로 한 번 실행하고 raw 판단·proof·readout·adoption·finished packet을 저장한다. 별도 evaluator가 authored world로 correct와 proof_valid를 산출한다. 같은 finish branch에 피드백을 한 번 적용한 M1과 요청 직후 packet을 보존한다. 오답 피드백을 강제하지 않는다. 예상과 달리 오답 피드백이나 요청이 없으면 payload와 후속 실행의 부재를 기록한다.

| 경로 | memory | payload |
| --- | --- | --- |
| 새 세션 | M0 | stale: e1=+0.8 |
| 새 세션 | M0 | fresh: e1=-1 |
| 새 세션 | M1 | stale |
| 새 세션 | M1 | fresh |
| 정상 revision | M1 | stale |
| 정상 revision | M1 | fresh |

후속 관측은 모두 같은 episode·revision=1·config·topology·e0 score를 사용한다. 설정상 회로 gate는 ON이다. 정상 revision은 현재 core 계약에 따라 실제 circuit eligibility가 OFF다. 두 revision은 같은 request packet에서 각각 복원한다. 후속 피드백과 자동 retry는 없다.

## 예측과 중단 기준

최초 donor는 True를 채택해 참조 세계에서 오답이고, 실제 재사용한 회로는 오답 피드백으로 약화하며 e1만 요청할 것으로 예측한다. 회로 약화가 없으면 learning_construct_not_engaged로 판정한다. 모든 stale 분기는 True 오답, fresh 분기는 False 정답 채택을 예측한다. 예측 위반을 코드 실패와 동일시하지 않으며 원자료를 보존한다. 한 donor와 여섯 분기 슬롯 뒤 종료한다. 예상한 결과를 얻기 위해 조건을 바꾸거나 반복하지 않는다.

## 비교와 비용

새 세션 M0/M1 비교는 checkpoint 변경 효과다. 각 경로의 stale/fresh 비교는 전달 score 내용 변경 효과다. M1 새 세션/revision 비교는 attempt·authorization·mismatch·회로 사용 정책이 함께 달라지는 API 경로 차이다. 순수 세션 지속 효과로 해석하지 않는다.

요청한 e1의 이상적인 toy-world 측정을 한 번 획득하고 fresh 세 분기에 같은 payload를 전달한다. stale은 cached 전달이며 획득은 0회다. acquisition 1, fresh delivery 3, cached delivery 3을 분리한다. 이는 물리 센서나 새 독립 표본이 아니다. donor·피드백·획득은 한 번씩 기록하고, 복제된 이력을 각 branch 비용에 중복 합산하지 않는다. kernel ticks, expansion, reuse, binding과 observation_requests를 따로 보고한다. 시간·전력·총효율 우위를 주장하지 않는다.

## 검증

별도 프로세스의 reference·measurement·최종 evaluator가 기존 수식·학습·요청·revision 검산기를 재사용한다. raw/hash coverage, 정확한 finished/feedback/request prefix, M0/M1, 관측과 branch delivery 결속을 확인한다. 변조 거부와 source/parent/bundle 바이트 일치, 최종 core 회귀 1회를 수행한다. 합성 selftest는 참조 fixture 검사이며 연구 실행에 합산하지 않는다. 실패 시 새 evidence에 first failure와 로그를 보존한다.

## 주장 경계

이진 True 판단에 correct=False라는 피드백은 이미 False 정답 정보를 제공한다. 새 측정 후 교정이 일어나도 정답 정보를 최초로 획득했다거나 센싱이 반드시 필요했다고 주장할 수 없다. feedback 정보만과 학습만의 효과, 순수 persistence, 자율 conflict sensing, HCC 고유 우위와 일반화는 이번 비교로 검증하지 않는다.

실행: 저장소 루트 Run-HCR-R069.cmd. 설치와 Git 조작은 원클릭에 포함하지 않는다.
