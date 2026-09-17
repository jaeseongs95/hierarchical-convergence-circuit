# R035 구현 검증 기록

## 확인한 결과

2026-09-17 개발 환경에서 **신규 실험 도구 67개 테스트, 적용기 17개 테스트, 합계 84개가 통과**했다. 실패나 skip은 없다. 실행 환경은 Linux / Python 3.13.5다. 모든 배포 Python 파일은 Python 3.12 문법 기준으로도 AST 파싱했다. Windows와 Python 3.12에서의 실제 실행 결과를 대신하는 기록은 아니다.

| 검증 | 실제 수행한 범위 |
|---|---|
| 선택·변환·독립 DAG 검산·파일 I/O·CLI | unittest 67개 통과 |
| 추가 전용 적용기 | unittest 17개 통과 |
| Synthetic 상태 속성 검사 | 192개 상태 × 3개 변형 × 3개 정책의 검산 1,728회 |
| 기존 R034 선택 기준 대조 | 5개 관측 score 조건 × 16개 변형 = 80개 비교 |
| Native 재구성 | 기준 커밋의 실제 `hcr.proof.reconstruct` 함수를 import하여 실행 |
| 변조 거부 | 부모 참조, cycle, depth, 선택 경로, raw/plan/snapshot/시도 로그 변조 탐지 |
| 예산 및 실패 | 0 예산과 경계 예산, 최초 실패 보존, 자동 retry 없음, 기존 output/analysis 덮어쓰기 거부 |
| 적용 보호 | 기준선 drift·파일 충돌·경로 탈출·symlink 거부, 동일 재적용, 기존 evidence 보존 |

속성 검사와 R034 대조의 개별 조합은 67개 unittest 내부에서 수행된다. 이를 별도의 unittest 수로 중복 합산하지 않는다. 이 합성 검증을 EXP-16 본 실행의 새 native 표본이나 연구 결과로 사용하지 않는다.

## 실제 기준 소스를 사용한 부분

`hcr.model`, `hcr.binding`, `hcr.proof`, R034의 `hcr.selection` 및 선택 검산 관련 파일을 기준 커밋/배포본과 해시 대조한 로컬 부분 트리에서 실행했다. 실제 native 재구성 함수를 임의 구현으로 바꿔 테스트하지 않았다. 기존 지원 선택기와 새 지원 선택기의 proof·출력·계수도 직접 비교했다.

테스트용 부분 트리는 완전한 HCC 저장소가 아니다. runtime/session 계층과 EXP-15 전체 raw는 이 로컬 검증에 포함되지 않는다. 파일 생성→검산→보고 통합 테스트에서는 **synthetic fixture에 한해** 원 EXP-15 전체 검산 호출을 mock했다. 생산 코드에는 native 감사 생략 옵션이나 mock 결과를 성공으로 인정하는 경로가 없다.

## 이 환경에서 실행하지 않은 것

기준 저장소의 전체 회귀시험, 실제 `HCR-Evidence/exp15/r034-first` 전량 재검산, 이를 입력으로 하는 EXP-16 전체 prepare/execute/audit/verify는 이 기록에 포함되지 않는다. 따라서 원 상태 수나 실제 회복 건수는 여기서 확정하지 않는다.

제공한 `Run-HCR-R035.py`는 사용자 저장소에서 기존 회귀와 EXP-15 검산을 먼저 수행한 다음, EXP-16 동결·생성·독립 검산·재검산을 별도 프로세스로 실행하도록 구성했다. 어느 단계든 실패하면 중단하고 해당 기록을 보존한다. 이후 실제 실행 기록이 이 개발 검증과 구별되는 연구 evidence다.

## 배포 보호

업데이트는 기존 `src/hcr` 62개 파일에 대한 추가·수정 없이 `tools/r035_frozen_selection`, 전용 runner/CLI/검사기와 문서만 추가한다. 기존 릴리스 manifest, README, evidence, Git commit/서명 설정을 바꾸지 않는다. 기존 엔진 버전 문자열을 바꾸지 않고 독립 추가 실험 패키지로 관리한다.

`patch_manifest.json`은 적용 파일과 기준선 레지스트리의 SHA-256을, `R035_MANIFEST.json`은 설치된 새 파일의 SHA-256을 기록한다. 줄바꿈만 CRLF/LF로 달라진 경우를 구분하며, 의미가 바뀐 소스는 일치로 처리하지 않는다.

원본 개발 테스트 로그와 배포 파일 검사 결과는 압축파일의 `validation/`에 있다.
