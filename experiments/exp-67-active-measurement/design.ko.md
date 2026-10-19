# EXP-67 / r21: 추가 측정의 요청 조건과 비용 상한

## 질문과 현재 구현 경계

r20의 조건부 피드백은 오답을 줄였지만, 출처 조건을 통과한 잘못된 aux와 안정적으로 결정된 잘못된 primary 입력은 truth를 판별할 새 정보가 없다. 이번에는 **추가 측정을 언제 요청할지, 비용 상한 안에서 정답·오답·보류가 어떻게 달라지는지**를 작은 합성 실험으로 확인한다.

기존 `AdaptiveEngine.request_revision`은 외부 오답 피드백을 요구한다(runtime.py:372 이후). 이번 오류 확인 전 요청에 쓰면 정답 피드백이 정책 입력에 들어간다. 엔진은 수정하지 않고 기존 `ObservationRequest` DTO와 `World.measure`를 task wrapper에서 사용한다. native revision controller, 학습된 수정 기억이나 자율 관측 학습을 구현했다고 주장하지 않는다.

분류/관계 계산은 main `6fc4a89`의 r20 gated 전체 실행을 그대로 재사용한다. 모든 방식이 **초기 r20 추론을 전부 지불한 뒤** 측정 여부를 결정한다. 피드백 전에 계산을 선별한 결과로 해석하지 않는다. 새 primary 응답을 받아도 r20 프로그램·커널·gain·.5 초기 state는 동일하다.

## 세 방식과 공개 예산

- `no_query`: 현재 r20 gated 결과를 유지한다.
- `after_abstention`: 초기 최종 분류가 보류일 때만 측정을 요청한다.
- `primary_uncertainty`: 초기 하위 primary 수렴이 `stable_ambiguous`이면 측정을 요청한다. aux 피드백 뒤 분류가 채택됐어도 요청할 수 있다. 안정적으로 틀린 primary 입력은 이 조건에서 놓칠 수 있다.

정책은 관측·예산·초기 추론 기록만 읽는다. case key·hidden category reference·provider fault mode나 아직 받지 않은 응답으로 요청을 선택하지 않는다. public observation은 r20의 id/revision/measurement/context/aux이며 예산은 별도 공개 필드다.

고정 공개 quote는 요청1회당 f0/f1 두 feature, `feature_units=2`, 재추론 settle 최대4회다. 공개 예산에서 요청1회·feature2단위·재추론4회를 모두 예약할 수 있어야 호출한다. 재추론 예산3인 경우 실제로2회에 끝날 가능성이 있어도 응답을 미리 보지 않고 거부한다. 이 예산은 **추가 비용만** 제한한다. 초기 추론까지 포함한 전체 native 비용도 별도로 합산한다.

요청은 fingerprint로 초기 판단에 결속하고 동일 episode의 다음 revision·f0/f1을 지정한다. 소스·요청 hash·episode·revision·대상·topology·score 계약을 검사한다. 유효 응답은 primary 두 score와 revision만 갱신하며 기존 context/aux는 그대로 둔다. aux revision을 새 관측처럼 고쳐 쓰지 않는다.

응답이 유효하면 r20 gated를 한 번 새로 실행한다. 오래된/부적합 응답은 재추론 없이 분류/관계를 보류한다. 요청이 거부되면 초기 결과를 유지한다. 시도한 요청은 잘못되거나 정보가 없어도2 feature 단위를 부과한다. 예약4회 중 실제 재추론 사용분만 계산 비용으로 세고 나머지는 해제한다. 어떤 응답에도 두 번째 요청은 없다.

## 합성 측정 제공자와 10개 조건

provider는 요청을 받은 뒤에만 별도 fixture의 hidden feature 두 값을 읽고 native `World.measure`를 한 번 호출한다. 이 API는 요청한 feature마다 ±0.98 score를 반환한다. goal/category label을 반환하지 않는다. s→m→t Observation은 f0/f1 측정 역할의 컨테이너이며 분류 과제의 route proof가 아니다.

정책은 provider fixture 파일을 읽지 않는다. 평가 reference와 hidden feature/fault fixture는 분리한다. 모든 데이터는 합성이며 ±0.98은 실제 정확도98%를 뜻하지 않는다. 이상적인 측정이 유용하다는 가정의 효과를 시험하며 실제 센서의 독립성·신뢰도는 검증하지 않는다. 그 한계를 드러내기 위해 stale/no-information/flip 응답도 사전에 고정한다.

