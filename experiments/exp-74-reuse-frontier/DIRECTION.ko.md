# R28 방향성 판정

## 1. Executive Verdict

`conditional_consensus`: 기존 재사용 정책의 eligible 판정을 정확히 변환하고, 원래 6입력 수명에서 변환·검증을 포함한 비용을 비교한다. HIGH 토론은 과제 선택이며 구현의 독립 감사가 아니다.

## 2. Consensus Proposal

EXP-74는 reset / legacy_guarded / compiled_guarded × 4 streams × 4 blocks × 6 cells의 288회 native settle 비교다. 최대 46,080 tick, 전체 600초·단계 60초·worker 1·retry 0을 고정했다. 새 학습·세계 측정은 0회다.

## 3. Strong Consensus

기존 choose, native 수렴, 링크 순서와 상태 저장 규칙을 유지한다. Boolean만 교체하고 gate 전체의 q·rows 메타데이터 대체를 주장하지 않는다. stream·block 간 compiler와 상태를 재사용하지 않는다. 비용 이득이 없어도 유효한 결과다.

## 4. Material Disagreements

box 기반 gate는 기존 허용 경계를 가로지르면 정책 변경이 성능 차이에 섞일 수 있어 제외했다. 미래 입력의 reset 품질 증명은 기존 정책 구현의 동치 비용 연구와 구분했다. 저장 자료만으로는 실제 변환 비용을 알 수 없어 서버 실험을 선택했다. 원래 6입력 대신 24입력 이상을 공유 수명으로 삼거나 임의 5% 개선 문턱을 두지 않는다.

## 5. Decision by Axis

| 축 | 결정 |
|---|---|
| 비중복성 | R27 저장 기록 사후 인증 뒤 runtime 변환·검증 비용을 관측 |
| 의미 | eligible Boolean, 선택·초기 상태·kernel·cache 전이의 타입/float bit 동일성 |
| 증명 | 같은 input row·단조성·고정 goal row와 인접 binary64 최소성 연결 |
| 수명 | 매 6입력 새 process·빈 상태·새 compiler |
| 프로토콜 | 기존 24입력 개발 부하를 고정 4블록으로 반복 |
| 채택 | 동치·관측 품질 통과 후 모든 블록의 CPU/wall이 양 baseline보다 작을 때만 제한적 개선 관측 |

## 6. Evidence

R26의 eligible 소비 경계와 수명, R27의 사후 인증 및 조건부 비용 산술을 원문에서 확인했다. R27의 CPU headroom 약 2.08%는 변환 구현의 실측 이득이 아니다. claim별 원문 SHA와 축 연결은 `decision-record.json`에 있다.

## 7. Required Actions

native 실행 전에 source binding, 단조성 유도와 별도 다항식 검산을 통과한다. 원격 실행에서는 96개 legacy/compiled 대응 cell과 96개 reset 품질 대조를 검사한다. config/program/source 결속, 변환·검증·lookup·상태·결과 구성 비용을 포함한다. process CPU/wall에는 import·최종 직렬화·파일 출력도 포함해 별도 보고한다. 불일치·한도 초과는 중단하고 반복·수명·threshold를 사후 조정하지 않는다.

## 8. Optional Optimizations

없음. threshold의 사전 저장·전역 cache·수명 연장은 이번 연구에서 제외한다.

## 9. Unresolved

실제 비용 이득과 서버 native 동치는 실행 전에는 미관측이다. 기존 24입력은 개발 부하이며 미래 입력 품질의 독립 표본이 아니다. 범영역 native/reset 품질 보장은 이번 연구의 결론에 포함하지 않는다.

## 10. Method / Run Summary

4개 blind 관점(수학·실험 타당성·비용·구조), 4개 비원저자 교차검토, 별도 fresh Judge 1명이 완료했다. worker 5명, specialist/reserve와 adaptive 재숙고 0명이다. 요청 모델은 노출된 gpt-6.1-sol/xhigh이며 Terra 선호는 가용하지 않았다. 실제 provider 모델 내부와 토큰 사용량은 NOT_OBSERVABLE이다. assurance `independent`는 관찰한 절차를 뜻하며 provider 격리의 외부 증명이 아니다. Judge는 정제 dossier로 판정했으며 원문을 직접 재검증한 것으로 표현하지 않는다.
