# Hierarchical Convergence Circuit

사고의 Graph 형성·검증·회로화·재사용·재확장을 분리해 검증하는 연구 저장소다.
현재 저장소의 구현은 소규모 계산 연구 장치이며, 가설·실행 결과·검증 범위를 구분한다.

[현재 구조와 실행 안내](docs/current/REPOSITORY_GUIDE.ko.md) · [실험 색인](experiments/INDEX.ko.md) · [가설](theory/core-hypothesis.md) · [주장 기록](evidence/claims.yaml)

최신 연구 판단: [2026-10-15 주장–증거 연결표](evidence/claim-evidence-links-20261015.ko.md)

최신 비교 결과: [2026-10-15 같은 graph의 실제 6셀 종료정책 비교](evidence/termination-sixcell-20261015-r10/report.ko.md)

## 실행과 자료 찾기

`Run-HCR.cmd --list`는 실험과 보존 자료의 위치만 표시한다.
인수 없는 `Run-HCR.cmd`는 기존과 동일하게 **설치된 R049 / EXP-30** 실행기를 호출한다.
구조 정리 도구를 실행하는 명령이 아니며, 실제 연구 실행과 원자료 생성을 수행한다.

Python CLI 진입점은 `hcr.py`, 기존 기본 PowerShell 진입점은 `Run-HCR.ps1`이다.
현재 등록 실험, 과거 실행기, 실험 결과 존재 여부와 가설 지지 여부는 서로 다른 상태로 관리한다.

## 구조

```text
src/hcr/                       공통 계산 엔진·독립 평가 계층 (이번 정리에서 변경 없음)
tests/                         기존 core 회귀시험 (6개 파일의 실행기 경로만 갱신)
configs/                       기존 실행 조건 (변경 없음)
tools/                         버전별 연구 장치와 자체시험 (변경 없음)
scripts/
  legacy/                      구버전 실행기; 루트 계산과 테스트 참조를 함께 이전
  run_indexed_experiment.py     현재 실행 / 역사 보존 상태를 구분하는 공통 진입점
  maintenance/layout_v3/        정리·검증·명시적 복구 도구
experiments/                   설계, 동결 조건 및 현재/과거 경로 색인
evidence/                      claim·구현 상태 registry
HCR-Evidence/                  실행 원자료 및 정리 작업의 신규 evidence
archive/
  releases/                    이미 보존된 R034~R047 release 원본
  layout-v3-originals/          이번에 위치·내용이 바뀐 파일의 원래 바이트
  distributions/               앞 단계에서 보존한 배포 파일
docs/current/                  현재 구조·운영 문서
theory/ formalism/ architecture/ 가설·계산 정의·아키텍처 문서
```

R048/R049의 루트 실행기·README·manifest는 설치된 release의 상속·해시 검증 계약 때문에 유지한다.
역사적 `RELEASE_MANIFEST.json`과 `archive/releases/`의 manifest는 수정하지 않는다.
이 파일들을 현재 전체 checkout의 무결성 인증으로 해석하지 않는다.

## 재현성과 연구 기록

기존 source snapshot·raw evidence·실패 기록·과거 manifest는 다시 봉인하거나 덮어쓰지 않는다.
과거 실험의 재현에는 해당 실행의 원본 commit과 봉인된 source를 사용한다.
`Run-HCR.cmd`는 보관된 실행기를 새 현재 실험처럼 자동 실행하지 않는다.

정리 작업의 신규 plan·전체 파일 해시 대조·구조 검산·마지막 회귀시험은
`HCR-Evidence/repository-layout/layout-v3-*/`에 저장한다.
기존 symlink 환경 skip은 pass로 바꾸지 않고, 이전 성공 기록과 같은 항목/사유인지 비교한다.

- [동일 graph 인증 비용 대조(r11)](evidence/certificate-cost-20261015-r11/report.ko.md)

- [동일 graph 전진 시간·C 전체 비용 교차 대조(r12)](evidence/forward-crossover-20261015-r12/report.ko.md)
