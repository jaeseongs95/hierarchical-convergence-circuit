# EXP-09 후속 실행 안내

기존 수집 절차와 capture는 그대로 사용한다. 후속 probe의 현재 schema는 r2다.
[EXP-09 r2 실행·결과 경로·audit 안내](EXP09_R2.ko.md)를 먼저 참고한다.
`--execute` 없는 probe 호출은 계획 출력만 하고, 결과 폴더를 생성하지 않는다.

---

# R0.2 기준선 정리 패키지 사용법

## 1. 이번 패키지의 의미

엔진/기존 tests/설정은 바꾸지 않는다. 현재 상태 문서, 실행 수용 기록, 원시 기록 수집기와 EXP-09 진단기를 추가한다. 배포 당시 정적 검사 기록은 보존한다. 버전은 0.2.0이며 0.2.1 기능을 추가한 패키지가 아니다.

소스 작성 단계에서는 HCR import, check/demo/verify, 새 수집기·probe·보조 테스트를 실행하지 않았다. 정적 검사 결과는 ZIP 루트의 `STATIC_REVIEW.json`이다. 사용자 환경에서 다음 절차를 직접 실행한다.

## 2. 기존 저장소에 적용

ZIP을 저장소 밖에 풀고 `apply_baseline.py`가 있는 폴더에서 실행한다. 아래 경로는 앞서 사용자 실행 로그의 저장소 위치다.

```powershell
$Repo = 'D:\codex\진짜미친짓\hierarchical-convergence-circuit'

# 읽기 전용 preflight
python -X utf8 -B .\apply_baseline.py --repo $Repo

# preflight 통과 후 문서·보조 도구 적용
python -X utf8 -B .\apply_baseline.py --repo $Repo --apply
```

기준 파일이 다르면 쓰기 전에 중단한다. 변경 전 파일은 저장소 형제 폴더에 백업한다. `.git`과 기존 `runs`를 건드리지 않는다. Git 커밋·push, 모델 호출, 설치, HCR 실행을 자동으로 하지 않는다.

## 3. 보조 도구 검사 — 기존 136개와 별도

기존 테스트 파일들은 변경하지 않았다. 새 보조 도구의 계약 테스트 16개는 `tools/r02_baseline/tests`에 별도로 있다.

```powershell
Set-Location $Repo
python -X utf8 -B -m unittest discover -s tools/r02_baseline/tests -p 'test_*.py' -v
```

이 명령은 보조 도구의 데이터·파일 계약을 검사한다. HCR inference는 실행하지 않는다. 원본 R0.2의 136개 테스트를 확인하려면 기존 `python -X utf8 -B hcr.py check`를 사용할 수 있다. 다만 이번 문서 작성 때 다시 통과했다고 보고하지 않는다.

## 4. 원본 r02_first 동결·비용 분석 — 새 inference 없음

```powershell
$Capture = Join-Path (Split-Path $Repo -Parent) 'hcr-r02-baseline-capture-20260916'

python -X utf8 -B tools/r02_baseline/collect.py `
  --repo $Repo `
  --run runs/r02_first `
  --out $Capture
