# 현재 저장소 탐색 안내

확인 기준: `83d07f43cb9b138cadfcdbdd1f0e40bcfb5857e9`. 구조 정리 v1이며 연구 구현 버전을 올리거나 새로운 결과를 주장하지 않는다.

| 구획 | 현재 역할 |
|---|---|
| `src/hcr/` | 기존 공통 엔진. 파일·import·동작 유지 |
| `tools/r0xx_*/` | 기존 실험별 장치/검산기. revision 경로 유지 |
| `experiments/INDEX.json` | EXP↔설계↔revision↔원자료 경로 색인 |
| `evidence/` | 기존 claim/구현 상태 registry. 이번 정리에서 상태 변경 없음 |
| `HCR-Evidence/` | 실행 원자료·실패·source snapshot. 이동/재작성 없음 |
| `validation/` | 기존 구현 검증 기록 |
| `theory/`, `formalism/`, `architecture/` | 가설·정의·계산 구조 |
| `docs/` | 원 설계/사용법/동결 문서. 기존 문서 바이트 유지 |
| `archive/distributions/` | 참조되지 않는 과거 설치용 원클릭 배포파일 |
| `Run-HCR.cmd` | 설치된 실험 Python 진입점 호출. 패치/설치 아님 |

## 이번에 하지 않는 변경

`HCR-Evidence`→`results` 변경, 엔진/도구 import 재배치, 과거 manifest 수정, 기존 README 덮어쓰기를 하지 않는다. 기존 README도 `RELEASE_MANIFEST.json`의 해시 대상이므로 최신 진입 안내는 [START_HERE](../../START_HERE.ko.md)로 제공한다.

이번 작업은 탐색과 배포파일 정리를 위한 1차 migration이다. 모든 루트 파일을 이동한 완전한 패키지 재설계가 아니다.
검산기는 원자료를 다시 생성하거나 정답을 보정하지 않는다. 기존 source/evidence의 전후 동일성 및 정리 계획의 이행을 별도 감사한다.
