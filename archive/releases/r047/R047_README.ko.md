# HCR R047 / EXP-28 사용 안내

## 실행

**`HCR_R047_EXP28_OneClick.cmd` 하나를 기존 저장소 최상위 폴더에 놓고 더블클릭한다.** ZIP을 따로 풀거나 여러 명령을 입력할 필요가 없다. 현재 R046 실행에 사용한 원래 로컬 checkout에서 실행하는 것을 전제로 한다.

필수 환경은 기존 Git, Python 3.12 이상, Windows PowerShell이다. Python이나 모델을 자동 설치하지 않는다. `HCR_PYTHON` 환경변수가 있으면 그 기존 실행파일을 사용한다. 없으면 기존 Python launcher와 PATH에서 사용 가능한 인터프리터를 찾는다. 선택 후 실패한 실험을 다른 Python으로 다시 실행하지 않는다.

CMD는 다음을 한 번씩 수행한다.

```text
소스 ZIP checksum 확인
→ 기준선 Git ancestry/native blob 확인
→ 기존 파일을 덮어쓰지 않는 additive 설치
→ EXP-27 원본 evidence 완전성 및 독립 재검산
→ self-test / EXP-27 dynamics 회귀검사
→ EXP-28 plan 동결
→ A 2회 + B 42조건 실제 실행
→ raw·매 tick event·부분 실패 보존
→ 독립 scalar/proof/binding audit
→ analysis 독립 재집계·verify
→ summary + portable evidence ZIP + checksum receipt
```

## 무엇을 실험하는가

정상 연장에서는 같은 B network에서 **전달 없음 / A edge만 / A prefix만 / 둘 다**를 비교한다. 각 mask에는 실제 A 수치 대신 **사전에 고정한 0.99**를 넣는 대조가 추가된다. 총 7개 처리다. 대상 불일치와 근거 변경을 포함한 3상황×2 ID×7처리=42 B 조건이며 A source는 2개를 공유한다.

고정값과 실제 상태가 같은 ticks를 보여도 실패를 숨기거나 값을 바꾸지 않는다. 모든 가설 상태가 summary에 표시된다. native core, 경로 탐색, B graph, 정지 기준은 변경하지 않으며 새 goal과 안정화 이력을 복사하지 않는다.

가소성·잠재 연결 공간은 이번에 직접 구현하지 않았다. 해당 통합 가설의 첫 판별 실험인 **계산 상태 성분의 기여 분리**를 구현했다. 상세 설계는 `docs/R047_DESIGN.ko.md`에 있다.

## 기준선과 기존 파일 보존

기준 commit: `bdd24df2d783a1cea82a6050f4f793c9eb06ca0a` (`R046 exp27 commit`). 이 commit이 현재 HEAD의 ancestor여야 하며, 사용하는 native 8파일과 부모 snapshot은 정확히 일치해야 한다. 최신 main을 자동으로 pull하거나 checkout하지 않는다. 실행 HEAD와 실제 source hashes를 evidence에 남긴다.

기존 `src/hcr/*`, R046 소스, EXP-27 raw/summary/manifest는 수정하지 않는다. R047 파일과 연구 로그 보존용 scoped `.gitignore` 두 개를 추가한다. 같은 이름의 다른 파일이 있으면 덮어쓰지 않고 중단한다. 같은 내용의 R047 파일은 그대로 두므로 설치 재실행은 가능하다. 사용자가 다시 실행한 연구는 새 run ID로 구분되며 자동 retry는 없다.

## 부모 evidence 누락 시

고정 부모 폴더:

`HCR-Evidence/exp27/r046-20260918T052020_778586Z-c3aecba2`

Git에 push되지 않은 `source/validation/r046/*.log`가 부모 manifest에 등재되어 있으므로 **Git clone만 새로 받은 환경은 preflight에서 멈출 수 있다.** 실제 실행했던 원래 로컬 폴더에는 해당 로그가 남아 있을 수 있다.

누락/해시 불일치 시 `HCR-Evidence/exp28/r047-.../failure.json`에 전체 목록과 traceback을 기록하고 **새 EXP-28 추론을 시작하지 않는다.** 로그를 재생성하지 않고, manifest를 줄이지 않으며, skip 옵션도 제공하지 않는다. 정확한 원본 bytes가 필요하다. 이 패키지가 과거에 누락된 원본을 복구했다고 주장하지 않는다.

## 결과 위치

매번 별도 폴더:

`HCR-Evidence/exp28/r047-<UTC timestamp>-<unique id>/`

주요 내용:

| 위치 | 내용 |
|---|---|
| `plan.json` | 공개 입력, 별도 world, 처리 순서, 가설, config, source/parent hashes |
| `raw/` | A 2개·B 42개 원자료, 실제 초기값·state·proof·비용 |
| `attempts.jsonl` | 시작→gate→network→모든 tick→proof→adoption→완료의 append-only 기록 |
| `source/` | 실행에 사용한 R047 소스와 native 핵심 snapshot |
| `basis/exp27/` | 검증한 부모 원자료·소스·analysis 사본 |
| `analysis/summary.ko.md` | 관찰표, 성공/실패를 포함한 가설 전체 판정, 해석 경계 |
| `analysis/parent_review.ko.md` | 원래 EXP-27 H_ID 실패를 보존한 별도 보완 보고 |
| `analysis/trials.csv`, `pairs.csv`, `hypotheses.csv` | 조건별·paired 비교와 가설 판정 |
| `analysis/transfer_maps.csv`, `dependency_scans.csv` | 실제 상태 매핑과 검증 순서 |
| `analysis/ID_controls.csv`, `interactions.csv` | ID/검사 비용 분리와 기술적 상호작용 |
| `analysis/audit.json`, `record_audits.json` | 독립 재계산과 proof 검사 |
| `raw_manifest.json`, `bundle_manifest.json` | raw 및 완성 묶음의 byte hash |
| `execution/` | 단계 시작/완료 JSON, self-test 출력 `.txt` |
| `VERIFY_BUNDLE.cmd` | 완성 evidence 또는 ZIP 해제본의 읽기 전용 재검증 |

폴더 옆에 `*_evidence.zip`과 `.receipt.json`이 생긴다. ZIP은 source와 부모 근거를 포함하며 생성 후 bytes를 다시 검증한다. Git push는 자동 수행하지 않는다. `failure.json`이 있으면 성공 bundle로 해석하지 않는다.

## 검증 범위

함께 제공한 `HCR_R047_release_validation.json`은 이 패키지 작성 환경에서 실행한 self-test·원래 dynamics 회귀·합성 integration 검증 결과다. **정식 EXP-28 연구 결과가 아니다.** Windows CMD/PowerShell 실제 실행과 사용자의 전체 원래 부모 evidence에 대한 현장 검증은 실제 OneClick 실행에서 확인된다.

가설 실패는 장치 오류가 아니다. 정답과 채택을 유지하지 못한 조건에서 빠르다는 이유만으로 효율 지지를 선언하지 않는다. raw가 유효한 상태에서 가설이 실패하면 실패로 보고한다.
