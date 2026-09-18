# R049 / EXP-30 HF1 — 탐색 회귀의 정확한 해시와 수치 동등성 분리

## 원인과 확인 범위

사용자 로그의 실패 지점은 `test_native_prior_exploration_regression`이다. 기존 `evaluate.py`는 매 tick의 실수 상태와 residual을 JSON으로 직렬화한 SHA256이 Linux에서 계산한 과거 탐색 SHA256과 완전히 같은지만 `dynamics_equal`로 판정했다. 테스트는 16개 모두 이 값이 True여야 통과했다.

반면 같은 로그에서 독립 수치·proof 감사는 통과했다. 따라서 확인된 구현 문제는 **교차 환경의 수치 회귀 판정에 raw-byte 식별 기준만 사용하고, 어떤 값이 얼마나 다른지 기록하지 않았다는 점**이다. 현재 제공된 로그에는 사용자 PC의 차이값이 없으므로 특정 Windows 수학 라이브러리나 Python 버전이 실제 차이를 만들었다고 단정하지 않는다. HF1은 사용자 PC에서 이 차이를 실제로 계산하고 그 결과에 따라 설치를 진행하거나 멈춘다.

Python `math`의 상당수 구현은 플랫폼 C 수학 라이브러리를 사용한다. 부동소수점의 아주 작은 차이만으로도 직렬화된 전체 SHA256은 달라질 수 있다. 이 일반적 가능성과 해당 사용자 실행에서 관찰된 구체적 원인은 별개다. 공식 문서: https://docs.python.org/3.12/library/math.html

## 실행

`HCR_R049_EXP30_Hotfix1_OneClick.cmd`를 기존 저장소 최상위 폴더에 놓고 한 번 실행한다.

```text
D:\codex\진짜미친짓\hierarchical-convergence-circuit\
```

현재 R049 설치 상태 그대로 사용한다. 과거 R047/HF1/HF2/HF3를 다시 적용하지 않는다. 기존 실패 폴더 `HCR-Evidence/exp30/r049-260918-a8cbbcd4`는 변경·삭제하지 않는다.

원클릭은 패키지 checksum, Git 기준선, R048/native 소스, 알려진 R049 원본 또는 HF1 파일 상태를 검사한다. 승인된 원본/패치 내용 외의 편집은 중단하며 현재 파일의 hash를 임의로 새 기준으로 채택하지 않는다.

## 설치 전의 실제 진단

임시 staging source에서 기존 native를 호출하여 16개 탐색 대조를 각각 한 번 실행한다. 이 실행은 **implementation_validation/self-test**이며 정식 연구 표본으로 세지 않는다. 기존 native, `device.py`, `audit.py`, `spec.py`는 변경하지 않는다.

원래 SHA256 8개와 일치하는 전체 탐색 궤적을 포함했다. 그 원본 파일 자체의 SHA256도 이전 `R049_PRIOR_EXPLORATION.json`에 적힌 `525432b15b4320a6d8615919a7f22246ffd659f859c6e5058a4970e5516ce44e`와 동일하다. 현재 실행으로 expected를 재생성하거나 실패한 digest를 덮어쓰지 않는다.

다음 결과는 별도 deployment 폴더에 보존된다.

- `diagnosis.json`: 16조건의 정확 SHA256 일치, 수치·이산 판단 동등성, 최대 차이와 위치, 진단 분류.
- `diagnostic_raw/`: 진단에 실제 사용한 native 기록. 기존 실패 실행의 원자료라고 재명명하지 않는다.
- `tests-staged.txt`: 변경 후 전체 self-test 출력.
- `backup/`, `transaction.json`, `writes.jsonl`: 교체 전 bytes와 적용 이력.
- `snapshot-before.json`, `snapshot-after.json`: 실제 package_check/copy_source를 통한 전후 snapshot 검증.
- `failure.json` 또는 `rollback.json`: 최초 오류와 복원 결과.

위치: `HCR-Evidence/deployments/r049-hf1-<ID>/`.

진단이 수치 또는 판단의 실질적 차이를 발견하면 **소스를 적용하지 않고 중단**한다. 이 경우 `diagnosis.json`에 구체적인 차이가 남는다. 원인이 다른데도 이 패치로 무조건 통과시키지 않는다.

## 바뀌는 검증 계약

정확한 SHA256 비교는 없애지 않는다. `dynamics_equal`은 계속 원래 SHA256의 완전 일치만 뜻한다. 새로 `regression_passed`를 추가하여 다음 조건을 모두 요구한다.

