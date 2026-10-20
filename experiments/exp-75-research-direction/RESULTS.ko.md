# EXP-75 결과: 공간 공유 기회 확인, runtime 검증은 다음 단계

## 1. Executive Verdict

전체 연구 방향의 HIGH 토론과 AI Research SSH의 R29 A-0 분석을 완료했다. 현재 학습 회로의 효율 우위 주장은 보류하고, 실제 원계산을 대체하는지부터 확인하는 방향을 선택했다. 고정32조건 중12조건에서 보수적 ordered-row 규칙으로 공유 가능한 class가 있었다. 이는 A-1 계약 심사로 넘어갈 기회 조건을 충족한 것이며, 실제 연산 절감·수치 실행 동치·속도·학습 효율의 양성 결과가 아니다.

## 2. Consensus Proposal

전체 가설별 방향과 대안은 ROADMAP.ko.md에 보존했다. 이번 A-0은 완료한다. 다음 후보는 원래32조건에서 원본과 대표 갱신·복원 runtime을 최대64settles로 대조하는 A-1이며 별도 프로토콜이 필요하다. 양성이므로 이번에 native 실행을 자동 추가하지 않았다. 기존 kernel·learner·pool과 이전 연구는 수정하지 않는다.

## 3. Strong Consensus

동일 drive의 네 조건(+4/-4/+0/+0.4)에서 shared_bypass, lower, upper의 공유 기회를 확인했다. chain2는 모든8조건에서0이었다. 나머지 세 Program도 한 input의 drive 크기·부호·1ULP 또는 초기 state를 바꾼 네 비대칭 조건에서는 모두0이었다. 이 비대칭 결과를 대칭 결과의 안전한 범위 경계로 보존한다. 결과 후 입력을 바꾸거나 실행을 추가하지 않았다.

## 4. Material Disagreements

A의 정적 기회 분석을 우선하는 조건부 합의는 있었으나 통상적 실행계획 대조(B), H07 자기이득 검사(C), matched-task 공통 primitive 대조(D)와의 실제 성능 우열에는 합의가 없다. A-0의 양성 결과가 이 대안들의 우열을 해결하지 않는다. 현재 학습기는 고정 path motif를 만들고 최종 primitive 판단을 유지하므로 학습 구조 재사용을 산술 대체와 구별한다.

## 5. Decision by Axis

| 축 | 판정 |
|---|---|
| 고정32query의 충분조건·최대 class | 별도 pair-elimination 검산 PASS |
| 공유 기회 | 12/32query 양성; 조건별 class32개 합계(반복 조건을 합산한 수) |
| 실제 native 실행 동치·품질 | 미실행·미검증 |
| 실제 연산·속도 절감 | 미측정 |
| 학습 포함 총비용·일반화 | 미검증 |
| 다음 단계 | 별도 A-1 계약 심사 허용, production 채택 없음 |

## 6. Evidence

아래 group/link 전후 수는 **동일 drive 한 조건의 가상 한 tick**에서 원본과 대표 행만 계산할 때의 투영량이다. 실제 runtime을 실행한 수치가 아니다. 비대칭 네 조건에서는 원본과 대표 수가 같다.

| Program | query | 기회 query | group 원본→대표 | link 원본→대표 행 |
|---|---:|---:|---:|---:|
| chain2 | 8 | 0 | 5→5 | 8→8 |
| shared_bypass | 8 | 4 | 15→9 | 32→19 |
| lower | 8 | 4 | 3→2 | 4→3 |
| upper | 8 | 4 | 5→4 | 12→10 |

shared_bypass의 양성 각 조건에는6개의2node class가 있다: e:1/e:3, e:2/e:4와 p:0:i/p:1:i(i=0..3). lower는 f0/f1, upper는 promoted/context다. 전체32query 각각 가상 한 tick을 합산하면 생략 group/normalization32회·link64회다. alias 복원32slot과 원래 full-state 출력 slot은 별도 ledger에 남겼다. 이 합계를 실제 추론비용 절감률로 바꾸지 않는다.

