# EXP-69 / r23: 측정 전 출처 적격 확인

2026-10-19 KST. 실행 전 고정. 기준 main `1f5540f1ed6244d30ef6fdc379dcfbec4ff5bcbc`.

r22는 두 측정의 일치와 선언된 계보 분리가 동시 오답을 막지 못하고, 올바른 단일 응답도 보류함을 보였다. 이번에는 그 채택 기준을 다시 조정하지 않는다. **평가와 분리된, 알려진 feature의 사전 검증 이력으로 측정 전에 출처를 선택하는 효과와 비용**을 확인한다. 기존 EXP-00의 명확한 world 기능 점검이나 r22의 응답 간 합의와 구별되는 출처 선택 실험이다.

## 고정 규칙과 정보 경계

두 출처에 각각 8개 calibration 패널을 World.measure로 요청한다. 알려진 feature 부호와 측정 부호가 모두 일치하고 각 절대 score가 기존 상수0.8 이상이며 기존 응답 계약도 만족한 패널만 통과다. **8/8 통과, 실패0**인 출처를 적격으로 하고, 고정된 출처 목록에서 첫 적격 출처 하나를 고른다. 하나도 없으면 측정을 요청하지 않고 초기 결과를 유지한다. 표본 수·상수·출처 순서 탐색은 없다.

calibration의 primary는 6/8, witness는 8/8이 되도록 고정한 합성 개발 fixture다. 이 숫자는 실행 전 입력으로 알 수 있는 조건이며 새 측정 결과가 아니다. ±0.98은 관측 score이지 정확도98%가 아니다. 8/8은 유한 검증 이력이고 확률 calibration·통계적 신뢰구간·미래 오류 상한을 뜻하지 않는다. source ID는 인증되지 않은 선언이다.

calibration과 evaluation의 episode ID는 겹치지 않는다. calibration의 알려진 feature label은 별도 인증 생성 단계에서만 사용한다. 평가 정책이 받는 것은 public 관측·예산·초기 추론과 출처별 examples/passed/failures/qualified 및 고정 규칙·calibration hash다. 평가 reference/fault는 제공자와 audit만 읽으며 정책에 전달하지 않는다. 해시가 출처의 인증이나 독립성을 증명하지 않는다. 두 집합은 같은 합성 World.measure 장치를 공유하므로 독립한 실제 환경 표본이 아니다.

## 비교

평가10입력×4방식40조건을 한 번 순차 실행한다.

- `no_query`: 초기 r20 gated만 실행한다.
- `single_contract`: 초기 primary가 stable_ambiguous이면 기존 primary 한 번을 요청한다.
- `corroborated`: 같은 조건에서 기존 primary/witness 두 번을 요청하고 r22의 합의·선언 계보·강도 조건을 적용한다.
- `qualified_single`: 같은 조건에서 calibration 적격 출처 하나를 요청한다. 이후 채택·재추론은 single_contract와 **같은 단일 응답 계약**이다. 추가적인 런타임 강도 조건이나 다수결은 넣지 않는다.

세 요청 정책의 초기 추론과 요청 조건, 비용 예약은 같다. 각 요청당 합성 feature2단위를 부과하고, 두 출처 정책은 요청2/feature4를 호출 전에 예약한다. 추가 settle4회도 사전 예약하고 실제 사용분과 해제를 기록한다. invalid/불일치 측정도 비용을 지불한다. 초기 추론을 모든 정책에 부과하며 수정은 fresh state의 r20 gated 한 번이다. native ADAPT·학습·회로 메모리 수정은 없다.

| 평가 ID | 숨은 분류 / 공개 context | 제공자 조건 | 검사 목적 |
|---|---|---|---|
| eval_00 | A / −1 | 둘 다 정상 | 정상 A |
| eval_01 | B / +1 | 둘 다 정상 | 정상 B |
| eval_02 | A / +1 | primary만 반전 | 과거 실패 출처 회피 |
| eval_03 | B / −1 | 적격 witness만 반전 | 적격 이력 이후 오류 |
| eval_04 | A / −1 | 둘 다 반전 | 공통 오류 |
| eval_05 | B / +1 | witness stale revision | 적격 이력과 응답 계약 구분 |
| eval_06 | A / −1 | witness 약한 score0.2 | calibration 때 없던 관측 강도 |
| eval_07 | B / −1 | primary만 반전, 요청1/feature2 | 단일/이중 요청 예산 차이 |
| eval_08 | A / +1 | 초기 [1,0.8], 둘 다 정상 | 요청 없는 정상 통제 |
| eval_09 | B / +1 | 초기 [1,0.8], 둘 다 정상 | 안정된 초기 오답의 요청 누락 |

