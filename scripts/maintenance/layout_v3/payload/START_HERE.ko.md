# 현재 저장소 진입점

**설계·결과를 찾을 때:** [실험 색인](experiments/INDEX.ko.md)

**구조·실행 계약을 확인할 때:** [현재 구조 안내](docs/current/REPOSITORY_GUIDE.ko.md)

**연구 실험을 실행할 때:** 루트 `Run-HCR.cmd`. 기본 EXP-30 / R049는 변경하지 않는다.
목록만 확인하려면 `Run-HCR.cmd --list`, 경로 검사만 하려면 `Run-HCR.cmd --check-index`를 사용한다.

`archive/releases/`는 과거 배포본 보존 구역이다. 그 위치로 이동했다는 이유만으로
원래 실행기가 새 위치에서 그대로 재현 가능해진 것은 아니다. 정확 재현은 원본 checkout과
봉인된 source를 기준으로 한다.

`src/hcr`, `tools`, 기존 raw evidence와 원래 release manifest는 이번 구조 정리에서 바꾸지 않는다.
구버전 실행기 6개는 `scripts/legacy/`로 이동하며, 기존 테스트의 파일 참조도 함께 갱신한다.
