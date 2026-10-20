# EXP-73 / R27 결과: 관측된 유한 종료는 인증했지만 선별 비용 문제가 남았다

**R26 guarded의 관측된 24쌍을 사후 인증했다. 실행 전 채택 gate나 비용 개선으로 채택하지 않는다.** 정확한 전체 kernel record 동일성이20쌍, 마지막 native 갱신의 점별 수치 결함을 포함한 수축 오차 경계가4쌍이다. carry는24쌍 중10쌍만 인증하고14쌍은 미인증이었다. 인증한 쌍에서 관측 품질 기준 위반은0이었다. 저장된 R26 비용에서 다른 비용이 고정이라는 조건을 두면 gate CPU 비용을 약97.12% 줄여야 순이득이 난다. 최적화된 구현이나 통계적 성능 개선을 측정한 결과는 아니다.

## 새로 확인한 범위

기존 EXP62 계열에 잔차·수축 기반 종료/거리 분석이 있고, R26에는 입력별 실수 map의 전역 수축 상계가 있다. 이번 새 개입은 **이미 끝난 R26 native warm/reset 기록의 마지막 step을 exact-rational exp 구간으로 둘러싸 점별 결함을 계산하고, 서로 다른 tick 수에서 끝난 두 상태의 품질 경계를 확인한 것**이다. 새 수축 정리나 단순 초기값 실험으로 세지 않는다.

R26의4stream×6입력×3arm=72record 전체, reset 대비 carry/guarded의48pair 전체를 사용했다. 원 native source·controller·기억·과거 연구를 변경하지 않았다. 신규 native 추론·학습·World.measure·성능 benchmark는0회다. 저장 궤적은 별도 scalar 수식으로 재생했으며 새로운 태스크 입력의 native 실행으로 표현하지 않는다.

실행 전에 고정한 [설계](design.ko.md), [spec](frozen_spec.json), [입력 hash](input_manifest.json)의 정책과 허용치를 바꾸지 않았다. threshold 탐색, 좋은 입력 선별, 반복 확대, 새 독립 토론 패널은 수행하지 않았다.

## 실제 유한 종료의 인증

R26의 이상적 실수 map F와 weighted norm(1,1,8)을 그대로 사용했다. q<1인 기록의 마지막 native step에서 입력p와 출력y를 가져오고, Fraction으로 logit과 exp의 구간을 계산했다. exp는 고정128항 양의 Taylor 합·기하급수 tail 및2^-192 dyadic 바깥쪽 반올림으로 둘러쌌다. 별도 verifier는 항마다 반올림하지 않는 exact Fraction 합과 tail로 제안 구간을 검산했다. 플랫폼 math.exp가 정확 반올림된다는 가정은 사용하지 않았다.

관측된 eta>=||y-F(p)||와 마지막 상태 변화r로부터

    rho = (eta+q*r)/(1-q)

가 해당 종료 상태와 공통 이상적 고정점의 weighted 거리를 둘러싼다. 두 rho를 더한 성분별 상계가1e-4 이하이고, 재생된 두 native status가 stable_decision이며, goal 구간 전체가 같은 부호와 고정 margin_threshold를 만족할 때 pair를 인증했다. 실제 adopted와 상태 차이도 별도로 대조했다. q>=1은 미인증이지 비수축·오답의 증명이 아니다.

| reset 대비 방식 | 비교 쌍 | 전체 record 정확 동일 | 수축 오차 경계 인증 | 미인증 | 인증 쌍의 품질 위반 |
| --- | ---: | ---: | ---: | ---: | ---: |
| carry | 24 | 4 | 6 | 14 | 0 |
| guarded | 24 | 20 | 4 | 0 | 0 |

정확 동일성은 타입·float bit까지 포함한 **전체 kernel record**의 동일성이다. guarded의20쌍은 reset을 선택한18쌍과, 직전 중립 reset의0.5 state를 warm 초기값으로 전달하여 reset과 같은 기록을 낸 strong 두 stream의 step3 두 쌍이다. 따라서20을 모두 reset 정책 선택으로 해석하면 안 된다. R26의 guarded warm 시작은 여전히6회이며, 그중4쌍에 비자명한 수축 오차 인증이 적용됐다.

guarded 수축 인증4쌍은 strong positive/negative-first의 step1/4다. terminal 최대 성분 차이의 인증 상계는 최대 약1.18547e-5로 허용치1e-4 안이고, 실제 차이는 최대 약2.58074e-7이었다. carry 수축 인증6쌍에는 strong 두 stream의 step3도 포함되며, 최대 인증 상계는 약1.18549e-5였다.

