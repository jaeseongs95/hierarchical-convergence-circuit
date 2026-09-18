# R0.3.6 적용 및 실행

## 기준선

`main`의 `28b1dea8a309df62bd89ac36e340cd904726a45a`에 추가한다. 설치기는 기존 파일 95개(native source 62개 포함)의 내용 해시와 새 파일 충돌을 확인한다. CRLF/LF 차이는 텍스트 해시 계산에서만 정규화하며, 실제 기존 파일은 변경하지 않는다.

ZIP을 프로젝트 밖의 새 폴더에 풀고, 그 폴더에서 실행한다. 패키지 전체를 프로젝트 루트에 덮어쓰지 않는다.

```powershell
$PY = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
$REPO = "D:\codex\진짜미친짓\hierarchical-convergence-circuit"

# 검사만 수행
& $PY -X utf8 -B .\apply_r036.py --repo $REPO
if ($LASTEXITCODE -ne 0) { throw "기준선 또는 파일 충돌을 확인하세요." }

# 새 파일 추가
& $PY -X utf8 -B .\apply_r036.py --repo $REPO --apply
if ($LASTEXITCODE -ne 0) { throw "적용이 완료되지 않았습니다." }
```

기준 커밋의 후속 commit이라도 기존 기준 소스 해시가 같아야 한다. 다른 개발 변경을 덮어씌우거나 과거 evidence의 소스 해시를 고치지 않는다. 설치 기록만 `HCR-Evidence/deployments/`의 새 경로에 추가한다.

## 권장 실행

```powershell
Set-Location $REPO
& $PY -X utf8 -B .\Run-HCR-R036.py --out "HCR-Evidence\exp17\r036-first"
```

기본 입력은 `HCR-Evidence/exp15/r034-first`다. EXP-16은 새 memory를 학습하지 않았으므로, EXP-17도 EXP-15의 원 seed와 기본 입력 계획을 읽는다. EXP-15의 Graph/activation을 새 실험 결과로 재사용하지는 않는다.

실행기는 기존 소스 검사와 회귀시험, R035 시험, R036 단위시험, **실제 native 통합시험 7개**, EXP-15 전체 검산을 선행한다. 그다음 prepare → execute → audit → verify를 별도 프로세스로 실행한다. 실제 native 통합시험에서 source/엔진이 없으면 skip하지 않고 실패한다.

원본 결과 경로가 다르면 `--source-run`으로 지정한다.

```powershell
& $PY -X utf8 -B .\Run-HCR-R036.py --source-run "HCR-Evidence\exp15\별도실행" --out "HCR-Evidence\exp17\r036-custom"
```

새 native 실험 전의 검사만 실행하려면 `--check-only`를 사용한다. 여기에는 회귀 및 native 통합시험용 실행이 포함된다. 이것은 EXP-17 본 실험이 아니다.

## 결과

```text
HCR-Evidence/exp17/r036-first.plan.json
HCR-Evidence/exp17/r036-first/
  plan.json
  environment.json
  attempts.jsonl
  upstream/              # 동결 seed·기존 계획·학습 기록·manifest
  source/                # 원 native/선택 도구/새 도구의 실행 소스 사본
  raw/t0000.json ...      # 실제 native session 및 모든 readout 비교
  manifest.json
  analysis/
    audit.json
    summary.ko.md
    summary.json
    conditions.csv
    records/t0000.json ...
```

stdout와 명령 종료 코드는 `HCR-Evidence/exp17/execution-logs/<새 시각>/`에 `.stdout.txt`와 `execution.json`으로 남는다. 기존 `.gitignore`의 `*.log`에 의해 실행 로그가 사라지는 형식을 쓰지 않는다.

중간 실패가 발생하면 같은 output 경로에 재실행하지 않는다. 해당 실패 기록을 보존한 채 별도의 `--out` 경로로 명시적인 다음 시도를 수행해야 한다. 새 시도를 최초 성공으로 합치지 않는다.

## 독립 재검산

```powershell
& $PY -X utf8 -B .\scripts\r036_cli.py verify --run "HCR-Evidence\exp17\r036-first"
```

이는 저장된 summary만 확인하는 명령이 아니다. raw와 복사한 seed/소스에서 native session·입력 대응·DAG·비용·summary를 다시 계산한다. 일치하는 기존 source와 R035 도구가 필요하다. 복사된 upstream 파일을 사용하므로 audit/verify에는 원 EXP-15 전체 경로가 없어도 되지만, prepare/execute에는 해당 원자료 폴더가 필요하다.
