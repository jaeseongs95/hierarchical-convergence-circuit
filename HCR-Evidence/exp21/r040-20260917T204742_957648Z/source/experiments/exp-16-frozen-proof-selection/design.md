# EXP-16: 고정 native 상태에서 재구성과 선택의 분리

기준 커밋은 `a9c643954696cbe309f29691bf63e5d4fe463f91`이다. 실행 정의는 `tools/r035_frozen_selection/spec.py`, 상세 설계는 `docs/R035_DESIGN.ko.md`에 있다.

## 질문

원 native proof를 다시 만들기만 해도 보류가 해소되는가, 아니면 같은 activation/생성 경로에서 관측 지지를 반영한 선택이 필요한가?

## 대조

`native_saved`, 실제 기존 `hcr.proof.reconstruct` 호출인 `native_rebuild`, `support_first`를 동일 공개 상태에서 비교한다. 각 원 snapshot에 node alias×edge alias×edge slot 역순×경로 역순의 16개 선택 경계 재표현을 적용한다. 예산 0 대조는 별도 그룹이다.

## 자료와 범위

EXP-15 `main/expand_only`의 모든 case×scope에서 사전식 첫 world의 모든 candidate를 사용한다. 최초 판단도 보존한다. 같은 상태/다른 world를 독립 표본으로 세지 않는다. 새 native Graph 실행, input-to-Graph 이름 효과, 학습된 controller는 이번 범위 밖이다.

## 판정

생성기는 raw만 기록한다. 독립 evaluator가 원 EXP-15 전량을 재검산하고, 새 변형/정책/예산/proof DAG/깊이/최초 시도 로그를 다시 계산한 뒤 보고서를 만든다. 외부 정답은 audit 통과 요건이 아니다. identity native 재구성이 보존 proof와 다르면 그 차이를 선택 개선으로 집계하지 않고 측정 불일치로 중단한다.

이 계획은 EXP-15를 본 뒤 정한 후향적 개입 정의이며 독립적인 새 문제 일반화 결과를 주장하지 않는다.
