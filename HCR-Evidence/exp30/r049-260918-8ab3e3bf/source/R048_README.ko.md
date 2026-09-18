# R048 / EXP-29 원클릭 실행 안내

## 실행

**`HCR_R048_EXP29_OneClick.cmd` 하나를 현재 저장소 최상위에 놓고 더블클릭한다.** ZIP을 따로 풀거나 HF1/HF2/HF3를 다시 실행할 필요가 없다. 기존 Python 3.12 이상과 Git을 사용하며 자동 설치·모델 다운로드·git pull/commit/push는 하지 않는다.

기준 commit은 `b10f571eb02e296b2ccb3f16eaf727da7d0e4d45`이다. 해당 commit이 현재 HEAD의 ancestor이고 사용한 native 및 R047 모듈이 고정된 원본과 일치해야 한다. 이미 R047 EXP-28을 완료한 원래 checkout에서 사용한다. 상위 commit이 있더라도 사용한 구현이 바뀌었으면 중단한다.

## 하는 일

관측 강도 0.02/0.10/0.25/0.50/0.75/0.92/1.00에서 실제 A 상태와 fixed 0.99를 기존 7처리로 비교한다. A 14회 공유, B 98조건이며 약한 A의 양성 채택 실패도 삭제하지 않는다. 상세 설계는 `docs/R048_DESIGN.ko.md`에 있다.

```text
패키지·기준선 확인 → 새 소스만 추가 설치
→ 부모 evidence를 별도 사본에 정확한 원본 bytes로 복원
→ 기존 부모 verify → 실행 source snapshot 고정
→ 기존 R047 테스트 + 새 R048 테스트
→ Git bytes/ignore 검사 → plan 동결
→ A 14 + B 98 실행 → 전체 raw/event 저장
→ 독립 audit → 독립 재집계 → byte 봉인
→ 봉인본 전체 verify → evidence ZIP 생성·재확인
```

테스트는 절대경로 runner가 `src/hcr/`를 먼저 로드한 다음 수집하므로 루트의 `hcr.py`와 충돌하지 않는다. 실패하면 콘솔에 하위 오류의 마지막 부분도 표시하고 전체 로그를 보존한다. 자동으로 재실행하거나 실패 단계를 skip하지 않는다.

## 기존 파일 보존

기존 native/R047 코드, manifest, 이전 실패 run과 원자료는 수정하지 않는다. R048 이름의 새 파일과 `HCR-Evidence/exp29/`에 한정된 Git 속성/ignore 파일만 추가한다. 같은 이름의 다른 파일이 있으면 덮어쓰지 않고 중단한다. 같은 내용이면 설치를 반복해도 기존 파일을 그대로 둔다. 매번 사용자가 실행하면 새로운 run ID를 만들며 이전 실행을 이어 쓰거나 덮어쓰지 않는다.

## EXP-28 줄바꿈 복원

부모 파일이 이미 원래 manifest와 일치하면 그대로 복사한다. Git이 LF/CRLF를 바꾼 경우는 **기존에 봉인한 해시를 복원 목표로 삼고 그 해시와 정확히 일치할 때만** 새 사본에 원본 bytes를 구성한다. 원본 폴더는 그대로 두며 어떤 파일을 복원했는지 `parent_byte_recovery.json`에 남긴다. 내용 수정, 누락 로그, 잘못된 manifest는 자동 수리하지 않는다.

새 evidence는 Git 줄바꿈 변환과 clean filter를 막는 경로 속성을 함께 저장한다. 실제 적용되는 속성·ignore 상태·clean 이후 bytes를 검사한다. 원격 저장소에 push하는 작업은 사용자 작업으로 남겨 둔다.

## 결과

`HCR-Evidence/exp29/r048-<UTC시각>-<ID>/`

| 파일/폴더 | 용도 |
|---|---|
| `analysis/summary.ko.md` | 모든 조건, 성공/실패/판정불가, 해석 범위 |
| `analysis/sources.csv` | A 정확도·채택·재사용 가용성 |
| `analysis/pairs.csv` | 실제값/fixed 비교와 비교 불가능 사유 |
| `analysis/checkpoints.csv` | 실제 실행된 공통 tick의 상태·goal·residual 차이 |
| `analysis/hypotheses.csv` | 사전 가설 전체 판정 |
| `analysis/trials.csv`, `vs_cold.csv` | raw/readout/adoption·각 비용·cold 비교 |
| `raw/`, `attempts.jsonl` | 원자료와 append-only 사건 기록 |
| `source/`, `basis/exp28/` | 실행 source snapshot과 검증한 부모 원본 사본 |
| `parent_byte_recovery.json` | 원본을 수정하지 않은 byte 복원 내역 |
| `raw_manifest.json`, `bundle_manifest.json` | byte hash 봉인 |
| `execution/` | 단계 시작·완료·self-test 출력과 실패 정보 |
| `VERIFY_BUNDLE.cmd` | 압축 해제본의 읽기 전용 전체 검증 |

폴더 옆에 `*_evidence.zip`, `.receipt.json`, `*_receipts/`가 생성된다. 봉인 이후의 검사 로그를 봉인 폴더 안에 추가하지 않는다. `failure.json`이 있으면 어느 단계에서 멈췄는지부터 확인한다. 실패 원자료나 부분 source는 자동 삭제하지 않는다.

## 검증 범위

배포된 validation 문서에는 실제 수행한 로컬 검사와 하지 않은 검사를 구분한다. 개발용 112개 계산과 합성 Git/부모 fixture는 정식 연구 결과가 아니다. Windows CMD/PowerShell 및 사용자의 전체 부모 EXP-28 corpus에 대한 실행은 사용자 원클릭에서 확인한다. 계산값·가설이 실패해도 장치·기록이 유효하면 그대로 보고하며 강도나 fixed 값을 바꾸지 않는다.
