# HCC EXP-31 / R050 — 소스 구현 보고

## 완료한 작업

이전 후보 패키지의 실행 소스를 바탕으로 `r050-source-implementation-2`를 작성했다. 최신 main은 `7ba5f31fb68a92fa0eca8ed0bf5f302fe2d36b86`으로 다시 확인했다. 원래 실험의 `frozen_spec.json`, 24조건·4 arm, 관측 대상 정책과 worker 실행 규칙은 유지했다. core 및 kernel 변경은 없다.

## 이번에 보완한 소스

| 파일 | 구현 내용 |
|---|---|
| `audit.py` | 각 advance 직전의 worst-case tick 예약 검산, typed 실행 필드, arm schema 검사, native budget 종료와 일반 실패 구분 |
| `analysis_contract.py` | 96개 case/arm의 누락·중복, 공유 기준선 결속, 비용 중복 합산, 보류의 정답화, 72개 수치 비교 coverage 검사 |
| `reporting.py` | 파일 쓰기와 순수 렌더링 분리, 검산 결과의 plan/raw 결속 확인 |
| `verify_analysis.py` | 새 raw 재검산 결과와 저장된 audit/summary/CSV/Markdown의 읽기 전용 대조 |
| `selftest.py` | 빈 suite·신규 skip·expected failure·unexpected success를 pass로 처리하지 않는 실행기 |
| `pipeline.py` | strict self-test 및 산출물 대조 단계 연결, 기존 bundle 재검산에서도 산출물 대조 수행 |
| `maintenance.py` | 이전 R050의 알려진 hash만 갱신, 모든 preimage 보존, journal 기록 실패에도 변경 소유권 유지 |
| `regression.py` | 기존 core test의 expected failure·unexpected success를 명시적으로 보존·실패 판정 |

summary/CSV 대조는 원자료 audit를 대체하지 않는다. 독립 raw 재생 결과를 먼저 얻은 뒤 결정적인 포맷팅을 재실행하여 저장된 파생물과 비교한다. 같은 원자료의 재분석을 독립 표본으로 더하지 않는다.

## 확인된 실제 결과

이 환경에서 원래 후보의 단위 테스트 69개를 실행했고 모두 통과했다. 보완 후 최종 strict self-test는 **112개, 실패 0, 오류 0, skip 0**이었다. 새로운 검사에는 예산 예약·schema, 집계 위변조, 기존 버전 갱신·rollback, journal 실패 시 변경 소유권 보존이 포함된다. mock/synthetic 테스트는 구현 검사이며 실제 HCC 연구 결과가 아니다.

컨테이너의 Git 네트워크 접근은 `Could not resolve host: github.com`으로 실패했다. GitHub connector로 현재 main과 필요한 실행 계약 원문은 읽었지만 전체 checkout을 실행 컨테이너로 옮기지는 못했다. 실제 HCC 연동, 602개 core regression, 본 실험과 Windows 실행은 여기서 미실행이다. 사용자 저장소의 원클릭 실행에서 실제 연동 검산과 최종 core regression을 통과해야만 본 실험을 실행한다.

## 변경하지 않은 것

`src/hcr`, 기존 `tests`, R048/R049 release·manifest, historical raw evidence, dispatcher 기본값, 원래 EXP-31 frozen 조건은 변경하지 않았다. 원격 GitHub 수정·commit·push는 하지 않았다. 이전 후보의 manifest·보고·검증 로그도 이 전달본의 provenance 영역에 보존했다.

## 실행

`HCC_EXP31_R050_IMPLEMENTED/Run.cmd`를 실행한다. 저장소 안에 폴더째 풀면 경로를 자동 확인한다. 신규 설치와 이전 후보의 정확한 원본에서의 갱신을 모두 지원한다. 알 수 없는 수정 파일은 덮어쓰지 않는다.

실제 실행 결과는 `HCR-Evidence/exp31/`의 새 고유 폴더와 ZIP으로 남는다. 첫 실패나 부분 결과는 삭제·재분류하지 않는다. 현 단계는 **소스 구현 및 add-on 검사 완료**이지 연구 가설 검증 완료가 아니다.

## 전달 소스 전체에 대한 설치 검사

35개 payload 파일을 사용하는 임시 저장소 디렉터리에서 신규 설치와 rollback, 이전 후보에서 16개 파일 갱신과 원본 바이트 복원, 설치 후 동일 버전의 무변경 재적용을 확인했다. 외부 수정 파일은 적용 전에 거부됐고 원래 바이트가 보존됐다. 이는 파일시스템 설치 검사이며 실제 HCC 실행이나 GitHub 저장소 변경이 아니다.

`install.py --help`와 `Run-HCR-R050.py --help`는 정상 종료했다. worker 소스를 의도적으로 변조한 전달본은 저장소에 접근하기 전에 checksum 오류로 거부됐다. Python 소스 28개는 Python 3.12 문법 기준으로 검사했다.
