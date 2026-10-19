# EXP-71 / r25 결과: 정확 고정점 산술 생략은 이번 부하에서 느렸다

**후보를 채택하지 않는다.** 기존 36개 kernel 입력에서 고정점 뒤 산술 18회를 실제 생략하면서 상태·tick 이력·종료·readout·논리 Cost는 원본과 bit exact하게 보존했다. 그러나 고정 7쌍 모두 후보가 느렸고 CPU 시간 비율의 중앙값은 1.436932, wall 시간 비율은 1.437166이었다. 이 연구용 구현은 같은 서버·고정 component 부하에서 각각 약 43.69%·43.72% 더 오래 걸렸다. 의미 보존과 실제 순이득을 구별해야 한다는 음성 결과다.

## 무엇을 새로 확인했나

R24는 과거 저장 궤적에서 정확 반복의 존재만 분석했다. 이번에는 AI Research SSH에서 원 native settle과 연구 전용 fixed-point wrapper를 새로 실행했다. native `src/hcr/dynamics.py`와 settle controller는 수정하지 않았다. 원 R19의18case 중 전이가 있는36kernels를 고정 program/config/initial/drives로 대조했다. 전체 AI task의 새 coupling 경로나 정책·학습·센서 신뢰성을 시험한 것은 아니다.

후보는 실제 native tick으로 current==next의 float bit를 확인한 뒤에만 이후 산술을 생략한다. 근접값·signed zero를 합치지 않고 매 invocation마다 latch를 폐기한다. 원 controller는 residual·patience·observe·margin·history·budget·종료를 매 논리 tick마다 그대로 처리한다. 새 dict를 반환하고 원래 증가할 Cost를 논리적으로 기록한다. 물리 산술 생략은 별도 ledger로 남겼다. 이 구현은 자체 입력과 observer를 소유하는 단일 worker의 연구 경로이며, 외부에서 인자를 변경하는 callback·동시 호출·범용 cache API의 안전성을 보증하지 않는다.

## 의미와 산술 횟수

| 한 번의36kernel 부하 | baseline | fixed_point |
|---|---:|---:|
| 논리 tick | 988 | 988 |
| 실제 native tick 호출 | 988 | 970 |
| 생략된 tick 산술 | 0 | 18 |
| 실제 group update | 4,212 | 4,158 |
| 실제 signal transmission | 8,944 | 8,872 |
| 고정점 검출 검사 | 0 | 970 |

즉 전체 logical tick의 1.82%에 해당하는 산술을 생략했다. 생략 group54개·signal72개는 R24에서 예측한 양과 같았다. 고정점 탐지 뒤에도 논리 Cost는 증가하므로 논리 Cost를 물리 실행량으로 해석해서는 안 된다. 원본과 후보의 최종 state뿐 아니라 모든 tick의 state·residual·stable_steps, convergence·readout·Cost가 타입과 float bit까지 일치했다. 기존 정답을 덜 내놓아 비용을 줄인 비교가 아니다. 새로운 독립 품질/일반화 표본을 얻었다는 뜻도 아니다.

correctness72회와 timing2,016회를 합쳐 native settle2,088회를 수행했다. 같은 입력의 timing 반복까지 포함한 총 logical tick은57,304회, 실제 native tick은56,782회, 생략된 산술은522회였다. 이 반복을 독립 kernel 사례2,088개로 세지 않는다. 학습·World.measure 호출은0회다.

## 전체 component 시간 비교

correctness 대조를 먼저 통과한 뒤 같은 process에서7쌍을 측정했다. 각 block은36kernel×4회=144settle이다. 짝수 index는 baseline→후보, 홀수 index는 반대 순서로 고정했다. 결과를 보고 반복을 늘리거나 block을 제외하지 않았다. Python3.12.3·Linux x86_64, 환경의 cpu_count 관측값은2였다. 호스트 부하 격리나 cold-start 측정은 하지 않았다.

| 쌍 | 실행 순서 | CPU ms: baseline / 후보 | wall ms: baseline / 후보 |
|---|---|---:|---:|
| 1 | baseline→fixed_point | 66.981 / 96.420 | 66.978 / 96.425 |
| 2 | fixed_point→baseline | 66.724 / 96.786 | 66.723 / 96.798 |
| 3 | baseline→fixed_point | 66.699 / 98.638 | 66.702 / 99.210 |
| 4 | fixed_point→baseline | 69.677 / 96.852 | 69.676 / 96.864 |
| 5 | baseline→fixed_point | 78.122 / 96.608 | 78.205 / 96.612 |
| 6 | fixed_point→baseline | 67.183 / 96.537 | 67.181 / 96.551 |
| 7 | baseline→fixed_point | 67.140 / 96.320 | 67.139 / 96.318 |

실행 전 채택 기준은 의미/ledger 검증 통과, paired CPU·wall 비율의 중앙값 각각≤0.95, CPU 개선≥6/7쌍이었다. 의미는 보존했으나 CPU 개선은0/7쌍으로 성능 기준을 충족하지 못했다. 위 비율은 paired 비율의 중앙값이며, 두 arm 시간 중앙값의 비율과 혼동하지 않는다. 이 작은 반복 시험으로 통계적 유의성·다른 장비/부하의 성능을 주장하지 않는다.

