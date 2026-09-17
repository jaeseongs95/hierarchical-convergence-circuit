# EXP-19 / R0.3.8 — proof 선택 효과와 조기 종료 효과의 분리

## 결론과 출발점

기준선은 `main`의 `d25f4bd4e3bd8c8aae763e3ee6542dbfd590900f`다. 출처는 해당 커밋의 `HCR-Evidence/exp18/r037-first/analysis/conditions.csv`, `summary.ko.md`, `records/t0016.json`, `records/t0017.json`, raw `t0017.json`이다.

EXP-18에서 `irrelevant_missing / legacy`의 온라인 support-first는 추가 전개 후 기존 비지지 proof 대신 지지되는 대체 proof를 채택했다. Native-saved와 support-first의 해당 실행은 모두 102 native ticks였고 전체 16개 비교 쌍에서 ticks가 같았다. 지지 경로가 확보된 때에는 전체 Graph가 이미 완성돼 있어, 미탐색 가지를 생략하는 효과를 그 결과만으로 구별할 수 없었다. 이 문단은 **이전 evidence에 근거한 설계 출발점**이며 신규 EXP-19 결과가 아니다.

새 연구 질문은 다음과 같다.

> 같은 지지 경로를 같은 선택기로 채택하더라도, 선택 결과를 실제 계산 종료 전에 적용하는가에 따라 추가 전개량이 달라지는가?

이것은 기존 native 엔진의 계산 규칙을 고치는 실험이 아니다. R037의 원 엔진/온라인 제어기를 그대로 호출하고 새로운 실험군과 독립 계측을 추가한다.

## 최소 비교: 세 실험군

| 실험군 | 실제 native 계산의 종료 기준 | Support-first 적용 시점 | 구별하는 효과 |
|---|---|---|---|
| `native` | R037 `native_saved` | 미적용 | 기존 기준선 |
| `posthoc_support` | 위와 동일 | 기존 실행이 종료된 뒤 현재 terminal readout에 한 번 | proof 선택에 따른 채택 변화 |
| `online_support` | R037 `support_first` | 매 실제 readout에서 적용하여 채택 시 종료 | 선택 시점에 따른 추가 전개 생략 |

각 실험군은 같은 관측·config·memory에서 시작하는 **별도의 fresh native session**이다. `native`와 `posthoc_support`는 같은 R037 native-saved 계산 흐름을 실행한다. `posthoc_support`가 대체 proof를 찾더라도 이미 수행한 native 계산을 소급해서 절약했다고 처리하지 않는다. `online_support`도 새로운 자체 구현이 아니라 검증 대상 기준선에 있는 R037 온라인 support-first를 재사용한다.

두 prior는 `legacy`, `route_only`다. 같은 입력/prior 안에서는 세 실험군의 session identity도 같다. 기존 native session 이름이 `online-r037-...`인 것은 동일 제어기 재사용을 표시한 것이며 R038 버전 누락이 아니다.

## 입력: 기존 8개 대조 + 신규 6개 topology

기존 8개 관측과 평가 world, 학습 seed는 EXP-18의 원 입력 출처에서 그대로 가져온다. 요약문을 읽고 seed를 새로 만들어내지 않는다. EXP-15의 6회 학습으로 만들어져 EXP-18에서 사용한 동일 frozen memory/config를 재사용한다. 새 학습·모델 다운로드·외부 LLM 호출은 없다.

신규 6개는 다음 유한 grid다.

- 지지 가지: 길이 2, score `0.92, 0.92`.
- missing 가지: 길이 2, score `null, 0.92`.
- 나머지 가지: 길이 2·3·4 중 하나. 첫 edge는 `-0.92`, 이후는 `0.92`.

각 길이에 대해 공개 edge 배열 순서를 두 가지로 둔다. `early`는 지지 가지 → missing 가지 → 나머지 가지 순서이고, `late`는 나머지 가지 → missing 가지 → 지지 가지 순서다. 이름은 의도한 전개 순서를 나타내는 **설계 라벨**일 뿐, 엔진에 그 순서대로 선택하라고 지시하는 정보가 아니다. Trial runtime에는 case/cohort/manipulation/world를 전달하지 않고 관측, config, memory, prior, 실험군, 예산만 전달한다.

각 관측에는 경로 3개, edge 6·7·8개, 최대 경로 길이 2·3·4개가 있다. 기존 엔진/selector의 edge 8개·경로 4개·길이 4개 범위 안이다. 계획 단계의 topology 범위 검사는 score나 외부 world를 사용하지 않고 결과를 native workspace에 전달하지 않는다.