1. 입력·config·저장 graph·top-down·초기조건이 같다.
2. 전체 tick 길이, tick 번호, 매 tick stable_steps, 종료 tick/status가 정확히 같다.
3. 모든 실행 tick의 모든 group activation과 residual, 최종 상태·margin의 절대차가 `2e-12` 이하다.
4. 매 tick의 0.5 부호와 margin 기준 통과 여부, raw 결과·채택·censored 여부·proof 경계·D_DAG·갱신/신호 횟수가 정확히 같다.
5. 기존 독립 scalar/proof/event 감사도 그대로 통과한다.

`2e-12`는 기존 독립 수치 감사의 절대 허용오차와 같다. kernel의 종료 residual 기준 `1e-6`, patience 4 또는 실험 가설을 변경하는 값이 아니다. raw를 반올림하거나 틀린 값을 수정하지 않는다. 아주 작은 수치차라도 부호·정지·판단이 바뀌면 회귀 불일치로 처리한다.

원자료, source, manifest, Git 배포 bytes 검증에는 여전히 **정확한 해시 일치**를 요구한다. 서로 다른 실행의 수치 동등성과 동일 파일의 무결성은 분리한다.

## 수정 범위

기존 파일 3개와 R049 manifest를 갱신한다.

- `evaluate.py`: 전체 기준 궤적과의 비교 결과 추가.
- `reporting.py`: 해시와 수치·이산 판단 회귀 결과를 구분해 출력.
- `tests/test_r049_device.py`: 문제의 assertion만 새 회귀 조건으로 변경하고 실패 상세 출력.
- `R049_MANIFEST.json`: 위 변경과 추가 파일의 승인된 해시를 함께 등록.

비교기, 원래 전체 탐색 기록, 오류주입 테스트, 로컬 진단·안전 적용 스크립트, 이 안내와 변경 증명서를 추가한다. `docs/R049_HF1_CHANGE.json`에 원래 manifest를 보존한다.

native 8파일, 실행 `device.py`, 기존 독립 `audit.py`, `spec.py`, 동결 plan, 관측·world, 48조건, top-down/초기값, bias/damping, proof 규칙, 가설·판정 기준, 원래 탐색 digest 파일, 이전 evidence는 변경하지 않는다.

## 적용 절차

```text
원본 및 패키지 검증
→ staging에서 실제 로컬 16조건 진단
→ 수치·이산 판단의 실질적 불일치이면 중단
→ 수정 후 전체 테스트
→ 실제 package_check와 source snapshot 검증
→ 수정 전 bytes 백업
→ 소스 교체, manifest는 마지막에 갱신
→ 실제 설치본과 snapshot 재검증
→ 새 run ID로 기존 R049 pipeline을 한 번 실행
```

파일별 교체는 Python `os.replace`를 사용한다. 여러 파일의 교체 전체가 원자적이라고 주장하지 않는다. 잡힌 교체·검증 오류에는 역순 복원을 시도하고 완전 복원 여부를 기록한다. 동시에 다른 도구가 파일을 바꾸면 그 편집을 덮어쓰지 않고 중단한다. 전원 차단으로 중간 상태가 남더라도 알려진 원본/패치 bytes의 혼합만 허용하며 임의의 손상은 승인하지 않는다.

실제 정식 48조건 실행은 기존 pipeline에서 부모 EXP-29 검증과 상속 테스트를 포함해 다시 수행한다. 기존 실패 run을 덮어쓰거나 이어서 성공한 것으로 바꾸지 않는다. 자동 설치, 모델 변경, 자동 재시도, git add/commit/push는 하지 않는다.

## 개발 검증의 경계

이 패키지 작성 환경은 Linux/Python 3.13이다. native 핵심 8파일은 commit의 Git blob과 동일한 bytes로 검증한 후 실행했다. 원래 71개 테스트와 추가 수치 회귀 오류주입 테스트를 실제 native로 실행했다. 미세한 exp 결과 차이를 주입하여 기존 해시 비교는 실패하지만 독립 감사와 수치 회귀는 통과하는 상황을 재현했으며, 큰 수치차·부호·판단·정지 변화는 계속 거부함을 검사했다.

Windows CMD/PowerShell 실행, 사용자의 이번 실패 당시 정확한 수치차, 전체 부모 EXP-29 재생은 이 환경에서 수행하지 않았다. 설치 시 로컬 진단과 원래 pipeline이 이를 실제 조건에서 확인한다. 개발 진단은 정식 EXP-30 연구 결과가 아니다.
