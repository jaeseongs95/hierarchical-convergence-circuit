# R0.3.2 적용 후 실행

패치의 `apply_r032.py --repo ...`로 사전 검사한 다음 `--apply`로 적용한다.
README 본문은 보존하며 기존 실험 결과는 건드리지 않는다. 커밋·push는 자동 실행하지 않는다.

프로젝트 루트에서 전체 검증과 EXP-13 실행:

```powershell
python -X utf8 -B Run-HCR-R032.py --out 'HCR-Evidence\exp13\r032-first'
```

Python 실행기이므로 PowerShell execution policy 변경은 필요 없다.
실행 순서는 release 검사 → core tests → baseline/복구 tests → concept tests/registry →
EXP-13 → 재검산이다. 어느 단계든 실패하면 다음 단계로 진행하지 않는다.

개별 명령:

```powershell
python -X utf8 -B hcr.py grounding plan
python -X utf8 -B hcr.py grounding demo --out 'HCR-Evidence\exp13\r032-first'
python -X utf8 -B hcr.py grounding verify --run 'HCR-Evidence\exp13\r032-first'
```

plan은 계획만 출력한다. demo만 새 학습/추론을 수행한다. verify는 새 추론을 하지 않는다.
기존 출력은 덮어쓰지 않는다. 실패한 결과도 삭제하지 말고 별도의 새 폴더명을 사용한다.
새 폴더 선택은 자동 retry가 아니라 사용자가 명시적으로 지정하는 별도 실행이다.

## 결과 폴더

```text
HCR-Evidence/exp13/r032-first/
  plan.json
  source/src/hcr/...
  seed/3.json, 6.json, 9.json
  training.json
  raw/{학습량}/{사례}/{엔진}.json
  records/{학습량}/{사례}/{엔진}.json
  conflicts/{학습량}/{사례}.json
  costs.csv
  summary.json
  summary.ko.md
  audit.json
  manifest.json
```

분석 전달은 **r032-first 전체를 ZIP으로 압축**한다. 원시 packet과 source를 빼면
감사 범위가 줄어든다. 이전 EXP-09~12는 이번 분석에 매번 같이 보낼 필요 없다.

## 정상 완료의 의미

`state=complete`, `verified=true`, `task_inferences=126`, `training_inferences=9`,
`readout_policy_evaluations=378`, `paired_input_memory_cells=42`를 확인한다.
`verified=true`는 기록/계약 검산이지 정확도 100%나 모든 지지 문제 해결이라는 뜻이 아니다.
원시 오답은 raw에 남고 dependency_gate에서 보류했으면 records에 None으로 따로 남는다.

## 같은 run을 나중에 읽는 경우

검사 코드는 실행 source와 일치해야 한다. 새 버전 소스에 맞추어 과거 packet의 source hash를
바꾸지 않는다. 과거 기록은 해당 버전/frozen source의 감사기로 검증한다. 폴더를 통째로
이동하는 것은 허용되지만 내부 경로·파일 내용을 바꾸지 않는다.
