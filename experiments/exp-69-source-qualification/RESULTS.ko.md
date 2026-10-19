# EXP-69 / r23 결과: 과거 검증 이력과 현재 측정의 신뢰는 다르다

2026-10-19 KST. AI Research SSH에서 출처별 calibration8회×2출처를 먼저 측정하고, 분리한 평가10입력×4정책40조건을 한 번 실행했다. **검증 이력으로 출처를 선택하면 기존 단일 출처보다 오답은4→3개로 줄었지만, 기존 정답 입력에서 새 오답1개와 보류1개가 생겼다.** 정답 합계는6개로 같고 개별 품질 보존 조건은 실패했다. 사전 검증을 포함한 측정 요청은8→24회로 늘었다. 이 방식을 품질 보존·전체 비용 절감 정책으로 승격하지 않는다.

## 실행과 검증

준비1·평가40·audit1의42단계가 모두 exit0으로 종료했다. 봉인 포함7.280286686초, 실제 native settle84회·tick1,587개·World.measure46회다. 측정46회는 calibration16회와 평가30회이며 전체600초·settle240회·측정64회 상한 안이다. 학습0·threshold/출처 순서 탐색0·자동 재실행0이다. 결과를 본 뒤 실험 코드·입력·기준을 바꾸지 않았다.

서버의 pure 준비 검사162개는 새 native settle·World.measure 없이 통과했다. stub40조건과 calibration 공식·선택 거부·저장된 과거 trace를 확인한 뒤 실제 calibration16측정을 수행했다. 서버는 실제40행의 초기/수정 추론을 기존 별도 scalar 수식으로 절대오차0에서 재생했다. 로컬 저장 자료 재생은 사전 허용 절대오차1e-15·상대오차0에 대해 최대 차이8.673617379884035e-19로 통과했다. 로컬 재생 중 새 native tick/settle/World.measure와 실행 함수를 금지했으며, 이 재생을 새 실험이나 성능 표본으로 세지 않는다.

request gate/revision/charge/response/adoption, request/unit/revision cap, 상위 tick/program bias의 변조10종은 각각 정한 거부 사유까지 서버와 로컬에서 일치했다. calibration 응답·인증·비용도 별도 예상 응답 공식과 대조했고 전체 summary를 다시 집계했다. calibration 변조4종 및 위조 인증·누락/중복·전역 cap 거부는 pure 준비 검사다. 실제 OS 자원 초과·SIGTERM 실패를 주입한 실측은 아니다.

## 출처 선택과 품질

calibration은 알려진 feature 부호와 응답 부호가 맞고 절대 score0.8 이상이며 계약도 유효한 패널을 통과로 센다. primary는6/8, witness는8/8이었다. 고정된8/8·실패0 규칙에 따라 qualified_single은 요청하기 전에 witness를 선택했다. 평가 label이나 fault 이름은 정책에 전달하지 않았다. 평가와 calibration의 episode ID는 겹치지 않는다.

| 정책 | 분류 정답 / 오답 / 보류 | 관계 정답 / 오답 / 보류 |
|---|---:|---:|
| no_query | 1 / 1 / 8 | 1 / 1 / 8 |
| single_contract | 6 / 4 / 0 | 6 / 4 / 0 |
| corroborated | 3 / 2 / 5 | 3 / 2 / 5 |
| qualified_single | 6 / 3 / 1 | 6 / 3 / 1 |

qualified_single은 출처 선택만 바꾸고 응답 후에는 single_contract와 같은 단일 응답 계약을 적용한다. 두 정책의 요청 조건·초기 추론·예산 예약도 같다. corroborated는 기존 r22의 두 응답 합의·강도·선언 계보 검사를 적용한다.

| 입력 | single_contract → qualified_single | 확인한 효과 |
|---|---|---|
| eval_00, eval_01 | 정답 → 정답 | 정상 A/B |
| eval_02 | 오답 → 정답 | primary 반전 회피 |
| eval_03 | 정답 → 오답 | 과거8/8 witness가 이후 반전; 개별 품질 보존 실패 |
| eval_04 | 오답 → 오답 | 두 출처 공통 오류는 calibration 이력으로 막지 못함 |
| eval_05 | 정답 → 보류 | 선택된 witness의 stale revision을 계약 검사에서 거부 |
| eval_06 | 정답 → 정답 | witness score0.2도 단일 계약으로 채택; 교차 확인은 강도 부족으로 보류 |
| eval_07 | 오답 → 정답 | 요청1회 예산으로 적격 출처 한 번 사용; 이중 정책은 요청 전 예산 거부 |
| eval_08 | 정답 → 정답 | 요청 없는 정상 초기 결과 |
| eval_09 | 오답 → 오답 | 안정된 초기 오답은 모든 정책의 요청 조건에서 누락 |

