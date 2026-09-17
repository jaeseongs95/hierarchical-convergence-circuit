# R0.2.1 — dependency 경계의 Session / Snapshot / Restore / Resume

## 1. 기준과 범위

기준 소스는 `main`의 `2e67f71804b172673212822291b15885ca64f729`(분석결과 commit)이다.
R0.2의 오수렴·prior·학습·경로 선택·비용 집계 의미를 유지하면서 진행 중 계산을 저장하고 다시 시작한다.
EXP-09의 복구 결과는 기존 60회 기록이며, 이 구현의 개발 검증을 그 연구 표본에 추가하지 않는다.

유지하는 정책: 같은 prior 전달, 길이 2·3 motif, 사용된 회로만 약화, 거짓 출력의 정답에서 예외회로를 새로 학습하지 않음,
forced revision에서는 circuit bypass, 기존 부정 판단의 dependency coverage, 동일한 예산·보류 처리.
다음 정책 변경은 별도 실험이다: routing-only prior, 오류 binding 제약, negative exception memory, pool 최적화.

## 2. 실행 단위

`AdaptiveEngine.infer()`의 원래 반복문을 `begin → advance* → finish`로 분리했다.
`infer()`는 그 동일 API를 끝까지 수행하므로 실행 알고리즘이 두 벌 존재하지 않는다. R0.1 Engine 경로는 보존한다.

| 호출 | 계약 |
|---|---|
| `begin(observation, mode, revision_of=...)` | 기존 관측·모드·revision 권한을 검사하고 workspace를 생성 |
| `advance()` | frontier 하나의 dependency 확장/종료 또는 예산 중단까지 실행. 해당 pool/판단 settle은 이 호출 안에서 끝남 |
| `finish()` | 준비된 값을 바꾸지 않고 기존 primitive proof를 복원한 뒤 decision을 등록 |
| `complete()` | session의 남은 advance와 finish를 한 번에 수행 |
| `feedback()` | 판단 뒤에만 기존 학습 규칙을 적용. 진행 중에는 거부 |
| `request_revision()` | 외부 오류 feedback과 기존 권한 범위에 따라 요청. 기존과 같은 조건에서만 허용 |

`running → readout_ready → idle`의 phase를 구분한다. readout_ready에서는 계산된 value·state가 있지만 decision/proof는 아직 등록하지 않았다.
이는 판단 준비와 정당화 생성의 프로그램 경계다. 인간 직관의 원인 경로나 자연어 설명 동일성을 검증한 것이 아니다.
기존 R0.2 decision 이벤트를 재작성하거나 과거 실행에 새 readout 시간을 덧붙이지 않는다.

## 3. 시간과 identity

- session ID는 세션의 identity다.
- generation 0은 init. 성공한 begin/advance/finish/feedback/request_revision 호출마다 증가한다. 요청할 것이 없어 None이 반환된 호출도 기록한다.
- kernel tick은 종료된 signal network 내부 갱신 수다. generation으로 대체하지 않는다.
- observation revision은 허용된 새 관측, memory version은 검증된 학습 변경을 뜻한다.
- save/load는 generation, node ID, decision ID, engine trace count를 증가시키지 않는다.

별도의 transition journal은 각 generation의 연산, 인수 digest, 이전/다음 state hash, 부모 transition hash,
연결된 engine event 구간을 보유한다. engine trace와 transition journal은 정당화 proof DAG가 아니다.
일반 JOIN/소멸/graph rewrite는 아직 없으므로 그런 전이를 구현한 것처럼 이름만 붙이지 않는다.

## 4. 저장하는 실제 상태

`ExecutionState`는 현재 관측, 모드, revision_of, attempt, decision ID, memory hash/version, 설정 서명, 세 가지 실행 스위치,
누적 비용, frontier·완료 경로·known 집합·next_node, 역할 binding·AppliedCircuit,
현재 mismatch, 마지막 program/digest, 종료된 activation/state, convergence, 준비 value, settled_paths, failure_reason을 보관한다.

session에는 이와 함께 memory 문서, _held의 기존 decision과 hash, episode별 attempt 횟수,
처리한 feedback, 발급/소비 중인 revision request, 전체 engine event 및 transition journal을 담는다.
새 프로세스에서 이미 처리한 확장·pool·학습을 생산 함수로 다시 실행해서 재생하는 방식이 아니다.
검산 이후 자료구조를 직접 재구성하여 남은 작업부터 수행한다. pickle이나 캡처 안의 Python 소스 실행을 사용하지 않는다.

