# 현재 기준선 — R0.2 실행 완료 / 기준선 정리

2026-09-16 사용자가 제공한 Windows 11 · Python 3.12.10 실행 로그에서 `136/136 passed`, R0.2 `demo complete=true`, `verify verified=true`, `differences=[]`를 확인했다. 이는 배포 당시의 정적 검사 이후에 발생한 실행이다.

- 현재 수용·한계: `docs/R02_BASELINE.ko.md`
- 원시 증거 동결·실행 방법: `docs/R02_BASELINE_USAGE.ko.md`
- EXP-09 비교 명세: `docs/R02_BASELINE_PROTOCOL.ko.md`
- 사용자 실행 수용 기록: `evidence/implementation/r02_execution_acceptance_20260916.json`
- 후속 전체 로드맵: `docs/reference/R02_PLUS_ROADMAP_20260916.ko.md`

이번 정리는 엔진 0.2.0의 동작을 바꾸지 않는다. `r02_status.json`, `r02_static_review.json`, `docs/R02_ACCEPTANCE.ko.md`는 **소스 배포 당시 기록**으로 그대로 두고, 현재 상태는 위의 별도 기록에 둔다. 과거 문서의 “실행 전”을 현재 상태로 다시 해석하지 않는다.

## 현재 완료와 남은 자료

기준선 문서, 사용자 실행 수용, 소스 경계 검토, 후속 비교 명세와 보조 도구 작성을 완료했다. 원시 `runs/r02_first`의 동결·비용 분석은 로컬 수집기가 수행하며, 새 paired 진단은 별도의 명시적 실행이 필요하다. 이미 통과한 R0.2 실행을 다시 미완료로 되돌리는 뜻은 아니다.

## 이후 순서

1. R0.2.1: 기존 dependency 계산의 시간·상태 계약과 snapshot/restore/resume.
2. R0.3: 제한된 M specialization과 처리 결과 통합.
3. R0.4: 작은 fork/join motif와 회로 간 구조 학습.
4. R0.5a/b: 지속 activation/readout와 제한된 새 후보 조합.
5. R0.6: A adaptation.
6. R0.7: A/D/M 단독·조합과 일반화.

버전 순서와 실제 선행 의존성은 전체 로드맵을 따른다. R0.2 기준선 정리에서 R0.2.1 기능을 먼저 넣지 않는다.

## 기록 보존

변경 직전 로드맵과 release manifest는 `docs/reference/r02_pre_baseline_*`에 보존했다. 기존 인계의 연구 원칙과 초기 제안은 삭제하지 않는다. 원본 run을 덮어쓰거나 현재 source hash를 과거 plan에 다시 써 넣지 않는다.