72record 중24개는 finite terminal envelope를 계산했고48개는 global q 상계가1 미만임을 보이지 못했다. 인증한 점의 weighted 마지막 변화r 최댓값은 약1.22549e-7, 점별 native 결함 상계 eta 최댓값은 약1.28719e-16, rho 최댓값은 약8.67749e-7이었다. exp 제안 구간 폭 최댓값은 약8.52304e-56으로 고정 검산 기준1e-40보다 작았다. 정확한 유리수 끝점·반경은 raw JSON에 보존했다.

carry 미인증14쌍 중8쌍은 R26에서 관측 품질이 달랐고6쌍은 품질이 같았다. 미인증을 오답 판정으로 바꾸면 후자6쌍을 잘못 해석한다. 이번 인증은 reset과의 같은 종료 status/adopted 및 terminal 차이1e-4 이내라는 기준이며, 외부 세계의 정답·학습 성능을 인증하지 않는다.

## gate 비용의 조건부 손익분기

R26의 gate 포함 비용C, 그중 gate 비용G, reset 비용R에서 `D=R-(C-G)`를 계산했다. **그 밖의 비용이 그대로일 때만** 새 gate 비용이D보다 작아야 순이득이다. gate를 전체에 다시 더하지 않았다. CPU와 wall을 합치지 않았고, 이번 분석 시간을 원래 gate 시간으로 바꾸지 않았다.

| 전체24입력 기준 | CPU | wall |
| --- | ---: | ---: |
| 저장된 reset R (ms) | 6.523254 | 6.491059 |
| 저장된 guarded C, gate 포함 (ms) | 11.109569 | 11.078949 |
| 그중 gate G (ms) | 4.722266 | 4.699977 |
| 다른 비용 고정 시 허용 gate 예산D (ms) | 0.135951 | 0.112087 |
| 순이득에 필요한 gate 감소 | 약97.12%보다 큼 | 약97.62%보다 큼 |

전역 및4stream×prefix K=1..6의 CPU/wall, 총50개 원장을 보존했다. K>=2의20개 CPU prefix 중6개는D<=0이었다. 전체6입력 strong_negative_first의 wall 및 weak_positive_first의 CPU/wall에서도D<=0이었다. 이 항목들은 gate를0으로 만들어도 다른 비용 고정이라는 가정 안에서는 이기지 못한다.

가상으로 같은 gate 비용G를 유효하게 m회 분담하고 다른 비용이 그대로라면 `m>G/D`다. 전역 CPU는 최소35회, wall은 최소42회라는 산술이 나온다. **실제로35/42회 쓰면 이긴다는 실험 결과가 아니다.** 입력 영역·binding에 대한 certificate 공유 타당성, 컴파일·저장·조회 비용, 반복 입력 분포와 수명은 확인하지 않았다. native 반올림과 유한 종료를 미래 입력에 보장하는 prospective certificate도 없다.

비용 입력은 R26의 작은 고정 부하를 한 번 측정한 값이다. 실제 kernel record가 같아도 순서·잡음·상태 관리 비용 때문에 시간은 다르다. 따라서 D와 감소율은 이 저장 관측의 조건부 예산이며 인과 추정·성능 예측·통계적 속도 향상으로 일반화하지 않는다. R27에서 학습 비용은0이므로 학습이 있는 방식과의 총비용 비교도 아니다.

## 실행과 검증

AI Research SSH `aws-local`의 대체 요청 `e3d3d6a79ad7e2317aa1c256fbc45270588b4b4d45bd739f`가 소유자 승인(`owner`)으로 완료됐다. 앞선 `ff95a800...`는 한 시간 유효기간이 지난 뒤 포털이 unknown request를 반환했다. 읽기 전용 ls에서 ZIP은 있으나 분석 폴더가 없었고, source121 불변을 확인해 같은 고정 ZIP으로 대체 요청을1회 제출했다. 구요청의 과거 실행이 절대 없었다고 단정하지 않으며, 구요청 기록을 삭제·성공 처리하지 않았다. ZIP 재전송이나 입력 변경은 없었다.

