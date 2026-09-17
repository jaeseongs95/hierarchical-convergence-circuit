# R040 / EXP-21 적용·실행

## 한 파일로 실행

`HCR_R040_EXP21_OneClick.cmd` 하나를 기존 저장소 루트에 두고 더블클릭한다.
CMD 내부에 소스 ZIP이 포함되어 있어 별도 압축 해제나 명령 입력은 필요 없다.

```text
hierarchical-convergence-circuit/
├─ HCR_R040_EXP21_OneClick.cmd
├─ Run-HCR-R039.py
├─ R039_MANIFEST.json
├─ src/hcr/
├─ tools/
└─ HCR-Evidence/exp20/r039-20260917T135401_019010Z/
```

Python 3.12 이상이 필요하다. `%LOCALAPPDATA%/Programs/Python/Python312/python.exe`를 먼저 확인하고,
이후 설치된 3.13/3.14, `py -3.12`, `python` 순서로 확인한다. Python·모델·패키지를 설치하거나 다운로드하지 않는다.
프로젝트 경로의 공백·한글·느낌표를 보존하도록 경로를 인자로 전달하고 CMD delayed expansion을 끈다.

내장 ZIP 해시 → R039 기준 manifest/파일 → 설치 충돌 순서로 검사한다.
수정된 기존 R040 파일이나 다른 파일과 충돌하면 덮어쓰지 않고 중단한다. 동일한 파일의 재설치는 새로 쓰지 않는다.
부분 설치가 실패하면 설치 기록과 실패 원문을 남긴다. 수동 수정 파일을 자동 복구하지 않는다.

## 실행 순서

1. 신규 배포와 기존 동결 의존 소스 검사
2. 신규 단위·합성 제어/파일·보고 검사
3. 기존 R038 selector 연결 검사
4. 지정 EXP-20 원자료 전체 verify
5. 실제 native 통합 self-test (본 실험과 별도 32 session)
6. EXP-21 조건 동결
7. 72개 본 native 실행
8. 독립 audit
9. verify
10. evidence ZIP 생성

첫 실패에서 중단하고 execution.json·단계 로그·가능한 부분 evidence를 남긴다.
자동 retry, 기존 evidence 덮어쓰기, 모델 서버 조작, commit/push는 하지 않는다.

## 결과

```text
HCR-Evidence/exp21/r040-<UTC실행시각>/
├─ plan.json
├─ attempts.jsonl
├─ raw/                       72개 원문
├─ source/                    실제 사용한 소스 snapshot
├─ basis/exp20/               기존 기준 조건과 36개 raw
├─ upstream/                  학습 seed 계보
├─ manifest.json
└─ analysis/
   ├─ summary.ko.md
   ├─ paired.csv              같은 scheduler 안의 native/사후/온라인 비교
   ├─ scheduler_contrasts.csv 같은 순열의 scheduler 두 방식 비교
   ├─ mediation.csv           순열 간 격차의 감소·잔존
   ├─ scheduler_decisions.csv 각 선택·native priority 호출
   ├─ order_effects.csv
   ├─ readouts.csv
   ├─ trials.csv
   ├─ audit.json
   └─ records/
```

실행 로그는 `HCR-Evidence/exp21/execution-logs/`, 설치 로그는 `HCR-Evidence/deployments/r040-*`에 남는다.
결과 ZIP은 run 폴더 옆의 `<run-name>_evidence.zip`이다.

## 직접 명령 실행

이미 소스 ZIP의 내용물을 프로젝트 루트에 병합했다면 `Run-HCR-R040.bat`를 실행한다.
PowerShell에서 직접 실행할 수도 있다.

```powershell
python -X utf8 -B .\Run-HCR-R040.py
```

검사만 수행:

```powershell
python -X utf8 -B .\Run-HCR-R040.py --check-only
```

`--check-only`는 기존 EXP-20 verify와 실제 native self-test까지 수행하되, 본 72회는 실행하지 않는다.
출력 경로를 지정할 때는 아직 존재하지 않는 새 경로를 사용한다.

```powershell
python -X utf8 -B .\Run-HCR-R040.py --out HCR-Evidence/exp21/r040-first
```

기준 폴더를 이동했다면 `--source-run`으로 지정할 수 있지만, raw manifest는 지정된 EXP-20 해시와 같아야 한다.
`Exit code: 0`과 마지막 audit/verify의 `verified: true`는 정합성 검증 완료를 뜻한다. 연구 가설의 지지는 결과 표로 판단한다.
