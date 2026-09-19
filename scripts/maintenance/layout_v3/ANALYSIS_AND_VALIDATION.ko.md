# HCC 저장소 구조 정리 V3 — 분석 및 전달 전 검증

## 1. 기준선과 결정

대상 저장소: `jaeseongs95/hierarchical-convergence-circuit`  
확인한 최신 `main`: `afb5d5e5b67906b7697f16163e166f59b17e1655`  
커밋 메시지: `프로젝트 구조 정리`  
이전 기준선: `83d07f43cb9b138cadfcdbdd1f0e40bcfb5857e9`

이번 작업은 기존 엔진에 새 계산 메커니즘을 추가하는 실험 revision이 아니라 저장소 구조의 정리다.
파일의 위치만 바꾸지 않고 **실행기 내부 루트 계산 → 테스트 참조 → 실험 색인 → 공통 진입점 → 현재 문서**를 함께 정리한다.
현재 R048/R049의 상속된 source/manifest 계약은 그대로 두고, 실험 의미·조건·raw evidence를 변경하지 않는다.

## 2. 실제 확인한 문제

### 루트에 남은 구버전 실행기 6개

| 기존 루트 파일 | 이동 후 위치 | 함께 변경하는 테스트 모듈 |
|---|---|---|
| `Run-HCR-R02.ps1` | `scripts/legacy/Run-HCR-R02.ps1` | `tests/test_r02_audit_cli.py` |
| `Run-HCR-R021.ps1` | `scripts/legacy/Run-HCR-R021.ps1` | `tests/test_r021_cli.py` |
| `Run-HCR-R03.ps1` | `scripts/legacy/Run-HCR-R03.ps1` | `tests/test_r03_methods.py` |
| `Run-HCR-R031.py` | `scripts/legacy/Run-HCR-R031.py` | `tests/test_r031_prior_scope.py` |
| `Run-HCR-R032.py` | `scripts/legacy/Run-HCR-R032.py` | `tests/test_r032_grounding.py` |
| `Run-HCR-R033.py` | `scripts/legacy/Run-HCR-R033.py` | `tests/test_r033_review.py` |

Python 실행기는 `Path(__file__).resolve().parent`를 두 곳에서 루트로 사용한다. `scripts/legacy/` 이전 후에는 `.parents[2]`를 사용한다.
PowerShell 실행기는 `$PSScriptRoot`의 부모의 부모를 루트로 사용하게 수정한다.
해당 테스트 모듈은 각각 파일 경로 리터럴 한 곳만 바꾼다. assertion·테스트 수·ID·실패 판정은 바꾸지 않는다.
적용 후 독립 감사기는 경로 치환을 역으로 적용해 원문과 바이트 및 전체 Python AST를 비교한다.

### 이전 archive 이동을 반영하지 못한 색인

현재 `experiments/INDEX.json`에는 이미 archive로 옮긴 R034~R047 Python 실행기와 manifest를 루트 경로로 가리키는 참조가 각각 14개씩, 총 28개 남아 있다.
현재 `scripts/run_indexed_experiment.py`도 단일 루트 파일명만 실행 대상으로 받는다. 따라서 602개 core 회귀시험 통과와 별개로 색인/공통 진입점의 경로 정합성을 고쳐야 한다.

V3는 이를 실제 `archive/releases/rNNN/...` 경로로 바꾼다. 31개 실험 ID, 기존 `source_commit`, `run_status`, 원 실험 설계와 결과 위치는 그대로 유지한다.
`current_python_entrypoint`와 `execution_status`를 추가해 현재 실행 가능한 release와 과거 자료를 명확히 구분한다.

### R048/R049는 유지하는 이유가 다르다

R049의 `tools/r049_signal_boundary/provenance.py`는 원래 위치의 R048 manifest를 읽고, 그 Git blob pin과 R048의 등록 파일 해시까지 검증한다.
이 파일들을 옮기면 단순 실행 경로 변경이 아니라 source-freeze와 부모 release 검증 체인의 재설계가 필요하다.
이번 정리에서는 그 비용을 들여 현재 실험 계약을 바꾸지 않는다. 다음 파일 8개는 루트에 유지한다.

```text
R048_MANIFEST.json    R048_README.ko.md
Run-HCR-R048.cmd      Run-HCR-R048.py
R049_MANIFEST.json    R049_README.ko.md
Run-HCR-R049.cmd      Run-HCR-R049.py
```

기본 `hcr.py`, `Run-HCR.cmd`, `Run-HCR.ps1`도 공통 진입점으로 유지한다.

## 3. 실행 상태의 의미

`Run-HCR.cmd`의 기본값은 기존과 같은 EXP-30 / R049다. EXP-29 / R048도 명시적으로 선택할 수 있다.
기존 R048/R049 실행기 파일·인수·작업 디렉터리·반환코드는 변경하지 않는다.

