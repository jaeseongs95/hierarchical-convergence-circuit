# R43 방향 판정 — 동결 전 검토 입력

사용자 요청은 연구 방향을 토론으로 정한 뒤 다음 연구를 실제 진행하는 것이다. 현재 기준 main은 eaba8fdedc3a3cfdaac9f7257dab5acc4bbf5b67이다. 연구 문서·이전 원자료·공통 엔진을 보존하고, 지정된 AI Research SSH에서 자원 상한·worker1/retry0와 사후 튜닝 금지를 적용한다. 새 유료 자원·의존성·서비스·전역 설정·외부 메시지는 범위 밖이다. 기존 비공개 origin push 요청은 유지된다.

HIGH: 서로 다른 실패 함수의 blind reviewer4명(이론 정합성, 의미 계약, 실험 타당성, 구현·비용) 뒤 비원저자 주장 교차검토와 별도 fresh Judge를 적용한다. fork_turns:none은 호스트가 제공하는 격리 수단이며 provider 내부 격리/실제 모델·effort의 외부 증명은 아니다. Terra 선호가 가용하지 않아 노출된 gpt-6.1-sol/xhigh를 요청한다. worker cap8, reserve는 필요할 때만 최대1명이며 현재 미사용이다.

## Coordinator가 직접 확인한 근거

- C1: theory/core-hypothesis.md, evidence/claims.yaml의 H01/H02/H03은 가설이다. formalism/invariants.md는 안정 수렴과 정답을 구별하고 검증 기준 보존을 요구한다.
- C2: exp-75-research-direction/ROADMAP.ko.md는 학습 산출물과 연결되지 않은 성과를 compiler/runtime 연구로 한정하고 중복 비용분해·gate 튜닝으로 음성을 구제하지 않도록 정했다.
- C3: exp-77-macro-control/RESULTS.ko.md는 실제 학습3회·hcr/macro/primitive·K1..4 비용을 이미 비교했다. macro는 최종 primitive 판단을 남겼고 학습 포함 비용 회수가 없었다.
- C4: exp-71-fixedpoint-elision/RESULTS.ko.md는 산술1.82% 생략에도 CPU약43.69% 증가, exp-76-spatial-sharing/RESULTS.ko.md는 약18% 연산 감소에도 cold CPU18.21% 증가를 보고한다. 호출 감소와 총비용 개선을 분리해야 한다.
- C5: exp-88-coarse-profile/RESULTS.ko.md와 analysis.json은 2,304출력/288fullbytepairs 보존, native 부담약2.11%/1.63%, whole-settle약66%를 확인했다. 내부 산술의 비중·제거 가능한 비용·최적화 효과는 확인하지 않았다.
- C6: src/hcr/dynamics.py의 tick 음수분기는 같은 z로 exp(z)/(1+exp(z))를 계산한다. 같은 builtin math.exp 결과를 한 번 계산해 두 위치에서 사용하는 후보가 있다. 실제 bit 보존·시간 이득은 새 실험 전 미확정이다.
- C7: tools/r35_compositional_slot/compiler.py는 depth4/32group의 not/and/or와 top_down link를 생성하고 runtime.py encode_role는 vocabulary index를3bit로 인코딩한다. exp-82-overlap-composition은 실제8leaf패턴과 서로 다른6AST를 검증했다. 동치 AST나 codebook 개입은 다른 질문이다. 기존 namespace 변형은 code 대응을 보존했다.
- C8: tools/r36_overlap_composition/recording.py의 Recorder는 같은 bytes의 후발 참조에서 쓰기를 생략한다. baseline/candidate의 저장기 상태를 분리하지 않으면 선작성/참조 비용이 섞인다.

## 비교할 선택지와 미지수

A. 같은 음수 exp의 분기 내부 재사용 한 변경을 유한 runtime 연구로 한 번 직접 비교한다. 원본 엔진·controller·validation·나머지 산술·trace·Cost는 보존한다. correctness에서만 exp를 실제 계수하고 timing은 probe0, 저장 arm 분리, source/준비/검산/봉인 포함 총비용을 고정한다. 의미는 고정되지만 H03 재사용·학습 효율 검증은 아니다.

B. 의미·AST·Config를 유지하고 일대일 token→3bit codebook만 바꿔 표현 불변성을 검사한다. Hamming 거리·bit 위치·극성·실제 비교쌍 coverage를 먼저 정해야 하며 모든 injective codebook의 증명은 아니다. 각 trace를 재생하되 map 사이 trace 동일은 요구하지 않는다.

C. 동치 AST군과 같은 graph의 top_down ON/OFF를 비교한다. R36의 비동치 함수 비교와 다르지만 AST 변화가 규모·깊이·feedback 경로를 함께 바꾸므로 실패 원인 해석이 더 복잡하다. top_down=False와 gain=0은 다른 개입이다.

세 선택지 모두 현재 수작업/유한 문법 밖의 학습·일반성·제품효율을 주장하지 않는다. 속도·반례 존재·실제 응용 수명은 미지수다. 과거 trace에서 파생한 exp 감소량은 CPU 절감 예측이 아니며, 실행 전 기회/상한과 실행 후 실측을 구분한다.