체크포인트는 `{schema, document, sha256}` 형식의 JSON이다. schema는 `hcr-session-checkpoint-r021-v1`.
source hashes는 현재 `src/hcr/*.py`의 CRLF/LF 정규화 hash이며 실행 의미·검산 구현이 달라진 소스로 복원하지 않는다.
기존 R0.2 run의 raw source hash 계약을 바꾼 것은 아니다. 기존 run은 당시 source/capture와 보관한다.

## 5. 원자성과 재개 권한

`AdaptiveSession`의 각 전이는 복사된 in-memory engine에 적용되고 완전히 성공한 뒤 commit된다.
예산 오류·binding 오류·예외가 나면 기존 session의 memory/workspace/trace는 그대로다.
단일 writer·명시적 checkpoint 경계를 위한 참조 구현이다. 이 복사 자체는 성능 최적화가 아니다.

파일 저장은 같은 디렉터리의 임시 파일을 쓰고 fsync한 뒤 hard-link로 배타적 공개한다.
기존 파일은 덮어쓰지 않는다. hard-link를 지원하지 않는 파일시스템에서는 오류를 내며 덮어쓰기 방식으로 후퇴하지 않는다.
Linux 작성 환경에서 실행했고 Windows/NTFS의 실제 실행은 사용자 검증 대상으로 남긴다.

`load(..., expected_ref=...)`로 session/generation/state/transition 기준을 고정할 수 있다.
expected_observation, expected_memory_hash, expected_program_digest 검사가 추가로 가능하다.
CLI의 `--expect-sha256`는 외부에 보관한 정확한 checkpoint 문서 해시를 검사한다.
서명 없는 hash는 외부 인증이 아니며, 기준 참조를 제공하지 않으면 유효한 이전 checkpoint 자체를 '최신이 아님'이라고 알아낼 수는 없다.
같은 checkpoint를 다른 프로세스에서 의도적으로 분기하는 것을 글로벌 잠금으로 막지 않는다.
한 세션 내부에서 이미 소비한 feedback/revision을 재소비하는 것은 거부한다.

프로세스가 kernel 한가운데서 죽었을 때 그 순간까지 복구하는 기능은 아니다. 마지막 성공 checkpoint 이후 연산은 다시 수행해야 한다.
처리 중 exception의 저장과 운영체제 crash-consistency 전체 보장은 구별한다.

## 6. 검산

`evaluation/session_audit.py`는 생산 runtime/state/sessions/dynamics/activation/expansion/learning/workspace를 실행하지 않는다.
기존 독립 평가 helper를 사용하여 event chain, binding scan, 후보 순위, macro 내부 side branch, frontier·node identity,
수치 tick, convergence, 판단값, proof 유효성, memory 변경, observation 권한, 누적 카운터를 재계산한다.
각 generation의 실제 state hash를 계산한 뒤 마지막 snapshot과 대조하므로 외피 SHA만 새로 계산한 변조도 검사한다.

공유 구성요소: JSON/자료 계약, memory structural certificate loader, 외부 proof/reference validator,
R0.2 독립 audit helper. 따라서 제삼자 인증이거나 모든 구현이 완전히 독립된 것이라고 표현하지 않는다.
seed memory와 외부 feedback의 진실성은 session audit의 판정 대상이 아니다. EXP-10에서 별도의 world 평가로 검사한다.

## 7. 비용

기존 primitive proof D, expansions, binding, pool/decision tick·signal 카운터는 그대로 누적한다.
snapshot 때문에 완료된 연산을 누락하거나 생산 엔진 카운터에 재검산을 더하지 않는다.
`cost.wall_seconds`는 begin/advance/finish의 실제 계산 구간 누적이며 중단·디스크·session 복사·독립 검산 시간은 제외한다.
따라서 R0.2.1 wall_seconds는 end-to-end 비용이나 속도 개선의 지표가 아니다.
`checkpoint_io.jsonl`에는 save/load의 bytes와 관리 wall time(직렬화·검산 포함)을 별도로 기록한다.
현재 transaction deepcopy 비용은 항목별 분리 측정하지 않는다. 이 한계까지 포함해 참조 구현의 효율을 해석한다.

## 8. 증거 저장 위치

새 session/EXP-10 도구는 저장소 내부의 `HCR-Evidence` 하위 새 경로를 정식 허용한다.
`src`, `tests`, 원본 입력 경로, 기존 결과 덮어쓰기, symlink/junction 경유는 거부한다.
완료 manifest나 FAILED.json이 있는 증거 폴더 내부에 새 파일을 추가하지 않는다.
외부 새 폴더도 허용하지만 강제하지 않는다. 이 변경은 과거 recovery/collect 도구의 경계 규칙을 소급 변경하지 않는다.
