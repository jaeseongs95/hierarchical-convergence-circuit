# EXP-09 r2 — 기준선 원인분리·비용 계측 후속 소스

현재 R0.2 engine 동작은 유지한다. 다음 실행은 기존 `probe.py`의 후속 비교이며 R0.2.1 구현과 구분한다.

- 실행·결과 위치·검산 범위: [EXP-09 r2](docs/EXP09_R2.ko.md)
- 비교: direct/reload, memory × 측정 × routing, 동일 점수 revision, training 3/6/9, 순서 교대 비용쌍.
- 관측할 것: 회로 약화/재선택, 음의 정답 이후 학습 내용, pool/decision 연산.
- 순수 도구 시험 51개는 작성 환경에서 통과했다. 실제 새 probe는 사용자 실행 후 판정한다.
- R0.2.1 session/snapshot/restore/resume은 이 결과를 기준선에 기록한 뒤 이어간다.

---

# HCR 현재 기준선과 개발·연구 로드맵

## 현재 상태

R0.2 Windows/Python 3.12.10 사용자 실행: 136/136 테스트, demo complete, audit verified/differences=[] 보고. 이후 기준선 패키지 적용, 보조 도구 16/16 테스트, capture 생성 완료도 보고됐다. capture에는 실행 소스 30개와 run 파일 11개가 있으며 원본 변경/새 inference는 없었다.

이는 사용자 로그로 수용한 범위다. 이 패치 작성 환경에서 원시 capture를 읽거나 EXP-09 새 비교를 실행한 것은 아니다. 상세 비용·재오답 원인은 아직 그 자료와 대조 실험으로 분석한다.

## 기준 문서

- [현재 전체 로드맵](docs/HCR_MASTER_ROADMAP.ko.md)
- [24개 개념 추적표](docs/CONCEPT_COVERAGE.ko.md)
- [소스 대조와 수정 이유](docs/CONCEPT_PATCH_REVIEW.ko.md)
- [기준선 수용](docs/R02_BASELINE.ko.md) / [EXP-09](docs/R02_BASELINE_PROTOCOL.ko.md)
- [substrate/I/F 계약](architecture/substrate-contract.ko.md)
- [오류 taxonomy](formalism/failure-taxonomy.ko.md)

## 구현 순서

| 단계 | 구현 | 동시에 유지할 연구 과제 |
|---|---|---|
| R0.2 baseline | 기존 실행·capture 보존, 원시 분석 | EXP-09와 기존 trace의 설명 포함 관계 관찰 |
| R0.2.1 | 시간·state·snapshot/restore/resume | 오류 근거와 readout/설명 계측 계약 |
| R0.3 | 제한된 M specialization/통합 | 같은 총예산·근거 중복·선택/실행 구별 |
| R0.4 | Fork/Join, 회로 간 연결·학습·pruning | binding·현실 검증·revisability |
| R0.5a/b | 지속 activation/readout / 제한된 새 조합 | 다중안정의 basin과 trajectory switching 구별 |
| R0.6 | A adaptation, cross-A 승격·재귀 | EXP-05 공통 primitive/low-mid-high symbolic 과제 |
| R0.7 | A/D/M 단독·두 축·세 축 일반화 | 지원 정보·LLM/HCR evidence 분리 |
| B0/B1/B2 | 자원·I/F 계약 / local event backend / 물리 prototype | 동기 reference·비용·소자/측정 경계 |

EXP-03·04·05·06은 이미 존재하던 초안이며 관련 버전과 함께 수행한다. 별도 R0.8/0.9 뒤로 미뤄서 현재 기반과 분리하지 않는다. B0는 설계 계약이고 B1/B2 착수는 실제 선행 조건에 따른다.

다음 기능 구현은 R0.2.1이다. 이번 패치는 개념 누락/오독을 막는 문서·정적 추적·기존 기록 분석만 추가하며 엔진 버전 0.2.0과 실행 의미를 유지한다. 과거 로드맵·배포 당시 정적검사·source/run hash는 변경하지 않는다.
