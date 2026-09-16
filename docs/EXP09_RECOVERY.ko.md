# EXP-09 r2 요약 오류 수정 및 원본 보존 복구

## 범위와 기준

기준 원격 커밋은 `89ad36c70e2dcc1cc6455a101b2366f2f3f71a9d`다. `src/hcr`, 두 설정, 기존 엔진 회귀시험은 변경하지 않는다. 엔진 버전은 0.2.0이며 이번 패치는 R0.2.1 session/snapshot 기능이 아니다.

이번 변경은 실제로 관찰된 요약기 오류를 고치고, 이미 실행한 60회 기록을 새 추론 없이 수용하는 단계다. 재오답/속도 문제의 동작 변경은 [관측 기준선](R02_EXP09_OBSERVED_BASELINE.ko.md)에 분리했다.

## 1. 수정한 동등성 계약

원래 `probe_analysis.py`는 `same_score_control`과 `measured_replay`의 두 번째 판단 직전 memory 해시 전체가 같아야 한다고 요구했다. 실제로는 첫 판단/feedback의 실행 ID가 달라 memory 이력 네 곳이 달라졌다.

`memory_equivalence.py`는 다음을 순서대로 확인한다.

1. 같은 시작 memory, 같은 첫 입력/외부 정답, 같은 첫 판단과 평가인가? 판단에서 제외하는 것은 ID와 실측 wall time뿐이다.
2. 각 arm의 첫 오류 feedback이 해당 판단을 가리키는가? 첫 오류 뒤 상태가 실제 두 번째 판단의 memory인가?
3. 대응하는 decision ID와 feedback ID만 `feedback_ids`, `consumed_feedback`, `patches`의 명시된 참조 위치에서 일대일 대응시킨다.
4. 이 대응 후 두 **전체 문서**를 비교한다. strength, failure, active, version, pending, 증거 episode, proof digest, 이전 이력은 삭제하지 않는다.

결과는 `exact_document_equal`, `execution_state_equal`, `provenance_correspondence_valid`로 분리한다. 이번 로그는 각각 `false / true / true`다. 기존 `memory_equal_at_revision`은 이제 **원본 전체 문서 동일성**을 뜻하므로 false가 정상이다. 상태 동등성은 새 명시 필드를 확인한다.

직접 사용과 save/load 대조에는 이 대응을 사용하지 않는다. 그 경우에는 여전히 전체 memory 문서·digest가 같아야 한다.

## 2. 이번 저장소의 실제 입력 경로

원격 저장소에서 결과가 다음 위치에 있는 것을 확인했다. 로컬이 같은 구조라면 아래 명령 그대로 사용한다.

```text
hierarchical-convergence-circuit/
├─ HCR-Evidence/
│  ├─ hcr-r02-baseline-capture-20260916/
│  └─ r02-diagnostic-01/
└─ tools/r02_baseline/
   ├─ probe.py
   ├─ probe_analysis.py
   ├─ audit_probe.py
   ├─ memory_equivalence.py
   ├─ measurement_journal.py
   └─ recover_probe.py
```

입력은 이미 저장소에 있는 파일을 읽을 뿐이다. 복구 출력은 저장소·원본 capture·실패 run 밖의 새 폴더에 둔다. 결과/백업 폴더를 옮겼다면 `--run`, `--bundle`의 경로만 바꾸며 내부 파일과 과거 hash는 고치지 않는다.

## 3. 실행 — 재추론 없이 기존 결과 복구

```powershell
$Repo = 'D:\codex\진짜미친짓\hierarchical-convergence-circuit'
Set-Location $Repo

$FailedRun = Join-Path $Repo 'HCR-Evidence\r02-diagnostic-01'
$Capture = Join-Path $Repo 'HCR-Evidence\hcr-r02-baseline-capture-20260916'
$Recovered = 'D:\HCR-Evidence\exp09\r02-diagnostic-01-recovered'

# 기존 51개 + 이번 39개: baseline 도구 시험 90개
python -X utf8 -B -m unittest discover -s tools/r02_baseline/tests -p 'test_*.py' -v

# 원래 capture까지 대조하는 권장 복구 경로
python -X utf8 -B tools/r02_baseline/recover_probe.py `
  --run $FailedRun `
  --bundle $Capture `
  --out $Recovered

