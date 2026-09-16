# R0.2 적용 및 실행

## 기준과 적용

이 패키지는 새 저장소 초기화본이 아니라 **기존 R0.1 위에 적용하는 변경분**이다. GitHub 연결에서 지정 원격이 404였으므로 회수한 실제 R0.1 배포 ZIP을 기준으로 작성했다. 최신 커밋과 동일한지는 적용기의 로컬 파일 해시 검사로 확인한다. 원격 조회가 성공한 것으로 해석하지 않는다.

업데이트 ZIP은 저장소 바깥 임의 경로에 푼다. 압축 루트의 `payload/`를 바로 덮어쓰기보다는 안전 적용기를 사용한다. 먼저 읽기 전용 검사:

```powershell
python -X utf8 -B "D:\downloads\hcr-r02-update\apply_r02.py" --repo "D:\codex\hierarchical-convergence-circuit"
```

경로는 실제 압축 해제 위치와 기존 저장소 경로로 바꾼다. 모든 검사가 통과한 뒤 실제 파일 적용:

```powershell
python -X utf8 -B "D:\downloads\hcr-r02-update\apply_r02.py" --repo "D:\codex\hierarchical-convergence-circuit" --apply
```

`--apply`가 없으면 저장소에 파일을 쓰지 않는다. 기준 파일이 다르면 변경 시작 전에 중단한다. CRLF/LF는 정규화 비교하되 실제 기존 바이트는 별도 백업한다. 원본 백업은 저장소의 형제 경로에 생성하고 그 위치를 출력한다. 자동 git 명령·패키지 설치·모델 호출·테스트 실행은 하지 않는다. `.git`, `runs`, 미등록 로컬 파일은 변경하지 않는다.

검사가 실패하면 충돌 파일을 읽고 현재 변경사항과 패키지의 `r02_changes.patch`를 비교해야 한다. 강제 덮어쓰기 옵션은 없다. 적용 이후 출력되는 `written_files`가 실제 변경 파일 목록이다. 이미 동일한 파일이 모두 적용돼 있으면 `already_applied`로 종료한다.

## 순서대로 실행

아래 명령은 **기존 저장소 루트**에서 실행한다. 배포 세션에서는 실행하지 않았다.

```powershell
python -X utf8 -B hcr.py check
python -X utf8 -B hcr.py demo --engine r02 --config configs/r02.toml --out runs/r02_first
python -X utf8 -B hcr.py verify --run runs/r02_first
```

`check`는 기존 R0.1 시험과 R0.2 시험을 함께 발견한다. R0.1의 72개 시험 원문은 보존했다. 신규 시험 수와 구문검사 결과는 static review에 있지만, 통과 수는 사용자의 실제 `check` 결과로만 판단한다.

R0.1 실행 경로를 별도 확인하는 명령도 그대로 유지한다.

```powershell
python -X utf8 -B hcr.py demo --config configs/r01.toml --out runs/r01_after_r02
python -X utf8 -B hcr.py verify --run runs/r01_after_r02
```

`--engine` 생략은 R0.1이다. `verify`는 run manifest의 schema로 R0.1/R0.2를 구분한다. 과거 run이 기록한 source hash와 현재 소스가 다르면 source check가 실패할 수 있다. 과거 run을 덮어쓰지 말고 해당 버전 소스와 보관한다.

PowerShell 실행기를 직접 호출할 수도 있다.

```powershell
.\Run-HCR-R02.ps1
# 또는 설치 경로를 명시
.\Run-HCR-R02.ps1 -PythonPath "C:\Users\sjs95\AppData\Local\Programs\Python\Python312\python.exe"
```

이 실행기는 check → demo → verify 순서로 실행하고 실패하면 중단한다. 사용자가 직접 호출한 시점에만 수행된다. 기존 `Run-HCR.ps1`은 변경하지 않았다.

## 결과 파일

`plan.json`은 실행 전에 config와 source hash, 개발 protocol을 기록한다. `events.jsonl`은 모든 수렴·매칭·확장·판단·학습·측정의 append-only 기록이다. `episodes.jsonl`은 각 attempt를 별도 행으로 보존한다. `summary.json`/`summary.ko.md`는 실제 실행 후 생성된다. `memory_after_training.json`, `memory_after_adaptation.json`, 두 training count checkpoint는 지속성을 검사한다. `manifest.json`은 완료 run의 파일 집합과 해시를 기록한다.

같은 출력 폴더가 있으면 자동으로 덮어쓰지 않는다. 다음 실행은 `runs/r02_second`처럼 새 경로를 지정한다. 실패 run은 원인 분석 자료이므로 기존 내용은 남는다.

## 공개 입력만으로 infer

```powershell
python -X utf8 -B hcr.py infer --engine r02 --config configs/r02.toml --input configs/example_observation.json --out runs/r02_infer_first
```

학습된 R0.2 memory를 재사용할 때는 `--memory runs/r02_first/memory_after_training.json`을 추가한다. infer는 frozen 실행이며 correctness를 평가하거나 학습하지 않는다. R0.1 memory를 R0.2에 넣으면 schema 오류로 거부한다.

## 해석

`complete=true`는 실험 실행 완료, `verified=true`는 기록/수치/집계 검산 통과다. 연구 가설의 사실성이나 성능 우월성의 입증이 아니다. graph dependency 수, matching 비용, 신호 연산, latency, primitive proof D를 각각 비교한다. 오수렴이나 수정비용 증가가 발생하지 않더라도 결과를 강제하거나 성공으로 꾸미지 않는다.
