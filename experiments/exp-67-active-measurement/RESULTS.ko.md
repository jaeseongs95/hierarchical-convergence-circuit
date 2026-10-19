# EXP-67 / r21 결과: 추가 측정의 요청 조건과 전체 비용

2026-10-19 KST. AI Research SSH에서 고정한 합성 입력10개×3정책, 총30조건을 한 번 실행했다. **초기 primary가 불확실할 때 측정하면 정답은2→4개로 늘었지만 오답3개는 남았고, 전체 tick은474→702로 늘었다.** 최종 보류 때만 측정한 정책은 정답3·오답4·보류3개였다. 추가 측정의 효용과 비용을 확인했으며, 품질 보존이나 계산 절감은 입증하지 못했다.

## 실행과 검증

준비1·case30·audit1의32단계가 모두 exit0으로 끝났다. 봉인 포함4.088238006초로 전체600초 상한 안이었다. 실제 native settle77회·World.measure10회·tick1,766개를 기록했으며 사전 상한200회/20회 이내다. 학습0·자동 재시도0·결과 기반 정책/입력 변경0이다. 초기 추론은 모든 정책이 전부 지불하고, 요청이 수락된 경우에만 추가 측정과 재추론 비용을 더했다.

서버 준비146개 assertion은 새 native 실행이나 측정 없이 통과했다. 실제30개 기록의 초기·재추론 tick은 별도 scalar 수식으로 재생했고 사전 서버 절대오차0에서 통과했다. 요청 조건·요청 revision·측정 과금·응답 score·초기 상위 tick·상위 program bias 변조6종은 각각 고정한 `request gate binding`·`request binding`·`measurement charge ledger`·`provider response binding`·`scalar replay tick mismatch`·`fixed program` 사유로 거부됐다. 상위 tick/program 변조를 사용해 하위 trace hash가 더 깊은 검사를 먼저 가리는 문제를 피했다.

로컬 보조 재생도30조건 전체를 통과했다. 사전 고정한 절대오차1e-15·상대오차0에서 최대 차이는0이었다. 새 native tick/settle과 World.measure를 금지한 상태에서 원자료·정답/오답/보류·요청/과금/예약·전체 비용·summary를 대조하고, 변조6종의 정확한 거부 사유를 다시 확인했다. 이는 저장 기록 검산이며 독립 실험 반복이나 추가 성능 표본은 아니다.

## 품질과 요청 범위

| 정책: 각10조건 | 분류 정답 | 오답 | 보류 | 관계 정답 | 오답 | 보류 | 요청 수 |
|---|---:|---:|---:|---:|---:|---:|---:|
| no_query | 2 | 3 | 5 | 2 | 3 | 5 | 0 |
| after_abstention | 3 | 4 | 3 | 3 | 4 | 3 | 4 |
| primary_uncertainty | 4 | 3 | 3 | 4 | 3 | 3 | 6 |

이 집합은 실패 경로를 포함하도록 설계한10개 합성 조건이다. 모집단 정확도나 일반화 성능을 추정하지 않는다. 분류와 관계 판정 수가 같은 것은 이 고정 과제의 결과이며 두 개의 독립 표본으로 세지 않는다.

| 조건 | no_query / after_abstention / primary_uncertainty 분류 | 관측된 행동 |
|---|---|---|
| clear_A | A / A / A: 모두 정답 | 이미 안정된 primary이므로 요청 없음 |
| aux_pair_A | B / B / A: 마지막만 정답 | 최종 보류 조건은 aux가 만든 오답을 놓쳤고 초기 불확실성 조건은 유효 측정으로 교정 |
| aux_pair_B | B / B / B: 모두 정답 | 초기 불확실성 조건은 이미 맞은 결과에도 추가 비용 지불 |
| missing_aux_A | 보류 / A / A | 두 요청 정책 모두 유효 측정 후 정답 채택 |
| feature_budget_A | B / B / B: 모두 오답 | 초기 불확실성 조건은 feature 예산1로 제공자 호출 전에 거부; 다른 정책은 요청 조건 불충족 |
| compute_budget_A | 모두 보류 | 요청 정책은 재추론 예약4회에 예산3으로 호출 전에 거부 |
| stale_reply_A | 모두 보류 | 요청 정책은 측정1회·2단위를 지불하고 revision 오류로 거부; 재추론0 |
| no_information_A | 모두 보류 | 요청 정책은 새 revision에도 score0/0이 같음을 기록; 측정1회·재추론1회/4tick을 지불했지만 정보·정답 증가 없음 |
| flipped_reply_A | 보류 / B / B: 뒤 두 정책 오답 | 형식상 유효한 반전 응답을 채택해 새 오답 생성 |
| strong_primary_wrong_B | A / A / A: 모두 오답 | 안정된 primary 오답을 두 요청 조건 모두 놓침 |

