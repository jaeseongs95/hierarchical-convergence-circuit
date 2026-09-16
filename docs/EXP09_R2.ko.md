# EXP-09 r2 — 재오답 원인분리와 비용 분해

기준: `jaeseongs95/hierarchical-convergence-circuit`의 `99e052ee3d27a3958bd741ad10ede36f6e90306d`.
엔진 버전은 **0.2.0 유지**. 이번 변경은 기존 EXP-09 평가 실행기를 확장한다.
R0.2.1의 session/snapshot 기능, 학습 규칙 변경, pool 최적화를 섞지 않는다.

## 1. 이번 단계가 필요한 이유

사용자가 제공한 R0.2 review에는 36개 판단 중 안정 오답 5개, full의 episode 내부 수정,
새 약한 입력에서의 retention 재오답이 기록됐다. cold/warm 세 쌍에서는 warm의 실측 infer 시간이 더 길었다.
이는 이전 run의 관찰이지 이번 새 실험의 결과가 아니다.

현재 소스에서 확인한 조건은 다음과 같다.

- `src/hcr/runtime.py::AdaptiveEngine.infer`: revision이 있으면 `use_circuits=self.use_circuits and not forced`.
  재시도는 memory 변경뿐 아니라 회로 사용도 비활성화한다.
- `src/hcr/learning.py::update_adaptive`: 오류는 `decision.circuit_ids`에 포함된 회로만 약화한다.
  후보로 나타났지만 선택되지 않은 다른 회로는 이 분기로 약화하지 않는다.
- 동일 학습기에서 새 부분회로를 컴파일하는 조건은 `correct is True and proof_valid and decision.value is True`다.
  출력이 거짓인 정답을 얻어도 음의 예외 회로를 자동 학습하는 구현은 아니다.
- `src/hcr/activation.py`: 구조 매칭, pool network 구성, 회로 간 경쟁이 추가된다.
  구조적 expansion 감소와 tick/signal/시간 감소를 분리해야 한다.

위 코드는 가능한 작동 경로를 알려준다. 실제 재오답에 어떤 회로가 사용됐는지는 새 결과의 후보·학습 기록과 짝 비교로 확인한다.
원인을 미리 정하고 모든 회로를 약화하거나 threshold를 바꾸는 수정은 하지 않았다.

## 2. 기존 probe와의 관계

기존 `tools/r02_baseline/probe.py`의 2×2×2 비교와 save/load 비교를 유지·보강했다.
새 평가 엔진을 복제하지 않는다. 실제 계산은 기존 baseline capture의 `source/src/hcr`에서 실행한다.
`collect.py`, R0.2의 engine/kernel/learning/workspace, 기존 run과 capture는 변경하지 않는다.

새 파일:

| 파일 | 책임 |
|---|---|
| `probe_analysis.py` | 같은 입력의 쌍 비교, pool/decision 비용 분해, 후보와 feedback 연결 |
| `audit_probe.py` | 입력 조건·해시·tick 수치·외부 proof·학습 전이 재검산 |
| `tests/test_exp09_r2.py` | HCR 추론 없이 도구 계약을 검사하는 추가 시험 |

`probe.py`의 기본 동작은 여전히 **계획 출력만**이다. `--execute`가 있어야 새 추론이 시작된다.

## 3. 고정할 것과 바꿀 것

### A. 저장·복원

동결된 학습 memory에서 adaptation을 재현하고, 그 직후의 같은 memory를 다음 두 조건에 준다.

1. 직접 복사한 live memory
2. 파일에 저장한 뒤 복원한 memory

동일 공개 입력에서 전체 decision을 비교한다. 제외하는 값은 decision ID와 실측 wall time뿐이다.
proof, activation state, circuit ID, memory version, 연산 수는 제외하지 않는다.
원 사용자 실행 세션의 RAM을 복구한 것으로 기록하지 않는다.
둘 다 오답이더라도 행동이 같으면 저장·복원 동등성은 성립한다.

### B. memory × 측정 × routing

- memory: 원 capture의 `memory_after_training.json` / `memory_after_adaptation.json`
- 입력: 원 run에서 실제 사용한 약한 관측 / 실제 correction에서 사용한 강한 관측
- routing: 회로 사용 / graph-only

각 축을 바꾼 쌍을 따로 출력한다. 측정 조건 비교를 제외한 모든 쌍은 공개 입력 전체가 동일해야 한다.
engine은 `World.hidden`, 실험 phase/arm, 평가용 정답을 입력으로 받지 않는다.
강한 관측은 새 실험에서 처음부터 제공하는 지원 조건이며, 원래보다 자율 계산이 개선됐다고 세지 않는다.

### C. 추가 정보 없는 재시도

같은 학습 memory와 같은 약한 입력에서 두 경로를 비교한다.

