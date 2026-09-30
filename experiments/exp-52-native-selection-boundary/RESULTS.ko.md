# R071 결과: 선택은 분리됐지만 판단과 총 ticks는 같았다

## 결론

R070에서 도출한 midpoint threshold를 적용한 native 실행에서 M0는 circuit, 더 약화된 M1은 primitive를 선택했다. 네 평가의 route_only 최종 판단과 채택은 모두 True 오답이었다. 선택 경계의 민감도는 확인했지만 행동 교정은 일어나지 않았다.

## 관찰

[집계](../../HCR-Evidence/exp52/r071-20260930T132808Z-695d047b35/summary.json)와 [별도 검산](../../HCR-Evidence/exp52/r071-20260930T132808Z-695d047b35/verification.json)을 기준으로 한다. 각 threshold의 empty memory에서 training 세 개와 두 donor의 native 피드백을 수행했다. 실제 회로 재사용과 약화로 strength 0.55→0.11→0.022, circuit version 1→2→3, failures 0→1→2가 확인됐다. 네 평가는 동일 관측 e0=1.0/e1=0.8, revision=1을 사용했다.

| threshold | checkpoint | pool activation | eligible | 최초 선택 | expansions | pool/decision ticks | 판단·채택 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.55 | M0 | 0.9942212668099926 | True | circuit | 1 | 35/33 | True 오답 |
| 0.55 | M1 | 0.9938918635122408 | True | circuit | 1 | 35/33 | True 오답 |
| 0.9940565651611166 | M0 | 0.9942212668099926 | True | circuit | 1 | 35/33 | True 오답 |
| 0.9940565651611166 | M1 | 0.9938918635122408 | False | primitive | 2 | 35/33 | True 오답 |

같은 checkpoint의 두 config에서 pattern/program·strength·episodes·version·failures·active·pending projection이 같았다. pool grammar·drive와 전체 수치 궤적도 같았으며 mismatch는 0이었다. threshold만 pool settle 이후 eligibility 판정을 다르게 했다. midpoint-M1의 실제 전개는 primitive [0] 뒤 [1]이고 나머지는 circuit [0,1]이었다. 전체 native kernel ticks는 모두 68이었다.

준비 실행 10개, 평가 4개, native 피드백 10회가 수행됐다. 이는 하나의 동결된 결정적 toy 비교이며 독립 표본 14개가 아니다. midpoint는 기존 R070 자료에서 고른 값이다. 원자료를 새 native 실행 증거로 기록하되 경계 발견의 독립 성공으로 세지 않는다.

## 해석

회로 약화의 수치 차이가 실제 circuit/primitive 선택에 연결될 수 있다는 좁은 예측을 지지한다. R069 기본 조건에서 선택이 유지됐다는 관찰은 그대로다. circuit 선택을 제외해도 같은 관측과 route_only decision 근거로 True 오답이 유지됐다. 따라서 회로 제외 자체가 오류 수정의 충분조건은 아니었다.

전개 수의 차이와 kernel ticks의 차이는 별개였다. primitive 경로는 두 번 전개됐지만 pool/decision network ticks는 같았다. 이를 wall-time, 메모리나 에너지 효율로 확대하지 않는다.

## 대안 설명

단일 회로 후보와 짧은 경로가 선택 변화에도 판단·ticks가 같았던 결과와 양립한다. threshold를 기존 activation 사이 좁은 구간에 정했으므로 자연 입력 변화에서의 일반적 민감도나 강건성은 확인하지 않았다. M0/M1는 strength뿐 아니라 feedback·version·failures를 포함한 checkpoint bundle이며 순수 strength 개입이 아니다.

## 판별 실험

[다음 작업](NEXT.ko.md)은 threshold와 checkpoint를 고정한 입력 변화에서 선택 분리가 유지되는 범위를 별도로 검사한다. 선택, 정답, proof와 비용을 계속 분리하며 새 메커니즘을 붙이지 않는다.

## 현재 주장 가능한 범위

observed: 계약을 보존해 native로 형성·약화한 단일 후보에서 threshold에 따른 실제 선택 분리가 나타났다. 네 평가의 판단·채택은 True 오답이고 native ticks는 같았다. partially-supported: R070의 약화 신호→eligibility 경계→선택 경로라는 설명이 이 특정 조건의 native 결과와 맞는다. unsupported: 독립 경계 발견, 순수 strength 효과, 회로 간 경쟁, 일반적 학습 우위, 행동 교정, 자율 sensing과 HCC 고유 우위.

검산은 생산 runtime과 분리된 수식·프로세스로 수행했다. 독립 연구자의 외부 재현은 아니다. 실제 에너지와 peak memory는 측정하지 않았다.

## 검증과 복구

최초 실행은 모든 native 원자료를 저장한 뒤 집계의 raw_value 필드 오타로 실패했다. [최초 실패](../../HCR-Evidence/exp52/r071-20260930T132520Z-7de16f135c/failure.json)와 봉인된 source·로그를 보존했다. raw_decision으로 수정하고 새 recovery 폴더에서 같은 자료의 검산·집계를 수행했다. 추가 native 실행은 0이며 원자료와 최초 실패 폴더의 전체 바이트 hash가 보존됐다. 일곱 종류 변조와 기존 memory의 config 불일치를 거부했다. 최종 회귀·bundle·범위·수용 결과는 [전달 검증](../../HCR-Evidence/r071-validation/delivery-verification.json)에 기록한다.

재현 진입점은 Run-HCR-R071.cmd다. 저장된 최초 실패의 분석만 복구하려면 Run-HCR-R071.cmd --recover HCR-Evidence\exp52\r071-20260930T132520Z-7de16f135c를 사용한다. 기존 결과는 덮어쓰지 않는다.
