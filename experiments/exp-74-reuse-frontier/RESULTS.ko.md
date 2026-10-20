# EXP-74 결과: 동치 보존, cold6 비용 개선 실패

## 1. Executive Verdict

AI Research SSH에서 R28을 완료했다. eligible Boolean의 정확한 source 변환은 고정 지원 영역의 유도와 실험 대조를 통과했다. 그러나 매 6입력마다 생성·검증을 수행하는 이번 구현은 비용 채택 기준을 통과하지 못했다. 기존 runtime/production에는 반영하지 않는다. HIGH의 conditional consensus는 이 실험을 선택한 판정이며, 속도 개선이나 미래 입력 품질의 합의가 아니다.

## 2. Consensus Proposal

이번 과제는 완료·미채택으로 닫는다. 원래 정책의 선택 계산을 변환하는 것과 미래 native/reset 품질 증명을 분리한다. 입력·수명·threshold·반복 수를 바꿔 결과를 구제하지 않았다. 다음 연구를 시작하려면 compiler의 실제 재사용 수명을 별도 계약으로 정해야 하며, 이 결과만으로 수명 연장 이득을 단정하지 않는다.

## 3. Strong Consensus

288settles, 총5536ticks를 실행했다. 정책별 tick은 reset=1952, legacy=1792, compiled=1792다. 기존 choose와 native source를 그대로 사용했다. legacy/compiled96대응 cell의 선택·initial·kernel·cache 전이가 타입/float bit까지 동일했고, reset 대비96품질 대조도 status/adopted 동일·state 차이1e-4 이내였다. 최대 terminal state 차이는 2.5807367320940244e-07다. 이는 고정24개 개발 입력을4회 실행한 결과이며, 독립96개 품질 표본이 아니다. 비동일 kernel 대조는16개(블록마다4개)다.

## 4. Material Disagreements

구간 box로 정책을 바꾸는 안과 저장 자료만 분석하는 안을 배제하고 exact Boolean 변환을 선택했다. 비용이 좋아질 것이라는 가정은 실측으로 지지되지 않았다. 수축 q의 실수 map 상계, native 실행 동치, reset 대비 관측 품질과 미래 품질 보장은 서로 구별한다.

## 5. Decision by Axis

| 축 | 판정 |
|---|---|
| 지원 영역의 Boolean 유도 | 단조성·동일 row·고정 goal·인접 binary64 최소성으로 연결, 런타임 source 결속 |
| 의미 대조 | 96/96 exact, 별도 scalar/controller/cost 재생 PASS |
| reset 대비 관측 품질 | 96/96 통과, 미래 입력 보장 없음 |
| cold6 비용 | 모든4블록에서 양 baseline 대비 CPU/wall 개선 실패 |
| case process 총비용 | 모든4블록에서 양 baseline 대비 개선 기준 실패 |
| 채택 | 미채택, production_adoption=false |

## 6. Evidence

각 표의 R/L/C는 reset/legacy_guarded/compiled_guarded다. 단위는 ms이며 블록당4stream 합계다.

| 블록 | cold CPU R | L | C | cold wall R | L | C |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 16.877 | 23.814 | 130.332 | 16.875 | 23.799 | 132.354 |
| 1 | 16.431 | 25.301 | 124.978 | 16.418 | 25.312 | 125.085 |
| 2 | 14.141 | 19.208 | 97.064 | 14.129 | 19.194 | 97.064 |
| 3 | 22.577 | 31.112 | 144.817 | 22.560 | 31.740 | 144.988 |

cold lifecycle에는 설정·program·source/binding, compiler의62회 이분 탐색과 별도 검증, lookup·native·tick trace·상태·결과 구성과 한 번의 전체 직렬화가 포함된다. threshold는 하드코딩하지 않았고 매 lifecycle 생성했다. 실제 cache artifact store/load 호출은0이다. 4stream compiler 생성·검증 CPU는 블록별 111.490, 106.820, 83.113, 123.444ms였다.