실제 분석은 Linux/Python3.12.3, worker1/retry0이었다. 준비→4stream→audit의6stage가 모두 exit0이고, 봉인 포함3.781887초로600초 상한 안이었다. child CPU 합3.426872초, stage 종료 시 raw 누적 최댓값284,324bytes다. 각 stage60초 상한을 지켰다. 부모 AS512MiB/파일32MiB 및 준비 child AS512MiB/파일16MiB를 기록·확인했다. peak RSS·hard disk quota·모든 OS 실패의 봉인을 보증하지 않는다. 이 값은 사후 분석/검산 비용이며 R26 후보의 runtime 비용이 아니다.

서버 준비에서 신규 순수 수식·경계23개와 기존 정책 경계35개가 통과했다. interval/q/radius/source/order/scope/pair/cost 변조8종을 각각 의도한 사유로 거부했다. 인증 실패는 유효한 결과이고, 검산 실패·잘못된 인증과 구별했다.

수신한4stream/preparation/result/summary의7개 JSON 전체 bytes가 raw manifest SHA-256과 일치한다. 로컬 [저장 결과 검산](../../evidence/finite-stop-envelope-20261019-r27/local-replay.json)에서도 source121, raw7, 별도 Taylor 전개·point defect·pair 판정·50개 비용 원장과8종 변조를 확인했다. 새 native/benchmark 호출은0이었다. `replay_saved.py`는 source 동결 이후 추가한 로컬 전용 helper이며 서버 ZIP/동결 CS 후보6파일에 포함되지 않았다.

CS 의무 BOUND/RECORD/COST3개의 구현자 검토 및 check-bundle이 PASS다. raw 파일·후보·동결 계약 결속을 확인한 결과이며 독립 수학 감사·정책 권한 인증·실행 attestation은 아니다. 재현 bundle과 receipt는 [evidence](../../evidence/finite-stop-envelope-20261019-r27/)에 보존했다.

## 출처와 제한

송신 source ZIP은398,048bytes, SHA-256 `7d23265d6ab704663e7222a76063dd98c4f1e20aa236f68687b0952c0e078594`다. source121과 입력18개를 실행 전에 고정했다. manifest SHA는 `f0c5a2cba0de3b0f15dbfe55af7e1fce55cdf40dc30943961c342404be70e916`이고 서버는 같은 hash와 source_unchanged=true를 보고했다. 송신 사본과 원격 목록 재수신을 구별하며, 원격 source/postcheck 전체 목록의 원문은 회수하지 않았다. 실행 명령은 ZIP SHA를 확인한 뒤에만 exclusive root를 생성한다. 재개 시 별도 read-only sha256sum 조회는 INVALID_ARGUMENT로 거부돼 사전 원격 재해시 성공으로 보고하지 않는다.

adapter는 redacted outcome과 upstream completeness unknown을 표시한다. 핵심 raw7개는 개별 hash로 완전성을 대조했지만 manifest도 같은 채널의 자료이며 독립 서명이 아니다. stdout/stderr12개, 원격 evidence ZIP, source-postcheck 원문은 수신하지 않았다. completion이 보고한 ZIP은45,209bytes / SHA `dccceb9a29511abb90d954408480a694751b3698ab5d9ad5dcd1956a4dff07be`이며 로컬 다운로드·검증으로 바꾸지 않는다.

**인증은 이 hash 고정 기록의 관측된 종료 상태에만 적용한다.** eta는 마지막 한 점의 native 결함 상계이고 함수 전체·다음 step의 uniform roundoff bound가 아니다. 미래 입력의 종료 status를 예측하지 않으며, native 동역학 전체와 이상적 실수 map이 같다는 증명도 아니다. 일반 품질·학습 우위·제품 채택을 주장하지 않는다.

## 다음 비중복 질문

유한 종료 품질을 설명할 수 있다는 점은 확인했지만, 사후 인증에는 이미 계산한 기록이 필요하고 비용은 줄지 않았다. 다음 후보는 **구조·입력 영역별 충분조건을 실행 전에 검증해 공유할 수 있는지, 그 공유 비용과 조회 비용까지 포함한 예산이 위 D 안에 드는지**다. 동일 global q를 공유할 수 있다는 사실만으로 prospective native 품질 certificate를 얻었다고 해석하지 않는다. native 유한 종료 보존 조건을 먼저 분리하고, 고정한 입력 영역과 수명·손익분기 계약을 만족할 수 있을 때만 작은 후속 실험을 선택한다. 이번 결과로 자동 편입이나 더 큰 실험을 시작하지 않는다.
