# R0.3.4 적용 및 실행

## 기준선

원격 main 확인 커밋: `54330d01c979cb942b39558186c206b4373b758e`.
Windows 11 / Python 3.12 이상 / PowerShell을 대상으로 한다. 외부 라이브러리, 모델, 서버, API key는 필요 없다.

이 ZIP은 전체 저장소가 아니라 **추가 패치**다. 새 빈 폴더에 압축을 해제하고 적용기를 사용한다. `overlay` 디렉터리 자체를 프로젝트 안에 붙여 넣는 방식이 아니다.

## 적용

압축 해제 폴더를 `C:\Users\sjs95\Desktop\hcr-r034-update`로 가정한다.

먼저 쓰기 없는 검사:

```powershell
python -X utf8 -B "C:\Users\sjs95\Desktop\hcr-r034-update\apply_r034.py" --repo "D:\codex\진짜미친짓\hierarchical-convergence-circuit"
```

검사 후 실제 추가:

```powershell
python -X utf8 -B "C:\Users\sjs95\Desktop\hcr-r034-update\apply_r034.py" --repo "D:\codex\진짜미친짓\hierarchical-convergence-circuit" --apply
```

적용기는 R0.3.3 기준 src 54개를 LF-normalized SHA-256으로 검사한다. 기존 소스가 다르거나 새 파일 이름이 사용자 파일과 충돌하면 덮어쓰지 않고 중단한다. 이미 같은 패치가 적용돼 있으면 재작성하지 않는다. Git commit/signing/config/push를 수행하지 않는다.

새 설치 기록은 `HCR-Evidence/deployments/r034-시간/installation.json`에 기록한다. 과거 실험 evidence는 바꾸지 않는다.

## 회귀와 EXP-15 실행

```powershell
Set-Location "D:\codex\진짜미친짓\hierarchical-convergence-circuit"
python -X utf8 -B Run-HCR-R034.py --out HCR-Evidence/exp15/r034-first
```

실행 순서:

1. 기존 release와 R0.3.4 추가 파일 검사
2. `hcr.py check` 전체 회귀: 새 순수 모듈 시험과 실제 엔진 통합시험 포함
3. 기존 baseline/concept 도구 시험 및 concept 검사
4. EXP-15 조건·source 동결
5. raw 생성
6. 별도 프로세스의 독립 audit 및 analysis 생성
7. analysis를 다시 계산해 원자료와 대조

어느 단계에서든 실패하면 종료한다. 자동 retry, 자동 dependency 설치, 과거 파일 교체는 없다.

회귀만 실행:

```powershell
python -X utf8 -B Run-HCR-R034.py --check-only
```

## 결과 위치

```text
HCR-Evidence/exp15/
├─ r034-first.plan.json                 # 실행 전 동결 계획
├─ r034-first/
│  ├─ plan.json                        # 같은 동결 계획의 실행 내 사본
│  ├─ environment.json                 # Python/platform/Git HEAD
│  ├─ source/                          # 실행 시 src snapshot
│  ├─ training.json, seed/6.json        # 학습 원자료와 memory 계보
│  ├─ baselines/                       # 공유 최초 계산 18개
│  ├─ raw/                             # 조건별 실제 실행 기록
│  ├─ attempt_logs/                    # 첫 실행의 action log
│  ├─ manifest.json                    # 원자료 파일 무결성
│  └─ analysis/
│     ├─ summary.ko.md                 # 독립 재계산 요약
│     ├─ summary.json, costs.csv       # 구조화 결과와 구분된 비용
│     ├─ records/                      # 조건별 독립 검산
│     ├─ audit.json                    # 전체 독립 검산
│     └─ manifest.json                 # 분석과 원자료 연결
└─ execution-logs/시간/                # 회귀부터 전체 실행 로그
```

`manifest.json`의 `independent_audit_pending: true`는 **raw가 생성된 시점**의 상태를 보존한다. 이 필드를 나중에 고치지 않는다. 독립 검산 완료 여부는 `analysis/audit.json`과 그 manifest로 확인한다.

이미 같은 out 또는 plan이 있으면 `r034-second` 등 새 이름을 사용한다. 실패 실행도 지우고 같은 이름으로 재시도하지 말고, 남긴 뒤 별도 실행으로 구분한다.

## 개별 명령

```powershell
python -X utf8 -B scripts/r034_cli.py prepare --out HCR-Evidence/exp15/r034-manual.plan.json
python -X utf8 -B scripts/r034_cli.py execute --plan HCR-Evidence/exp15/r034-manual.plan.json --out HCR-Evidence/exp15/r034-manual
python -X utf8 -B scripts/r034_cli.py audit --run HCR-Evidence/exp15/r034-manual
python -X utf8 -B scripts/r034_cli.py verify --run HCR-Evidence/exp15/r034-manual
```

`audit`는 새 analysis 디렉터리를 만든다. 이미 분석이 있으면 `verify`로 재계산·대조한다. source를 바꾼 후 오래된 계획이나 checkpoint의 해시를 현재 소스로 교체하지 않는다.

추가 모듈도 실행 source fingerprint에 들어가므로, 과거 EXP-14 checkpoint를 재검산할 때는 그 결과에 보존된 원 source 환경을 사용해야 한다. R0.3.4 적용이 과거 기록을 변경하거나 무효화한 것은 아니다.

## 실행 결과 해석

main 182개, running 대조 8개, 선택 예산 대조 4개로 총 194 rollout이다. native 최초 판단, 검토 후 native 판단, sidecar proof 선택을 구별한다. 새로운 개입이 성공하는지는 실제 EXP-15 결과로 판정한다. 개발 단위시험 통과를 EXP-15 연구 결과로 사용하지 않는다.

실행과 결과 확인 이후 commit/push는 사용자가 수행한다.
