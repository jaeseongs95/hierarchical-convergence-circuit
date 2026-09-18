# R045 / EXP-26 — 최종 지지 경로의 직접 회로 사용 진단

기준선: `3bfeb64af877a7512071798fd77d8eba839760a1` (`main`, R044).

EXP-25에서 macro 적용은 관찰됐지만 최종 채택된 양성 경로에는 직접적인 circuit use가 없었다. Expansion 감소도 native ticks 감소로 이어지지 않았다. EXP-26은 **지원되는 단일 경로에 회로가 직접 쓰일 때 무엇이 대체되는가**를 검사한다. 엔진·회로 선택·pool·scheduler를 고치지 않는다.

## 실행

배포된 **`HCR_R045_EXP26_OneClick.cmd`를 기존 저장소 루트에 놓고 실행**한다. 별도의 압축 해제나 패치 명령은 필요 없다. 기존 설치된 Python 3.12 이상을 찾으며, 설치·다운로드·서버 시작·Git 변경은 하지 않는다.

소스 ZIP으로 검토할 때는 압축 구조가 저장소 루트 기준임에 유의한다. ZIP을 덮어붙이는 대신 OneClick CMD를 사용해야 패치 충돌·기준선 검사가 먼저 실행된다. 설치 뒤에는 `Run-HCR-R045.cmd`가 같은 실험을 새 실행 폴더에 시작한다.

자동 순서:

```text
기준선·파일 무결성 확인 → 충돌 없는 R045 추가 파일 설치
→ 전체 의존성/API 검사 → 기존 R044 및 신규 R045 단위검사
→ EXP-25 전체 raw 재검증 → native 회귀 4조건 + 별도 smoke 6조건
→ plan 동결 → EXP-26 실제 native 12조건
→ 독립 audit → 재계산 verify → CSV/한국어 summary/evidence ZIP
```

최초 실패에서 중단한다. 재시도·관측 보완·ID/proof 수정·기존 결과 덮어쓰기·검사 skip은 없다. 실패 로그, 부분 raw, traceback 및 불완전 forensic ZIP은 남긴다.

## 새 연구 조건

| 계열 | 입력 | 조건 수 | 목적 |
|---|---|---:|---|
| `supported_len2` | `v0 → v1 → v2`, 두 관측 모두 `+0.92` | 4 | 최종 양성 지지 경로의 직접 사용 및 계산 대체 |
| `no_match_len1` | `v0 → v2`, 관측 `+0.92` | 4 | 구조적 매칭 없이도 발생하는 회로 탐색 비용 |
| `conflict_len2` | 동일 길이 2 경로의 둘째 관측만 `-0.92` | 4 | 구조적 매칭과 관측 충돌 거부의 구분 |

각 계열은 `회로 ON/OFF × identity/fresh_ids`이다. 본 실험 총 12조건, gate 비교 6쌍이며 **주요 길이 2 양성 비교는 2쌍**이다. 12개 독립 문제나 6개 독립 topology가 아니다. len1은 다른 topology의 별도 대조이고, conflict는 같은 session의 수정·재학습이 아닌 정적 관측 반전이다.

## 산출물

- `HCR-Evidence/exp26/r045-<UTC>-<suffix>/analysis/summary.ko.md`: 한국어 결과 및 주장 범위.
- `comparisons.csv`, `trials.csv`, `cost_differences.csv`: 가족별 ON/OFF와 각 비용 단위.
- `candidate_exposure.csv`, `binding_scans.csv`, `expansion_actions.csv`: 매칭·적격·macro의 단계별 증거.
- `decision_networks.csv`, `network_costs.csv`: decision 계산 서명과 pool/decision 비용.
- `ID_controls.csv`, `conflict_controls.csv`, `readouts.csv`: ID 및 관측 대조.
- `raw/*.json`, `attempts.jsonl`, `source/`, `upstream/`, `basis/exp25/`: 원자료와 동결 기준.
- `HCR-Evidence/exp26/r045-<UTC>-<suffix>_evidence.zip`: 실행 전 검증 로그·native self-test를 포함한 묶음.

본문의 `verified`는 근거·실행·계수 검사가 통과했음을 뜻한다. 회로가 유익했다거나 과학적 예측이 지지됐다는 뜻이 아니다. 긍정·부정·측정 불가 판정은 별도 필드다.

설계는 `docs/R045_DESIGN.ko.md`, 사용·실패 처리는 `docs/R045_USAGE.ko.md`, 작성 환경의 실제 검증 범위는 `validation/r045/검증보고서.md`에 있다.