신규 입력은 `spec.py`의 고정 정의로 만들어지며 native 결과를 보고 성공 입력만 골라내지 않는다. 실제 native가 의도한 순서를 보이지 않거나 목표 경계가 만들어지지 않아도 입력을 버리지 않는다. Edge 순서는 열거/slot/binding에도 영향을 줄 수 있으므로 `early`와 `late` 차이를 독립적인 인간 사고 깊이 효과로 부르지 않는다. 주된 비교는 **각 동일 입력 내의 세 실험군**이다.

기존 입력 8개 + 신규 입력 6개 = 기본 입력 14개. 2개 prior × 3개 실험군으로 fresh native trial 84개를 실행한다. 기본 입력, prior, 실험군, readout, world를 서로 독립적인 문제 표본으로 합산하지 않는다. 실행 순서는 case/prior에 따라 세 실험군을 순환 배치하여 사전에 고정한다. 반복 wall-time 벤치마크는 아니다.

## 개입과 관찰을 분리하는 기준

평가기는 실제 native event prefix에서 각 readout 시점의 frontier 수를 별도로 재계산한다. 완성 경로 중 관측 지지와 activation 조건을 만족하는 경로를 검사하고 다음을 구분한다.

`지원 경로 사용 가능`: raw 값이 True이며 완성된 지지/activation 적격 경로가 존재한다.

`조기 채택 기회`: 위 조건에 더하여 미탐색 frontier가 남아 있다.

`차등 기회`: 위 조건에 더하여 같은 native readout은 보류하고 있다.

전체 topology에 지지 경로가 존재하는 것과 현재 workspace에 그 경로가 완성된 것은 다르다. 이 진단은 **실행 후 독립 evaluator에서만** 수행하며 controller 입력으로 사용하지 않는다.

## 사전 예측과 해석

지지 경로가 미완성인 readout에서는 support-first만으로 새 경로를 만들어내지 않아야 한다. 추가 전개가 필요하다.

차등 기회가 실제로 발생하고 충분한 선택 예산이 있다면 온라인 실험군은 그 자리에서 별도 proof/adoption을 채택할 수 있다. 같은 지지 출력을 native-saved 종료 후 사후에 채택하는 방식에 비해 이후 전개를 생략할 수 있다. 비교할 것은 terminal 누적 ticks, native advance 수, expansion 수이며 지지 출력 및 외부 평가도 함께 확인한다.

기회가 발생하지 않으면 “조기 종료 가설이 반증됐다”가 아니라 이 입력/엔진 조건에서 그 효과를 판별할 경계가 만들어지지 않았다고 기록한다. 기회가 발생해도 실제 ticks가 줄지 않거나 결과가 달라지면 그대로 보고한다. `late`에서 기회가 없어질 것이라는 예상 역시 native 실행으로 관찰할 대상이지 성공 판정의 전제가 아니다.

`weak_negative`처럼 raw 값 자체가 관측과 충돌하는 경우의 값 반전, `critical_missing`/`critical_zero`의 추가 관측, `misleading_direction`의 외부 관측 오류 수정은 포함하지 않는다. 지원된 오답으로 더 빨리 종료한 경우에는 올바른 정답을 보존한 계산 절감과 구분한다.

## Paired 검증과 비용

첫 native view 일치, native/posthoc의 전체 의미 trace 일치, online의 native trace prefix 일치를 보고한다. Trace 비교에서는 시간과 그로부터 달라지는 봉인 hash만 제외하고 실제 event·경로·activation·계수는 유지한다. 개별 hash chain의 유효성은 별도 native auditor가 검사한다.

`절감 ticks = posthoc native ticks − online native ticks`다. 음수도 그대로 보존한다. 같은 최종 지지 출력인지, 모든 선언 world에서 정답인지, paired 실행이 비교 가능한지를 함께 기록한다. 기회 발생 입력을 사후에 전체 표본에서 빼지 않으며 기회 여부와 층화 결과를 전체 보고서에 남긴다.

Native ticks는 각 session의 최종 누적값을 한 번만 집계한다. readout마다 반복된 누적값을 더하지 않는다. 원 native finish proof 생성, 온라인 selector의 경로/edge 검사와 proof 생성·재사용, 사후 selector의 추가 검사와 proof 비용을 각각 분리한다. Native capture 내부의 미계측 scan은 `null`이다. 다른 단위들을 하나의 총비용/전력량으로 합하지 않는다.

