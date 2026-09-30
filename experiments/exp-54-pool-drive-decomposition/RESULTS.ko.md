# R073 결과: 이 수식에서는 evidence 증가보다 uncertainty prior 감소의 영향이 컸다

## 결론

R072의 activation 감소를 동일 pool 수식 안에서 분해했다. e1을 0.8→1.0으로 높이면 evidence drive만 바꾼 activation은 조금 증가했고, uncertainty prior만 바꾼 activation은 더 크게 감소했다. 두 변경을 합친 replay는 기존 감소 관찰을 재현했다. prior=0이면 evidence를 0.8에 고정해도 M0/M1의 수치 입력과 궤적이 같아졌다. 이 조건에서는 checkpoint 차이를 수치 drive로 전달하는 prior 항의 소멸로 기존 관찰을 설명할 수 있다.

## 관찰

[동결 명세](frozen_spec.json), [replay 집계](../../HCR-Evidence/exp54/r073-20260930T211742Z-26d148fdc6/summary.json), [별도 검산](../../HCR-Evidence/exp54/r073-20260930T211742Z-26d148fdc6/verification.json)을 기준으로 한다. 기존 native 12개 관찰을 다시 검산했으며, 같은 program·initial state·top_down·config·checkpoint에서 evaluator 수식 replay 18개를 계산했다. 새 native 실행·학습·feedback·독립 표본은 모두 0이다.

아래 값은 score 0.8의 terminal activation 대비 차이다. `E`는 evidence-only, `P`는 prior-only, `J`는 joint이며 결합 비가산 항은 `J−E−P+B`다.

| checkpoint | e1 | ΔE | ΔP | ΔJ | 비가산 항 |
| --- | --- | --- | --- | --- | --- |
| M0 | 0.6 | −4.49168e−6 | +3.85761e−4 | +3.81852e−4 | +5.83227e−7 |
| M0 | 1.0 | +8.97408e−7 | −4.14799e−4 | −4.13767e−4 | +1.34400e−7 |
| M1 | 0.6 | −5.02222e−6 | +8.41581e−5 | +7.92743e−5 | +1.38398e−7 |
| M1 | 1.0 | +1.00336e−6 | −8.53954e−5 | −8.43635e−5 | +2.84449e−8 |

score 0.8에서는 모든 차이와 비가산 항이 0이었다. 방향 예측 18개와 zero-prior의 두 checkpoint 대응 예측은 모두 supported였다. joint 여섯 replay는 두 threshold arm의 기존 12개 native pool 궤적·자연 종료·eligibility와 tolerance 이내에서 대응했다. 별도 수식의 최대 차이는 9.44e−16으로 동결 tolerance 2e−12보다 작았다. 모든 replay는 stable_decision으로 자연 종료했으며 evaluator 반복 횟수는 각각 35였다.

score 1.0의 evidence-only에서 midpoint eligibility는 M0=True/M1=False로 유지됐다. prior-only와 joint에서는 M0/M1 모두 False였다. prior-only에서는 evidence drive를 0.8에 고정해도 prior가 모두 0이 되어 두 checkpoint의 수치 입력·궤적이 정확히 같았다. default threshold의 counterfactual eligibility는 전 셀 True였다. 이 값은 수식 분류이며 새 native 선택 기록이 아니다. 기존 R072의 실제 True 오답과 native ticks 68은 parent 관찰로만 남긴다.

## 해석

이번 코드 조건에서 evidence 증가 자체는 회로 활성도를 조금 올렸지만, 같은 score 변화가 uncertainty prior를 줄이는 영향이 더 컸다. 따라서 R072의 역방향 activation 관찰은 evidence 효과의 반전으로 해석할 필요가 없다. zero-prior에서 checkpoint 차이가 사라지는 기존 코드 설명은 native 관찰 대응과 두 가지 수식 개입으로 지지됐다. 이는 같은 원자료를 설명하는 추가 검산이며 독립 연구 증거가 아니다.

결합 효과는 정확히 가산적이지 않았다. 작은 양의 비가산 항은 동기 갱신·sigmoid·top_down과 자연 종료를 함께 포함한 terminal activation 함수에서 계산한 값이다. 특정 링크나 생물학적 메커니즘 하나의 기여로 분리하지 않았다.

## 대안 설명

evidence-only 효과가 작은 이유에는 강한 양의 evidence drive에 따른 포화와 이 짧은 경로의 입력 배치가 포함될 수 있다. 이번 분해만으로 그 크기의 원인을 구분하지 못했다. M0/M1는 strength·version·failures·이력을 포함한 checkpoint bundle이다. 같은 prior 항을 바꾼 수식 결과를 순수 native strength 개입이나 실제 기억 기능의 완전 소멸로 일반화하지 않는다.

## 판별 실험

기존 감소 관찰의 수식 설명은 이번에 정리됐다. [다음 질문](NEXT.ko.md)은 evidence-only 효과가 작은 이유를 확인할 필요가 있을 때만 evidence gain을 제한된 두 값으로 비교하는 evaluator 분해다. 새 native 실행의 필요성은 별도 조건 동결 전에 판단한다.

## 현재 주장 가능한 범위

observed: 봉인 자료의 재검산과 제한된 수식 replay에서 evidence-only와 prior-only의 방향이 반대였고 prior 감소의 절대 변화량이 더 컸다. partially-supported: 완전 양의 입력에서 prior 항이 0이 되어 이 pool의 checkpoint 수치 차이가 사라진다는 코드 설명. supported는 이번 수식 명세의 예측 상태이며 새로운 native 발견을 뜻하지 않는다. unsupported: 연속구간의 일반 강건성, 다중 회로 경쟁, 학습 우위, 판단 교정, HCC 고유 우위, 인간·모델 내부 기제와 시간·전력 효율.

counterfactual replay에 native expansions·decision cost를 부여하지 않았다. evaluator 반복 횟수와 native kernel ticks를 합산하지 않는다. 에너지·peak memory는 null이다. 별도 프로세스와 별도 수식 구현의 내부 검산이며 외부 연구자의 독립 재현은 아니다.

## 검증 기록

첫 run은 reduced-budget self-test가 `max_ticks ≥ patience` Config 조건을 어겨 멈췄다. [실패 자료](../../HCR-Evidence/exp54/r073-20260930T211539Z-d719c0ba3d/failure.json), native anchor 재분석과 로그를 보존했다. recurrence 연구 계산 전에 발생한 구현 오류이며 자동 retry는 없었다. [진단](../../HCR-Evidence/r073-validation/selftest-diagnosis.json) 뒤 self-test의 max_ticks와 patience를 모두 1로 수정했다. 연구 config·입력·예측은 바꾸지 않고 새 run을 만들었다.

성공 run에서는 replay 변조 8종과 집계 변조 4종을 거부했고 budget_exhausted 및 stable_ambiguous 장치 검사를 보존했다. core 회귀 결과와 최종 byte·ZIP·범위·수용 판정은 [전달 검증](../../HCR-Evidence/r073-validation/delivery-verification.json)에 연결한다. `Run-HCR-R073.cmd`로 동일 흐름을 새 폴더에 실행할 수 있다.
