# 물리 substrate까지 이어지는 실행·학습 계약

## 목적과 현재 경계

S01·S02·S04·S06의 **고정 자원 풀 + 가변 연결 + Plasticity/I/F**를 장기 설계 계약으로 보존한다. 현재 구현은 CPU symbolic reference이고 물리 신경망이 아니다. 이 문서는 아직 호출되지 않는 하드웨어 추상 클래스나 simulator를 추가하지 않는다.

`Physical system IS the network`는 가중치를 파일에 저장한다는 뜻이 아니라 소자의 상태·상호작용이 계산에 직접 참여한다는 원문 목표다. 이를 단순 GPU 가속의 별명으로 바꾸지 않는다.

## B0 — 고정 자원 풀과 인터페이스 계약

뉴런 수를 생물학적 상수로 가정하지 않고 **특정 실험의 계산 자원 총량**을 고정한다. 물리 slot identity, 논리 NodeIdentity, SemanticIdentity, RoleIdentity는 다르다. slot 재사용은 기존 proof/reference를 다른 의미로 바꾸면 안 된다.

| 실행 영역 | 보유·수행 | 하지 않을 것 |
|---|---|---|
| local execution | 현재 state, 인접 연결, 입력 event, integrate/decay/inhibit/propagate | 정답 조회, 모든 이벤트의 중앙 재판단 |
| routing/I/F | 연결·port mapping·revision 및 배치 | 이미 처리 중인 event의 의미를 몰래 변경 |
| plasticity | connect/disconnect, weight/threshold/delay 갱신, 승인된 구조 변경 | 미검증 공동 활성화를 자동 정답 지식으로 승격 |
| modulation | 공개 novelty/error, reward/attention, 업데이트 예산 | hidden truth를 실행 입력으로 제공 |

원문 원칙 **Configuration은 상대적으로 느리게, Execution은 local하게**는 Python controller 함수가 나뉘었다는 사실만으로 달성되지 않는다. 초기 reference controller는 지역 동작을 시뮬레이션할 수 있으나 나중에는 중앙 개입 횟수와 inter-region 통신량을 실제 계측한다.

빠른 state 갱신, 중간 가소성, 느린 topology 변경의 시간축을 나누되 원문의 μs~시간 예시는 구현 목표값으로 복사하지 않는다. 실험에서는 tick/generation/learning epoch 및 물리 시간의 대응을 따로 정한다. transition 도중 graph 수정은 barrier/version 계약으로 처리한다.

## B1 — sparse / local / event-driven backend

현재 `dynamics.tick`은 모든 group/link를 동기로 계산한다. `Trace.emit`은 실행 기록이지 event-driven scheduler가 아니다. 첫 backend는 활성 변경 집합, 지역 이웃, 큐와 지연을 명시하고 같은 입력·memory·회로를 동기 reference와 비교한다.

단순히 변경 없는 값을 건너뛰는 정확한 최적화와, asynchronous update처럼 상태 궤적 자체가 달라지는 알고리즘 변경을 구별한다. 수치 허용오차·순서·최종 판단·오수렴·보류 기준을 미리 고정한다. trace hash가 완전히 같아야 한다는 조건을 무조건 부과하지 않는다.

계측: 활성 slot 비율, event/queue 수, routing hop·byte, state/memory read-write, queue 지연, learning/reconfiguration 비용, 정확도·수정비용. 연산 카운터는 에너지 proxy일 뿐 실제 joule 측정으로 바꾸지 않는다. GPU의 우월성/비효율성을 선결론으로 두지 않는다.

## B2 — physical / neuromorphic 실험

B0의 의미 계약과 B1의 실제 병목 결과에 근거해 장치를 선택한다. local competition/recurrence, 여러 표현 수준의 primitive 재사용, binding 유지, 구조 변경 비용, 잘못된 attractor 수정 가능성을 각각 검사한다. 소자 잡음·정밀도·routing 제약·재구성 시간·전력의 단위와 조건을 기록한다.

기존 LLM 결과, CPU HCR 효과, backend 비교, 물리 측정을 별도 evidence로 유지한다. 학습 I/F가 병목이면 그 결과도 남긴다. 범용 인지·생물학적 동일성이나 효율 우위를 이 문서만으로 주장하지 않는다.

## 소프트웨어 단계와의 관계

B0 명세는 지금 유지한다. B1/B2는 R0.7 전체가 기술적으로 필수라는 뜻이 아니라 비교할 primitive·과제·계측 계약이 확보될 때 독립 조건으로 착수한다. backend를 만들기 위해 EXP-03/04/05/06 진단을 뒤로 미루지 않는다.