| key | 초기 공개 입력·예산 | provider 응답 조건 | reference category |
|---|---|---|---|
| clear_A | 강한 A feature, +context, aux 없음 | 유효 A feature | A |
| aux_pair_A | 0/0, −context, fresh aux−1 | 유효 A feature | A |
| aux_pair_B | aux_pair_A와 id 외 공개 정보 동일 | 유효 B feature | B |
| missing_aux_A | 0/0, −context, aux 없음 | 유효 A feature | A |
| feature_budget_A | 0/0, −context, fresh aux−1, feature 예산1 | 유효 A feature | A |
| compute_budget_A | 0/0, −context, aux 없음, 재추론 예산3 | 유효 A feature | A |
| stale_reply_A | 0/0, −context, aux 없음 | 측정 후 reply revision을 이전 값으로 바꿈 | A |
| no_information_A | 0/0, −context, aux 없음 | 새 revision에 기존 score0/0을 반환 | A |
| flipped_reply_A | 0/0, −context, aux 없음 | 측정 score 부호를 반대로 바꿈 | A |
| strong_primary_wrong_B | 강한 A feature, +context, aux 없음 | 요청하면 유효 B feature | B |

명시하지 않은 예산은 요청1·feature2·추가 settle4다. relation reference는 category와 context가 일치하는지다. aux_pair의 초기 예측이 같아야 하지만, 서로 다른 feature 응답을 실제로 요청한 후에는 달라질 수 있다. id만 바꿔 정답을 맞히도록 요구하지 않는다.

`measurement_changed`는 score 벡터가 달라졌는지이며 정보량/정확도의 추정치가 아니다. no-information의 revision 증가만을 성공으로 세지 않는다. flipped 응답은 계약 형식은 맞아도 오답을 만들 수 있다. 강한 primary 오답과 예산 때문에 못 고친 결과도 보존한다.

## 측정·검산·완료 기준

10×3=30개 cell을 각각 한 번만 실행한다. 준비1→case30→audit1의32단계, native settle 최대200회, World.measure 최대20회, 학습0, seed/threshold 탐색0, 결과 기반 재실행0이다. 추가 측정이 무조건 품질을 보존하거나 비용을 줄인다는 가설을 완료 조건으로 강제하지 않는다.

분류/관계 정답·오답·보류, 요청/거부 사유·실제 응답·검증 실패·score 변경을 보고한다. 초기/재추론/전체 settle·tick·group update·signal/normalization, 요청 수·합성 feature 단위·예약/사용/해제, provider wall, cell child CPU/wall과 출력 bytes를 분리한다. feature 단위와 tick을 임의 환율로 합치지 않으며 금전/에너지 우위나 통계적 속도 차이를 주장하지 않는다. 전체 child CPU에는 import·graph·정책/hash·fixture I/O·측정·재계산·직렬화가 포함된다.

기존 별도 scalar 수식으로 초기/재추론의 모든 tick을 재생한다. 서버 절대오차0, 별도 호스트 보조 재생 절대오차1e-15·상대오차0을 PRE 고정한다(r20에서 이미 사용한 경계). discrete 판정·Program·drive·provenance는 정확히 비교한다. 허용치가 형식적인 모든 반올림 오차 상한을 증명하는 것은 아니다.

provider 응답은 fixture의 feature별 ±0.98 및 fault 공식을 감사자가 따로 대조하며 감사 중 World.measure를 다시 호출하지 않는다. request gate·request revision·charge·response score 변조와, 초기 **상위** tick/program 변조6종은 각각 고정한 거부 사유와 일치해야 한다. 상위 변조는 하위 gate hash가 먼저 가리는 경로를 피한다. source 전후 hash·전체 비용·요청/예약 상한도 검사한다.

로컬/서버 preparation은 예산/응답 검증, synthetic stub orchestration, 저장 r20 trace 재생이다. 새 커널 추론·World.measure 호출이 없으며 stub 결과를 실험 관측으로 세지 않는다. 실제 새 관측은 서버 case 단계에서만 얻는다. 학습0·fresh state 재계산이므로 수정 기억 유지·native AdaptiveSession adoption·일반화·학습 효율·자율 계층 형성의 증거가 아니다.

## 자원·보존

AI Research SSH 전용 `/home/mcpops/hcc-active-measurement-20261019-r21`에서 전체600초·순차1·stage60초·child 주소공간512MiB·child 개별 파일16MiB·raw stage 종료 후128MiB 검사를 적용한다. 입력 spec과 runtime이 같은 상한을 사용한다. raw 합계 검사는 디스크 hard quota가 아니다.

부모 SIGTERM은 예외로 받아 child를 정리하고 실패 자료와 봉인을 남기도록 준비한다. 이는 best effort이며 SIGKILL·저장 장치 정지 등 모든 실패에서의 봉인 보장은 아니다. 외부 timeout은600초와 kill-after5초다. 정상/실패 모두 source 후검사를 시도하고 서버 내부 hostname/IP는 결과에 기록하지 않는다. src·이전 하네스·봉인은 수정하지 않는다.

원자료·manifest·검산·source 전후 검사·봉인 ZIP SHA와 수신 범위를 보존한다. 포털 마스킹 등으로 byte 일치가 확인되지 않은 자료는 검증된 raw와 구분한다. 실패 또는 불리한 결과를 숨기거나 같은 조건을 자동 반복하지 않는다.
