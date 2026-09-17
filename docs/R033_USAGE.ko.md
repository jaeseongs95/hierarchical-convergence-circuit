# R0.3.3 적용 후 실행

Python 3.12 이상. 기존 프로젝트 루트에서 다음 명령을 사용한다. PowerShell 실행 정책을 바꿀 필요가 없다.

```powershell
python -X utf8 -B Run-HCR-R033.py --out 'HCR-Evidence\exp14\r033-first'
```

순서: release 검사 → core 회귀시험 → baseline/concept 도구 시험 → concept 검사 → EXP-14 → 저장된 결과 재검산.
실패하면 이후 단계로 진행하지 않는다. 기존 출력 폴더를 덮어쓰지 않는다.

## 선택: 별도 계획 동결

```powershell
python -X utf8 -B hcr.py review plan --out 'HCR-Evidence\exp14\r033-plan.json'
python -X utf8 -B hcr.py review execute --plan 'HCR-Evidence\exp14\r033-plan.json' --out 'HCR-Evidence\exp14\r033-first'
python -X utf8 -B hcr.py review verify --run 'HCR-Evidence\exp14\r033-first'
```

학습량까지 확장할 때는 계획 생성 시 `--training-counts 3 6 9`를 붙인다. 기본 단일 시점 결과와 별도 계획/폴더로 관리한다.

## 전달할 결과

`HCR-Evidence/exp14/r033-first` 전체를 ZIP으로 주거나 그 폴더를 원격에 push한다.
`baselines`는 최초 ready 상태와 정상 finish branch, `raw`는 controller/추가 상태/관측/후속 candidate, `records`는 독립 감사·외부 채점이다.
`plan.json`, `source`, `seed`, `training.json`, `summary.json`, `summary.ko.md`, `costs.csv`, `audit.json`, `manifest.json`을 빼지 않는다.

`verified=true`는 기록/계약의 검산이지 모든 과제가 정답이라는 뜻이 아니다.
`measurement_unavailable`, `measurement_no_new_information`, `stop_compute_budget`, `stop_frontier_exhausted` 등은 실패/보류의 실험 결과로 남긴다.
`FAILED.json`이 있으면 실행/기록 생성 오류이며 완료된 run으로 수용하지 않는다. 원본 실패 폴더를 고쳐서 성공으로 만들지 않는다.
