# R050 proof 실패 검산 수정

구현 식별자: `r050-source-implementation-3-proof-audit`

## 확인한 원인

최초 실행 `r050-20260919T074408Z-2ef29df6ea`의 03 로그는
`hcr.evaluation.grounding_audit.verify_diagnostic`의 `invalid primitive proof`에서 실패했다.
`c000`은 raw=False, proof 유효성=False, proof nodes=0, accepted=False였다.
기존 session auditor는 proof의 독립 재계산 결과와 자기보고가 일치하는지를 검사하며 이 상태를 허용한다.
반면 기존 grounding auditor는 값이 있는 모든 판단에서 유효한 proof를 요구했다.
proof 구성 실패를 관찰하도록 동결된 R050 설계와 이 추가 전제의 불일치가 직접 원인이다.

설치 receipt의 `rollback.json`에는 complete=true, unresolved=[]가 기록되어 있다.
따라서 설치가 유지됐다는 이전 인계의 설명과 달리, 작업 시작 시 R050 설치는 롤백된 상태였다.

## 변경 범위와 검증 계획

보존된 최초 실행 source의 R050 manifest 해시를 확인한 뒤 해당 addon을 복원했다.
`candidate_audit.py`는 고정된 core의 candidate/diagnostic 검산을 R050 범위로 옮긴 것이다.
기존 provenance·상태/event 재생·진단·readout·시간 검사를 유지한다.
값이 있는 판단의 proof 유효성은 독립 재검산 결과와 보고값이 정확히 일치해야 한다.
유효하지 않은 proof는 비어 있는 실패 재구성이어야 하고, grounding support=False,
readout accepted=False 및 value=None이어야 한다. proof 실패를 성공으로 바꾸지 않는다.

원래 core, core tests, R048/R049, worker, 개입 정책, frozen_spec 및 최초 실패 evidence는 변경하지 않는다.
새 검산기를 smoke와 본실험의 공통 NativeVerifier에 연결한다.
실제 native candidate를 사용하는 회귀 테스트는 기존 오류 재현, 실패 관측 허용,
정상 proof 유지, 다시 봉인한 진단·채택 및 proof·identity 변조 거부를 확인한다.
이 테스트는 연구 표본으로 합산하지 않는다.

변경 후 manifest를 고정하고 단일 CMD 진입점 `Run-HCR-R050.cmd`로
selftest → smoke/audit → core regression 1회 → 본실험 → 독립 audit → 집계 일치 검사를 수행한다.
새 run만 새 고유 evidence 경로에 기록하며 최초 실패 디렉터리를 덮어쓰지 않는다.
이 문서 자체는 실행 성공이나 연구 결론을 주장하지 않는다. 결과는 새 run의 receipt와 원자료로 확인한다.
