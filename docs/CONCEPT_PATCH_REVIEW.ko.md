# 개념 보강 패치 — 소스 대조 결과

## 1. 실제 기준과 제한

사용자 지정 저장소는 `jaeseongs95/hierarchical-convergence-circuit`다. 이번 세션의 GitHub metadata/file 읽기 모두 404였고 공개 페이지도 취득하지 못했다. 현재 remote HEAD SHA와 새 커밋 내용은 확인하지 못했다. 따라서 이 패치를 '원격 최신 commit 확인본'이라고 부르지 않는다.

대신 실제 제공했던 R0.1 배포, R0.2 overlay, 기준선 overlay를 순서대로 합친 **127개 파일 기준 트리**를 읽었다. 이 조합은 사용자가 적용기/테스트/capture 로그로 적용 완료를 보고한 조합이다. 기준 manifest가 정확히 일치하는지 적용기가 사용자 로컬에서 검사한다. 차이가 있으면 쓰기 전에 중단한다.

| 입력 | SHA-256 |
|---|---|
| R0.1 source ZIP | c69ba87af591fa508f9d9cfd9b42e5515aef5206034e78b89e801f56e43d50b0 |
| R0.2 update ZIP | 1ef93af88705bb16c134eafb6ee6e98673d59065d9d9b8d6259c8c61c916fc66 |
| R0.2 baseline ZIP | efb574bf2183ff953b74c407918485a9bef715d9f6502d3cddb31072845d759f |

이번에는 동결 capture의 원시 파일을 전달받지 않았다. 사용자 로그가 말하는 capture 완료와 실제 원시 분석 수행을 구분한다. 원격 커밋·사용자 로컬 파일을 변경하지 않았다.

## 2. 앞선 개념 점검을 소스와 대조해 수정한 부분

| 앞선 누락 평가 | 실제 기준 트리 | 수정 방향 |
|---|---|---|
| 공통 primitive/cross-A가 없음 | `theory/core-hypothesis.md`, `evidence/claims.yaml` HCC-H01/H02, EXP-05가 존재 | 원 개념은 보존하고 로드맵·실험 gate에 다시 연결 |
| Decision/Explanation이 없음 | R0.1 `runtime.Engine.infer`에 readout/explanation 이벤트. R0.2는 value 다음 proof 호출. EXP-06 존재 | 없는 것은 R0.2의 별도 관측 시점과 비교. 기존 것을 새 구현으로 세지 않음 |
| 다중안정 기반이 없음 | `Dynamics.test_same_input_can_have_two_stable_states_in_explicit_unit_fixture` 존재 | basin dependence와 지속 trajectory switching을 구분 |
| semantic binding 효과 재현만 추가하면 됨 | `bind_path`의 semantic_id는 현재 객체 문자열이며 learned semantic matcher가 아님 | 먼저 재명명 불변성. 의미 학습 효과는 별도 조건 |
| control 함수 분리가 local 실행을 의미 | 중앙 `AdaptiveEngine`과 동기 `tick`의 reference 실행 | local/event-driven/hardware는 설계·backend gate로 명시 |

이는 계산 구조를 전면 교체할 근거가 아니다. 실제 부족한 명세·계측과 장기 목표를 연결하는 수정이다.

## 3. 이번 패치의 변경

**기존 엔진 보존:** `src/hcr`, `hcr.py`, `configs`, 기존 136개 시험 파일, `tools/r02_baseline`과 그 16개 시험은 바이트 단위로 그대로 둔다. engine version은 0.2.0이다. 기존 run이 기록한 30개 실행 파일 집합에 파일을 추가하지 않는다.

**문서 연결:** README의 현재 상태와 과거 배포 문구를 구별하고, ROADMAP을 최신 master roadmap·24개 개념 catalog에 연결한다. 원 658행 로드맵 snapshot과 `evidence/claims.yaml`은 변경하지 않는다. 원 EXP-03/04/05/06 draft의 본문을 보존한 채 구체화 절을 추가한다.

**오류/설명 보조 코드:** `tools/r02_concepts/check.py`는 concept→원문 ID→code/test definition/design→stage의 누락·stale anchor를 검사한다. 정의의 존재는 의미 검증이나 시험 통과가 아니다. `review.py`는 동결된 capture에서 외부 평가·수렴 상태·proof 가정의 당시 program 포함 관계를 읽는다. 알고리즘상의 원인을 자동 확정하지 않는다.

**미래 설계:** fixed pool/Plasticity I/F/local execution을 `architecture/substrate-contract.ko.md`의 B0/B1/B2로 유지한다. 여러 A 수준의 공통 primitive, cross-A 승격/재귀, EXP-06, 오류 taxonomy는 관련 버전의 횡단 검증으로 배치한다. 기존 후속 순서를 불필요하게 R0.8/0.9까지 늘리지 않는다.

## 4. 기존 기록으로 새 분석이 가능한 범위

review 도구는 baseline 수집기의 bundle·파일·chain·집계 검사를 재사용한다. capture 안의 Python 소스를 실행하지 않는다. 별도 readout/explanation event와 latency는 R0.2 기록에 없으므로 `false`로 보고한다. R0.2.1에서 새 trace schema로 추가해야 한다.

실행 signal graph와 proof DAG는 유형이 다르다. 탐색한 모든 가지가 최종 proof에 등장해야 한다고 요구하지 않는다. primitive로 설명을 전개해서 노드가 늘었다고 fabricated dependency로 분류하지 않는다. 이번 도구가 검사하는 것은 포함 관계와 기록의 가용 범위이며 정당화의 전체 논리 검산·실제 인과 경로 복원을 대신하지 않는다.

## 5. 완료/미완료

완료: 실제 기준 코드 열람, 앞선 오독 정정, 문서·추적 catalog·보조 도구/39개 계약 시험 작성, 배포 패치 구성. 구문·정적 anchor·해시·diff 적용 가능성 검사는 별도 STATIC_REVIEW.json에 수행 범위로 남긴다.

미수행: HCR import/실행, 기존 또는 신규 unittest 실행, 실제 capture 분석, EXP-09, R0.2.1 구현, 커밋·push. 사용자 실행 통과 수를 이번 세션에서 재실행한 것처럼 기록하지 않는다.
