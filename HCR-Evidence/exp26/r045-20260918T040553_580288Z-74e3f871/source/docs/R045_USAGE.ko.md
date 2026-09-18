# R045 설치·실행 안내

## 권장 실행

`HCR_R045_EXP26_OneClick.cmd`를 현재 R044 저장소의 최상위 폴더에 넣고 더블클릭한다. `src`, `tools`, `HCR-Evidence`, `R044_MANIFEST.json`이 있는 폴더다. 별도 ZIP 해제·명령 입력은 필요 없다.

CMD에 소스 ZIP이 포함되어 있다. 내장 ZIP 해시 확인 후 설치기가 기존 R044와 전체 의존 소스 무결성을 확인하고 **새 R045 파일만** 추가한다. 설치 후 검사·plan·실제 native 실행·검산·결과 압축까지 이어진다. 저장소 root가 아니거나 기준선이 바뀌었으면 중단한다.

기존 Python 3.12 이상이 필요하다. `HCR_PYTHON`, 저장소 `.venv`, 사용자 Python 설치 경로 및 PATH에서 실제 설치된 interpreter만 찾는다. Microsoft Store 실행 alias와 자동 설치 경로는 사용하지 않는다. 필요한 패키지·모델을 내려받거나 Ollama를 시작하지 않는다. 이 실험은 기존 native Python 엔진을 사용하며 LLM 요청을 하지 않는다.

## 사용자 수정 및 반복 실행

기존 R044 소스·의존성에 수정이 있으면 자동으로 원복하지 않는다. 로그의 최초 충돌 파일과 현재 Git 변경을 확인해야 한다. Git pull, checkout, commit, push는 실행기가 수행하지 않는다. HEAD 문자열만 강제 비교하지는 않고 고정된 R044 manifest와 의존 소스 해시를 기준으로 허용 여부를 검사한다. 다른 문서만 추가한 commit 때문에 원자료가 바뀌었다고 오판하지 않는다.

R045 파일이 이미 동일한 내용으로 설치됐으면 재설치하지 않는다. 다른 내용이면 중단한다. 재실행은 UTC와 임의 suffix를 갖는 새 run을 만든다. 이전 raw와 실패 결과를 삭제하거나 같은 run을 재시작하지 않는다. 사람이 다시 실행했다면 다른 intervention/run으로 보존된다.

## 검사 범위

기존 R044 단위검사, 신규 R045 단위검사, EXP-25 전체 저장 raw verify, 부모 4조건 live 회귀와 별도 smoke 6조건이 먼저 실행된다. 어느 단계든 실패하면 본 실험은 실행하지 않는다. Native self-test는 synthetic fallback이나 skip으로 대체되지 않는다.

제작 환경에서 실행한 검사와 사용자 환경에서 실행할 검사는 다르다. 작성 환경의 90개 단위검사는 합성 fixture·mock을 사용하는 구현 검사다. 전체 native dependency가 없기 때문에 실제 엔진 실행·독립 native replay·Windows PowerShell 더블클릭은 제작 환경에서 검증하지 못했다. 자세한 실제 로그는 `validation/r045/`를 따른다.

## 파일 위치

```text
HCR-Evidence/
  deployments/r045-<UTC>/              설치한 파일·실패 기록
  deployments/r045-bootstrap-<UTC>/    Python 탐색·설치·실행 transcript
  exp26/
    execution-logs/<UTC-suffix>/
      01.log ... 10.log                 각 단계 stdout/stderr
      stages.jsonl                     최초 실행 순서·종료 코드
      execution.json                   전체 성공/실패 상태
      native-selftest/                 10회 검증의 raw/events/audits
      sealed-execution/                bundle 직전 고정한 검증 로그
    r045-<UTC-suffix>.plan.json         사전 동결 계획
    r045-<UTC-suffix>/
      plan.json
      environment.json
      source/                          실제 사용 source snapshot
      upstream/                        학습 계보
      basis/exp25/                     부모 manifest/plan/audit/raw 4개
      attempts.jsonl
      raw/t0000.json ... t0011.json
      manifest.json
      analysis/                        summary, audit, CSV, 독립 records
    r045-<UTC-suffix>_evidence.zip
```

정상 evidence ZIP에는 run과 **bundle 전에 끝난 단계의 로그·native self-test**가 포함된다. bundle 실행 자체의 마지막 `10.log`와 최종 `execution.json`은 무한 자기포함을 피하기 위해 ZIP 밖의 실행 로그 폴더에 남는다. ZIP 안의 `prebundle.json`은 bundle 전 검사·실행·검산이 끝났음을 기록한다.

실패 시 `execution-logs/<UTC-suffix>_forensic.zip`에 부분 run과 실행 로그를 담는다. forensic ZIP도 만들지 못한 디스크/I/O 상황에서는 기존 파일을 그대로 남기고 그 실패를 출력한다. 성공 ZIP처럼 취급하지 않는다.

## 결과 읽기

먼저 `analysis/audit.json`으로 원자료 검산 여부를 보고 `summary.ko.md`에서 family별 사전 예측을 읽는다. `H_kernel` 실패와 audit 성공은 양립한다. macro가 없거나 정답을 채택하지 않은 결과도 삭제하지 않는다. 모든 비용은 실제 원값과 차이를 기록한다.

주요 해석 순서는 `candidate_exposure.csv → expansion_actions.csv → 최종 직접 사용 → decision_networks.csv/network_costs.csv → comparisons.csv`이다. family 간 원자료를 함께 보되 len1-vs-len2 차이를 단일 인과효과로 바꾸지 않는다.

고급 명령은 설치된 `Run-HCR-R045.py --help` 및 `scripts/r045_cli.py --help`에 있다. 일반 실행은 원클릭 파일 하나로 충분하다.
