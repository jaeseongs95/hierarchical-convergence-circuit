# R0.4.2 / EXP-23 — ID와 경로 역할의 결합 분리

기준선: `11f43790c0cb1b4732199ae4fb17c5bbbed4cd5b`의 R041 소스와 EXP-22 실행 결과.
기존 `src/hcr`, R041 실행기, selector, scheduler, auditor, 이전 evidence는 수정하지 않는 **추가 패치**다.

## 실행

이 ZIP의 내용을 저장소 **루트에 병합**한다. `Run-HCR-R041.py` 옆에 `Run-HCR-R042.py`가 생기면 맞다.
그다음 `Run-HCR-R042.bat`를 더블클릭하거나 아래 명령을 실행한다.

```powershell
python -X utf8 -B Run-HCR-R042.py
```

Python 3.12 이상이 필요하며 새 패키지를 설치하지 않는다. Git commit/push, LLM 호출, 다운로드, 자동 재시도를 하지 않는다.

## 질문과 조건

“작은 ID를 먼저 처리하는 규칙 자체가 좋은가, 아니면 현재 ID 배치가 지원 경로 S를 먼저 처리하게 만든 것인가?”를 구분한다.

`legacy / online_support`를 고정하고 **ID 배치 2 × 배열 순열 6 × scheduler 2 = 24 native 조건**을 실행한다.

| 배치 | e0 | e1 | e2 | e3 | e4 | e5 | e6 |
|---|---|---|---|---|---|---|---|
| identity | e0 | e1 | e2 | e3 | e4 | e5 | e6 |
| swap_SD | e4 | e5 | e2 | e3 | e0 | e1 | e6 |

S는 원래 `e0→e1`, D는 원래 `e4→e5→e6`이다. `swap_SD`는 두 경로의 ID 우선순위를 바꾸되 vocabulary, 문자열 길이, edge slots, 내부 분기 순서, node IDs, 관계, score, episode, revision을 유지한다. 평가 world의 edge key도 같은 대응으로 옮기지만 world는 실행기에 전달하지 않는다.

기존 memory/config는 그대로 유지한다. 이 고정 baseline에서 current edge ID가 memory/config의 JSON key/value에 들어 있지 않은지 검사하고, 발견되면 추측해서 고치지 않고 중단한다.

## 자동 실행 순서

패키지·이전 소스 무결성 → 신규 단위 검사 → EXP-22 전체 재검산 → native 통합 smoke 검사 4조건 → prepare → execute 24조건 → 독립 audit → 재계산 verify → evidence ZIP.

native smoke 4조건은 설치/연동 검사다. 본 실험 24조건에 합산하지 않으며 해당 원문은 execution-logs 아래 별도로 보존한다.

## 결과

`HCR-Evidence/exp23/r042-<UTC timestamp>/analysis/summary.ko.md`가 주 보고서다.
`id_role_reversal.csv`는 순열별 비용 역전, `comparisons.csv`는 동일 scheduler와 교차 scheduler의 inverse-ID 경로 대응을 비교한다.

반전 없음, 비용 동률, 순열 민감도 유지, 오답 또는 abstention도 유효한 관찰이다. **audit 통과가 이 가설의 성공을 뜻하지 않는다.**

설계는 `docs/R042_DESIGN.ko.md`, 실행 옵션은 `docs/R042_USAGE.ko.md`, 생성 환경에서 실제 수행한 검증 범위는 `validation/r042/검증보고서.md`에 있다.
