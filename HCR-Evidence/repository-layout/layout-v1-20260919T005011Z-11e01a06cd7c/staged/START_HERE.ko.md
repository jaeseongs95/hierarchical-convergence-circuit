# HCC — 현재 작업 시작점

이 안내는 `83d07f43cb9b` (`R049_EXP30 commit`)의 실제 파일 배치에 대한 구조 정리 v1이다.

[실험 색인](experiments/INDEX.ko.md) · [구조 안내](docs/current/REPOSITORY_GUIDE.ko.md) · [배포파일 보관](archive/distributions/README.ko.md)

## 실행

루트의 `Run-HCR.cmd`는 **이미 설치된 EXP-30/R049** 진입점을 호출한다. 기존 전체 연구 파이프라인/검증을 그대로 사용하며 새 결과 폴더는 원래 프로그램이 생성한다. 정리 스크립트 실행 자체는 연구 실험을 재실행하지 않는다.

목록 확인: `Run-HCR.cmd --list`

실험 선택: `Run-HCR.cmd --experiment EXP-29`

색인은 자동으로 최신 revision을 추측하지 않는다. 다음 연구 revision을 추가할 때 기본 실험과 색인도 명시적으로 갱신한다.

## 보존 범위

기존 엔진·tests·도구·manifest·설계·README·원자료는 바이트를 바꾸지 않는다. 과거 자체설치 배포파일 중 참조 검사를 통과한 항목만 `archive/distributions/`로 옮겼다. 기존 문서에 남은 과거 원클릭 파일명은 당시 배치 기록이다.

정리 계획·원본 해시·회귀검사·독립 audit·실패 및 복구 이력은 `HCR-Evidence/repository-layout/`에서 확인한다. Git add/commit/push, 설치, 다운로드, 자동 retry는 하지 않는다.
