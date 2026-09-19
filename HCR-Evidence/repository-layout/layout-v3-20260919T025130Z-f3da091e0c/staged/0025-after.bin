# 현재 구조와 실행 계약

## 세 종류의 경로

**현재 실험 실행:** `Run-HCR.cmd` → `scripts/run_indexed_experiment.py` → 기존 R049/EXP-30.
R048/EXP-29도 명시적으로 선택할 수 있다. 기본값·실행 인수·작업 디렉터리·실험 소스는 변경하지 않는다.

**구버전 실행기와 회귀 계약:** R02/R021/R03/R031/R032/R033은 `scripts/legacy/`로 이동한다.
실행기가 계산하는 저장소 루트와 여섯 테스트 모듈의 참조 경로를 함께 변경한다.
테스트의 assertion과 테스트 ID는 유지한다. root에 compatibility wrapper를 또 만들지 않는다.
이전 release 검사를 포함하는 역사적 드라이버이며, 현재 전체 checkout에서 과거 실험이
그대로 재현된다고 보증하는 경로가 아니다. 정확 재현에는 원본 commit/source를 사용한다.

**보존 자료:** R034~R047 파일은 기존 `archive/releases/` 위치와 바이트를 유지한다.
색인의 옛 루트 경로를 실제 archive 위치로 갱신하고, 실행 가능한 최신 항목과 구분한다.
`--list`나 `--describe EXP-15`는 조회만 하며, archive를 자동 재설치하거나 실행하지 않는다.

## 사용

```text
Run-HCR.cmd --list
Run-HCR.cmd --check-index
Run-HCR.cmd --describe EXP-30
Run-HCR.cmd
```

위에서 마지막 명령만 기본 연구 실험을 실행한다. 구조 정리 자체는
`scripts/maintenance/layout_v3/ORGANIZE.cmd`를 실행한다.

## 그대로 보존하는 계약

`src/hcr/`, `tools/`, `configs/`, 기존 `HCR-Evidence/`, 기존 archive release,
R048/R049 manifest와 등록 파일은 수정하지 않는다. R049가 R048의 원 manifest blob까지
고정하고 있어 이 부분을 옮기면 경로 수정 이상의 release chain 변경이 되기 때문이다.

과거 `RELEASE_MANIFEST.json`은 배포 시점의 경로·바이트 목록이다. 이번 경로 이전을 반영하려고
그 기대 해시를 다시 만들지 않으며, 이를 새 레이아웃 전체에 대한 인증서로 표시하지 않는다.
기존 manifest나 봉인 결과의 기대 해시를 바꿔서 검증을 통과시키지 않는다.
변경 전 README·실행기·테스트·색인은 `archive/layout-v3-originals/`에 원래 바이트로 보존한다.
현재 레이아웃 변경분은 `LAYOUT_V3.json`과 정리 evidence의 전후 해시로 관리한다.

## 정리 검증

preflight → 원본·plan 동결 → 파일/참조/색인 정리 → 독립 구조 감사 → core 회귀시험 1회 → 최종 해시 감사.
정리 전/중간에 전체 테스트를 실행하지 않는다. 기존 정상 실행의 skip 목록을 읽어
기존 미측정 상태로 유지하며, 새 skip·error·failure는 통과로 바꾸지 않는다.
기존 skip이 실제 pass가 된 경우는 별도 개선으로 기록한다.

실패 시 이번 변경분만 바이트를 확인해 되돌린다. 외부에서 달라진 파일은 강제로 덮어쓰지 않는다.
기존 로그는 수정하지 않고 `HCR-Evidence/repository-layout/layout-v3-*/`에 새 실행을 남긴다.
강제종료 후 복구는 같은 도구 폴더의 `RECOVER.cmd`가 수행한다. 자동 재시도는 없다.