과거 실행기에는 원래 release의 root 경로와 해시 검사가 남아 있다. archive에 들어 있거나 새 `scripts/legacy/`에서 찾아진다는 사실을 현재 checkout의 재현 가능성으로 오해하면 안 된다.
공통 진입점은 과거 항목에 대해 원본 commit/sealed source가 필요한 보존 자료임을 알리고 자동 실행하지 않는다. 동작 가능한 것처럼 보이게 하려고 원래 manifest를 다시 해싱하거나 과거 테스트를 건너뛰지 않는다.

조회 기능은 다음과 같다. 아래는 **정리 실행 명령이 아니라 정리 후 연구 자료를 조회하는 예시**다.

```text
Run-HCR.cmd --list
Run-HCR.cmd --describe EXP-15
Run-HCR.cmd --check-index
```

인수 없는 `Run-HCR.cmd`는 실제 연구 실험을 실행한다. 정리는 별도의 `scripts/maintenance/layout_v3/ORGANIZE.cmd`로 한다.

## 4. 변경 및 보존 경계

V3는 실행기 6개, 테스트 모듈 6개, 현재 색인과 문서, dispatcher만 지정된 계획대로 변경한다.
수정 전 입력 19개는 `archive/layout-v3-originals/`에 정확한 원래 바이트로 보존한다. 실제 개수와 변경분은 생성된 plan이 기준이다.
현재 README를 새 안내로 교체하되 과거 내용을 원문 보존본으로 남긴다.

다음은 변경하지 않는다.

- `src/`, `tools/`, `configs/`의 기존 코드와 조건
- 기존 `HCR-Evidence/`, `evidence/`, `validation/`의 자료
- 기존 `archive/releases/`와 `archive/distributions/` 자료
- R048/R049 manifest 및 등록된 파일
- 역사적 `RELEASE_MANIFEST.json`의 기대 해시
- `hcr.py`, `Run-HCR.cmd`, `Run-HCR.ps1`

역사적 RELEASE_MANIFEST는 과거 배포에 대한 원기록으로 남긴다. 새 레이아웃 전체를 증명하는 인증서로 표시하지 않으며, 이를 최신화해 원래 기대값을 바꾸지 않는다.
새 레이아웃은 `docs/current/LAYOUT_V3.json`, 동결된 변경 계획, 실제 전후 파일 해시, 독립 감사 결과로 기록한다.

## 5. 원클릭 운영 계약

```text
패키지 해시 확인
→ Git/commit/사용자 변경/기존 성공 영수증/현재 release 계약 확인
→ 전체 작업 파일 해시와 원본·변경 후 바이트 및 plan 동결
→ 지정된 경로·테스트 참조·색인·문서 이전
→ 독립 구조 감사
→ 기존 core 회귀시험 한 번
→ 전체 작업 파일 재대조 및 결과 봉인
```

정리 전/중간에 전체 project tests를 실행하지 않는다. 합성 장치 시험 43개도 사용자 정리 중 자동으로 반복하지 않는다.
core 회귀는 현재 `tests/`만 한 번 수집·실행한다. 버전별 모든 tool 시험이나 과거 연구 전체를 재실행했다는 뜻은 아니다.

실제 로컬 HEAD가 지정 commit과 다르거나 tracked 사용자 수정이 있으면 적용 전 중단한다.
원래 공개한 정상 회귀 결과 `HCR-Evidence/repository-layout/phase2-v2-20260919T020845Z-5406ad54f3a6/regression.json`을 Git 원문과 대조한다.
그 기준선의 602개와 기존 skip 상세를 최종 결과와 비교한다. 새 skip/error/failure와 누락/중복 수집은 실패다.
기존 skip이 실제 pass가 된 경우에는 별도로 기록하며 오류로 취급하지 않는다.

파일 쓰기 전에 의도를 기록하고 원본 바이트를 보관한다. 일부 쓰기 직후 중단돼도 기록된 작업을 거슬러 복구한다.
복구 대상 파일이 외부에서 바뀌었다면 강제로 덮어쓰거나 삭제하지 않고 충돌로 남긴다. 다른 사용자 파일도 삭제하지 않는다.
정상 실행 종료 후 완성된 정리를 다시 적용하지 않는다. 이미 적용된 상태면 설치된 변경분과 봉인 영수증만 확인한다.

Git은 읽기 명령만 사용한다. git add/commit/push/reset, 자동 설치, 모델 다운로드, Windows 개발자 모드, 관리자 권한, 영구 환경변수 수정은 없다.

## 6. 전달 전 검증 — 실제 수행 범위

**완전한 HCC checkout 전체를 복제해 602개를 실행한 검증은 수행하지 않았다.**
GitHub의 현재 원문과 blob을 직접 확인한 파일들을 사용한 대상 검증과 정리 장치 검증을 수행했다.
작성 환경은 Linux / Python 3.13.5이며 Python 3.12 문법 파싱을 별도 확인했다.

