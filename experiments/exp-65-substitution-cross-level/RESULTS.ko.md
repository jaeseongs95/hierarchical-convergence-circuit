# EXP-65 / r19 결과: 문맥 피드백의 이득·오류 전파와 비용

2026-10-19 KST. AI Research SSH에서 준비 검사와 18개 조건을 한 번 실행했다. 외부 경계 state를 생략하는 정확 대체 후보는 반례로 기각됐다. 최소 cross-A에서는 피드백이 모호한 입력을 문맥 방향으로 결정했으며, 잘못된 문맥도 그대로 오답으로 전파했다. 다음 연구는 **불확실성과 독립 근거를 반영한 승격·피드백 허용 조건**으로 좁힌다.

## 실행 상태와 검산 복구

원격 run은 `FAILED_AT_AUDIT`다. 준비 1단계와 case 18단계는 exit 0, audit 1단계는 exit 1이었다. 봉인까지 2.879830284초로 600초 상한 안에서 끝났고, PID 12939는 이후 `/proc`에 없었다. 실패를 성공한 원격 run으로 바꾸거나 실험을 재실행하지 않았다.

audit가 JSON 배열과 `dataclasses.asdict(Program)`의 튜플을 직접 비교해 같은 프로그램을 `adapter program changed`로 오판했다. 실제 저장 기록으로 수정 전 실패를 재현한 뒤 기존 `hcr.codec.plain`으로 비교 대상을 정규화했다. 입력·graph·gain·커널·18개 출력은 바꾸지 않았다. 원래 실행한 probe는 `executed-probe.py.txt`로 보존했다.

저장된 18개 case와 preparation/failure JSON의 해시 20개, audit stderr 해시 1개를 원격 raw manifest와 대조했다. 별도 수식 재생은 36개 settle의 **988개 tick**을 검사했고, native tick/settle 호출을 금지한 상태에서 통과했다. 원래 감사의 revision·값·state 변조와 stale packet 4종, 추가 program bias 변조도 거부했다.

로컬 Windows 재생은 두 coupled 조건의 작은 상태값에서 최대 절대차 `1.6940658945086007e-21`을 보였다. 로컬 재생 허용치는 사후에 명시한 `1e-15`이며 기본 서버 검산 허용치는 0이다. 실수 state·residual·margin만 이 오차로 비교한다. 수렴 상태·tick 수·stable_steps·판정·Program·drive·승격 provenance·비용은 정확히 대조한다. 따라서 원래 계획한 동일 호스트의 완전 일치 감사가 완료됐다고 주장하지 않는다.

원격 source 71개는 실행 전 해시 검사를 통과했다. 실행 후 전체 source 검사는 audit 중단 때문에 수행되지 않았다. 원격 source manifest를 회수해 동결 manifest와 일치함을 확인했으나, 이것을 source 71개 각각의 실행 후 재해시로 대신하지 않는다. 현재 저장소 probe는 감사 수정본이며 실행 ZIP과 동일한 파일이 아니다.

## 정확 대체 후보

공식 길이 2 pattern에서 국소 state와 drive를 같게 두고 외부 goal state만 바꿨다.

| 외부 goal state | 다음 내부 `p:0:1` state |
|---|---:|
| 0.1 | 0.2796591818889913 |
| 0.9 | 0.28898081787185037 |

경계 state를 키에서 빼면 서로 다른 전이를 구별하지 못한다. 이 **경계 생략형 국소 1 tick 정확 대체**만 기각된다. 실제 r18 궤적에서의 도달성, 최종 출력만 보존하는 근사, 전체 state cache, 모든 회로 축약의 불가능성은 판정하지 않았다. 실제 계산 절감을 달성한 결과도 아니다.

r18 gate의 순환 반례는 재현됐고 r19 사본은 이를 거부했다. 77,400개 작은 graph 대조가 통과했다. 과거 r18 source·결과는 그대로이며 cross-A는 이 gate를 사용하지 않는다.

## cross-A 관측

하위는 두 feature의 A/B 분류, 상위는 category confidence와 context의 XNOR 관계 판정이다. 별도 Program에서 같은 tick/settle을 썼다. `coupled`는 상위 신호를 고정 1회 보내 하위·상위를 재계산한다. 학습은 0회다. 표의 각 셀은 `분류 / 관계 일치 여부 / tick`이다. `보류`는 하위 판정 없음이다.

| 조건 | reference 분류/관계 | bottom_up | coupled | 수작업 별도 알고리즘 |
|---|---|---|---|---|
| clear_A_match | A / 일치 | A / 일치 / 56 | A / 일치 / 111 | A / 일치 / 0 |
| clear_B_match | B / 일치 | B / 일치 / 56 | B / 일치 / 111 | B / 일치 / 0 |
| ambiguous_A | A / 일치 | 보류 / 일치 / 48 | A / 일치 / 114 | A / 일치 / 0 |
| ambiguous_B | B / 일치 | 보류 / 일치 / 48 | B / 일치 / 114 | B / 일치 / 0 |
| misleading_A | A / 불일치 | 보류 / 일치 / 48 | B / 일치 / 114 | B / 일치 / 0 |
| strong_conflict | A / 불일치 | A / 불일치 / 56 | A / 불일치 / 112 | A / 불일치 / 0 |

분류는 bottom_up 정답 3·오답 0·보류 3, coupled 정답 5·오답 1·보류 0이었다. 관계는 세 방식 모두 정답 5·오답 1이다. 이는 선정한 6개 reference에 대한 기술 관측이며 일반 정확도 추정이 아니다.

