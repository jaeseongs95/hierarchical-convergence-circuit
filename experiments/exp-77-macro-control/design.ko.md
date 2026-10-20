# EXP-77 / R31: 같은 경험으로 만든 일반 macro 대조

전체 방향 HIGH 토론의 결론을 이번 설계 gate에 적용했다. 프로젝트의 공통 primitive·Graph↔Circuit·학습/재사용/재개방 방향은 유지하되, 현재 표현과 실제 소비 경로로 경쟁 설명을 가를 수 있는 과제 하나만 실행한다. 이번 연구는 recurrent activation pool의 실행 기여를 묻는다. 학습 패러다임의 우월성이나 새로운 수치 압축을 주장하지 않는다.

## 두 후보 gate와 선택

| 후보 | 필요한 표현·실제 소비 | 기존 연구와 구별되는 조건 | 판정 |
|---|---|---|---|
| 계층 의미 전달 | 같은 confidence지만 다른 대상/역할의 typed relation을 상위 추론에서 소비 | R19 scalar 전달과 EXP-27 typed reachable/proof memo를 넘어 미학습 역할 조합을 정답 adapter 없이 판별 | 현재 상위 Program은 scalar 입력이며 새 의미 소비기를 구현해야 한다. packet/차단 재검사만으로 H02를 시험할 수 없어 이번 실행에서 보류 |
| 학습 후 실행 방식 비교 | 실제 3episode 학습으로 형성한 길이2 motif를 native workspace가 multi-edge expansion으로 소비 | EXP-25/26의 ON/OFF, R18의 pre-gate와 달리 같은 경험의 일반 verified macro가 동일 primitive 판단/증명에 연결 | 현재 표현·소비 경로로 가능. 누락된 경쟁 설명을 저비용으로 추가하므로 채택 |

지속 예외 교정은 별도 보류다. 현재 learning.py는 오류 시 사용한 회로를 약화하고, 올바른 True proof로 고정 path 문법을 컴파일한다. False 예외 조건을 저장해 새 동일 관측에 적용하는 일반 표현은 없다. EXP-50의 M0/M1×stale/fresh를 반복해 이론을 반증했다고 표시하지 않는다. H01/H02/H07 전체·생물학·LLM·하드웨어에 이번 toy 결과를 일반화하지 않는다.

근거는 src/hcr/{patterns,learning,activation,expansion,workspace,identity}.py, EXP-25/26/27의 design, EXP-50 결과, R18 설계/입력이다. 모두 input_manifest.json에 source SHA를 고정한다. 앞선 HIGH 토론의 4개 독립 관점·교차반박·fresh Judge가 준 조건부 합의를 요약한 것이며, 이번 구현을 다시 독립 감사받았다는 뜻은 아니다.

## 고정 조건과 세 방식

R18의 실제 native 학습 입력3개와 평가 관측4개(chain4_open, chain4_blocked, fan5_open, fan5_blocked), Config를 그대로 쓴다. 새 데이터셋이나 독립 일반화 표본으로 세지 않는다. prior_gain=0, pattern_lengths=[2], min_valid_episodes=3, 판단 정책은 모든 군 route_only다. 공통 실제 학습은 외부 참조 채점→Feedback→native learner로 진행하고 형성된 circuit 1개의 evidence episode가 정확히3개인지 검사한다. 임의로 memory에 circuit을 주입하지 않는다.

- hcr: 형성된 실제 memory, 원본 bounded matching·수치 activation pool·native proposal/적용.
- macro: 동일 memory의 path certificate·역할·길이·활성 flag·version과 동일 matching/후보수/경로길이/binding scan 상한을 사용한다. 모든 결속 edge score가 존재하고 >0일 때만 eligible이다. activation 필드는 정렬용 상수1이며 confidence 추정이 아니다. 길이 내림차순→edge index tuple→circuit ID 순으로 정렬한다. 숫자 pool은 만들지 않는다.
- primitive: 학습 없는 empty memory로 기존 use_circuits=False. 해당 군에 불필요한 학습비를 부과하지 않는다.

macro는 점수와 현재 topology/현재 revision binding 및 공통 memory만 읽는다. truth, case ID, 평가 결과, 채택한 원본 경로를 읽지 않는다. 독립 학습기를 구현한 군은 아니며 motif의 저장 문서 형식도 공유한다. **같은 learned motif를 실행하는 방법**을 비교한다. 일반 macro가 동등하면 고정 path 문법에서 recurrent pool의 추가 이득 주장을 낮춘다. 이는 다른 과제의 유용성·이론의 가능성 반증이 아니다.