원 native proof는 여전히 먼저 생성된다. 이 구현은 native proof 생성 제거 최적화가 아니다. Serializing, copying, journal fsync, Python wrapper 시간이 실제 wall time에 포함된다. 따라서 native ticks 절감과 시스템 전체의 실행 시간/전력 절감을 동일시하지 않는다.

## Terminal readout 계약

사후 선택은 native 실행이 끝난 실제 terminal 경계와 generation이 일치하는 readout에만 적용한다. 최초 readout이 없으면 가짜 후보를 만들지 않는다. 마지막 readout 이후 계산 도중 예산이 소진되어 pending이 미완성이라면 그 과거 readout을 최종 후보로 사용하지 않는다. 엔진 실패가 남은 경계에서도 사후 채택하지 않는다.

현재 readout-ready 경계에서 추가 계산 예산이 부족해 중단한 경우에는 이미 존재하는 그 readout에 사후 선택을 적용할 수 있다. 이 경우에도 기존 계산 종료 이유는 별도로 보존한다. 선택 예산 실패를 숨기려고 native 출력으로 자동 fallback하지 않는다.

## 가정 수 정정

기존 R035 auditor의 `supported_assumptions`는 Boolean 지지 목록의 `len`이어서 실질적으로 검사 수였다. R038은 이전 소스·원자료·analysis를 바꾸지 않고 신규 분석에서 다음을 분리한다.

```text
assumptions_checked     = 검사한 가정 수
supported_assumptions   = 지지 여부가 True인 가정 수
unsupported_assumptions = 검사 수 − 지원 수
```

기존 반환값은 `legacy_field_meant_assumptions_checked`로 명시한다. 원 가정에 대한 지지 판정은 score 존재 여부, 엄격한 절댓값 threshold, 부호 일치로 재계산한다. 관측 `null` 및 0은 지원으로 세지 않는다. 기존 `accepted` 알고리즘은 수정하지 않는다. 선택한 proof가 없으면 그 proof의 검사 수는 0이며, 최초 readout 자체가 없을 때의 최종 가정 계측은 `null`이다.

선택 명령 `errata-exp18`은 원 EXP-18을 다시 독립 검산하고 원 폴더 밖에 정정 sidecar만 만든다. 이전 analysis를 덮어쓰지 않는다.

## 원자료와 감사 경로

`prepare → execute → audit → verify`를 별도 CLI 단계로 유지한다. Execute는 고정된 source/seed/입력과 별도의 raw trial, 최초 candidate, 실제 native event, 사후 선택 전/후 사건, 최종 채택을 보존한다. Journal은 작업마다 flush/fsync한다. 실패 시 원문·부분 상태·traceback·실패 유형을 기록하고 자동 retry하지 않는다.

독립 경로는 R037 `audit_native`의 상태·제어·원 proof 검증, 기존 R035 `audit_result`의 선택/proof DAG 검증, R038 wrapper/terminal 경계 재계산, R038 지표 및 paired 집계다. 생산 `TimingTrial.run`, `OnlineTrial.run`, `run_policy`를 재실행해서 자기 결과가 맞다고 판정하지 않는다. 기존 `check_seed(root, plan)`으로 학습 계보도 재검산한다.

EXP-19 capsule은 EXP-18의 입력/seed/manifest/audit 출처 부분집합과 필요한 소스를 포함한다. EXP-18의 모든 raw trial을 다시 복제한 것은 아니다. 기존 EXP-18 전체 재검증은 실행기의 사전 단계에서 원 폴더를 대상으로 수행한다. 신규 capsule의 auditor는 새 84개 trial과 학습/입력 계보를 독립 검증한다.

## 합격과 주장 범위

합격 조건은 schema·출처·계보·상태·제어·proof·비용의 정합성이다. 정확도 향상, 차등 기회 발생, ticks 절감을 합격 조건에 넣지 않는다. 실패와 측정 불가를 논리적 보류로 합치지 않는다.

이 실험은 동결 memory를 사용하는 작은 native toy engine에서 proof 선택 시점을 조작하는 최소 판별 실험이다. 학습된 자율 repair, native kernel 내부의 정책 교체, Circuit 재학습, LLM hidden state, 인간 뇌 구조의 검증으로 해석하지 않는다.
