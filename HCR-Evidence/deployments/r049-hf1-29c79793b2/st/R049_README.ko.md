# R049 / EXP-30 실행 안내

## 원클릭

`HCR_R049_EXP30_OneClick.cmd` **하나를 현재 저장소 최상위 폴더에 놓고 실행**한다.

```text
D:\codex\진짜미친짓\hierarchical-convergence-circuit\
```

현재 R048 실행을 완료한 checkout이 기준이다. ZIP을 별도로 풀거나 이전 패치를 다시 적용할 필요는 없다. 필수 환경은 기존 Python 3.12 이상, Git, Windows PowerShell이다. 모델·패키지·Python을 자동 설치하지 않는다.

기준 commit은 `426ad699235935a97b74b1dcd1acbcd4890313b2`이다. 이후 commit도 해당 commit을 포함하고 상속 소스가 같으면 허용하지만, 사용한 실제 HEAD와 source hashes를 기록한다. 원격 pull/fetch를 자동 하지 않는다.

## 무엇을 실행하는가

관측 강도 0.02·0.10·0.92, 두 edge 관계 (++/ +−), 두 ID 배치, top_down ON/OFF × 중립/높은 초기값의 48조건이다. 높은 초기값은 edge·prefix=0.99, goal=0.5이고 모든 world에 동일하다. 실제 상태 carry나 새 학습이 아니다.

신호 분해는 실행 후 모든 tick/group에서 생성한다. raw 오판, 내부 edge와 관측의 충돌, proof를 못 만든 경우, 만든 proof가 지지되지 않는 경우, 채택 거부와 예산 종료를 따로 보고한다. 가설 실패를 건너뛰거나 성공으로 바꾸지 않는다.

## 자동 실행 순서

```text
내장 ZIP checksum 확인
→ additive 설치 및 설치본 내용 확인
→ 최신 확인 기준 commit ancestry/native/R048 manifest 확인
→ 부모 EXP-29 원본 사본의 bytes·전체 verifier 확인
→ 실제 실행 source snapshot 동결
→ 기존 R047/R048 self-test + 새 R049 self-test
→ Git clean-filter/ignore 검사
→ plan 동결
→ 실제 native 48조건 실행 및 append-only raw 기록
→ 독립 scalar/proof/event audit·신호 분해
→ 분석 재집계 및 verify
→ 봉인·독립 재검증·Git bytes 확인·ZIP 생성 및 bytes 재확인
```

기존 native 8파일, R047/R048 소스·manifest, 원자료와 실패 폴더는 수정하지 않는다. 설치 중 같은 이름의 다른 R049 파일이 발견되면 덮어쓰지 않고 멈춘다. 원본과 동일한 R049 파일은 그대로 두므로 사용자가 다시 실행하면 새 run으로 기록된다. 자동 retry는 없다.

## 결과 위치

`HCR-Evidence/exp30/r049-YYMMDD-<8자리 ID>/`

| 파일/폴더 | 역할 |
|---|---|
| `plan.json` | 48조건, 별도 world, source/parent hashes, 가설·종료 기준 |
| `raw/tNNNN.json` | query별 관측·초기값·활성 link·모든 tick·proof·support·adoption |
| `attempts.jsonl` | 시작부터 완료까지 append-only 사건 기록 |
| `analysis/summary.ko.md` | 전체 결과·실패 경계·가설 판정 |
| `analysis/signal_ledger.csv` | 모든 tick/group의 신호 항 분해 |
| `analysis/boundaries.csv` | 동시에 나타날 수 있는 실패 flag와 최초 충돌 시점 |
| `analysis/pairs.csv`, `interactions.csv` | 한 요인씩 비교한 대조와 2×2 상호작용 |
| `analysis/hypotheses.csv` | 지지·실패·판정불가를 빠짐없이 표시 |
| `analysis/prior_regressions.csv` | 이미 본 탐색 16조건과 이번 native 실행 비교 |
| `analysis/audit.json` | 수치·proof·event 검증 결과 |
| `source/` | 실제 사용한 전체 상속·신규 source snapshot |
| `parent/` | 검증한 EXP-29 및 그 부모 evidence 사본 |
| `parent_byte_recovery.json` | 사본 생성 시 적용한 정확한 줄바꿈 복원 기록 |
| `execution/` | 단계별 시작/완료, 기존·신규 테스트 및 실행 로그 |
| `raw_manifest.json`, `bundle_manifest.json` | 원자료/전체 묶음의 정확한 byte hash |
| `VERIFY_BUNDLE.cmd` | ZIP 해제본에서도 쓰는 읽기 전용 전체 재검증 |

폴더 옆에 `_evidence.zip`, ZIP checksum receipt, `_receipts/`가 생성된다. 봉인 후 기록은 봉인 폴더 밖에만 저장한다. Git push는 사용자가 수행한다.

## 오류가 나면

`failure.json`과 해당 `execution/*.txt`의 원래 traceback을 보존한다. 하위 프로세스의 마지막 오류 내용을 콘솔에도 출력한다. `partial_progress.json`과 `attempts.jsonl`은 최초 시도를 남긴다. 같은 run을 덮어쓰지 않는다.

부모 폴더의 필수 원본이 없으면 새 실험 전에 중단한다. 로그를 새로 만들어 채우거나 verifier를 skip하지 않는다. Git에서 LF/CRLF가 바뀐 텍스트는 사본의 변환 결과가 과거 SHA256과 정확히 맞는 경우에만 복원한다.

## 검증 범위

배포 검증은 Python/Linux의 실제 native 8파일 hash 확인, 48조건의 개발 실행, 별도 방정식·proof 검산, 오류주입과 Git bytes roundtrip을 포함한다. 정식 사용자 EXP-30 결과는 이 개발 검증과 합산하지 않는다.

Windows CMD/PowerShell과 실제 전체 부모 corpus는 작성 환경에서 실행하지 못했다. 사용자의 OneClick은 원래 부모 verifier와 기존 테스트를 실제로 실행해야 진행한다. 전체 workflow의 작성환경 통합 시험에서 사용하는 합성 부모 fixture와 기존 corpus 테스트 대체는 검증 JSON에 명시하며, production에는 우회·skip 옵션이 없다.

자세한 설계와 기존 탐색 구분은 `docs/R049_DESIGN.ko.md`, `docs/R049_PRIOR_EXPLORATION.json`을 참고한다.
