# EXP-62 / r16: 공유 줄기와 재합류 우회로의 기술 확인

## 질문과 표현 가능성

현재 Adaptive learner가 세 번의 검증된 양성 경험으로 형성한 길이 2 motif를 새 graph에서 적용할 때, motif 내부의 다른 출구가 보존되고 후속 판단의 실제 primitive 근거로 이어지는가?

학습 대상은 세계 사실이나 실패 위치가 아니라 역할화된 양성 경로 패턴이다. compiler의 양성 최종 primitive proof 추출 → native feedback → pending 3회 → pattern circuit → activation/binding → workspace.apply → 내부 side-exit 추가 → dependency coverage → finish proof → dependency_gate 채택 경로를 검증한다. 엔진·학습 규칙·threshold는 변경하지 않는다. pattern_lengths=[2], prior_gain=0을 EXP58 설정 그대로 사용하며 route_only로 판정한다. strength에 의한 답 교정이나 새로운 탐색 정책의 효과를 주장하지 않는다.

## 비중복 범위

EXP44는 길이 4 경로와 목표에 닿지 않는 dead-end 분기를 평가했다. EXP58~61은 시작과 목표를 공유하는 분리된 두 완결 경로 및 score/readout 경계를 다뤘다. 이번 graph는 **하나의 stem, motif 내부의 갈림길, 재합류, 공통 마지막 edge**를 가진다. 첫 macro가 지나간 내부 노드에서 시작하는 우회 경로가 있어야만 True를 증명할 수 있다. 새 알고리즘·발견의 독립 표본이 아니라 현재 코드의 새로운 조합에 대한 기술 확인이다. EXP50~52의 약화×관측 조합과 다르다.

## 고정 입력과 대조

슬롯 순서는 e0:S→A, e1:A→B, e2:B→J, e3:A→C, e4:C→J, e5:J→G이다. e2는 -1이고 e0/e1/e3/e5는 +1이다. bypass_open의 e4는 +1, all_blocked의 e4는 -1이다. 외부 world의 실제 passability는 이 두 authored 입력에서 score의 부호와 일치한다. 이 정보가 native inference나 선택에 정답으로 전달되지는 않는다.

다른 ID를 가진 양성 길이 2 chain 세 개를 native train하고, 각 inference 뒤 별도 reference 프로세스가 truth·proof·가정을 검사하여 feedback을 발급한다. host가 memory나 strength를 편집하지 않는다. 해당 episode 세 개는 컴파일의 이력 조건이며 서로 다른 구조적 일반화 표본이 아니다.

평가는 각 case에 learned_on, learned_off, unlearned_on 순서로 실행한다. ON/OFF는 같은 학습 memory, config, observation, episode/revision과 budget을 받는다. 미학습은 빈 memory에 ON이다. 각 evaluation은 새 frozen session이며 feedback·관측 갱신·강제 frontier 선택·재시도가 없다. 같은 topology의 두 world를 독립 family로 세지 않는다.

## 사전 예측과 판정

1. learned_on의 첫 circuit 후보는 [0,1]이고 apply의 추가 frontier에는 [0,3]이 남는다. 이를 측정하지 못하거나 다른 행동을 하면 이 예측은 불충족으로 기록한다.
2. 막힌 첫 경로의 잠정 False는 전체 coverage 전 최종 False로 채택되지 않는다. 열린 경우 [e0,e3,e4,e5]의 실제 최종 proof로 True를 채택하고, 모두 막힌 경우 두 경로를 포괄하는 False를 채택할 것으로 예측한다. raw 정답·proof validity·가정의 사실성·채택을 따로 판정한다.
3. learned_on은 learned_off보다 expansion이 적을 것으로 예측한다. tick 감소는 탐색 지표이며 요구하지 않는다. 학습·binding·pool·proof·저장 비용을 생략한 전체 효율 주장은 하지 않는다.
4. learned_off와 unlearned_on의 정수 비용 및 판단이 같을 것으로 예측한다. wall time은 고정 순서·단일 실행의 기술적 측정이며 속도 우위 추론에 사용하지 않는다.

기술 수용은 정확한 입력·기억·제어·예산·원자료와 독립 검산이 성립하는지다. 예측이 맞는지는 별도 결과다. 불일치·오답·abstention·시간 초과를 제거하거나 성공하도록 조건을 바꾸지 않는다.

## 예산과 보존

서버 준비 시작부터 검산·봉인까지 총 wall 600초, 순차 numeric worker 1개, train 3회와 evaluation 최대 6회다. session당 advance 16회·kernel tick 5120 상한을 기존 execute가 예약한다. native/reference/learn stage는 최대 60초, audit은 최대 90초이며 eval 종료 전 검산·봉인 110초, audit 종료 뒤 봉인 20초를 예약한다. 하위 프로세스 주소 공간 한도는 512MiB이며 RSS나 전체 프로세스 트리 메모리 측정과 같지 않다. raw 출력은 128MiB 한도다. 새 전용 폴더와 배타적 출력으로 중복 실행·덮어쓰기를 막는다.

서버 전송용 archive의 hash와 모든 source bytes를 검증하고 시작·종료 source 불변성을 검사한다. 초기/진행 packet, training/reference/learning, memory0~3, 여섯 evaluation, partial/failure, summary, phase timing, manifest와 ZIP을 남긴다. 기존 독립 journal replay와 candidate/proof/readout 검산을 재사용하고 두 종류의 변조가 거부되는지 확인한다. 전송 및 사람이 승인하는 대기 시간은 서버 실험 실행시간과 별도로 취급한다.

이번 요청은 작은 기술 확인까지다. 12-family 확인 실험, 임계값 조정, 약화·관측 갱신, 새 기능 구현, 기존 인증 run 재실행은 수행하지 않는다. 효과 부재도 유효한 결론으로 남기며, 이 한 family로 일반화·학습 비용 회수·물리 효율을 입증하지 않는다.