timed boundary에는 입력 재구성·개인 drive/initial 복사·후보 설치/복원·고정점 검출·trace 복사·수렴 controller·logical charging·결과 구성·공통 counter/checksum을 포함했다. 후보의 검출 overhead를 빼지 않았다. imports·입력 파일 I/O·최종 검산은 바깥이며 단계 비용으로 별도 기록했다. 전체 후보 경로의 추가 부담이 이번 작은 산술 절감보다 컸다. bit 비교나 wrapper 한 요소의 시간을 따로 분해해 원인 기여도를 측정한 것은 아니다. 학습비용 상각·금액·에너지·제품 전체 비용 절감은 입증하지 않았다.

## 실행·검증·출처

소유자 승인된 요청 `c63e71feb66d5cd6480c147a88caf017945c79f1fdad684f`을 한 번 실행했다. 준비→native matrix→audit3단계 모두 exit0, 봉인 포함 wall2.079776초, child CPU 합계1.801091초였다. 자동 재시도는 없었다. 준비의 합성 tick stub18검사와 실제 state/Cost/stable_steps/physical ledger/timing workload 변조5종 거부가 통과했다.

완전 수신한 correctness·timing·preparation·result·summary5개 JSON의 SHA를 서버 raw manifest와 대조했다. correctness557,277 bytes와 timing6,315 bytes는 한 저장 출력의35개 페이지를 읽어 받았고, 잘림이나 redaction 없이 전체 해시가 일치했다. 로컬 재검산은 새 native/timing 호출을 금지한 채 같은 bit 동등성·ledger·ratio·변조 거부를 확인했다. 수식 재생 최대 절대오차는 서버0, 로컬1.6940658945086007e-21로 PRE1e-15, 상대오차0 이내였다. 이 허용치는 양 arm의 bit 동등성에는 쓰지 않았다. 사후 추가한 `replay_saved.py`는 서버 동결 ZIP 밖의 재검산 도구다.

로컬 동결 source121개의 bytes와 manifest SHA를 확인했고 서버는 source_unchanged=true를 보고했다. 다만 remote source manifest와 postcheck의 일부 경로가 가려져 두 목록의 정확한 bytes를 대조하지는 못했다. 가려진 경로를 복원하지 않고 원문을 보존했다. 정상 완료 run에 없는 failure.json을 함께 읽으려 한 조회1건은 exit1이었고, 함께 나온 redacted postcheck와 오류를 보존했다. **이는 실험 실패가 아니라 선택적 실패 파일 조회의 오류다.** stdout/stderr6개 및 완성 evidence ZIP은 로컬 미수신이며 ZIP 준비 완료를 수신 완료로 세지 않았다.

원 R19의 FAILED_AT_AUDIT·수정 저장 재생·실행 후 전체 source 재해시 미완료 이력은 그대로 보존한다. 이번 새 component 실행 성공이 과거 run 상태를 바꾸지 않는다. 별도 독립 토론 패널이나 구현 독립 감사를 이번에 수행했다고 주장하지 않는다.

CS 조건3개의 구현자 검토와 `check-bundle`은 PASS였다. 이는 같은 동결 후보·의무·원시파일14개의 digest 결속 확인이며 테스트 실행의 진실성·정책 권한·독립 감사를 인증하지 않는다. 성능 악화는 계측 조건의 위반이 아니라 유효한 음성 결과다. 검토 report와 재현 가능한 bundle ZIP을 evidence에 보존했다.

부모 AS512MiB/개별파일32MiB, 준비 child AS512MiB/개별파일16MiB를 관측했다. 최대 stage raw565,430 bytes, stage60초·전체600초 제한 안이었다. stage 종료 raw128MiB는 soft 검사다. hard disk quota·peak RSS·모든 child의 개별 getrlimit·OS 실패 시 봉인 보장을 시험하지 않았다.

## 결정과 재현

이번 연구용 fixed-point wrapper는 원 구현에 편입하지 않는다. 보존한 것은 결과와 이력이고, 줄인 것은 소수의 산술 호출이며, **실제 시간은 늘었다.** 검출을 더 미세하게 최적화하는 후속 실험을 자동으로 추가하지 않는다. 향후 재사용 후보도 충분한 반복량과 관리 비용을 함께 입증해야 한다는 제약으로 남긴다.

- source ZIP SHA256: `8f921838d49a186b9f62c0724287bd4025490e0dc00a1e5edb10a732d9871e58` (374,278 bytes)
- source manifest SHA256: `0269e7a24524eadbcf7b502f87761575b51108847bf93f4eedbeb4c324be0a39` (121 files)
- frozen spec SHA256: `649e7025d568672af94e44ccf8287085c393d7e7ce1cc8a1fa9f2fde236519ec`
- summary SHA256: `011d93379122c0764bcfe1b5d9ccc0d4db82c27af0478e4abbbdc2a7135862f9`
- server evidence ZIP SHA256: `bc2772860b44e1f1229d0bf60f451acfa8b7aaf76788b76dce6a5cf2e9002e40` (49,120 bytes; 로컬 미수신)

저장 결과만 재검산하는 명령(저장소 root 기준):

```powershell
python -B tools/r25_fixedpoint_elision/replay_saved.py --evidence evidence/fixedpoint-elision-20261019-r25 --out <별도-검산-영수증.json>
```