# 별도 프로세스의 복구 산출물 재검산
python -X utf8 -B tools/r02_baseline/recover_probe.py `
  --verify $Recovered `
  --bundle $Capture
```

두 명령 모두 새 inference를 수행하지 않는다. 같은 출력 폴더가 이미 있으면 덮어쓰지 않는다. 재검산은 `--verify`를 사용하고, 새 복구가 필요하면 새로운 출력 폴더를 지정한다.

원래 capture가 없지만 당시 실행 소스가 있을 때는 다음처럼 제한된 검산도 가능하다.

```powershell
python -X utf8 -B tools/r02_baseline/recover_probe.py `
  --run $FailedRun --source-root $Repo --out 'D:\HCR-Evidence\exp09\r02-record-only-recovery'
```

이 모드는 수치·proof·학습 전이와 기록 내부의 실험 조건을 검산하지만, **최초 seed/사례가 원래 capture와 동일한지는 다시 검사하지 못한다**. `baseline_capture_reverified=false`로 표시한다. 소스가 바뀌었으면 임의로 hash를 맞추지 말고 당시 `capture/source`를 `--source-root`로 지정한다.

## 4. 결과와 상태의 뜻

```text
r02-diagnostic-01-recovered/
├─ original/                 # FAILED.json 포함 원본의 바이트 보존 복사본
├─ source/                   # plan hash와 일치하는 30개 실행 소스/설정
├─ recovery_tool_source/     # 이번 복구 도구 snapshot, 자동 실행하지 않음
├─ baseline_contract.json
├─ summary.json
├─ summary.ko.md
├─ costs.csv
├─ candidate_trace.json
├─ feedback_changes.json
├─ audit.json
├─ receipt.json
└─ recovery_manifest.json
```

`recovery_manifest.json.state=complete`는 **복구 보고서 생성 완료**다. `original_run_state=failed`는 그대로 남으며 원래 실행의 완료 manifest를 새로 만들지 않는다. `original/FAILED.json`도 삭제하지 않는다.

옛 실행에서 요약 전에 파일로 남지 않은 초기화·save/load·전체 실행 시간은 `null`로 둔다. 0으로 채우거나 새 실행 시간을 옛 측정으로 사용하지 않는다.

`audit.json`은 수치 recurrence, 외부 proof/reference 평가, 학습 전이, 짝별 입력·조건을 검산한다. 전체 frontier 선택의 독립 재생은 여전히 범위 밖이며 `full_runtime_graph_audit=false`다. 원본 완료 manifest가 없으므로 원시 trace tail과 계획된 모든 셀을 검사했다는 범위를 따로 표시한다.

## 5. 앞으로 새 EXP-09 실행을 할 때

`probe.py`의 같은 명령을 유지한다. `--execute`가 없는 호출은 계획 출력만 하고, 직접 지정했을 때만 새 추론을 실행한다. 이번 기존 로그 복구를 위해 다시 실행할 필요는 없다.

새 실행에서는 `measurements.jsonl`에 engine 초기화와 save/load 완료 시간을 그때그때 기록하고 flush/fsync한다. 이 파일은 별도 hash chain이며 HCR 신호 trace를 바꾸지 않는다. 요약기 뒤에서 실패하더라도 그 전에 실제 측정한 값은 남는다. 실측 시간 자체를 수치 재현했다고 주장하지 않고 기록 연결과 집계만 검사한다.

## 6. 다음 개발과 분리

R0.2.1의 목표는 같은 계산을 snapshot/restore/resume해도 의미가 같게 만드는 것이다. 현재의 오답을 몰래 없애거나 pool 경쟁 비용을 다른 구현으로 바꾸는 작업을 함께 넣지 않는다.

후속 별도 개입 후보는 (a) routing용 구조 친숙도와 관측 참값 prior의 분리, (b) 오류 edge/role 조건의 국소 제약, (c) pool 비용과 실제 대체 계산량의 비교다. 이 패치에서 이들 정책이나 성능 개선이 구현됐다고 표기하지 않는다.