matching이 미완료이거나 후보수를 넘으면 일부 후보를 승자로 쓰지 않고 모두 버려 primitive로 복귀한다. native와 같은 합성 후보 group 상한도 해석식으로 점검한다. macro의 공개 점수 검사 수는 별도 ledger로 남기며 native Cost와 서로 다른 단위를 합치지 않는다. native source='circuit' 확장 schema는 검증된 multi-edge 경로를 전달하기 위해 그대로 사용한다. macro arm의 circuit_reuses를 실제 수치 회로 활성화 횟수로 해석하지 않는다.

기존 Workspace.apply가 중간의 side branch를 보존하고 최종 판단 Program·settle·proof를 그대로 수행한다. macro가 답을 반환하거나 decision 수치 계산을 생략하지 않는다. isolated 연구 process에서 expansion.CircuitActivationPool 클래스만 일시 교체하고 finally로 복원한다. core 파일은 수정하지 않는다. 일반 서비스·동시 실행에 이 전역 치환을 배포하지 않는다. 변경 정책 기록은 명시적 research schema로 남기며 native session checkpoint 감사 통과를 사칭하지 않는다.

## 사전 판정과 실패

품질은 각 arm의 외부 정답, abstention, primitive proof validity와 실제 관측 가정의 진실성을 분리한다. strict_correct는 정답 채택+유효 proof+모든 가정의 참조 진실이다. 세 군 모두 strict_correct인 cell만 같은 품질의 비용 비교에 쓴다. 채택/정책 차이는 그대로 보고하며 보정하지 않는다. 적용 순서가 다른 cell은 전체 정책의 효과이고 순수 pool 표현 효과로 부르지 않는다. 같은 expansion을 고른 cell에서만 pool 계산의 추가 비용을 제한적으로 해석한다.

H_pool_added: 같은 품질에서 hcr가 macro에 비해 실제 native 작업이나 실제 총비용의 추가 이득을 보이는가. 같거나 더 비싸면 이 좁은 조건의 추가 이득 예측은 미지지다. H_reuse_vs_primitive는 두 재사용군을 각자 primitive와 대조한다. expansion 감소와 수치 tick/group/link 감소는 별도다. 단회 시간 차이로 통계 속도 우위를 채택하지 않는다. 수치 kernel 압축이 없다는 기존 설명과 모순되지 않는다.

검산 실패·source 변동·역할/분기 누락·숨은 참조 접근·시간/자원 상한 초과는 기술 실패이며 음성 결과로 바꾸지 않는다. 품질 열화·절감 부재는 연구 결과로 보존한다. 입력·threshold·회수·순서를 결과 후 바꾸거나 확인 batch를 추가하지 않는다.

## 실행과 총비용

학습3회 뒤 평가4×3=12회. 평가 순서는 case-major이며 군 순서를 case index마다 한 칸 회전한다. 초기화1, 학습3, 평가12, 준비1, 검산1의 18단계다. 한 session 최대8advance·2560ticks, 보수적 전체 최대240settles·38400ticks, 실제 수를 따로 센다. AI Research SSH 전체600초/단계60초/worker1/retry0, AS512MiB·parentfile32MiB/child16MiB·raw128MiB 단계 종료 soft 합계 검사다. World.measure는0회이며 금지 함수로 차단한다. 로컬은 구조 검사와 수신 원자료 재생만 하고 native 추론/학습을 실행하지 않는다.

총비용 주 경계는 부모가 측정한 각 process의 CPU/wall이다. init·모듈 import·입력/memory 구성·source 검사·pool/macro 준비·실제 탐색/수치 계산/증명·trace/JSON/디스크 쓰기를 포함한다. 학습 단계에는 실제 외부 참조 채점과 피드백·컴파일·기억 저장도 포함된다. reference와 learning 부분 시간은 별도로 기록하되 부모 단계 시간에 다시 더하지 않는다. 직접 session 시간은 Config/memory 구성 및 최종 파일 쓰기를 제외하는 부분집합이며 총비용이라고 부르지 않는다.

공통 실제 학습을1회만 수행하고 두 학습군에 같은 관측 비용을 각각 부과하는 paired 회계다. 두 군을 독립적으로 재학습한 복제는 아니다. primitive는 init만 부과한다. 실제 사용 prefix K=1..4까지만 init+training+각 evaluation 단계 비용과 단위별 native 학습/피드백/평가 비용을 합산한다. 아직 수행하지 않은 미래 수명·상각·손익분기점을 외삽하지 않는다. 준비/audit/봉인/호스트 orchestration 비용은 별도 보고한다. 시간은 단회 기술 관측이며 전력·독립 반복·production 채택은 없다.

hash chain, 독립 matching DFS/grammar/graph expansion helper, 별도 scalar/controller 재생, reference proof 검증, native operation accounting, 독립 dict 학습 전이와 표적 변조로 saved event를 확인한다. 검산은 production runtime/activation/expansion/learning을 호출하지 않는다. 구조 loader와 기존 평가 helper는 공유하며 내부 일관성 검사이지 외부 실행의 독립 인증은 아니다.