```

출력 경로는 저장소와 원 run 밖의 **존재하지 않는 새 폴더**여야 한다. 이미 있으면 다른 이름을 사용한다. `collect.py`는 기존 run과 code의 bytes만 읽고 복사·집계하며 HCR 엔진을 import하지 않는다.

출력 구성:

```text
hcr-r02-baseline-capture-20260916/
├─ source/                    # 원 plan에 실제 hash가 있는 실행 소스 30개
├─ run/                       # 원 r02_first 파일 그대로, 기존 manifest 포함
├─ capture_receipt.json
├─ analysis.json
├─ analysis.ko.md
├─ costs.csv
├─ familiarity_pairs.csv
├─ memory_delta.csv
├─ candidate_trace.json
└─ bundle_manifest.json       # 수집 결과 전체의 hash/완료 상태
```

`source/`는 당시에 plan에 hash를 기록한 실행 범위다. 전체 Git checkout이나 미기록 파일들의 당시 상태를 복원했다는 뜻이 아니다. `run/` 안에는 임의 파일을 추가하지 않는다. 원 manifest가 인증하는 파일 집합이 달라진다.

수집기가 `source differs`에 해당하는 오류를 내면 현재 엔진이 실행 당시와 달라진 것이다. 과거 plan/hash를 고치지 말고 해당 버전 소스를 별도 경로에 확보하여 `--repo`에 지정한다. 파일이 빠진 run을 콘솔 요약만으로 채우지 않는다.

동결본 해시 재확인:

```powershell
python -X utf8 -B tools/r02_baseline/collect.py --verify-bundle $Capture
```

원 run의 수치 audit를 동결 source로 다시 수행:

```powershell
python -X utf8 -B "$Capture\source\hcr.py" verify --run "$Capture\run"
```

기본 verify 명령은 결과를 콘솔에 출력한다. 결과 영수증을 따로 저장한다면 `$Capture` 밖에 둔다. 동결 bundle 안에 파일을 추가하면 전체 inventory 검사가 실패한다.

## 5. EXP-09 — 실제 새 비교 실행

이 단계만 새 추론·외부 평가·feedback·측정을 수행한다. 원 `r02_first`를 다시 demo로 만드는 작업이 아니다.

```powershell
# 계획/입력 동결본만 확인. 새 inference 없음.
python -X utf8 -B tools/r02_baseline/probe.py --bundle $Capture

# 계획 확인 후 새 paired 진단 실행
$Probe = Join-Path (Split-Path $Repo -Parent) 'hcr-r02-exp09-20260916'
python -X utf8 -B tools/r02_baseline/probe.py `
  --bundle $Capture `
  --out $Probe `
  --execute
```

probe는 저장소의 최신 HCR이 아니라 `$Capture\source`를 사용한다. 먼저 원 run의 기존 독립 audit를 통과해야 실행한다. 출력에는 `plan.json`, `original_run_audit.json`, `episodes.jsonl`, `events.jsonl`, `live_after_adaptation.json`, `summary.json`, `summary.ko.md`, `factorial.csv`, `initializations.csv`, `manifest.json`이 들어간다.

새 probe는 원 demo protocol과 다르므로 기존 `hcr.py verify --run $Probe`를 실행하지 않는다. 새 protocol 전체의 독립 수치 감사는 아직 없다는 상태를 결과에 명시한다. 계약 실패와 연구적 오답은 구분한다.

## 6. 원시 증거 보관

코드 저장소에는 문서·명세·수용 영수증·hash를 두고 큰 run/trace는 별도 보관한다. 기본 도구는 외부 클라우드나 GitHub로 전송하지 않는다.

공유할 파일로 묶을 때는 원본 폴더 밖에 새 ZIP을 만든다.

```powershell
Compress-Archive -LiteralPath $Capture -DestinationPath "$Capture.zip"
# EXP-09까지 실행했다면 별도 묶음
Compress-Archive -LiteralPath $Probe -DestinationPath "$Probe.zip"
```

완료 manifest가 없는 실패 폴더도 원인 분석 자료로 보존한다. 실패 폴더를 지우고 같은 경로에서 성공한 것처럼 재사용하지 않는다.

## 7. 결과를 읽는 순서

`analysis.ko.md`에서 기존 cold/warm 비용과 memory delta를 먼저 본다. `candidate_trace.json`에서 재오답 시 회로 후보·prior·선택을 확인한다. 새 probe의 `summary.ko.md`에서는 direct/reload 동등성, before/after × weak/measured × routing, training3/6/9 수정비용을 각각 비교한다.

문서·소스의 기준선은 이미 정리되어 있다. 사용자 로컬에서 수행되는 동결과 추가 비교는 그 기준선에 새 증거를 연결하는 과정이다.
