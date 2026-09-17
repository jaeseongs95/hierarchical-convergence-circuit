# EXP-18 설계 — native readout 이후의 온라인 proof 채택

## 1. 출발점과 연구 질문

기준선은 `b6b57589e18cc4be97cea10515f90ffbf100218f`이고, EXP-17의 결과를 출발점으로 삼는다. EXP-17에서 `irrelevant_missing / legacy`는 지지 경로가 처음에는 미완성이었고, 추가 전개 후 완성되어도 native proof가 기존 비지지 경로를 유지했다. 동일 후속 상태의 `support_first` 선택은 raw 값을 바꾸지 않고 보류를 해제했다. `weak_negative`는 raw 값과 관측의 충돌이 남았고, `misleading_direction`은 관측 지지가 외부 정답을 보증하지 않는 대조였다.

이 문단은 이전 결과에 대한 설계 근거이며 새 EXP-18 결과가 아니다. 출처는 기준 커밋의 `HCR-Evidence/exp17/r036-first/analysis/summary.ko.md` 및 `analysis/records/t0064.json`, `t0016.json`, `t0112.json`이다. 실행 조건·입력·memory는 summary가 아니라 보존된 plan 및 seed에서 가져온다.

**새 연구 질문:** 사후 비교에서 회복 가능했던 proof를 실행 중 채택하도록 연결하면, 최초 판단을 보존하면서 최종 채택과 필요한 추가 전개가 어떻게 달라지는가?

## 2. 최소 비교

| Judgment prior | readout 이후 활성 proof 정책 |
|---|---|
| `legacy` | `native_saved` |
| `legacy` | `support_first` |
| `route_only` | `native_saved` |
| `route_only` | `support_first` |

기존 8개 기본 입력 각각에 위 네 조건을 적용한다. 총 32개의 fresh native session이며, 각 session은 같은 EXP-15 학습 memory/config의 복사본에서 시작한다. EXP-17의 계산된 Graph 상태는 재사용하지 않는다. 두 policy 비교에는 같은 session identity 규칙을 사용한다. 정책별 실행 순서는 사전 동결하며, 단일 실행의 wall time을 일반적인 속도 우위로 해석하지 않는다.

이번에는 재명명 변형, 새 topology, 추가 학습, measurement, restart, trial 중 prior 변경을 포함하지 않는다. 이전 실험에 없던 요인을 한꺼번에 넣지 않고 **온라인 채택 경계**만 먼저 시험하기 위한 선택이다. 새 topology 일반화와 자율 action 선택은 후속 실험이다.

8개 입력은 고정된 진단 case 집합이다. prior/policy/readout/world를 독립 표본으로 세지 않으며, 확률 표집이나 통계적 독립성이 확보되었다고 주장하지 않는다.

## 3. 개입 위치

```text
기존 AdaptiveSession begin / advance
    ↓ 실제 readout_ready
기존 capture_candidate → 원 native finish 판단/proof 보존
    ↓ 공개 view 투영
사전 지정한 R035 selector 한 개 실행
    ↓
원 판단과 분리된 adoption
    ├─ 지지된 출력 채택 → 실제 실행 종료
    ├─ selector 예산 종료 → 별도 종료 사유
    └─ 보류 → native failure/frontier/계산 예산 검사
                  ↓ 가능할 때만
          continue_dependency / advance
```

EXP-17의 선택 결과는 후속 전개를 제어하지 않았다. EXP-18에서는 그 결과가 제어에 사용된다. 그러나 `src/hcr`와 기존 `finish`는 그대로이며, 선택한 proof를 원 native packet에 다시 써 넣지 않는다. 별도 정책이 만든 proof를 native 자체 출력인 것처럼 표기하지 않는다.

`support_first`는 기존 R035 구현을 그대로 사용한다. 현재 workspace에서 완성된 경로만 조사하며 활성화와 관측 지지 조건을 만족하는 경로를 선택한다. raw `True`를 `False`로 바꾸지 않는다. raw가 `False` 또는 `None`이면 기존 proof를 통과시키는 기존 계약을 유지한다. 새 negative proof 검색기나 진리 oracle을 추가한 구현이 아니다.

원 native proof도 먼저 만들어지므로, 이 구현은 native proof 생성 비용을 제거한 최적화가 아니다. 온라인 채택의 효과와 추가 비용을 측정하는 연구 장치다.

## 4. 사전 예측과 대조

**경로 미완성 대조:** 지지 경로가 아직 workspace에 없으면 선택만으로 새 경로를 만들어 회복하지 않아야 한다.

**완성된 지지 경로:** raw 값이 같고 지지·활성화 조건이 충족된 기존 경로가 생기면 `support_first`는 그 proof를 채택할 수 있어야 한다. 최종 회복은 trial 결과로 기록하며 native 통합 합격 조건에 정확도 향상을 강제하지 않는다.

**Raw 충돌 대조:** `weak_negative`형의 잘못된 raw 값은 같은 값의 proof 선택만으로 뒤집히지 않아야 한다. prior별 결과 차이는 같은 실험 안에서 분리 관찰한다.

**정보 부족 대조:** 관측 정보가 판별에 부족하면 근거 없는 확정을 만들지 않아야 한다.

