# R046 / EXP-27 — 생각 A의 산출물을 생각 B에 전달

## 실행
`HCR_R046_EXP27_OneClick.cmd` 하나를 현재 저장소 루트에 두고 실행한다. ZIP은 별도로 해제할 필요 없다. 설치 후에는 `Run-HCR-R046.cmd`로 실행할 수 있다. 기본 부모는 `HCR-Evidence/exp26/r045-20260918T040553_580288Z-74e3f871`이며 다른 내용으로 자동 대체하지 않는다.

필수 과정: 기준선·파일 검사 → 기존 EXP-26 전체 verify → 단위·native-core tests → EXP-26 OFF core 회귀 6조건 → plan 동결 → 원천 A 2개·후속 B 24조건 → 독립 audit → 재계산 verify → evidence ZIP. 어느 검사도 실패하면 건너뛰지 않는다.

## 실제로 구현한 것
같은 episode에서 A(u→w)를 계산하고 다음 질문 B(u→z)를 처리한다. cold, 수치 state carry, 일반 dependency-aware proof memo, typed relation carry를 비교한다. relation/memo는 **B 수렴 전에** A proof와 새 관측을 조합해 B 후보를 만든다. native kernel은 그 뒤 동일한 원관측으로 B를 따로 확인한다. candidate가 있어도 native 확인이 없으면 양성 채택하지 않고 두 판단을 보존한다.

이것은 기존 native **핵심 함수**를 호출하는 새로운 순차 계산 어댑터다. 기존 AdaptiveSession이나 학습회로 pool의 성능을 직접 확장 측정한 것으로 표시하지 않는다. native source를 수정하거나 monkeypatch하지 않는다. native search와 full decision program은 모든 군에서 유지한다. 이번 relation carry가 줄일 수 있는 것은 proof 생성 작업이며, native decision을 생략하는 구조가 아니다.

학습 memory는 같은 원본을 보존하지만 이번 adapter에서는 학습회로를 검색·실행하지 않는다. 새 학습, pool→decision 상태 전달, 일반적인 계층 신경회로 효과를 측정하는 실험도 아니다. 수치 상태 전달은 A decision→B decision이며 relation/proof 전달과 결합하지 않았다.

## 대조
1. 정상 연장: u→v→w 다음에 w→z를 추가한다.
2. 대상 불일치: 같은 True인 A가 있어도 p→q→r→s에는 전용하지 않는다.
3. 근거 변경: v→w 관측을 반전하면 기존 A 결과의 재사용을 거부하고 재계산한다.

각 상황에서 일관된 ID 재명명 대조를 둔다. 같은 원천 A를 공유한 B 조건들을 독립 학습/독립 문제로 중복 집계하지 않는다. 일반 proof memo에도 같은 근거 검증과 참조 재사용을 허용하므로 relation군에 유리하게 약한 기준선을 만들지 않는다.

## 결과
`HCR-Evidence/exp27/r046-<run-id>/analysis/summary.ko.md`가 주 보고서다.

- `pairs.csv`: 각 carry군 대 cold 및 사전 예측 판정.
- `memo_controls.csv`: 일반 proof memo와 typed relation 비교.
- `transfer_maps.csv`, `proof_refs.csv`: 실제 state 대응과 A node 참조.
- `signatures.csv`: 원형 program/drive, 유효 drive, 수치 궤적을 분리한 서명.
- `cost_differences.csv`: native 계수·전달 byte·binding·proof 작업량. 다른 단위를 합산하지 않는다.

원자료에는 최초 후보·후속 native 판정·최종 채택을 구별해 남긴다. D_DAG는 A의 외부 parent까지 펼쳐 재계산한다. 숫자 동일성, proof identity, 최신 근거의 유효성은 서로 다른 지표다. byte 수는 ID 문자열 길이에 영향을 받으므로 ID 불변성 성공 기준에서 제외하고 차이 자체는 보존한다.

## 실패 보존
기존 파일 충돌 시 설치하지 않는다. 실행은 매번 새 run ID이고 자동 retry/repair는 없다. 첫 실패의 로그·traceback·부분 raw·forensic ZIP을 보존한다. 입력의 올바른 대상 불일치/근거 변경을 거부한 뒤 cold로 계산하는 것은 사전 등록된 실험 동작이다. 잘못된 packet/proof/schema를 자동으로 고치는 것과 다르다.

Git commit/push, 패키지 설치, 모델 다운로드, 기존 evidence 변경은 수행하지 않는다.