`ambiguous_B`와 `misleading_A`는 ID를 제외한 공개 measurement/context가 같고 hidden truth만 다르다. 둘을 모두 맞히는 기준을 요구할 수 없다. 현재 시스템은 모호한 입력을 문맥 방향으로 결정할 수 있지만, 그 결정이 참인지 구별할 추가 정보는 없다. 하위가 보류했는데도 상위가 관계를 채택한 현상도 남았다. 수렴·자기 일관성을 독립된 truth 검증으로 해석해서는 안 된다.

## 비용

| 방식: 6개 case 합계 | settle 호출 | tick | group update | signal transmission | case child CPU초 |
|---|---:|---:|---:|---:|---:|
| bottom_up | 12 | 312 | 1,380 | 3,024 | 0.542587 |
| coupled | 24 | 676 | 2,832 | 5,920 | 0.543224 |
| 수작업 별도 알고리즘 | 0 | 0 | 0 | 0 | 0.519687 |

피드백으로 tick은 2.17배, group update는 2.05배가 됐다. 명확한 세 조건에서는 판정 개선 없이 재계산 비용이 늘었다. 별도 알고리즘의 0은 **커널 카운터 0**이며 실제 연산 비용 0이 아니다. 각 case의 import·graph 구성·직렬화가 CPU에 포함되어 작은 커널 차이가 단일 CPU 관측에 드러나지 않는다. 준비와 실패한 감사를 포함한 전체 child CPU는 2.257027초이고, 로컬 재생 wall은 별도로 0.0875004초다. 다른 호스트의 시간을 하나의 속도 비교로 합치지 않는다.

승격 bytes·전체 JSON bytes는 `summary.replayed.json`, 부분 adapter 변환 수와 수작업 기준선 연산 수는 raw case에 있다. 이 선언된 수는 모든 Python 연산을 센 값이 아니다. 학습·메모리 적응은 없으므로 학습 포함 총비용 절감, 손익분기, 에너지·통계적 속도 우위를 주장하지 않는다.

## 다음 비중복 과제

**독립 근거가 없는 문맥 피드백이 보류를 오답으로 바꾸지 않도록 하는 승격·피드백 계약**을 먼저 설계한다. 현재 wrapper 수준의 한계 검증이며 자율 계층 학습을 도입하지 않는다.

1. 하위 채택 여부·불확실성, 문맥의 출처·revision·독립 근거 유무를 공개 입력으로 명시한다. 같은 근거에서 나온 상·하위 신호를 새 증거로 중복 계산하지 않는다.
2. 하위가 안정적으로 결정됐고 상위와도 일치하면 피드백을 생략한다. 모호할 때는 사전 검증된 독립 근거가 있는 경우만 1회 허용하고, 없으면 보류한다. 숨은 reference로 분기하거나 문맥의 정오를 사후 주입하지 않는다.
3. 같은 공개 입력의 paired world는 둘 다 보류할 수 있음을 허용한다. 그 뒤 새 독립 측정이 실제로 추가되는 별도 revision 사례로만 수정 가능성을 검사한다. 단순 stale packet 거부를 실제 수정 유지 실험으로 세지 않는다.
4. baseline·무조건 피드백·조건부 피드백을 작은 고정 사례에서 비교한다. 오답 채택·보류·정답 전환과 gate/adapter 포함 전체 계산을 함께 센다. 오답을 숨기고 coverage 증가만 성과로 세지 않는다.

새 protocol·수용 기준은 실행 전에 동결해야 한다. 이번 작업에서는 후속 서버 실험을 추가 실행하지 않았다. 공통 kernel의 두 수작업 기능 연결을 보였을 뿐 H01/H02 일반화, native AdaptiveSession adoption, 경로 proof, 학습 효율, 자율 계층 형성·장기 수정 유지의 증거는 아니다.

## 재현과 원자료

- evidence: `evidence/substitution-cross-level-20261019-r19/`의 `raw/`, `summary.replayed.json`, `replay-receipt.json`, `executed-probe.py.txt`, `source-manifest.actual.json`, `completion.actual.json`.
- raw 폴더를 새 작업 폴더에 복사한 후 `python -B tools/r19_cross_level/replay_saved.py --raw <복사한 폴더>`로 저장 기록만 검사한다. 이미 생성된 summary/receipt가 있는 폴더를 재사용하지 않는다. 실제 tick/settle 호출은 금지된다.
- 동결 ZIP SHA256: `756e4ece8a31c9aa833779cb1331c71a58eda158b8ae1e67d3859133d7b264d5`.
- 실행 probe SHA256: `79809e6a6e0a39dc88a829d03586b3b3d159e0f1942fd26dd6b7b8fad23f68c1`.
- 원격 raw ZIP: `/home/mcpops/hcc-cross-level-20261019-r19/evidence.zip`, 86,032 bytes, SHA256 `adb4ff3383513b063839ef93b1aead621869a0d2209c8bd0782e11895feec9ff`.
- 다운로드 요청 `34cf79c2…`은 서버 파일 준비 완료 상태다. ZIP 자체의 로컬 수신은 확인하지 않았다. 별도로 18개 전체 case JSON·preparation·failure·manifest·audit stderr를 읽어 로컬 보존했다. 전체 ZIP의 나머지 빈 stdout/stderr까지 로컬에 받았다고 주장하지 않는다.
- 실행 요청 `1135a52b…`은 소유자 승인 후 시작됐다. 과거 `ac46959a…`는 unknown이었고 실행 폴더 부재를 확인한 뒤 사용자의 재개 지시로 새 요청을 제출했다. 실제 기술 실행은 한 번이다.