합계 정답6개가 같아도 eval_02/07에서 정답2개를 얻고 eval_03/05에서 기존 정답2개를 잃었다. 새 오답이 없는 것을 요구한 사전 최소 필터는 eval_03 때문에 실패했다. 보류로 바뀐 eval_05도 품질 보존으로 세지 않는다. 교차 확인보다 정답은3→6개지만 오답도2→3개이므로 그 비교에서도 품질 동등성을 주장하지 않는다.

corroborated와 qualified_single이 모두 실제 측정한 입력은 eval_00~06이다. eval_07의 차이는 이중 요청 예산 거부 효과가 추가된 조건이다. 위 구분은 입력별 결과 해석이며 새 실험이나 사후 정책 선택이 아니다.

이번 calibration은 사전에 설계한 출처 오류를 가진 작은 합성 fixture다. 8/8 통과는 미래 정확도·오류 상한·확률 calibration이 아니다. source ID와 root는 선언이며 출처 인증이나 통계적/물리적 독립성을 입증하지 않는다. 평가에는 calibration 이후 오류·약한 관측·revision 오류를 의도적으로 포함했다. 따라서 현재 결과는 유한 개발 반례 확인이며 자연 발생 오류율이나 모집단 일반화 추정이 아니다. ±0.98은 측정 score이지 정확도98%가 아니며 분류/관계의 같은 수를 독립 표본 두 개로 세지 않는다.

## 사전 검증을 포함한 비용

초기10입력 비용은 모든 정책에서 settle12회·tick144개·group552·signal1,056으로 같다. 아래 전체 추론은 이 초기 비용을 포함한다.

| 정책 | 평가 요청 / feature | calibration 요청 / feature 귀속 | 합계 요청 / feature | 수정 settle / tick | 전체 settle / tick | 전체 group / signal |
|---|---:|---:|---:|---:|---:|---:|
| no_query | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 12 / 144 | 552 / 1,056 |
| single_contract | 8 / 16 | 0 / 0 | 8 / 16 | 16 / 448 | 28 / 592 | 2,376 / 4,768 |
| corroborated | 14 / 28 | 0 / 0 | 14 / 28 | 6 / 168 | 18 / 312 | 1,236 / 2,448 |
| qualified_single | 8 / 16 | 16 / 32 | 24 / 48 | 14 / 395 | 26 / 539 | 2,157 / 4,316 |

calibration은 실제 실행에서 한 묶음만 수행했고 qualified_single의 평가10입력 전체에 한 번 귀속했다. 다른 방식에는 필요하지 않아0으로 귀속했다. 실제 측정46회를 방식별 귀속 비용에서 중복 합산하지 않았다. calibration에는 알려진 feature label16개도 사용했다. 그 현실의 취득 비용·금액은 측정하지 못했으며0원으로 가정하지 않는다. 학습0이므로 학습 포함 손익분기는 평가하지 않았다.

qualified_single은 단일 출처보다 tick이592→539(약9.0% 감소)였지만, stale 응답을 보류해 재추론을 생략한 효과를 포함한다. 개별 품질을 보존하지 못했으므로 같은 품질에서 계산을 절약한 결과가 아니다. 평가 측정8회는 같아도 사전 검증을 포함하면24회로3배다. 이중 측정 방식의14회보다도 많다. 이번 작은 실험에서는 사전 검증 비용을 회수하지 못했다. 서로 다른 tick·feature·label·시간을 임의 환율로 더하거나 금액·에너지 우위를 주장하지 않는다.

| 정책 | case child CPU초 | case wall초 | provider wall초 | case JSON bytes |
|---|---:|---:|---:|---:|
| no_query | 1.201215 | 1.666051 | 0 | 64,398 |
| single_contract | 1.218987 | 1.666332 | 0.001665186 | 201,472 |
| corroborated | 1.212054 | 1.666353 | 0.002697266 | 124,391 |
| qualified_single | 1.217149 | 1.666874 | 0.001658132 | 186,235 |

calibration 측정/적격 확인의 wall은0.003617418초, 준비 process 전체는 CPU0.165246초·wall0.216332471초였다. case CPU/wall에는 import·graph 구성·calibration 파일의 공식 대조·policy/hash·provider I/O·재추론·기록을 포함한다. 세 비교 정책의 case도 기술적인 증거 결속을 위해 calibration 공식을 대조했으며 그 작은 확인 overhead를 차감하지 않았다. provider 시간은 합성 World.measure 장치의 시간이고 실제 센서 대기시간이 아니다. 전체 child CPU5.216502초에는 준비와 audit도 포함한다. 짧은 단일 실행과 process 대기 간격의 영향을 받으므로 미세한 시간 차이를 속도 개선으로 해석하지 않는다. normalization 수는 각 group update 수와 같다.