**잘못된 관측 대조:** 현재 관측이 잘못되었지만 내부적으로 충분한 지지를 제공하면, 선택 개선 뒤에도 외부 오답이 남을 수 있다. 선택기의 관측 지지 성공과 외부 정답은 별도로 평가한다.

## 5. 예산과 비용

초기 최대 advance 64회 / 초기 kernel ticks 65,536. 최초 readout 이후 최대 advance 8회 / 추가 ticks 2,048. 각 advance 전에 기존 `tick_bound`의 최악 상한을 예약한다. 남은 예산보다 큰 작업은 시작하지 않으므로 실제 사용량이 한도보다 작아도 종료할 수 있다.

선택 예산은 기존 기본값을 유지한다. readout당 최대 ranked paths 64, path checks 64, edge checks 256, proof nodes 128. 이 수치는 엔진이 해당 규모의 topology를 지원한다는 선언이 아니라 selector의 상한이다. 기존 입력 계약은 edge 8개 이하, 완성 경로 4개 이하, 경로 길이 4 이하 범위를 유지한다.

Native ticks는 session의 최종 누적값을 한 번만 합산한다. 최초/마지막 readout의 누적값을 다시 더하지 않는다. 선택기의 경로 검사, edge 검사, proof 생성/재사용, 원 native finish proof 생성 수를 별도 단위로 기록한다. native capture 내부의 미계측 scan은 `null`이며 0이 아니다. 단위가 다른 비용을 하나의 숫자로 더하지 않는다.

Native fork/capture 및 selector의 시간 원자료는 유지되지만, 직렬화·보존·Python wrapper overhead가 섞인 trial wall time을 순수 kernel 성능으로 해석하지 않는다. 독립 audit의 replay 비용은 온라인 task 비용이 아니다. 기존 학습 비용도 새 task 비용에 다시 넣지 않는다.

## 6. 원자료와 독립 검증

실행 모듈은 case 라벨, world 정답, 식별 가능성 판정 결과를 받지 않는다. 이름에 따른 조건 분기는 없다. 원자료 운반 계층에는 평가용 upstream 문서가 존재하지만 실제 `OnlineTrial`에 전달되는 값은 observation/config/memory/prior/policy/예산뿐이다.

`attempts.jsonl`은 각 작업을 flush/fsync하고, selector 호출 **전에 원 native candidate 전체**를 기록한다. 결과가 잘못되어도 자동으로 ID/parent/dependency를 고치지 않는다. 예상된 보류는 정상 연구 데이터이고, schema/parsing/runtime/audit 오류와 구분한다.

검산 경로는 다음과 같다.

```text
기존 packet_states / verify_candidate
    → native 상태·계보·finish branch 독립 재생
기존 R035 audit_result
    → 공개 view와 선택 순서·proof DAG·가정·D_DAG·비용 검산
신규 control_audit
    → 선택 이후 실제 continue/advance/stop 및 예산을 별도 구현으로 재계산
독립 world 평가 / report
    → 외부 정답, 보류, paired 차이, 비용 집계
```

검산에서 `OnlineTrial.run`, 생산 `run_policy`를 재호출하여 일치 여부를 판정하지 않는다. 공유한 간단한 hash/파일 계약과 기존 독립 native auditor는 provenance에 명시한다. EXP-15 학습 seed의 독립 재생도 재사용한다.

첫 readout과 마지막 readout, terminal adoption, terminal pending의 ready 여부를 구분한다. 최초 readout 전에 예산이 끝나면 가짜 보류 candidate를 만들지 않는다. 마지막 readout 이후 계산이 미완성으로 끝난 경우에도 그 이전 readout을 terminal 결과로 위장하지 않는다.

## 7. 실패와 반증을 읽는 법

Audit 통과는 원자료·계보·제어·proof·비용이 계약과 일치한다는 의미다. 정답이나 개선을 의미하지 않는다. support-first가 회복하지 못하거나 기존 정책보다 채택이 줄어도, 유효한 원자료라면 그대로 요약한다.

첫 native view의 policy 간 일치와 공통 readout prefix를 보고한다. 불일치가 있으면 selector 개입 이전의 교란 또는 실행 차이를 먼저 조사한다. 실제 engine 동작이 예측과 다르면 원인을 자동으로 '학습 편향'으로 이름 붙이지 않는다.

실행 실패 시 `failure.json`과 부분 원문을 보존하고 중단한다. JSON으로 표현 불가능한 부분 상태는 보정하지 않고 repr 별도 파일과 직렬화 오류를 남긴다. audit 실패는 종류와 traceback을 따로 기록한다. 실패 폴더에 재실행하거나 덮어써서 최초 실패를 숨기지 않는다.

## 8. 현재 주장 범위

검증 대상은 **동결 memory를 사용하는 작은 native toy engine의 온라인 proof 채택 정책**이다. native kernel 내부 선택기 교체, 회로 학습, 자율 repair 정책 학습, 새 topology 일반화, LLM hidden state, 인간 뇌 기제를 이 실험의 성과로 주장하지 않는다.

R037 배포 환경의 unit/selector self-test와 사용자가 실행할 실제 native EXP-18 원자료를 같은 연구 증거로 합산하지 않는다.
