# R0.2.1 작성 환경의 실행 검증

기준: `main@2e67f71804b172673212822291b15885ca64f729`. 소스·시험·도구 등 10개 디렉터리의 Git tree와 수정 대상 루트 파일을 원격 기준과 대조했다.
실험 결과는 기존 EXP-09와 별도의 synthetic 개발 검증이다. 로컬 Windows의 실행 결과는 아직 받지 않았다.

| 검사 | 실제 결과 |
|---|---|
| 기존 136개 + 신규 79개 core 시험 | 215 실행, 212 통과, 3 skip, 실패·오류 0 |
| skip 사유 | Linux에 PowerShell native parser 없음. 기존 R01/R02, 신규 R021 실행기 검사 |
| baseline/복구 보조 도구 | 90/90 통과 |
| 개념 보조 도구 | 39/39 통과 |
| 개념 registry | 24개 개념, 55개 근거, 20개 파일 검사 |
| 변경 전/후 실제 engine 별도 프로세스 | 12개 설정 × 합계 78개 판단과 5,870개 event payload, memory·proof·카운터 일치 |
| 위 differential의 seed | 버전별 18개 학습 실행. 비교 판단과 별도 |
| standalone EXP-10 | 비교 추론 30회 + seed 6회, complete/verified/equivalent=true |
| snapshot | 52개 파일 검산. 모든 resumed 전이 후 실제 save/load |
| CLI | start 프로세스 종료 뒤 별도 resume 프로세스로 남은 계산 완료·검산 |

위 코드 실행은 Linux / Python 3.13.5에서 수행했다. Python 3.12 구문 호환성은 AST 검사로 따로 확인하며 Windows 실행을 대신하지 않는다.
추가로 배포 ZIP 해시·safe apply·idempotency·conflict 거부·git apply --check와 release manifest 검사 결과는 배포 `VALIDATION.json`에 기록한다.

## 실제 보존된 것

정답뿐 아니라 weak conflict와 retention의 오답, length3 약화 후 length2 재사용, same-score revision의 39 ticks,
unknown의 보류, budget 소진, 요청 비활성화, 기존 pool/판단 카운터가 유지된다.
동등성 비교는 wall_seconds와 그 값에서 파생된 event hash chain만 제외한다. 각 chain의 무결성은 별도로 검사한다.

## 검산 경계

session audit는 생산 infer를 다시 실행하지 않는다. 기존 독립 audit helper와 자료계약·외부 proof validator를 공유한다.
프로세스 간 snapshot 이동과 형식/계보/상태 조작을 검사했으나 임의 지점 crash recovery나 글로벌 exactly-once 시스템은 아니다.
checkpoint 직렬화·검산 시간을 추론 tick에 합산하지 않는다. transaction deepcopy의 세부 소요시간은 미계측이다.
복구·증거 캡처 전체를 새로운 연구 표본으로 세지 않는다. 성능·prior 정책의 개선은 이번 버전의 주장이 아니다.

기계 판독 기록: `evidence/implementation/r021_status.json`.