## 무결성·승인 추적과 한계

case40개와 calibration/preparation/result/summary/source-postcheck5개, **총45개 원자료 JSON의 SHA256이 서버 manifest와 모두 일치**한다. source manifest의 원본 bytes도 전송 전 SHA와 일치하며87개 source의 현재 로컬 bytes·원격 전후 일치 보고를 대조했다. 마스킹된 필드는 관측하지 않았다. 서버 manifest의 stdout/stderr84개는 수신/커밋하지 않았다. 전체 evidence.zip은 서버 준비 완료일 뿐 agent/기기의 로컬 수신과 ZIP 내부 bytes 대조는 확인하지 않았다. 수신 자료의 범위를 transport-receipt와 local-replay에 명시했다.

기존 요청08a40825를 소유자 승인 후 한 번 실행했다. 사용자 답변과 questionItemId, 도구의 approvalMode owner·completed·createdAt·finishedAt을 기록했다. approvedAt/actor는 도구가 제공하지 않아 null로 남겼다. finishedAt은 bootstrap 실행 명령의 완료 시각이며 승인 시각이나 전체 실험 완료 시각으로 쓰지 않았다. 별도 독립 감사는 실행하지 않았고 사후 검사를 PRE 승인으로 부르지 않는다.

부모의 실제 AS soft/hard512MiB·파일32MiB, 준비 child의 실제 AS512MiB·파일16MiB를 확인했다. 동일 runner 경로로 각 child에 한도를 적용하지만 모든 child의 개별 getrlimit/RSS를 측정한 것은 아니다. stage raw 최대632,753bytes였다. raw128MiB는 stage 종료 soft 합계 검사이며 hard disk quota가 아니다. 전역 요청/settle 검사는 최종 audit이고 실시간 누적 interrupt가 아니다. 고정된 행렬/분기 구조로 상한을 제한했다. 초기 설정 실패나 SIGKILL·디스크 정지·봉인 자체의 한도 실패를 포괄적으로 보증하지 않는다.

source ZIP 전송 영수증의 SHA와 실행 전 hash guard가 일치했다. 별도 sha256sum 읽기 요청은 포털에서 INVALID_ARGUMENT로 거부돼 해당 명령 실행이나 원격 출력 확인을 주장하지 않는다. 이를 이유로 실험을 재요청하지 않았다. bootstrap의 이번 상한 영수증은 spec에서 읽는다. replay_saved.py는 실행 뒤 추가한 보조 검산 도구이며 동결 ZIP에 없다. src·tests·r19~r22 하네스와 과거 입력/증거는 변경하지 않았다.

## 연구 판단

측정 전 출처 선택은 구현 가능했고, 알려진 과거 오류 출처를 피하는 제한된 효과가 있었다. 그러나 **검증 이력만으로 현재 출처를 믿고 채택할 조건은 얻지 못했다.** 적격 출처가 바뀌거나 두 출처가 함께 틀릴 때는 과거 이력으로 막지 못했고 검증 비용도 컸다.

다음에는 이 이력을 보장으로 승격하기보다, 최근의 검증 가능한 오류 증거가 들어왔을 때 적격 상태를 언제 중단할지와 그 확인 비용을 분리할 수 있다. 그 후속은 이번에 실행하지 않았다. 안정된 초기 오답의 요청 누락, 실제 label 획득·센서 인증·정상성·일반화·학습/기억 유지·자율 계층 형성은 여전히 미입증이다.

## 재현 핀

- source ZIP:262,320bytes, SHA256 `5ab90bb696c8d9b0a999c7250e8f390caa775ab1515e75b87adb601f23af55fd`.
- source manifest SHA256: `d9ca0dc403091c2482c37911bbf896c197413e2bb25115376592eba689494627`.
- summary SHA256: `5e85ac38b42b4549fbab20346bb345c67af6163e44ca945c2d258a774c4a6b01`.
- 서버 evidence.zip:188,040bytes, SHA256 `65ae0853150c7e2381b0bacc1a7784e00b2e22ec0b19dcbb5e007ba54d8d47cc`.
- 실행 요청 `08a40825…`, 다운로드 준비 요청 `8dddf9e0…`(서버 준비 완료·로컬 ZIP 미수신).
- 저장 자료 재생: `python -B tools/r23_source_qualification/replay_saved.py --evidence evidence/source-qualification-20261019-r23 --out <존재하지 않는 새 receipt.json 경로>`.
