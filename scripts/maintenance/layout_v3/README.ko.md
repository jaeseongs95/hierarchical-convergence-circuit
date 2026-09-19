# 저장소 정리 V3

기준: main `afb5d5e5b67906b7697f16163e166f59b17e1655` (프로젝트 구조 정리).

## 실행

ZIP의 `scripts` 폴더를 저장소 루트에 합친다.
`scripts/maintenance/layout_v3/ORGANIZE.cmd`를 더블클릭한다.
Windows 개발자 모드나 관리자 권한은 요구하지 않는다. Python 3.12 이상과 Git은 기존 설치본을 사용한다.
연구 중이거나 파일을 편집 중이면 완료한 뒤 실행한다. tracked 변경이 있으면 적용 전 중단한다.
기존 패키지와 같은 파일을 덮어쓰는 도구가 아니며, 새 toolkit 폴더만 추가한다.

## 범위

구버전 실행기 6개를 `scripts/legacy/`로 옮긴다. 실행기의 repository root 계산과
테스트 파일 6개에 들어 있는 경로 리터럴도 함께 갱신한다. assertions나 테스트 ID는 바꾸지 않는다.
R034~R047의 색인을 이미 옮겨진 archive 경로로 수정하고, 보관 자료와 현재 실행을 구분한다.
현재 README와 안내를 갱신한다. 변경 전 원문은 `archive/layout-v3-originals/`에 보존한다.
R048/R049 실행기/manifest, `src`, `tools`, `configs`, 기존 raw evidence는 그대로 둔다.

## 순서

preflight → 전체 파일 해시·원본·plan 동결 → 정리 → 독립 구조 감사 → core 회귀시험 1회 → 최종 파일 해시 감사.
정리 전/중간에 전체 테스트를 돌리지 않으며 새 연구 실험도 실행하지 않는다.
기존 성공 기록의 602개 core 테스트와 skip 상세를 기준으로 최종 결과를 비교한다.
새 skip, 실패, 오류, 테스트 누락은 중단 사유다. 기존 skip이 실제 pass로 바뀐 경우는 별도로 기록한다.

## 결과

완료: `LAYOUT_V3_APPLIED_AND_VERIFIED`

로그: `HCR-Evidence/repository-layout/layout-v3-<시간>-<ID>/`

`summary.ko.md`, `structure_audit.json`, `regression.txt`, `regression.json`,
`regression_acceptance.json`, `final_audit.json`, `plan.json`, `operations.jsonl`이 저장된다.
기존 evidence는 덮어쓰지 않는다. 실패 시 최초 traceback과 이 작업 변경분의 rollback 결과가 남는다.
강제 종료 후에는 `RECOVER.cmd`로 명시적으로 복구한다. 정상 작업을 반복하거나 자동 재시도하지 않는다.

## 주의할 구분

이 정리는 과거 실험을 새 경로에서 자동 재현하는 framework가 아니다.
과거 release의 원래 경로/해시 계약을 최신 계약인 것처럼 다시 봉인하지 않는다.
`Run-HCR.cmd`는 현재 R048/R049만 dispatch하며 구버전 항목은 보관 위치와 재현 조건을 표시한다.
`VERIFY.cmd`는 완료된 정리 파일의 바이트·현재 release 계약만 확인하며 실험을 실행하지 않는다.

commit/push, 시스템 설정 변경, 자동 설치, 모델 다운로드는 하지 않는다.