- `measured_replay`: 실제 `request_revision` 후 기존 World 측정 규칙으로 관측을 갱신.
- `same_score_control`: 같은 요청을 받고 revision만 증가시키며 공개 점수는 그대로 유지.

두 조건 모두 기존 구현대로 재시도에서는 회로를 끈다. 첫 재시도 직전 memory도 일치하는지 검사한다.
동일 점수 조건은 **정밀 측정을 수행한 것으로 표시하지 않는다**. `new_information=false`인 대조다.
이 조건은 1회 재시도까지만 수행하여 반복 약화를 추가로 누적하지 않는다.
실제 측정 조건은 기존 관측 예산을 따른다. 최초 판단이 오답이 아니라면 재시도를 강제하지 않는다.

이 비교의 질문은 “강한 측정 없이도 해당 수정이 일어나는가?”다.
회로 비활성화와 이미 일어난 memory 약화의 개별 기여는 B의 쌍 결과와 함께 읽는다.

### D. 비용

기존 familiar 3개와 novelty 2개를 그대로 사용한다.
모든 쌍에서 **같은 학습된 before memory를 주고 `use_circuits`만 변경**한다.
기존 cold는 빈 memory였으므로 이번 graph-only 대조와 같다고 섞지 않는다.
과거 cold/warm 비용은 `original_cost_analysis.json`에 별도로 보존한다.

기본 반복은 사례당 4쌍이다. graph-only 우선/회로 우선 순서를 번갈아 사용한다.
반복 수는 2~20의 짝수만 허용한다. 반복 측정을 새 독립 과제로 세지 않는다.

비용 항목:

- dependency node/edge, expansions, frontier retirements
- recall checks, binding operations, circuit candidates
- 전체 tick/signal과 그 내역인 **pool / decision** tick/signal
- proof 복원 항목
- engine 초기화·memory 복사 시간(별도 표), infer 호출 시간, 외부 평가 시간
- feedback 학습·직렬화 비용

별칭(`signal_events` 등)을 원래 값과 더하지 않는다. pool/decision 내역을 전체와 다시 합산하지 않는다.
단위가 다른 카운터를 임의의 총비용 점수로 합하지 않는다.
wall time에는 현재 Python·trace·검증 구현의 오버헤드가 포함되며, 하드웨어 에너지 실측이 아니다.

### E. training 3/6/9

새 훈련 corpus를 만들지 않고 기존 3회·6회·9회 checkpoint를 같은 conflict에 적용한다.
attempt 수만이 아니라 inference/feedback 비용과 회로 후보의 strength, evidence count, prior, 실패 이력도 기록한다.
회수 차이에는 가용 회로와 증거 수가 함께 달라질 수 있으므로 순수 weight 개입이라고 부르지 않는다.

## 4. 후보·학습의 추적

`candidate_trace.json`에는 회로 ID, pattern 길이, strength, failures, evidence count, prior, activation,
mismatch, eligible, 실제 binding 적용 여부, 최종 판단에 포함된 회로 여부가 들어간다.
`binding_applied_in_attempt`는 해당 attempt 중 그 binding이 사용됐다는 뜻이며, 특정 pool 호출이 원인이라고 확정하는 표시는 아니다.

`feedback_changes.json`은 다음을 구분한다.

- history/version만 변경됐는지
- circuits/pending 내용도 변경됐는지
- 어떤 회로가 얼마나 약화됐는지
- 올바른 거짓 출력 이후 음의 회로를 새로 생성했는지(현재 엔진은 이 기능을 추가하지 않음)

약화된 회로 대신 아직 약화되지 않은 다른 후보가 재선택됐다면 이를 관찰로 남긴다.
다른 후보가 존재했다는 이유만으로 전체 원인을 단정하지 않는다.

## 5. 실행 방법 — 결과 폴더를 옮겼어도 사용 가능

프로젝트 루트 PowerShell에서 실행한다. `$Capture`는 현재 실제 capture 경로로 지정한다.
아래 `$Out`은 이번부터 사용할 새 출력 경로다. 기존 폴더는 덮어쓰지 않는다.

```powershell
$Repo = 'D:\codex\진짜미친짓\hierarchical-convergence-circuit'
Set-Location $Repo

# capture를 옮겼다면 이 값만 실제 위치로 변경
$Capture = 'D:\codex\진짜미친짓\hcr-r02-baseline-capture-20260916'
$Out = 'D:\HCR-Evidence\exp09\r02-diagnostic-01'

# 기존 16개 + 신규 35개 도구 시험. HCR 추론 없음.
python -X utf8 -B -m unittest discover -s tools/r02_baseline/tests -p 'test_*.py' -v

# 계획·무결성 확인만 수행. 결과 폴더도 만들지 않음.
python -X utf8 -B tools/r02_baseline/probe.py --bundle $Capture --out $Out

# 새 비교 추론, 원시 기록 생성, 작성된 범위의 audit까지 수행
python -X utf8 -B tools/r02_baseline/probe.py --bundle $Capture --out $Out --execute
```

