# EXP-63 / r17: 후보 풀 상한에서의 primitive 복귀와 근거 보존

## r16 이후의 질문

r16은 학습한 길이2 motif의 내부 출구 보존과 최종 근거 연결을 확인했지만 tick은 늘었다. 같은 조건의 반복으로 효율 우위를 찾지 않는다. 다음 질문은 후보를 늘려 현재 max_pool_candidates=4 경계를 넘었을 때, 일부만 검사한 후보로 승자를 정하지 않고 primitive 확장으로 돌아가는가다. 활성화 풀이 넘친 상태에서도 실제 답에 필요한 마지막 분기와 정당화가 보존되는지 본다.

EXP44의 단일 dead-end spur, EXP58~61의 분리된 두 완결 경로, r16/EXP62의 내부 갈림길·재합류와 구별된다. 이번에는 start에서 가능한 길이2 binding이 정확히 4개/5개인 fanout을 만든다. 네트워크를 새로 학습하거나 자율적인 탐색 정책을 구현하는 과제가 아니라 기존 예산 경계의 기술 확인이다. 이전 설계·결과 문서와 activation/workspace의 실제 경계를 확인했으며 상한 초과→primitive fallback을 겨냥한 이 조건은 해당 문서들에 없다.

## 입력과 고정 대조

S→A 뒤 A→B1..Bn, 마지막 Bn→G만 연결하며 n=4/5다. 다른 B는 dead end이고 score는 +1이다. 마지막 edge만 +1(open)/-1(blocked)로 달라진다. 두 크기·두 world가 만드는 4개 case에 learned_on, learned_off, unlearned_on을 case-major 고정 순서로 실행한다. 토폴로지가 다른 경우의 비용 차이를 상한만의 순수 효과로 해석하지 않는다.

학습은 서로 다른 episode ID의 양성 길이2 chain 3개, 빈 memory부터 기존 native inference→별도 reference→native feedback이다. learner·src·threshold·binding 순서·pool 상한·route_only·prior_gain=0·pattern_lengths=[2]는 r16 그대로다. 평가 중 feedback·강제 frontier 선택·관측 갱신·재시도는 없다. 외부 world는 별도 reference/audit 단계만 읽는다. 독립 구조 표본은 아니며 authored fanout family 하나의 경계 사례다.

## 사전 예측

1. fan4 learned_on의 첫 scan은 complete=True, matched=4이며 첫 확장은 circuit이다. fan5는 matched=5에서 complete=False/fallback_reason=pool_capacity, 해당 root의 pool 결과 없이 primitive e0를 확장할 것이다. scan의 부분 목록은 활성화·선택에 쓰이지 않아야 한다.
2. learned_on에서 모든 [e0,ei] 분기 prefix가 실제 expansion의 added path에 남는다. root 또는 그 뒤 확장의 추가분을 함께 확인한다. 이 체크는 최종 proof의 대체물이 아니다.
3. 12개 evaluation이 올바른 값·유효 proof·사실인 가정·실제 답 채택을 유지할 것이다. open의 최종 근거는 e0/en/e(n+1), blocked는 실제 False 답이다. 미탐색 분기가 있는 잠정 False와 최종 False를 구별한다.
4. learned_off와 unlearned_on은 case별 판단·정수 비용이 같을 것이다. expansion·binding·pool_calls·kernel tick·학습 및 저장 비용을 별도로 기록한다. 비용 감소는 수용 조건이 아니며 wall 단일 순서로 통계적 속도 우위를 주장하지 않는다.

## 예산·검증·중단

AI Research SSH의 새 전용 폴더에서 train3/feedback3/eval12, 순차 numeric worker1, 서버 준비~독립 검산~봉인 600초 상한이다. stage60초(audit90초), audit+seal110초와 seal20초 예약, session16 advances/5120ticks, child 주소공간512MiB, stage 종료 후 raw128MiB 한도, retry0이다. 주소공간은 peak RSS 측정이 아니다.

r16의 동결 하네스에서 식별자·case 수·관측 집계만 새 도구로 파생하고 원본은 수정하지 않는다. 기존 execute·packet_states·verify_candidate를 재사용해 source·config·memory chain·관측·정확한 journal·proof/readout을 별도 프로세스에서 검산한다. 값/proof 변조 거부와 새 trace 집계 self-check를 남긴다. 시작/종료 source hash, partial/failure, 각 stage 시간, raw manifest와 ZIP을 보존한다. 예측 불일치를 제거하거나 성공하도록 입력을 바꾸지 않는다. 장치 실패와 가설 실패를 따로 보고한다.

이 요청은 이 작은 기술 실험까지다. 일반화·효율 우위·새 학습법·물리 에너지 우위는 입증 대상이 아니다. 새로운 최적화나 대규모 확인 배치는 별도 결정이다.
