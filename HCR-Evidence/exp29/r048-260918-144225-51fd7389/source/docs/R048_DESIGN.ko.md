# R048 / EXP-29 — 관측 강도에 따른 초기 상태 정밀도 대조

## 결론이 아니라 사전 실험 설계

기준선은 `b10f571eb02e296b2ccb3f16eaf727da7d0e4d45` (`R047_EXP28 commit`)이다. EXP-28의 정상 +0.92 조건에서 edge/prefix/both 실제 상태 전달은 33/31/29 ticks, 같은 mask의 fixed 0.99도 33/31/29였다. 엄격한 actual < fixed 가설은 여섯 비교에서 실패했지만 궤적까지 같지는 않았다.

이번 질문은 **그 동등성이 강한 양성 관측에 한정되는지, 공유 근거의 강도가 바뀌면 정밀한 A 상태의 추가 이득 또는 불리함이 나타나는지**다. 고정 잠재 연결 공간·가소성·문맥 경쟁을 덧붙이지 않고 이 대안 설명을 먼저 분리한다.

## 동결 조건

공유 A 근거의 score는 `0.02, 0.10, 0.25, 0.50, 0.75, 0.92, 1.00` 일곱 값이다. 새 조건의 수치 실행 전에 정했으며 결과를 본 뒤 구간·fixed 값·판정 기준을 조정하지 않는다. 이는 native 모델의 관측 강도 값이며 인간의 확신도나 통계적으로 보정된 확률이 아니다.

A는 `u→v→w`, B는 `u→v→w→z`다. 같은 block에서는 A와 B의 공유 두 edge의 ID, endpoint, score가 동일하다. B에서 추가되는 `w→z` score만 모든 block에서 0.92로 고정한다. 모든 세계 edge는 별도의 plan world에서 True로 고정한다. runtime은 world와 강도 조건 이름을 받지 않고 공개 observation만 받는다.

R047의 7개 처리와 코드 경로를 그대로 사용한다.

| 처리 | 이전 edge 초기값 | 이전 prefix 초기값 |
|---|---|---|
| cold | 0.5 | 0.5 |
| carry_edge | 실제 A 상태 | 0.5 |
| carry_prefix | 0.5 | 실제 A 상태 |
| carry_both | 실제 A 상태 | 실제 A 상태 |
| fixed_edge | 0.99 | 0.5 |
| fixed_prefix | 0.5 | 0.99 |
| fixed_both | 0.99 | 0.99 |

새 edge, 새 prefix, 새 goal은 0.5다. 안정화 이력은 0부터 시작한다. 이전 state를 clamp하지 않고 기존 수렴식으로 다시 갱신한다. 초기값을 정하는 mask와 source packet, binding/dependency 검증은 actual과 fixed에서 동일하다. 두 기존 edge의 강도는 함께 바뀌므로 이들 개별 기여는 이번에 분리하지 않는다.

7강도 × 2 ID 배치 × 7처리 = B 98조건. A는 강도×ID별 한 번씩 총 14회 수행하여 공유한다. 총 native query는 112개다. A/B와 여러 분석에서 같은 원자료를 재사용해도 독립 표본으로 중복 계산하지 않는다. 일관된 ID 재명명은 독립 무작위 반복이 아니다.

0.92는 기존 EXP-28 조건을 재확인하는 anchor다. 그 동등성이 재현되어도 신규 독립 발견으로 세지 않는다. 대상·근거 변경 guard 대조는 새 연구 변수로 추가하지 않고 부모 검증과 기존 self-test에서 회귀검사한다.

## 가용성·실패·판정

낮은 강도에서 A가 올바른 양성 결과를 채택하지 못하면 기존 gate가 packet 생성을 거부한다. 해당 A를 다시 풀거나 지우지 않는다. 그 block의 B 7처리도 모두 한 번씩 실행한다. 미적용에 의해 모두 cold로 돌아간 결과를 actual/fixed 정밀도 동등성의 증거로 세지 않는다.

효율 비교의 가용성은 A의 올바른 양성 채택, actual/fixed 양쪽 B의 올바른 채택, 양쪽 gate 적용, 예산 종료 없음이다. 이 조건을 만족하지 않으면 Δticks 자체는 기록하지만 효율 가설은 `not_evaluable`로 남긴다. raw 값의 정확도, proof 지원, 채택 정확도, native convergence, budget termination은 별도 필드다. 강도에 따라 오답·unsupported가 나오면 그대로 보존한다.

`spec.py`에 고정한 가설은 다음과 같다.

- H_precision_at_cell: 비교 가능한 같은 강도·ID·mask에서 actual ticks < fixed ticks. 같거나 더 크면 해당 예측은 falsified.
- H_outcome_at_cell: actual과 fixed의 raw value·adoption이 동일. 정확도와는 별개이며 예산 종료 조건은 판정불가.
- H_ID_native: 같은 강도·처리에서 일관된 ID 재명명 후 native 계수·수치 궤적·결과가 동일.
- H_gate: A의 양성 채택이 없으면 packet·state 전달이 없음.

