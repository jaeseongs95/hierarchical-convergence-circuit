# R051 소스 검증 결과

상태: `SOURCE_VALIDATED`. EXP-32 본실험은 아직 실행하지 않았다.

성공 run: `r051-20260919T132210Z-4f174055e0`.

- `Run-HCR-R051.cmd --validate-only` 실제 Windows 실행 성공.
- 신규 self-test 13개 통과, 실패·오류·skip 0.
- native smoke 2개 기준선·8개 paired arm 독립 상태/proof/support/개입 검산 통과.
- 최종 core 회귀 602개 실행: 599개 통과, 기존 Windows symlink skip 3개. 실패·오류·새 skip 0.
- source·raw·baseline·intervention·progress inventory와 hash 검산 통과.
- CSV·Markdown과 freshly audited rows의 렌더링 일치 확인.
- 최종 bundle manifest, ZIP CRC 및 216개 파일의 archive/disk SHA-256 일치 확인.
- experiment index 33개 항목 경로 검사 통과. 기본 EXP-30 유지.
- core, core tests, R048/R049/R050 소스·manifest 변경 없음.

첫 validation run `r051-20260919T131752Z-33818e3861`은 회귀 실행 경로 결함으로 실패했다.
이전 실패를 포함해 개발 중 전체 회귀는 총 2회였으며, 최종 수정본의 전체 회귀는 1회다.
첫 실패 evidence를 보존했고 자동 retry 기능을 추가하지 않았다.
수정 후 기존 R02 CLI 검사 14개가 별도 target 검사에서 통과했다.
원인과 변경은 [DEVELOPMENT_FAILURES.ko.md](DEVELOPMENT_FAILURES.ko.md)에 기록했다.

구현 검증의 smoke/positive sanity는 EXP-32 연구 결과에 포함하지 않는다.
본실험 4개 기준선·16개 분기 결과나 가설 지지 여부는 아직 보고할 수 없다.

## 실행

저장소 루트의 `Run-HCR-R051.cmd`를 실행하면 검증 후 본실험을 1회 수행한다.
검증만 할 때는 `Run-HCR-R051.cmd --validate-only`를 사용한다.
실패 시 원자료와 로그를 보존하고 중단한다. 재실행은 별도 고유 evidence 경로를 사용한다.

## 근거

- [최종 상태](../../HCR-Evidence/r051-validation/r051-20260919T132210Z-4f174055e0/result.json)
- [core 회귀](../../HCR-Evidence/r051-validation/r051-20260919T132210Z-4f174055e0/validation/core_regression.json)
- [native smoke 독립 검산](../../HCR-Evidence/r051-validation/r051-20260919T132210Z-4f174055e0/analysis/audit.json)
- [최초 실패](../../HCR-Evidence/r051-validation/r051-20260919T131752Z-33818e3861/failure.json)
- [결과 토론](DISCUSSION.ko.md)
- [동결 설계](design.ko.md)
