# EXP-76 / R30 A-1 결과

원본·공유판의 고정32쌍은 매 tick 전체 state·순서·residual·stable_steps와 종료 판정·readout가 타입/float bit까지 동일했다. R29에서 기회가 있던12쌍은 실제 group/normalization/link 계산도 줄였다. 다만 query마다 계획 생성·검증을 포함한 cold CPU 합계는 공유판이 원본의 1.1821배였다. **계산 생략과 관측 동치에는 성공했지만 이번 workload의 총비용 개선은 관측되지 않았다.** 통계적 속도 우위·학습 효율·production 채택은 판정하지 않는다.

## 대조와 수용 결과

R29와 같은4Program×8drive/initial 조건에서 원본·공유판을 각1회, 총64settles·2240ticks 실행했다. 각 arm의 tick은1120회다. query별 새 process, query index 짝수/홀수에서 arm 순서를 번갈아 실행했다. 계획을 다른 query로 재사용하지 않았고 입력·조건·반복·비용 경계를 사후 조정하지 않았다. 이는 동일 입력 쌍의32개 개발 조건 대조이며 독립 정확도 표본이나 시간 반복32회가 아니다.

| 기준 | 결과 |
|---|---|
| full tick state·key 순서·residual·stable | 32/32 bit 동일 |
| 종료 status/ticks/residual/margin/stable·최종 state·readout | 32/32 bit 동일 |
| 별도 scalar/controller 재생 | server 최대오차0, local 5.5511151231257827e-17 ≤1e-14 |
| 실제 계산 감소 | 12/32쌍, R29의 공유 기회와 일치 |
| 입력·trace·순서·비용·복원·timing·readout·partition·누락 변조 | 9종 모두 거부 |
| 학습·World.measure | 0회 |
| 실제 통계적 속도·학습 효율·production 채택 | 미판정·미채택 |

품질 보존은 현재 원본의 관측 보존을 뜻한다. 이 결과로 원본의 외부 정답률이나 미래 입력의 정확성을 보장하지 않는다. 원본 settle의 residual/history/stable/종료 controller는 수정하지 않았으며 source SHA와 동일 전체 trace·복원 순서로 결속했다. shared tick은 대표 행의 원래 link 순서를 유지하고 매 tick 모든 node를 복원한다. 중복 link와 경계 feedback을 제거하거나 weight를 합치지 않는다.

## 실제 계산량과 cold 비용

| Program | 쌍 | group 원본→공유 | link 원본→공유 | cold CPU 원본 / 공유(ms) |
|---|---:|---:|---:|---:|
| chain2 | 8 | 1510→1510 | 2416→2416 | 14.020 / 16.838 |
| lower | 8 | 576→488 | 768→680 | 8.266 / 10.526 |
| shared_bypass | 8 | 5565→4221 | 11872→8960 | 36.255 / 41.350 |
| upper | 8 | 1275→1141 | 3060→2792 | 13.615 / 16.582 |