aux_pair_A/B는 id 외 공개 정보가 같고 초기 판단은 모두B였다. primary_uncertainty만 실제로 받은 서로 다른 feature 응답을 사용해 각각A/B로 바뀌었다. 정책에는 hidden category reference나 provider fault mode를 넘기지 않았다. 이 구별은 새로운 관측 정보의 효과이며 기존 출처 필드나 자신감이 truth를 보증한 결과가 아니다.

primary_uncertainty는 aux_pair_A의 오답1개를 고쳤지만 flipped_reply_A에서 보류를 새 오답으로 바꿔 전체 오답 수는3개로 같았다. after_abstention은 그 교정을 놓치면서 반전 응답의 오답을 받아4개가 됐다. 오답 수가 같거나 보류가 줄었다는 집계만으로 개별 입력의 품질 보존을 주장할 수 없다.

## 초기 추론·측정·재계산 비용

모든 정책의 초기10조건 합계는 동일하게 settle21·tick474·group update1,986·signal4,152다. 아래 전체 비용은 이 초기 비용을 포함한다.

| 정책 | 요청/feature 단위 | 재추론 settle / tick | 전체 settle / tick | 전체 group update | 전체 signal | case child CPU초 | case wall초 |
|---|---:|---:|---:|---:|---:|---:|---:|
| no_query | 0 / 0 | 0 / 0 | 21 / 474 | 1,986 | 4,152 | 1.082787 | 1.207314 |
| after_abstention | 4 / 8 | 5 / 116 | 26 / 590 | 2,454 | 5,096 | 1.061290 | 1.157118 |
| primary_uncertainty | 6 / 12 | 9 / 228 | 30 / 702 | 2,910 | 6,024 | 1.071291 | 1.156874 |

after_abstention의 전체 tick은 기준선보다24.5%, primary_uncertainty는48.1% 늘었다. 뒤 두 정책의 합성 feature 비용은8/12단위이며 이 단위와 tick을 임의 환율로 합치지 않는다. normalization 연산 수는 각 정책에서 group update 수와 같다. 원자료 JSON bytes 합계는157,262 / 194,476 / 228,264다.

추가 settle 예약은 after_abstention16회 중5회 사용·11회 해제, primary_uncertainty24회 중9회 사용·15회 해제였다. stale/no-information/반전 응답도 요청과 feature 비용을 부과했다. 예산3인 경우 실제 재추론이2회로 끝날 수 있어도 결과를 미리 보지 않고 예약4회가 불가능하므로 거부했다. 비용 상한을 지키는 것과 예산 배분이 최적인 것은 별개다.

provider wall 합계는 after_abstention0.000772758초, primary_uncertainty0.001173028초였다. 이는 합성 fixture I/O와 World.measure 호출·변환을 포함한 짧은 코드 경로이며 실제 센서 대기시간이 아니다. case child CPU/wall은 import·graph·정책/hash·fixture I/O·측정·재계산·직렬화를 포함한다. 준비·서버 검산을 포함한 전체 child CPU는3.529815초다. 표의 작은 CPU/wall 차이는 단일 실행과 대기 간격의 영향을 받으므로 연산량 증가에도 실행 속도가 개선됐다고 해석하지 않는다. 금전·에너지·학습 포함 손익분기는 판정하지 않았다.

## 구현 경계와 보존

