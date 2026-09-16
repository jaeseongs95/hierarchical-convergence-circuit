# 개념 보강 패치 적용·확인

## 패키지와 기준

이것은 R0.2 + baseline overlay에 적용하는 조건부 패치다. 원격 HEAD 미확인 상태이므로 **127개 기준 파일 비교를 먼저 수행**한다. 소스 차이/새 파일 충돌은 강제로 덮어쓰지 않는다. ZIP은 저장소 밖에 해제한다. patch 파일과 안전 적용기는 같은 변경을 표현하므로 둘 다 적용하지 않는다.

```powershell
$Repo = 'D:\codex\진짜미친짓\hierarchical-convergence-circuit'

# apply_concepts.py가 있는 압축 해제 폴더에서 실행. 이 명령은 읽기 전용이다.
python -X utf8 -B .\apply_concepts.py --repo $Repo

# state=ready, 충돌 없음 확인 후 실제 적용
python -X utf8 -B .\apply_concepts.py --repo $Repo --apply
```

기본 명령은 쓰기 없이 검사한다. `--apply`는 쓰기 전 원본 백업을 저장소 형제 경로에 만들고 변경 파일만 적용한다. `.git`, `runs`, 원시 capture, 미등록 로컬 파일을 수정하지 않는다. 차이가 있으면 해당 파일과 `concepts_changes.patch`를 대조해야 한다. `--force`는 없다. 적용 중 다른 편집기/프로세스로 대상 파일을 동시에 수정하지 않는다. 파일 단위 원자 쓰기와 예외 시 복원을 사용하지만 OS 강제 종료 시 전체 트리 원자성을 보장하지 않는다.

## 1. 개념 연결과 신규 도구 검사

```powershell
Set-Location $Repo
python -X utf8 -B tools/r02_concepts/check.py --repo $Repo
python -X utf8 -B -m unittest discover -s tools/r02_concepts/tests -p 'test_*.py' -v
```

checker의 `state=complete`는 24개 개념의 파일·정의·명세 연결이 유효하다는 뜻이다. 새 시험은 39개 정의이며 이번 배포 세션에서는 실행하지 않았다. 기존 HCR 136개 시험 및 baseline 16개 시험은 수정하지 않았다. 필요 시 아래로 별도 재검사할 수 있다.

```powershell
python -X utf8 -B hcr.py check
python -X utf8 -B -m unittest discover -s tools/r02_baseline/tests -p 'test_*.py' -v
```

## 2. 이미 만든 capture 읽기 — demo 재실행 불필요

```powershell
$Capture = Join-Path (Split-Path $Repo -Parent) 'hcr-r02-baseline-capture-20260916'
$Review = Join-Path (Split-Path $Repo -Parent) 'hcr-r02-concept-review-20260916'

python -X utf8 -B tools/r02_concepts/review.py --capture $Capture --out $Review
```

원본 capture나 현재 소스를 실행하지 않는다. manifest/chain/기본 집계를 확인하고 다음을 새 폴더에 쓴다.

- `review.ko.md`: attempt별 수렴 상태·오답·보류·관측 label.
- `review.json`: 가정과 공개 관측/당시 decision program의 포함 관계, 기록 시점, 미측정 항목.
- `receipt.json`, `manifest.json`: 입력 hash·수행 범위·생성 파일 hash.

`state=complete`는 분석 완료다. `numerical_audit_executed=false`가 정상이며 기존 독립 audit를 대신 실행했다는 뜻이 아니다. label 목록은 중첩 가능하다. stable wrong라는 관측과 over-compression이라는 원인 가설을 섞지 않는다. `separate_latencies_measured=false`는 기존 R0.2 기록에 해당 값이 없기 때문이다.

기존 `$Review`가 있으면 중단한다. 다음번은 새로운 출력 경로를 지정한다. 원시 capture의 파일을 직접 편집하거나 거기에 보고서를 저장하지 않는다.

## 직접 git patch를 쓰는 경우

`concepts_changes.patch`는 검토용/표준 unified patch로 함께 제공한다. 안전 적용기가 수행하는 전체 기준 파일·백업 검사를 git apply 자체가 대체하지는 않는다. 권장 경로는 위 `apply_concepts.py`다. 이 패키지는 git commit/push 명령을 자동 실행하지 않는다.