| 검증 | 실제 결과와 범위 |
|---|---|
| 원본 파일 정체성 | 실행기 6개와 전체 INDEX.json, 총 7개 완전한 파일이 GitHub blob과 일치 |
| 유지보수 장치 시험 | **43개 통과, 실패 0, 오류 0, skip 0** |
| 기존 launcher assertion | 위 시험에 포함된 별도 실제 subprocess에서 **기존 assertion 6개 통과** |
| 원본 Python 실행기의 계획/cwd/인수 | 이전 전후 비교 통과; 실제 연구 실행은 하지 않음 |
| 오류 주입 | 부분 쓰기, 최종 시험 실패, 봉인 직전 실패, 외부 수정, 복구 경로 점검 통과 |
| 구조 검산 | 전체 fixture 파일 대조, 원본 보존, test AST 동등성, 색인 경로 검사 통과 |
| 구문 | Python 3.12 문법 파싱 통과 |
| 실제 Windows CMD/PowerShell | 이 환경에서 실행하지 않음 |
| 전체 HCC core 602개 | 작성 환경에서 실행하지 않음. 사용자 PC에서 정리 후 실행하여 통과해야 완료 |

여기서 43개와 6개는 독립 표본을 더한 49개라는 의미가 아니다. 43개 중 통합 시험 한 개가 6개 원본 assertion을 별도 프로세스로 실행한다.
같은 검증을 패키징 후 반복해도 새로운 연구 증거로 합산하지 않는다.

작은 Git fixture에는 실제 원본 실행기와 색인, 추출한 6개 기존 테스트를 사용한다.
나머지 저장소 모양과 import용 최소 fixture는 완전한 HCC 엔진이 아니며 실제 연구 원자료로 취급하지 않는다.
통합 fixture의 preflight는 fixture 전용 대조로 대체했다. 전달하는 production에는 조건 우회나 테스트 생략 옵션이 없다.

### 검증 코드와 로그

패키지 `tests/`에 검증 코드를 포함했다. `validation/`에는 최초 수행부터 최종 수행까지 로그와 범위를 보존했다.
핵심 기록은 `003_final_tests.txt`, `reference_demo_regression.txt`, `reference_demo_scope.json`, `verified_upstream_files.json`이다.
`reference_demo_*`는 작은 fixture의 실행 결과이며 실제 HCC 602개 결과가 아니다.

검증 담당자가 정리 장치 시험만 재현할 때 사용할 명령은 다음과 같다. 일반 사용자의 원클릭 정리에는 직접 입력할 필요 없다.

```text
cd scripts/maintenance/layout_v3
python -X utf8 -B -m unittest discover -s tests -p test_*.py -v
```

## 7. 사용자 실행

ZIP 내부의 `scripts` 폴더를 저장소 루트에 합친 후 다음 파일을 더블클릭한다.

```text
D:\codex\진짜미친짓\hierarchical-convergence-circuit\scripts\maintenance\layout_v3\ORGANIZE.cmd
```

ZIP은 새 maintenance 폴더만 담는다. 압축을 푸는 단계에서 기존 연구 소스·manifest를 덮어쓰지 않는다.
현재 프로젝트를 편집하거나 실험 실행 중이라면 그 작업이 끝난 상태에서 정리를 실행한다.

새 로그 위치:

```text
HCR-Evidence/repository-layout/layout-v3-<UTC 시간>-<ID>/
```

`regression.txt`는 마지막 시험 중 실시간으로 쌓인다. 콘솔과 `summary.ko.md`로 완료 상태를 확인한다.
완료 문구는 `LAYOUT_V3_APPLIED_AND_VERIFIED`다.
오류 발생 시 `failure-*.json`, `rollback.json` 또는 명시적 `recovery-*.json`에 최초 오류·복구 경계를 남긴다.
정상 완료 뒤 전체 시험을 다시 돌리지 않고 설치 상태만 확인할 때는 같은 폴더의 `VERIFY.cmd`를 사용한다.
강제종료로 중간에 멈췄을 때만 `RECOVER.cmd`를 사용한다. 진행 중인 원래 프로세스가 있으면 복구를 거부한다.

## 8. 이번 분석에서 사용한 저장소 원문

모든 경로는 위 기준 commit에서 읽었다.

- `scripts/run_indexed_experiment.py`: 구형 root-only dispatcher
- `experiments/INDEX.json`: 전체 31개 실험 색인; blob `1e2208b837969a7b32b9a5fa3f138296d9cfe5ad`
- `Run-HCR-R02.ps1`, `Run-HCR-R021.ps1`, `Run-HCR-R03.ps1`
- `Run-HCR-R031.py`, `Run-HCR-R032.py`, `Run-HCR-R033.py`
- 표에 적은 여섯 `tests/` 모듈의 실제 경로 참조 및 launcher test 본문
- `tools/r049_signal_boundary/provenance.py`: R048 상속 pin과 source 복제/검산 계약
- `HCR-Evidence/repository-layout/phase2-v2-20260919T020845Z-5406ad54f3a6/regression.json`: 정상 로컬 회귀 기준선

구조·바이트·장치 회귀의 검증은 HCC 가설의 새 지지 증거가 아니며, 기존 실험 결과를 재판정하지 않는다.
