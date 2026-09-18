# R0.4.1 / EXP-22 적용·실행

## 원클릭

`HCR_R041_EXP22_OneClick.cmd` 한 파일을 기존 hierarchical-convergence-circuit 프로젝트
루트에 놓고 더블클릭한다. 내부에 소스 ZIP이 포함되어 있어 별도 압축 해제나 명령 입력은 필요 없다.
네트워크 다운로드, 모델 설치·갱신, 관리자 권한, Git commit/push를 수행하지 않는다.

필수 기준선은 main의 `37bb3c19f27dfbd73de7519fc8cad399395bcf3a`에 해당하는 R040 파일과
EXP-21 결과다. 기본 원자료 폴더는 다음과 같다.

```
HCR-Evidence/exp21/r040-20260917T204742_957648Z
```

원본 manifest SHA-256은
`18075ae1ad5fe4eba29161948bbb89218a5eed02bd688972962728e0a55f7464`다.
기본 폴더가 없을 때는 exp21의 r040-* 중 이 해시가 일치하는 폴더 하나를 탐색한다.
다른 실험의 결과나 새 실행을 임의로 기준선으로 사용하지 않는다.

## 설치 동작

내장 ZIP 해시를 검사하고 Python 3.12 이상을 탐색한다. Python312 설치 위치를 우선 사용한다.
기존 R040 manifest Git blob `d7213c8c9415016a047ed0004ff3ffd7ac43366a`와 해당 파일들을 검산한다.
신규 R041 파일만 설치하며, 이미 같은 파일이면 유지한다. 내용이 다른 파일을 만나면 설치 전에
중단한다. 기존 파일을 강제로 덮어쓰지 않는다. 설치 원문은 `HCR-Evidence/deployments/r041-*`에 남긴다.

같은 원클릭 파일을 다시 누르면 source 설치는 중복하지 않지만, 사용자가 시작한 별도 실행은
새 timestamp 폴더에 기록된다. 자동 retry나 기존 실패를 덮는 재실행은 아니다.

## 실행 순서

```
R041 및 동결 의존 source 검사
→ 신규 115개 단위·합성 경계 검사
→ 기존 R038/R035 selector 연결 검사
→ EXP-21 전체 verify
→ 별도 실제 native 통합 self-test
→ EXP-22 prepare (조건 동결)
→ 108회 fresh native execute
→ 독립 audit
→ verify
→ evidence bundle
```

Native self-test에는 기존 2개 진단 입력과 min/max API coverage용 별도 2개 probe를 사용한다.
54개 treatment + R040 대조 6회 + 직접 API probe 1회로 구성되고, 본 108회와 분리한다.
실제 native 검사에 필요한 파일이 없으면 skip이나 합성 성공으로 바꾸지 않고 중단한다.

## 수동 설치 대안

별도 additive ZIP의 내용물을 루트에 병합한 경우 `Run-HCR-R041.bat`를 실행한다.
Python 직접 명령은 다음과 같다.

```powershell
python -X utf8 -B .\Run-HCR-R041.py
```

본 실험 없이 검사만 실행하려면 다음 명령을 사용한다.

```powershell
python -X utf8 -B .\Run-HCR-R041.py --check-only
```

이 옵션에서도 EXP-21 전체 verify와 별도 native self-test는 실행한다. 신규 108회 본 실험은 시작하지 않는다.

## 결과

```
HCR-Evidence/exp22/r041-<UTC timestamp>/
  plan.json
  environment.json
  attempts.jsonl
  raw/
  source/
  basis/exp21/
  upstream/
  analysis/
    summary.ko.md
    invariance_efficiency.csv
    mediation.csv
    scheduler_contrasts.csv
    scheduler_decisions.csv
    order_effects.csv
    paired.csv
    readouts.csv
    trials.csv
    audit.json
    records/
```

동일 위치의 `r041-<timestamp>_evidence.zip`에 원자료·실행 소스·분석이 묶인다.
`execution-logs/<timestamp>`에는 단계별 로그와 exit code가 남는다.
분석 결과의 핵심은 min/max가 모두 순열에 불변이면서도 서로 다른 비용을 보이는지다.
가설에 맞는 결과인지와 실행·audit의 정상 완료 여부는 구분한다.

## 실제 검증 범위

배포 검증 보고서의 완료/미실행 범위를 참고한다. 제공 환경에서는 Linux/Python 3.13.5로
단위·합성 검사와 설치기 roundtrip을 수행했다. Windows CMD/PowerShell, Python 3.12 실제
인터프리터, 전체 native 통합 및 108회 본 실험은 여기서 실행하지 않았다.