| 블록 | process CPU R | L | C | process wall R | L | C |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 588.284 | 596.735 | 711.545 | 766.823 | 766.865 | 817.851 |
| 1 | 592.238 | 614.520 | 727.032 | 719.028 | 769.434 | 819.561 |
| 2 | 510.508 | 508.187 | 598.174 | 668.361 | 668.172 | 668.691 |
| 3 | 703.277 | 741.523 | 799.829 | 774.160 | 879.250 | 883.572 |

process CPU는 case 자식의 getrusage 차분이며 import와 최종 파일 출력을 포함한다. process wall은 runner 호출 구간으로 process wait/polling·scheduling도 포함하므로 정확한 child 내부 실행시간으로 해석하지 않는다. 큰 wall 양자화와 호스트 변동이 있어 통계적 속도나 일반화는 주장하지 않는다.

블록별 비율의 중앙값에서 C의 cold CPU는 R 대비 7.2350배, L 대비 4.9966배다. cold wall은 각각 7.2444배/4.9994배다. process CPU는 1.1906배/1.1801배, process wall은 1.1032배/1.0350배다. 매번의 compiler 비용을 포함한 cold6에서 개선이 없었다는 결론이며, compiler 생성 비용을 무료로 둔 가상 runtime 이득은 보고하지 않는다.

50stage 모두 exit0, 봉인 포함 10.853728초(상한600초), 최대 stage wall 1.171563초(상한60초), child CPU 합계 9.041991초다. 학습·세계측정0, worker1·retry0이며 raw peak 1410186bytes다. Linux Python3.12.3, AS512MiB·parentfile32MiB/child16MiB를 확인했다.

164개 pure oracle 대조·17개 부정대조가 서버에서 통과했다. 수신 raw52개가 같은 채널 manifest의 SHA와 일치했고 로컬 별도 전개 재생의 최대 scalar 오차는 1.3877787807814457e-17다. gate/initial/trace/cost/cache/timing/missing-job 변조7종을 모두 거부했다. frozen source151개는 로컬 SHA가 같고 서버 source-postcheck의151항목이 unchanged였다.

전송은 redacted-adapter-outcome이며 upstream SSH 완전성은 unknown이다. full evidence ZIP(서버 보고 321252bytes)과 로그100개·원격 source 전체 bytes는 수신하지 않았다. 수신한52개 JSON의 동일채널 manifest 일치를 검증한 것이며 독립 서버 attestation은 아니다. 상세 원장은 evidence/reuse-frontier-20261020-r28/transport-receipt.json과 cost-analysis.json에 있다.

## 7. Required Actions

검증된 연구 결과와 음성 결론을 보존한다. 구현자 직접 CS 검토의3개 의무와 bundle check는 PASS다. 이는 근거 결속 검사와 작성자의 source/result 검토이며 독립 구현 감사가 아니다. 최종 범위와 staged bytes를 확인한 뒤 사용자 지시의 서명커밋·main 병합·같은 private remote push를 수행한다.

## 8. Optional Optimizations

추가 반복·입력 선택·threshold 사전 저장·전역 cache·수명 확대를 실행하지 않았다.

## 9. Unresolved

미래 입력의 reset/native 품질, 다양한 program/config로의 확대, 장기 compiler 재사용 비용 이득, 통계적 성능 일반화는 미검증이다. 원 threshold의 bool 동치를 full gate 객체 대체나 새 native 오차 증명으로 해석하지 않는다.

## 10. Method / Run Summary

방향 선택은 HIGH4blind관점+4non-origin 교차검토+별도 fresh Judge, 요청 Sol/xhigh로 완료했다. provider 내부는 NOT_OBSERVABLE이며 specialist/adaptive 추가는0이다. 이후 구현과 실제 결과 검토는 Coordinator가 수행했다. 단일 owner 승인 요청 d3885d9b…로 실행했고 새 실행·재시도·사후 프로토콜 변경은 없다. 처음 DecisionRecord schema의 capability/lifecycle/owner bookkeeping 오류는 실행 전 고쳐 VALID를 확인했으며 과학적 수용 기준을 바꾸지 않았다.