분할 생성기는 bias·drive·initial binary64 bit와 level/goal 역할에서 시작해 원래 순서의 incoming source class/weight/kind로 반복 분할한다. 별도 검산기는 같은 local label의 모든 pair에서 불일치 pair를 제거하며 closure·그 규칙 안의 maximality·coverage·대표 순서·투영 ledger를 검증한다. 중복 link와 feedback을 유지한다. 동기 갱신의 귀납 근거와 한계는 proof.ko.md에 있다. 존재하지 않는 runtime의 실측 동치 증거로 표현하지 않는다.

Linux Python3.12.3에서6stage 모두 exit0, 봉인 포함 1.179188초(상한600초), 최대 stage 0.166681초(상한60초), 자식 CPU 합계 0.838791초였다. 이는 정적 연구 실행 비용이며 native benchmark가 아니다. worker1/retry0, AS512MiB·parentfile32MiB/child16MiB와 raw peak55863bytes를 확인했다. native tick/settle·학습·World.measure·신규 timing benchmark는0회다.

서버 준비 검사는 합성 대칭/비대칭·순서·중복 link·signed zero를 확인했고, 잘못된 binding/공유/분할 누락/순서/ledger 등의11개 대조를 거부했다. 별도 서버 audit와 로컬 저장 결과 audit는 binding·coverage·ledger·missing-query·scope 변조5종을 거부했다. 받은8개 결과 JSON은 같은 채널 manifest의 SHA-256과 일치했고, 고정 source191개는 로컬 SHA와 서버 source-postcheck에서 unchanged였다.

전송은 redacted-adapter-outcome이며 SSH upstream 완전성은 unknown이다. 서버 보고 evidence ZIP(11218bytes) 자체와12개 stdout/stderr 파일 및 원격 source 전체 bytes는 수신하지 않았다. 수신 JSON과 동일채널 manifest의 일치를 확인한 것이며 독립 호스트 attestation은 아니다. 상세 원장은 evidence/research-direction-20261020-r29/transport-receipt.json과 cost-analysis.json이다.

## 7. Required Actions

A-0 결과와 음성 조건을 보존한다. 작성자의 source/result CS 검토3의무와 bundle check(21개 raw 결속)는 PASS이며 독립 구현 감사는 아니다. 최종 변경 범위·staged byte 고정을 확인한 뒤 사용자 지시대로 서명커밋·main 병합·동일 private remote push한다. 다음 A-1은 fullstate·residual·history·종료 controller·readout bit 대조와 복원/생성/검증 비용 경계를 계약에 명시해야 한다.

## 8. Optional Optimizations

새 scheduler·cache·학습 규칙·입력 확대·추가 timing·서버 증설은 수행하지 않았다.

## 9. Unresolved

공유 class는 특정 drive/initial에 결속된다. 미래 query·실제 수명에서도 유지되는지, 대표 갱신·복원 runtime이 모든 관측을 보존하는지, 검증·분할 생성 비용까지 회수하는지 미검증이다. 학습 산출물과 연결하지 않은 양성은 compiler 기회 확인에 한정한다. 입력은 의도한 구조 진단32조건이며 정확도·일반화 독립 표본이 아니다. 이 보수적 규칙 밖의 의미적 동치를 모두 탐색했다고 주장하지 않는다.

## 10. Method / Run Summary

HIGH4blind관점(구조·타당성·자원·전략), 비원저자 교차검토4건, 별도 fresh Judge1명을 완료했다. specialist/reserve/adaptive 추가는0이며 requested gpt-6.1-sol/xhigh, 실제 provider 내부는 NOT_OBSERVABLE이다. 방향 토론의 independent 절차는 구현 감사나 플랫폼 격리의 증명이 아니다. 구현·실행 결과 검토는 Coordinator가 수행했다. 실행 요청 e56574fa…는 자동 심사가 high_risk로 분류해 보류했으며 사용자가 포털에서 승인한 같은1개 요청으로 완료했다. 상세 위험 사유는 반환되지 않았다. 재시도·대체 요청·사후 조건 변경은0이다.
