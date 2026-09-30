# R053 구현 검토 기록

본 연구 실행 전에 생산기·파이프라인과 검산기를 분리해 구현했다.
main이 worker/pipeline/launcher를, r053_auditor가 numerical auditor와 해당 tests를 소유했다.
검산기 구현자를 최종 독립 감사자로 세지 않는다. r053_contract는 쓰기 없이
producer/pipeline이 설계 계약을 지키는지 검토했다.

## 검토와 반영

- 최초 producer는 level로만 feedback을 분류했다. 검토 후 spec의 directed partition을 전달하고
  중복·누락·여분 링크와 level 불일치를 실행 전에 거부하도록 보완했다.
- freeze에 전체 frozen spec fingerprint 검사를 추가했다. condition·mask·부모 hash·
  미측정 표식이 바뀐 matrix를 실행하지 않는다. auditor는 자체 spec fingerprint를 검사한다.
- worker 직전에 복사한 parents/의 정확한 inventory/hash를 다시 검사한다.
- 모든 R053 파일이 확정된 뒤 manifest를 생성한다. manifest 없는 중간 상태를
  실행 가능 release라고 보고하지 않는다.
- Coordinator는 auditor의 상태 갱신·최초 종료·counter·여섯 부모 실행 결속을 읽고,
  카운터 정수형 검사와 네 조건부 단순 효과, budget/oscillation synthetic 검사를 요청했다.
- 기존 R050 manifest의 schema는 candidate-release-v1임을 확인해 새 pipeline에 그대로 반영했다.
  과거 schema나 manifest를 변경하지 않았다.

계약 검토자의 표적 재확인에서 directed partition, 전체 spec preflight,
worker 직전 parent 재검사가 확인됐다. manifest 생성은 소스 마감 후 수행하는 완료 조건이다.

## 검증 경계

개발 중 표적 self-test를 수행했으며 본 연구 수치 선택·최적화에 쓰지 않았다.
검산기의 weakweak full fixture는 기존 조건의 synthetic replay 검사이며 새 독립 연구 표본이 아니다.
one-click에서 봉인된 최종 소스로 self-test·별도 smoke·core regression·연구 audit를 수행하고,
실제 횟수·통과/skip·경로와 결과는 RESULTS.ko.md 및 각 receipt에 남긴다.
필수 회귀는 최종 후보에서 한 번 실행한다. 예측이 틀린 경우 조건·마스크를 수정하지 않는다.
