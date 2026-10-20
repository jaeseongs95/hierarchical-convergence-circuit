# R39 방향성 토론

## 1. Executive Verdict
조건부 합의다. R38의 XY 투영 다음에 XY조건부 Z 허용집합의 보존을 검증한다. 수치 정확성은 아직 미관측이며 실행과 원자료 검산이 필요하다.

## 2. Consensus Proposal
Z별 XY4 두 slice를 보존하는 native_joint, 동일 triple을 계산한 뒤 XY4/Z2 주변집합만 남기는 native_compact, 동일 최초정보 exact_joint를 비교한다. 질의 전에 producer를 봉인하고 공개 slot4개와 unaryZ전체를 같은 표현에서 소비한다.

## 3. Strong Consensus
unaryZ 성공은 conditionalZ 충분성이 아니다. 두 관계표의 XY/Z 주변집합이 같아도 조건부 답은 반대일 수 있다. 정보손실 개입과 별도 full/product oracle를 구분하고, host 정답 수리나 출처 해시 조회를 금지한다.

## 4. Material Disagreements
넓은518context 대신 먼저 판별표 중심의28context가 제안됐다. 교차검토에서 비대각 XY양성 경로가 빠지는 결함을 발견해 (R6,S9,U6)을 추가한32context로 확정했다. 나머지 관계표 밀도/행수0·3·4까지의 확대는 이번 주장에서 제외한다.

## 5. Decision by Axis
의미: XY조건부Z set/분류/선택을 검증한다. 구현: 기존3leafAND/OR/feasible2, 공개 slot routing과 격리된 수치consumer를 쓴다. 자원:32context/160context-query쌍/480arm출력이며6360수렴·전체180초를 운영상한으로 고정한다.

## 6. Evidence
R38 runtime의 projection/반환경계, R35 compiler의5group AND3/11group feasible2, 독립8triple 상징 열거와 R38실측을 직접 확인했다. decision-record.json에 source locator와SHA를 기록한다. reviewer의 동의 자체를 증거로 세지 않는다.

## 7. Required Actions
producer가query를받기전에1회봉인하고,consumer에선언수치payload/publicslot/fixedcfg/docs/initial외정보를주지않는다. 모든중간층·Zeligibility·kind/selected·unary/conditional·변형·source/scalar/controller/cost를검산한다. 정보손실과구현오류/증거부족을분리하고동결뒤재실행/retune하지않는다.

## 8. Optional Optimizations
factor/separator표현과518context확대는현재과제성공에필수아니므로추가하지않는다.

## 9. Unresolved
새native결합의실제수렴은미관측이다. 최소표현·일반정보론적복원불가능성·일반CSP·학습·효율우위는이실험으로판정하지않는다. 동일한것은고정margin의허용의미payload이며rawpacket/연속수치의완전동일성이아니다.

## 10. Method / Run Summary
MEDIUM, degraded_ok 기본, 두 reviewer를 fork_turns:none으로시작하고비원저자교차검토를각1회수행했다. Coordinator가직접증거를확인해통합했다. 별도Judge요구가없어만들지않았으며assurance는partially_independent다. reserve/specialist/adaptive재숙고없음. 선호Terra모델이호스트에없어명시override없이상속설정을썼으며실제모델/effort는별도관측되지않았다. 재위임·다른세션native기록열람·파일변경·SSH실행은reviewer가수행하지않았다. 플랫폼격리의외부증명/구현완료감사를대신하지않는다.
