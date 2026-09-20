# R052 구현 검토 기록

본 연구 실행 전에 development-orchestration으로 실행기와 독립 평가기 구현을 분리했다.
이 문서는 원자료 결과가 아니라 구현·검토 근거다.

## 선택과 책임

R051 토론의 두 후보 중 기존 core를 유지하는 배열/binding 불변성 대조를 선택했다.
feedback-link ablation은 새 kernel/config와 독립 재생 계약이 필요한 별도 후속으로 남겼다.
메인은 worker, pipeline, launcher, frozen spec, 계약 테스트와 통합을 맡았다.
r052_auditor는 audit와 비교기 테스트를 구현했고, r052_contract_review는 별도로
설계·worker·pipeline을 읽기 전용으로 검토했다. 후자는 audit 내부 검토나 전체 테스트를 수행했다고 주장하지 않았다.

## 본 실험 전 확인·수정

- 실제 native network의 drive는 모든 group을 담지 않는 sparse dictionary다.
  메인은 원 packet에서 e:0/e:1/goal만 있고 prefix drive는 생략됨을 확인했다.
  초안의 전체 group key 일치 조건을 알려진 group의 부분집합 조건으로 수정했다.
  없는 drive를 임의의 관측값으로 생성하지 않고 원 key만 구조 역할에 대응한다.
- 초안 비교기는 첫 차이에서 재귀 비교를 멈춰 maximum absolute difference가 전체 최대가
  아닐 수 있었다. 모든 하위 값을 비교한 뒤 결과와 최대값을 집계하도록 수정하고 회귀 테스트를 추가했다.
- network/state/candidate가 없는 경우 비교 불가(null)를 유지한다.
  빈 tick 두 목록이 같다는 이유만으로 trajectory 일치로 올리지 않는 테스트를 추가했다.
- 원자료 변형 없음, raw 좌표 일치와 role 좌표 일치의 구분, goal/prefix/proof/support 변조 검출,
  알 수 없는 좌표·구조 역할 거부, 정답/오답 채택과 보류의 집계 분리를 테스트한다.
- 별도 계약 검토의 manifest 부재 지적은 구현 도중의 알려진 미완료 항목이었다.
  모든 구현 파일이 확정된 뒤 manifest를 생성하고 source freeze 전에 검증한다.

이는 본 연구 결과에 맞춰 조건이나 판정 기준을 바꾼 작업이 아니다.
core, 과거 manifest/evidence, 동결된 4기준선·16기록, 개입 방식과 허용오차는 유지했다.
최종 실행·검증 결과는 새 run의 validation, result, analysis와 별도 결과 보고서에서 확인한다.
