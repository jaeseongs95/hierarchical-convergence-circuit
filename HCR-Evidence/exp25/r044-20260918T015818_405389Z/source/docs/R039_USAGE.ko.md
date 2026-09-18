# R039 / EXP-20 적용·실행 안내

## 더블클릭 한 번으로 설치와 실행

`HCR_R039_EXP20_OneClick.cmd` 한 파일을 기존 프로젝트 루트에 놓고 더블클릭한다. 이 CMD에는 추가 소스 ZIP이 내장되어 있다. 별도의 ZIP 다운로드·수동 압축 해제·명령 입력은 필요 없다.

```text
hierarchical-convergence-circuit/
├─ HCR_R039_EXP20_OneClick.cmd  ← 이 파일만 놓고 더블클릭
├─ Run-HCR-R038.py
├─ R038_MANIFEST.json
├─ src/hcr/
├─ tools/
└─ HCR-Evidence/exp19/r038-20260917T121349_552337Z/
```

실행기는 내장 ZIP SHA-256, R038 기준 manifest와 파일 checksum, 기존 대상 파일의 충돌을 검사한다. 새 R039 파일만 설치하며 다른 내용의 기존 파일이 있으면 강제로 덮어쓰지 않고 중단한다. 동일 파일은 다시 쓰지 않는다. 설치 중 I/O 실패 시 설치된 파일 목록과 실패 기록을 남긴다. 자동 rollback으로 증거를 삭제하지 않는다.

설치 후 Python 3.12 이상을 사용한다. 사용자 LocalAppData의 Python312 경로를 먼저 확인하고, Python313/314, py -3.12, PATH의 python 순서로 확인한다. 모델·라이브러리·저장소를 다운로드하지 않고, Git 설정·commit·push·시스템 영구 실행 정책을 바꾸지 않는다.

## 자동 진행 단계

배포·의존 소스 checksum → 신규 self-test → 기존 selector 연결 검사 → 기존 EXP-19 전체 verify → native 연결 self-test → EXP-20 plan 동결 → 36회 본 실행 → 독립 audit → verify → evidence bundle.

매 단계 console과 execution-logs에 기록하며 첫 실패에서 중단한다. 종료 코드가 0이면 위 단계가 끝난 것이다. 정확도나 절감률이 높다는 뜻은 아니다.

기준 EXP-19 폴더 이름은 기본으로 인식한다. 위치를 옮겼을 때는 exp19 바로 아래에서 같은 raw manifest hash를 가진 유일한 r038 폴더를 찾는다. 변경된 기준 폴더를 발견했을 때 다른 폴더로 몰래 대체하지 않는다.

## 결과 위치

```text
HCR-Evidence/exp20/r039-<UTC timestamp>/
  plan.json
  environment.json
  attempts.jsonl
  raw/t0000.json ... t0035.json
  source/                  실제 실행 소스 snapshot
  upstream/                원 학습 seed
  basis/exp19/             이전 실험의 입력·audit 출처 capsule
  analysis/
    summary.ko.md          전체 결과
    paired.csv             순열 내부 native/사후/온라인 비교
    order_effects.csv      순열 간 경로·비용·최종 결과 변화
    readouts.csv           각 readout의 ID 기반 경로·시점
    trials.csv
    summary.json
    audit.json
    records/t0000.json ... t0035.json
```

원자료 ZIP은 `HCR-Evidence/exp20/r039-<UTC timestamp>_evidence.zip`이다. 단계별 실행 로그는 `HCR-Evidence/exp20/execution-logs/<timestamp>/`, 설치 로그는 `HCR-Evidence/deployments/r039-<timestamp>/`에 남는다. 기존 EXP-19 데이터는 그대로 둔다.

## ZIP을 직접 적용한 경우

`HCR_R039_EXP20_additive_source.zip`은 전체 저장소가 아닌 추가 파일 묶음이다. 내용물이 루트에 병합되도록 적용한 경우에는 `Run-HCR-R039.bat`를 더블클릭한다. 기존 프로젝트 안에 ZIP 파일명과 같은 하위 폴더를 하나 더 만드는 방식이 아니다.

선택적인 명령행 실행:

```powershell
python -X utf8 -B .\Run-HCR-R039.py
```

다른 위치의 EXP-19 원자료를 사용해야 할 때:

```powershell
python -X utf8 -B .\Run-HCR-R039.py --source-run "D:\실제경로\r038-20260917T121349_552337Z"
```

`--check-only`는 배포/기존 EXP-19 검산/native 연결 self-test까지만 실행하며, 신규 36회 본 실험은 실행하지 않는다. self-test 자체의 12개 native 실행은 포함된다. 자동 실행에서는 이 옵션을 사용하지 않는다.

## 범위와 검증

실행 환경은 기존 저장소와 보존한 EXP-19 결과, Windows PowerShell 및 Python 3.12 이상을 전제로 한다. 제공자의 Linux 검사와 사용자의 Windows native 본 실험을 구분한다. 세부 실행·미실행 범위는 `validation/r039/검증보고서.md`를 확인한다.