총 group update와 normalization은 각각8926→7360회(17.54% 감소), link 계산은18116→14848회(18.04% 감소했다. 이는 실행 loop에서 계수한 실제 연산량이다. R29의 가상 한 tick 투영량과 다르다. tick 수는 같고, full-state 출력 slot은 양 arm 각각8926개이며 shared alias copy는1566개다. 이 장부는 CPU 명령 수·물리 에너지·메모리 트래픽 측정이 아니다.

동일 drive의4조건에서 shared_bypass/lower/upper에 기회가 있었고, chain2 전8조건 및 세 Program의 비대칭4조건에서는 계산 감소가 없었다. 1ULP drive 차이와 initial 차이도 그대로 음성으로 남겼다. 공유 불가 query의 분할/검증 비용도 제외하지 않았다.

cold CPU 합계는 원본 72.154940ms, 공유 85.294964ms로 공유판이 18.21% 더 컸다. wall 합계는 각각 72.159785ms / 85.291008ms(1.1820배)였다. 공유판의 계획 생성·별도 검증·index 구성 CPU 합계는 16.694094ms이며 cold 내부에 포함됐다. 이를 공짜로 빼거나 미래 수명에 임의 분산한 수치는 보고하지 않는다.

cold 경계에는 arm 진입 뒤 deepcopy·Program/Config·검증·source SHA·binding, 공유 준비, settle·복원·trace/readout/result 구성·payload JSON 직렬화1회가 포함된다. 최종 pair 파일 재직렬화/디스크 쓰기·import·공통 전체 source 검사·pair/scalar 검산은 pair stage에 포함되고 cold에는 없다. pair-stage CPU 합계 5.048884초는 양 arm과 검산의 합이므로 arm별 전체 process 비용으로 나누지 않았다. 모든 stage 자식 CPU 합계는 5.828411초다.

shared_bypass weak_equal 한 query에서는 cold CPU가 더 작게 관측됐지만, 단회 짧은 시간값과 사후 query 선택으로 속도 개선을 주장하지 않는다. 전체 합계도 시간 불확실성에 대한 반복 실험을 거치지 않은 기술 관측이다. 미리 고정한 statistical_speed_verdict는 null을 유지한다.

## 실행·근거 검증

AI Research SSH의 같은 owner 승인 요청7ced7280… 하나로 실행했다. 자동 심사가 high_risk로 자동 승인을 허용하지 않은 뒤 소유자 승인을 받았으며 상세 위험 사유는 반환되지 않았다. 대체 요청·재시도·새 실험은0이다. Linux Python3.12.3에서34stage 모두 exit0, 봉인 포함 6.607468초(상한600초), 최대 stage wall 0.667963초(상한60초)였다. worker1/retry0, AS512MiB·parentfile32MiB/child16MiB 및 raw peak 1140836bytes를 확인했다.

실행 전/서버 준비 단계에서 R29의11개 구조 대조와 실제 Program/Config/native source 결속3개 대조가 통과했다. 로컬에서는 native tick/settle을 실행하지 않았고, 받은 원자료만 별도 scalar/controller/cost로 재생했다. source223개의 로컬 SHA와 서버 source-postcheck는 unchanged였고 수신36개 결과 JSON은 같은 채널 manifest의 SHA-256과 일치했다. server scalar tolerance와 local tolerance는1e-14이며, 직접 arm 비교의 bit 일치 기준은 완화하지 않았다.

전송은 redacted-adapter-outcome이고 upstream SSH 완전성은 unknown이다. 서버 보고 evidence ZIP(199981bytes) 자체·68개 stdout/stderr·원격 source 전체 bytes는 수신하지 않았다. 수신 JSON과 동일채널 manifest의 일치를 확인한 것이며 독립 호스트 attestation은 아니다. transport-receipt.json·local-replay.json·cost-analysis.json을 보존했다.

작성자의 source/result CS 검토3의무와 bundle check(49개 raw 결속)는 PASS다. 이는 독립 구현 감사나 테스트 실행의 자동 증명이 아니다. 새 방향 토론을 반복하지 않고 R29 HIGH 판정의 A-1 후보를 별도 계약으로 실행했다. core와 이전 연구는 수정하지 않았다.

## 후속 판단

A-1을 고정 조건의 관측 동치·실제 연산 생략 양성, cold 총비용 미개선 관측으로 닫는다. 이번 연구용 runtime을 production이나 learner에 적용하지 않는다. query당 생성·검증이 필요한 현재 경로에서 준비 비용을 생략하는 사후 변경은 하지 않았다.

다음 과제는 실제 learner 산출물에서 공유 구조가 존재하는지, 같은 구조가 실제 query 수명에서 유지되는지부터 계약으로 정해야 한다. 존재하지 않는 반복 수명이나 준비 비용 상각을 가정해 이번 음성 비용 결과를 구제하지 않는다. 이 연결 없는 성과는 compiler/runtime 연구의 좁은 결과이며 H03의 학습 효율 검증으로 세지 않는다.