src와 r19/r20 구현은 바꾸지 않았다. 기존 r20 gated 추론을 그대로 호출하고 기존 ObservationRequest DTO·World.measure만 새 task wrapper에서 사용했다. native AdaptiveEngine.request_revision은 외부 오답 피드백을 요구하므로 이번 오류 확인 전 정책에서는 사용하지 않았다. 새 primary 응답을 받으면 revision과 두 score만 바꾸고 기존 aux revision을 새것으로 고쳐 쓰지 않았다. 각 추론은 새 .5 state에서 시작하며 학습된 수정 기억은 없다.

제공자는 요청 후에만 별도 fixture의 hidden feature 값을 읽고 ±0.98 score를 반환한다. 이 수치는 실제 정확도98%를 뜻하지 않는다. 고정된 합성 측정의 효과를 시험했으며 센서 독립성·물리적 신뢰도·source 인증·학습 효율·수정 기억 유지·일반화·자율 계층 학습을 입증하지 않았다.

`evidence/active-measurement-20261019-r21/raw/`의 case30개와 preparation/result/summary/source-postcheck4개, **총34개 JSON의 SHA256이 서버 raw manifest와 모두 일치**한다. 원격 source manifest도 전송 전 동결 digest와 일치하며78개 source의 현재 로컬 bytes 및 원격 전후 일치 보고를 대조했다. 이번 수신 원자료와 source manifest/postcheck에는 포털 마스킹이 없었다.

전체 evidence.zip은 서버에서 준비됐지만 agent/기기에 전달된 것은 아니다. 따라서 ZIP 내부를 로컬에서 직접 byte 대조했다고 주장하지 않는다. 서버 준비 완료와 실제 로컬 수신을 구분해 transport receipt에 보존했다. raw manifest는 텍스트로 수신했고 위34개 원문 JSON은 그 digest와 대조했다. completion은 raw 봉인 후 생성된 별도 영수증이다.

상한은 전체600초·stage60초·순차1·child 주소공간512MiB·child 개별 파일16MiB·raw stage 종료 후128MiB 검사였다. raw 합계 검사는 디스크 hard quota가 아니며 부모 SIGTERM 정리·실패 봉인은 best effort다. 이번 정상 종료의 봉인만 확인했다.

## 다음 연구 판단

다음은 **요청 범위와 응답 채택의 신뢰 조건을 분리하는 것**이 우선이다. 초기 불확실성만 보면 안정된 오답을 놓치고, source/revision/형식 검사만으로는 반전 측정의 truth를 검증할 수 없다. 같은 관측을 반복해서 confidence만 높이는 방향은 피한다.

후속 설계에서는 추가 공개 근거가 무엇인지 먼저 정하고, 그 근거가 없는 조건에서는 채택을 보류할 수 있어야 한다. source별 신뢰도를 쓰려면 그것을 추정하는 별도 calibration 근거·분리된 평가 입력·calibration 비용까지 고정해야 한다. 현재10개 결과에 맞춰 threshold를 조정하거나 hidden fault 정답을 정책에 넣지 않는다. 이 보고서는 그 후속 실행을 포함하지 않는다.

## 재현 핀

- 실행 source ZIP:248,396bytes, SHA256 `12a8fa8a5fc5e506cae9a2c21cd1b6f5f5368cabb93e9290092f39b5d293c68d`.
- source manifest SHA256: `f5c48cae4481237c9d11df58b76b250296d08f9f37786896157ed91111f5b98b`.
- summary SHA256: `d19b8491259b3e95959fa8e7d4220c5de7d187be67e6f05d3c718b53c460dce6`.
- 서버 evidence.zip:176,024bytes, SHA256 `e60261e0b22f582a725c9ea28d928e4545ee491ddccf94c7860866d94907e19c`.
- 소유자 승인 실행 요청 `b1f27e40…` 1회, 다운로드 준비 요청 `b5282cdf…` 서버 준비 완료·로컬 ZIP 수신 미확인.
- 저장 자료 재생: `python -B tools/r21_active_measurement/replay_saved.py --evidence evidence/active-measurement-20261019-r21 --out <존재하지 않는 새 receipt.json 경로>`.
- replay_saved.py는 실행 후 추가한 보조 검산 도구다. 동결 ZIP에 포함되지 않았으며, 실행된 probe/정책/입력은 결과를 보고 바꾸지 않았다.