나머지 초기 score는 [0,0], aux는 모두 없다. 표의 fault 이름·reference는 정책 분기가 아니다. 입력들은 실패 경로를 확인하려고 고른 합성 반례 집합이며 모집단 정확도·출처의 자연 발생 오류율을 추정하지 않는다. calibration 이후 오류를 포함했으므로 정상성 가정의 한계가 결과에 남아야 한다.

## 판정과 전체 비용

분류/관계의 정답·오답·보류, 입력별 전이, 초기/추가 settle·tick·group·signal·normalization, 측정 요청/feature 단위, CPU/wall·raw 크기를 따로 보고한다. 분류와 관계는 독립 표본 두 개가 아니다. 적격 방식에서만 사전 검증16요청/feature32/알려진 feature label16개 취득을 평가 묶음 전체에 한 번 귀속한다. 다른 정책에는 이 검증이 필요하지 않으므로0으로 귀속한다. 물리 실행에서는 calibration 한 묶음을 공통 생성하며 실제 실행 횟수를 중복 합산하지 않는다. 알려진 label 취득의 금전·현실 비용은 측정하지 못하므로0원으로 가정하지 않는다.

개별 품질 보존의 최소 판별 조건은 기존 single_contract가 정답인 입력에서 qualified_single이 새 오답을 만들지 않는 것이다. 새 오답 하나라도 나오면 이 조건은 실패다. 보류를 정답으로 세지 않는다. 이 조건을 통과해도 일반 안전성·완전한 품질 동등성을 인정하지 않는다. 전체 수와 측정 비용도 함께 비교한다. 이는 실험의 보수적인 승격 필터이며 사용자의 실제 업무상 허용 오류율을 대신 정한 것이 아니다.

검증 비용을 빼고 비용 절감을 주장하지 않는다. 서로 다른 tick/feature/label/시간을 임의 환율로 더하지 않는다. 가상의 반복 묶음에 대한 나눗셈은 새 관측이나 품질을 맞춘 손익분기가 아니다. 이번에는 반복 묶음·학습·실제 센서 지연을 실행하지 않는다.

## 실행·검산·감사 추적

AI Research SSH의 새 전용 폴더에서 worker1, retry0, 전체600초·stage60초, 주소공간512MiB, 부모 파일32MiB·자식16MiB, stage 종료 raw 합계128MiB soft 검사를 적용한다. 최대 측정64·native settle240·학습0으로 제한한다. calibration도 이 측정 총량에 포함한다. 네 정책의 최대 요청 합계는 입력당4이므로 calibration16을 더해도56이다. aux가 없는 고정 관측에서는 초기/수정 추론이 각각 최대2 settle이고, 요청 후 최대30개 수정으로 구조적 상한140이다. 최종 audit에서 전역 카운터를 검사하며 실행 도중 누적 카운터 interrupt를 구현한 것은 아니다.

기존 r22의 제한 실행·실패 기록·봉인 runner를 재사용하고 새 child entry와 spec만 연결한다. bootstrap 영수증의 상한은 이번 spec에서 읽는다. 초기 폴더/한도 설정 전 실패, SIGKILL·디스크 정지의 봉인을 보장하지 않는다. raw 합계는 hard 디스크 quota가 아니고 parent 한도 때문에 봉인 자체가 실패할 수도 있다. 실제 한도는 parent와 preparation child의 getrlimit으로 확인한다. 모든 child의 개별 RSS를 측정하는 것은 아니다.

실행 전 pure preparation은 새 native tick/settle/World.measure를 금지하고 stub40조건, calibration 공식·선택 거부·과거 저장 trace 재생을 점검한다. 실제 calibration16회는 pure 준비 뒤 실행한다. 서버 audit는 calibration 응답·인증·비용을 공식으로 대조하고 실제40행을 기존 별도 scalar 수식으로 재생한다. request gate/revision/charge/response/adoption와 세 cell cap, 상위 trace/program 변조10종은 정확한 거부 사유까지 확인한다. 전역 cap 거부는 함수 직접 시험이며 OS 실패 주입으로 확대 해석하지 않는다.

ZIP/source manifest/spec/design hash를 전송 전에 고정한다. 소유자 승인이 필요한 경우 정확한 요청 ID와 사용자 답변, 이후 도구가 반환하는 상태/필드를 기록한다. 도구가 approvedAt/actor를 주지 않으면 null/미제공으로 남기고 finishedAt을 승인 시각으로 대체하지 않는다. 최초 연구·push 지시의 원문과 범위 해석도 분리 기록한다. 사전 감사가 없었다면 뒤의 감사를 PRE 승인으로 부르지 않는다.

실행 후 원자료 JSON과 source 전후 SHA를 확인한다. 전체 ZIP 준비와 로컬 실제 수신, stdout/stderr 수신 여부를 각각 구별한다. 실행하지 않은 재검사·독립 감사·실제 센서 성능을 완료로 보고하지 않는다. 결과를 보고 코드·입력·기준을 바꾸거나 같은 실험을 다시 실행하지 않는다.