기본 설정에서 계획상 최대 65회 추론이다. 실제 횟수는 오류 수정 진행에 따라 달라질 수 있다.
추론·학습·측정은 위 마지막 명령을 사용자가 실행할 때 수행된다. 모델/API/네트워크 호출은 없다.

완료된 결과를 다시 검산하는 명령:

```powershell
python -X utf8 -B tools/r02_baseline/audit_probe.py --bundle $Capture --run $Out
```

`--run`은 EXP-09의 새 결과다. 기존 `hcr.py verify`는 다른 run schema이므로 EXP-09 결과를 넘기지 않는다.
`--bundle`에는 review 결과가 아니라 **baseline capture 전체**를 지정해야 한다.

## 6. 결과 파일

| 파일 | 내용 |
|---|---|
| `summary.ko.md`, `summary.json` | 짝 비교·수정 조건·저장 동등성·반복 비용·학습 횟수별 요약 |
| `costs.csv` | 판단별 전체 카운터 및 pool/decision 내역 |
| `candidate_trace.json` | 후보 회로의 강도·prior·실제 binding 적용 |
| `feedback_changes.json` | 실제 학습 patch와 구조/이력 변화의 구분 |
| `initializations.csv` | memory 복사·engine 초기화 시간 |
| `original_cost_analysis.json` | 이전 R0.2 run의 비용·학습·후보 분석; 새 표본 아님 |
| `episodes.jsonl`, `events.jsonl` | 새 비교의 원시 판단과 append-only trace |
| `live_after_adaptation.json`, `memory_after_error.json` | 재현한 correction 후/최초 오류 feedback 직후 memory. 후자는 최초 오류가 발생했을 때만 생성 |
| `plan.json`, `status.json`, `manifest.json`, `audit.json` | 실행 전 계획, 완료 상태, 파일 무결성, 검산 범위 |
| `original_run_audit.json` | 기존 capture의 R0.2 독립 auditor 실행 결과 |
| `tool_source/` | 이번 probe에 실제 사용한 평가 도구 소스 |

폴더 전체를 옮겨도 된다. 내부 파일·상대경로·내용은 그대로 보존한다.
새 결과를 검산할 때는 옮긴 capture와 결과 위치를 인수로 넘긴다.

## 7. audit의 범위

재검산하는 것: 파일과 trace hash, 실험 셀과 입력·memory·routing의 대응, 수치 tick,
수렴 분류, 외부 proof/reference 판정, feedback 허가·독립 학습 전이식, 비용 일부 및 요약 집계.

생산 `AdaptiveEngine.infer`, `update_adaptive`, `dynamics.tick`은 audit에서 호출하지 않는다.
기존 독립 audit의 수치식·학습식과 외부 평가기는 공유한다. 요약 분석 코드는 실행기와 공유하므로
이를 또 하나의 독립 알고리즘 검증으로 계산하지 않는다.

**전체 frontier 정책·graph 전개의 독립 재생은 하지 않는다.** `full_runtime_graph_audit=false`를 유지한다.
벽시계 시간 재현, 외부 실행 인증, 가설 사실성 검증과도 구분한다.

## 8. 이번에 수행한 검증과 남은 실행

작성 환경에서 순수 도구 시험 51개(기존 16 + 신규 35)를 실행했다. 이 시험은 HCR를 import하지 않는다.
Python 3.12 문법과 패치/배포 파일 무결성은 별도로 검사한다.
**새 EXP-09 추론·원 capture 전체를 이용한 audit·Windows 실행은 작성 환경에서 수행하지 않았다.**
사용자가 보낸 4개 review 파일은 원 capture 전체가 아니므로, 새 실행 성공 수치를 대신 만들어 넣지 않았다.

## 9. 다음 개발 판단

이 단계는 R0.2 기준선을 닫기 위한 후속 비교다. 결과를 보고 다음을 분리한다.

- direct/reload가 같고 둘 다 틀림: 저장 실패 대신 같은 memory의 판단·회로 선택을 조사.
- 같은 memory/입력에서 graph-only와 circuit 결과가 다름: 해당 조건에서 routing의 효과가 있음.
- 같은 점수 재시도에서도 수정됨: 그 대조에서는 강한 추가 측정이 수정의 필수조건이 아니었음.
- 학습 기록은 바뀌었지만 회로 내용은 같음: 회로/예외 학습까지 완료됐다고 기록하지 않음.
- expansion은 줄고 pool signal은 늘어남: 국소적 압축과 전체 연산 절감을 구분.

결과를 기준선 문서에 고정한 뒤 R0.2.1의 중단·복원·재개 계약을 구현한다.
학습 규칙과 실행 최적화는 그 이후 별도의 비교 패치로 다룬다.
