# R035 실행 및 결과 제출

## 적용 후 검사

```powershell
python -X utf8 -B scripts/verify_r035.py
python -X utf8 -B Run-HCR-R035.py --check-only
```

첫 명령은 새 파일과 native 기준선 62개만 확인한다. 두 번째는 기존 릴리스 검사, R034/R035 검사, 기존 회귀, baseline/concept 검사, R035 테스트, EXP-15 evidence 재검산까지 수행한다. 전체 실행은 같은 사전 검사를 다시 포함한다. 중복 검사 시간을 피하려면 전체 실행 한 번만 해도 된다.

## 전체 실행

```powershell
python -X utf8 -B Run-HCR-R035.py --out "HCR-Evidence\exp16\r035-first"
```

원자료 위치가 다르면 다음처럼 지정한다.

```powershell
python -X utf8 -B Run-HCR-R035.py --source-run "HCR-Evidence\exp15\r034-first" --out "HCR-Evidence\exp16\r035-first"
```

이 실행기는 총 13개 단계 명령을 순서대로 실행하며 오류가 나면 중단한다. `prepare/execute/audit/verify`는 각각 별도 Python 프로세스다. Git 변경, 네트워크 요청, 모델 다운로드/실행은 하지 않는다.

원 저장소 `.gitignore`의 `*.log` 제외 규칙 때문에 실행 stdout/stderr는 `*.stdout.txt`로 저장한다. `.gitignore` 자체는 바꾸지 않는다. 실행 단계/종료코드는 같은 로그 폴더의 `execution.json`에 기록된다.

## 개별 명령

```powershell
python -X utf8 -B scripts/r035_cli.py prepare --source-run "HCR-Evidence\exp15\r034-first" --out "HCR-Evidence\exp16\r035-first.plan.json"
python -X utf8 -B scripts/r035_cli.py execute --plan "HCR-Evidence\exp16\r035-first.plan.json" --out "HCR-Evidence\exp16\r035-first"
python -X utf8 -B scripts/r035_cli.py audit --run "HCR-Evidence\exp16\r035-first"
python -X utf8 -B scripts/r035_cli.py verify --run "HCR-Evidence\exp16\r035-first"
```

`prepare`는 코드·원 자료·모집단·행렬을 고정한다. 이 단계가 성공했다고 full native audit을 마쳤다는 뜻은 아니다. `execute`는 raw를 생성하며 마지막 출력에 `independent_audit_pending: true`가 남는다. `audit`가 처음 analysis를 만들고 `verify`가 이를 재계산한다.

원 EXP-15를 다른 폴더로 옮겼다면 `execute/audit/verify --source-run "새 위치"`를 쓸 수 있다. 내용이 동일한 원 manifest/plan인지 다시 검사한다. 원자료 내용이 바뀐 상태를 경로 변경으로 통과시키지 않는다.

## 파일 구조

```text
HCR-Evidence/exp16/
├── r035-first.plan.json
├── r035-first/
│   ├── plan.json                # 실제 실행에 사용한 동결 계획
│   ├── environment.json         # Python/platform/HEAD/원자료 경로
│   ├── source/                  # 이번 도구 소스 snapshot
│   ├── upstream/                # 원 manifest/plan과 선택된 EXP-15 raw·baseline 사본
│   ├── snapshots/               # 원 candidate provenance + 공개 선택 입력
│   ├── attempts.jsonl           # 최초 시도 시작/완료 로그
│   ├── raw/                    # 조건별 변환 사상·입력·정책 출력·proof·비용
│   ├── manifest.json            # raw 완료·파일 무결성
│   ├── analysis/
│   │   ├── summary.ko.md        # 사람용 해석 보고
│   │   ├── summary.json         # paired 비교·모든 조건·world별 정확성
│   │   ├── audit.json           # 독립 검산 결과
│   │   ├── conditions.csv       # 표 형태의 조건 결과
│   │   ├── records/             # 조건별 독립 평가
│   │   └── manifest.json        # analysis 무결성
│   ├── failure.json             # 생성 실패 때만 존재
│   └── audit_failures/          # 검산 실패 때만 생성
└── execution-logs/<시각>/
    ├── 00.stdout.txt ...
    └── execution.json
```

원자료 전체를 중복 복사하지 않기 때문에 `upstream/`만으로 원 EXP-15 전량을 재검산할 수는 없다. 원 `HCR-Evidence/exp15/r034-first` 폴더를 계속 보관한다. 이 의존성은 plan의 manifest hash로 명시적으로 결속돼 있다.

## 실패와 재실행

기존 결과/계획이 존재하면 새 이름을 지정한다. 실패한 raw를 지우거나 성공한 조건만 덮어쓰지 않는다. 원인이 소스 변경이라면 새 소스를 확정하고 새 계획으로 실행한다. 같은 기존 계획을 자동 갱신하는 명령은 없다.

정상 종료 후 결과를 분석할 때에는 `summary.ko.md`만 제출하기보다 `exp16` 결과 폴더와 원 `exp15` 자료를 함께 저장소에 유지한다. commit/push는 사용자가 직접 수행한다. 이 패키지는 commit을 만들지 않는다.