전체 조건이 통계적으로 독립이라는 가정이나 p-value는 사용하지 않는다. 일부 셀의 결과를 보편적 우위로 요약하지 않는다. EXP-27 전체 H_ID 실패와 EXP-28 정밀도 가설의 여섯 실패는 기존 기록 그대로 유지한다.

## 궤적과 비용

정해진 checkpoints `1, 4, 8, 16, 24`에서 두 실행에 실제 존재하는 tick만 비교한다. 중간 group의 최대 절대 차이, goal 차이, residual 차이와 실행된 공통 구간의 최대 차이를 기록한다. 먼저 끝난 실행을 연장하거나 마지막 상태를 복제하여 값을 채우지 않는다. 없으면 null과 이유를 기록한다.

D_DAG는 기존 독립 proof 검사기의 펼친 parent 관계로 검사한다. ticks, group updates, signals, 경로 검사, dependency/descriptor 검사, state read/write, bytes, proof 생성량, wall time은 별도 단위다. native와 bridge의 proof 생성 계수는 같은 작업의 별칭이므로 더하지 않는다. 에너지·peak memory는 null이다. wall time에는 상세 기록/fsync가 포함되므로 실행시간 효율을 판단하지 않는다.

기존 전체 A packet을 계속 사용한다. fixed 값 대체가 A 실행, binding, 저장량, 전송량을 없앴다는 주장은 하지 않는다.

## 구현 및 독립 검산

기존 native 8파일과 R047의 runtime, spec, storage, audit를 checksum 고정하여 그대로 호출한다. R048은 조건 생성, 실행 registry, 비교 지표, artifact 전달 계층만 추가한다. R047 원자료 record 스키마는 내부에 그대로 보존하고 바깥 wrapper만 EXP-29 query로 식별한다.

기존 auditor는 producer/native를 import하지 않고 BFS, 별도의 tanh 갱신식, proof term 규칙으로 재계산한다. 새 evaluator도 producer를 import하지 않는다. 전체 tick·정지 조건·초기값 mapping·source hash·proof·event 순서를 검사한 뒤에만 집계한다. 감사 통과와 가설 지지는 서로 다른 값이다.

## evidence의 줄바꿈 문제

원본 EXP-28 폴더는 수정하지 않는다. 기준 commit의 bundle_manifest Git blob을 먼저 고정하고, 새 run의 `basis/exp28/`에 복사본을 만든다. 차이가 있으면 LF/CRLF 변환만 시도하고 **변환 결과의 SHA256이 원래 manifest의 해시와 정확히 일치하는 경우에만** 원본 bytes로 복원한다. 변환 전후와 파일별 방법을 `parent_byte_recovery.json`에 기록한다. 원본 raw 값을 계산으로 생성하거나 누락 로그를 재작성하거나 manifest 해시를 교체하지 않는다. 원본 사본은 기존 R047 verify로 전체 재검산한다.

새 EXP-29 evidence에는 `-text -filter -ident`를 적용하고 working-tree-encoding을 해제한다. 모든 파일에 실제 적용되는 Git attributes, ignore 상태, 정상 clean 처리 후 Git blob과 원본 bytes의 동등성을 읽기 전용으로 검사한다. 사용자 Git index, commit, push는 변경하지 않는다. 이것은 현재 작업트리의 게시 준비 검사이며, 아직 수행하지 않은 원격 push의 검증으로 부르지 않는다.

완성 bundle의 source snapshot과 부모 사본을 포함해 모든 파일의 byte hash를 봉인한다. 봉인 이후의 검사/ZIP receipt는 폴더 밖에 기록한다. ZIP을 다시 열어 목록과 모든 bytes를 검사한다. `VERIFY_BUNDLE.cmd`로 압축 해제본을 다시 검증할 수 있다.

## 근거

기준 source: `jaeseongs95/hierarchical-convergence-circuit`, commit `b10f571eb02e296b2ccb3f16eaf727da7d0e4d45`.
부모 run: `HCR-Evidence/exp28/r047-20260918T134449_415062Z-82c4ceae`.
직접 연구 근거: 이 세션 EXP-28 분석의 성분별 효과·fixed 0.99 동등성·궤적 차이·배포 byte 불일치.
추가 설계 선택: 관측 강도 7값, 고정 checkpoints와 비교 가용성 규칙. 이들은 새 소스의 동결 조건이며 이전 실험의 관찰 결과가 아니다.
Git 동작은 공식 `gitattributes`의 text/encoding/filter 규칙과 `git-hash-object`의 clean-filter 출력 검사에 따른다: https://git-scm.com/docs/gitattributes 및 https://git-scm.com/docs/git-hash-object.
